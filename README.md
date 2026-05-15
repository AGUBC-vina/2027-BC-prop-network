# Vina Subbasin 2027 RMS Network Dashboard

Static interactive dashboard for the 2027 Representative Monitoring Site (RMS)
network in the Vina Subbasin (DWR B118 5-021.57), Butte County, California.

Built from `BC Network 2026 v8.xlsx` and modeled on the
[2022 RMS reference dashboard](https://cosmo1007.github.io/2022-rms-network/).

- **§5.2** — Interactive Leaflet map (basin boundary, 28 Thiessen polygons,
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
python3 scripts/resolve_sites.py             # xlsx -> data/wells_resolved.json
python3 scripts/build_polygons.py            # -> data/vina_2027_thiessen.geojson + js/polygons-data.js
python3 scripts/build_wells_js.py            # -> js/wells-data.js
python3 scripts/fetch_dwr_measurements.py    # -> js/measurements-data.js (~15 MB)

# 3. open the dashboard
open index.html
```

The dashboard is pure static HTML/JS — no build step, no server. Drop it on
GitHub Pages, S3, or open `index.html` directly.

## Repo layout

```
.
├── index.html                       Dashboard shell (§5.2, §5.3, §5.4)
├── README.md                        This file (also rendered inside the dashboard)
├── BC Network 2026 v8.xlsx          Source workbook (79 wells, RMS flags, metadata)
├── js/
│   ├── wells-data.js                const WELLS — 79 wells joined to DWR site_code
│   ├── polygons-data.js             const RMS_POLYGONS — 28 Thiessen polygons (lat,lng rings)
│   ├── measurements-data.js         const MEASUREMENTS, MEASUREMENTS_META — periodic GWL
│   ├── basin-boundary.js            const VINA_BOUNDARY — B118 5-021.57 GeoJSON
│   └── main.js                      UI logic (Leaflet, Plotly, layer toggles, picker)
├── data/                            Intermediate JSON for the JS bundles
│   ├── wells_resolved.json          Excel rows joined to DWR Stations
│   ├── thresholds_2022.json         MT/MO/IM-2027 carried over from the 2022 GSP
│   └── vina_2027_thiessen.geojson   Polygons as proper GeoJSON
├── raw/                             Cached raw downloads
│   ├── stations.csv                 DWR CKAN periodic GWL Stations resource
│   ├── vina_subbasin.geojson        DWR B118 (5-021.57) boundary
│   ├── b118_vina_esri.json          Source Esri JSON before reshaping to GeoJSON
│   └── cosmo_wells.js               2022 dashboard wells-data.js (for threshold carryover)
└── scripts/                         Build scripts (run in order)
    ├── resolve_sites.py
    ├── build_polygons.py            <-- Thiessen polygon construction (documented below)
    ├── build_wells_js.py
    └── fetch_dwr_measurements.py
```

## How the 28 Thiessen polygons are built

A Thiessen polygon (aka Voronoi cell) for a point is the locus of points in
space that are closer to that point than to any other point in the seed set.
Used in groundwater monitoring to define the area each RMS well is
**presumed** to represent.

`scripts/build_polygons.py` is the canonical builder. It runs in five steps:

### 1. Pick the seeds

Read `BC Network 2026 v8.xlsx`. Keep every row where column **E (`2027 GWL
RMS?`) = "Yes"**. That yields exactly **28 wells**:

| Mgmt Area | Count | Wells |
|-----------|-------|-------|
| 01-Vina-North | 13 | 22N01W05M001M, 23N01E07H001M, 23N01E29P002M, 23N01E33A001M, 23N01W03H004M, 23N01W09E001M, 23N01W10M001M, 23N01W14R002M, 23N01W27L001M, 23N01W28M004M, 23N01W31M004M, 23N01W36P001M, 23N02W25C001M |
| 02-Vina-Chico |  2 | 22N01E09B001M, 22N01E20K001M |
| 03-Vina-South | 13 | 20N01E02H003M, 20N02E08H003M, 20N02E09G001M, 20N02E24C001M, 20N03E33L001M, 21N01E10B003M, 21N01E13L004M, 21N01E25K001M, 21N01E27D001M, 21N02E18C003M, 21N02E26E006M, 21N02E32E001M, 21N03E32B001M |

Coordinates come from columns **L (latitude)** and **M (longitude)** of the
workbook. The script asserts `len(seeds) == 28` and aborts otherwise — so if
the workbook changes RMS flags, you get a hard failure instead of silent
drift.

### 2. Get the clip boundary

The Vina Subbasin polygon (`Basin_Subbasin_Number = '5-021.57'`) is pulled
from the DWR ArcGIS REST service:

```
https://gis.water.ca.gov/arcgis/rest/services/Geoscientific/i08_B118_CA_GroundwaterBasins/MapServer/0/query?
  where=Basin_Subbasin_Number='5-021.57'
  &outFields=*
  &returnGeometry=true
  &outSR=4326
  &f=json
```

We pull as Esri JSON (the `f=geojson` form intermittently throws on this
endpoint), then convert to GeoJSON locally using Shapely. The result lives at
`raw/vina_subbasin.geojson` — a single Polygon with a 1,729-vertex outer
ring, area ≈ 0.079 sq° (~184,000 acres).

### 3. Project to an equal-area metric CRS

Voronoi tessellation only behaves sensibly in a Euclidean metric. Lat/lon
degrees aren't Euclidean — a degree of longitude at 39.7° N is about 23 %
shorter than a degree of latitude. So before computing the diagram we
project both the seeds and the basin boundary from **WGS-84 (EPSG:4326)**
into **NAD-83 California Albers Equal Area (EPSG:3310)** using `pyproj`.

EPSG:3310 is the standard DWR / Bulletin 118 working CRS, so polygon areas
in the dashboard (e.g. "11,638 ac") match what you'd compute against the
official DWR layers.

### 4. Compute & clip the Voronoi diagram

`scipy.spatial.Voronoi` over the 28 projected seed points. Two technical
notes:

* **Bounded cells.** SciPy returns unbounded regions for sites on the convex
  hull of the seed set (they emit "open rays"). The script adds **four
  anchor points** ~10 bounding-box-widths outside the basin so that every
  one of the 28 real cells is finite and well-formed; the anchors are
  discarded after the diagram is built.
* **Clipping.** Each finite cell is intersected with the Albers-projected
  Vina Subbasin polygon using `shapely.Polygon.intersection`. This trims the
  cells to the basin footprint — so polygon edges along the basin perimeter
  are taken from the official B118 line, not from the (much sloppier) outer
  Voronoi edges.

The script asserts no cell is empty after clipping (which would indicate a
seed well sitting outside the basin polygon) and no region is open after
the anchor-padding (which would indicate the anchor box is too small).

### 5. Project back & export

Cells are projected back to EPSG:4326 and written out two ways:

| File | Use |
|------|-----|
| `data/vina_2027_thiessen.geojson` | Real GeoJSON `FeatureCollection`, includes mgmt area, area-in-acres, seed lat/lon. Drop into QGIS or ArcGIS to inspect. |
| `js/polygons-data.js` | `const RMS_POLYGONS = [...]` with rings in `[lat, lng]` order to match Leaflet's `L.polygon` API. |

Each polygon carries the SWN of its seed RMS well as `zone_label`, so the
dashboard can index hydrographs and the scatter plot off the polygon click
without a separate lookup table.

### Sanity check

The 28 clipped cells total **~184,400 acres**, which matches the published
Vina Subbasin area of ~184,000 acres (DWR B118 2016). The discrepancy is
under 0.3 % and is attributable to the conversion from sq-deg → sq-meters →
acres.

| polygon | mgmt area | acres |
|---------|-----------|-------|
| 22N01W05M001M | 01-Vina-North |  7,047 |
| 23N01E07H001M | 01-Vina-North |  7,823 |
| 23N01E33A001M | 01-Vina-North | 11,053 |
| 23N01W36P001M | 01-Vina-North |  7,089 |
| 23N02W25C001M | 01-Vina-North |  4,902 |
| 23N01E29P002M | 01-Vina-North |  3,968 |
| 23N01W03H004M | 01-Vina-North |  1,997 |
| 23N01W09E001M | 01-Vina-North |  5,285 |
| 23N01W10M001M | 01-Vina-North |  2,110 |
| 23N01W14R002M | 01-Vina-North |  3,865 |
| 23N01W27L001M | 01-Vina-North |  3,166 |
| 23N01W28M004M | 01-Vina-North |  3,227 |
| 23N01W31M004M | 01-Vina-North |  1,575 |
| 22N01E20K001M | 02-Vina-Chico | 11,638 |
| 22N01E09B001M | 02-Vina-Chico | 11,159 |
| 20N02E24C001M | 03-Vina-South |  7,863 |
| 21N02E18C003M | 03-Vina-South | 17,184 |
| 20N01E02H003M | 03-Vina-South |  4,899 |
| 20N02E08H003M | 03-Vina-South |  3,458 |
| 20N02E09G001M | 03-Vina-South |  4,209 |
| 20N03E33L001M | 03-Vina-South |  5,182 |
| 21N01E10B003M | 03-Vina-South | 10,124 |
| 21N01E13L004M | 03-Vina-South |  2,713 |
| 21N01E25K001M | 03-Vina-South |  2,748 |
| 21N01E27D001M | 03-Vina-South | 10,931 |
| 21N02E26E006M | 03-Vina-South | 11,791 |
| 21N02E32E001M | 03-Vina-South |  3,692 |
| 21N03E32B001M | 03-Vina-South | 14,223 |

### What this version does *not* do

The 2022 reference dashboard had two special-cases worth flagging in case
they come back into scope:

1. **Chico dissolve.** The 2022 build merged three Chico cells into one
   polygon to match a GSP figure. The 2027 build does **not** — each of the
   28 RMS wells gets its own Voronoi cell, including the two Chico wells.
2. **Named-polygon overrides.** The 2022 build had hard-coded "this RMS
   well belongs to that polygon" overrides for geographic edge cases (e.g.
   `23N01E33A001M` straddling Vina-North vs. Chico). The 2027 build doesn't
   need them — every Voronoi cell, by construction, contains exactly its
   own RMS well.

If a future workbook revision adds more RMS wells right next to existing
ones (so cell shapes get awkward), revisit the Chico-style dissolve.

## MT / MO / IM-2027 threshold methodology

The dashboard shows Sustainable Management Criteria (SMC) threshold lines on
every 2027 RMS well's hydrograph. Values come from one of two sources, both
expressed as **groundwater elevation in ft msl** (not depth-below-RPE):

### Source 1 — "2022 GSP" (adopted, 7 wells)

These are the **Minimum Threshold (MT)**, **Measurable Objective (MO)**, and
**Interim Milestone for 2027 (IM-2027)** values carried over **unchanged**
from the 2022 Vina GSP for the seven wells that are in both the 2022 and
2027 RMS networks. Rendered with **dashed** lines in §5.3 hydrographs and
labeled with the "GSP-adopted MT/MO" pill in the §5.3 table.

| Well | MT | MO | IM-2027 |
|---|---|---|---|
| 22N01W05M001M | 31 | 115 | 116 |
| 23N01E07H001M | 72 | 136 | 140 |
| 23N01E33A001M | 72 | 125 | 128 |
| 23N01W36P001M | 45 | 108 | 110 |
| 23N02W25C001M | 50 | 130 | 130 |
| 20N02E24C001M | 18 | 77 | 81 |
| 21N02E18C003M | 65 | 130 | 132 |

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
