"""Build polygons for the revised 2027 RMS network (Vina GSP update).

NEW STRUCTURE (2026-05-19 revision — replaces prior three-zone tessellation):

    North (13 wells)
        Voronoi tessellation of the 13 North-assigned RMS wells, clipped
        to (North mgmt area ∪ Chico mgmt area). Two of the 13 seed wells
        (22N01E09B001M, 22N01E20K001M) are physically in Chico but are
        treated as North RMS for the 2027 network. Their cells extend
        into Chico territory naturally via Voronoi proximity. The 11
        originally-North wells primarily fill North; the 2 reassigned
        wells' cells sit inside Chico territory.

    Chico (1 polygon, 2 nested RMS sites, 10 well completions)
        ONE dissolved polygon = the Chico mgmt area boundary. No Voronoi.
        Associated with two 2022-GSP nested sites:
          - CWSCH 7-nest: CWSCH01b/02/03/04/05/06/07
          - 22N01E28J 3-nest: 22N01E28J001M/003M/005M
        Of those 10, 5 primaries (CWSCH01b/02/03/07, 22N01E28J003M)
        have 2022 GSP thresholds; the other 5 are monitored but unthresholded
        (same as in the 2022 GSP).

    South (12 wells)
        Voronoi tessellation of the 12 South-assigned RMS wells, clipped
        to the South mgmt area.

Total output: 13 + 1 + 12 = 26 polygon entries; 35 RMS well completions.

Array order in the output JS: [Chico, ...North, ...South]. This puts the
big Chico polygon FIRST so the dashboard's Leaflet renderer draws it at
the back; the 2 reassigned wells' Voronoi cells overlay on top in Chico
territory (the user-requested visual stacking).

Membership comes from `rms_mgmt_area` in wells_resolved.json (network-
design assignment), NOT spatial containment. `mgmt_area_full` is the
geographic truth and is preserved as `workbook_mgmt_area` + `reassigned`
on every feature for the audit trail.
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

# Chico nested-site primaries that carry 2022 GSP thresholds (visible
# in §5.3 hydrograph as dashed lines). The other 5 completions in those
# nests are monitored but unthresholded (same convention as 2022 GSP).
CHICO_PRIMARIES = {"CWSCH01b", "CWSCH02", "CWSCH03", "CWSCH07", "22N01E28J003M"}


def load_seeds():
    """Return list of dicts for every RMS well (post-2026-05-19 revision)."""
    wells = json.loads(WELLS_JSON.read_text())
    seeds = []
    for w in wells:
        if not w["is_2027_gwl_rms"]:
            continue
        seeds.append({
            "swn": w["swn_or_name"],
            "workbook_ma": w["mgmt_area_full"],         # geographic truth
            "rms_ma": w.get("rms_mgmt_area", w["mgmt_area_full"]),  # network
            "lon": float(w["longitude"]),
            "lat": float(w["latitude"]),
        })
    return seeds


def load_mgmt_areas(to_albers):
    """Return {mgmt_area_full: shapely polygon in Albers}."""
    fc = json.loads(MGMT_AREAS.read_text())
    areas = {}
    for feat in fc["features"]:
        ma = feat["properties"]["mgmt_area_full"]
        geom = shape(feat["geometry"])
        areas[ma] = transform(to_albers, geom)
    return areas


def voronoi_cells(boundary, seed_xy):
    """Voronoi cells for seeds, each clipped to `boundary` (Albers)."""
    coords = np.array([[x, y] for x, y in seed_xy])
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
                f"Seed {site_idx} clipped to empty — seed sits outside "
                f"the Voronoi domain"
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


def acres(geom_albers):
    return round(geom_albers.area / 4046.8564224, 1)


def main():
    seeds = load_seeds()
    print(f"Loaded {len(seeds)} RMS-flagged well completions")

    to_albers = Transformer.from_crs(WGS84, ALBERS, always_xy=True).transform
    to_wgs = Transformer.from_crs(ALBERS, WGS84, always_xy=True).transform
    areas = load_mgmt_areas(to_albers)
    print(f"Loaded {len(areas)} management areas: {sorted(areas)}")

    # Group seeds by network assignment (rms_mgmt_area)
    by_net = {}
    for s in seeds:
        s["xy"] = to_albers(s["lon"], s["lat"])
        s["reassigned"] = s["rms_ma"] != s["workbook_ma"]
        by_net.setdefault(s["rms_ma"], []).append(s)

    print("\nNetwork-design distribution:")
    for ma in sorted(by_net):
        n = len(by_net[ma])
        reassigned = sum(1 for s in by_net[ma] if s["reassigned"])
        print(f"  {ma}: {n} ({reassigned} reassigned)")

    polygons_js = []
    features = []

    # ---------------- CHICO: ONE DISSOLVED POLYGON ------------------
    # Drawn FIRST so it sits at the back of the SVG; the 2 North cells
    # that extend into Chico territory overlay on top.
    chico_seeds = by_net.get("02-Vina-Chico", [])
    chico_swns = sorted(s["swn"] for s in chico_seeds)
    chico_primaries_present = [s for s in chico_swns if s in CHICO_PRIMARIES]
    chico_supps = [s for s in chico_swns if s not in CHICO_PRIMARIES]
    chico_boundary_albers = areas["02-Vina-Chico"]
    chico_boundary_wgs = transform(to_wgs, chico_boundary_albers)

    chico_props = {
        "zone_label": "02-Vina-Chico",
        "rms_well_swn": None,
        "rms_well_swns": chico_swns,
        "rms_primary_swns": chico_primaries_present,
        "rms_supplemental_swns": chico_supps,
        "rms_label": f"Chico  ·  {len(chico_swns)} completions across 2 nested sites",
        "mgmt_area_full": "02-Vina-Chico",
        "mgmt_area": "Chico",
        "is_aggregate": True,
        "area_acres": acres(chico_boundary_albers),
    }
    polygons_js.append({**chico_props, "rings": geom_to_rings_latlng(chico_boundary_wgs)})
    features.append({
        "type": "Feature",
        "properties": chico_props,
        "geometry": mapping(chico_boundary_wgs),
    })

    # ---------------- NORTH: 13 VORONOI CELLS ------------------------
    # Domain = North ∪ Chico so the 2 reassigned wells' cells can extend
    # into Chico territory. The 2 Chico nested-site coordinates are added
    # as PHANTOM Voronoi seeds to bound the 2 reassigned wells' cells from
    # the south (otherwise they would sweep most of Chico). Cells for those
    # phantom seeds are computed but discarded — Chico's territory is
    # represented by the aggregate polygon emitted above.
    north_seeds = by_net.get("01-Vina-North", [])
    north_domain = unary_union([areas["01-Vina-North"], areas["02-Vina-Chico"]])

    # Phantom seeds: collapse the 10 Chico nested-site completions to their
    # distinct lat/lng (typically 2 sites, but compute defensively).
    chico_sites = {}
    for s in chico_seeds:
        key = (round(s["lat"], 5), round(s["lon"], 5))
        chico_sites[key] = s["xy"]
    phantom_xy = list(chico_sites.values())
    print(f"  Phantom seeds for North Voronoi: {len(phantom_xy)} Chico-site coords")

    combined_xy = [s["xy"] for s in north_seeds] + phantom_xy
    combined_cells = voronoi_cells(north_domain, combined_xy)
    # Keep only the first len(north_seeds) cells; the rest are phantoms.
    north_cells_albers = combined_cells[: len(north_seeds)]

    for s, cell_alb in zip(north_seeds, north_cells_albers):
        cell_wgs = transform(to_wgs, cell_alb)
        props = {
            "zone_label": s["swn"],
            "rms_well_swn": s["swn"],
            "mgmt_area_full": "01-Vina-North",
            "mgmt_area": "North",
            "workbook_mgmt_area": s["workbook_ma"],
            "reassigned": s["reassigned"],
            "is_aggregate": False,
            "seed_lat": round(s["lat"], 6),
            "seed_lon": round(s["lon"], 6),
            "area_acres": acres(cell_alb),
        }
        polygons_js.append({**props, "rings": geom_to_rings_latlng(cell_wgs)})
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(cell_wgs),
        })

    # ---------------- SOUTH: 12 VORONOI CELLS ------------------------
    south_seeds = by_net.get("03-Vina-South", [])
    south_cells_albers = voronoi_cells(
        areas["03-Vina-South"], [s["xy"] for s in south_seeds]
    )
    for s, cell_alb in zip(south_seeds, south_cells_albers):
        cell_wgs = transform(to_wgs, cell_alb)
        props = {
            "zone_label": s["swn"],
            "rms_well_swn": s["swn"],
            "mgmt_area_full": "03-Vina-South",
            "mgmt_area": "South",
            "workbook_mgmt_area": s["workbook_ma"],
            "reassigned": s["reassigned"],
            "is_aggregate": False,
            "seed_lat": round(s["lat"], 6),
            "seed_lon": round(s["lon"], 6),
            "area_acres": acres(cell_alb),
        }
        polygons_js.append({**props, "rings": geom_to_rings_latlng(cell_wgs)})
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": mapping(cell_wgs),
        })

    # ---------------- WRITE OUT ------------------------
    GEOJSON_OUT.write_text(json.dumps(
        {"type": "FeatureCollection", "features": features}, indent=2))
    print(f"\nWrote {GEOJSON_OUT}")

    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "// Auto-generated by scripts/build_polygons_three_zone.py - do not edit by hand.\n"
        "// 2026-05-19 network revision:\n"
        "//   - 1 Chico aggregate polygon (dissolved mgmt area, 10 well completions)\n"
        "//   - 13 North Voronoi cells (incl. 2 reassigned from Chico)\n"
        "//   - 12 South Voronoi cells\n"
        "// Array order is [Chico, ...North, ...South] so the dashboard draws\n"
        "// Chico at the back and the 2 reassigned-North cells overlay it in\n"
        "// Chico territory.\n"
        "// rings are arrays of [lat, lng] pairs (Leaflet convention).\n\n"
        "const RMS_POLYGONS_THREE_ZONE = " + json.dumps(polygons_js) + ";\n"
    )
    print(f"Wrote {JS_OUT}")

    # Coverage report
    print("\n=== Coverage report ===")
    chico_overlap = unary_union(
        [shape(f["geometry"]) for f in features
         if f["properties"]["mgmt_area_full"] == "01-Vina-North"
         and not f["properties"].get("is_aggregate")]
    ).intersection(chico_boundary_wgs)
    chico_overlap_ac = acres(transform(to_albers, chico_overlap))
    print(f"  Chico mgmt area:        {chico_props['area_acres']:>10.1f} ac")
    print(f"  ... overlapped by N cells: {chico_overlap_ac:>10.1f} ac (the 2 reassigned wells)")
    for f in features:
        p = f["properties"]
        if p.get("is_aggregate"): continue
        tag = "  <-reassigned" if p["reassigned"] else ""
        print(f"  {p['mgmt_area_full']:15} {p['rms_well_swn']:24} "
              f"{p['area_acres']:>10.1f} ac{tag}")


if __name__ == "__main__":
    main()
