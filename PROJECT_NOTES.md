# Project Notes — What We Did

A working-notes file recording **what was built, why, and how** for the
Vina Subbasin 2027 RMS Network Dashboard (26-polygon three-zone tessellation (27 RMS sites, 35 well completions), hydrograph
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

### 3. Built 26-polygon three-zone tessellation (27 RMS sites, 35 well completions) clipped to the Vina Subbasin (10 min)

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

### 12. 2026-05-20 clipping refinement — no N-cells in Chico, slivers absorbed

Tovey reviewed step 11 and asked for a tighter geometric story:

- **No North polygon should overlap with the Chico mgmt area.** The
  3 N RMS wells whose physical location is inside Chico
  (`22N01E09B001M`, `22N01E20K001M`, `23N01E33A001M`) keep their own
  §5.3 picker entries, but their Thiessen cells are clipped to NOT
  include Chico territory — the cells therefore sit *north* of the
  well markers (in N proper), wherever the 13-seed Voronoi gives them
  territory closer to that well than to any other N seed.
- **Slivers along the north Chico boundary and at the basin
  W/E edges get absorbed.** Earlier builds had thin uncovered
  bands between the mgmt-area polygons (the source mgmt-area
  GeoJSON does not perfectly tile the basin). Computing the
  Voronoi directly over the clip domain `(Basin − Chico − South)`
  with all 13 N seeds means every point in that region is assigned
  to its nearest seed — no orphan slivers.
- **Three Chico-located N RMS wells.** Both reassigned wells
  (`22N01E09B001M`, `22N01E20K001M`) and `23N01E33A001M` (workbook-
  tagged North but spatially in Chico) fall into this case. The
  dashboard popup now calls out the relationship: "physical location
  inside the Chico mgmt area; RMS for the North network. The Thiessen
  cell sits north of this well (Chico territory is clipped away)."
- **Single tessellation revised.** Updated `build_polygons_single.py`
  to dedupe seeds by `(lat, lng)` so the CWSCH 7-nest and 22N01E28J
  3-nest each collapse to one Voronoi seed. Output: 27 cells (was
  28 before the revision). Each nested-site cell carries
  `is_aggregate: true` and `rms_well_swns` so the dashboard's
  `polygonWells()` helper finds all completions at that site.
- **KPI relabeled.** The "2027 GWL RMS" KPI now counts distinct
  lat/lng sites (= 27) instead of `is_2027_gwl_rms` entries (= 35).
  Matches Tovey's framing of "27 RMS wells" (the 10 nested Chico
  completions collapsing to 2 sites).

Coverage after this change (three-zone):
- 13 N cells total ~72,000 ac (= `Basin − Chico − South`)
- Chico aggregate ~29,700 ac (full mgmt area)
- 12 S cells total ~83,000 ac (= South mgmt area)
- N-Chico overlap: **0 ac**
- Basin total ~184,400 ac, within rounding

Branch: `2027-network-revision` (continuing); cache-buster bumped to
`?v=10` for polygons + main.js.

---

### 13. 2026-05-21 — Chico = 1 RMS (CWSCH01b); new MT-buffer methodology for non-carryovers

Two big updates rolled in together:

**Chico shrinks to one RMS well.** Per Tovey's review, the Chico
management area now has only ONE RMS designation for the 2027 network:
`CWSCH01b`. The 9 other completions at the 2 historical 2022 GSP
nested sites — CWSCH02/03/04/05/06/07 and 22N01E28J001M/003M/005M —
become **supplemental** (not is_2027_gwl_rms). The Chico dissolved
polygon still plots all 10 wells in §5.3 (CWSCH01b RMS + 9 supplemental
nested completions) for hydrograph context, but only CWSCH01b carries
threshold lines.

This drops the network to **26 RMS wells across 26 polygons**:

| Mgmt area (network) | 2022 carryover | New Mirror | Total |
|---|---:|---:|---:|
| 01-Vina-North | 5 | 8 | 13 |
| 02-Vina-Chico | 1 (CWSCH01b) | 0 | 1 |
| 03-Vina-South | 3 | 9 | 12 |
| **Total** | **9** | **17** | **26** |

A new well joined the carryover set: `21N02E26E006M` (South). It wasn't
a 2022 GSP RMS itself, but it's at the same lat/lng as `21N02E26E005M`
(the 2022 RMS at that nested site, retired from 2027). The 006M
completion inherits 005M's 2022 GSP MT/MO/IM (36 / 95 / 97 ft msl) via
a new `carryover_from` field in `wells_resolved.json`. The dashboard
popup surfaces the inheritance explicitly.

