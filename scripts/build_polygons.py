"""Build Thiessen (Voronoi) polygons for the 2027 RMS network.

Pipeline:
    1. Load Vina Subbasin boundary (raw/vina_subbasin.geojson).
    2. Project boundary + 28 RMS-well coords to California Albers (EPSG:3310)
       so the Voronoi tessellation is computed in equal-area metric space
       (DWR / B118 standard for area-weighted GW work).
    3. Build a Voronoi diagram around the 28 RMS sites.
    4. Clip each Voronoi cell to the Vina Subbasin polygon.
    5. Verify that exactly one cell maps to each RMS well (28 polygons).
    6. Re-project the clipped cells back to WGS-84 (EPSG:4326).
    7. Emit:
         - data/vina_2027_thiessen.geojson  (FeatureCollection)
         - js/polygons-data.js              (`const RMS_POLYGONS = [...]`,
                                             rings in [lat,lng] order to match
                                             the Leaflet UI in main.js)

Notes / decisions baked in:
    - The Voronoi seed set is the 28 wells flagged `2027 GWL RMS? = Yes` in
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
GEOJSON_OUT = ROOT / "data" / "vina_2027_thiessen.geojson"
JS_OUT = ROOT / "js" / "polygons-data.js"

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
    """Return list of (well_name, mgmt_area_full, lon, lat) for 28 RMS wells."""
    wells = json.loads(WELLS_JSON.read_text())
    seeds = []
    for w in wells:
        if not w["is_2027_gwl_rms"]:
            continue
        seeds.append((
            w["swn_or_name"],
            w["mgmt_area_full"],
            float(w["longitude"]),
            float(w["latitude"]),
        ))
    if len(seeds) != 28:
        raise SystemExit(f"Expected 28 RMS wells, got {len(seeds)}")
    return seeds


def make_polygons(boundary_albers: Polygon | MultiPolygon, seed_albers: list[tuple]):
    """Build Voronoi polygons clipped to the boundary, one per seed."""
    coords = np.array([[x, y] for _, _, x, y in seed_albers])

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
    seed_albers = [(name, ma, *to_albers(lon, lat)) for name, ma, lon, lat in seeds]

    # Sanity check: every seed must fall inside the boundary
    outside = [s for s in seed_albers if not boundary_albers.covers(Point(s[2], s[3]))]
    if outside:
        print(f"WARN: {len(outside)} seed(s) outside the Vina boundary; will still be Voronoi'd:")
        for s in outside:
            print(f"  {s[0]} ({s[1]})")

    cells_albers = make_polygons(boundary_albers, seed_albers)
    print(f"Built {len(cells_albers)} clipped Voronoi cells")

    cells_wgs = [transform(to_wgs, c) for c in cells_albers]

    features = []
    polygons_js = []
    for (name, ma_full, lon, lat), cell_albers, cell_wgs in zip(seeds, cells_albers, cells_wgs):
        area_acres = cell_albers.area / 4046.8564224
        props = {
            "zone_label": name,           # SWN of the seed RMS well
            "rms_well_swn": name,
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
        polygons_js.append({
            "zone_label": name,
            "rms_well_swn": name,
            "mgmt_area_full": ma_full,
            "mgmt_area": props["mgmt_area"],
            "area_acres": props["area_acres"],
            "seed_latlng": [round(lat, 6), round(lon, 6)],
            "rings": geom_to_rings_latlng(cell_wgs),
        })

    fc = {"type": "FeatureCollection", "features": features}
    GEOJSON_OUT.write_text(json.dumps(fc, indent=2))
    print(f"Wrote {GEOJSON_OUT}")

    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "// Auto-generated by scripts/build_polygons.py - do not edit by hand.\n"
        "// 28 Thiessen polygons (Voronoi cells of the 28 2027 RMS wells)\n"
        "// clipped to the Vina Subbasin (DWR B118 5-021.57).\n"
        "// rings are arrays of [lat, lng] pairs (Leaflet convention).\n\n"
        "const RMS_POLYGONS = " + json.dumps(polygons_js) + ";\n"
    )
    print(f"Wrote {JS_OUT}")

    print("\nPolygon summary (mgmt area / well / acres):")
    for f in features:
        p = f["properties"]
        print(f"  {p['mgmt_area_full']:15} {p['rms_well_swn']:24} {p['area_acres']:>10.1f} ac")


if __name__ == "__main__":
    main()
