"""Build Thiessen (Voronoi) polygons for the 2027 RMS network.

THREE-ZONE METHOD (supersedes the single-tessellation version on `main`).

Pipeline:
    1. Load the 28 2027-RMS seed wells (data/wells_resolved.json).
    2. Load the three Vina management-area polygons
       (raw/vina_management_areas.geojson: 01-Vina-North / 02-Vina-Chico /
       03-Vina-South).
    3. Project boundaries + seed coords to California Albers (EPSG:3310) so
       the tessellation and area math run in equal-area metric space
       (DWR / B118 standard for area-weighted GW work).
    4. Assign each seed well to a management area by *spatial containment*
       in the projected polygons (geometric truth — NOT the workbook
       mgmt-area attribute). This is an explicit, on-the-record boundary
       call for subsidence SMC defensibility.
    5. For EACH management area independently:
         - build a Voronoi diagram from only that area's seed wells,
         - clip every cell to that area's polygon.
       The three tessellations are stitched into one output. Cells do NOT
       cross management-area lines — hard seams at the boundaries, because
       each area carries distinct sustainable management criteria.
    6. Re-project clipped cells to WGS-84 (EPSG:4326) and emit:
         - data/vina_2027_thiessen_three_zone.geojson  (FeatureCollection)
         - js/polygons-data-three-zone.js
             (`const RMS_POLYGONS_THREE_ZONE = [...]`, rings in [lat,lng]
             order to match the Leaflet UI in main.js)

THREE-ZONE METHOD — companion to `build_polygons_single.py`, which keeps
the single-basin tessellation. The dashboard loads both and lets the
viewer toggle between them in §5.2.

Decisions baked in (differences from the single-tessellation version):
    - Seed set is unchanged: exactly the 28 wells flagged
      `is_2027_gwl_rms` in `BC Network 2026 v8.xlsx`. No supplemental
      wells. Output is still exactly 28 cells, distributed across the
      three areas (12 North / 3 Chico / 13 South for the v8 workbook).
    - Zone membership is now spatial, so a seed whose workbook
      mgmt-area disagrees with where it physically sits is assigned to
      the area it falls in. The original workbook tag is preserved on
      every feature as `workbook_mgmt_area`, with a `reassigned` boolean,
      so the one v8 mismatch (23N01E33A001M: tagged North, sits in Chico)
      is auditable rather than silent.
    - A seed that falls outside ALL three management areas is a hard
      error (it cannot be silently dropped). A seed that lands on a
      shared edge (covered by two areas) is resolved to the area whose
      interior strictly contains it, else the nearest area centroid,
      with a WARN.
    - Output is grouped by management area then seed. The dashboard keys
      polygons by `zone_label`/`rms_well_swn` and joins hydrographs by
      geometric containment (README 5.3), so ordering does not matter to
      the front end. No front-end changes are required by this script.
    - Mgmt-area attribution (`mgmt_area_full` / `mgmt_area`) now reflects
      the SPATIAL zone, so "shade by management area" colors the
      reassigned polygon by where it actually is.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parent.parent
WELLS_JSON = ROOT / "data" / "wells_resolved.json"
MGMT_AREAS = ROOT / "raw" / "vina_management_areas.geojson"
GEOJSON_OUT = ROOT / "data" / "vina_2027_thiessen_three_zone.geojson"
JS_OUT = ROOT / "js" / "polygons-data-three-zone.js"

WGS84 = "EPSG:4326"
ALBERS = "EPSG:3310"  # NAD83 California Albers, equal-area meters

MA_SHORT = {
    "01-Vina-North": "North",
    "02-Vina-Chico": "Chico",
    "03-Vina-South": "South",
}
# Stable output order: North, Chico, South.
MA_ORDER = ["01-Vina-North", "02-Vina-Chico", "03-Vina-South"]


def load_seeds():
    """Return list of dicts for the 28 RMS wells (raw WGS-84 lon/lat)."""
    wells = json.loads(WELLS_JSON.read_text())
    seeds = []
    for w in wells:
        if not w["is_2027_gwl_rms"]:
            continue
        seeds.append({
            "swn": w["swn_or_name"],
            "workbook_ma": w["mgmt_area_full"],
            "lon": float(w["longitude"]),
            "lat": float(w["latitude"]),
        })
    if len(seeds) != 28:
        raise SystemExit(f"Expected 28 RMS wells, got {len(seeds)}")
    return seeds


def load_mgmt_areas(to_albers):
    """Return {mgmt_area_full: shapely polygon in Albers}, ordered."""
    fc = json.loads(MGMT_AREAS.read_text())
    areas = {}
    for feat in fc["features"]:
        ma = feat["properties"]["mgmt_area_full"]
        geom = shape(feat["geometry"])
        areas[ma] = transform(to_albers, geom)
    missing = [m for m in MA_ORDER if m not in areas]
    if missing:
        raise SystemExit(f"Management-area GeoJSON missing: {missing}")
    return {m: areas[m] for m in MA_ORDER}


def assign_zone(pt: Point, areas: dict[str, Polygon]) -> str:
    """Assign a seed point to a management area by spatial containment."""
    covering = [m for m, g in areas.items() if g.covers(pt)]
    if len(covering) == 1:
        return covering[0]
    if not covering:
        raise SystemExit(
            f"Seed at {pt.x:.1f},{pt.y:.1f} (Albers) is outside ALL three "
            f"management areas — cannot assign. Fix the well coords or the "
            f"management-area boundary before rebuilding."
        )
    # On a shared edge: prefer strict interior, else nearest centroid.
    strict = [m for m in covering if areas[m].contains(pt)]
    if len(strict) == 1:
        return strict[0]
    chosen = min(covering, key=lambda m: areas[m].centroid.distance(pt))
    print(f"  WARN: seed on shared edge of {covering}; assigned to {chosen}")
    return chosen


def make_zone_cells(boundary: Polygon | MultiPolygon, seed_xy: list[tuple]):
    """Voronoi cells for one zone's seeds, each clipped to that zone."""
    coords = np.array([[x, y] for x, y in seed_xy])

    # Far anchor points so every real cell is bounded (scipy emits open
    # rays otherwise). Box is sized off THIS zone's bounds.
    minx, miny, maxx, maxy = boundary.bounds
    dx, dy = maxx - minx, maxy - miny
    anchors = np.array([
        [minx - 10 * dx, miny - 10 * dy],
        [maxx + 10 * dx, miny - 10 * dy],
        [minx - 10 * dx, maxy + 10 * dy],
        [maxx + 10 * dx, maxy + 10 * dy],
    ])
    vor = Voronoi(np.vstack([coords, anchors]))

    cells = []
    for site_idx in range(len(coords)):
        region = vor.regions[vor.point_region[site_idx]]
        if -1 in region or not region:
            raise RuntimeError(
                f"Open Voronoi region for seed {site_idx} — anchor box too small"
            )
        cell = Polygon([vor.vertices[i] for i in region])
        clipped = cell.intersection(boundary)
        if clipped.is_empty:
            raise RuntimeError(
                f"Seed {site_idx} clipped to empty — seed sits outside its "
                f"assigned management-area polygon (zone-assignment bug)"
            )
        if clipped.geom_type == "GeometryCollection":
            clipped = MultiPolygon(
                [g for g in clipped.geoms
                 if g.geom_type in ("Polygon", "MultiPolygon")]
            )
        cells.append(clipped)
    return cells


