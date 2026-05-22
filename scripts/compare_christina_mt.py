"""Compare current "2022-Mirror buffer" MT/MO/IM against Christina Buck's
proposed AGWL-anchored Mirror, and report domestic-well dry counts under
both methodologies and both dry-rules (with/without LWA's +10 ft well-pump
allowance).

Read-only — does NOT modify thresholds.json, the dashboard, or anything
under js/. Writes a comparison report to analysis/christina_mt_comparison.md
and prints a summary to stdout.

Christina Buck's methodology (per email follow-up, 2026-05-20):
    1. For each 2022 GSP RMS well, compute AGWL = average spring
       groundwater level (ft msl) over its full timeseries.
       "Spring" = DWR's Feb-May convention. Christina's earlier draft
       called this "AGWL"; her follow-up renamed to AGWL ("average
       groundwater level"), which is the standard term — AGWL would
       technically mean ground surface elevation, a fixed quantity.
       Computation is identical: average of QA-Good DWR GWE measurements
       within Feb-May months.
    2. For each management area zone, compute the average gap from AGWL
       to the adopted 2022 MT:
           AveDeltaGWL_MT_zone = mean over 2022 RMS in zone of
                                 (AGWL_RMS - MT_2022_RMS)
       Repeat for MO and IM-2027 to get _MO and _IM zone offsets.
    3. For each NEW 2027 RMS well (the ones currently using the buffer
       methodology — "2022 Mirror" source in thresholds.json):
           MT_christina = AGWL_well - AveDeltaGWL_MT_zone
           MO_christina = AGWL_well - AveDeltaGWL_MO_zone
           IM_christina = AGWL_well - AveDeltaGWL_IM_zone

Zone assignment uses each well's rms_mgmt_area (network), matching the
current methodology so the two North wells physically inside Chico
(22N01E09B001M, 22N01E20K001M) get the North offset, not Chico's.

Dry-count comparison: cosmo domestic wells with include=1 and a valid
well_bottom_amsl, joined to their containing 2027 polygon. Four rules:
    A. current MT, dry = (bottom > MT)                  [our 511 baseline]
    B. current MT, dry = (bottom + 10 > MT)             [apples-to-LWA on current network]
    C. Christina MT, dry = (bottom > MT)                [new methodology, our framework]
    D. Christina MT, dry = (bottom + 10 > MT)           [apples-to-LWA on new methodology]
LWA's +10 ft accounts for domestic pumps not drawing from absolute bottom.

Carryover wells (9 — 2022 GSP source in thresholds.json) keep their
adopted MT/MO/IM under both methodologies. They are NOT recomputed.
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WELLS_JSON = ROOT / "data" / "wells_resolved.json"
THR_CURRENT = ROOT / "data" / "thresholds.json"
THR_2022 = ROOT / "data" / "thresholds_2022.json"
MEAS_JS = ROOT / "js" / "measurements-data.js"
POLYS = ROOT / "data" / "vina_2027_thiessen_three_zone.geojson"
DOMESTIC = ROOT / "data" / "domestic_wells.json"
OUT_MD = ROOT / "analysis" / "christina_mt_comparison.md"

SPRING_MONTHS = {2, 3, 4, 5}  # DWR spring convention (Feb-May)
LWA_PAD_FT = 10  # LWA's well-bottom pump allowance


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


def spring_records(recs: list[dict]) -> list[dict]:
    """QA-Good GWE measurements in Feb-May of any year."""
    out = []
    for r in qa_good(recs):
        try:
            month = int(r["d"][5:7])
        except (KeyError, ValueError):
            continue
        if month in SPRING_MONTHS:
            out.append(r)
    return out


def agwl_for_site(meas: dict, site_code: str) -> tuple[float | None, int]:
    """Return (AGWL_Feb-May, n_measurements) for a site_code."""
    recs = meas.get(site_code, [])
    spring = spring_records(recs)
    if not spring:
        return None, 0
    avg = statistics.mean(r["gwe"] for r in spring)
    return avg, len(spring)


def main() -> None:
    wells = json.loads(WELLS_JSON.read_text())
    wells_by_swn = {w["swn_or_name"]: w for w in wells}

    thr_current = json.loads(THR_CURRENT.read_text())
    thr_current_by_swn = {r["swn"]: r for r in thr_current}

    thr_2022 = json.loads(THR_2022.read_text())
    thr_2022_by_swn = {r["swn"]: r for r in thr_2022}

    meas = load_measurements()

    polys = json.loads(POLYS.read_text())

    # --- Step 1: AGWL for every 2022 RMS well, organized by zone ----------
    rms_2022_by_zone: dict[str, list[str]] = {}
    for w in wells:
        if w.get("is_2022_gwl_rms"):
            zone = w["mgmt_area_full"]
            rms_2022_by_zone.setdefault(zone, []).append(w["swn_or_name"])

    rms_2022_agwl: dict[str, dict] = {}  # swn -> {agwl, n, mt22, mo22, im22, delta_mt, ...}
    for zone, swns in rms_2022_by_zone.items():
        for swn in swns:
            w = wells_by_swn[swn]
            t22 = thr_2022_by_swn.get(swn)
            agwl, n = agwl_for_site(meas, w["site_code"])
            gse = w.get("gse")
            rms_2022_agwl[swn] = {
                "zone": zone,
                "agwl": agwl,
                "gse": gse,
                "agwl_dbs": (gse - agwl) if (agwl is not None and gse is not None) else None,
                "n_spring": n,
                "mt22": t22["mt_ft"] if t22 else None,
                "mo22": t22["mo_ft"] if t22 else None,
                "im22": t22["im_2027_ft"] if t22 else None,
                "mt22_dbs": (gse - t22["mt_ft"]) if (t22 and gse is not None) else None,
                "mo22_dbs": (gse - t22["mo_ft"]) if (t22 and gse is not None) else None,
                "im22_dbs": (gse - t22["im_2027_ft"]) if (t22 and gse is not None) else None,
            }
            r = rms_2022_agwl[swn]
            r["delta_mt"] = (agwl - r["mt22"]) if (agwl is not None and r["mt22"] is not None) else None
            r["delta_mo"] = (agwl - r["mo22"]) if (agwl is not None and r["mo22"] is not None) else None
            r["delta_im"] = (agwl - r["im22"]) if (agwl is not None and r["im22"] is not None) else None

    # --- Step 2: zone-level average offsets -------------------------------
    zone_offsets: dict[str, dict] = {}
    for zone, swns in rms_2022_by_zone.items():
        deltas_mt = [rms_2022_agwl[s]["delta_mt"] for s in swns if rms_2022_agwl[s]["delta_mt"] is not None]
        deltas_mo = [rms_2022_agwl[s]["delta_mo"] for s in swns if rms_2022_agwl[s]["delta_mo"] is not None]
        deltas_im = [rms_2022_agwl[s]["delta_im"] for s in swns if rms_2022_agwl[s]["delta_im"] is not None]
        agwl_dbs_vals = [rms_2022_agwl[s]["agwl_dbs"] for s in swns if rms_2022_agwl[s]["agwl_dbs"] is not None]
        zone_offsets[zone] = {
            "n_wells": len(swns),
            "n_mt": len(deltas_mt),
            "ave_delta_mt": statistics.mean(deltas_mt) if deltas_mt else None,
            "ave_delta_mo": statistics.mean(deltas_mo) if deltas_mo else None,
            "ave_delta_im": statistics.mean(deltas_im) if deltas_im else None,
            "ave_agwl_dbs": statistics.mean(agwl_dbs_vals) if agwl_dbs_vals else None,
        }

    # --- Step 3: apply Christina's formula to each "2022 Mirror" well -----
    new_rms_results: list[dict] = []
    for tc in thr_current:
        if tc["source"] != "2022 Mirror":
            continue
        swn = tc["swn"]
        w = wells_by_swn[swn]
        agwl_new, n_new = agwl_for_site(meas, w["site_code"])
        gse_new = w.get("gse")
        zone = w.get("rms_mgmt_area") or w["mgmt_area_full"]
        zo = zone_offsets.get(zone)
        if agwl_new is None or zo is None or zo["ave_delta_mt"] is None:
            christina_mt = christina_mo = christina_im = None
        else:
            christina_mt = round(agwl_new - zo["ave_delta_mt"])
            christina_mo = round(agwl_new - zo["ave_delta_mo"]) if zo["ave_delta_mo"] is not None else None
            christina_im = round(agwl_new - zo["ave_delta_im"]) if zo["ave_delta_im"] is not None else None

        def to_dbs(x):
            return (gse_new - x) if (x is not None and gse_new is not None) else None

        new_rms_results.append({
            "swn": swn,
            "zone_geographic": w["mgmt_area_full"],
            "zone_rms": zone,
            "gse": gse_new,
            "agwl_new": agwl_new,
            "agwl_new_dbs": to_dbs(agwl_new),
            "n_spring": n_new,
            "current_mt": tc["mt_ft"],
            "current_mo": tc["mo_ft"],
            "current_im": tc["im_2027_ft"],
            "current_mt_dbs": to_dbs(tc["mt_ft"]),
            "current_mo_dbs": to_dbs(tc["mo_ft"]),
            "current_im_dbs": to_dbs(tc["im_2027_ft"]),
            "christina_mt": christina_mt,
            "christina_mo": christina_mo,
            "christina_im": christina_im,
            "christina_mt_dbs": to_dbs(christina_mt),
            "christina_mo_dbs": to_dbs(christina_mo),
            "christina_im_dbs": to_dbs(christina_im),
        })

    # --- Step 4: dry-count comparison -------------------------------------
    # Build polygon -> primary RMS swn map. For aggregates (Chico), use the
    # first primary in the list. For single-RMS cells, use rms_well_swn.
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

    # Build MT lookups: swn -> MT, under each methodology
    mt_current: dict[str, int] = {r["swn"]: r["mt_ft"] for r in thr_current}
    mt_christina: dict[str, int] = dict(mt_current)  # carryovers unchanged
    for r in new_rms_results:
        if r["christina_mt"] is not None:
            mt_christina[r["swn"]] = r["christina_mt"]

    # Load domestic wells
    dom = json.loads(DOMESTIC.read_text())
    active_dom = [
        d for d in dom
        if d.get("include") == 1
        and d.get("well_bottom_amsl") is not None
        and d.get("our_polygon")
        and d.get("lat") is not None
        and d.get("lon") is not None
    ]

    # Count dry under 4 scenarios, per polygon
    per_poly: dict[str, dict] = {}
    for d in active_dom:
        zl = d["our_polygon"]
        rms_swn = polygon_primary.get(zl)
        if rms_swn is None:
            continue
        mt_c = mt_current.get(rms_swn)
        mt_x = mt_christina.get(rms_swn)
        if mt_c is None or mt_x is None:
            continue
        b = d["well_bottom_amsl"]
        primary_gse = wells_by_swn.get(rms_swn, {}).get("gse")
        per_poly.setdefault(zl, {
            "rms": rms_swn,
            "rms_gse": primary_gse,
            "mt_current": mt_c,
            "mt_christina": mt_x,
            "mt_current_dbs": (primary_gse - mt_c) if primary_gse is not None else None,
            "mt_christina_dbs": (primary_gse - mt_x) if primary_gse is not None else None,
            "n_total": 0,
            "dry_A": 0,  # current MT, bottom > MT
            "dry_B": 0,  # current MT, bottom + 10 > MT
            "dry_C": 0,  # christina MT, bottom > MT
            "dry_D": 0,  # christina MT, bottom + 10 > MT
            "dry_E": 0,  # current MT + elev correction, bottom > eff_MT
            "dry_F": 0,  # christina MT + elev correction, bottom > eff_MT
            "dry_G": 0,  # christina MT + elev correction + LWA +10
            "dry_H": 0,  # current MT + elev correction + LWA +10
        })
        rec = per_poly[zl]
        rec["n_total"] += 1
        # One-sided elev correction (cosmo): raise MT for uphill wells, leave
        # downhill wells with full RMS protection.
        well_gse = d.get("local_gse")
        if well_gse is not None and primary_gse is not None:
            elev_adj = max(0, well_gse - primary_gse)
        else:
            elev_adj = 0
        eff_mt_c = mt_c + elev_adj
        eff_mt_x = mt_x + elev_adj
        if b > mt_c:
            rec["dry_A"] += 1
        if b + LWA_PAD_FT > mt_c:
            rec["dry_B"] += 1
        if b > mt_x:
            rec["dry_C"] += 1
        if b + LWA_PAD_FT > mt_x:
            rec["dry_D"] += 1
        if b > eff_mt_c:
            rec["dry_E"] += 1
        if b > eff_mt_x:
            rec["dry_F"] += 1
        if b + LWA_PAD_FT > eff_mt_x:
            rec["dry_G"] += 1
        if b + LWA_PAD_FT > eff_mt_c:
            rec["dry_H"] += 1

    tot = {k: sum(p[k] for p in per_poly.values()) for k in ("n_total", "dry_A", "dry_B", "dry_C", "dry_D", "dry_E", "dry_F", "dry_G", "dry_H")}

    # --- Step 5: write report ---------------------------------------------
    lines: list[str] = []
    lines.append("# Christina Buck MT methodology — comparison report\n")
    lines.append(f"Generated by `scripts/compare_christina_mt.py`. Read-only; no dashboard changes.\n")
    lines.append("## 1. Zone offsets derived from 2022 RMS wells\n")
    lines.append(
        "Values shown in **DBS (depth below ground surface, ft)** — so larger = deeper. "
        "AGWL = average Feb-May depth-to-water over the full QA-Good DWR timeseries "
        "(DWR's standard \"spring\" window). Zone Δ values are the gaps from AGWL down to "
        "the 2022 GSP MT/MO/IM lines, averaged across the 2022 RMS wells in the zone.\n"
    )
    lines.append("| Zone | n RMS | avg AGWL (DBS) | AveΔGWL→MT | AveΔGWL→MO | AveΔGWL→IM |")
    lines.append("|---|---|---|---|---|---|")
    for zone in ["01-Vina-North", "02-Vina-Chico", "03-Vina-South"]:
        zo = zone_offsets.get(zone)
        if not zo:
            continue
        lines.append(
            f"| {zone} | {zo['n_wells']} | "
            f"{zo['ave_agwl_dbs']:.2f} | {zo['ave_delta_mt']:.2f} | "
            f"{zo['ave_delta_mo']:.2f} | {zo['ave_delta_im']:.2f} |"
        )
    lines.append("")
    lines.append("Current methodology uses an *all-time-min* anchor with fixed regional buffers: "
                 "N=69.55, S=57.60, Chico=27.93 ft. Christina's anchors on AGWL with the offsets above.\n")

    lines.append("### 2022 RMS detail (DBS — depth below ground surface, ft)\n")
    lines.append("All values are depths below each well's own ground surface. "
                 "AGWL = avg Feb-May depth to water; MT/MO/IM = 2022 GSP-adopted depth-to-undesirable thresholds.\n")
    lines.append("| Well | Zone | AGWL | n_spr | MT_2022 | ΔGWL→MT | MO_2022 | ΔGWL→MO | IM_2022 | ΔGWL→IM |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for swn in sorted(rms_2022_agwl, key=lambda s: (rms_2022_agwl[s]["zone"], s)):
        r = rms_2022_agwl[swn]
        agwl_s = f"{r['agwl_dbs']:.1f}" if r['agwl_dbs'] is not None else "—"
        mt_s = f"{r['mt22_dbs']:.0f}" if r['mt22_dbs'] is not None else "—"
        mo_s = f"{r['mo22_dbs']:.0f}" if r['mo22_dbs'] is not None else "—"
        im_s = f"{r['im22_dbs']:.0f}" if r['im22_dbs'] is not None else "—"
        dmt = f"{r['delta_mt']:.1f}" if r['delta_mt'] is not None else "—"
        dmo = f"{r['delta_mo']:.1f}" if r['delta_mo'] is not None else "—"
        dim = f"{r['delta_im']:.1f}" if r['delta_im'] is not None else "—"
        lines.append(
            f"| {swn} | {r['zone']} | {agwl_s} | {r['n_spring']} | {mt_s} | {dmt} | "
            f"{mo_s} | {dmo} | {im_s} | {dim} |"
        )
    lines.append("")

    lines.append("## 2. Per-well MT/MO/IM comparison — 17 \"2022 Mirror\" wells (DBS, ft)\n")
    lines.append("All depths below ground. Δ MT shown in DBS — *positive Δ means a deeper (more permissive) MT* "
                 "(Christina sets MT further below ground than current). Negative Δ means shallower MT (more conservative — more domestic wells at risk).\n")
    lines.append("| Well | Zone | GSE (msl) | AGWL | n_spr | MT cur → Christina | Δ MT | MO cur → Christina | IM cur → Christina |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in sorted(new_rms_results, key=lambda x: (x["zone_rms"], x["swn"])):
        agwl_s = f"{r['agwl_new_dbs']:.1f}" if r['agwl_new_dbs'] is not None else "—"
        gse_s = f"{r['gse']:.1f}" if r['gse'] is not None else "—"
        mt_cur_s = f"{r['current_mt_dbs']:.0f}" if r['current_mt_dbs'] is not None else "—"
        mt_chr_s = f"{r['christina_mt_dbs']:.0f}" if r['christina_mt_dbs'] is not None else "—"
        mo_cur_s = f"{r['current_mo_dbs']:.0f}" if r['current_mo_dbs'] is not None else "—"
        mo_chr_s = f"{r['christina_mo_dbs']:.0f}" if r['christina_mo_dbs'] is not None else "—"
        im_cur_s = f"{r['current_im_dbs']:.0f}" if r['current_im_dbs'] is not None else "—"
        im_chr_s = f"{r['christina_im_dbs']:.0f}" if r['christina_im_dbs'] is not None else "—"
        if r["christina_mt_dbs"] is not None and r["current_mt_dbs"] is not None:
            d_mt = r["christina_mt_dbs"] - r["current_mt_dbs"]
            d_mt_s = f"{d_mt:+.0f}"
        else:
            d_mt_s = "—"
        z_disp = f"{r['zone_geographic']}"
        if r["zone_geographic"] != r["zone_rms"]:
            z_disp += f" → {r['zone_rms']}"
        lines.append(
            f"| {r['swn']} | {z_disp} | {gse_s} | {agwl_s} | {r['n_spring']} | "
            f"{mt_cur_s} → {mt_chr_s} | {d_mt_s} | "
            f"{mo_cur_s} → {mo_chr_s} | {im_cur_s} → {im_chr_s} |"
        )
    lines.append("")

    lines.append("## 3. Domestic-well dry counts\n")
    lines.append(
        f"Universe: {len(active_dom):,} cosmo wells with include=1, valid "
        "well_bottom_amsl, and a containing 2027 polygon. LWA's +10 ft "
        "well-pump allowance applied where indicated.\n"
    )
    lines.append("| Scenario | MT method | Dry rule | Dry wells | % of universe |")
    lines.append("|---|---|---|---|---|")
    n = tot["n_total"]
    lines.append(f"| A (baseline) | Current (2022-Mirror buffer) | bottom > MT | **{tot['dry_A']:,}** | {tot['dry_A']/n*100:.1f}% |")
    lines.append(f"| B (LWA-comparable, current MT) | Current (2022-Mirror buffer) | bottom + 10 > MT | **{tot['dry_B']:,}** | {tot['dry_B']/n*100:.1f}% |")
    lines.append(f"| C (Christina, our rule) | Christina (AGWL Mirror) | bottom > MT | **{tot['dry_C']:,}** | {tot['dry_C']/n*100:.1f}% |")
    lines.append(f"| D (Christina + LWA) | Christina (AGWL Mirror) | bottom + 10 > MT | **{tot['dry_D']:,}** | {tot['dry_D']/n*100:.1f}% |")
    lines.append(f"| E (current + elev correction) | Current (2022-Mirror buffer) | bottom > eff_MT | **{tot['dry_E']:,}** | {tot['dry_E']/n*100:.1f}% |")
    lines.append(f"| F (Christina + elev correction) | Christina (AGWL Mirror) | bottom > eff_MT | **{tot['dry_F']:,}** | {tot['dry_F']/n*100:.1f}% |")
    lines.append(f"| G (Christina + elev + LWA) | Christina (AGWL Mirror) | bottom + 10 > eff_MT | **{tot['dry_G']:,}** | {tot['dry_G']/n*100:.1f}% |")
    lines.append(f"| H (current + elev + LWA) | Current (2022-Mirror buffer) | bottom + 10 > eff_MT | **{tot['dry_H']:,}** | {tot['dry_H']/n*100:.1f}% |")
    lines.append("")
    lines.append(f"LWA's published number: 400 wells dry at 2022 GSP MTs with the +10 ft rule.\n")
    lines.append("Elev correction (one-sided, cosmo convention): `eff_MT = MT + max(0, well_local_gse - rms_gse)`. "
                 "Raises MT for uphill wells to reflect topography; leaves downhill wells with full basin protection.\n")

    lines.append("### Per-polygon dry counts — MT in DBS (sorted by current MT dry count, desc)\n")
    lines.append("MT values shown as depth below RMS-well surface (ft). Larger MT DBS = deeper threshold = more permissive.\n")
    lines.append("| Polygon | Primary RMS | n dom | MT cur DBS | MT Chr DBS | dry A | dry B | dry C | dry D | dry E | dry F |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for zl, p in sorted(per_poly.items(), key=lambda kv: -kv[1]["dry_A"]):
        mt_cur_dbs = f"{p['mt_current_dbs']:.0f}" if p['mt_current_dbs'] is not None else "—"
        mt_chr_dbs = f"{p['mt_christina_dbs']:.0f}" if p['mt_christina_dbs'] is not None else "—"
        lines.append(
            f"| {zl} | {p['rms']} | {p['n_total']} | "
            f"{mt_cur_dbs} | {mt_chr_dbs} | "
            f"{p['dry_A']} | {p['dry_B']} | {p['dry_C']} | {p['dry_D']} | {p['dry_E']} | {p['dry_F']} |"
        )
    lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines))

    # --- Step 6: stdout summary -------------------------------------------
    print("\n=== ZONE OFFSETS (DBS, ft below ground) ===")
    print(f"{'Zone':<18} {'n':>3} {'AGWL_DBS':>10} {'ΔMT':>8} {'ΔMO':>8} {'ΔIM':>8}")
    for zone in ["01-Vina-North", "02-Vina-Chico", "03-Vina-South"]:
        zo = zone_offsets.get(zone)
        if not zo:
            continue
        agwl_dbs_s = f"{zo['ave_agwl_dbs']:.2f}" if zo['ave_agwl_dbs'] is not None else "—"
        print(f"{zone:<18} {zo['n_wells']:>3} {agwl_dbs_s:>10} "
              f"{zo['ave_delta_mt']:>8.2f} {zo['ave_delta_mo']:>8.2f} {zo['ave_delta_im']:>8.2f}")

    print("\n=== NEW RMS WELLS: current MT → Christina MT (DBS, ft below ground) ===")
    print(f"{'Well':<18} {'zone':<14} {'AGWL':>7} {'MT cur':>7} {'MT Chr':>7} {'Δ':>6}")
    for r in sorted(new_rms_results, key=lambda x: (x["zone_rms"], x["swn"])):
        agwl_s = f"{r['agwl_new_dbs']:.1f}" if r['agwl_new_dbs'] is not None else "—"
        mt_cur_s = f"{r['current_mt_dbs']:.0f}" if r['current_mt_dbs'] is not None else "—"
        mt_chr_s = f"{r['christina_mt_dbs']:.0f}" if r['christina_mt_dbs'] is not None else "—"
        if r["christina_mt_dbs"] is not None and r["current_mt_dbs"] is not None:
            delta = r["christina_mt_dbs"] - r["current_mt_dbs"]
            delta_s = f"{delta:+.0f}"
        else:
            delta_s = "—"
        print(f"{r['swn']:<18} {r['zone_rms']:<14} {agwl_s:>7} "
              f"{mt_cur_s:>7} {mt_chr_s:>7} {delta_s:>6}")

    print("\n=== DRY COUNTS (universe = {:,}) ===".format(len(active_dom)))
    print(f"  A. current MT, bottom > MT:                       {tot['dry_A']:>4}  ({tot['dry_A']/n*100:.1f}%)")
    print(f"  B. current MT, bottom + 10 > MT:                  {tot['dry_B']:>4}  ({tot['dry_B']/n*100:.1f}%)")
    print(f"  C. Christina MT, bottom > MT:                     {tot['dry_C']:>4}  ({tot['dry_C']/n*100:.1f}%)")
    print(f"  D. Christina MT, bottom + 10 > MT:                {tot['dry_D']:>4}  ({tot['dry_D']/n*100:.1f}%)")
    print(f"  E. current MT + elev correction:                  {tot['dry_E']:>4}  ({tot['dry_E']/n*100:.1f}%)")
    print(f"  F. Christina MT + elev correction:                {tot['dry_F']:>4}  ({tot['dry_F']/n*100:.1f}%)")
    print(f"  G. Christina MT + elev correction + LWA +10:      {tot['dry_G']:>4}  ({tot['dry_G']/n*100:.1f}%)")
    print(f"  H. current MT + elev correction + LWA +10:        {tot['dry_H']:>4}  ({tot['dry_H']/n*100:.1f}%)")
    print(f"  LWA published baseline:                            400  (-/-%)")
    print(f"\nReport written to {OUT_MD}")


if __name__ == "__main__":
    main()
