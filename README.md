# Vina Subbasin 2027 RMS Network Dashboard

Static interactive dashboard for the 2027 Representative Monitoring Site (RMS)
network in the Vina Subbasin (DWR B118 5-021.57), Butte County, California.

Built from `BC Network 2026 v8.xlsx` and modeled on the
[2022 RMS reference dashboard](https://cosmo1007.github.io/2022-rms-network/).

> **2026-05-19 network revision.** The 2027 RMS network was restructured
> based on stakeholder input. The proposed network is now **35 well
> completions across 26 polygons**: 13 North (Voronoi cells, including
> 2 wells physically in Chico that are RMS for the North network), 1
> dissolved Chico mgmt-area polygon (10 well completions across the 2
> 2022 GSP nested sites: CWSCH and 22N01E28J), and 12 South (Voronoi
> cells). Replaces the prior 28-cell three-zone tessellation. See
> "Method B" below and PROJECT_NOTES for rationale.

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
│   ├── polygons-data-single.js             const RMS_POLYGONS_SINGLE — 28 cells, basin-wide Voronoi
│   ├── polygons-data-three-zone.js         const RMS_POLYGONS_THREE_ZONE — 28 cells, per-mgmt-area Voronoi
│   ├── measurements-data.js                const MEASUREMENTS, MEASUREMENTS_META — periodic GWL
│   ├── basin-boundary.js                   const VINA_BOUNDARY — B118 5-021.57 GeoJSON
│   ├── readme-data.js                      const README_MD — this README bundled for the in-page accordion
│   └── main.js                             UI logic (Leaflet, Plotly, layer toggles, polygon-method picker)
├── data/                                   Intermediate JSON for the JS bundles
│   ├── wells_resolved.json                 Excel rows joined to DWR Stations
│   ├── thresholds.json                     MT/MO/IM-2027 for all 28 RMS wells (7 adopted + 21 mirror)
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

## How the 28 Thiessen polygons are built

A Thiessen polygon (aka Voronoi cell) for a point is the locus of points in
space that are closer to that point than to any other point in the seed set.
Used in groundwater monitoring to define the area each RMS well is
**presumed** to represent.

The dashboard ships **two complete tessellations** — both methods produce
exactly 28 cells (one per 2027 RMS well), but they answer different
questions about how the basin should be partitioned. A `Polygon method`
picker at the top of §5.2 swaps between them instantly without reloading.

| Method | What it is | When to use |
|---|---|---|
| **Single tessellation** (default) | One Voronoi diagram across the whole Vina Subbasin, clipped to DWR B118 5-021.57 | Basin-wide proximity view; matches the original dashboard on `main` prior to this branch |
| **Three-zone tessellation** | Three independent Voronoi diagrams — one per management area — each clipped to its own management-area polygon. Cells do not cross management-area lines | SMC-defensible view: each management area carries distinct sustainability criteria, so partitioning *within* each area gives a self-contained polygon-by-polygon story |

Both methods share the same foundations (steps 1, 3, common technical
details in step 4); they diverge on the **clip boundary** (basin polygon
vs. mgmt-area polygons) and on how seeds are **grouped before the Voronoi
runs** (all 28 together vs. partitioned by area). The diagrams below walk
each one through.

### Step 1 (shared): Pick the seeds

Read `BC Network 2026 v8.xlsx`. Keep every row where column **E (`2027 GWL
RMS?`) = "Yes"**. That yields exactly **28 wells**:

| Mgmt Area (workbook tag) | Count | Wells |
|-----------|-------|-------|
| 01-Vina-North | 13 | 22N01W05M001M, 23N01E07H001M, 23N01E29P002M, 23N01E33A001M, 23N01W03H004M, 23N01W09E001M, 23N01W10M001M, 23N01W14R002M, 23N01W27L001M, 23N01W28M004M, 23N01W31M004M, 23N01W36P001M, 23N02W25C001M |
| 02-Vina-Chico |  2 | 22N01E09B001M, 22N01E20K001M |
| 03-Vina-South | 13 | 20N01E02H003M, 20N02E08H003M, 20N02E09G001M, 20N02E24C001M, 20N03E33L001M, 21N01E10B003M, 21N01E13L004M, 21N01E25K001M, 21N01E27D001M, 21N02E18C003M, 21N02E26E006M, 21N02E32E001M, 21N03E32B001M |

Coordinates come from columns **L (latitude)** and **M (longitude)**. Each
build script asserts `len(seeds) == 28` and aborts otherwise — so if the
workbook changes RMS flags, you get a hard failure instead of silent drift.

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

**Tessellation**: `scipy.spatial.Voronoi` over all 28 projected seeds at
once. Four anchor points 10× the basin bounding box outside ensure every
real cell is bounded (SciPy emits open rays for hull sites otherwise).
Each finite cell is intersected with the Albers-projected basin polygon,
so cell edges along the basin perimeter follow the official B118 line.

**Export**:
- `data/vina_2027_thiessen_single.geojson` — GeoJSON FeatureCollection
- `js/polygons-data-single.js` — `const RMS_POLYGONS_SINGLE = [...]`, rings
  in `[lat, lng]` order for Leaflet

Sanity check: 28 cells total **~184,400 acres** — within 0.3% of the
published Vina Subbasin area.

### Method B — Three-zone (per-mgmt-area) — 2026-05-19 revision

`scripts/build_polygons_three_zone.py`.

The three management areas are handled with **different polygon
strategies** that reflect how the GSA's stakeholders want each area
represented:

**North** — 13 wells, **Voronoi cells**. The clip domain is the union of
the North mgmt area and the Chico mgmt area, so that the cells around
the **2 wells reassigned to the North RMS network despite physically
sitting in Chico** (`22N01E09B001M`, `22N01E20K001M`) extend southward
into Chico territory naturally. The two Chico nested-site coordinates
are added as **phantom Voronoi seeds** when computing the diagram so
that those two cells don't dominate the entire southern half of N∪C
(without the phantoms, scipy gives them a Voronoi region bounded only
by the basin boundary; with them, the cells are bounded by the Chico
sites' midlines — typical area 7,000–9,000 ac instead of 18,000+).
The phantom seeds' cells are computed and then discarded — Chico's
territory is represented by the aggregate polygon below.

**Chico** — **one dissolved polygon** = the entire Chico mgmt area
boundary (no internal Voronoi subdivision). Associated with **10 well
completions across 2 nested 2022 GSP RMS sites**: the CWSCH 7-nest
(CWSCH01b/02/03/04/05/06/07) and the 22N01E28J 3-nest
(22N01E28J001M/003M/005M). The dashboard renders this as a single
picker entry; selecting it plots all 10 well traces in §5.3. Of the
10, **5 have 2022 GSP thresholds** (CWSCH01b/02/03/07 and 22N01E28J003M
— matching the 2022 GSP's "primary completion" convention); the other
5 are monitored but unthresholded, again matching 2022 GSP.

**South** — 12 wells, **Voronoi cells**, clipped to South mgmt area.
Straightforward — same approach as the prior three-zone build.

**Drawing order** in the dashboard: the output JS array is
`[Chico, ...North, ...South]`, which determines the SVG draw order in
the Leaflet `polygonsPane`. Chico is drawn first (at the back); the 13
North cells overlay on top, so the 2 reassigned-well cells that extend
into Chico territory are visible against the Chico fill. The dashboard
uses dedicated Leaflet panes (`polygonsPane` z-index 400,
`wellsPane` z-index 450) so the well markers always sit above polygons
regardless of toggle order.

**Membership**: comes from a new `rms_mgmt_area` field in
`wells_resolved.json` (the network-design assignment, which can differ
from the geographic `mgmt_area_full`). For the 2 Chico-located North
wells, `rms_mgmt_area = "01-Vina-North"` while `mgmt_area_full` stays
`"02-Vina-Chico"`. Every polygon feature also carries
`workbook_mgmt_area` and `reassigned: true|false` for the audit trail.

**Export**:
- `data/vina_2027_thiessen_three_zone.geojson` — FeatureCollection of 26 features
- `js/polygons-data-three-zone.js` — `const RMS_POLYGONS_THREE_ZONE = [...]`
- The Chico aggregate entry carries `is_aggregate: true`,
  `rms_well_swns: [...10 SWNs]`, and a custom `rms_label` for the picker

Sanity check: total 26 entries (1 + 13 + 12). The Chico polygon covers
the entire Chico mgmt area (~29,718 ac); the 2 reassigned-North cells
overlap into Chico for a total of ~7,200 ac — this overlap is
intentional and matches the user-requested "north cells overlay Chico"
visual.

### Per-polygon areas (both methods)

The reassigned well's cell shrinks dramatically when constrained to its
spatial zone; its old neighbors absorb the released area. Other cells are
similar between methods; differences are largest along the management-area
boundaries.

| polygon | mgmt area (single) | acres (single) | mgmt area (three-zone) | acres (three-zone) |
|---|---|---:|---|---:|
| 22N01W05M001M | 01-Vina-North |  7,047 | 01-Vina-North |  7,468 |
| 23N01E07H001M | 01-Vina-North |  7,823 | 01-Vina-North |  8,342 |
| **23N01E33A001M** | 01-Vina-North | **11,053** | **02-Vina-Chico (reassigned)** | **1,092** |
| 23N01W36P001M | 01-Vina-North |  7,089 | 01-Vina-North | 15,173 |
| 23N02W25C001M | 01-Vina-North |  4,902 | 01-Vina-North |  4,900 |
| 23N01E29P002M | 01-Vina-North |  3,968 | 01-Vina-North | 14,798 |
| 23N01W03H004M | 01-Vina-North |  1,997 | 01-Vina-North |  1,996 |
| 23N01W09E001M | 01-Vina-North |  5,285 | 01-Vina-North |  5,275 |
| 23N01W10M001M | 01-Vina-North |  2,110 | 01-Vina-North |  2,110 |
| 23N01W14R002M | 01-Vina-North |  3,865 | 01-Vina-North |  3,865 |
| 23N01W27L001M | 01-Vina-North |  3,166 | 01-Vina-North |  3,166 |
| 23N01W28M004M | 01-Vina-North |  3,227 | 01-Vina-North |  3,227 |
| 23N01W31M004M | 01-Vina-North |  1,575 | 01-Vina-North |  1,575 |
| 22N01E20K001M | 02-Vina-Chico | 11,638 | 02-Vina-Chico | 12,799 |
| 22N01E09B001M | 02-Vina-Chico | 11,159 | 02-Vina-Chico | 15,827 |
| 20N02E24C001M | 03-Vina-South |  7,863 | 03-Vina-South |  7,861 |
| 21N02E18C003M | 03-Vina-South | 17,184 | 03-Vina-South |  5,244 |
| 20N01E02H003M | 03-Vina-South |  4,899 | 03-Vina-South |  4,897 |
| 20N02E08H003M | 03-Vina-South |  3,458 | 03-Vina-South |  3,457 |
| 20N02E09G001M | 03-Vina-South |  4,209 | 03-Vina-South |  4,209 |
| 20N03E33L001M | 03-Vina-South |  5,182 | 03-Vina-South |  5,186 |
| 21N01E10B003M | 03-Vina-South | 10,124 | 03-Vina-South |  6,650 |
| 21N01E13L004M | 03-Vina-South |  2,713 | 03-Vina-South |  2,713 |
| 21N01E25K001M | 03-Vina-South |  2,748 | 03-Vina-South |  2,748 |
| 21N01E27D001M | 03-Vina-South | 10,931 | 03-Vina-South | 10,825 |
| 21N02E26E006M | 03-Vina-South | 11,791 | 03-Vina-South | 11,480 |
| 21N02E32E001M | 03-Vina-South |  3,692 | 03-Vina-South |  3,692 |
| 21N03E32B001M | 03-Vina-South | 14,223 | 03-Vina-South | 14,225 |

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

### What neither version does

The 2022 reference dashboard had two special-cases worth flagging in case
they come back into scope:

1. **Chico dissolve.** The 2022 build merged three Chico cells into one
   polygon to match a GSP figure. Neither 2027 method does this — each of
   the 28 RMS wells gets its own cell.
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

### Source 1 — "2022 GSP" (adopted, 12 wells)

These are the **Minimum Threshold (MT)**, **Measurable Objective (MO)**, and
**Interim Milestone for 2027 (IM-2027)** values carried over **unchanged**
from the 2022 Vina GSP for the 12 wells (7 from the original 2027 RMS plus
5 Chico primaries added in the 2026-05-19 revision) that are in both the
2022 and 2027 RMS networks. Rendered with **dashed** lines in §5.3
hydrographs and labeled with the "GSP-adopted MT/MO" pill in the §5.3
table.

| Well | Mgmt area | MT | MO | IM-2027 |
|---|---|---|---|---|
| 22N01W05M001M | North | 31 | 115 | 116 |
| 23N01E07H001M | North | 72 | 136 | 140 |
| 23N01E33A001M | North | 72 | 125 | 128 |
| 23N01W36P001M | North | 45 | 108 | 110 |
| 23N02W25C001M | North | 50 | 130 | 130 |
| CWSCH01b | Chico | 85 | 106 | 107 |
| CWSCH02 | Chico | 85 | 105 | 108 |
| CWSCH03 | Chico | 85 | 108 | 109 |
| CWSCH07 | Chico | 85 |  95 |  97 |
| 22N01E28J003M | Chico | 85 | 111 | 113 |
| 20N02E24C001M | South | 18 | 77 | 81 |
| 21N02E18C003M | South | 65 | 130 | 132 |

The 5 supplemental Chico nested completions (CWSCH04/05/06,
22N01E28J001M/005M) are monitored but unthresholded, matching the 2022
GSP convention.

### Source 2 — "2022 Mirror" (baseline pending GSA review, 21 wells)

The other 21 wells in the 2027 RMS network were not RMS wells in 2022, so
they have no carry-over GSP values. To give every polygon a usable baseline
in the dashboard pending formal GSA action, this build computes
**MT / MO / IM-2027** by mirroring the empirical pattern of the seven
already-adopted thresholds.

> **Proposed values mirror the empirical pattern of the adopted 2022
> thresholds (MT ≈ 70 ft below drought minimum, MO ≈ drought minimum,
> IM ≈ MO + 2 ft); formal derivation pending.**

Rendered with **dotted** lines in §5.3 hydrographs and labeled with the
"2022 mirror MT/MO" pill in the §5.3 table.

**Formulas** (all in ft msl, rounded to nearest 1 ft):

```
drought_min = min GWE recorded during 2012-2016 + 2020-2022 drought windows
              (DWR Periodic Measurements, all QA flags)

MT_ft       = round(drought_min − 70)
MO_ft       = round(drought_min)
IM_2027_ft  = round(MO + 2)
```

**Why these coefficients?** Empirically, across the 7 adopted-threshold
wells: MT_22 sits a mean of −68.5 ft (median −66 ft) below `drought_min`;
MO_22 sits within ±6 ft of `drought_min` (mean offset effectively zero);
IM_22 sits a mean of +2.3 ft above MO_22. The Mirror formulas round these
to clean coefficients (−70 / 0 / +2).

### Caveats

The Mirror methodology is a defensible interim baseline, not an adopted
SMC. Specific limitations to flag in any external use:

- **No traceable derivation document for the 2022 GSP values.** AGUBC,
  Butte County, and Vina GSA staff have searched for the methodology memo
  that drove the original 2022 MT/MO/IM values; no documentation has
  surfaced (it may have lived with a former consultant). The Mirror
  approach is the most faithful empirical reconstruction available.
- **All 21 Mirror wells have abundant drought-window data** (minimum 14
  readings, most have 30+; nine continuous-logger wells have 1,000+
  readings during the 2012-16 / 2020-22 windows). No well in the 2027
  network triggers a low-drought-data flag. If a future RMS swap brings
  in a well with <3 drought-window readings, the threshold for that well
  should be flagged in the dashboard and reviewed before being plotted.
- **One MT value is below mean sea level** — `21N01E13L004M` MT = −11 ft
  msl. This is physically valid: its drought minimum is +59 ft msl with
  a 353-ft-deep well that bottoms well below sea level, so −11 ft msl
  is ~70 ft above the well bottom. Reviewers should confirm the value
  visually but it is not a computational error.
- **The Mirror is NOT a request for GSA approval.** Adopted MT/MO/IM
  remain the 2022 GSP values until the GSA formally updates them in
  the 2027 GSP cycle. The Mirror exists solely to give the dashboard
  a complete set of comparison lines so every polygon's hydrograph can
  be evaluated in the same visual framework.

### Rebuilding

```bash
python3 scripts/compute_thresholds.py          # -> data/thresholds.json
python3 scripts/build_wells_js.py              # -> js/wells-data.js
python3 scripts/update_workbook_thresholds.py  # -> appends MT/MO/IM/Source columns to xlsx
```

The workbook now carries four trailing columns (W–Z) — `MT_ft`, `MO_ft`,
`IM_2027_ft`, `Threshold_Source` — populated for all 28 RMS wells, with
2022 GSP rows shaded light blue and 2022 Mirror rows shaded warm cream.

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
