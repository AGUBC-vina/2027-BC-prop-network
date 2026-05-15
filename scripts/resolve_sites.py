"""Resolve DWR site_code for every well in BC Network 2026 v8.xlsx.

Uses the DWR CKAN Stations resource (periodic gwl Stations CSV) as the authoritative
station list. Joins on State Well Number (SWN). For wells without an SWN (e.g.
CWSCH01b, TNC-MW-1, FC-MW-2) we fall back to `well_name`. Where the same SWN
appears in multiple rows of the station file (rare — usually nested completions
with separate stations) we pick the row whose lat/lon best matches the xlsx.

Output: data/wells_resolved.json (one record per xlsx row, with `site_code` if
resolved or None).
"""
import json
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "BC Network 2026 v8.xlsx"
STATIONS = ROOT / "raw" / "stations.csv"
OUT = ROOT / "data" / "wells_resolved.json"


def load_wells():
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    ws = wb["Monitoring Network - 2027 (BC)"]
    wells = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[1]:
            continue
        wells.append({
            "mgmt_area_full": row[0],
            "swn_or_name": row[1],
            "well_depth": row[2],
            "is_2022_gwl_rms": row[3] == "Yes",
            "is_2027_gwl_rms": row[4] == "Yes",
            "butte_co_reasoning": row[5],
            "is_2027_isw_rms": row[6] == "Yes",
            "well_use": row[7],
            "well_type": row[8],
            "basin": row[9],
            "wcr_no": row[10],
            "latitude": row[11],
            "longitude": row[12],
            "monitor_freq": row[13],
            "multi_completion": row[14],
            "gse": row[15],
            "rpe": row[16],
            "screen_intervals": row[17],
            "bbgm_loc_id": row[18],
            "bbgm_aqu_layer": row[19],
            "bbgm_calib_resid_ft": row[20],
            "bbgm_source": row[21],
        })
    return wells


def main():
    wells = load_wells()
    print(f"Loaded {len(wells)} wells from xlsx")

    stations = pd.read_csv(
        STATIONS,
        usecols=[
            "site_code", "swn", "well_name", "latitude", "longitude",
            "basin_code", "basin_name", "well_use", "well_type",
            "well_depth", "wcr_no", "county_name",
            "continuous_data_station_number",
        ],
        dtype=str,
    )
    print(f"Stations total: {len(stations)}")

    # Narrow to Butte county or Sac Valley basins (5-021.*) for speed
    subset = stations[
        stations["county_name"].fillna("").str.contains("BUTTE", case=False)
        | stations["basin_code"].fillna("").str.startswith("5-021")
    ].copy()
    print(f"Butte/Sac Valley subset: {len(subset)}")

    # Convert lat/lon to float on the subset
    for c in ("latitude", "longitude"):
        subset[c] = pd.to_numeric(subset[c], errors="coerce")

    # Build SWN -> rows and well_name -> rows maps (upper-cased)
    swn_map: dict[str, list[dict]] = {}
    name_map: dict[str, list[dict]] = {}
    for _, s in subset.iterrows():
        rec = s.to_dict()
        if pd.notna(s["swn"]):
            key = str(s["swn"]).strip().upper()
            if key:
                swn_map.setdefault(key, []).append(rec)
        if pd.notna(s["well_name"]):
            key = str(s["well_name"]).strip().upper()
            if key:
                name_map.setdefault(key, []).append(rec)

    unresolved = []
    for w in wells:
        key = str(w["swn_or_name"]).strip().upper()
        hits = swn_map.get(key) or name_map.get(key) or []
        if not hits:
            unresolved.append(w["swn_or_name"])
            continue
        if len(hits) > 1 and w["latitude"] and w["longitude"]:
            best = min(
                hits,
                key=lambda s: (
                    (float(s["latitude"]) - float(w["latitude"])) ** 2
                    + (float(s["longitude"]) - float(w["longitude"])) ** 2
                    if pd.notna(s["latitude"]) and pd.notna(s["longitude"])
                    else float("inf")
                ),
            )
        else:
            best = hits[0]
        w["site_code"] = best["site_code"]
        w["dwr_lat"] = best["latitude"]
        w["dwr_lon"] = best["longitude"]
        w["dwr_basin_code"] = best["basin_code"]
        w["continuous_station_no"] = best["continuous_data_station_number"]
        w["n_station_hits"] = len(hits)

    resolved = sum(1 for w in wells if w.get("site_code"))
    print(f"\nResolved {resolved}/{len(wells)} wells")
    print(f"Unresolved ({len(unresolved)}): {unresolved}")

    rms = [w for w in wells if w["is_2027_gwl_rms"]]
    rms_resolved = sum(1 for w in rms if w.get("site_code"))
    print(f"\n2027 RMS resolved {rms_resolved}/{len(rms)}")
    for w in rms:
        sc = w.get("site_code", "<MISS>")
        print(f"  {w['swn_or_name']:24}  site_code={sc}  hits={w.get('n_station_hits')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(wells, indent=2, default=str))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
