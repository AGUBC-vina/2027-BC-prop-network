"""Compare three AGWL window definitions for Christina's Mirror methodology.

Variants:
  1. Feb-May      — average of QA-Good GWE in Feb/Mar/Apr/May months across
                    all years (wide spring window)
  2. Feb-April    — average of QA-Good GWE in Feb/Mar/Apr months across
                    all years (excludes May; closer to pre-pumping conditions)
  3. Highest March — per year, take the highest QA-Good March GWE; average
                    those annual peaks across all years. Captures the
                    peak-of-peak each year. NOT an average across all
                    measurements — only the per-year maximum, then averaged
                    across years.

For each variant we recompute:
  - AGWL per well (2022 RMS + new RMS)
  - Zone offsets AveΔGWL_MT/_MO/_IM from the 2022 RMS
  - Per-well Christina MT/MO/IM for the 17 new wells
  - Dry-well counts under (a) bottom > MT and (b) with one-sided elev
    correction.

Writes a comparison report to analysis/agwl_window_comparison.md.

Carryover wells (9) keep their adopted 2022 GSP MT/MO/IM under every
variant. LWA's +10 ft pump-allowance rule is intentionally NOT applied —
we anchor to the same dry rule the 2022 GSP used (bottom > MT).
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WELLS_JSON = ROOT / "data" / "wells_resolved.json"
THR_CURRENT = ROOT / "data" / "thresholds.json"
THR_2022 = ROOT / "data" / "thresholds_2022.json"
MEAS_JS = ROOT / "js" / "measurements-data.js"
POLYS = ROOT / "data" / "vina_2027_thiessen_three_zone.geojson"
DOMESTIC = ROOT / "data" / "domestic_wells.json"
OUT_MD = ROOT / "analysis" / "agwl_window_comparison.md"


def load_measurements() -> dict:
    text = MEAS_JS.read_text()
    m = re.search(r"const MEASUREMENTS\s*=\s*({.*?});", text, re.S)
    if not m:
        raise SystemExit("Could not parse MEASUREMENTS from js/measurements-data.js")
    return json.loads(m.group(1))


def qa_good(recs: list[dict]) -> list[dict]:
    return [
        r for r in recs
        if r.get("gwe") is not None
        and r.get("qa")
        and "good" in r["qa"].lower()
    ]


def month_of(r: dict) -> int | None:
    try:
        return int(r["d"][5:7])
    except (KeyError, ValueError, IndexError):
        return None


def year_of(r: dict) -> str | None:
    try:
        return r["d"][:4]
    except (KeyError, IndexError):
        return None


# --- AGWL definitions -------------------------------------------------------


def agwl_window(recs: list[dict], months: set[int]) -> tuple[float | None, int]:
    """Mean of QA-Good GWE measurements falling in the given months."""
    good = qa_good(recs)
    vals = [r["gwe"] for r in good if month_of(r) in months]
    if not vals:
        return None, 0
    return statistics.mean(vals), len(vals)


def agwl_annual_peak_march(recs: list[dict]) -> tuple[float | None, int]:
    """Per-year highest QA-Good March GWE; mean across years.

    Returns (mean_of_annual_peaks, n_years_with_data).
    """
    good = qa_good(recs)
    by_year: dict[str, list[float]] = defaultdict(list)
    for r in good:
        if month_of(r) == 3:
            y = year_of(r)
            if y is not None:
                by_year[y].append(r["gwe"])
    peaks = [max(vals) for vals in by_year.values() if vals]
    if not peaks:
        return None, 0
    return statistics.mean(peaks), len(peaks)


VARIANTS: list[tuple[str, callable, str]] = [
    ("Feb-May",       lambda r: agwl_window(r, {2, 3, 4, 5}), "Average of all QA-Good GWE measurements in Feb, Mar, Apr, May months across the full record."),
    ("Feb-April",     lambda r: agwl_window(r, {2, 3, 4}),    "Average of all QA-Good GWE measurements in Feb, Mar, Apr months across the full record."),
    ("Highest March", lambda r: agwl_annual_peak_march(r),    "Per year: highest QA-Good March GWE. Then average those annual peaks across years."),
]


# --- Core computation -------------------------------------------------------


def compute_variant(
    variant_name: str,
    agwl_fn,
    wells: list[dict],
    wells_by_swn: dict,
    thr_current: list[dict],
    thr_2022_by_swn: dict,
    meas: dict,
    polygon_primary: dict,
    active_dom: list[dict],
) -> dict:
    # AGWL per 2022 RMS well, grouped by zone
    rms_2022_by_zone: dict[str, list[str]] = {}
    for w in wells:
        if w.get("is_2022_gwl_rms"):
            zone = w["mgmt_area_full"]
            rms_2022_by_zone.setdefault(zone, []).append(w["swn_or_name"])

    rms_2022_agwl: dict[str, dict] = {}
    for zone, swns in rms_2022_by_zone.items():
        for swn in swns:
            w = wells_by_swn[swn]
            t22 = thr_2022_by_swn.get(swn)
            agwl, n = agwl_fn(meas.get(w["site_code"], []))
            gse = w.get("gse")
            rec = {
                "zone": zone, "agwl": agwl, "gse": gse,
                "agwl_dbs": (gse - agwl) if (agwl is not None and gse is not None) else None,
                "n_obs": n,
                "mt22": t22["mt_ft"] if t22 else None,
                "mo22": t22["mo_ft"] if t22 else None,
                "im22": t22["im_2027_ft"] if t22 else None,
            }
            rec["delta_mt"] = (agwl - rec["mt22"]) if (agwl is not None and rec["mt22"] is not None) else None
            rec["delta_mo"] = (agwl - rec["mo22"]) if (agwl is not None and rec["mo22"] is not None) else None
            rec["delta_im"] = (agwl - rec["im22"]) if (agwl is not None and rec["im22"] is not None) else None
            rms_2022_agwl[swn] = rec

    # Zone offsets
    zone_offsets: dict[str, dict] = {}
    for zone, swns in rms_2022_by_zone.items():
        d_mt = [rms_2022_agwl[s]["delta_mt"] for s in swns if rms_2022_agwl[s]["delta_mt"] is not None]
        d_mo = [rms_2022_agwl[s]["delta_mo"] for s in swns if rms_2022_agwl[s]["delta_mo"] is not None]
        d_im = [rms_2022_agwl[s]["delta_im"] for s in swns if rms_2022_agwl[s]["delta_im"] is not None]
        agwl_dbs_vals = [rms_2022_agwl[s]["agwl_dbs"] for s in swns if rms_2022_agwl[s]["agwl_dbs"] is not None]
        zone_offsets[zone] = {
            "n_wells": len(swns),
            "ave_agwl_dbs": statistics.mean(agwl_dbs_vals) if agwl_dbs_vals else None,
            "ave_delta_mt": statistics.mean(d_mt) if d_mt else None,
            "ave_delta_mo": statistics.mean(d_mo) if d_mo else None,
            "ave_delta_im": statistics.mean(d_im) if d_im else None,
        }

    # Apply Christina to each 2022-Mirror well
    new_results: list[dict] = []
    for tc in thr_current:
        if tc["source"] != "2022 Mirror":
            continue
        swn = tc["swn"]
        w = wells_by_swn[swn]
        agwl_new, n_new = agwl_fn(meas.get(w["site_code"], []))
        gse_new = w.get("gse")
        zone = w.get("rms_mgmt_area") or w["mgmt_area_full"]
        zo = zone_offsets.get(zone)
        if agwl_new is None or zo is None or zo["ave_delta_mt"] is None:
            mt_new = mo_new = im_new = None
        else:
            mt_new = round(agwl_new - zo["ave_delta_mt"])
            mo_new = round(agwl_new - zo["ave_delta_mo"]) if zo["ave_delta_mo"] is not None else None
            im_new = round(agwl_new - zo["ave_delta_im"]) if zo["ave_delta_im"] is not None else None
        new_results.append({
            "swn": swn,
            "zone_geographic": w["mgmt_area_full"],
            "zone_rms": zone,
            "gse": gse_new,
            "agwl": agwl_new,
            "agwl_dbs": (gse_new - agwl_new) if (agwl_new is not None and gse_new is not None) else None,
            "n_obs": n_new,
            "current_mt": tc["mt_ft"],
            "christina_mt": mt_new,
            "christina_mo": mo_new,
            "christina_im": im_new,
            "current_mt_dbs": (gse_new - tc["mt_ft"]) if gse_new is not None else None,
            "christina_mt_dbs": (gse_new - mt_new) if (mt_new is not None and gse_new is not None) else None,
        })

    # Dry-well counts
    mt_current = {r["swn"]: r["mt_ft"] for r in thr_current}
    mt_christina = dict(mt_current)
    for r in new_results:
        if r["christina_mt"] is not None:
            mt_christina[r["swn"]] = r["christina_mt"]

    counts = {"n_total": 0, "dry_at_MT": 0, "dry_at_MT_elev": 0,
              "dry_current_MT": 0, "dry_current_MT_elev": 0}
    for d in active_dom:
        zl = d["our_polygon"]
        rms_swn = polygon_primary.get(zl)
        if rms_swn is None:
            continue
        mt_c = mt_current.get(rms_swn)
        mt_x = mt_christina.get(rms_swn)
        if mt_c is None or mt_x is None:
            continue
        primary_gse = wells_by_swn.get(rms_swn, {}).get("gse")
        well_gse = d.get("local_gse")
        if well_gse is not None and primary_gse is not None:
            elev_adj = max(0, well_gse - primary_gse)
        else:
            elev_adj = 0
        b = d["well_bottom_amsl"]
        counts["n_total"] += 1
        if b > mt_x:
            counts["dry_at_MT"] += 1
        if b > (mt_x + elev_adj):
            counts["dry_at_MT_elev"] += 1
        if b > mt_c:
            counts["dry_current_MT"] += 1
        if b > (mt_c + elev_adj):
            counts["dry_current_MT_elev"] += 1

    return {
        "variant": variant_name,
        "zone_offsets": zone_offsets,
        "new_results": new_results,
        "counts": counts,
        "rms_2022_agwl": rms_2022_agwl,
    }


# --- Main -------------------------------------------------------------------


def main() -> None:
    wells = json.loads(WELLS_JSON.read_text())
    wells_by_swn = {w["swn_or_name"]: w for w in wells}
    thr_current = json.loads(THR_CURRENT.read_text())
    thr_2022_by_swn = {r["swn"]: r for r in json.loads(THR_2022.read_text())}
    meas = load_measurements()
    polys = json.loads(POLYS.read_text())

    polygon_primary: dict[str, str] = {}
    for feat in polys["features"]:
        p = feat["properties"]
        zl = p["zone_label"]
        if p.get("is_aggregate"):
            primaries = p.get("rms_primary_swns") or []
            polygon_primary[zl] = primaries[0] if primaries else None
        else:
            polygon_primary[zl] = p.get("rms_well_swn") or (
                p.get("rms_primary_swns") or [None]
            )[0]

    dom = json.loads(DOMESTIC.read_text())
    active_dom = [
        d for d in dom
        if d.get("include") == 1
        and d.get("well_bottom_amsl") is not None
        and d.get("our_polygon")
        and d.get("lat") is not None
        and d.get("lon") is not None
    ]

    results: dict[str, dict] = {}
    for name, fn, _desc in VARIANTS:
        results[name] = compute_variant(
            name, fn, wells, wells_by_swn, thr_current,
            thr_2022_by_swn, meas, polygon_primary, active_dom,
        )

    # --- Build markdown report ---------------------------------------------
    L: list[str] = []
    L.append("# AGWL Mirror — spring-window sensitivity\n")
    L.append("Comparison of three definitions of \"average spring groundwater level\" (AGWL) for "
             "the Christina Buck Mirror methodology. Goal: identify the spring window that best "
             "balances **operational flexibility** (deeper MT = more drawdown allowed before "
             "triggering undesirable result) against **fewest potential domestic wells dry at MT** "
             "(shallower MT = fewer wells exposed).\n")
    L.append("These two objectives pull in opposite directions; a single variant cannot maximize "
             "both. The table below shows where each variant lands.\n")
    L.append("LWA's +10 ft well-pump allowance is intentionally NOT applied — we use the same "
             "dry rule as the 2022 GSP (`well_bottom > MT`), and the analysis is a sensitivity "
             "snapshot at MT, not a mitigation forecast.\n")

    # --- Headline: dry counts and avg MT depth by variant ---
    L.append("## Headline comparison\n")
    L.append("Universe = 1,253 cosmo active domestic wells. Universe and the dry rule are "
             "identical across variants — only the AGWL definition changes.\n")
    L.append("| Variant | Description | Dry at MT (Christina) | Dry at MT (Christina, elev-corrected) |")
    L.append("|---|---|---|---|")
    for name, _fn, desc in VARIANTS:
        c = results[name]["counts"]
        n = c["n_total"]
        L.append(f"| **{name}** | {desc} | **{c['dry_at_MT']}** ({c['dry_at_MT']/n*100:.1f}%) | **{c['dry_at_MT_elev']}** ({c['dry_at_MT_elev']/n*100:.1f}%) |")
    L.append("")
    L.append("Reference: under the **current 2022-Mirror buffer methodology** (not Christina), the "
             f"same universe yields {results['Feb-May']['counts']['dry_current_MT']} dry at MT and "
             f"{results['Feb-May']['counts']['dry_current_MT_elev']} dry at MT with elev correction.\n")

    # --- Flexibility view: avg MT depth (DBS) for new wells, by variant ---
    L.append("## Operational flexibility view — average MT depth below ground (DBS, ft) for the 17 new RMS wells\n")
    L.append("Deeper MT = more drawdown allowed = more operational room.\n")
    L.append("| Zone | n new RMS | Feb-May avg MT DBS | Feb-April avg MT DBS | Highest-March avg MT DBS |")
    L.append("|---|---|---|---|---|")
    for zone in ["01-Vina-North", "03-Vina-South"]:
        row = [zone, None]
        # collect avg MT_DBS by zone per variant
        for name, _fn, _desc in VARIANTS:
            new_results = results[name]["new_results"]
            zone_results = [r for r in new_results if r["zone_rms"] == zone and r["christina_mt_dbs"] is not None]
            n = len(zone_results)
            avg = statistics.mean(r["christina_mt_dbs"] for r in zone_results) if zone_results else None
            if row[1] is None:
                row[1] = n
            row.append(f"{avg:.1f}" if avg is not None else "—")
        L.append("| " + " | ".join(str(x) for x in row) + " |")
    L.append("")
    L.append("(Chico has no new RMS wells — only carryover CWSCH01b, unchanged across variants.)\n")

    # --- Zone offsets by variant ---
    L.append("## Zone offsets (DBS, ft) derived from 2022 RMS under each variant\n")
    L.append("Larger ΔGWL→MT = the GSP allowed more drawdown below AGWL before declaring undesirable result.\n")
    for zone in ["01-Vina-North", "02-Vina-Chico", "03-Vina-South"]:
        L.append(f"### {zone}\n")
        L.append("| Variant | avg AGWL DBS | ΔGWL→MT | ΔGWL→MO | ΔGWL→IM |")
        L.append("|---|---|---|---|---|")
        for name, _fn, _desc in VARIANTS:
            zo = results[name]["zone_offsets"].get(zone)
            if not zo or zo["ave_agwl_dbs"] is None:
                continue
            L.append(f"| {name} | {zo['ave_agwl_dbs']:.2f} | {zo['ave_delta_mt']:.2f} | "
                     f"{zo['ave_delta_mo']:.2f} | {zo['ave_delta_im']:.2f} |")
        L.append("")

    # --- Per-well MT DBS by variant ---
    L.append("## Per-well MT (DBS, ft below ground) — 17 new RMS wells\n")
    L.append("Christina MT under each variant, sorted by zone and well.\n")
    L.append("| Well | Zone | Current MT | Feb-May | Feb-April | Highest March |")
    L.append("|---|---|---|---|---|---|")
    # Build lookup: swn -> variant -> mt_dbs
    feb_may_by_swn = {r["swn"]: r for r in results["Feb-May"]["new_results"]}
    feb_apr_by_swn = {r["swn"]: r for r in results["Feb-April"]["new_results"]}
    peak_by_swn    = {r["swn"]: r for r in results["Highest March"]["new_results"]}
    for swn in sorted(feb_may_by_swn, key=lambda s: (feb_may_by_swn[s]["zone_rms"], s)):
        rm = feb_may_by_swn[swn]
        cur = f"{rm['current_mt_dbs']:.0f}" if rm['current_mt_dbs'] is not None else "—"
        fm  = f"{feb_may_by_swn[swn]['christina_mt_dbs']:.0f}" if feb_may_by_swn[swn]['christina_mt_dbs'] is not None else "—"
        fa  = f"{feb_apr_by_swn[swn]['christina_mt_dbs']:.0f}" if feb_apr_by_swn[swn]['christina_mt_dbs'] is not None else "—"
        pm  = f"{peak_by_swn[swn]['christina_mt_dbs']:.0f}"   if peak_by_swn[swn]['christina_mt_dbs']   is not None else "—"
        L.append(f"| {swn} | {rm['zone_rms']} | {cur} | {fm} | {fa} | {pm} |")
    L.append("")

    # --- (Interpretation block intentionally omitted — neutral writeup
    #     authored separately in agwl_window_comparison.md.)
    # Placeholder block to satisfy the rest of the function
    if False:
        L.append("Important caveat: AGWL_new and AGWL_2022 both shift together as the window narrows, so the net effect "
             "on MT depends on whether the new wells have systematically different seasonal patterns than the 2022 "
             "RMS. The numbers in the headline table reflect that interaction empirically — don't extrapolate "
             "without checking the table.")
    L.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(L))

    # --- Stdout summary ---
    print("\n=== HEADLINE: domestic wells dry at MT (universe = 1,253) ===\n")
    print(f"{'Variant':<16} {'Dry at MT':>11} {'Dry (elev-corr)':>18}")
    for name, _fn, _desc in VARIANTS:
        c = results[name]["counts"]
        print(f"{name:<16} {c['dry_at_MT']:>11} {c['dry_at_MT_elev']:>18}")
    print()
    print("Reference (current buffer methodology):")
    print(f"{'':<16} {results['Feb-May']['counts']['dry_current_MT']:>11} {results['Feb-May']['counts']['dry_current_MT_elev']:>18}")
    print()
    print(f"Report written to {OUT_MD}")


if __name__ == "__main__":
    main()
