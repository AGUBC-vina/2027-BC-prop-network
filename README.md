# Vina Subbasin 2027 RMS Network Dashboard

Static interactive dashboard for the 2027 Representative Monitoring Site (RMS)
network in the Vina Subbasin (DWR B118 5-021.57), Butte County, California.

Built from `BC Network 2026 v8.xlsx` and modeled on the
[2022 RMS reference dashboard](https://cosmo1007.github.io/2022-rms-network/).

> **2026-05-19 network revision (most recent: 2026-05-21).** The 2027
> RMS network has been progressively refined through stakeholder review.
> The current state is **26 RMS wells across 26 polygons**:
>
> - **13 North** Voronoi cells. Three of the 13 RMS wells
>   (`22N01E09B001M`, `22N01E20K001M`, `23N01E33A001M`) physically sit
>   inside the Chico mgmt area but are part of the North RMS network.
>   Their Thiessen cells are clipped to NOT overlap with Chico — the
>   cells sit north of the wells (in N proper), while the well markers
>   themselves remain inside Chico. The 11 cells whose seed wells are
>   physically in N tile the rest of the basin-minus-Chico-minus-South
>   region, absorbing any sliver between mgmt-area boundaries.
> - **1 dissolved Chico** mgmt-area polygon, with **CWSCH01b as the
>   single RMS well** for the 2027 Chico network. The 9 other
>   completions at the historical 2022 GSP nested sites — CWSCH 7-nest
>   (CWSCH02/03/04/05/06/07) and 22N01E28J 3-nest (22N01E28J001M/003M/
>   005M) — are now supplemental, plotted in §5.3 for hydrograph context
>   but without threshold lines.
> - **12 South** Voronoi cells, clipped to South mgmt area.
>
> **Threshold methodology (revised 2026-05-21):** 9 wells are direct
> 2022 GSP carryovers (5 N, 3 S, 1 Chico = CWSCH01b); 17 wells get the
> new **2022 Mirror** thresholds derived via the *MT Buffer Analysis*
> described in the methodology section below. The 9 Chico supplementals
> remain monitored but unthresholded.
>
> See "Method B" below and PROJECT_NOTES for full history.

- **§5.2** — Interactive Leaflet map (basin boundary, 26 polygons,
  all 79 wells with layer toggles for 2022 RMS / 2027 RMS / supplemental).
- **§5.3** — Per-polygon hydrograph (Plotly) with MT / MO / IM-2027 threshold
  lines where the 2022 GSP carried forward, plus a per-polygon well-detail
  card and a sortable record-count table.
- **§5.4** — Same-month paired GWE scatter (1:1 line, Pearson R² in the
  legend) for representativeness comparison of supplemental wells against
  the polygon's RMS well.

## Quick start

```bash
# 1. (one-time) install Python deps used by the build scripts
pip3 install --user openpyxl pandas geopandas pyproj scipy shapely requests

# 2. (one-time per data refresh) rebuild the data files
python3 scripts/resolve_sites.py               # xlsx -> data/wells_resolved.json
python3 scripts/build_polygons_single.py       # -> data/vina_2027_thiessen_single.geojson + js/polygons-data-single.js
python3 scripts/build_polygons_three_zone.py   # -> data/vina_2027_thiessen_three_zone.geojson + js/polygons-data-three-zone.js
python3 scripts/fetch_dwr_measurements.py      # -> js/measurements-data.js (~15 MB)
python3 scripts/compute_thresholds.py          # -> data/thresholds.json
python3 scripts/build_wells_js.py              # -> js/wells-data.js
python3 scripts/build_readme_js.py             # -> js/readme-data.js (so the in-page README accordion is in sync)

# 3. open the dashboard
open index.html
```

The dashboard is pure static HTML/JS — no build step, no server. Drop it on
GitHub Pages, S3, or open `index.html` directly.

## Repo layout

```
.
├── index.html                              Dashboard shell (§5.2, §5.3, §5.4)
├── README.md                               This file (also rendered inside the dashboard)
├── BC Network 2026 v8.xlsx                 Source workbook (79 wells, RMS flags, metadata)
├── js/
│   ├── wells-data.js                       const WELLS — 79 wells joined to DWR site_code
│   ├── polygons-data-single.js             const RMS_POLYGONS_SINGLE — 27 cells (one per unique RMS site), basin-wide Voronoi
│   ├── polygons-data-three-zone.js         const RMS_POLYGONS_THREE_ZONE — 26 entries (13 N Voronoi cells + 1 dissolved Chico polygon + 12 S Voronoi cells)
│   ├── measurements-data.js                const MEASUREMENTS, MEASUREMENTS_META — periodic GWL
│   ├── basin-boundary.js                   const VINA_BOUNDARY — B118 5-021.57 GeoJSON
│   ├── readme-data.js                      const README_MD — this README bundled for the in-page accordion
│   └── main.js                             UI logic (Leaflet, Plotly, layer toggles, polygon-method picker)
├── data/                                   Intermediate JSON for the JS bundles
│   ├── wells_resolved.json                 Excel rows joined to DWR Stations
│   ├── thresholds.json                     MT/MO/IM-2027 for 30 RMS wells (12 adopted + 18 mirror); 5 supplemental Chico nested completions are monitored but unthresholded
│   ├── thresholds_2022.json                Adopted carry-overs only (7 wells, kept for provenance)
│   ├── vina_2027_thiessen_single.geojson   Single-tessellation polygons as GeoJSON
│   └── vina_2027_thiessen_three_zone.geojson  Three-zone polygons as GeoJSON
├── raw/                                    Cached raw downloads (gitignored)
│   ├── stations.csv                        DWR CKAN periodic GWL Stations resource
│   ├── vina_subbasin.geojson               DWR B118 (5-021.57) boundary
│   ├── vina_management_areas.geojson       Three Vina mgmt-area polygons (input for three-zone)
│   ├── b118_vina_esri.json                 Source Esri JSON before reshaping to GeoJSON
│   └── cosmo_wells.js                      2022 dashboard wells-data.js (for threshold carryover)
└── scripts/                                Build scripts
    ├── resolve_sites.py                    xlsx + DWR Stations -> wells_resolved.json
    ├── build_polygons_single.py            Single basin-wide tessellation (Method A below)
    ├── build_polygons_three_zone.py        Per-management-area tessellations (Method B below)
    ├── fetch_dwr_measurements.py           DWR CKAN -> measurements-data.js
    ├── compute_thresholds.py               7 adopted + 21 mirror -> thresholds.json
    ├── build_wells_js.py                   wells_resolved + thresholds -> wells-data.js
    ├── update_workbook_thresholds.py       Appends MT/MO/IM/Source columns to xlsx
    └── build_readme_js.py                  README.md -> readme-data.js
```

## How the polygons are built

> **Counts at a glance (post-2026-05-19 revision).** Both methods seed
> from the same set of **27 unique RMS sites** (35 well completions,
> with the CWSCH 7-nest and 22N01E28J 3-nest collapsing to one site each).
> - **Single tessellation** → 27 cells (one per site). The 2 Chico
>   nested sites get aggregate cells with `rms_well_swns` listing all
>   completions at that site.
> - **Three-zone tessellation** → 26 entries: 13 N Voronoi cells +
>   1 dissolved Chico mgmt-area polygon (covering the 2 nested sites)
>   + 12 S Voronoi cells.
>
> The 28-cell framing in the discussion below was the *pre-revision*
> default. The mechanics (Voronoi, projection, clipping) are unchanged;
> only the seed deduping and Chico aggregation are new. "Method B"
> below describes the current three-zone build.

A Thiessen polygon (aka Voronoi cell) for a point is the locus of points in
space that are closer to that point than to any other point in the seed set.
Used in groundwater monitoring to define the area each RMS well is
**presumed** to represent.

The dashboard ships **two complete tessellations** that answer different
questions about how the basin should be partitioned. A `Polygon method`
picker at the top of §5.2 swaps between them instantly without reloading.

| Method | Output | When to use |
|---|---|---|
| **Three-zone tessellation** (default) | 26 entries: 13 N Voronoi cells + 1 dissolved Chico mgmt-area polygon (covering the 2 nested 2022 GSP RMS sites) + 12 S Voronoi cells. No N or S cell overlaps Chico. | SMC-defensible view: each management area carries distinct sustainability criteria, so partitioning *within* each area gives a self-contained polygon-by-polygon story. Chico's hydrogeology is better captured by the nested sites than by Voronoi subdivision. |
| **Single tessellation** | 27 cells, one Voronoi per unique RMS site. The 2 Chico nested sites get aggregate cells (carrying `rms_well_swns` for all completions at that site). | Basin-wide proximity view; closer to the original 2022 dashboard. |

Both methods share the same foundations (Step 1 below: seeds, Step 2:
project to EPSG:3310). They diverge on the **clip boundary** (basin vs.
mgmt-area polygons) and on **how Chico is handled** (Chico is dissolved
in three-zone; in single it's just whatever 2 cells the Voronoi gives
for the 2 nested sites). The diagrams below walk each one through.

### Step 1 (shared): Pick the seeds

Read `BC Network 2026 v8.xlsx`. Keep every row where column **E (`2027 GWL
RMS?`) = "Yes"**. After the 2026-05-19 revision this yields **35 well
completions** which deduplicate by `(latitude, longitude)` to **27 unique
RMS sites**:

| RMS sites (network design) | Sites | Wells (completions) |
|-----------|-------|-------|
| 01-Vina-North (network) | 13 | 11 in N + 3 physically in Chico but RMS-for-North (`22N01E09B001M`, `22N01E20K001M`, `23N01E33A001M`) |
| 02-Vina-Chico | 2 sites / 10 completions | CWSCH 7-nest: `CWSCH01b/02/03/04/05/06/07`. 22N01E28J 3-nest: `22N01E28J001M/003M/005M`. |
| 03-Vina-South | 12 | 12 individual wells |

Coordinates come from columns **L (latitude)** and **M (longitude)**. A
new `rms_mgmt_area` field in `wells_resolved.json` captures the
network-design mgmt-area assignment, which can differ from the workbook
`mgmt_area_full` (geographic). For the 2 reassigned wells
(`22N01E09B001M`, `22N01E20K001M`) `rms_mgmt_area = "01-Vina-North"`
while `mgmt_area_full` stays `"02-Vina-Chico"`.

### Step 2 (shared): Project to an equal-area metric CRS

Voronoi tessellation only behaves sensibly in a Euclidean metric. Lat/lon
degrees aren't Euclidean — a degree of longitude at 39.7° N is about 23 %
shorter than a degree of latitude. So before computing any diagram we
project both seeds and clip boundaries from **WGS-84 (EPSG:4326)** into
**NAD-83 California Albers Equal Area (EPSG:3310)** using `pyproj`.
EPSG:3310 is the standard DWR / Bulletin 118 working CRS, so polygon areas
in the dashboard match what you'd compute against the official DWR layers.

### Method A — Single tessellation

`scripts/build_polygons_single.py`.

**Clip boundary**: Vina Subbasin (`Basin_Subbasin_Number = '5-021.57'`)
pulled from the DWR ArcGIS REST service, then converted from Esri JSON to
GeoJSON locally with Shapely. Lives at `raw/vina_subbasin.geojson` — a
single Polygon with a 1,729-vertex outer ring (~184,000 acres).

**Tessellation**: `scipy.spatial.Voronoi` over all 27 unique site
coordinates at once (35 well completions deduped by lat/lng — scipy
can't handle coincident points). Four anchor points 10× the basin
bounding box outside ensure every real cell is bounded (SciPy emits open
rays for hull sites otherwise). Each finite cell is intersected with the
Albers-projected basin polygon, so cell edges along the basin perimeter
follow the official B118 line. For the 2 Chico nested sites, the cell
emits with `is_aggregate: true` and `rms_well_swns: [...]` carrying the
SWNs of all completions at that location.

**Export**:
- `data/vina_2027_thiessen_single.geojson` — GeoJSON FeatureCollection
- `js/polygons-data-single.js` — `const RMS_POLYGONS_SINGLE = [...]`, rings
  in `[lat, lng]` order for Leaflet

Sanity check: 27 cells total **~184,400 acres** — within 0.3% of the
published Vina Subbasin area (post-revision: 2 Chico cells are aggregate
sites for the CWSCH and 22N01E28J nests).

### Method B — Three-zone (per-mgmt-area) — 2026-05-19+ revision

`scripts/build_polygons_three_zone.py`.

The three management areas are handled with **different polygon
strategies** that reflect how the GSA's stakeholders want each area
represented. **No polygon overlaps with the Chico management area.**

**North** — 13 wells, **Voronoi cells**, all clipped to
`(Basin − Chico mgmt area − South mgmt area)`. The Voronoi is computed
directly over that clipped domain using all 13 seeds; scipy handles
seeds that sit *outside* the clip domain correctly (their Voronoi
regions still extend into the domain wherever they're the nearest seed).
Three of the 13 RMS wells (`22N01E09B001M`, `22N01E20K001M`,
`23N01E33A001M`) physically sit inside the Chico management area; their
clipped cells therefore sit *north* of where the well markers are drawn.
The cells together tile the entire `(Basin − Chico − South)` region, so
any sliver between mgmt-area boundaries on the W and E edges is
absorbed into the adjacent N cell — no orphan slivers.

**Chico** — **one dissolved polygon** = the entire Chico mgmt area
boundary (no internal Voronoi subdivision). Associated with **10 well
completions across 2 nested 2022 GSP RMS sites**: the CWSCH 7-nest
(CWSCH01b/02/03/04/05/06/07) and the 22N01E28J 3-nest
(22N01E28J001M/003M/005M). The dashboard renders this as a single
§5.3 picker entry; selecting it plots all 10 well traces in the
hydrograph. Of the 10, **5 have 2022 GSP thresholds**
(CWSCH01b/02/03/07 and 22N01E28J003M — matching the 2022 GSP's
"primary completion" convention); the other 5 are monitored but
unthresholded, again matching 2022 GSP.

**South** — 12 wells, **Voronoi cells**, clipped to the South mgmt
area.

**Drawing order** in the dashboard: the output JS array is
`[Chico, ...North, ...South]`. Leaflet draws polygons in array order,
so the Chico aggregate sits at the back of the SVG; the 13 North
cells (and 12 South cells) overlay on top. The 3 Chico-located N
wells' cells do *not* overlap with Chico (they sit north of those
wells), so there's no visible overlay in Chico mgmt area — Chico
appears as the peach mgmt-area background only.

The dashboard uses dedicated Leaflet panes (`polygonsPane` z-index 400,
`wellsPane` z-index 450) so the well markers always sit above polygons
regardless of toggle order. The well markers for the 3 Chico-located N
RMS wells appear inside Chico (their physical location); clicking them
shows a popup that calls out the "well location inside Chico mgmt area,
RMS for the North network" relationship.

**Membership**: comes from the `rms_mgmt_area` field in
`wells_resolved.json` (the network-design assignment, which can differ
from the geographic `mgmt_area_full`). For the 2 reassigned wells
(`22N01E09B001M`, `22N01E20K001M`), `rms_mgmt_area = "01-Vina-North"`
while `mgmt_area_full` stays `"02-Vina-Chico"`. Every polygon feature
also carries `workbook_mgmt_area` and `reassigned: true|false` for
the audit trail, and `well_in_chico_mgmt_area: true|false` derived
from spatial containment so the dashboard popup can call out the
3 wells whose physical location is in Chico.

**Export**:
- `data/vina_2027_thiessen_three_zone.geojson` — FeatureCollection of 26 features
- `js/polygons-data-three-zone.js` — `const RMS_POLYGONS_THREE_ZONE = [...]`
- The Chico aggregate entry carries `is_aggregate: true`,
  `rms_well_swns: [...10 SWNs]`, and a custom `rms_label` for the picker

Sanity check: total 26 entries (13 N + 1 Chico + 12 S). The 13 N
cells together cover **~72,000 ac** (= basin − Chico − South within
rounding); the Chico aggregate is **~29,700 ac** (full mgmt area); the
12 S cells are **~83,000 ac** (= full South mgmt area). N-Chico
overlap: **0 ac**.

### Per-polygon areas (post-2026-05-19+ revision)

Acres are rounded to the nearest integer. In three-zone, the 3
Chico-located N RMS wells (marked ⚑) have polygons in N (north of where
the well marker sits), not in Chico — their cell area is whatever piece
of (Basin − Chico − South) is closer to that well than any other N
seed. Both methods' totals are within rounding of 184,400 ac (the Vina
Subbasin).

| site / polygon | mgmt area (network) | acres (single) | acres (three-zone) |
|---|---|---:|---:|
| 22N01W05M001M | North | 7,541 | 7,541 |
| 23N01E07H001M | North | 8,272 | 8,272 |
| ⚑ 23N01E33A001M | North (in Chico geo) | 10,782 | 9,963 |
| 23N01W36P001M | North | 7,088 | 7,088 |
| 23N02W25C001M | North | 5,850 | 5,850 |
| 23N01E29P002M | North | 3,968 | 3,896 |
| 23N01W09E001M | North | 5,311 | 5,311 |
| 23N01W10M001M | North | 3,522 | 3,522 |
| 23N01W14R002M | North | 3,975 | 3,975 |
| 23N01W27L001M | North | 3,166 | 3,166 |
| 23N01W28M004M | North | 3,359 | 3,359 |
| ⚑ 22N01E20K001M | North (in Chico geo) | 9,007 | 8,147 |
| ⚑ 22N01E09B001M | North (in Chico geo) | 6,739 | 1,966 |
| 02-Vina-Chico (dissolved, 10 wells) | Chico | — | 29,718 |
| `CWSCH` 7-nest (single tess. cell) | Chico | 13,605 | (covered by Chico aggregate) |
| `22N01E28J` 3-nest (single tess. cell) | Chico | 2,820 | (covered by Chico aggregate) |
| 20N02E24C001M | South | 7,863 | 7,861 |
| 21N02E18C003M | South | 12,365 | 5,244 |
| 20N01E02H003M | South | 5,202 | 5,200 |
| 20N02E09G001M | South | 6,522 | 6,521 |
| 20N03E33L001M | South | 5,182 | 5,186 |
| 21N01E10B003M | South | 5,839 | 6,650 |
| 21N01E13L004M | South | 2,713 | 2,713 |
| 21N01E25K001M | South | 2,748 | 2,748 |
| 21N01E27D001M | South | 10,931 | 10,825 |
| 21N02E26E006M | South | 11,791 | 11,480 |
| 21N02E32E001M | South | 4,534 | 4,534 |
| 21N03E32B001M | South | 14,223 | 14,225 |

### How the dashboard chooses

`index.html` loads both `polygons-data-single.js` and
`polygons-data-three-zone.js` as siblings; `js/main.js` keeps a swappable
`RMS_POLYGONS` reference pointing at whichever set the `Polygon method`
picker has selected. Switching the picker calls `setPolygonMethod()`,
which clears and rebuilds the Leaflet polygon layer, re-populates the
§5.3 picker (so the mgmt-area-prefixed label updates for the reassigned
well), and re-selects the previously-active well if it still exists in
the new set — which it always does, since both methods carry the same 28
SWNs as keys.

### Method-specific notes

The 2022 reference dashboard had a few special-cases worth flagging:

1. **Chico dissolve.** The 2022 build merged three Chico cells into one
   polygon to match a GSP figure. Post-2026-05-19 the **three-zone
   method now does this too** (Chico is one dissolved mgmt-area polygon).
   The single tessellation method does not — each of its 27 RMS sites
   gets its own cell.
2. **Named-polygon overrides.** The 2022 build had hard-coded "this RMS
   well belongs to that polygon" rules for geographic edge cases
   (e.g. `23N01E33A001M`). The single-tessellation method doesn't need
   them; the three-zone method handles the same edge case **via spatial
   assignment with an auditable `reassigned` flag** rather than a manual
   override.

## MT / MO / IM-2027 threshold methodology

The dashboard shows Sustainable Management Criteria (SMC) threshold lines on
every 2027 RMS well's hydrograph. Values come from one of two sources, both
expressed as **groundwater elevation in ft msl** (not depth-below-RPE):

### Source 1 — "2022 GSP" (adopted, 9 wells)

These are the **Minimum Threshold (MT)**, **Measurable Objective (MO)**,
and **Interim Milestone for 2027 (IM-2027)** values carried over
**unchanged** from the 2022 Vina GSP for the 9 wells that are in both
the 2022 and 2027 RMS networks. Rendered with **dashed** lines in §5.3
hydrographs and labeled with the "GSP-adopted MT/MO" pill in the §5.3
table.

| Well | Mgmt area | MT | MO | IM-2027 | Notes |
|---|---|---|---|---|---|
| 22N01W05M001M | North | 31 | 115 | 116 | |
| 23N01E07H001M | North | 72 | 136 | 140 | |
| 23N01E33A001M | North | 72 | 125 | 128 | well location in Chico mgmt area |
| 23N01W36P001M | North | 45 | 108 | 110 | |
| 23N02W25C001M | North | 50 | 130 | 130 | |
| 20N02E24C001M | South | 18 | 77 | 81 | |
| 21N02E18C003M | South | 65 | 130 | 132 | |
| 21N02E26E006M | South | 36 |  95 |  97 | inherits from `21N02E26E005M`, the 2022 GSP RMS at this same lat/lng (retired from 2027, different completion depth) |
| CWSCH01b | Chico | 85 | 106 | 107 | the only RMS at the Chico aggregate; 9 nested-completion supplementals plot for context but are unthresholded |

### Source 2 — "2022 Mirror" (new buffer-based methodology, 17 wells)

The other 17 wells in the 2027 RMS network were not RMS wells in 2022,
so they have no carry-over GSP values. **As of the 2026-05-21 revision**,
the Mirror baseline is derived from a regional **MT-buffer analysis** of
the original 2022 GSP RMS network. This replaces the prior "MT ≈
drought_min − 70" coefficient. Rendered with **dotted** lines in §5.3
hydrographs and labeled with the "2022 mirror MT/MO" pill in the §5.3
table.

#### MT Buffer Analysis — the 2022 GSP RMS benchmark

**Purpose.** For each well designated 2022 GWL RMS in the Vina GSP,
calculate the buffer (in feet) between the GSP's per-well MT and the
lowest QA-Good GWE on record. Aggregate by management area to produce
a regional benchmark for how much historical headroom exists above the
MT.

**Method.** For each 2022 GWL RMS well excluding the four CWSCH nested
completions (CWSCH01b/02/03/07 — they share a single Chico pad and
would skew aggregate statistics):

1. Pull the full DWR CKAN periodic-measurement record (resource
   `bfa9f262-24a1-45bd-8dc8-138bc8107266`).
2. Restrict to `QA = "Good"` readings (drop Questionable / Missing flags).
3. Identify the all-time observed minimum GWE (`min_GWE`).
4. Compute `buffer = min_GWE − MT` (feet). MT values are taken from the
   2022 GSP / 2025 Annual Report.
5. Average by mgmt area (North, South, Chico).

**Data scope.** DWR CKAN periodic measurements through the dashboard's
last refresh date. 13 RMS wells in the benchmark (17 designated 2022
GWL RMS minus 4 CWSCH wells). Period of record and monitoring frequency
vary by well — hourly transducer sites carry >20,000 Good readings;
quarterly-monitoring sites carry as few as 14.

**Results** (the regional benchmarks used to derive MT for the 17
non-carryover wells):

| Region | n RMS wells | Avg buffer (ft) | Range (ft) |
|---|---:|---:|---|
| Chico  | 1  | 27.93 | single well (22N01E28J003M) |
| North  | 6  | 69.55 | 58.45 – 81.50 |
| South  | 6  | 57.60 | 38.63 – 71.15 |
| Overall | 13 | 60.83 | 27.93 – 81.50 |

#### Applying the buffer to derive Mirror MT/MO/IM

For each of the 17 non-carryover 2027 RMS wells:

```
alltime_min = min GWE on the full DWR record, QA=Good only
drought_min = min GWE during 2012-2016 + 2020-2022 drought windows
region_buf  = regional buffer (69.55 N, 57.60 S, 27.93 Chico) — KEYED
              ON NETWORK rms_mgmt_area, not geographic mgmt_area_full

MT_ft       = round(alltime_min − region_buf)
MO_ft       = round(drought_min)         [unchanged from prior Mirror]
IM_2027_ft  = round(drought_min + 2)     [unchanged from prior Mirror]
```

**Why use network mgmt area for the buffer?** These wells are
designated as RMS for a specific network's monitoring purposes; the
buffer they should be benchmarked against is the buffer of that
network. So the 2 wells that are RMS for the North network but
physically inside Chico mgmt area (`22N01E09B001M`, `22N01E20K001M`)
use the North buffer (69.55 ft), consistent with their role as North
RMS wells.

**Why two different "low" bases for MT vs MO?** MT uses all-time min
(matches the 2022 GSP MT-buffer benchmark exactly). MO uses
drought-window min so MO retains a "measurable objective tied to
drought-period hydrology" interpretation consistent with how the GSA
treated MO in 2022.

### Caveats

The Mirror methodology is a defensible interim baseline, not an adopted
SMC. Specific limitations:

- **Buffer reflects the observed historical low, not the true low.**
  Wells with short records or sparse monitoring may understate how low
  water levels actually got. Buffers derived from such wells are
  conservative (the buffer benchmark may be smaller than what would be
  observed with more data).
- **The Chico regional buffer (27.93 ft) comes from a single well**
  (22N01E28J003M) after CWSCH exclusion. Thin coverage for a whole
  management area — a caveat worth flagging in any downstream use of
  the Chico average.
- **Buffer is a descriptive statistic, not a margin of safety or
  forward projection.** It does not account for drought severity,
  climate change, or pumping trajectories. It is a backward-looking
  measure of how close historical lows came to the GSP MT.
- **No traceable derivation document for the 2022 GSP MT values.**
  AGUBC, Butte County, and Vina GSA staff have searched for the
  methodology memo that drove the original 2022 MT/MO/IM values; no
  documentation has surfaced (it may have lived with a former
  consultant). The buffer benchmark is the most faithful empirical
  reconstruction available.
- **The Mirror is NOT a request for GSA approval.** Adopted MT/MO/IM
  remain the 2022 GSP values until the GSA formally updates them in
  the 2027 GSP cycle. The Mirror exists solely to give the dashboard
  a complete set of comparison lines so every polygon's hydrograph can
  be evaluated in the same visual framework.

### How to apply the buffer benchmark in other dashboards

To use the regional averages as a reference benchmark in another
dashboard, compute an "expected operating low GWE" from any well's MT:

```
expected_low_GWE = MT + region_avg_buffer
```

**Example.** A North-region RMS well with `MT = 50 ft msl` carries an
expected operating low of `50 + 69.55 ≈ 119.55 ft msl` based on the
regional buffer benchmark. Wells whose actual observed lows fall
meaningfully below this benchmark (smaller buffers than peers) are
candidates for closer attention in the next GSP periodic evaluation.

For visualization, the benchmark can be drawn on a per-well hydrograph
as a dashed horizontal line at `MT + region_avg_buffer`, alongside the
existing MT / MO / IM-2027 reference lines.

### Rebuilding

```bash
python3 scripts/compute_thresholds.py          # -> data/thresholds.json
python3 scripts/build_wells_js.py              # -> js/wells-data.js
python3 scripts/update_workbook_thresholds.py  # -> appends MT/MO/IM/Source columns to xlsx
```

The workbook now carries four trailing columns (W–Z) — `MT_ft`, `MO_ft`,
`IM_2027_ft`, `Threshold_Source` — populated for 30 RMS wells (the 35
RMS-flagged completions minus the 5 supplemental Chico nested completions
that the 2022 GSP did not threshold), with 2022 GSP rows shaded light
blue and 2022 Mirror rows shaded warm cream.

---

## Data sources

| Layer | Source | Endpoint |
|-------|--------|----------|
| Wells (network membership, metadata) | `BC Network 2026 v8.xlsx` | local file |
| DWR site_code resolution | DWR CKAN Stations resource | https://data.cnra.ca.gov/dataset/periodic-groundwater-level-measurements (resource `af157380-...`) |
| Periodic GWL measurements | DWR CKAN Measurements resource | same dataset, resource `bfa9f262-24a1-45bd-8dc8-138bc8107266` (filtered to network sites via `datastore_search` API) |
| Vina Subbasin boundary | DWR ArcGIS REST i08 B118 | `Basin_Subbasin_Number='5-021.57'` |
| MT / MO / IM-2027 thresholds | 2022 Vina GSP, carried via the cosmo1007 wells-data.js | only set for the 7 wells in both 2022 and 2027 RMS networks |

DWR refresh stamp is shown in the page header — it comes from
`MEASUREMENTS_META.fetched_at` in `js/measurements-data.js`. To refresh, just
re-run `scripts/fetch_dwr_measurements.py`.

## Acknowledgements

Built for the AGUBC 2027 GSP update. Layout & color palette mirror the 2022
RMS dashboard so reviewers familiar with the prior cycle have a near-zero
learning curve. The Voronoi pipeline is a clean reimplementation against
the original workbook (no inheritance of the Chico-dissolve or override
logic baked into the 2022 builder).
