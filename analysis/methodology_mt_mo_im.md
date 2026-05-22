# 2027 RMS Network — MT/MO/IM-2027 methodology

How the dashboard's MT, MO, and IM-2027 values were derived for the 26 wells in the Vina Subbasin's 2027 Representative Monitoring Site (RMS) network.

**Status:** adopted by Butte County Water Resources Conservation staff on 2026-05-21 for use in the AGUBC dashboard. Adopted MT/MO/IM in the 2022 Vina GSP remain in effect until the GSA formally updates them in the 2027 GSP cycle; the values described here are an internal working baseline for visualization and sensitivity analysis.

---

## Summary

The 26 RMS wells in the 2027 network fall into two groups:

| Group | n wells | Source of MT/MO/IM |
|---|---|---|
| 2022 GSP carryovers | 9 | Unchanged from the adopted 2022 Vina GSP |
| New RMS wells | 17 | **AGWL Mirror** — each well's Feb–April average groundwater level minus a per-zone offset calibrated against the 2022 GSP MT/MO/IM |

The AGWL Mirror methodology was proposed by Christina Buck (BCWRC) and selected over two alternatives after a side-by-side sensitivity comparison.

---

## The two paths

### 2022 GSP carryovers (9 wells)

Nine wells in the 2027 network were also RMS wells in the 2022 Vina GSP, or are nested-completion siblings of 2022 RMS wells at the same lat/lng:

- **North (5):** 22N01W05M001M, 23N01E07H001M, 23N01E33A001M, 23N01W36P001M, 23N02W25C001M
- **South (3):** 20N02E24C001M, 21N02E18C003M, 21N02E26E006M (inherits from `21N02E26E005M`, retired from the 2027 network)
- **Chico (1):** CWSCH01b

These wells keep their adopted 2022 GSP MT, MO, and IM-2027 values verbatim. Rendered with dashed threshold lines in §5.3 and labeled with the "GSP-adopted MT/MO" pill.

### New RMS wells (17 wells) — AGWL Mirror

The remaining 17 wells were not in the 2022 GSP RMS network, so they have no carry-over GSP values. The AGWL Mirror methodology produces MT/MO/IM for each by:

1. Computing the well's own **average Feb–April groundwater level** (AGWL) from the full QA-Good DWR record.
2. Subtracting a **per-zone offset** that captures the typical gap between AGWL and the GSP's adopted MT/MO/IM at the original 2022 RMS wells in the same management area.

Christina Buck's formula:

```
MT_new = AGWL_new − AveΔGWL_MT_zone
```

where `AveΔGWL_MT_zone = mean over 2022 RMS wells in zone of (AGWL_RMS − MT_2022_RMS)`. Same form applies to MO and IM-2027 using their respective zone offsets.

---

## Zone offsets (Feb–April, ft msl)

| Region | n 2022 RMS wells | avg AGWL | AveΔGWL→MT | AveΔGWL→MO | AveΔGWL→IM |
|---|---|---|---|---|---|
| North | 6 | 149.32 | 90.99 | 24.32 | 22.49 |
| Chico | 5 | 128.24 | 43.24 | 23.24 | 21.44 |
| South | 6 | 121.96 | 92.12 | 30.46 | 28.12 |

**Notes on the zone offsets:**

- **Sample selection.** All 17 designated 2022 GSP RMS wells contribute to their respective zone offsets, including the 4 CWSCH nested completions that share a single Chico pad for privacy. Each has a distinct DWR site_code and timeseries.
- **The Chico offset is computed but not applied.** No new RMS wells are assigned to the Chico zone in the 2027 network. The sole Chico carryover (CWSCH01b) keeps its 2022 GSP MT/MO/IM unchanged.
- **Zone keying for new wells.** Each new well's zone offset is determined by its NETWORK assignment (`rms_mgmt_area`), not its geographic location. Two wells that are RMS for the North network but physically inside Chico (`22N01E09B001M`, `22N01E20K001M`) use the North offsets, consistent with their role as North RMS wells.

---

## Why Feb–April? The variant comparison

Three definitions of the "average spring groundwater level" window were tested:

| Variant | Definition |
|---|---|
| **Feb–May** | Mean of QA-Good GWE readings in Feb, Mar, Apr, May across the full record (broadest spring window) |
| **Feb–April** | Same as Feb–May but excludes May readings, which tend to reflect evapotranspiration onset |
| **Highest March** | Per-year highest QA-Good March GWE, averaged across years with March data (peak-of-peak per year) |

The three variants produced very similar outcomes — headline dry-well counts within 9 wells of each other (430–438), and per-well MTs clustering within a few feet across variants.

Staff selected **Feb–April** on 2026-05-21 because:

- It excludes May readings, when the water table typically begins to decline as evapotranspiration picks up — capturing post-recharge / pre-pumping conditions more cleanly than Feb–May.
- It uses essentially the full Feb–April record (tens to thousands of measurements per well), giving statistically stable AGWL estimates.
- It handles all 5 Chico 2022 RMS wells in the zone offset calculation (the 4 CWSCH wells have Feb and Apr readings, just not March). Highest-March would drop Chico to n=1.
- The dry-well count is marginally lower than Feb–May (430 vs. 438) without sacrificing statistical robustness.