def geom_to_rings_latlng(geom):
    """List of rings (each a list of [lat,lng] pairs) for Leaflet."""
    rings = []
    geoms = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    for g in geoms:
        rings.append([[round(y, 6), round(x, 6)] for x, y in g.exterior.coords])
        for interior in g.interiors:
            rings.append([[round(y, 6), round(x, 6)]
                          for x, y in interior.coords])
    return rings


def main():
    seeds = load_seeds()
    to_albers = Transformer.from_crs(WGS84, ALBERS, always_xy=True).transform
    to_wgs = Transformer.from_crs(ALBERS, WGS84, always_xy=True).transform

    areas = load_mgmt_areas(to_albers)
    print(f"Loaded {len(areas)} management areas: {list(areas)}")

    # Spatially assign every seed to a zone.
    for s in seeds:
        s["xy"] = to_albers(s["lon"], s["lat"])
        s["zone"] = assign_zone(Point(*s["xy"]), areas)
        s["reassigned"] = s["zone"] != s["workbook_ma"]

    by_zone = {m: [s for s in seeds if s["zone"] == m] for m in MA_ORDER}
    print("Seed distribution (spatial):")
    for m in MA_ORDER:
        print(f"  {m}: {len(by_zone[m])}")
    flips = [s for s in seeds if s["reassigned"]]
    print(f"Reassigned vs workbook tag: {len(flips)}")
    for s in flips:
        print(f"  {s['swn']}: workbook {s['workbook_ma']} -> spatial {s['zone']}")

    features, polygons_js = [], []
    total = 0
    for ma in MA_ORDER:
        zone_seeds = by_zone[ma]
        if not zone_seeds:
            print(f"  NOTE: {ma} has no seeds — no cells emitted for it")
            continue
        cells_albers = make_zone_cells(
            areas[ma], [s["xy"] for s in zone_seeds]
        )
        cells_wgs = [transform(to_wgs, c) for c in cells_albers]
        for s, ca, cw in zip(zone_seeds, cells_albers, cells_wgs):
            props = {
                "zone_label": s["swn"],
                "rms_well_swn": s["swn"],
                "mgmt_area_full": ma,
                "mgmt_area": MA_SHORT[ma],
                "workbook_mgmt_area": s["workbook_ma"],
                "reassigned": s["reassigned"],
                "seed_lat": round(s["lat"], 6),
                "seed_lon": round(s["lon"], 6),
                "area_acres": round(ca.area / 4046.8564224, 1),
            }
            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": mapping(cw),
            })
            polygons_js.append({
                "zone_label": s["swn"],
                "rms_well_swn": s["swn"],
                "mgmt_area_full": ma,
                "mgmt_area": MA_SHORT[ma],
                "workbook_mgmt_area": s["workbook_ma"],
                "reassigned": s["reassigned"],
                "area_acres": props["area_acres"],
                "seed_latlng": [round(s["lat"], 6), round(s["lon"], 6)],
                "rings": geom_to_rings_latlng(cw),
            })
            total += 1

    if total != 28:
        raise SystemExit(f"Expected 28 cells total, built {total}")

    GEOJSON_OUT.write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}, indent=2))
    print(f"Wrote {GEOJSON_OUT}")

    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "// Auto-generated by scripts/build_polygons_three_zone.py - do not edit by hand.\n"
        "// 28 Thiessen polygons: three INDEPENDENT Voronoi tessellations,\n"
        "// one per Vina management area (01-Vina-North / 02-Vina-Chico /\n"
        "// 03-Vina-South), each clipped to its own management-area polygon.\n"
        "// Cells do not cross management-area lines. Zone membership is\n"
        "// spatial; `workbook_mgmt_area` + `reassigned` preserve the audit.\n"
        "// Companion to js/polygons-data-single.js — main.js picks one based\n"
        "// on the §5.2 'Polygon method' toggle.\n"
        "// rings are arrays of [lat, lng] pairs (Leaflet convention).\n\n"
        "const RMS_POLYGONS_THREE_ZONE = " + json.dumps(polygons_js) + ";\n"
    )
    print(f"Wrote {JS_OUT}")

    # Coverage check: stitched cells vs union of the three areas.
    stitched = unary_union(
        [shape(f["geometry"]) for f in features]
    )
    stitched_ac = transform(to_albers, stitched).area / 4046.8564224
    areas_ac = unary_union(list(areas.values())).area / 4046.8564224
    print("\nMgmt area / well / acres:")
    for f in features:
        p = f["properties"]
        tag = "  <-reassigned" if p["reassigned"] else ""
        print(f"  {p['mgmt_area_full']:15} {p['rms_well_swn']:24} "
              f"{p['area_acres']:>10.1f} ac{tag}")
    print(f"\nStitched cells: {stitched_ac:,.0f} ac | "
          f"union of 3 areas: {areas_ac:,.0f} ac | "
          f"gap: {areas_ac - stitched_ac:,.1f} ac")


if __name__ == "__main__":
    main()