**New "2022 Mirror" methodology — MT buffer analysis.** Replaces the
prior `MT ≈ drought_min − 70` coefficient. The new approach:

1. For the 13 2022 GSP RMS wells (excluding 4 CWSCH nested completions
   that would skew the average), compute
   `per_well_buffer = all_time_min_QA_Good_GWE − adopted_2022_MT`.
2. Average by management area:
   - North: **69.55 ft** (n=6, range 58.45–81.50)
   - South: **57.60 ft** (n=6, range 38.63–71.15)
   - Chico: **27.93 ft** (n=1, single well: 22N01E28J003M)
3. For each of the 17 non-carryover 2027 RMS wells, derive:
   ```
   MT_ft = round(alltime_min − region_buffer)
   MO_ft = round(drought_min)        [unchanged from prior Mirror]
   IM_ft = round(drought_min + 2)    [unchanged from prior Mirror]
   ```
   `region_buffer` is keyed on the **network** `rms_mgmt_area`, so the
   2 N-network wells located in Chico (22N01E09B001M, 22N01E20K001M)
   use the **North** buffer (69.55 ft), consistent with their role as
   North RMS wells. (An earlier draft used the geographic mgmt area;
   corrected on 2026-05-21.)

**MT vs MO use different "low" bases by design.** MT uses all-time min
to match the 2022 GSP MT-buffer benchmark exactly. MO stays on
drought-window min so the "measurable objective" retains its tie to
drought-period hydrology.

**Implementation:** `scripts/compute_thresholds.py` was rewritten to
encode the new methodology; `data/thresholds_2022.json` is unchanged
(the carryover source of truth); `wells_resolved.json` carries the
new `carryover_from` field; `build_polygons_three_zone.py` reduces the
Chico aggregate to 1 RMS + 9 supplementals (identified by collapsing
to lat/lng sites and pulling any site that hosted a 2022 GSP RMS,
which preserves the 22N01E28J site even though 003M is now
supplemental); `build_wells_js.py` surfaces `carryover_from` in
wells-data.js; `main.js` adds an inheritance note to the well popup.

**Cache-buster** bumped to `?v=11` for changed JS bundles. Branch:
direct commits to `main` (working tree on `main` since the 2026-05-21
revision).

---

### 14. 2026-05-22 — Domestic-well overlay + MT sensitivity widget

