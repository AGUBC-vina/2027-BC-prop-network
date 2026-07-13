"""Print the README's per-well AGWL derivation table (markdown).

Reads data/thresholds.json and emits the table for the 17 wells whose
displayed MT/MO/IM come from county Strawman Table 3 — each well's own
Feb-April AGWL (the Mirror methodology's input), the number of QA-Good
spring readings behind it, and the Mirror result (AGWL minus the zone
offsets), side-by-side with the displayed Table 3 values.

Usage:
    python3 scripts/print_agwl_table.py

Paste the output over the table in README.md's "Per-well derivation"
subsection whenever compute_thresholds.py is rerun with changed inputs,
then rebuild js/readme-data.js via scripts/build_readme_js.py.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THRESH_JSON = ROOT / "data" / "thresholds.json"

MA_SHORT = {
    "01-Vina-North": "North",
    "02-Vina-Chico": "Chico",
    "03-Vina-South": "South",
}


def main():
    rows = json.loads(THRESH_JSON.read_text())
    strawman = [r for r in rows if r["source"] == "Strawman Table 3"]
    strawman.sort(key=lambda r: (r["rms_mgmt_area"], r["swn"]))

    print("| Well | Zone | Feb–Apr AGWL (ft msl) | n spring obs | Mirror MT / MO / IM | Table 3 MT / MO / IM (displayed) |")
    print("|---|---|---:|---:|---|---|")
    any_low = False
    for r in strawman:
        zone = MA_SHORT.get(r["rms_mgmt_area"], r["rms_mgmt_area"])
        low = "\\*" if r.get("low_spring_data") else ""
        any_low = any_low or bool(r.get("low_spring_data"))
        mirror = f"{r['mirror_mt_ft']} / {r['mirror_mo_ft']} / {r['mirror_im_2027_ft']}"
        t3 = f"{r['mt_ft']} / {r['mo_ft']} / {r['im_2027_ft']}"
        if r.get("table3_divergence"):
            t3 = f"**{t3}** &#9888;"
        print(f"| `{r['swn']}` | {zone} | {r['agwl_ft']:.1f} | {r['n_spring_obs']:,}{low} | {mirror} | {t3} |")

    print()
    print("&#9888; = county Table 3 differs from the Mirror — see the"
          " cross-check table above for the trace.")
    if any_low:
        print("\\* = fewer than 5 QA-Good spring readings; AGWL estimate"
              " flagged as low-data.")


if __name__ == "__main__":
    main()
