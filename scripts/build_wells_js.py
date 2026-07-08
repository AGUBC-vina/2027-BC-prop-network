"""Emit js/wells-data.js for the dashboard.

Joins:
    - data/wells_resolved.json   (every xlsx row, with DWR site_code)
    - data/thresholds.json       (MT/MO/IM-2027 for the 29 2027 RMS wells:
                                  12 "2022 GSP" carry-overs + 17 county
                                  "Strawman Table 3" values with the
                                  dashboard's AGWL Mirror cross-check riding
                                  along, computed by
                                  scripts/compute_thresholds.py; 6 supplemental
                                  Chico nested completions are unthresholded
                                  per 2022 GSP convention)
    - data/tnc_ecological_thresholds.csv
                                 (TNC "Ecological Threshold Recommendations -
                                  Vina Subbasin", 9 wells. UNITS NOTE: the
                                  CSV column headers say "(ft bgs)" but the
                                  values are groundwater ELEVATIONS in ft msl
                                  — TNC's per-well hydrograph PDFs plot the
                                  same numbers on a "Groundwater Elevation
                                  (ft)" axis, and read as depths they would
                                  be physically impossible, e.g. 147 ft bgs
                                  in the 110-ft-deep well 23N01W09E001M.)

Output schema (one element per well in the xlsx):
    well_name, swn, site_code, mgmt_area_full, mgmt_area, well_depth,
    is_2022_gwl_rms, is_2027_gwl_rms, is_2027_isw_rms,
    well_use, well_type, basin, wcr_no, latitude, longitude,
    monitor_freq, multi_completion, gse, rpe, screen_intervals,
    butte_co_reasoning,
    bbgm_loc_id, bbgm_aqu_layer, bbgm_calib_resid_ft, bbgm_source,
    mt_ft, mo_ft, im_2027_ft,
    threshold_source     ("2022 GSP" | "Strawman Table 3" | null for non-RMS)
    threshold_low_data   (true if <3 drought-window readings)
    mirror_mt_ft, mirror_mo_ft, mirror_im_2027_ft
                         (dashboard's independent AGWL Mirror cross-check;
                          null for carryovers and non-RMS)
    table3_divergence    (note string when county Table 3 != Mirror, else null)
    tnc_eco_threshold_ft, tnc_mean_summer_gwe_ft, tnc_sd_summer_ft,
    tnc_rpe_ft           (TNC recommendation fields, ft msl; null for the
                          70 wells TNC did not evaluate)
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WELLS_JSON = ROOT / "data" / "wells_resolved.json"
THRESH_JSON = ROOT / "data" / "thresholds.json"
TNC_CSV = ROOT / "data" / "tnc_ecological_thresholds.csv"
OUT = ROOT / "js" / "wells-data.js"

MA_SHORT = {
    "01-Vina-North": "North",
    "02-Vina-Chico": "Chico",
    "03-Vina-South": "South",
}


def load_tnc() -> dict:
    """TNC ecological threshold recommendations, keyed by well SWN.

    Values in the CSV are groundwater elevations in ft msl despite the
    "(ft bgs)" column headers (see module docstring). The recommended
    threshold works out to roughly (mean summer GWE - 1.3 sd), i.e. about
    the 10th percentile of historically observed summer levels.
    """
    tnc = {}
    with TNC_CSV.open(newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("WELL_NAME") or "").strip()
            if not name:
                continue
            tnc[name] = {
                "tnc_rpe_ft": float(row["RPE"]),
                "tnc_mean_summer_gwe_ft": float(row["mean_gwe_summer (ft bgs)"]),
                "tnc_sd_summer_ft": float(row["sd_gwe_summer (ft bgs)"]),
                "tnc_eco_threshold_ft": float(row["recommended_ecological_threshold (ft bgs)"]),
            }
    return tnc


def main():
    wells = json.loads(WELLS_JSON.read_text())
    thresholds = {t["swn"]: t for t in json.loads(THRESH_JSON.read_text())}
    tnc = load_tnc()

    out = []
    for w in wells:
        name = w["swn_or_name"]
        thresh = thresholds.get(name, {})
        rec = {
            "well_name": name,
            "swn": name,
            "site_code": w.get("site_code") or "",
            "mgmt_area_full": w["mgmt_area_full"],
            "mgmt_area": MA_SHORT.get(w["mgmt_area_full"], "Other"),
            # Network-design assignment (may differ from geographic mgmt_area_full
            # for the 2 Chico-located wells reassigned to North in the 2026-05-19
            # network revision).
            "rms_mgmt_area": w.get("rms_mgmt_area", w["mgmt_area_full"]),
            "rms_mgmt_area_short": MA_SHORT.get(
                w.get("rms_mgmt_area", w["mgmt_area_full"]), "Other"),
            # 21N02E26E006M inherits its 2022 GSP MT/MO/IM from a nested
            # sibling at the same lat/lng (21N02E26E005M, retired from 2027).
            "carryover_from": w.get("carryover_from"),
            "well_depth": w["well_depth"],
            "is_2022_gwl_rms": bool(w["is_2022_gwl_rms"]),
            "is_2027_gwl_rms": bool(w["is_2027_gwl_rms"]),
            "is_2027_isw_rms": bool(w["is_2027_isw_rms"]),
            "well_use": w["well_use"],
            "well_type": w["well_type"],
            "basin": w["basin"],
            "wcr_no": w["wcr_no"] if w["wcr_no"] not in (None, "None") else "",
            "latitude": w["latitude"],
            "longitude": w["longitude"],
            "monitor_freq": w["monitor_freq"],
            "multi_completion": w["multi_completion"],
            "gse": w["gse"] if w["gse"] not in (None, "None") else None,
            "rpe": w["rpe"] if w["rpe"] not in (None, "None") else None,
            "screen_intervals": w["screen_intervals"] if w["screen_intervals"] not in (None, "None") else "",
            "butte_co_reasoning": w["butte_co_reasoning"] or "",
            "bbgm_loc_id": w["bbgm_loc_id"] if w["bbgm_loc_id"] not in (None, "None") else "",
            "bbgm_aqu_layer": w["bbgm_aqu_layer"] if w["bbgm_aqu_layer"] not in (None, "None") else "",
            "bbgm_calib_resid_ft": w["bbgm_calib_resid_ft"] if w["bbgm_calib_resid_ft"] not in (None, "None") else None,
            "bbgm_source": w["bbgm_source"] or "",
            "mt_ft": thresh.get("mt_ft"),
            "mo_ft": thresh.get("mo_ft"),
            "im_2027_ft": thresh.get("im_2027_ft"),
            "threshold_source": thresh.get("source") if thresh else None,
            "threshold_low_data": thresh.get("low_spring_data", False) if thresh else False,
            # Dashboard's independent AGWL Mirror cross-check of the county
            # Table 3 values (null for 2022 GSP carryovers and non-RMS wells).
            "mirror_mt_ft": thresh.get("mirror_mt_ft"),
            "mirror_mo_ft": thresh.get("mirror_mo_ft"),
            "mirror_im_2027_ft": thresh.get("mirror_im_2027_ft"),
            "table3_divergence": thresh.get("table3_divergence"),
        }
        # TNC ecological threshold recommendation fields (9 wells).
        rec.update(tnc.get(name, {
            "tnc_rpe_ft": None,
            "tnc_mean_summer_gwe_ft": None,
            "tnc_sd_summer_ft": None,
            "tnc_eco_threshold_ft": None,
        }))
        out.append(rec)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "// Auto-generated by scripts/build_wells_js.py - do not edit by hand.\n"
        "// Source: BC Network 2026 v8.xlsx + DWR CKAN Stations + 2022 GSP thresholds.\n\n"
        "const WELLS = " + json.dumps(out) + ";\n"
    )
    n_2027 = sum(1 for r in out if r["is_2027_gwl_rms"])
    n_2022 = sum(1 for r in out if r["is_2022_gwl_rms"])
    n_thresh = sum(1 for r in out if r["mt_ft"] is not None)
    n_tnc = sum(1 for r in out if r["tnc_eco_threshold_ft"] is not None)
    unmatched_tnc = sorted(set(tnc) - {r["swn"] for r in out if r["tnc_eco_threshold_ft"] is not None})
    if unmatched_tnc:
        raise SystemExit(f"TNC wells not found in the network: {unmatched_tnc}")
    print(f"Wrote {OUT}")
    print(f"  total wells: {len(out)}")
    print(f"  2022 RMS:    {n_2022}")
    print(f"  2027 RMS:    {n_2027}")
    print(f"  w/ MT/MO:    {n_thresh}")
    print(f"  w/ TNC eco threshold: {n_tnc} (all {len(tnc)} CSV wells matched)")


if __name__ == "__main__":
    main()
