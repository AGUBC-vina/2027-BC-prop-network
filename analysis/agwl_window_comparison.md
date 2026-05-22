# AGWL Mirror — spring-window sensitivity analysis

> **Decision (2026-05-21):** Butte County Water Resources Conservation staff selected the **Feb–April** variant for the 2027 RMS network. Adopted in `data/thresholds.json` and live in the dashboard at the same date. See `analysis/methodology_mt_mo_im.md` for the standalone methodology memo.

Three definitions of "average spring groundwater level" (AGWL), all applied within Christina Buck's Mirror methodology, compared side-by-side. The methodology itself is unchanged across variants — only how we compute AGWL for each well changes. Carryover wells (9 with adopted 2022 GSP MT/MO/IM) are unchanged in every variant; only the 17 new RMS wells (added to the 2027 network without 2022 GSP-adopted thresholds) are affected.

---

## How to read the dry-well count

This is a sensitivity analysis, not a forecast. It answers a single question — *"if groundwater dropped to MT everywhere in the basin, how many domestic wells would have their bottom above the water table?"* — and we don't intend to build mitigation plans against that worst-case theoretical. Three reasons it overstates real impact:

1. **The subbasin manages to MO, not MT.** WY 2025 groundwater was ~68 ft above MT and ~18 ft above MO (Vina GSA Annual Report). MT is a hard floor that triggers undesirable-result findings, not an operational target.

2. **Observed dry wells through two drought events: ~35.** The DWR Dry Well Reporting System recorded approximately 35 dry well reports in the Vina Subbasin from January 1, 2014 through December 31, 2025 — a period that included the 2012-16 and 2020-22 droughts. The observed count is an order of magnitude below any theoretical-at-MT scenario.

3. **The MT scenario assumes uniform basin-wide drawdown to MT.** Real drawdown is spatially uneven and rebounds between drought cycles. Sustained groundwater at MT across the entire basin is not what the GSP envisions managing toward.

The right way to read the variant numbers below is as a *comparison of methodology choices*, not as predictions. LWA's +10 ft well-pump allowance is intentionally not applied — we use the same dry rule the 2022 GSP used (`well_bottom > MT`).

---

## The three variants

Each variant changes only how AGWL is computed per well. Christina's formula is otherwise identical: `MT_new = AGWL_new − AveΔGWL_MT_zone`, where the zone offset is computed from the 2022 RMS wells under the same definition.

### Variant 1 — Feb–May average

For each well, AGWL = mean of every QA-Good groundwater elevation reading from DWR's record that falls in February, March, April, or May, regardless of year.

- **Sample size per well**: highest of the three variants. Each well in the 2022 RMS contributes 38 to 1,568 individual measurements; new wells generally contribute fewer but still tens to hundreds.
- **What it captures**: typical spring conditions averaged across the full record, including both early-spring (recharge-influenced) and late-spring (pre-summer drawdown) readings.

### Variant 2 — Feb–April average

For each well, AGWL = mean of every QA-Good GWE reading in February, March, or April. Same as Feb–May but excludes May readings.

- **Sample size per well**: slightly smaller than Feb–May (drops ~25% of the months).
- **What it captures**: spring conditions weighted slightly more toward the post-recharge / pre-pumping window. May readings tend to be lower as evapotranspiration picks up, so excluding May raises the average somewhat.

### Variant 3 — Highest March, averaged across years

For each well, walk through every year in the record. In each year, find all QA-Good March GWE readings; take the *highest* one. Then average those annual peaks across all years with March data.

- **Sample size per well**: equals the number of years with at least one March reading. For most 2022 RMS wells this is 10 to 55 years. For wells with no March data in DWR's record (notably the 4 CWSCH wells in Chico), this variant cannot be computed.
- **What it captures**: the per-year peak in March, averaged. Not an average across all measurements — by construction, only the year-by-year maximum.

### Note on a citation I previously made

In an earlier draft I described Feb–May as "DWR's standard spring convention." On review, I cannot point to a specific DWR publication that fixes Feb–May as *the* spring window. DWR's groundwater monitoring guidance under SGMA and CASGEM requires semiannual measurements (one spring, one fall) but the precise month range varies across documents. Different Vina GSA reports and DWR Bulletin 118 materials have used windows including Feb–Apr, Mar–Apr, and Feb–May. **Worth confirming the exact citation with Christina or against DWR documentation before publishing externally.**

---

## A statistical note on averaging vs. peak-of-peak

The Feb–May and Feb–April variants are averages over many measurements. The Highest-March variant is an average of single-point per-year peaks. The two approaches have different statistical properties worth being explicit about:

- **Averaging many measurements reduces variance.** The standard error of a sample mean shrinks as √n. Pulling 100 measurements gives a more stable estimate than pulling 10. Both Feb–May and Feb–April use the full record of qualifying measurements, so each well's AGWL is anchored on a large sample.

- **A per-year maximum is a single value per year.** "Highest March" picks one observation per year and averages those. The sample size is the number of years, not the number of measurements. This makes Highest-March more sensitive to (a) outlier years and (b) wells with short records.

- **A per-year maximum is biased upward by construction.** Taking the max each year guarantees the result sits at or above the mean. Whether that matters depends on interpretation — if the intent is to anchor on "typical recharge-period peak," it's faithful; if the intent is to anchor on "typical condition," an average is closer.

- **Data-completeness matters.** A well with March readings in only 4 of 30 years can still contribute under Highest-March (n_years=4), but the resulting estimate is fragile. Under Feb–May or Feb–April, that same well's spring readings (regardless of which month) would all contribute to a more stable average.

None of these properties are reasons to pick or rule out any variant — they're characteristics to weigh against the analytical objective. Highest-March is well-suited to anchoring on a clear seasonal peak; Feb–May and Feb–April are well-suited to anchoring on average spring conditions.

