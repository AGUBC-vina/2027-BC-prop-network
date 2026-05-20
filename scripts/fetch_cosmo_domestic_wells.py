"""Pull domestic-well data from the cosmo MT-sensitivity dashboard and
spatial-join each well to our 2027 three-zone polygons.

Source: https://cosmo1007.github.io/2022-RMS-Well-MT-Sensitivity/js/wells-data.js
The cosmo bundle is a JS file that wraps a JSON array as
    `const WELLS = [ ... ];`

Each input record has many fields; we keep only the geometry, elevation, and
basic identification we need for the §5.3 sensitivity feature:

    wid, lat, lon, install_date, well_depth, local_gse, well_bottom_amsl,
    include (cosmo's keep-or-drop flag, =0 for malformed records)

We add:
    our_polygon       — zone_label of the 2027 three-zone polygon containing
                        this well (point-in-polygon against our 26 polygons),
                        or None if outside all of them.
    our_mgmt_area     — short name of the polygon (North / Chico / South)

Outputs:
    raw/cosmo_domestic_wells.js              — verbatim fetched bundle
    data/domestic_wells.json                  — pruned + spatial-joined
    js/domestic-wells-data.js                 — dashboard bundle:
                                                `const DOMESTIC_WELLS = [...]`

3,212 wells in the cosmo bundle; expect most to map to one of our 26
polygons. Wells outside (basin-boundary mismatch, foothill outliers) are
emitted with our_polygon=null so the dashboard can choose whether to
render them.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from shapely.geometry import Point, Polygon, MultiPolygon, shape

ROOT = Path(__file__).resolve().parent.parent
COSMO_URL = "https://cosmo1007.github.io/2022-RMS-Well-MT-Sensitivity/js/wells-data.js"
RAW_OUT = ROOT / "raw" / "cosmo_domestic_wells.js"
POLYGONS_GEOJSON = ROOT / "data" / "vina_2027_thiessen_three_zone.geojson"
JSON_OUT = ROOT / "data" / "domestic_wells.json"
JS_OUT = ROOT / "js" / "domestic-wells-data.js"

# Fields to keep from the cosmo well record
KEEP_FIELDS = [
    "wid", "lat", "lon", "install_date",
    "well_depth", "local_gse", "well_bottom_amsl",
    "perf_top_amsl", "perf_bot_amsl",
    "include", "accuracy",
]


def fetch_cosmo() -> str:
    if RAW_OUT.exists():
        print(f"Reusing cached {RAW_OUT} ({RAW_OUT.stat().st_size:,} bytes)")
        return RAW_OUT.read_text()
    print(f"Fetching {COSMO_URL}")
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(COSMO_URL, timeout=30) as r:
        data = r.read().decode("utf-8")
    RAW_OUT.write_text(data)
    print(f"  wrote {RAW_OUT} ({len(data):,} bytes)")
    return data


def parse_wells(js_text: str) -> list[dict]:
    """Strip the `const WELLS = ` prefix and trailing `;`, parse as JSON."""
    m = re.search(r"const\s+WELLS\s*=\s*(\[.*\])\s*;?\s*$", js_text, re.S)
    if not m:
        raise SystemExit("Could not find `const WELLS = [...]` in cosmo bundle")
    return json.loads(m.group(1))


def load_polygons() -> list[tuple[str, str, Polygon | MultiPolygon]]:
    """Return [(zone_label, mgmt_area_short, polygon)] for our 26 polygons.

    Some clipped polygons may have minor topology issues at edge cases
    (slivers, near-zero-area dangles); buffer(0) is the standard shapely
    trick to clean these without changing geometry meaningfully.
    """
    fc = json.loads(POLYGONS_GEOJSON.read_text())
    out = []
    for feat in fc["features"]:
        props = feat["properties"]
        geom = shape(feat["geometry"])
        if not geom.is_valid:
            geom = geom.buffer(0)
        out.append((props["zone_label"], props["mgmt_area"], geom))
    return out


def main() -> None:
    js_text = fetch_cosmo()
    wells_in = parse_wells(js_text)
    print(f"Parsed {len(wells_in):,} wells from cosmo bundle")

    polys = load_polygons()
    print(f"Loaded {len(polys)} three-zone polygons for spatial join")

    out = []
    by_polygon: dict[str | None, int] = {}
    n_dropped_geom = 0
    for w in wells_in:
        if w.get("lat") is None or w.get("lon") is None:
            n_dropped_geom += 1
            continue
        pt = Point(w["lon"], w["lat"])
        match_label: str | None = None
        match_ma: str | None = None
        for zone_label, mgmt_area_short, poly in polys:
            if poly.covers(pt):
                match_label = zone_label
                match_ma = mgmt_area_short
                break
        rec = {k: w.get(k) for k in KEEP_FIELDS}
        rec["our_polygon"] = match_label
        rec["our_mgmt_area"] = match_ma
        out.append(rec)
        by_polygon[match_label] = by_polygon.get(match_label, 0) + 1

    print(f"\n  kept {len(out):,} wells (dropped {n_dropped_geom} with no lat/lon)")
    print(f"  outside all 26 polygons: {by_polygon.get(None, 0)}")
    print(f"  with include=0:          {sum(1 for r in out if r.get('include') == 0)}")

    # Per-polygon count (sorted by count desc)
    print("\n  by polygon (top 10):")
    items = sorted(((k, v) for k, v in by_polygon.items() if k), key=lambda x: -x[1])
    for k, v in items[:10]:
        print(f"    {k:<24} {v:>5}")

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {JSON_OUT}")

    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "// Auto-generated by scripts/fetch_cosmo_domestic_wells.py - do not edit by hand.\n"
        f"// Source: {COSMO_URL}\n"
        "// Pruned to dashboard-relevant fields + spatial-joined against our\n"
        "// 2027 three-zone polygons (each well's `our_polygon` field is the\n"
        "// zone_label of the containing 2027 polygon, or null if outside the\n"
        "// 26-polygon coverage). `our_mgmt_area` is the short name (North /\n"
        "// Chico / South) for color/legend purposes.\n\n"
        "const DOMESTIC_WELLS = " + json.dumps(out) + ";\n"
    )
    print(f"Wrote {JS_OUT} ({JS_OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