Added a "Show domestic wells" toggle to §5.2 and an MT sensitivity
widget to §5.3, mirroring features from the cosmo
[2022-RMS-Well-MT-Sensitivity](https://cosmo1007.github.io/2022-RMS-Well-MT-Sensitivity/)
dashboard but built against our revised 2027 RMS network instead of
the 2022 GSP one.

**Data pull.** `scripts/fetch_cosmo_domestic_wells.py` downloads the
cosmo `js/wells-data.js` bundle (3,212 wells, 1,253 with
`include=1`), spatial-joins each well to our 2027 three-zone polygons
(buffer(0) trick to clean minor topology issues in the clipped polys),
and emits a pruned `js/domestic-wells-data.js` bundle (~1 MB,
down from cosmo's 2 MB by dropping unused fields). Each well carries
its `our_polygon` (2027 zone_label) and `our_mgmt_area`.

**Map overlay.** New canvas-rendered Leaflet layer for performance
with 1,253 markers; color-coded by mgmt area (blue/peach/green). New
toggle in §5.2 controls; off by default. Markers are non-interactive
(no per-well popup) to keep pan/zoom responsive.

**Sensitivity widget.** A new `<div id="sensitivity-widget">` block
in §5.3 after the hydrograph. Contains:
- Slider 0–30 ft (`#mt-raise-slider`), 1-ft increments.
- Toggle `#tog-elev-correction` for cosmo's one-sided elevation
  correction.
- 2-row sensitivity table: subbasin (n=1,253) and selected polygon.

**Dry formula.**
```
gse_delta    = elev_correction ? max(0, domestic_gse - rms_gse) : 0
effective_MT = polygon_MT + slider_raise + gse_delta
dry          = (well_bottom_amsl > effective_MT)
```
Dry counts *decrease* as MT is raised (more conservative threshold
= more water preserved = fewer wells lose pumping capacity).

**Popup additions** for RMS well markers (function-content
`bindPopup` so they recompute on each open):
- "Dry domestic wells at MT (`N` ft): `X` of `Y` (`Z%`)"
- "Dry at MT + `S` ft: `X'` of `Y` (`Z'%`)"

**Sign convention** confirmed with Tovey: slider raises MT (more
conservative); display reads "+N ft". Matches cosmo.

**Implementation notes:**
- All sensitivity calcs are pure functions over the cached
  `DOMESTIC_BY_POLYGON` dict; no external recomputation needed when
  the slider moves.
- 23N01E33A001M and the 2 reassigned wells (22N01E09B001M,
  22N01E20K001M) use their polygon's MT via `polygonMT()`, which
  reads `is_aggregate ? rms_primary_swns[0] : rms_well_swn`.
- The hydrograph adds a dashed orange "MT + N" line only when
  slider > 0 AND the trace's well is the polygon's seed RMS.

**Sibling repo:** The 2027-BC-storage dashboard reads our polygons
but not the new domestic-wells bundle. No update needed there for
this feature.

Branch `domestic-wells-sensitivity`; cache-buster bumped to `?v=13`.

---

### 15. 2026-05-21 — AGWL Mirror methodology adopted; supersedes buffer-based Mirror

BCWRC staff (Christina Buck) proposed a new methodology for deriving
MT/MO/IM for the 17 non-carryover 2027 RMS wells, anchored on each
well's average spring groundwater level rather than its all-time min.
After a three-variant sensitivity comparison (Feb–May / Feb–April /
Highest March), staff selected the **Feb–April AGWL Mirror** approach
on 2026-05-21 for the dashboard.

**Formula** (per well, applied to MT, MO, and IM-2027):

```
AGWL_well = mean of QA-Good GWE in Feb/Mar/Apr months across full record
zone_offset = mean over 2022 RMS wells in same network zone of
              (AGWL_RMS − threshold_2022_RMS)
threshold_new = round(AGWL_well − zone_offset)
```

**Zone offsets (Feb–April):** North 91.0 / Chico 43.2 / South 92.1 for
MT; smaller offsets for MO and IM (see `analysis/methodology_mt_mo_im.md`).

**What changed in the data.** All 17 new RMS wells got fresh MT/MO/IM
values. Some MTs raised (shallower DBS = more protective), some
lowered, average per-zone shift modest. The 9 carryover wells were
NOT touched — they keep their adopted 2022 GSP MT/MO/IM unchanged.

**Source label changed** from `"2022 Mirror"` → `"AGWL Mirror"` in
`thresholds.json`, `wells-data.js`, the §5.3 pill text, popup tooltips,
and the workbook column. The CSS pill class `pill-thr-mirror` was
kept (stable internal identifier).

**Analysis artifacts** added under `analysis/`:
- `methodology_mt_mo_im.md` — standalone explainer of the adopted methodology
- `agwl_window_comparison.md` — three-variant sensitivity comparison
- `christina_methodology_summary.md` — original summary prepared for Christina, May 2026
- `christina_mt_comparison.md` — earlier detailed comparison (pre-variant work)

**Comparison scripts** added under `scripts/` (read-only, do not modify
dashboard outputs):
- `compute_thresholds.py` — rewritten in place to AGWL Mirror methodology
- `compare_agwl_windows.py` — three-variant sensitivity comparison
- `compare_christina_mt.py` — earlier baseline-vs-Christina comparison

**Sibling repo `2027-BC-storage`:** uses water-level deltas, not MT, so
no update needed there for this change.

Branch `agwl-mirror-methodology`; cache-buster bumped to `?v=15` (main.js
and readme-data.js) and `?v=13` (wells-data.js).

---

### 16. 2026-05 — Removed single-tessellation toggle; added 3 Chico RMS wells (CWSCH02/03/07)

Two changes landed together on branch `chico-3-new-rms`.

**Single-tessellation toggle removed.** The §5.2 "Polygon method" picker
and its underlying `RMS_POLYGONS_SINGLE` / `polygons-data-single.js`
infrastructure are no longer wired into the dashboard. `js/main.js` now
hardcodes `RMS_POLYGONS = RMS_POLYGONS_THREE_ZONE`; `setPolygonMethod()`
and its event listener were deleted. `index.html` no longer loads
`polygons-data-single.js`. README's "How the polygons are built"
section was rewritten to describe only the three-zone method (Method A
/ Method B framing, the comparison table, and "How the dashboard
chooses" section were all removed). `scripts/build_polygons_single.py`
and `data/vina_2027_thiessen_single.geojson` are left in place
(unreferenced) rather than deleted, in case the single-tessellation
view is wanted again later.

**Chico RMS expansion.** BCWRC flagged `CWSCH02`, `CWSCH03`, and
`CWSCH07` as 2027 RMS wells (column E in the workbook), joining the
existing `CWSCH01b`. All 4 are 2022 GSP RMS wells, so each keeps its
adopted MT/MO/IM unchanged (Chico's "2022 GSP" carryover count went
from 1 to 4; the basin-wide carryover total is now 12 instead of 9).
2027 RMS wells basin-wide: 26 → 29. Because Chico is a single
fixed-boundary polygon (no internal Voronoi), this is purely a
hydrograph/threshold-line change — **polygon count stays 26, no
geometry changes anywhere in the network.**

**Bug found and fixed during this work — two manual data overrides
were not durable.** `data/wells_resolved.json` is regenerated from
scratch by `scripts/resolve_sites.py` on every run and is gitignored,
so it carries no memory between sessions. Two fields that previous
sessions had patched directly into that JSON (rather than encoding in
a script) were silently lost the moment the workbook changed and
`resolve_sites.py` was rerun:

1. `rms_mgmt_area` override for `22N01E09B001M` and `22N01E20K001M`
   (RMS-for-North despite sitting in Chico mgmt area). Losing this
   caused North's Voronoi seed count to drop from 13 to 11 and
   completely reshaped the North tessellation (e.g. `23N01W36P001M`
   jumped from 7,088 to 15,307 ac) — caught before commit by comparing
   against the previously-documented per-polygon areas.
2. `carryover_from` override for `21N02E26E006M` → `21N02E26E005M`
   (inherits the retired sibling's 2022 GSP MT/MO/IM). Losing this
   flipped the well from "2022 GSP" (MT=36) to a freshly-computed
   "AGWL Mirror" value (MT=18) — caught the same way.

**Fix:** both overrides are now hardcoded dicts
(`RMS_MGMT_AREA_OVERRIDE`, `CARRYOVER_FROM_OVERRIDE`) directly in
`scripts/resolve_sites.py`, applied unconditionally on every run. This
makes them durable — future workbook edits and re-runs will no longer
silently drop them. If a *third* override of this kind is ever needed,
it should go in `resolve_sites.py` the same way, not as a one-off
patch to the generated JSON.

`scripts/update_workbook_thresholds.py`'s `rms_label` generator was
also generalized to list N RMS primaries by name (was hardcoded to the
`len == 1` / "CWSCH01b" case); the auto-generated header comment in
`polygons-data-three-zone.js` is now computed from the actual seed
counts rather than hardcoded.

Verification: re-ran the full pipeline after the override fix and
confirmed every North/South polygon area matched the previously
committed values exactly; confirmed the Chico aggregate's
`rms_primary_swns` lists all 4 CWSCH RMS wells; confirmed the
hydrograph renders 4 independent threshold-line sets when the Chico
polygon is selected (each well's own MT/MO/IM, MT=85 for all four,
MO/IM differing); confirmed §5.2 KPI counts (79 wells / 29 RMS / 26
polygons) — note the RMS-wells KPI was changed from counting distinct
(lat,lng) sites to counting raw `is_2027_gwl_rms` entries, since the
old site-dedup logic was written when Chico had only 1 RMS well per
site and would have undercounted the new 4-wells-one-site reality.

Branch `chico-3-new-rms`; cache-buster bumped to `?v=17` (main.js),
`?v=20` (readme-data.js), `?v=14` (wells-data.js), `?v=12`
(polygons-data-three-zone.js).

### 17. 2026-07-07 — Strawman Table 3 display + proposed-LML overlay + TNC eco thresholds

Inputs: the county's GWL Strawman memo (Vina GSA, 6/18/2026 — "GWL
Strawman Final_6.18.2026", Attachment A) and TNC's "Ecological
Threshold Recommendations – Vina Subbasin" CSV (9 wells + per-well
hydrograph PDFs), both under `secondary/` (gitignored); the TNC CSV is
copied into the repo at `data/tnc_ecological_thresholds.csv`.

**Threshold display switched to county Table 3 (17 non-carryover
wells).** `compute_thresholds.py` gains a `COUNTY_TABLE3` constant (all
29 wells transcribed from the memo) applied as the displayed MT/MO/IM
with `source: "Strawman Table 3"`; the script's own AGWL Mirror
derivation is retained per-well in `mirror_mt_ft/mirror_mo_ft/
mirror_im_2027_ft`. Cross-check result: **Mirror reproduces Table 3
exactly for 27 of 29 wells.** Divergences auto-flagged in a
`table3_divergence` note surfaced in popups and a "⚠ T3 ≠ Mirror"
pill: `21N01E10B003M` (county 10/64/67 vs Mirror 30/92/94; the county
row is also internally inconsistent — printed ASGWL 102 minus South
offsets 92/30/28 implies MO 72/IM 74, not the published 64/67) and
`21N02E32E001M` (county 30/91/93 vs Mirror 25/87/89; county ASGWL 122
vs dashboard Feb–April AGWL 117.6). For the 12 carryovers the script
asserts Table 3 == 2022 GSP values so upstream changes fail the build.

**Proposed-LML overlay (strawman).** The 5 designated wells
(`23N01W09E001M`, `23N01W27L001M`, `23N01W36P001M`, `22N01E20K001M`,
`21N02E32E001M`) live in a `LML_SWNS` constant in `main.js`. §5.2 gets
a "Proposed LML polygons (strawman)" toggle (dark-cyan dashed overlay,
non-interactive so clicks still select the base cell). §5.3 gets a
teal LML widget — visible only when one of the 5 polygons is selected —
with a MO − 0…30 ft slider (5-ft steps, default 15 = midpoint of the
memo's 10–20 ft starting range), a dash-dot LML line on the
hydrograph, and a historical trigger-frequency readout (share of
QA-Good readings, and distinct years, below the candidate LML).
Scope decision (Tovey): LML applies ONLY to the 5 designated polygons,
mirroring the memo — no basin-wide exploration mode.

**TNC ecological thresholds.** Units gotcha: the CSV headers say
"(ft bgs)" but values are groundwater ELEVATIONS in ft msl — confirmed
against TNC's own hydrograph PDFs (elevation axis) and by physical
impossibility (147 "ft bgs" in a 110-ft well). Threshold ≈ mean summer
GWE − 1.3 sd (~10th percentile of summer record). Joined into
`wells-data.js` via `build_wells_js.py` (tnc_* fields; build fails if
any CSV well doesn't match). Displayed for all 9 wells exactly as TNC
named them — 6 RMS + 3 supplemental (`21N01E28F001M`, `23N01W28M005M`,
`23N01W31M004M`) — as a bright-green dashed hydrograph line, popup
line, "TNC eco" pill, and a §5.2 halo toggle.

No polygon geometry touched (`build_polygons_three_zone.py` not re-run;
`vina_2027_thiessen_three_zone.geojson` / `polygons-data-three-zone.js`
byte-identical). Workbook threshold columns re-synced via
`update_workbook_thresholds.py` (Threshold_Source now "Strawman
Table 3" for the 17). Branch `lml-tnc`; cache-busters bumped to
`?v=18` (main.js), `?v=21` (readme-data.js), `?v=15` (wells-data.js).

Follow-up (same day, after Tovey field-tested the map): the TNC rings
originally sized off the individual well's tier, so supplemental
`23N01W28M005M`'s ring (r=10) drew INSIDE the collapsed nested-pad
marker it shares with RMS `23N01W28M004M` (r=11) — the map read as
"7 RMS + 2 supplemental" instead of 6+3. Fix: ring radius now derives
from the pad's actual rendered marker (nested pads collapse to one
larger marker), supplemental completions get a DASHED ring vs solid
for RMS, and every ring carries a permanent short-name label
(`.tnc-label`, arrowless tooltip; labels flip to the left side for the
two same-latitude east-neighbor pairs: 28M-pad/27L001M and
28F001M/27D001M). Legend split into solid/dashed chips. Cache-busters:
main.js `?v=19`, readme-data.js `?v=22`.

Fourth follow-up (2026-07-08): (a) **ESA GDE scenario overlay** added
to §5.2 — a "ESA GDE areas" toggle + a 6-scenario dropdown over the
1,228 GDE polygon centroids from the ESA GDE Technical Study
(March 2026). Data copied from the sibling `vina-stream-connectivity`
repo (`data/gde-centroids-data.js` -> `js/gde-centroids-data.js`,
`const GDE_CENTROIDS`, 1,228 recs, each with 6 `roots_*` likely flags).
Canvas-rendered (non-interactive) in a dedicated `gdePane` (z-index 420,
between polygons 400 and wells 450): likely-this-scenario = solid green,
others = faint grey; bottom-left on-map legend reports scenario + counts.
The per-scenario likely counts reproduce ESA TM Table 3 exactly
(464/100/64/38/21/17) — verified in the build. Purpose: show how the
"likely GDE" footprint depends on the scenario choice, relative to the
RMS + LML polygons; the green cluster sits in the NW Sacramento River
corridor over the northern LML polygons. Only the scenario dropdown is
ported — NOT the connectivity dashboard's color-mode / surface / year /
shallow-wells / contour controls (Tovey's scope). (b) `.well-label`
font bumped 10px -> 13.5px (Tovey couldn't read them). Cache-busters:
main.js `?v=22`, readme-data.js `?v=25`, wells-data.js `?v=16`,
gde-centroids-data.js `?v=1`.

Fifth follow-up (2026-07-08): §5.3 LML widget gained two readouts that
operationalize the LML-siting/trigger argument. (a) **GDE persistence
readout** (`gdePersistenceHtml`): for the selected LML well, nearby
likely-GDE centroids within 1.5 mi under Spring-90th-pct vs. how many
persist to fall (`roots_p90_fall`), plus distance to the nearest
persistent GDE. Makes the case clickable — 32E001M reads "6 spring /
0 fall, nearest persistent 9.5 mi" (South/Durham, isolated), vs. the 4
northern/Chico wells within ~3-4 mi of the persistent Sacramento
corridor core. (b) **Drought split** on the trigger-frequency readout
(`isDroughtYear` via DROUGHT_PERIODS): shows how many exceedance-years
were NON-drought (only 20K001M, 2011); zero-cases now read "never —
including through the 2012-16 and 2020-22 droughts." Both verified in
preview against the standalone Node analysis (exact match). main.js
`?v=24`. Context: [[project_gde_tnc_advocacy]].

Sixth follow-up (2026-07-12, committed 2026-07-13 with entry 18):
(a) **USGS Topo basemap option** added to §5.2 (`usgs-topo`,
basemap.nationalmap.gov, maxZoom 16) — authoritative NHD blue-line
streams and named creeks/rivers, the best basemap for locating
hydrography relative to the RMS network / GDEs. (b) **LML widget
follows the GWE/DTW toggle**: when §5.3 is in Depth-to-GW mode the
LML level, trigger-frequency readout, and most-recent-reading line
convert to ft-below-GSE (`updateLmlControls` re-runs on mode switch)
so the green bar reads in the same units as the plot. main.js `?v=25`.

See also the GDE/TNC advocacy workstream — the reframed "Working
Technical Notes" (non-record strawman for Christina) and the fallback
comment letter / talking points live in
`00 COWORK/Projects/tag agubc/2027 GDE-LML Comments/` (moved there
2026-07-08), not in any repo.

Third follow-up (2026-07-08): TNC ecological-threshold overlay REMOVED
at Tovey's request — only the proposed-LML overlay remains. Deleted the
`tnc_*` fields + CSV loader from `build_wells_js.py`, `data/tnc_
ecological_thresholds.csv` (git rm; source still under
`secondary/TNC Thresholds/`), and from `main.js` the `TNC_COLOR`
constant, `tncLayer`, `buildTncLayer()`, the `#tog-tnc` toggle, the
green hydrograph line, the popup note, and the `TNC eco` table pill;
plus the corresponding index.html toggle/legend/CSS and README section.
The general **"Show well name labels"** toggle was KEPT — it is useful
independent of TNC (it was Tovey's fix for finding nested pads). Strawman
Table 3 thresholds, the AGWL Mirror cross-check, and the LML overlay all
stay. Context: the TNC ecological thresholds became a live advocacy issue
(Vina GSA GDE debate); AGUBC is commenting to county staff rather than
featuring TNC's numbers in the dashboard. Cache-busters: main.js `?v=21`,
wells-data.js `?v=16`, readme-data.js `?v=24`.

Second follow-up (2026-07-07): labeling only the 9 TNC wells read as
inconsistent, so the ring labels were replaced by a general §5.2
**"Show well name labels"** toggle covering every map pin
(`buildLabelsLayer()` in main.js, `.well-label` CSS, blue text for
RMS-bearing pins, gray for supplemental-only). One label per pin:
single wells get the short SWN via `shortWellName()` ("09E001M");
nested pads get a common-prefix pad label with completion count via
`siteLabelText()` ("28M ×4", "31M ×4", "28J ×3", "CWSCH ×7"). Labels
anchor to invisible zero-radius circleMarkers so hit-testing is
unaffected; default off. The underlying source of Tovey's "7 RMS with
thresholds" reading: the 28M pin renders as ONE RMS-style marker for a
4-completion nest (72 ft to 1,044 ft deep); TNC's threshold there is
on the shallow supplemental completion 28M005M (72 ft, screen
30-50 ft), not the RMS completion 28M004M (207 ft, screens
120-130/155-165 ft) — i.e., TNC targeted the water-table screen, which
the RMS well does not measure. Cache-busters: main.js `?v=20`,
readme-data.js `?v=23`.

### 18. 2026-07-13 — Per-well AGWL derivation surfaced (README table + popup line)

Tovey flagged that the "average GWL for each RMS well" narrative — the
per-well input that explains how the Mirror MT/MO/IMs were derived for
the 17 new wells — was no longer visible anywhere user-facing. Research
finding: the zone-level methodology survived the 2026-07-07 Table 3
rewrite (README "Method" subsection), but per-well AGWLs only ever
existed in `analysis/christina_mt_comparison.md` (stale: Feb–May era,
DBS units, pre-Table-3, never linked from the README) and as unexported
`agwl_ft`/`n_spring_obs` fields in `data/thresholds.json`.

Three changes, display/docs only — no threshold values, polygons, or
pipeline outputs changed:

1. **README "Per-well derivation (17 Strawman Table 3 wells)"
   subsection** (end of the Method section): 17-row table — each well's
   Feb–April AGWL (ft msl), QA-Good spring-reading count, Mirror
   MT/MO/IM from subtracting the zone offsets, and the displayed
   Table 3 values side-by-side, with the 2 divergent wells bolded and
   ⚠-flagged. Includes a worked example (103.2 − 92.12 → MT 11).
   Generated by the new `scripts/print_agwl_table.py` (reads
   `thresholds.json`; rerun and paste after `compute_thresholds.py`
   changes, then rebuild `readme-data.js`).
2. **Map-popup derivation line** for the 17 Strawman wells:
   `build_wells_js.py` now exports `agwl_ft`, `n_spring_obs`,
   `zone_offset_mt/mo/im`; `buildWellPopup()` renders "Feb–Apr AGWL
   103.2 ft msl (1,864 spring obs) − South offsets 92.1/30.5/28.1 ft →
   Mirror MT/MO/IM 11/73/75 = county Table 3" above the divergence
   warning (which replaces the "= county Table 3" tail for the 2
   mismatched wells). Carryover wells skip the line — their values are
   adopted, not AGWL-derived.
3. **`analysis/christina_mt_comparison.md` stamped HISTORICAL** — it
   predates the Feb–April window selection, uses depth-below-surface
   units, and compares against the retired buffer methodology; kept
   for provenance with a pointer to the current docs.

Cache-busters: wells-data.js `?v=17`, readme-data.js `?v=26`,
main.js `?v=26`. Branch `per-well-agwl`.

### 19. 2026-07-13 — Drought shading driven by the Sacramento Valley Water Year Index

Tovey flagged that the §5.3 hydrograph's drought shading (a hardcoded
3-window list: 1991-93, 2012-15, 2020-22) missed the dry years of the
1970s, mid-1980s, and 2007-2010 that are plainly in the record (the
data reaches 1946; there are 900 QA-Good readings in 1976-77, 2,730 in
1987-92, 22,140 in 2007-2010). Replaced the hardcoded list with DWR's
official **Sacramento Valley 40-30-30 Water Year Index**, shading Dry
and Critical water years, and aligned the §5.3 LML trigger-frequency
drought/non-drought split to the same definition so the dashboard tells
one consistent drought story.

Reviewed by a Fable 5 peer agent before implementation; its amendments
were folded in (band clipping, per-reading water-year classification,
generator + anchor assertions, remnant sweep).

- **Data.** New `scripts/fetch_wy_index.py` pulls CDEC WSIHIST, parses
  the **Sacramento** Yr-type column (NOT San Joaquin — the classic parse
  bug), and writes `js/wy-index-data.js` (`const WY_INDEX`, WY 1901-2025,
  24 Dry + 18 Critical) with a retrieval-date header and hard anchor
  assertions (1976/1977 C, 1983 W, 2015 C, 2017 W) that fail the build on
  parse drift. WY2026 isn't classified yet (in-progress), so the record
  tail stays unshaded. Sacramento Valley is the correct index for Vina
  (northern Sac Valley; the Feather is one of the index's four rivers).
- **Shading (`main.js` `droughtShapes`).** Bands for Dry (light orange,
  alpha 0.09) and Critical (deeper, 0.18); consecutive same-class water
  years merge; a band spans Oct 1 (prev cal yr) → Oct 1. **Clipped to the
  union of the plotted wells' measurement extent** — Plotly includes
  layout shapes in x-axis autorange, so an unclipped 1947 band would have
  stretched a short-record polygon's axis back 60 empty years. Memoized on
  `currentSelection` so slider ticks / DTW toggles don't recompute.
  `yref:"paper"` makes bands immune to the DTW y-axis reversal.
- **LML split (`isDryOrCriticalWY` + `lmlTriggerStatsHtml`).** Replaced
  the calendar-year `isDroughtYear`/`DROUGHT_PERIODS` with a water-year
  classifier (`waterYearOf`: Oct-Dec → next WY). The readout now counts
  distinct **water years** and its "never" fallback is generated from the
  data, not a hardcoded drought-name string. **Audit:** the landed LML
  position is unchanged — MO−15 still trips exactly one well
  (`22N01E20K001M`, the 2011-10-13 outlier reading, WY2012 = Below
  Normal, non-drought under both old and new) and MO−20 never trips.
  Changes only appear at MO−0/5/10, which aren't cited anywhere.
- **Legend/CSS/README.** Single hardcoded drought chip → two swatches
  (Dry / Critical water year); `.drought-strip` CSS split into two hues.
  New README "Drought shading (§5.3 hydrograph)" section (source, class
  legend, water-year mapping, Dry+Critical rationale, "hydrologic
  year-type not observed local GW drought" caveat, note that common
  drought names span more years than their Dry/Critical cores).

No polygon geometry, thresholds, or wells-data touched — shading + docs
only. Verified in preview: 21 bands on a 1946-record polygon aligning
with 1976-77 / 1987-94 / 2006-09 / 2013-15 / 2020-22, short-record
polygons not over-stretched, LML readout in water years, no console
errors. Cache-busters: `wy-index-data.js ?v=1` (new), readme-data.js
`?v=27`, main.js `?v=27`. Branch `per-well-agwl` (stacked on the AGWL
work, entry 18).

### 20. 2026-07-20 — LML designations expanded 5 → 14 (revised strawman), two-tier

Tovey supplied the list of 14 RMS wells to identify as proposed-LML
polygons: the original strawman 5 plus 9 added in the **revised
strawman** (under discussion, July 2026). Mapping from his short names
was verified programmatically against all 79 wells — 13 matched
uniquely; "09G01M" (a dropped-zero typo) was confirmed with Tovey as
`20N02E09G001M` per his ask-don't-infer instruction, and the two-tier
framing was his explicit choice (AskUserQuestion).

- **Two-tier constants** in `main.js`: `LML_STRAWMAN_SWNS` (5, the
  6/18/2026 memo designations — the shallower completions) +
  `LML_REV_SWNS` (9) + union `LML_SWNS` (existing keying unchanged), and
  `lmlTierLabel(swn)` for UI text.
  - Original 5: 09E001M, 27L001M, 36P001M, 20K001M, 32E001M.
  - Rev 9 (N): 23N02W25C001M, 22N01W05M001M, 23N01E29P002M.
  - Rev 9 (S): 21N01E10B003M, 21N01E27D001M, 20N01E02H003M,
    20N02E24C001M, 20N02E09G001M, 20N03E33L001M.
- **Map overlay styled by tier**: original 5 keep the heavier long-dash
  (weight 3.5, "8,5", fill 0.10); rev-9 get a lighter short-dash
  (weight 2, "2,6", fill 0.05). Two legend chips. Toggle label now
  "(strawman + revised)".
- **Tier-aware text**: popup LML note, §5.3 polygon-header callout, and
  the §5.3 "LML proposed" pill tooltip say which tier a well belongs to;
  the widget note explains 5-vs-9 provenance. All other LML behavior
  (slider, hydrograph line, trigger stats, GDE persistence readout) keys
  off the union and now applies to all 14 polygons.
- **README**: LML section rewritten — two-tier framing, 14-row table now
  with a **well-depth column** (values pulled from wells-data, not
  hand-typed). Depth matters to the tier story: the original 5 are
  102–184 ft completions; the rev-9 are median ~201 ft but NOT uniformly
  deeper (33L001M 101 ft, 27D001M 112 ft are as shallow as the
  original 5) — so the README lets the depth column speak instead of a
  blanket "deeper wells" claim. Data-sources row added for the revised
  strawman ("stakeholder process — not yet posted"; no public URL yet).

No polygon geometry, thresholds, wells-data, or measurement handling
touched. Cache-busters: main.js `?v=32`, readme-data.js `?v=29`.
Branch `lml-14`.

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