---

## Headline comparison

Universe: **1,253** cosmo active domestic wells (include=1, valid `well_bottom_amsl`, within a 2027 polygon). Dry rule: `well_bottom > MT`. "Elev-corrected" applies the one-sided dashboard correction `eff_MT = MT + max(0, well_local_gse − rms_gse)`.

| Variant | Dry at MT | Dry at MT (elev-corrected) |
|---|---|---|
| Feb–May | 438 (35.0%) | 356 (28.4%) |
| Feb–April | 430 (34.3%) | 349 (27.9%) |
| Highest March | 430 (34.3%) | 349 (27.9%) |

Feb–April and Highest March happen to produce the same headline dry-well count (430), despite computing AGWL very differently. The per-well MT values differ slightly between them; the totals coincide because the differences offset across polygons.

## Zone offsets (DBS, ft) under each variant

### 01-Vina-North (n=6 RMS wells under every variant)

| Variant | avg AGWL DBS | ΔGWL→MT | ΔGWL→MO | ΔGWL→IM |
|---|---|---|---|---|
| Feb–May | 50.4 | 90.5 | 23.9 | 22.0 |
| Feb–April | 49.9 | 91.0 | 24.3 | 22.5 |
| Highest March | 49.6 | 91.3 | 24.6 | 22.8 |

### 02-Vina-Chico

| Variant | n RMS wells | avg AGWL DBS | ΔGWL→MT | ΔGWL→MO | ΔGWL→IM |
|---|---|---|---|---|---|
| Feb–May | 5 | 89.4 | 43.1 | 23.1 | 21.3 |
| Feb–April | 5 | 89.2 | 43.2 | 23.2 | 21.4 |
| Highest March | 1 | 31.7 | 61.6 | 35.6 | 33.6 |

The Chico Highest-March row uses only 1 of the 5 Chico 2022 RMS wells. The 4 CWSCH wells have zero March measurements in DWR's record (they have Feb, Apr, and May readings, but not March). Under Feb–May and Feb–April, all 5 Chico wells contribute via their non-March readings; under Highest March, only 22N01E28J003M contributes.

The Chico zone offset is computed but is not applied to any well in the 2027 network — Chico has no new RMS wells, and the 2 Chico-located wells that are RMS for the North network use the North offset.

### 03-Vina-South (n=6 RMS wells under every variant)

| Variant | avg AGWL DBS | ΔGWL→MT | ΔGWL→MO | ΔGWL→IM |
|---|---|---|---|---|
| Feb–May | 33.3 | 91.7 | 30.0 | 27.7 |
| Feb–April | 32.9 | 92.1 | 30.5 | 28.1 |
| Highest March | 31.8 | 93.2 | 31.5 | 29.2 |

## Per-well MT (DBS, ft) — 17 new RMS wells

| Well | Zone | Feb–May | Feb–April | Highest March |
|---|---|---|---|---|
| 22N01E09B001M | 01-Vina-North | 132 | 132 | 131 |
| 22N01E20K001M | 01-Vina-North | 119 | 120 | 121 |
| 23N01E29P002M | 01-Vina-North | 145 | 144 | 144 |
| 23N01W09E001M | 01-Vina-North | 115 | 115 | 115 |
| 23N01W10M001M | 01-Vina-North | 116 | 116 | 114 |
| 23N01W14R002M | 01-Vina-North | 125 | 125 | 126 |
| 23N01W27L001M | 01-Vina-North | 108 | 107 | 107 |
| 23N01W28M004M | 01-Vina-North | 108 | 108 | 106 |
| 20N01E02H003M | 03-Vina-South | 121 | 121 | 120 |
| 20N02E09G001M | 03-Vina-South | 124 | 124 | 122 |
| 20N03E33L001M | 03-Vina-South | 127 | 125 | 125 |
| 21N01E10B003M | 03-Vina-South | 141 | 140 | 139 |
| 21N01E13L004M | 03-Vina-South | 162 | 159 | 156 |
| 21N01E25K001M | 03-Vina-South | 133 | 133 | 133 |
| 21N01E27D001M | 03-Vina-South | 121 | 120 | 121 |
| 21N02E32E001M | 03-Vina-South | 132 | 132 | 132 |
| 21N03E32B001M | 03-Vina-South | 105 | 105 | 107 |

Per-well MTs differ across variants by 0–6 feet. Most wells move 0–2 feet between variants; the largest single-well swing is 21N01E13L004M (162 / 159 / 156, a 6-ft range).

## Average MT depth across the 17 new RMS wells (DBS, ft)

| Zone | n new RMS | Feb–May | Feb–April | Highest March |
|---|---|---|---|---|
| 01-Vina-North | 8 | 121.3 | 121.1 | 120.8 |
| 03-Vina-South | 9 | 129.8 | 129.0 | 128.6 |

A higher number means MT sits deeper below the surface. Across all three variants the differences in zone-averaged MT depth are within 1.3 ft.

## Summary

The three variants produce very similar outcomes:

- Headline dry-well count ranges from 430 to 438 across variants (348 to 356 with elev correction).
- Per-well MTs cluster within a few feet across variants.
- Zone offsets shift by less than 3 ft as the window narrows from Feb–May to Feb–April to Highest March.
- Feb–April and Highest March happen to give the same headline dry count (430), arrived at via different per-well MT shifts that offset.

---

*Source script: `scripts/compare_agwl_windows.py`. All numbers reproducible from the public DWR CKAN periodic groundwater measurements feed (resource bfa9f262-24a1-45bd-8dc8-138bc8107266) and the 2027 network configuration. Carryover wells (9) keep their adopted 2022 GSP MT/MO/IM under every variant.*
