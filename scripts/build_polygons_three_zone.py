"""Build polygons for the revised 2027 RMS network (Vina GSP update).

STRUCTURE (2026-05-19 revision; Chico RMS membership updated 2026-05):

    North (Voronoi)
        Voronoi tessellation of the North-network-assigned RMS wells,
        clipped to (Basin - Chico mgmt area - South mgmt area). Some
        seed wells are physically in Chico but are treated as North RMS
        for the 2027 network (rms_mgmt_area override); their cells
        extend into Chico territory naturally via Voronoi proximity.

    Chico (1 dissolved polygon, multiple RMS wells allowed)
        ONE polygon = the Chico mgmt area boundary. No internal Voronoi
        subdivision, regardless of how many RMS wells are assigned to
        the Chico network — adding or removing Chico RMS wells changes
        which traces get threshold lines in §5.3, NOT the polygon count.
        Chico wells live at two physical pads (CWSCH 7-nest:
        CWSCH01b/02/03/04/05/06/07; 22N01E28J 3-nest:
        22N01E28J001M/003M/005M — 10 completions total). Whichever of
        those 10 are flagged is_2027_gwl_rms (via column E of the
        workbook) become RMS primaries with threshold lines; the rest
        plot as supplemental traces for context. RMS membership is read
        dynamically from wells_resolved.json on every run — there is no
        hardcoded list of which Chico wells are RMS.

    South (Voronoi)
        Voronoi tessellation of the South-network-assigned RMS wells,
        clipped to the South mgmt area.

Total polygon count = (N Voronoi cells) + 1 (Chico aggregate) + (S Voronoi
cells), regardless of how many wells are RMS within Chico.

Array order in the output JS: [Chico, ...North, ...South]. This puts the
big Chico polygon FIRST so the dashboard's Leaflet renderer draws it at
the back; reassigned-from-Chico North cells overlay on top in Chico
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
BASIN_GEOJSON = ROOT / "raw" / "vina_subbasin.geojson"
GEOJSON_OUT = ROOT / "data" / "vina_2027_thiessen_three_zone.geojson"
JS_OUT = ROOT / "js" / "polygons-data-three-zone.js"

WGS84 = "EPSG:4326"
ALBERS = "EPSG:3310"  # NAD83 California Albers, equal-area meters

MA_SHORT = {
    "01-Vina-North": "North",
    "02-Vina-Chico": "Chico",
    "03-Vina-South": "South",
}

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


def load_basin(to_albers):
    """Return Vina Subbasin (DWR B118 5-021.57) polygon in Albers."""
    fc = json.loads(BASIN_GEOJSON.read_text())
    feat = fc["features"][0] if fc.get("type") == "FeatureCollection" else fc
    geom = shape(feat["geometry"])
    return transform(to_albers, geom)


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
    basin = load_basin(to_albers)
    print(f"Loaded {len(areas)} management areas: {sorted(areas)}")
    print(f"Basin: {basin.area/4046.8564224:,.0f} ac")

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
    # Chico RMS membership is read dynamically (chico_rms_swns below) from
    # whichever wells the workbook flags is_2027_gwl_rms with
    # rms_mgmt_area == "02-Vina-Chico" — no hardcoded primary list. Wells
    # at the same physical pad as a Chico RMS well that are NOT themselves
    # RMS are supplemental — they plot in the §5.3 hydrograph for context
    # but don't carry threshold lines. Identify those supplementals by
    # collapsing all Chico wells to (lat, lng) sites and picking up every
    # well that shares a site with a historical 2022 GSP RMS well.
    all_wells_raw = json.loads(WELLS_JSON.read_text())
    chico_rms_swns = sorted(s["swn"] for s in by_net.get("02-Vina-Chico", []))
    # Map lat/lng → wells at that location (Chico mgmt area only)
    by_site = {}
    for w in all_wells_raw:
        if w["mgmt_area_full"] != "02-Vina-Chico":
            continue
        if w["latitude"] is None or w["longitude"] is None:
            continue
        key = (round(float(w["latitude"]), 5), round(float(w["longitude"]), 5))
        by_site.setdefault(key, []).append(w["swn_or_name"])
    # Find sites that host any HISTORICAL 2022 GSP RMS well (not current
    # 2027 RMS). This pulls in the 22N01E28J 3-nest as Chico context
    # even though only 22N01E28J003M (now supplemental) was 2022 RMS.
    chico_2022_swns = {
        w["swn_or_name"] for w in all_wells_raw
        if w["mgmt_area_full"] == "02-Vina-Chico" and w["is_2022_gwl_rms"]
    }
    historical_rms_sites = {
        key for key, swns in by_site.items()
        if any(swn in chico_2022_swns for swn in swns)
    }
    chico_all_context_swns = sorted({
        swn for key in historical_rms_sites for swn in by_site[key]
    })
    chico_supps = [s for s in chico_all_context_swns if s not in chico_rms_swns]
    chico_boundary_albers = areas["02-Vina-Chico"]
    chico_boundary_wgs = transform(to_wgs, chico_boundary_albers)
    print(f"\nChico aggregate: {len(chico_rms_swns)} RMS ({chico_rms_swns}) + "
          f"{len(chico_supps)} supplemental nested completions ({chico_supps})")

    # rms_label drives the §5.3 picker option text and polygon-header title.
    # Lists the RMS primaries by name (so reviewers can see at a glance which
    # wells carry threshold lines) plus a supplemental count.
    if chico_rms_swns:
        rms_part = f"{', '.join(chico_rms_swns)} (RMS)"
    else:
        rms_part = "no 2027 RMS wells"
    supp_part = f" + {len(chico_supps)} supplemental" if chico_supps else ""
    chico_props = {
        "zone_label": "02-Vina-Chico",
        "rms_well_swn": None,
        # rms_well_swns includes ALL context wells (RMS + supplemental) so
        # the dashboard's polygonWells() helper finds them all for the §5.3
        # hydrograph. Only the wells listed in rms_primary_swns are
        # is_2027_gwl_rms and carry threshold lines.
        "rms_well_swns": chico_all_context_swns,
        "rms_primary_swns": list(chico_rms_swns),
        "rms_supplemental_swns": chico_supps,
        "rms_label": f"Chico  ·  {rms_part}{supp_part}",
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

    # ---------------- NORTH: 13 VORONOI CELLS, CLIPPED OUT OF CHICO ---
    # Per 2026-05-20 user direction:
    #   - All 13 North RMS wells get their own Thiessen cells (one per
    #     picker entry). Voronoi midlines come from 13 N seeds + 2 phantom
    #     Chico nested-site seeds so the 3 Chico-located N wells'
    #     theoretical cells are bounded from the south.
    #   - Every cell is clipped to (Basin - Chico mgmt area - South mgmt
    #     area). No North cell overlaps with Chico territory.
    #   - The 3 Chico-located N wells (22N01E09B001M, 22N01E20K001M,
    #     23N01E33A001M) have their *well location* inside Chico, but their
    #     clipped cell is a sliver in N (whatever's outside Chico that's
    #     closer to that well than to any other N seed). One or more of
    #     these may end up empty if the well's entire Voronoi region is
    #     inside Chico — emit a degenerate "marker only" entry in that
    #     case (rings is an empty list) so the §5.3 picker still works.
    #   - Slivers along the north Chico boundary (basin areas outside Chico
    #     but not initially covered by any cell at the Voronoi step) get
    #     absorbed into the adjacent N cell naturally — clipping to
    #     (Basin - Chico - South) ensures the 13 cells tile every basin
    #     point that isn't in Chico or South.
    north_seeds = by_net.get("01-Vina-North", [])
    print(f"  North: {len(north_seeds)} seeds (including "
          f"{sum(1 for s in north_seeds if s['reassigned'])} workbook-reassigned)")

    # Voronoi over north_domain = (Basin - Chico - South) directly. Every
    # point in that domain is assigned to its nearest N seed, so the 13
    # cells tile north_domain exactly — no orphan slivers along the
    # Chico mgmt-area boundary, no leftover area between mgmt-area
    # polygons. The 3 Chico-located N wells have their positions outside
    # the clip domain, but their Voronoi regions naturally extend into
    # north_domain (the parts of N closer to them than to any other N
    # seed); scipy handles seeds-outside-clip correctly.
    north_domain = basin.difference(areas["02-Vina-Chico"]).difference(areas["03-Vina-South"])
    north_cells_clipped_list = voronoi_cells(
        north_domain, [s["xy"] for s in north_seeds]
    )
    north_cells_clipped = list(zip(north_seeds, north_cells_clipped_list))

    for s, cell_alb in north_cells_clipped:
        in_chico = s["workbook_ma"] == "02-Vina-Chico" or s["reassigned"]
        if cell_alb.is_empty:
            rings = []
            cell_wgs = None
            area_ac = 0.0
        else:
            cell_wgs = transform(to_wgs, cell_alb)
            rings = geom_to_rings_latlng(cell_wgs)
            area_ac = acres(cell_alb)
        props = {
            "zone_label": s["swn"],
            "rms_well_swn": s["swn"],
            "mgmt_area_full": "01-Vina-North",
            "mgmt_area": "North",
            "workbook_mgmt_area": s["workbook_ma"],
            "reassigned": s["reassigned"],
            "well_in_chico_mgmt_area": bool(areas["02-Vina-Chico"].covers(Point(*s["xy"]))),
            "is_aggregate": False,
            "is_marker_only": cell_alb.is_empty,
            "seed_lat": round(s["lat"], 6),
            "seed_lon": round(s["lon"], 6),
            "area_acres": area_ac,
        }
        polygons_js.append({**props, "rings": rings})
        if cell_wgs is not None:
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

    n_reassigned = sum(1 for s in north_seeds if s["reassigned"])
    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "// Auto-generated by scripts/build_polygons_three_zone.py - do not edit by hand.\n"
        f"//   - 1 Chico aggregate polygon (dissolved mgmt area, "
        f"{len(chico_rms_swns)} RMS well{'s' if len(chico_rms_swns) != 1 else ''} + "
        f"{len(chico_supps)} supplemental completions)\n"
        f"//   - {len(north_seeds)} North Voronoi cells "
        f"(incl. {n_reassigned} reassigned from Chico)\n"
        f"//   - {len(south_seeds)} South Voronoi cells\n"
        "// Array order is [Chico, ...North, ...South] so the dashboard draws\n"
        "// Chico at the back and the reassigned-North cells overlay it in\n"
        "// Chico territory.\n"
        "// rings are arrays of [lat, lng] pairs (Leaflet convention).\n\n"
        "const RMS_POLYGONS_THREE_ZONE = " + json.dumps(polygons_js) + ";\n"
    )
    print(f"Wrote {JS_OUT}")

    # Coverage report
    print("\n=== Coverage report ===")
    n_features = [f for f in features
                  if f["properties"]["mgmt_area_full"] == "01-Vina-North"
                  and not f["properties"].get("is_aggregate")]
    n_all = unary_union([shape(f["geometry"]) for f in n_features])
    n_in_chico = n_all.intersection(chico_boundary_wgs)
    print(f"  Chico mgmt area:                {chico_props['area_acres']:>10.1f} ac")
    print(f"  ... overlapped by any N cell:  {acres(transform(to_albers, n_in_chico)):>10.1f} ac (must be 0)")
    print(f"\n  Per-cell areas:")
    for p in polygons_js:
        if p.get("is_aggregate"): continue
        tag = ""
        if p.get("is_marker_only"):
            tag = "  <-marker-only (well in Chico, no N-side region)"
        elif p.get("well_in_chico_mgmt_area"):
            tag = "  <-well in Chico mgmt area"
        print(f"  {p['mgmt_area_full']:15} {p['rms_well_swn']:24} "
              f"{p['area_acres']:>10.1f} ac{tag}")


if __name__ == "__main__":
    main()