The full per-variant comparison — zone offsets, per-well MTs, dry-well counts under each variant with and without elevation correction — is in `analysis/agwl_window_comparison.md`.

### Why not Highest March?

The peak-based alternative — take the highest March GWE each year, then average those annual peaks — was considered and not adopted, primarily because:

- **Averaging reduces variance.** The standard error of a sample mean shrinks as √n. Feb–April uses tens to thousands of measurements per well; the per-year peak contributes one per year, sample size = number of years.
- **A per-year maximum is biased upward by construction.** Taking the max each year guarantees the result sits at or above the mean. Anchoring on "typical condition" rather than "best moment of best moment" is closer to the GSA's operational framing.
- **Data-completeness matters.** The 4 CWSCH wells in Chico have zero March readings in DWR's record (they do have Feb and Apr readings). Feb–April uses them; Highest-March drops them.

None of these are universal reasons to prefer averaging — peak-based estimates have their own uses in other contexts — but for setting MT/MO/IM mirrors on behalf of a regulatory framework, the averaging approach gave staff a more stable, more defensible anchor.

---

## How to read the dry-well count

The dashboard's §5.3 MT-sensitivity widget reports how many domestic wells in each polygon would have their bottom above the MT line if the water table dropped to MT everywhere in the basin. **This is a sensitivity analysis, not a forecast.** Three reasons it overstates real impact:

1. **The subbasin manages to MO, not MT.** Water Year 2025 groundwater was ~68 ft above MT and ~18 ft above MO (Vina GSA Annual Report). MT is a hard floor that triggers undesirable-result findings, not an operational target.

2. **Observed dry wells through two drought events: ~35.** DWR's Dry Well Reporting System recorded approximately 35 dry well reports in the Vina Subbasin from January 1, 2014 through December 31, 2025 — a period that included the 2012-16 and 2020-22 droughts. The observed count is an order of magnitude below any theoretical-at-MT scenario shown in the widget.

3. **The MT scenario assumes uniform basin-wide drawdown.** Real drawdown is spatially uneven and rebounds between drought cycles; sustained groundwater at MT across the entire basin is not what the GSP envisions managing toward.

The right way to read §5.3's dry-well numbers is as a comparison of methodology and elevation-correction choices, not as predictions. The intent of including the widget is to surface the relative differences between methodologies and elevation-correction toggles, not to suggest that any number represents a likely outcome.

---

## Caveats

- **AGWL reflects the observed Feb–April record.** Wells with short records or sparse spring monitoring may understate or overstate typical conditions; estimates from such wells should be considered conservative.
- **Zone offsets are descriptive statistics, not margins of safety or forward projections.** They do not account for drought severity, climate change, or pumping trajectories. They are a backward-looking calibration of how the GSA's adopted 2022 MT/MO/IM relate to typical spring groundwater levels at the 2022 RMS wells.
- **No traceable derivation document for the 2022 GSP MT values.** AGUBC, Butte County, and Vina GSA staff have searched for the methodology memo that drove the original 2022 MT/MO/IM values; no documentation has surfaced. The AGWL Mirror is the most faithful empirical reconstruction available given that constraint.
- **The Mirror is NOT a request for GSA approval.** Adopted MT/MO/IM remain the 2022 GSP values until the GSA formally updates them in the 2027 GSP cycle. The Mirror exists solely to give the dashboard a complete set of comparison lines so every polygon's hydrograph can be evaluated in the same visual framework.

---

## Reproducibility

All values in this memo can be regenerated from the public DWR CKAN periodic groundwater measurements feed (resource `bfa9f262-24a1-45bd-8dc8-138bc8107266`) and the 2027 network configuration in `data/wells_resolved.json`:

```bash
python3 scripts/compute_thresholds.py          # -> data/thresholds.json
python3 scripts/build_wells_js.py              # -> js/wells-data.js
python3 scripts/update_workbook_thresholds.py  # -> updates BC Network 2026 v8.xlsx
```

Variant comparison (Feb–May, Feb–April, Highest March):

```bash
python3 scripts/compare_agwl_windows.py        # -> analysis/agwl_window_comparison.md
```

---

## References

- `analysis/agwl_window_comparison.md` — full three-variant sensitivity comparison
- `analysis/christina_methodology_summary.md` — original summary prepared for Christina Buck, May 2026
- `analysis/christina_mt_comparison.md` — earlier detailed AGWL Mirror analysis (pre-variant comparison)
- `scripts/compute_thresholds.py` — production threshold derivation
- `scripts/compare_agwl_windows.py` — variant comparison script
- Vina GSA 2022 Groundwater Sustainability Plan and subsequent Annual Reports
- DWR CKAN Periodic Groundwater Level Measurements, resource bfa9f262-24a1-45bd-8dc8-138bc8107266
