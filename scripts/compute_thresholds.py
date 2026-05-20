"""Build data/thresholds.json — MT/MO/IM-2027 for the 2027 RMS network.

Post-2026-05-21 revision: two distinct methodologies depending on whether
the well was an RMS in the 2022 GSP.

(A) 2022 GSP carryovers (9 wells) — values unchanged from the 2022 GSP:
    - 5 North: 22N01W05M001M, 23N01E07H001M, 23N01E33A001M,
      23N01W36P001M, 23N02W25C001M
    - 3 South: 20N02E24C001M, 21N02E18C003M, 21N02E26E006M (inherits
      from its nested sibling 21N02E26E005M, same lat/lng)
    - 1 Chico: CWSCH01b

(B) New 2022 Mirror methodology (17 wells: 8 N + 9 S) — derived from a
    MT-buffer benchmark computed against the original 2022 GSP RMS wells.

    Step 1 (benchmark) — for each of the 13 well-level 2022 GSP RMS sites
    (17 designated minus 4 CWSCH nested completions that share a single
    pad and would skew aggregate statistics), compute:

        per_well_buffer = (all-time min QA-Good GWE) - (2022 GSP MT)

    Average by management area:
        Region    n   avg buffer (ft)
        North     6   69.55
        South     6   57.60
        Chico     1   27.93  (single well: 22N01E28J003M)

    Step 2 — for each non-carryover 2027 RMS well, derive:
        alltime_min  = min QA-Good GWE on the FULL DWR record
        region_buf   = regional buffer for the well's GEOGRAPHIC mgmt area
                       (N=69.55, S=57.60, Chico=27.93)
        MT_ft        = round(alltime_min - region_buf)
        MO_ft        = round(drought_min)                    [unchanged]
        IM_2027_ft   = round(drought_min + 2)                [unchanged]

    Notes on choice of geography for the buffer:
    - Buffer reflects regional hydrology where the well physically sits,
      not the network-design assignment. So the 2 wells that are RMS for
      the North network but physically inside Chico mgmt area
      (22N01E09B001M, 22N01E20K001M) use the Chico buffer (27.93 ft),
      giving them tight buffers consistent with their Chico setting.

Source labels in the output:
    "2022 GSP"     — adopted carryovers (9 wells). Visualized with dashed
                     threshold lines and a blue pill in §5.3.
    "2022 Mirror"  — new buffer-based derivation (17 wells). Visualized
                     with dotted threshold lines and a warm-cream pill.

Caveats baked into the README/PROJECT_NOTES:
- All-time min reflects the OBSERVED historical low, not the true low.
  Wells with short records or sparse monitoring may understate how low
  the water level actually got — buffers derived from such wells should
  be considered conservative.
- The Chico regional buffer (27.93 ft) comes from a single well
  (22N01E28J003M) after CWSCH exclusion. Thin coverage for a whole
  management area.
- Buffer is a descriptive statistic, not a margin of safety or forward
  projection. It does not account for drought severity, climate change,
  or pumping trajectories.
- Adopted MT/MO/IM remain the 2022 GSP values until the GSA formally
  updates them in the 2027 GSP cycle. The Mirror remains an internal
  working baseline.
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
IM_OFFSET = 2    # IM = drought_min + 2

LOW_DATA_THRESHOLD = 3  # fewer than this many drought-window readings = flag

# Regional MT buffers from the 2022 GSP buffer analysis (see module docstring).
# Keys are the geographic mgmt_area_full attribute on each well.
REGIONAL_BUFFER_FT = {
    "01-Vina-North": 69.55,
    "03-Vina-South": 57.60,
    "02-Vina-Chico": 27.93,
}


def load_measurements() -> dict:
    text = MEAS_JS.read_text()
    m = re.search(r"const MEASUREMENTS\s*=\s*({.*});", text, re.S)
    if not m:
        raise SystemExit("Could not parse MEASUREMENTS from js/measurements-data.js")
    return json.loads(m.group(1))


def filter_qa_good(records: list[dict]) -> list[dict]:
    """QA-Good readings only."""
    return [
        r for r in records
        if r.get("gwe") is not None
        and r.get("qa")
        and "good" in r["qa"].lower()
    ]


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
    wells_by_swn = {w["swn_or_name"]: w for w in wells}

    out = []
    for w in wells:
        if not w["is_2027_gwl_rms"]:
            continue
        name = w["swn_or_name"]
        site = w["site_code"]
        recs = meas.get(site, [])
        good_recs = filter_qa_good(recs)
        drecs = drought_records(recs)
        drought_n = len(drecs)
        drought_min = min(r["gwe"] for r in drecs) if drecs else None
        drought_first = drecs[0]["d"] if drecs else None
        drought_last = drecs[-1]["d"] if drecs else None
        alltime_min = min(r["gwe"] for r in good_recs) if good_recs else None

        # ---- 2022 GSP carryover path -------------------------------
        # Either the well was a 2022 RMS itself, or it inherits from a
        # nested sibling that was (e.g. 21N02E26E006M inheriting from
        # 21N02E26E005M, same lat/lng but different completion depth).
        carry_swn = name if name in carry else w.get("carryover_from")
        if carry_swn and carry_swn in carry:
            t = carry[carry_swn]
            note = (
                f"inherited from {carry_swn} (nested sibling)"
                if carry_swn != name else None
            )
            rec = {
                "swn": name,
                "site_code": site,
                "mgmt_area_full": w["mgmt_area_full"],
                "source": "2022 GSP",
                "mt_ft": t["mt_ft"],
                "mo_ft": t["mo_ft"],
                "im_2027_ft": t["im_2027_ft"],
                "drought_min": round(drought_min, 2) if drought_min is not None else None,
                "alltime_min": round(alltime_min, 2) if alltime_min is not None else None,
                "drought_n": drought_n,
                "drought_first": drought_first,
                "drought_last": drought_last,
                "low_drought_data": drought_n < LOW_DATA_THRESHOLD,
                "carryover_from": carry_swn if carry_swn != name else None,
                "note": note,
            }
            out.append(rec)
            continue

        # ---- 2022 Mirror — new buffer-based methodology ------------
        if alltime_min is None:
            # Wells without ANY QA-Good GWE — extremely rare for RMS;
            # flag and leave thresholds None.
            rec = {
                "swn": name,
                "site_code": site,
                "mgmt_area_full": w["mgmt_area_full"],
                "source": "2022 Mirror (no GWE data)",
                "mt_ft": None,
                "mo_ft": None,
                "im_2027_ft": None,
                "alltime_min": None,
                "drought_min": None,
                "drought_n": 0,
                "drought_first": None,
                "drought_last": None,
                "low_drought_data": True,
                "regional_buffer_ft": REGIONAL_BUFFER_FT.get(w["mgmt_area_full"]),
            }
            out.append(rec)
            continue

        region_buf = REGIONAL_BUFFER_FT.get(w["mgmt_area_full"])
        if region_buf is None:
            raise SystemExit(
                f"No regional buffer defined for mgmt_area_full = "
                f"{w['mgmt_area_full']!r} (well {name})"
            )

        mt_ft = round(alltime_min - region_buf)
        # MO and IM-2027 keep the prior Mirror formulas (drought-window
        # based) so the dashboard still has a "measurable objective" tied
        # to the same hydrologic concept the GSA used for 2022.
        mo_ft = round(drought_min) if drought_min is not None else None
        im_ft = round(drought_min + IM_OFFSET) if drought_min is not None else None

        rec = {
            "swn": name,
            "site_code": site,
            "mgmt_area_full": w["mgmt_area_full"],
            "source": "2022 Mirror",
            "mt_ft": mt_ft,
            "mo_ft": mo_ft,
            "im_2027_ft": im_ft,
            "alltime_min": round(alltime_min, 2),
            "drought_min": round(drought_min, 2) if drought_min is not None else None,
            "drought_n": drought_n,
            "drought_first": drought_first,
            "drought_last": drought_last,
            "low_drought_data": drought_n < LOW_DATA_THRESHOLD,
            "regional_buffer_ft": region_buf,
        }
        out.append(rec)

    out.sort(key=lambda r: r["swn"])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))

    n_adopted = sum(1 for r in out if r["source"] == "2022 GSP")
    n_mirror = sum(1 for r in out if r["source"].startswith("2022 Mirror"))
    n_low = sum(1 for r in out if r["low_drought_data"] and r["source"].startswith("2022 Mirror"))
    print(f"\nWrote {OUT}")
    print(f"  total RMS wells: {len(out)}")
    print(f"    adopted (2022 GSP):  {n_adopted}")
    print(f"    new (2022 Mirror):   {n_mirror}")
    print(f"      ...with thin drought data (<{LOW_DATA_THRESHOLD}): {n_low}")

    print(f"\n{'Well':<18} {'mgmt':<15} {'source':<14} {'alltime':>8} "
          f"{'buf':>6} {'MT':>5} {'MO':>5} {'IM':>5} {'n_drought':>10}")
    print("-" * 95)
    for r in out:
        am = f"{r['alltime_min']:.1f}" if r.get('alltime_min') is not None else "—"
        buf = f"{r['regional_buffer_ft']:.2f}" if r.get('regional_buffer_ft') is not None else "—"
        mt = str(r['mt_ft']) if r['mt_ft'] is not None else "—"
        mo = str(r['mo_ft']) if r['mo_ft'] is not None else "—"
        im = str(r['im_2027_ft']) if r['im_2027_ft'] is not None else "—"
        print(f"{r['swn']:<18} {r['mgmt_area_full']:<15} {r['source']:<14} "
              f"{am:>8} {buf:>6} {mt:>5} {mo:>5} {im:>5} {r.get('drought_n', 0):>10}")


if __name__ == "__main__":
    main()
