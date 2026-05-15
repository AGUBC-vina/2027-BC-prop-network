"""Build data/thresholds.json combining the 7 adopted 2022 GSP thresholds
with 21 newly-computed "2022 Mirror" baseline thresholds for the rest of the
28-well 2027 RMS network.

Methodology (Path 2 — empirical mirror of the 2022 GSP):
    drought_min  = min GWE recorded during 2012-2016 + 2020-2022 drought windows
                   (DWR Periodic Measurements, all QA flags)
    MT_ft        = round(drought_min - 70)
    MO_ft        = round(drought_min)
    IM_2027_ft   = round(drought_min + 2)

Source labels:
    "2022 GSP"     — values carried forward unchanged from the adopted 2022 GSP
                     (7 wells that were RMS in both the 2022 and 2027 networks)
    "2022 Mirror"  — values derived above; baseline pending GSA review
                     (21 wells added to RMS for 2027)

Output:
    data/thresholds.json — one record per 2027 RMS well with mt_ft, mo_ft,
                           im_2027_ft, source, drought_min, drought_n,
                           drought_first, drought_last, low_drought_data flag.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WELLS_JSON = ROOT / "data" / "wells_resolved.json"
CARRYOVER_JSON = ROOT / "data" / "thresholds_2022.json"
MEAS_JS = ROOT / "js" / "measurements-data.js"
OUT = ROOT / "data" / "thresholds.json"

DROUGHT_WINDOWS = [(2012, 2016), (2020, 2022)]
MT_OFFSET = -70   # MT = drought_min - 70
IM_OFFSET = 2    # IM = drought_min + 2

LOW_DATA_THRESHOLD = 3  # fewer than this many drought-window readings = flag


def load_measurements() -> dict:
    text = MEAS_JS.read_text()
    m = re.search(r"const MEASUREMENTS\s*=\s*({.*});", text, re.S)
    if not m:
        raise SystemExit("Could not parse MEASUREMENTS from js/measurements-data.js")
    return json.loads(m.group(1))


def drought_records(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        if r.get("gwe") is None:
            continue
        try:
            y = int(r["d"][:4])
        except (KeyError, ValueError):
            continue
        if any(y0 <= y <= y1 for y0, y1 in DROUGHT_WINDOWS):
            out.append(r)
    return out


def main():
    wells = json.loads(WELLS_JSON.read_text())
    carry = {t["swn"]: t for t in json.loads(CARRYOVER_JSON.read_text())}
    meas = load_measurements()

    out = []
    for w in wells:
        if not w["is_2027_gwl_rms"]:
            continue
        name = w["swn_or_name"]
        site = w["site_code"]
        recs = meas.get(site, [])
        drecs = drought_records(recs)
        drought_n = len(drecs)
        drought_min = min(r["gwe"] for r in drecs) if drecs else None
        drought_first = drecs[0]["d"] if drecs else None
        drought_last = drecs[-1]["d"] if drecs else None

        if name in carry:
            t = carry[name]
            rec = {
                "swn": name,
                "site_code": site,
                "mgmt_area_full": w["mgmt_area_full"],
                "source": "2022 GSP",
                "mt_ft": t["mt_ft"],
                "mo_ft": t["mo_ft"],
                "im_2027_ft": t["im_2027_ft"],
                "drought_min": drought_min,
                "drought_n": drought_n,
                "drought_first": drought_first,
                "drought_last": drought_last,
                "low_drought_data": drought_n < LOW_DATA_THRESHOLD,
            }
        else:
            if drought_min is None:
                # Wells without ANY drought data — extremely rare for RMS;
                # flag as such and leave thresholds None.
                rec = {
                    "swn": name,
                    "site_code": site,
                    "mgmt_area_full": w["mgmt_area_full"],
                    "source": "2022 Mirror (no drought data)",
                    "mt_ft": None,
                    "mo_ft": None,
                    "im_2027_ft": None,
                    "drought_min": None,
                    "drought_n": 0,
                    "drought_first": None,
                    "drought_last": None,
                    "low_drought_data": True,
                }
            else:
                rec = {
                    "swn": name,
                    "site_code": site,
                    "mgmt_area_full": w["mgmt_area_full"],
                    "source": "2022 Mirror",
                    "mt_ft": round(drought_min + MT_OFFSET),
                    "mo_ft": round(drought_min),
                    "im_2027_ft": round(drought_min + IM_OFFSET),
                    "drought_min": round(drought_min, 2),
                    "drought_n": drought_n,
                    "drought_first": drought_first,
                    "drought_last": drought_last,
                    "low_drought_data": drought_n < LOW_DATA_THRESHOLD,
                }
        out.append(rec)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    n_adopted = sum(1 for r in out if r["source"] == "2022 GSP")
    n_mirror = sum(1 for r in out if r["source"].startswith("2022 Mirror"))
    n_low = sum(1 for r in out if r["low_drought_data"] and r["source"].startswith("2022 Mirror"))
    n_total = len(out)
    print(f"\nWrote {OUT}")
    print(f"  total RMS wells: {n_total}")
    print(f"    adopted (2022 GSP):       {n_adopted}")
    print(f"    new (2022 Mirror):        {n_mirror}")
    print(f"      ...with thin drought data (<{LOW_DATA_THRESHOLD} readings): {n_low}")

    print(f"\n{'Well':<22} {'mgmt':<15} {'source':<14} {'dmin':>6} {'MT':>5} {'MO':>5} {'IM':>5} {'n':>4} {'low?':>5}")
    print("-" * 92)
    for r in out:
        dmin = f"{r['drought_min']:.1f}" if r['drought_min'] is not None else "—"
        mt = str(r['mt_ft']) if r['mt_ft'] is not None else "—"
        mo = str(r['mo_ft']) if r['mo_ft'] is not None else "—"
        im = str(r['im_2027_ft']) if r['im_2027_ft'] is not None else "—"
        low = "★" if r['low_drought_data'] and r['source'].startswith("2022 Mirror") else ""
        print(f"{r['swn']:<22} {r['mgmt_area_full']:<15} {r['source']:<14} {dmin:>6} {mt:>5} {mo:>5} {im:>5} {r['drought_n']:>4} {low:>5}")


if __name__ == "__main__":
    main()
