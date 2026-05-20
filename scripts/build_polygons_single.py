"""Build Thiessen (Voronoi) polygons for the 2027 RMS network.

Pipeline:
    1. Load Vina Subbasin boundary (raw/vina_subbasin.geojson).
    2. Project boundary + 27 unique RMS-site coords to California Albers (EPSG:3310)
       so the Voronoi tessellation is computed in equal-area metric space
       (DWR / B118 standard for area-weighted GW work).
    3. Build a Voronoi diagram around the 27 unique RMS sites.
    4. Clip each Voronoi cell to the Vina Subbasin polygon.
    5. Verify that exactly one cell maps to each unique site (27 polygons).
    6. Re-project the clipped cells back to WGS-84 (EPSG:4326).
    7. Emit:
         - data/vina_2027_thiessen_single.geojson  (FeatureCollection)
         - js/polygons-data-single.js
             (`const RMS_POLYGONS_SINGLE = [...]`, rings in [lat,lng] order
             to match the Leaflet UI in main.js)

This is the SINGLE-TESSELLATION method: one Voronoi diagram across the
whole basin. Companion to `build_polygons_three_zone.py`, which produces
three independent tessellations (one per management area). The dashboard
loads both and lets the viewer toggle between them in §5.2.

Notes / decisions baked in:
    - The Voronoi seed set is the unique sites among the wells flagged `2027 GWL RMS? = Yes` in
      `BC Network 2026 v8.xlsx`. The single Butte-basin row in the workbook
      is *not* a 2027 RMS well, so the seed set sits entirely in Vina.
    - Polygon membership is unambiguous: each cell contains exactly one seed
      well by construction. No 2022-style Chico dissolve, no membership
      override needed.
    - We do *not* apply a sliver-area filter — every cell is a real Voronoi
      cell of a real RMS well. The smallest valid cell wins, even if narrow.
    - Mgmt-area attribution is carried straight from the xlsx
      (01-Vina-North / 02-Vina-Chico / 03-Vina-South).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parent.parent
WELLS_JSON = ROOT / "data" / "wells_resolved.json"
BOUNDARY = ROOT / "raw" / "vina_subbasin.geojson"
GEOJSON_OUT = ROOT / "data" / "vina_2027_thiessen_single.geojson"
JS_OUT = ROOT / "js" / "polygons-data-single.js"

WGS84 = "EPSG:4326"
ALBERS = "EPSG:3310"  # NAD83 California Albers, equal-area meters

# Mgmt-area -> short label and color (mirrors 2022 dashboard scheme; Chico is
# rendered as Chico to keep continuity with the GSP figures).
MA_SHORT = {
    "01-Vina-North": "North",
    "02-Vina-Chico": "Chico",
    "03-Vina-South": "South",
}


def load_seeds():
    """Return one seed PER UNIQUE LAT/LNG SITE.

    Post-2026-05-19 the 2027 RMS network includes nested completions
    (CWSCH ×7 + 22N01E28J ×3) that share lat/lng. scipy.spatial.Voronoi
    can't handle coincident points; collapse each nested cluster to a
    single seed. Each seed carries the list of SWNs at that site so the
    dashboard can use `polygonWells()` to find all wells in the cell.
    Returns: list of (zone_label, rms_well_swns, mgmt_area_full, lon, lat).
    """
    wells = json.loads(WELLS_JSON.read_text())
    by_site = {}
    for w in wells:
        if not w["is_2027_gwl_rms"]:
            continue
        key = (round(float(w["latitude"]), 5), round(float(w["longitude"]), 5))
        by_site.setdefault(key, []).append(w)
    seeds = []
    for (lat, lng), wells_at_site in by_site.items():
        swns = [w["swn_or_name"] for w in wells_at_site]
        # Stable label: first SWN, alphabetically
        label = sorted(swns)[0]
        # Pick the mgmt_area_full of the first well (they share location)
        ma_full = wells_at_site[0]["mgmt_area_full"]
        seeds.append((label, swns, ma_full, lng, lat))
    return seeds


def make_polygons(boundary_albers: Polygon | MultiPolygon, seed_albers: list[tuple]):
    """Build Voronoi polygons clipped to the boundary, one per seed."""
    coords = np.array([[seed[3], seed[4]] for seed in seed_albers])

    # Buffer the boundary box outward for distant "anchor" points so the
    # outer Voronoi cells are bounded (scipy Voronoi otherwise emits open rays).
    minx, miny, maxx, maxy = boundary_albers.bounds
    dx, dy = maxx - minx, maxy - miny
    anchors = np.array([
        [minx - 10 * dx, miny - 10 * dy],
        [maxx + 10 * dx, miny - 10 * dy],
        [minx - 10 * dx, maxy + 10 * dy],
        [maxx + 10 * dx, maxy + 10 * dy],
    ])
    all_pts = np.vstack([coords, anchors])

    vor = Voronoi(all_pts)

    cells = []
    for site_idx in range(len(coords)):
        region_idx = vor.point_region[site_idx]
        region = vor.regions[region_idx]
        if -1 in region or not region:
            raise RuntimeError(f"Open Voronoi region for site {site_idx} — anchor box too small")
        ring = [vor.vertices[i] for i in region]
        cell = Polygon(ring)
        clipped = cell.intersection(boundary_albers)
        if clipped.is_empty:
            raise RuntimeError(f"Cell {site_idx} clipped to empty (well outside boundary?)")
        # Some intersections produce GeometryCollections — keep only polygons
        if clipped.geom_type == "GeometryCollection":
            clipped = MultiPolygon([g for g in clipped.geoms if g.geom_type in ("Polygon", "MultiPolygon")])
        cells.append(clipped)
    return cells


def geom_to_rings_latlng(geom):
    """Return list of rings (list of [lat,lng] pairs) for Leaflet polygon input."""
    rings = []
    geoms = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    for g in geoms:
        ring = [[round(y, 6), round(x, 6)] for x, y in g.exterior.coords]
        rings.append(ring)
        # Holes (very unlikely here, but support them)
        for interior in g.interiors:
            rings.append([[round(y, 6), round(x, 6)] for x, y in interior.coords])
    return rings


def main():
    seeds = load_seeds()
    boundary_geom = shape(json.loads(BOUNDARY.read_text())["features"][0]["geometry"])
    print(f"Loaded boundary ({boundary_geom.geom_type}, area={boundary_geom.area:.4f} sq-deg)")

    to_albers = Transformer.from_crs(WGS84, ALBERS, always_xy=True).transform
    to_wgs = Transformer.from_crs(ALBERS, WGS84, always_xy=True).transform

    boundary_albers = transform(to_albers, boundary_geom)
    # seed_albers entries: (label, swns, ma_full, x_albers, y_albers)
    seed_albers = [(label, swns, ma, *to_albers(lon, lat))
                   for label, swns, ma, lon, lat in seeds]

    # Sanity check: every seed must fall inside the boundary
    outside = [s for s in seed_albers if not boundary_albers.covers(Point(s[3], s[4]))]
    if outside:
        print(f"WARN: {len(outside)} seed(s) outside the Vina boundary; will still be Voronoi'd:")
        for s in outside:
            print(f"  {s[0]} ({s[2]})")

    cells_albers = make_polygons(boundary_albers, seed_albers)
    print(f"Built {len(cells_albers)} clipped Voronoi cells from {len(seeds)} unique sites")

    cells_wgs = [transform(to_wgs, c) for c in cells_albers]

    features = []
    polygons_js = []
    for (label, swns, ma_full, lon, lat), cell_albers, cell_wgs in zip(seeds, cells_albers, cells_wgs):
        area_acres = cell_albers.area / 4046.8564224
        is_aggregate = len(swns) > 1
        rms_label = (
            f"{label}  ·  nested site ×{len(swns)}" if is_aggregate else None
        )
        props = {
            "zone_label": label,           # SWN of one representative completion
            "rms_well_swn": label,
            "rms_well_swns": swns if is_aggregate else None,
            "rms_label": rms_label,
            "is_aggregate": is_aggregate,
            "mgmt_area_full": ma_full,
            "mgmt_area": MA_SHORT.get(ma_full, "Other"),
            "seed_lat": round(lat, 6),
            "seed_lon": round(lon, 6),
            "area_acres": round(area_acres, 1),
        }
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(cell_wgs),
        })
        polygons_js.append({**props, "rings": geom_to_rings_latlng(cell_wgs)})

    fc = {"type": "FeatureCollection", "features": features}
    GEOJSON_OUT.write_text(json.dumps(fc, indent=2))
    print(f"Wrote {GEOJSON_OUT}")

    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "// Auto-generated by scripts/build_polygons_single.py - do not edit by hand.\n"
        "// One Thiessen polygon per unique RMS site (post-2026-05-19 network:\n"
        "// 27 sites). The basin-wide Voronoi diagram is clipped to the Vina\n"
        "// Subbasin (DWR B118 5-021.57). Sites with nested completions (the\n"
        "// CWSCH 7-nest and the 22N01E28J 3-nest in Chico) emit one cell\n"
        "// each, with rms_well_swns + is_aggregate carrying the completion\n"
        "// list. Companion to js/polygons-data-three-zone.js. main.js picks\n"
        "// one based on the §5.2 'Polygon method' toggle.\n"
        "// rings are arrays of [lat, lng] pairs (Leaflet convention).\n\n"
        "const RMS_POLYGONS_SINGLE = " + json.dumps(polygons_js) + ";\n"
    )
    print(f"Wrote {JS_OUT}")

    print("\nPolygon summary (mgmt area / site / acres):")
    for f in features:
        p = f["properties"]
        tag = f"  <-nested ×{len(p['rms_well_swns'])}" if p.get("is_aggregate") else ""
        print(f"  {p['mgmt_area_full']:15} {p['zone_label']:24} {p['area_acres']:>10.1f} ac{tag}")


if __name__ == "__main__":
    main()
