# Project Notes — What We Did

A working-notes file recording **what was built, why, and how** for the
Vina Subbasin 2027 RMS Network Dashboard (28 Voronoi polygons, hydrograph
+ representativeness analysis, MT/MO/IM thresholds). The README is the
audience-facing methodology document; this file is the project history.

---

## Goal

Build a static, GitHub-Pages-deployable dashboard for the 2027 Vina
Representative Monitoring Site (RMS) network, modeled on the
[2022 RMS reference dashboard](https://cosmo1007.github.io/2022-rms-network/)
but rebuilt against:

- The **28-well 2027 RMS network** proposed by Butte County DWRC
  (`BC Network 2026 v8.xlsx`, column E)
- **Fresh DWR Periodic GWL measurements** pulled live from CKAN, not the
  2022 dashboard's bundled data
- **MT/MO/IM thresholds for all 28 polygons** — 7 carried forward from
  the adopted 2022 GSP, 21 newly derived via a "2022 Mirror" baseline
  methodology

Audience: AGUBC Board, Vina GSA staff, and technical reviewers preparing
the 2027 GSP update.

---

## Inputs (all read-only)

| Source | Files used | What we pulled |
|---|---|---|
| `BC Network 2026 v8.xlsx` (provided) | 79 wells, 22 metadata columns | RMS membership, lat/lon, GSE/RPE, screen, BBGM layer, Butte County reasoning |
| DWR CKAN Stations | `raw/stations.csv` (~47k rows) | site_code, swn for 77 of 79 wells (2 private wells unresolved) |
| DWR CKAN Measurements | resource `bfa9f262-24a1-45bd-8dc8-138bc8107266` | 227,647 periodic GWL records across 77 wells, refreshed 2026-05-15 via `datastore_search` |
| DWR ArcGIS REST B118 | `i08_B118_CA_GroundwaterBasins/0` (Esri JSON → GeoJSON) | Vina Subbasin boundary (5-021.57), 1,729-vertex outer ring |
| 2022 RMS reference dashboard | `cosmo1007/2022-rms-network/js/wells-data.js` | MT/MO/IM-2027 carry-over values for 7 wells in both networks |

---

## Steps taken

### 1. Scaffolded the project (5 min)

Created `2027-BC-prop-network/` with `scripts/`, `data/`, `raw/`, `js/`,
and `.claude/launch.json` for local preview. Repo lives in iCloud at
`00 COWORK/Projects/tag agubc/2027-BC-prop-network/`.

Note: macOS sandboxing blocks Python's `http.server` from accessing iCloud
working directories cleanly. The preview server uses `/tmp/vina-dash` as
a serving root with files copied into it after each rebuild — only matters
for the local preview, not for GitHub Pages deployment.

### 2. Resolved DWR site_codes for all wells (5 min)

`scripts/resolve_sites.py` joins the xlsx wells to DWR Stations on SWN
(case-insensitive, falls back to `well_name`). Output:
`data/wells_resolved.json` — 77 of 79 wells resolved cleanly. The two
unresolved private wells (`TNC-MW-1`, `FC-MW-2`) have no DWR registration
in either the Periodic GWL or Continuous GWL Stations datasets, and
neither is in the 2027 RMS network — they appear on the map as
supplemental but produce no time-series data.

### 3. Built 28 Voronoi polygons clipped to the Vina Subbasin (10 min)

`scripts/build_polygons_single.py` (Method A — the original):
- Reads the 28 wells where `2027 GWL RMS? = Yes` from `wells_resolved.json`
- Pulls the Vina Subbasin polygon via DWR ArcGIS REST in Esri JSON form
  (the `f=geojson` variant intermittently throws on this endpoint), then
  converts to GeoJSON locally with Shapely
- Projects seeds + boundary to **NAD-83 California Albers (EPSG:3310)** —
  equal-area metric CRS, the DWR/B118 standard
- Adds four anchor points 10× the bounding box outside the basin so
  every one of the 28 cells is bounded (scipy.spatial.Voronoi otherwise
  emits open rays for sites on the convex hull)
- Intersects each cell with the basin polygon; reprojects back to WGS-84
- Asserts exactly 28 cells; aborts on any open region or empty
  intersection (sanity guard against future workbook drift)

**Output:** `data/vina_2027_thiessen_single.geojson` (FeatureCollection)
and `js/polygons-data-single.js` (Leaflet-friendly `[lat,lng]` rings).
Total clipped area ≈ 184,400 acres, within 0.3% of the published Vina
Subbasin area — confirms the projection roundtrip is clean. (See
Step 10 below for the parallel three-zone tessellation added later.)

### 4. Pulled fresh DWR measurements via CKAN datastore API (~3 min)

`scripts/fetch_dwr_measurements.py` calls
`https://data.cnra.ca.gov/api/3/action/datastore_search` per-site for the
77 resolved site_codes, paginated at 32,000 records per page. Total time
~2.5 minutes; 231,330 raw rows; 227,647 deduplicated.

Initially tried `curl -o` on the full 2-3 GB statewide `measurements.csv`
bulk download; abandoned at 1 GB after realizing the per-site API is far
faster and reduces dashboard payload to 15 MB instead of needing a
filter pass over the bulk CSV.

**Output:** `js/measurements-data.js` — `MEASUREMENTS` object keyed by
`site_code`, plus a `MEASUREMENTS_META` block with `fetched_at`,
`n_records`, `n_wells` for the freshness banner in the header.

### 5. Built `wells-data.js` + initial dashboard (45 min)

`scripts/build_wells_js.py` emits one record per xlsx row with full
metadata, joining the 7 carry-over thresholds from the 2022 reference
dashboard. Initial `index.html` + `js/main.js` implemented:

- **§5.2** — Leaflet map, basin boundary, 28 colored polygons, well
  markers in 3 tiers (later collapsed to 2)
- **§5.3** — polygon picker + Plotly hydrograph + per-RMS detail card +
  sortable record table (later restructured)
- **§5.4** — same-month paired GWE scatter with 1:1 line + Pearson R²

### 6. Iterated on UI through several rounds of user feedback

**Round 1 — basic layout:** Removed "Continuous loggers" KPI, doubled map
height, added basemap switcher (CartoDB Positron default, OSM, Esri
satellite, Esri topo), added "Shade by management area" toggle,
collapsed 2022/2027 RMS marker tiers into a single 2-tier system
(2027 Proposed RMS + Supplemental), removed the redundant basin-boundary
toggle.

**Round 2 — §5.3 cosmo parity:** User pointed out the side-by-side card
layout didn't match the 2022 reference. Rewrote §5.3 from a 2-column
grid (hydrograph left, card right) to single-column cosmo-style: header
block → "Toggle wells: Show all | Hide all" + sort tip → hydrograph →
sortable table with columns Show / Well Name / 2027 RMS / Continuous /
Record / Quality Flags / Well Use / Depth / GSE / Most Recent Reading.

**Round 3 — well popups:** Added Current WSE + date, Depth to GW + date,
Record span (year range + n good), and Butte County reasoning from
column F. Nested completions (e.g., 23N01W28M's 4 wells, CWSCH's 7
wells) now collapse to a single map marker with a tabbed popup, plus a
"Nested ×N" pill in the §5.3 table.

**Round 4 — bug fix, polygon click hit area:** Originally the click
area was the polygon's SVG bbox when shading was off (`fill: false`).
Fixed by keeping `fill: true` with `fillOpacity: 0.001` when shading is
off — visually invisible but fully clickable everywhere inside the
polygon. Also removed the hover tooltip which user described as a
"large rectangle" appearing on click.

**Round 5 — threshold orientation bug:** Originally my code did
`y = ref - val`, treating MT/MO/IM values as depth-below-RPE. User
caught that MO was plotting BELOW MT on the chart (inverted). Verified
against the 2022 cosmo dashboard source: the values are stored as
**groundwater elevations in ft msl** directly. Fix: use values as-is
on the y-axis. MO now plots near the top, IM just above MO, MT much
lower — matches SGMA semantics.

**Round 6 — GWE/DTW toggle:** Added two buttons to the §5.3 controls
row: "GWE (ft msl)" (default) and "Depth to GW (ft below GSE)". DTW
mode uses the `gse_gwe` field from DWR (falls back to `GSE − GWE`),
flips the y-axis to autorange "reversed" so shallow water is at the
top in both views, and converts threshold lines (`y_dtw = GSE − GWE_msl`).
Mode persists across polygon changes.

**Round 7 — §5.3/§5.4 sync:** Scatter colors now match hydrograph
colors (same `TRACE_COLORS` palette, same well order via
`wellsWithColor`). Toggling a well's Show checkbox in §5.3 also restyles
its scatter trace to `legendonly`. Same for "Show all" / "Hide all".

### 7. Bundled README into a JS const (5 min)

User reported the README accordion was empty. Root cause: opening
`index.html` via `file://` blocks `fetch("README.md")` due to CORS. The
fetch worked through the preview server but failed for the typical
"double-click the file in iCloud" workflow.

Wrote `scripts/build_readme_js.py` that bakes the markdown into
`js/readme-data.js` as `const README_MD = "..."`. The page now reads
that synchronously and pipes it through `marked.parse()`. Works
identically over `file://`, `http://`, and GitHub Pages.

Also fixed a CSS bleed where inline `<code>` styling (gray background)
was painting white strips inside the dark `<pre><code>` fenced blocks.
Switched fenced blocks to a light GitHub-style palette and added a
`pre code { background: transparent }` reset.

### 8. Pushed to GitHub (cosmo1007/2027-BC-prop-network, private) — May 2026

`git init`, `.gitignore` excludes `.claude/`, `secondary/`, `raw/`,
`data/measurements.json` (debug intermediate). Initial commit, push to
`main`. Repo is private; AGUBC Pro account supports GitHub Pages on
private repos when enabled later.

### 9. Added Path-2 MT/MO/IM thresholds for the 21 new wells (30 min)

In response to a user question about how to set MT/MO/IM for the wells
without 2022 carry-over: the original derivation methodology is
undocumented (Butte County, Vina GSA, and AGUBC staff confirmed no
methodology memo survives). The 2022 values were nonetheless adopted
by the GSA and accepted by DWR.

Computed the empirical pattern across the 7 adopted wells: MT sits
~70 ft below `drought_min` (mean −68.5 ft, median −66), MO sits
essentially at `drought_min` (mean −1.6 ft), IM sits ~2 ft above MO.

`scripts/compute_thresholds.py` produces `data/thresholds.json` for
all 28 wells using:

```
drought_min  = min GWE during 2012-2016 + 2020-2022 windows (all QA flags)
MT_ft        = round(drought_min − 70)
MO_ft        = round(drought_min)
IM_2027_ft   = round(MO + 2)
```

Wells in both networks keep their 2022 GSP values verbatim with source
flag `"2022 GSP"`; the 21 new wells get the computed baselines with
source flag `"2022 Mirror"`.

Dashboard distinguishes the two visually: **dashed** lines for 2022
GSP, **dotted** with "(2022 mirror)" suffix for 2022 Mirror. §5.3 table
shows a blue "GSP-adopted MT/MO" pill or a warm "2022 mirror MT/MO"
pill on each RMS row, with hover tooltips explaining the methodology.

`scripts/update_workbook_thresholds.py` appends four new columns (W–Z)
to `BC Network 2026 v8.xlsx` — `MT_ft`, `MO_ft`, `IM_2027_ft`,
`Threshold_Source` — color-coded by source. The pre-threshold workbook
is backed up to `secondary/BC_Network_2026_v8.backup-before-thresholds.xlsx`.

A separate 2-3 page AGUBC Staff Memorandum
(`memos/2026-05-15_thresholds_methodology.md`) explains the methodology
for Board distribution. The memo stays out of git (`memos/` in
`.gitignore`); it's distributed by email.

### 10. Added a three-zone tessellation alongside the original (45 min)

Followed up on a user request to add a per-management-area Voronoi
alternative — one independent Voronoi diagram per management area
(01-Vina-North / 02-Vina-Chico / 03-Vina-South), each clipped to its
own area polygon — so cells **do not cross management-area lines**.

Why this matters: each Vina management area carries distinct SMC, so a
polygon system where cell membership is unambiguous and constrained by
mgmt-area lines is easier to defend in the 2027 GSP. The single-basin
Voronoi (which is more permissive — it lets cells span management
areas) is kept as a comparison view.

**Implementation pattern:** two parallel build scripts, two parallel
data outputs, one dashboard toggle.

- `scripts/build_polygons_single.py` (recovered from `main`) →
  `js/polygons-data-single.js` (`const RMS_POLYGONS_SINGLE`)
- `scripts/build_polygons_three_zone.py` (new) →
  `js/polygons-data-three-zone.js` (`const RMS_POLYGONS_THREE_ZONE`)
- `index.html` loads both; `js/main.js` keeps a swappable `RMS_POLYGONS`
  reference; a new `<select id="picker-poly-method">` in the §5.2 map
  controls flips between them with instant redraw + §5.3/§5.4 re-sync.
- The three-zone script does **spatial zone assignment** (geometric
  containment in the area polygons) rather than trusting the workbook
  mgmt-area tag. Each feature preserves `workbook_mgmt_area` +
  `reassigned: true|false` so any disagreement is auditable rather than
  silent. v8 surfaces exactly one disagreement: **`23N01E33A001M`** is
  tagged 01-Vina-North in the workbook but physically sits in
  02-Vina-Chico. In three-zone mode this well anchors a ~1,090-ac cell
  in Chico instead of an ~11,050-ac cell in North.
- Coverage check (three-zone): stitched 28 cells = exact union of three
  area polygons, gap −0.0 ac.

**Cache-busting side-quest.** When testing the toggle, the browser kept
loading a stale cached `main.js` after rebuilds — the file mtime
changed in `/tmp/vina-dash/js/` but the unsuffixed `<script src="js/main.js">`
in index.html re-used the cached version. Fixed by appending `?v=3`
query strings to every script tag and adding a `cache-control: no-cache`
meta. Future rebuilds that change JS shape should bump the `?v=N` to
guarantee a fresh load.

Branch: `three-zone-thiessen`; PR
[#1](https://github.com/AGUBC-vina/2027-BC-prop-network/pull/1).
Default behavior on the dashboard is **Single tessellation** so nothing
visually changes for existing reviewers until they explicitly toggle.

### 11. 2026-05-19 network revision — restructure of all three areas

Tovey provided a revised RMS list reflecting stakeholder input. Key
changes:

- **North** grew from 13 → 13 wells, but composition changed:
  - **Dropped**: `23N01W03H004M`, `23N01W31M004M`
  - **Reassigned in**: `22N01E09B001M`, `22N01E20K001M` — both
    physically in the Chico mgmt area but treated as North RMS for the
    2027 network. A new `rms_mgmt_area` field on each well in
    `wells_resolved.json` carries the network-design assignment; the
    geographic `mgmt_area_full` is preserved.
- **Chico** shrank from 3 Voronoi cells with 3 RMS wells to **1
  dissolved mgmt-area polygon** associated with 10 well completions
  across 2 nested 2022 GSP RMS sites:
  - CWSCH 7-nest: `CWSCH01b/02/03/04/05/06/07`
  - 22N01E28J 3-nest: `22N01E28J001M/003M/005M`
  - The previous 3 Chico RMS wells (`22N01E09B001M`,
    `22N01E20K001M`) moved to North. The third (`23N01E33A001M`) which
    was reassigned to Chico spatially in step 10 stays geographically
    in Chico via `mgmt_area_full` but is back in North per the network
    design — covered by its own North Voronoi cell.
- **South** shrank from 13 → 12: `20N02E08H003M` dropped.
- Total: **35 RMS well completions** (was 28); **26 polygon entries**
  (was 28).

**Polygon strategy by area:**
- North: Voronoi of 13 seeds, clipped to (N∪C) so the 2 reassigned
  cells extend into Chico territory. Two **phantom seeds** (the CWSCH
  and 22N01E28J coordinates) are added to the Voronoi computation to
  bound the reassigned cells from the south — without them, scipy
  gives those 2 cells ~18,000 ac each (they'd dominate the southern
  half of N∪C); with them, each cell is 7,000–9,000 ac.
- Chico: dissolved polygon, no Voronoi. Carries `is_aggregate: true`,
  `rms_well_swns: [...10 SWNs]`, `rms_label` for the picker. Drawn
  first in the output array so the 2 reassigned-North cells overlay
  Chico in their overlap regions (~7,200 ac total overlap).
- South: Voronoi of 12 seeds clipped to South mgmt area.

**Thresholds:** dropped 3 (the dropped wells were 2022 Mirror, no
adopted values lost). Added 5 from 2022 GSP for the Chico primaries
(CWSCH01b/02/03/07, 22N01E28J003M). Total threshold entries: 30 (was
28; 12 "2022 GSP" + 18 "2022 Mirror"). The 5 supplemental Chico
nested completions have no thresholds, matching the 2022 GSP
convention.

**Dashboard handling:** new `polygonWells(poly)` helper resolves
"the wells this polygon represents" — for aggregate polygons, it uses
`rms_well_swns` directly; for per-well polygons, it falls back to
geographic point-in-polygon. §5.3 picker, header, hydrograph, and §5.4
scatter all support the aggregate case. Selecting Chico renders 25
Plotly traces (10 well GWE + 15 threshold lines for 5 primaries).

**Storage repo impact:** the sibling `2027-BC-storage` dashboard reads
`polygons-data-three-zone.js`. The data shape changed (Chico entry now
has `is_aggregate`, `rms_well_swns`; reassigned wells have new
mgmt-area-vs-workbook tagging). The storage dashboard will need a
parallel update to consume the new shape — flagged for follow-up.

Branch: `2027-network-revision`; bump cache-buster to `?v=8`. Default
polygon method on the dashboard remains **three-zone** (set as default
in the previous session).

---

## Key methodological decisions

| Decision | What we chose | Why |
|---|---|---|
| Polygon framework | 28 Voronoi cells, one per 2027 RMS well | No Chico-dissolve; each RMS gets its own cell by construction (no override logic needed) |
| Polygon-method choice | **Two parallel tessellations, dashboard toggle** (single basin-wide + three-zone per mgmt area) | Lets reviewers see both: the original single-basin view (simpler, basin-wide neighborhoods) and the SMC-defensible three-zone view (each mgmt area is a closed system). Same 28 SWNs key both sets, so switching preserves the §5.3 selection |
| Three-zone zone assignment | Spatial containment (geometric truth) — workbook mgmt-area tag preserved as audit field | One v8 well (`23N01E33A001M`) is reassigned vs. the workbook tag; making this an explicit on-the-record boundary call is more defensible than a silent override or trusting a possibly-stale tag |
| Voronoi projection CRS | NAD-83 California Albers (EPSG:3310) | Equal-area metric; matches B118 working CRS so polygon areas line up with DWR figures |
| Voronoi bounding | 4 anchor points 10× bbox outside basin | scipy emits open rays for hull sites; anchors guarantee bounded cells, discarded after computation |
| Clip boundary | DWR B118 5-021.57 outer polygon | Standard, downloadable, ~184k acres |
| Measurement fetch | CKAN `datastore_search` per-site | Far faster than 2 GB bulk CSV; produces 15 MB dashboard payload vs. needing a filter pass |
| Nested-completion handling | Group by `(lat, lng)` rounded to 5 decimals; one marker per site; tabbed popup | Reduces 79 wells to 54 unique marker locations; matches cosmo's "Nested ×N" convention |
| Marker tiers | 2 only — 2027 Proposed RMS (blue) + Supplemental (gray) | User explicitly requested simplification from the 3-tier 2022 / 2027 / supplemental split |
| Polygon click hit area | `fill: true` always, `fillOpacity: 0.001` when shading off | Keeps the polygon SVG fully clickable even when visually invisible — fixes "can't click polygon when shading off" bug |
| MT/MO/IM interpretation | GWE values in ft msl (NOT depth-below-RPE) | Matches the 2022 cosmo source; corrects an early bug where I subtracted from RPE |
| Drought-window data filter | All QA flags (Good + Questionable + Missing) | More inclusive than the original storage analysis, which uses Good-only — but storage and threshold-derivation are different purposes, and for thresholds you want the most conservative (lowest) drought_min |
| Threshold source for 21 new wells | "2022 Mirror" — empirical mirror of adopted pattern | No methodology document survives; mirroring the precedent is the most defensible interim approach |
| Threshold visual distinction | Dashed (adopted) vs. dotted (mirror); colored pills in the table; "(2022 mirror)" suffix in legend | At-a-glance clarity for reviewers — no risk of confusing baseline with adopted |
| README delivery | Bundled into `js/readme-data.js` as a string constant | Works over `file://` (no CORS issues), `http://`, and GitHub Pages identically |
| Memo distribution | Markdown only, kept in `memos/` excluded via `.gitignore` | Per AGUBC convention, staff memos go by email — not published to repo |

---

## Files produced

```
2027-BC-prop-network/
├── README.md                          Methodology document for the audience
├── PROJECT_NOTES.md                   This file — project history
├── index.html                         Dashboard shell (§5.2, §5.3, §5.4)
├── BC Network 2026 v8.xlsx            Source workbook + 4 new threshold columns (W–Z)
├── .gitignore                         excludes .claude/, secondary/, raw/, memos/
├── js/
│   ├── wells-data.js                  79 wells, joined to DWR site_code + thresholds
│   ├── polygons-data-single.js        28 single-basin Thiessen polygons (default)
│   ├── polygons-data-three-zone.js    28 three-zone Thiessen polygons (toggle in §5.2)
│   ├── measurements-data.js           227,647 DWR GWL records (15 MB)
│   ├── basin-boundary.js              Vina Subbasin GeoJSON
│   ├── readme-data.js                 README.md bundled as `const README_MD`
│   └── main.js                        UI logic (Leaflet, Plotly, picker, sort, toggle)
├── data/
│   ├── wells_resolved.json            Excel rows joined to DWR Stations
│   ├── thresholds_2022.json           7 wells carried from 2022 GSP (kept for provenance)
│   ├── thresholds.json                All 28 RMS wells — adopted + mirror, with source flag
│   ├── vina_2027_thiessen_single.geojson     Single-basin polygons as GeoJSON
│   └── vina_2027_thiessen_three_zone.geojson Three-zone polygons as GeoJSON
├── raw/                               (gitignored) cached source downloads
│   ├── stations.csv                   DWR CKAN Stations
│   ├── vina_subbasin.geojson          B118 5-021.57 boundary
│   ├── b118_vina_esri.json            Source Esri JSON (pre-conversion)
│   └── cosmo_wells.js                 2022 dashboard wells (for threshold carryover)
├── memos/                             (gitignored) staff memos distributed by email
│   └── 2026-05-15_thresholds_methodology.md
├── secondary/                         (gitignored) backups
│   └── BC_Network_2026_v8.backup-before-thresholds.xlsx
└── scripts/
    ├── resolve_sites.py               xlsx + DWR Stations → wells_resolved.json
    ├── build_polygons_single.py       Method A — single Voronoi clipped to Vina basin
    ├── build_polygons_three_zone.py   Method B — three Voronois, one per management area
    ├── fetch_dwr_measurements.py      DWR CKAN → measurements-data.js
    ├── compute_thresholds.py          7 adopted + 21 mirror → thresholds.json
    ├── build_wells_js.py              wells_resolved + thresholds → wells-data.js
    ├── update_workbook_thresholds.py  Appends MT/MO/IM/Source columns to xlsx
    └── build_readme_js.py             README.md → readme-data.js
```

---

## Outstanding items

- **Two private wells (TNC-MW-1, FC-MW-2) have no DWR data.** Both
  are flagged supplemental, not RMS. They appear on the map as gray
  dots with xlsx metadata but produce no time-series. If TNC or the
  FC-MW-2 owner shares their records, the pipeline would need a manual
  ingestion path (currently all measurements come from DWR CKAN).

- **GitHub Pages not enabled.** Private-repo Pages requires a manual
  toggle in repo settings. Once flipped (Settings → Pages → Source:
  Deploy from a branch → `main` / root), the dashboard is live at
  `cosmo1007.github.io/2027-BC-prop-network/`.

- **Workbook re-shipping on threshold updates.** `BC Network 2026 v8.xlsx`
  carries the four trailing columns now, but it's a tracked artifact —
  any future change to `data/thresholds.json` should also be reflected
  in the xlsx by re-running `update_workbook_thresholds.py`. The script
  is idempotent (skips the backup if one exists) so reruns are safe.

- **Threshold methodology — formal adoption.** The 2022 Mirror values
  are a defensible interim baseline, not adopted SMC. When the GSA
  initiates SMC review for the 2027 GSP, swap in the adopted values
  by editing `data/thresholds.json` and re-running `build_wells_js.py`
  + `update_workbook_thresholds.py`. No dashboard code change required.

---

## Reproducing

```bash
# One-time
pip3 install --user openpyxl pandas geopandas pyproj scipy shapely requests

# Refresh the full pipeline (top-to-bottom)
python3 scripts/resolve_sites.py               # → data/wells_resolved.json
python3 scripts/build_polygons_single.py       # → data/vina_2027_thiessen_single.geojson + js/polygons-data-single.js
python3 scripts/build_polygons_three_zone.py   # → data/vina_2027_thiessen_three_zone.geojson + js/polygons-data-three-zone.js
python3 scripts/fetch_dwr_measurements.py      # → js/measurements-data.js (~3 min, 15 MB)
python3 scripts/compute_thresholds.py          # → data/thresholds.json
python3 scripts/build_wells_js.py              # → js/wells-data.js
python3 scripts/update_workbook_thresholds.py  # → updates xlsx
python3 scripts/build_readme_js.py             # → js/readme-data.js

# Open the dashboard locally (works over file://)
open index.html
```

Edit `BC Network 2026 v8.xlsx` (RMS flags or coordinates) and re-run
the full pipeline. Edit `README.md` and re-run `build_readme_js.py`
only.
