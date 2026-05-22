# AGWL Mirror methodology — comparison & sensitivity summary

Prepared for Christina Buck, Butte County Water Resources Conservation, May 2026.

---

## Headline

Your AGWL Mirror methodology, applied to the 17 new ("2022 Mirror") wells in the 2027 RMS network, lowers the theoretical count of domestic wells that would go dry at MT from **511** under our current buffer methodology to **438** — a **14% reduction**. With the dashboard's one-sided elevation correction applied (raises a domestic well's effective MT when it sits uphill of its RMS), the count drops further to **356**. The 9 carryover wells (5 N, 3 S, 1 Chico = CWSCH01b) retain their adopted 2022 GSP MT/MO/IM unchanged.

**Recommendation:** adopt the AGWL Mirror methodology for the 17 new RMS wells.

## How to read the dry-well count

This is a sensitivity analysis, not a forecast. It answers a single question — *"if groundwater dropped to MT everywhere in the basin, how many domestic wells would have their bottom above the water table?"* — and we don't intend to build mitigation plans against that worst-case theoretical. Three reasons it overstates real impact:

1. **The subbasin manages to MO, not MT.** WY 2025 groundwater was ~68 ft above MT and ~18 ft above MO (Vina GSA Annual Report). MT is a hard floor that triggers undesirable-result findings, not an operational target.

2. **Observed dry wells through two drought events: ~35.** The DWR Dry Well Reporting System recorded approximately 35 dry well reports in the Vina Subbasin from January 1, 2014 through December 31, 2025 — a period that included the 2012-16 and 2020-22 droughts. The observed count is an order of magnitude below any theoretical-at-MT scenario.

3. **The MT scenario assumes uniform basin-wide drawdown to MT.** Real drawdown is spatially uneven and rebounds between drought cycles. Sustained groundwater at MT across the entire basin is not what the GSP envisions managing toward.

So the right way to read the numbers below is as a comparison of methodologies, not as predictions. The 511 → 438 (or 428 → 356) shift tells us your methodology produces a more permissive MT line in the places where domestic wells cluster — which is a defensible improvement on its own, independent of whether either number is operationally meaningful.

## Methodology applied

For each well, we computed **AGWL** = average Feb–May groundwater elevation over its full QA-Good DWR timeseries (CKAN resource bfa9f262-24a1-45bd-8dc8-138bc8107266). For each 2022 RMS well we calculated `ΔGWL→MT = AGWL_RMS − MT_2022_RMS`, then averaged within each management area to get a zone offset. For each new RMS well, `MT_new = AGWL_well − AveΔGWL_MT_zone`. Same approach for MO and IM, with their own zone offsets.

Zone assignment uses each well's network designation (`rms_mgmt_area`), not its geographic location — so the two North-network RMS wells that physically sit in Chico (22N01E09B001M, 22N01E20K001M) receive the North offset, consistent with their role.

## Zone offsets derived from 2022 RMS (DBS = depth below ground, ft)

| Zone | n RMS | avg AGWL DBS | ΔGWL→MT | ΔGWL→MO | ΔGWL→IM |
|---|---|---|---|---|---|
| North | 6 | 50.4 | 90.5 | 23.9 | 22.0 |
| Chico | 5 | 89.4 | 43.1 | 23.1 | 21.3 |
| South | 6 | 33.3 | 91.7 | 30.0 | 27.7 |

The Chico offset uses all 5 historical 2022 RMS wells (4 CWSCH + 22N01E28J003M). Distinct site_codes (CWSCH wells share a map coordinate for privacy but have separate DWR timeseries). The Chico offset is computed but is not applied to any well in the 2027 network — the only Chico RMS is CWSCH01b, which is a carryover.

## MT shifts (Christina vs current) — 17 new RMS wells, DBS

| Zone | n | avg Δ MT DBS | direction |
|---|---|---|---|
| North | 8 | −8 ft | shallower MT (more protective) |
| South | 9 | +2 ft | mixed; small net deeper |

Biggest North shifts: 22N01E20K001M (−20), 23N01E29P002M (−14), 23N01W09E001M (−14). South is mixed: 21N01E13L004M (−17) and 21N01E27D001M (−8) shallower; 21N03E32B001M (+26) and 21N02E32E001M (+11) deeper.

Most of the dry-well savings concentrate in two North polygons: 23N01E29P002M (182 → 134 dry wells, −48) and 22N01E20K001M (38 → 9 dry wells, −29). Together these account for ~77 of the 73 basin-wide savings (other polygons have small offsetting changes).

## Dry-well sensitivity table

Universe: 1,253 cosmo active domestic wells (include=1, valid `well_bottom_amsl`, within a 2027 polygon). Dry rule: `well_bottom > MT`.

| Methodology | Dry at MT | Dry at MT (elev-corrected) |
|---|---|---|
| Current 2022-Mirror buffer | 511 (40.8%) | 428 (34.2%) |
| **Christina AGWL Mirror** | **438 (35.0%)** | **356 (28.4%)** |
| Δ vs current | −73 (−14%) | −72 (−17%) |

The elevation correction is one-sided: `eff_MT = MT + max(0, well_local_gse − rms_gse)`. It raises the effective MT for domestic wells uphill of their RMS (since the water table follows topography) and leaves downhill wells with the full basin MT.

## Why AGWL Mirror is a better methodology, independent of the dry-well count

- **Statistically more stable** than our current approach, which anchors on each well's single observed all-time minimum. AGWL averages over the full Feb–May record, reducing sensitivity to a single dry-year reading.
- **Directly tied to the GSP's MT/MO/IM concept** — the zone offsets are calibrated against the adopted 2022 GSP thresholds, so the new wells inherit the same MT/MO/IM logic the GSA already adopted.
- **Transparent and reproducible** — `AGWL − offset` is a single subtraction and easy to explain to ag stakeholders and the SHAC.

## What we'd appreciate confirming with you

1. **Spring window**: we used DWR's Feb–May convention. Want us to also run a March-only variant for comparison?
2. **MO and IM**: we extended your formula to MO and IM with parallel zone offsets (your email covered MT explicitly). Confirm that's the intent?
3. **Chico n=5**: confirm using all 4 CWSCH wells + 22N01E28J003M (distinct site_codes) is acceptable for the Chico offset calculation — vs. the n=1 our current methodology used after excluding CWSCH as nested completions.

---

*Source script: `scripts/compare_christina_mt.py`. Detailed per-well and per-polygon tables: `analysis/christina_mt_comparison.md`. Both are reproducible from the public DWR CKAN feed and the 2027 network configuration.*
