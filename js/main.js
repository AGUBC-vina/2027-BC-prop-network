// Vina Subbasin 2027 RMS Network Dashboard — UI logic.
// Loads WELLS, RMS_POLYGONS_THREE_ZONE, MEASUREMENTS, VINA_BOUNDARY as
// globals. `RMS_POLYGONS` is a dashboard-local alias for the three-zone
// tessellation (three independent Voronoi diagrams, one per management
// area, with Chico dissolved into a single aggregate polygon).

(function () {
  "use strict";

  /* -------------- polygon set -------------------------------------------- */
  let RMS_POLYGONS = (typeof RMS_POLYGONS_THREE_ZONE !== "undefined")
    ? RMS_POLYGONS_THREE_ZONE
    : [];

  /* -------------- palette ------------------------------------------------ */
  const MA_COLORS = {
    "01-Vina-North": "#1f4ee0",
    "02-Vina-Chico": "#e07b1f",
    "03-Vina-South": "#2ca02c",
    "Other": "#888888",
  };
  const TRACE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#3b5fd9", "#c25a00", "#1ea54a", "#a32424", "#7a4ba1",
  ];
  // Drought context is driven by DWR's official Sacramento Valley Water Year
  // Index (js/wy-index-data.js, const WY_INDEX). "Drought" = a Dry or Critical
  // water year. Used to (a) shade those years on the §5.3 hydrograph and
  // (b) split the LML trigger-frequency readout into drought vs non-drought
  // water years. This replaced a hardcoded 3-window list (1991-93, 2012-15,
  // 2020-22) that missed 1976-77, 1987-92, and 2007-09 entirely and mislabeled
  // the early-90s and 2012-16 drought spans. See README "Drought shading".
  const DROUGHT_FILL = {
    D: "rgba(240,140,0,0.09)",   // Dry — light orange
    C: "rgba(220,70,0,0.18)",    // Critical — deeper orange
  };

  // Water year (Oct 1 - Sep 30) for an ISO date string: Oct-Dec readings
  // belong to the NEXT calendar year's water year (e.g. 2007-11-15 -> WY2008).
  function waterYearOf(isoDate) {
    const y = +isoDate.slice(0, 4), m = +isoDate.slice(5, 7);
    return y + (m >= 10 ? 1 : 0);
  }

  // True if a water year is Dry or Critical on the Sacramento Valley Index.
  // Unclassified years (the in-progress WY, or a stale/missing data file)
  // degrade to "not drought" — never a crash.
  function isDryOrCriticalWY(wy) {
    const rec = (typeof WY_INDEX !== "undefined") ? WY_INDEX[wy] : null;
    return !!rec && (rec.class === "D" || rec.class === "C");
  }

  /* -------------- strawman overlays (Vina GSA memo, 2026-06-18) ---------- */
  // RMS wells proposed for non-regulatory Local Management Levels (LMLs) in
  // GDE-sensitive areas, in two tiers:
  //   - LML_STRAWMAN_SWNS: the 5 wells designated in the original GWL
  //     Strawman memo (6/18/2026) — the shallower completions identified as
  //     representing regional shallow groundwater conditions.
  //   - LML_REV_SWNS: 9 wells added in the revised strawman (under
  //     discussion, 2026-07).
  // LML = MO minus an offset; the memo's discussion starting point is
  // 10-20 ft below MO, and the §5.3 slider explores 0-30 ft in 5-ft steps.
  // Reaching an LML would trigger investigation and adaptive management,
  // NOT an undesirable result. Nothing here is adopted.
  const LML_STRAWMAN_SWNS = [
    "23N01W09E001M",  // North — Sacramento River corridor
    "23N01W27L001M",  // North
    "23N01W36P001M",  // North
    "22N01E20K001M",  // North network (well physically in Chico mgmt area)
    "21N02E32E001M",  // South — Durham area
  ];
  const LML_REV_SWNS = [
    "23N02W25C001M",  // North
    "22N01W05M001M",  // North
    "23N01E29P002M",  // North
    "21N01E10B003M",  // South
    "21N01E27D001M",  // South
    "20N01E02H003M",  // South
    "20N02E24C001M",  // South
    "20N02E09G001M",  // South
    "20N03E33L001M",  // South
  ];
  const LML_SWNS = [...LML_STRAWMAN_SWNS, ...LML_REV_SWNS];
  // Tier label for UI text: "strawman 6/18/2026" | "revised strawman" | null.
  function lmlTierLabel(swn) {
    if (LML_STRAWMAN_SWNS.includes(swn)) return "strawman 6/18/2026";
    if (LML_REV_SWNS.includes(swn)) return "revised strawman";
    return null;
  }
  const LML_COLOR = "#00838f";   // dark cyan — LML line + polygon highlight
  // Current LML slider offset (ft below MO). Default 15 = midpoint of the
  // memo's suggested 10-20 ft starting range.
  let lmlOffsetFt = 15;

  /* -------------- ESA GDE scenario overlay (§5.2) ----------------------- */
  // ESA GDE Technical Study (March 2026): 1,228 mapped NCCAG polygon
  // centroids, each flagged "likely GDE" (1) or not under SIX hydrologic
  // scenarios. The count of "likely" centroids per scenario reproduces ESA
  // TM Table 3 exactly (464/100/64/38/21/17) — so toggling the scenario
  // dropdown shows how strongly the "likely GDE" footprint depends on the
  // scenario choice, relative to the RMS cells and proposed-LML polygons.
  // Data: js/gde-centroids-data.js -> const GDE_CENTROIDS.
  const GDE_SCENARIOS = [
    { key: "spring_p90",  field: "roots_p90_spring",  n: 1, label: "Spring 90th percentile", count: 464 },
    { key: "spring_2015", field: "roots_2015_spring", n: 2, label: "Spring 2015 (critically dry)", count: 100 },
    { key: "spring_2021", field: "roots_2021_spring", n: 3, label: "Spring 2021 (lowest year)", count: 64 },
    { key: "fall_p90",    field: "roots_p90_fall",    n: 4, label: "Fall 90th percentile", count: 38 },
    { key: "fall_2015",   field: "roots_2015_fall",   n: 5, label: "Fall 2015 (critically dry)", count: 21 },
    { key: "fall_2021",   field: "roots_2021_fall",   n: 6, label: "Fall 2021 (lowest year)", count: 17 },
  ];
  const GDE_LIKELY_COLOR = "#1f8f4e";
  const GDE_OTHER_COLOR  = "#b9b9b9";
  let gdeScenarioKey = "spring_p90";
  let gdeLayer = null;
  let gdeLegend = null;

  function gdeScenario() {
    return GDE_SCENARIOS.find((s) => s.key === gdeScenarioKey) || GDE_SCENARIOS[0];
  }

  // Canvas-rendered (perf: 1,228 points, same pattern as the domestic
  // overlay), non-interactive. Not-likely centroids draw faint underneath;
  // this-scenario "likely" centroids draw green on top.
  function buildGdeLayer() {
    const sc = gdeScenario();
    const canvas = L.canvas({ padding: 0.5, pane: "gdePane" });
    const layer = L.layerGroup();
    const src = (typeof GDE_CENTROIDS !== "undefined") ? GDE_CENTROIDS : [];
    const likely = [], other = [];
    src.forEach((c) => {
      if (c.lat == null || c.lon == null) return;
      (c[sc.field] === 1 ? likely : other).push(c);
    });
    other.forEach((c) => layer.addLayer(L.circleMarker([c.lat, c.lon], {
      radius: 2, fillColor: GDE_OTHER_COLOR, fillOpacity: 0.35,
      weight: 0, opacity: 0, renderer: canvas, interactive: false, pane: "gdePane",
    })));
    likely.forEach((c) => layer.addLayer(L.circleMarker([c.lat, c.lon], {
      radius: 4, fillColor: GDE_LIKELY_COLOR, fillOpacity: 0.85,
      color: "#0c5c2e", weight: 0.5, opacity: 0.9, renderer: canvas,
      interactive: false, pane: "gdePane",
    })));
    return layer;
  }

  function refreshGdeLayer() {
    if (!map) return;
    const on = !!($("#tog-gde") && $("#tog-gde").checked);
    if (gdeLayer) { map.removeLayer(gdeLayer); gdeLayer = null; }
    if (on) { gdeLayer = buildGdeLayer(); gdeLayer.addTo(map); }
    updateGdeLegend(on);
  }

  function updateGdeLegend(on) {
    if (!gdeLegend) return;
    const div = gdeLegend.getContainer();
    if (!div) return;
    if (!on) { div.style.display = "none"; return; }
    div.style.display = "block";
    const sc = gdeScenario();
    const total = (typeof GDE_CENTROIDS !== "undefined") ? GDE_CENTROIDS.length : 0;
    div.innerHTML =
      `<div style="font-weight:600;margin-bottom:2px;">ESA likely GDEs — Scenario ${sc.n} of 6</div>` +
      `<div style="font-size:11px;color:#555;margin-bottom:6px;">${sc.label}</div>` +
      `<div><span style="display:inline-block;width:11px;height:11px;border-radius:50%;background:${GDE_LIKELY_COLOR};margin-right:6px;vertical-align:middle;"></span><b>${sc.count}</b> likely GDE areas</div>` +
      `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${GDE_OTHER_COLOR};margin-right:8px;vertical-align:middle;"></span>${(total - sc.count).toLocaleString()} mapped, not likely</div>` +
      `<div style="font-size:10.5px;color:#888;margin-top:6px;">of ${total.toLocaleString()} ESA-mapped areas. Count reproduces ESA TM Table 3.</div>`;
  }

  /* -------------- helpers ------------------------------------------------ */
  const $ = (sel) => document.querySelector(sel);
  function fmt(v, d = 2) {
    if (v === null || v === undefined || v === "" || Number.isNaN(v)) return "—";
    if (typeof v === "number") return v.toFixed(d);
    return String(v);
  }
  function fmtDate(s) { return s || "—"; }

  // Build a Leaflet polygon from rings [[lat,lng], ...]
  function polyFromRings(rings, style) { return L.polygon(rings, style); }

  // Point-in-polygon: which polygon does a (lat,lng) fall into?
  function pointInRings(latlng, rings) {
    // Leaflet polygons accept rings in any winding; use a simple PIP on outer ring.
    const [lat, lng] = latlng;
    const ring = rings[0];
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [yi, xi] = ring[i], [yj, xj] = ring[j];
      const intersect = (yi > lat) !== (yj > lat)
        && lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi;
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function pointInPolygon(latlng, poly) {
    // Multi-ring support: outer + holes (we don't have holes, but keep correct)
    if (!pointInRings(latlng, poly.rings)) return false;
    // Subtract holes (rings beyond the first if they're contained)
    for (let i = 1; i < poly.rings.length; i++) {
      if (pointInRings(latlng, [poly.rings[i]])) return false;
    }
    return true;
  }

  function wellsInsidePolygon(poly) {
    return WELLS.filter((w) => {
      if (w.latitude == null || w.longitude == null) return false;
      return pointInPolygon([w.latitude, w.longitude], poly);
    });
  }

  // Resolve "the wells this polygon represents" depending on whether it's a
  // Voronoi cell (per-well) or an aggregate polygon (e.g. dissolved Chico
  // mgmt area in the 2026-05-19 network revision, which is associated with
  // 10 specific well completions across two nested sites instead of one
  // geographic seed).
  function polygonWells(poly) {
    if (poly.is_aggregate && Array.isArray(poly.rms_well_swns)) {
      return poly.rms_well_swns
        .map((swn) => WELLS.find((w) => w.swn === swn))
        .filter(Boolean);
    }
    const inside = wellsInsidePolygon(poly);
    if (poly.rms_well_swn && !inside.find((w) => w.swn === poly.rms_well_swn)) {
      const seed = WELLS.find((w) => w.swn === poly.rms_well_swn);
      if (seed) inside.unshift(seed);
    }
    return inside;
  }

  // Pearson correlation coefficient
  function pearson(xs, ys) {
    const n = xs.length;
    if (n < 2) return null;
    const mx = xs.reduce((a, b) => a + b, 0) / n;
    const my = ys.reduce((a, b) => a + b, 0) / n;
    let num = 0, dx2 = 0, dy2 = 0;
    for (let i = 0; i < n; i++) {
      const dx = xs[i] - mx, dy = ys[i] - my;
      num += dx * dy;
      dx2 += dx * dx;
      dy2 += dy * dy;
    }
    const denom = Math.sqrt(dx2 * dy2);
    if (denom === 0) return null;
    return num / denom;
  }

  /* -------------- KPI row ----------------------------------------------- */
  function renderKPIs() {
    const n = WELLS.length;
    // Count every is_2027_gwl_rms well individually, including the 4
    // Chico RMS wells (CWSCH01b/02/03/07) that share one map pin for
    // privacy display purposes — they're genuinely distinct RMS wells
    // (different MO/IM, different completion depths, each with its own
    // threshold lines), not duplicates, so the KPI shouldn't collapse
    // them. RMS-well count and polygon count are intentionally allowed
    // to differ — Chico is 1 polygon with 4 RMS wells.
    const n2027Rms = WELLS.filter((w) => w.is_2027_gwl_rms).length;
    $("#kpi-wells").textContent = n;
    $("#kpi-rms-2027").textContent = n2027Rms;
    $("#kpi-poly").textContent = RMS_POLYGONS.length;

    // Data freshness from MEASUREMENTS metadata if available
    const meta = (typeof MEASUREMENTS_META !== "undefined") ? MEASUREMENTS_META : null;
    if (meta && meta.fetched_at) {
      $("#data-freshness").textContent = `DWR refresh: ${meta.fetched_at.slice(0, 10)} · ${meta.n_records.toLocaleString()} records across ${meta.n_wells} wells`;
    }
  }

  /* -------------- nested-well grouping (by lat/lon) --------------------- */
  // siteGroups: "lat|lng" -> [well, ...]  ;  wellSiteKey: wellName -> "lat|lng"
  const siteGroups = {};
  const wellSiteKey = {};
  WELLS.forEach((w) => {
    if (w.latitude == null || w.longitude == null) return;
    const k = `${(+w.latitude).toFixed(5)}|${(+w.longitude).toFixed(5)}`;
    (siteGroups[k] = siteGroups[k] || []).push(w);
    wellSiteKey[w.swn] = k;
  });
  function nestedCount(w) {
    const k = wellSiteKey[w.swn];
    return (siteGroups[k] || []).length;
  }

  /* -------------- measurement helpers ----------------------------------- */
  function getMeas(w) {
    if (!w.site_code) return [];
    return MEASUREMENTS[w.site_code] || [];
  }
  function isContinuous(w) {
    return (w.monitor_freq || "").toLowerCase().includes("hour")
      || (w.monitor_freq || "").toLowerCase().includes("daily")
      || (w.monitor_freq || "").toLowerCase().includes("continuous");
  }
  function measurementSummary(records) {
    const good = records.filter((r) => r.qa && r.qa.toLowerCase().includes("good") && r.gwe !== null);
    const questionable = records.filter((r) => r.qa && r.qa.toLowerCase().includes("question"));
    const missing = records.filter((r) => r.qa && r.qa.toLowerCase().includes("missing"));
    const lastGood = good.length ? good[good.length - 1] : null;
    return {
      total: records.length,
      good: good.length,
      questionable: questionable.length,
      missing: missing.length,
      firstYear: good.length ? good[0].d.slice(0, 4) : null,
      lastYear: good.length ? good[good.length - 1].d.slice(0, 4) : null,
      lastGoodDate: lastGood ? lastGood.d : null,
      lastGoodGwe: lastGood ? lastGood.gwe : null,
    };
  }
  function currentWSE(w) {
    // Latest QA-Good GWE (popup helper) — same convention as every graph
    // and statistic on the page. Falls back to the latest reading of any
    // grade (labeled with its QA grade) only if a well has no Good record.
    // Returns both the groundwater elevation (msl) and depth-to-groundwater
    // (below GSE) when available. Falls back to computing dtw from gwe + gse
    // for the few records where only gwe is present.
    const ms = getMeas(w);
    const gse = w.gse != null ? +w.gse : null;
    const pick = (requireGood) => {
      for (let i = ms.length - 1; i >= 0; i--) {
        const m = ms[i];
        if (m.gwe == null) continue;
        if (requireGood && !(m.qa && m.qa.toLowerCase().includes("good"))) continue;
        let dtw = m.dtw;
        if (dtw == null && gse != null) dtw = gse - m.gwe;
        return { gwe: m.gwe, dtw, date: m.d, qa: m.qa };
      }
      return null;
    };
    return pick(true) || pick(false);
  }

  /* -------------- 5.2 Leaflet map --------------------------------------- */
  let map, polygonLayer, basinLayer, rms2027Layer, suppLayer, domesticLayer;
  let lmlLayer, labelsLayer;

  /* -------------- MT sensitivity (domestic wells) ---------------------- */
  // Slider value (0–30 ft, the amount by which MT is hypothetically raised
  // for sensitivity analysis). Updated by the §5.3 slider; drives the
  // sensitivity widget, the hydrograph's "raised MT" line, and the RMS
  // well popup's adjusted dry count.
  let mtRaiseFt = 0;
  // When true, apply the cosmo "one-sided" elevation correction to dry
  // counts: effective_MT for a domestic well = MT + max(0, well_gse - rms_gse).
  let elevCorrectionOn = false;

  // Threshold-raise columns shown in the sensitivity table.
  const SENS_RAISES = [0, 5, 10, 15, 20, 25, 30];

  // Active domestic wells: those flagged include=1 in the cosmo bundle and
  // with a valid lat/lon, well_bottom_amsl. Cached once at startup.
  let DOMESTIC_ACTIVE = [];
  // Per-polygon dictionary: zone_label -> array of active domestic wells
  // that fall inside that polygon. Cached once at startup.
  let DOMESTIC_BY_POLYGON = {};

  // Build the active-domestic-wells caches. Called once after data load.
  function buildDomesticCaches() {
    if (typeof DOMESTIC_WELLS === "undefined") return;
    DOMESTIC_ACTIVE = DOMESTIC_WELLS.filter((w) =>
      w.include === 1 && w.lat != null && w.lon != null && w.well_bottom_amsl != null
    );
    DOMESTIC_BY_POLYGON = {};
    DOMESTIC_ACTIVE.forEach((w) => {
      const key = w.our_polygon;
      if (!key) return;
      (DOMESTIC_BY_POLYGON[key] = DOMESTIC_BY_POLYGON[key] || []).push(w);
    });
  }

  // Count dry domestic wells in `wells` (a list of domestic-well records)
  // at the given polygon MT raised by `raise_ft`. If `elev_correct` is true,
  // each well's effective MT is raised further by max(0, well_gse - rms_gse).
  // Returns { dry, total }.
  function countDryDomestic(wells, mt_ft, rms_gse, raise_ft, elev_correct) {
    if (mt_ft == null) return { dry: 0, total: 0 };
    let dry = 0;
    const baseMT = mt_ft + raise_ft;
    for (const w of wells) {
      const gseDelta = (elev_correct && rms_gse != null && w.local_gse != null)
        ? Math.max(0, w.local_gse - rms_gse) : 0;
      const effectiveMT = baseMT + gseDelta;
      if (w.well_bottom_amsl > effectiveMT) dry++;
    }
    return { dry, total: wells.length };
  }

  // Basin-wide dry counts at the given raise. Uses each well's HOME polygon's
  // MT. For elev-correction, uses each polygon's seed RMS well's GSE.
  function basinDryCount(raise_ft, elev_correct) {
    let dry = 0, total = 0;
    if (typeof RMS_POLYGONS === "undefined") return { dry, total };
    RMS_POLYGONS.forEach((poly) => {
      const pgnWells = DOMESTIC_BY_POLYGON[poly.zone_label] || [];
      if (pgnWells.length === 0) return;
      const mt_ft = polygonMT(poly);
      const rms_gse = polygonRmsGSE(poly);
      const c = countDryDomestic(pgnWells, mt_ft, rms_gse, raise_ft, elev_correct);
      dry += c.dry;
      total += c.total;
    });
    return { dry, total };
  }

  // For aggregate polygons (Chico, which can carry multiple RMS wells),
  // use the first-listed RMS primary's MT as the polygon's representative
  // value. For per-well polygons, use the seed RMS well's MT. Chico's
  // current RMS wells all share MT=85, so the "which primary" choice is
  // not consequential today, but would matter if a future Chico RMS well
  // had a different MT.
  function polygonMT(poly) {
    const primarySwn = poly.is_aggregate
      ? (poly.rms_primary_swns || [])[0]
      : poly.rms_well_swn;
    if (!primarySwn) return null;
    const w = WELLS.find((x) => x.swn === primarySwn);
    return w ? w.mt_ft : null;
  }

  // Reference GSE for the one-sided elevation correction. For Chico
  // (multiple RMS primaries with materially different GSE — e.g.
  // CWSCH01b=200ft vs CWSCH07=266ft), this uses the first-listed
  // primary's GSE, same simplification as polygonMT() above.
  function polygonRmsGSE(poly) {
    const primarySwn = poly.is_aggregate
      ? (poly.rms_primary_swns || [])[0]
      : poly.rms_well_swn;
    if (!primarySwn) return null;
    const w = WELLS.find((x) => x.swn === primarySwn);
    return w ? (w.gse != null ? +w.gse : null) : null;
  }
  let basemapLayer = null;
  let polygonRefs = {};   // zone_label -> { leafletPoly, dataPoly }
  let selectedPoly = null;
  let shadingOn = true;
  // Wells whose manual QA-Good record has a multi-year lapse covered by a
  // county continuous recorder — bridged in the hydrograph by a flagged
  // "recorder-derived" monthly static-level proxy (see renderHydrograph).
  const RECORDER_DERIVED_SWNS = ["22N01W05M001M"];

  const BASEMAPS = {
    "carto": {
      url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      options: {
        maxZoom: 19, subdomains: "abcd",
        attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a> &copy; OSM',
      },
    },
    "osm": {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      options: { maxZoom: 19, attribution: "© OpenStreetMap" },
    },
    "esri-sat": {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      options: { maxZoom: 19, attribution: "Tiles © Esri" },
    },
    "esri-topo": {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
      options: { maxZoom: 19, attribution: "Tiles © Esri" },
    },
    // USGS National Map topo: authoritative NHD blue-line streams + named
    // creeks/rivers (Sacramento R., Big Chico / Butte / Mud Creek, etc.).
    // Best basemap for locating hydrography relative to the RMS network / GDEs.
    "usgs-topo": {
      url: "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
      options: { maxZoom: 16, attribution: "Tiles © USGS The National Map" },
    },
  };

  function setBasemap(key) {
    if (!map) return;
    if (basemapLayer) map.removeLayer(basemapLayer);
    const b = BASEMAPS[key] || BASEMAPS.carto;
    basemapLayer = L.tileLayer(b.url, b.options).addTo(map);
    basemapLayer.bringToBack();
  }

  // Look up "is this well's location inside the Chico mgmt area polygon"
  // from the three-zone polygons data (every N-cell polygon carries this
  // flag, derived during the build at scripts/build_polygons_three_zone.py).
  function isWellPhysicallyInChico(swn) {
    if (typeof RMS_POLYGONS_THREE_ZONE === "undefined") return false;
    const p = RMS_POLYGONS_THREE_ZONE.find((x) => x.rms_well_swn === swn);
    return !!(p && p.well_in_chico_mgmt_area);
  }

  function buildWellPopup(w) {
    const lat = w.latitude, lng = w.longitude;
    const wse = currentWSE(w);
    let wseLine;
    if (wse) {
      const dateSuffix = `<span style="color:#888;">(${wse.date}${wse.qa ? `, ${wse.qa}` : ""})</span>`;
      const dtwTxt = wse.dtw != null
        ? `${wse.dtw.toFixed(2)} ft below GSE ${dateSuffix}`
        : `<span style="color:#888;">—</span>`;
      wseLine =
        `<div><b>Current WSE:</b> ${wse.gwe.toFixed(2)} ft msl ${dateSuffix}</div>` +
        `<div><b>Depth to GW:</b> ${dtwTxt}</div>`;
    } else {
      wseLine = `<div><b>Current WSE / DTW:</b> <span style="color:#888;">no DWR record</span></div>`;
    }
    // Record span — first→last "Good" year, plus the count of good records
    const stats = measurementSummary(getMeas(w));
    const recordLine = stats.firstYear
      ? `<div><b>Record:</b> ${stats.firstYear}–${stats.lastYear} <span style="color:#888;">(${stats.good.toLocaleString()} good)</span></div>`
      : `<div><b>Record:</b> <span style="color:#888;">no DWR record</span></div>`;
    const nC = nestedCount(w);
    const nestedLine = nC > 1
      ? `<div><b>Nested completions:</b> <span style="color:#c2410c;font-weight:600;">×${nC}</span> wells share this location</div>`
      : "";
    const bcReason = (w.butte_co_reasoning || "").trim();
    const bcLine = bcReason
      ? `<div style="margin-top:6px; padding-top:6px; border-top:1px solid #eee;"><b>Butte County reasoning:</b><br>${bcReason}</div>`
      : "";
    // For the 3 N RMS wells whose physical location is inside the Chico
    // mgmt area (22N01E09B001M, 22N01E20K001M, 23N01E33A001M), surface
    // that fact so reviewers understand why the well marker sits inside
    // the Chico polygon while the well's Thiessen cell is drawn in N.
    const chicoNote = (w.is_2027_gwl_rms && isWellPhysicallyInChico(w.swn))
      ? `<div style="margin-top:4px;color:#c25a00;font-size:11.5px;"><b>Note:</b> physical location inside the Chico mgmt area; RMS for the North network. The Thiessen cell sits north of this well (Chico territory is clipped away).</div>`
      : "";
    // For 21N02E26E006M (and any future wells using the same convention)
    // the MT/MO/IM are inherited from a nested sibling that was 2022 RMS.
    const inheritNote = w.carryover_from
      ? `<div style="margin-top:4px;color:#c25a00;font-size:11.5px;"><b>Note:</b> MT/MO/IM inherited from <code>${w.carryover_from}</code>, the 2022 GSP RMS at this same lat/lng (different completion depth).</div>`
      : "";
    // Proposed-LML note for the 14 LML-designated wells (tier-labeled:
    // original strawman 5 vs revised-strawman 9). The value
    // follows the §5.3 slider offset — popup content is a function, so it
    // recomputes on every open.
    const lmlNote = (w.is_2027_gwl_rms && LML_SWNS.includes(w.swn) && w.mo_ft != null)
      ? `<div style="margin-top:4px;color:${LML_COLOR};font-size:11.5px;"><b>Proposed LML polygon (${lmlTierLabel(w.swn)}):</b> LML at MO &minus; ${lmlOffsetFt} ft = ${(w.mo_ft - lmlOffsetFt).toFixed(0)} ft msl. Non-regulatory trigger for GDE-sensitive areas — explore the offset with the §5.3 slider.</div>`
      : "";
    // Per-well AGWL derivation for the 17 Strawman Table 3 wells: the
    // well's own Feb-April average GWL (the Mirror methodology's input)
    // and the zone-offset subtraction, so the popup explains where the
    // dotted threshold lines come from. Carryovers skip this — their
    // MT/MO/IM are adopted 2022 GSP values, not AGWL-derived.
    const agwlNote = (w.threshold_source === "Strawman Table 3" && w.agwl_ft != null)
      ? `<div style="margin-top:4px;color:#555;font-size:11.5px;">` +
        `<b>Feb&ndash;Apr AGWL:</b> ${w.agwl_ft.toFixed(1)} ft msl ` +
        `<span style="color:#888;">(${(w.n_spring_obs || 0).toLocaleString()} spring obs)</span>` +
        ` &minus; ${w.rms_mgmt_area_short} offsets ` +
        `${w.zone_offset_mt.toFixed(1)} / ${w.zone_offset_mo.toFixed(1)} / ${w.zone_offset_im.toFixed(1)} ft ` +
        `&rarr; <b>Mirror MT/MO/IM ${w.mirror_mt_ft} / ${w.mirror_mo_ft} / ${w.mirror_im_2027_ft}</b>` +
        (w.table3_divergence
          ? ""
          : ` <span style="color:#1b5e20;">= county Table 3</span>`) +
        `</div>`
      : "";
    // County-Table-3 vs dashboard-Mirror cross-check flag (2 wells).
    const divergenceNote = w.table3_divergence
      ? `<div style="margin-top:6px;padding:5px 8px;background:#fff8e1;border-left:3px solid #f59e0b;font-size:11px;color:#7a5c00;line-height:1.4;"><b>&#9888; Threshold cross-check:</b> ${w.table3_divergence}</div>`
      : "";
    // Domestic-well dry counts at this RMS well's polygon. Two lines,
    // both INDEPENDENT of the sensitivity slider (the slider drives the
    // hydrograph + sensitivity table, not the popup):
    //   1. Dry domestic wells at MT — count at the polygon's original MT
    //      with no elevation adjustment. Always shown.
    //   2. Dry at adjusted MT, based on well elevation — count when each
    //      well's effective MT is shifted upward by max(0, well_gse - rms_gse)
    //      ONLY when the "Adjust threshold for each well's elevation"
    //      toggle is on. When the toggle is off, line 2 equals line 1
    //      (no per-well adjustment applied) — same number, kept visible so
    //      the toggle's effect is obvious when it's flipped.
    let domLine = "";
    if (w.is_2027_gwl_rms && typeof DOMESTIC_BY_POLYGON !== "undefined") {
      // Find the polygon for which this well is the (or a) RMS seed.
      const poly = (typeof RMS_POLYGONS !== "undefined" ? RMS_POLYGONS : []).find(
        (p) => p.rms_well_swn === w.swn
          || (p.is_aggregate && (p.rms_primary_swns || []).includes(w.swn))
      );
      if (poly) {
        const polyWells = DOMESTIC_BY_POLYGON[poly.zone_label] || [];
        if (polyWells.length > 0) {
          const rmsGse = w.gse != null ? +w.gse : null;
          // Line 1: original MT, no elevation correction, no slider raise.
          const cAt = countDryDomestic(polyWells, w.mt_ft, rmsGse, 0, false);
          // Line 2: elevation correction only when toggle is on; still no slider raise.
          const cAdj = countDryDomestic(polyWells, w.mt_ft, rmsGse, 0, elevCorrectionOn);
          const pct = (c) => c.total > 0 ? (100 * c.dry / c.total).toFixed(0) : "0";
          domLine =
            `<div style="margin-top:6px;padding-top:6px;border-top:1px solid #eee;">` +
            `<div><b>Dry domestic wells at MT (${w.mt_ft} ft):</b> ${cAt.dry} of ${cAt.total} (${pct(cAt)}%)</div>` +
            `<div><b>Dry at adjusted MT, based on well elevation:</b> ${cAdj.dry} of ${cAdj.total} (${pct(cAdj)}%)</div>` +
            (elevCorrectionOn
              ? `<div style="color:#888;font-size:11px;">(elevation correction <b>on</b>)</div>`
              : `<div style="color:#888;font-size:11px;">(elevation correction off — toggle on in §5.3 to apply)</div>`) +
            `</div>`;
        }
      }
    }
    return `
      <div style="font-size:12.5px;line-height:1.45;max-width:300px;">
        <div style="font-weight:600;font-size:13px;margin-bottom:4px;">${w.well_name}</div>
        <div><b>Mgmt area:</b> ${w.mgmt_area_full || "—"}</div>
        <div><b>Role:</b> ${w.is_2027_gwl_rms ? "2027 Proposed RMS" : "Supplemental"}${w.is_2022_gwl_rms ? " · was 2022 RMS" : ""}</div>
        ${chicoNote}
        ${inheritNote}
        ${lmlNote}
        ${agwlNote}
        ${divergenceNote}
        ${wseLine}
        ${recordLine}
        ${nestedLine}
        ${domLine}
        <div><b>Well use:</b> ${w.well_use || "—"}</div>
        <div><b>Depth:</b> ${fmt(w.well_depth, 0)} ft</div>
        <div><b>Screen:</b> ${w.screen_intervals || "—"}</div>
        <div><b>Monitor freq:</b> ${w.monitor_freq || "—"}</div>
        <div><b>GSE / RPE:</b> ${fmt(w.gse)} / ${fmt(w.rpe)} ft</div>
        <div><b>Site code:</b> <code>${w.site_code || "—"}</code></div>
        <div><b>Lat / Lon:</b> ${fmt(lat, 5)}, ${fmt(lng, 5)}</div>
        ${bcLine}
      </div>`;
  }

  // Invisible halo radius added around each visible marker, so near-miss
  // clicks still open the popup instead of falling through to the polygon
  // underneath. ~10px gives a comfortable target without overlapping
  // neighboring wells in the basin.
  const HIT_PAD_PX = 10;

  function makeWellMarker(w) {
    const lat = w.latitude, lng = w.longitude;
    if (lat == null || lng == null) return null;
    const nC = nestedCount(w);
    const baseStyle = w.is_2027_gwl_rms
      ? { radius: 9, fillColor: "#1e40af", color: "#fff", weight: 2, opacity: 1, fillOpacity: 0.95 }
      : { radius: 5, fillColor: "#888", color: "#fff", weight: 1, opacity: 1, fillOpacity: 0.85 };
    // Visually mark nested sites with a slightly larger radius + orange ring
    const style = nC > 1
      ? { ...baseStyle, radius: baseStyle.radius + 1, color: "#c2410c", weight: 2 }
      : baseStyle;
    const visible = L.circleMarker([lat, lng], { ...style, pane: "wellsPane" });
    const hit = L.circleMarker([lat, lng], {
      radius: style.radius + HIT_PAD_PX,
      opacity: 0, fillOpacity: 0, weight: 0,
      interactive: true, bubblingMouseEvents: false,
      pane: "wellsPane",
    });
    // Use function content so the popup re-computes the domestic-well dry
    // counts (which depend on the slider + elev-correction toggle) every
    // time the popup is opened. Leaflet 1.x calls the function with the
    // source layer each time the popup opens.
    visible.bindPopup(() => buildWellPopup(w), { maxWidth: 340 });
    hit.on("click", () => visible.openPopup());
    // 2022 RMS wells get a small white dot in the middle so reviewers can
    // tell at a glance which wells were already in the prior network.
    const layers = [hit, visible];
    if (w.is_2022_gwl_rms) {
      const dot = L.circleMarker([lat, lng], {
        radius: Math.max(2, Math.round(style.radius * 0.35)),
        fillColor: "#ffffff", fillOpacity: 1,
        color: "#ffffff", weight: 0, opacity: 1,
        interactive: false, pane: "wellsPane",
      });
      layers.push(dot);
    }
    const group = L.featureGroup(layers);
    group.well = w;
    return group;
  }

  /* For nested sites — one marker that opens a popup listing all completions */
  function makeNestedMarker(wells) {
    if (wells.length === 1) return makeWellMarker(wells[0]);
    const lat = wells[0].latitude, lng = wells[0].longitude;
    // Mark with priority = 2027 RMS if any, else supplemental
    const hasRms = wells.some((w) => w.is_2027_gwl_rms);
    const baseStyle = hasRms
      ? { radius: 11, fillColor: "#1e40af", color: "#c2410c", weight: 2.5, opacity: 1, fillOpacity: 0.95 }
      : { radius: 7,  fillColor: "#888",    color: "#c2410c", weight: 2,   opacity: 1, fillOpacity: 0.9 };
    const visible = L.circleMarker([lat, lng], { ...baseStyle, pane: "wellsPane" });
    const hit = L.circleMarker([lat, lng], {
      radius: baseStyle.radius + HIT_PAD_PX,
      opacity: 0, fillOpacity: 0, weight: 0,
      interactive: true, bubblingMouseEvents: false,
      pane: "wellsPane",
    });
    // Tab through each completion in the popup
    const tabs = wells.map((w, i) => `<button data-tab="${i}" class="nested-tab" style="margin-right:4px;padding:2px 8px;font-size:11px;cursor:pointer;border:1px solid #c7d6f5;background:${i===0?'#1e40af':'#f0f5ff'};color:${i===0?'#fff':'#1e40af'};border-radius:3px;">${w.well_name}</button>`).join("");
    const tabsHtml = `<div style="margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #eee;"><b>Nested site (×${wells.length}):</b><br><div style="margin-top:6px;">${tabs}</div></div>`;
    const popupEl = document.createElement("div");
    popupEl.style.fontSize = "12.5px";
    popupEl.style.maxWidth = "320px";
    function renderTab(i) {
      popupEl.innerHTML = tabsHtml + buildWellPopup(wells[i]);
      popupEl.querySelectorAll(".nested-tab").forEach((btn, j) => {
        btn.style.background = j === i ? "#1e40af" : "#f0f5ff";
        btn.style.color = j === i ? "#fff" : "#1e40af";
        btn.addEventListener("click", (e) => { e.stopPropagation(); renderTab(j); });
      });
    }
    renderTab(0);
    visible.bindPopup(popupEl, { maxWidth: 340 });
    hit.on("click", () => visible.openPopup());
    // 2022 RMS marker — show the white dot if ANY well at this site was
    // 2022 RMS (e.g. nested completions in the CWSCH and 22N01E28J sites
    // where some primaries are 2022 RMS but not all completions).
    const layers = [hit, visible];
    if (wells.some((w) => w.is_2022_gwl_rms)) {
      const dot = L.circleMarker([lat, lng], {
        radius: Math.max(2, Math.round(baseStyle.radius * 0.35)),
        fillColor: "#ffffff", fillOpacity: 1,
        color: "#ffffff", weight: 0, opacity: 1,
        interactive: false, pane: "wellsPane",
      });
      layers.push(dot);
    }
    const group = L.featureGroup(layers);
    group.wells = wells;
    return group;
  }

  function styleForPolygon(poly, selected) {
    const c = MA_COLORS[poly.mgmt_area_full] || "#888";
    // Critical: ALWAYS keep fill present (even when "shading off") so the
    // polygon's interior remains clickable. Use a near-transparent fill
    // when shading is off so visually only the outline shows.
    return {
      color: c,                                      // outline color
      weight: selected ? 3 : 1.5,                    // selection thickens outline only
      fillColor: c,
      fill: true,
      fillOpacity: shadingOn ? (selected ? 0.40 : 0.18) : 0.001,
    };
  }

  // (Re)build the Leaflet polygon layer from whichever set is active.
  // Clears `polygonRefs` and `polygonLayer` first so this can be called
  // both at initial render and when the method picker flips.
  function buildPolygonLayer() {
    polygonRefs = {};
    polygonLayer.clearLayers();
    RMS_POLYGONS.forEach((poly) => {
      const lp = L.polygon(poly.rings, { ...styleForPolygon(poly, false), pane: "polygonsPane" });
      lp.on("click", (e) => {
        L.DomEvent.stopPropagation(e);
        selectPolygon(poly.zone_label);
      });
      lp.on("mouseover", () => {
        if (selectedPoly !== poly.zone_label) lp.setStyle({ fillOpacity: shadingOn ? 0.30 : 0.10 });
      });
      lp.on("mouseout", () => {
        if (selectedPoly !== poly.zone_label) lp.setStyle(styleForPolygon(poly, false));
      });
      polygonRefs[poly.zone_label] = { lp, poly };
      polygonLayer.addLayer(lp);
    });
  }

  function renderMap() {
    map = L.map("map", { preferCanvas: false, zoomControl: true }).setView([39.74, -121.86], 11);
    setBasemap("carto");

    // Dedicated panes so well markers always sit above Thiessen polygons
    // regardless of layer add/remove order or setStyle calls. Stacking is
    // pinned via CSS z-index, not SVG DOM order — this is what makes the
    // hit halos reliable when the user toggles polygon methods.
    map.createPane("polygonsPane");
    map.getPane("polygonsPane").style.zIndex = 400;
    // ESA GDE centroids sit above the polygon fills but below the well
    // markers so they never obscure an RMS/LML well. The layer is purely a
    // non-interactive visual overlay, so the pane must NOT capture pointer
    // events — otherwise its canvas (z 420) sits over the polygon SVG (z
    // 400) and swallows polygon-selection clicks (which also drive the §5.3
    // hydrograph and the LML slider).
    map.createPane("gdePane");
    map.getPane("gdePane").style.zIndex = 420;
    map.getPane("gdePane").style.pointerEvents = "none";
    map.createPane("wellsPane");
    map.getPane("wellsPane").style.zIndex = 450;

    // Vina Subbasin boundary (always shown)
    basinLayer = L.geoJSON(VINA_BOUNDARY, {
      style: { color: "#222", weight: 2.2, fill: false, dashArray: "4,4", opacity: 0.85 },
      interactive: false,
    }).addTo(map);

    // Thiessen polygons (always interactive even when shading is off so clicks still work)
    polygonLayer = L.layerGroup();
    buildPolygonLayer();
    polygonLayer.addTo(map);

    // Marker layers (2 tiers only: 2027 RMS + supplemental); nested completions
    // collapse into a single marker per lat/lon site with a tabbed popup.
    rms2027Layer = L.layerGroup();
    suppLayer = L.layerGroup();
    const seenSites = new Set();
    WELLS.forEach((w) => {
      const sk = wellSiteKey[w.swn];
      if (!sk || seenSites.has(sk)) return;
      seenSites.add(sk);
      const group = siteGroups[sk];
      const m = makeNestedMarker(group);
      if (!m) return;
      // Place in 2027 layer if any well in the group is RMS, else supplemental
      const hasRms = group.some((g) => g.is_2027_gwl_rms);
      if (hasRms) rms2027Layer.addLayer(m); else suppLayer.addLayer(m);
    });
    rms2027Layer.addTo(map);
    suppLayer.addTo(map);

    // Domestic-wells overlay (lazily built — 1,253 active markers; uses a
    // canvas renderer for perf since SVG with 1k+ markers stutters on pan).
    // Each well is a small gray dot. The marker list is bundled in
    // js/domestic-wells-data.js as DOMESTIC_WELLS (include=1 only filters
    // applied at render time). Default: hidden.
    domesticLayer = buildDomesticLayer();
    // Not added to map by default; toggled via #tog-domestic below.

    // Strawman overlay — proposed LML polygons; default hidden, toggled
    // via #tog-lml below.
    lmlLayer = buildLmlLayer();
    // Well-name labels for every pin; default hidden, toggled via #tog-labels.
    labelsLayer = buildLabelsLayer();

    // Fit to polygons
    const allBounds = L.featureGroup(Object.values(polygonRefs).map((r) => r.lp)).getBounds();
    map.fitBounds(allBounds, { padding: [20, 20] });

    // Toggles
    $("#tog-polys").addEventListener("change", (e) => {
      if (e.target.checked) polygonLayer.addTo(map); else map.removeLayer(polygonLayer);
    });
    $("#tog-shading").addEventListener("change", (e) => {
      shadingOn = e.target.checked;
      Object.entries(polygonRefs).forEach(([k, r]) => {
        r.lp.setStyle(styleForPolygon(r.poly, k === selectedPoly));
      });
    });
    $("#tog-rms-2027").addEventListener("change", (e) => {
      if (e.target.checked) rms2027Layer.addTo(map); else map.removeLayer(rms2027Layer);
    });
    $("#tog-supp").addEventListener("change", (e) => {
      if (e.target.checked) suppLayer.addTo(map); else map.removeLayer(suppLayer);
    });
    $("#tog-domestic").addEventListener("change", (e) => {
      if (e.target.checked) domesticLayer.addTo(map); else map.removeLayer(domesticLayer);
    });
    $("#tog-lml").addEventListener("change", (e) => {
      if (e.target.checked) lmlLayer.addTo(map); else map.removeLayer(lmlLayer);
    });
    $("#tog-labels").addEventListener("change", (e) => {
      if (e.target.checked) labelsLayer.addTo(map); else map.removeLayer(labelsLayer);
    });
    // ESA GDE scenario overlay: bottom-left legend control + toggle + dropdown.
    gdeLegend = L.control({ position: "bottomleft" });
    gdeLegend.onAdd = () => {
      const div = L.DomUtil.create("div", "gde-legend");
      div.style.display = "none";
      L.DomEvent.disableClickPropagation(div);
      return div;
    };
    gdeLegend.addTo(map);
    $("#tog-gde").addEventListener("change", refreshGdeLayer);
    $("#gde-scenario").addEventListener("change", (e) => {
      gdeScenarioKey = e.target.value;
      refreshGdeLayer();
    });
    $("#picker-basemap").addEventListener("change", (e) => setBasemap(e.target.value));
  }

  // Overlay outlining the 14 polygons proposed for Local Management Levels,
  // styled by tier: the original strawman 5 get the heavier long-dash
  // outline; the 9 revised-strawman additions get a lighter short-dash so
  // the two tiers stay visually distinguishable on the map (see legend).
  // Non-interactive so clicks fall through to the base polygon (selection
  // keeps working); drawn in polygonsPane, added after the base cells so it
  // renders above them.
  function buildLmlLayer() {
    const layer = L.layerGroup();
    RMS_POLYGONS.forEach((poly) => {
      if (!LML_SWNS.includes(poly.rms_well_swn)) return;
      const isOriginal = LML_STRAWMAN_SWNS.includes(poly.rms_well_swn);
      layer.addLayer(L.polygon(poly.rings, isOriginal
        ? {
            pane: "polygonsPane",
            color: LML_COLOR, weight: 3.5, dashArray: "8,5", opacity: 0.95,
            fill: true, fillColor: LML_COLOR, fillOpacity: 0.10,
            interactive: false,
          }
        : {
            pane: "polygonsPane",
            color: LML_COLOR, weight: 2, dashArray: "2,6", opacity: 0.8,
            fill: true, fillColor: LML_COLOR, fillOpacity: 0.05,
            interactive: false,
          }));
    });
    return layer;
  }

  /* -------------- well name labels (§5.2 toggle) ------------------------- */
  // Short display name for a well: SWN-style names collapse to the
  // section-tract-sequence tail ("23N01W09E001M" -> "09E001M"); other
  // names (CWSCH01b etc.) are shown as-is.
  function shortWellName(name) {
    return /^\d{2}N\d{2}[EW]/.test(name || "") ? name.slice(-7) : (name || "");
  }

  // One label per map pin. Nested pads collapse to a pad-level label:
  // the common name prefix plus a completion count ("28M ×4",
  // "CWSCH ×7") — matching how the pads are referred to in the county
  // materials. The pad marker's tabbed popup identifies the individual
  // completions.
  function siteLabelText(group) {
    if (group.length === 1) return shortWellName(group[0].well_name || group[0].swn);
    const shorts = group.map((g) => shortWellName(g.well_name || g.swn));
    let prefix = shorts[0];
    for (const s of shorts.slice(1)) {
      while (prefix && !s.startsWith(prefix)) prefix = prefix.slice(0, -1);
    }
    prefix = prefix.replace(/\d+$/, "");
    return `${prefix || shorts[0]} ×${group.length}`;
  }

  // Permanent short-name labels for 2027 RMS map pins only, toggled via
  // #tog-labels. Supplemental-only sites are intentionally NOT labeled (they
  // clutter the map and aren't the network the labels are meant to identify).
  // A nested pad that includes at least one RMS completion still gets its
  // pad-level label. Labels are anchored to invisible zero-size markers so
  // they don't affect hit-testing.
  function buildLabelsLayer() {
    const layer = L.layerGroup();
    const seen = new Set();
    WELLS.forEach((w) => {
      const sk = wellSiteKey[w.swn];
      if (!sk || seen.has(sk)) return;
      seen.add(sk);
      const group = siteGroups[sk];
      const hasRms = group.some((g) => g.is_2027_gwl_rms);
      if (!hasRms) return;   // RMS pins only — skip supplemental-only sites
      const markerR = group.length > 1 ? 11 : 9;
      const anchor = L.circleMarker([+group[0].latitude, +group[0].longitude], {
        pane: "wellsPane", radius: 0.1,
        opacity: 0, fillOpacity: 0, weight: 0,
        interactive: false,
      });
      anchor.bindTooltip(siteLabelText(group), {
        permanent: true, direction: "right", offset: [markerR + 6, 0],
        className: "well-label well-label-rms",
        opacity: 1,
      });
      layer.addLayer(anchor);
    });
    return layer;
  }

  // Build the domestic-wells overlay layer. Canvas-rendered for performance
  // (1,253 active wells). Color-coded by their assigned 2027 mgmt area so
  // they're visually grouped without needing a separate marker per area.
  function buildDomesticLayer() {
    if (typeof DOMESTIC_WELLS === "undefined") return L.layerGroup();
    const canvas = L.canvas({ padding: 0.5 });
    const fillByMA = {
      "North": "#1f4ee0",
      "Chico": "#e07b1f",
      "South": "#2ca02c",
    };
    const layer = L.layerGroup();
    DOMESTIC_WELLS.forEach((w) => {
      if (w.include !== 1) return;
      if (w.lat == null || w.lon == null) return;
      const fill = fillByMA[w.our_mgmt_area] || "#9ca3af";
      L.circleMarker([w.lat, w.lon], {
        radius: 2.5,
        fillColor: fill,
        fillOpacity: 0.55,
        color: fill,
        weight: 0,
        opacity: 0,
        renderer: canvas,
        interactive: false,  // perf: skip event wiring (no click popups)
      }).addTo(layer);
    });
    return layer;
  }

  /* -------------- 5.3 picker & hydrograph ------------------------------- */
  function populatePolygonPicker() {
    const sel = $("#picker-poly");
    sel.innerHTML = "";
    // sort by mgmt area then SWN
    const sorted = RMS_POLYGONS.slice().sort((a, b) => {
      if (a.mgmt_area_full !== b.mgmt_area_full) return a.mgmt_area_full.localeCompare(b.mgmt_area_full);
      return a.zone_label.localeCompare(b.zone_label);
    });
    sorted.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.zone_label;
      // Aggregate polygons (e.g. dissolved Chico mgmt area in the
      // 2026-05-19 revision) supply their own display label since the
      // zone_label by itself ("02-Vina-Chico") would be noise here.
      opt.textContent = p.is_aggregate && p.rms_label
        ? p.rms_label
        : `${p.mgmt_area_full.replace(/^0\d-/, "")}  ·  ${p.zone_label}`;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => selectPolygon(sel.value));
  }

  // Current selection state for §5.3 table sorting / toggling
  let currentSelection = null;

  function selectPolygon(zoneLabel) {
    selectedPoly = zoneLabel;
    Object.entries(polygonRefs).forEach(([k, r]) => {
      r.lp.setStyle(styleForPolygon(r.poly, k === zoneLabel));
    });
    $("#picker-poly").value = zoneLabel;
    const poly = RMS_POLYGONS.find((p) => p.zone_label === zoneLabel);
    if (!poly) return;

    // Build well list. For aggregate polygons (Chico in the 2026-05-19
    // revision), the wells are the explicit completions associated with
    // the polygon, not a geographic PIP — Chico's territory contains many
    // wells but only 10 are RMS for this network.
    const wellsInside = polygonWells(poly);
    // Color each well using TRACE_COLORS, same order as hydrograph traces
    const wellsWithColor = wellsInside.map((w, i) => ({
      well: w,
      color: TRACE_COLORS[i % TRACE_COLORS.length],
    }));

    // Polygon header
    const rmsList = wellsInside.filter((w) => w.is_2027_gwl_rms).map((w) => w.swn).join(", ")
      || poly.rms_well_swn
      || (poly.rms_well_swns || []).join(", ");
    const headerTitle = poly.is_aggregate && poly.rms_label
      ? `${poly.rms_label} — ${poly.mgmt_area_full} Management Area`
      : `${poly.zone_label} — ${poly.mgmt_area_full} Management Area`;
    $("#poly-header").style.display = "block";
    $("#poly-header-title").textContent = headerTitle;
    $("#poly-header-meta").textContent = `${wellsInside.length} well${wellsInside.length === 1 ? "" : "s"} in zone · ${poly.area_acres.toLocaleString()} acres`;
    const lmlCallout = (!poly.is_aggregate && LML_SWNS.includes(poly.rms_well_swn))
      ? ` · <span style="color:${LML_COLOR}; font-weight:600;">Proposed LML polygon (${lmlTierLabel(poly.rms_well_swn)})</span>`
      : "";
    $("#poly-header-smc").innerHTML = `<strong>2027 GWL RMS well${rmsList.includes(",") ? "s" : ""}:</strong> ${rmsList}${lmlCallout}`;

    // Visibility init: all wells ON by default
    const visibility = {};
    wellsInside.forEach((w) => { visibility[w.swn] = true; });

    currentSelection = {
      poly,
      wellsWithColor,
      visibility,
      sortCol: "rms27",
      sortDir: "asc",
      traceIndices: {},   // §5.3 hydrograph: well.swn -> [traceIdx, ...]
      scatterTraceIndices: {}, // §5.4 scatter: well.swn -> [traceIdx, ...]
      displayMode: currentSelection?.displayMode || "gwe",  // remember mode across polygon changes
    };

    renderHydrograph(poly, wellsInside);
    renderWellDetailTable();
    populateRMSPicker(poly);
    renderSensitivityTable();
    updateLmlControls();
  }

  /* -------------- §5.3 proposed-LML widget (strawman 6/18/2026) --------- */
  // The selected polygon's LML well, if the polygon is one of the 14 the
  // strawman designates. All 5 are single-seed Voronoi cells, so
  // rms_well_swn IS the well; the Chico aggregate is not an LML polygon.
  function selectedLmlWell() {
    if (!currentSelection || !currentSelection.poly) return null;
    const poly = currentSelection.poly;
    if (poly.is_aggregate || !LML_SWNS.includes(poly.rms_well_swn)) return null;
    return WELLS.find((w) => w.swn === poly.rms_well_swn) || null;
  }

  function updateLmlControls() {
    const box = $("#lml-controls");
    if (!box) return;
    const w = selectedLmlWell();
    if (!w || w.mo_ft == null) { box.style.display = "none"; return; }
    box.style.display = "flex";
    const lml = w.mo_ft - lmlOffsetFt;
    // Track the §5.3 hydrograph GWE/DTW pill: when Depth-to-GW mode is active,
    // show the LML level (and the trigger readings) as ft-below-GSE instead of
    // ft msl, so the green bar reads in the same units as the plot above it.
    const gse = w.gse != null ? +w.gse : null;
    const isDtw = currentSelection?.displayMode === "dtw" && gse != null;
    $("#lml-offset-slider").value = lmlOffsetFt;
    const lmlLevelTxt = isDtw
      ? `LML = ${(gse - lml).toFixed(0)} ft below GSE`
      : `LML = ${lml.toFixed(0)} ft msl`;
    $("#lml-offset-display").textContent = `${lmlOffsetFt} ft  (${lmlLevelTxt})`;
    $("#lml-trigger-stats").innerHTML = lmlTriggerStatsHtml(w, lml, isDtw, gse);
    $("#lml-gde-stats").innerHTML = gdePersistenceHtml(w);
  }

  // Historical trigger frequency: of the LML well's QA-Good GWE record, how
  // many readings — and how many distinct WATER YEARS — fall below the
  // candidate LML at the current slider offset, split by drought (Dry/Critical
  // on the Sacramento Valley Index) vs non-drought water year. Answers "how
  // often would this trigger have fired historically, and would it have fired
  // on something other than a drought?" Classified by water year to match the
  // index and the hydrograph shading (and because groundwater lows and the
  // index are both water-year framed — this audience's native vocabulary).
  function lmlTriggerStatsHtml(w, lml, isDtw, gse) {
    const good = getMeas(w).filter((r) =>
      r.gwe != null && r.qa && r.qa.toLowerCase().includes("good"));
    if (!good.length) return `<span style="color:#888;">no QA-Good record to evaluate</span>`;
    const below = good.filter((r) => r.gwe < lml);
    const wyAll = new Set(good.map((r) => waterYearOf(r.d)));
    const wyBelow = [...new Set(below.map((r) => waterYearOf(r.d)))].sort();
    const nonDroughtWYs = wyBelow.filter((wy) => !isDryOrCriticalWY(wy));
    const pctVal = (100 * below.length) / good.length;
    const pct = pctVal.toFixed(pctVal > 0 && pctVal < 10 ? 1 : 0);
    const latest = good[good.length - 1];
    const latestState = latest.gwe < lml
      ? `<b style="color:#b45309;">below</b>`
      : `<b style="color:#1b5e20;">above</b>`;
    const latestTxt = isDtw && gse != null
      ? `${(gse - latest.gwe).toFixed(1)} ft below GSE`
      : `${latest.gwe.toFixed(1)} ft msl`;
    const split = wyBelow.length
      ? ` — <b>${nonDroughtWYs.length}</b> of those ${wyBelow.length === 1 ? "was a non-drought (not Dry/Critical) water year" : "were non-drought (not Dry/Critical) water years"}${nonDroughtWYs.length ? ` (${nonDroughtWYs.join(", ")})` : ""}`
      : ` (never — including every Dry and Critical water year in this well's record)`;
    return `Historically <b>${below.length}</b> of ${good.length.toLocaleString()} QA-Good readings ` +
      `(<b>${pct}%</b>) fell below this LML, in <b>${wyBelow.length}</b> of ${wyAll.size} water years with data${split}. ` +
      `Most recent QA-Good reading (${latest.d}): ${latestTxt} — ${latestState} the LML.`;
  }

  // Great-circle distance in miles between two lat/lon points.
  function haversineMi(lat1, lon1, lat2, lon2) {
    const R = 3958.8, toRad = (d) => (d * Math.PI) / 180;
    const dLat = toRad(lat2 - lat1), dLon = toRad(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 +
      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  // GDE persistence readout for a proposed-LML well: how many ESA "likely GDE"
  // centroids sit near the well under the inclusive Spring-90th-pct scenario
  // vs. how many of those persist into fall (roots_p90_fall), and the distance
  // to the nearest polygon that persists past the spring peak. Makes the LML
  // siting case visible: wells near the persistent Sacramento-corridor core vs.
  // wells (e.g. 32E001M) whose nearby GDEs exist only at the spring peak.
  const GDE_NEAR_MI = 1.5;
  function gdePersistenceHtml(w) {
    if (typeof GDE_CENTROIDS === "undefined" || w.latitude == null) return "";
    let springNear = 0, fallNear = 0, nearestPersistMi = Infinity;
    for (const c of GDE_CENTROIDS) {
      if (c.lat == null || c.lon == null) continue;
      const d = haversineMi(w.latitude, w.longitude, c.lat, c.lon);
      if (c.roots_p90_fall === 1 && d < nearestPersistMi) nearestPersistMi = d;
      if (d > GDE_NEAR_MI) continue;
      if (c.roots_p90_spring === 1) springNear++;
      if (c.roots_p90_fall === 1) fallNear++;
    }
    const nearest = nearestPersistMi === Infinity ? "—" : `${nearestPersistMi.toFixed(1)} mi`;
    const persistNote = fallNear === 0
      ? ` <span style="color:#b45309;">— none persist into fall/dry scenarios within ${GDE_NEAR_MI} mi</span>`
      : "";
    return `<b>Nearby likely GDEs (&le;${GDE_NEAR_MI} mi):</b> ` +
      `Spring 90th pct <b>${springNear}</b> &middot; persist to fall <b>${fallNear}</b>${persistNote}. ` +
      `Nearest GDE that persists past the spring peak: <b>${nearest}</b>. ` +
      `<span style="color:#607d8b;font-size:11px;">(ESA GDE Technical Study centroids; use §5.2 "ESA GDE areas" + scenario dropdown to view the footprints.)</span>`;
  }

  // Plotly background rects for every Dry/Critical water year that overlaps
  // the plotted record. Consecutive same-class water years merge into one rect
  // (fewer seams). CRITICAL: bands are clipped to the data extent — Plotly
  // includes layout shapes in x-axis autorange, so an unclipped 1947 band
  // would stretch a 2009-start well's axis back 60 empty years. A water year
  // spans Oct 1 (prev calendar year) -> Oct 1.
  function droughtShapes(insideWells) {
    if (typeof WY_INDEX === "undefined") return [];
    let minD = null, maxD = null;
    insideWells.forEach((w) => {
      const ms = MEASUREMENTS[w.site_code];
      if (!ms) return;
      ms.forEach((m) => {
        if (m.d == null) return;
        if (minD == null || m.d < minD) minD = m.d;
        if (maxD == null || m.d > maxD) maxD = m.d;
      });
    });
    if (minD == null) return [];
    // Merge consecutive same-class Dry/Critical water years into runs.
    const years = Object.keys(WY_INDEX).map(Number).sort((a, b) => a - b);
    const runs = [];
    years.forEach((y) => {
      const c = WY_INDEX[y].class;
      if (c !== "D" && c !== "C") return;
      const last = runs[runs.length - 1];
      if (last && last.cls === c && last.end === y - 1) last.end = y;
      else runs.push({ cls: c, start: y, end: y });
    });
    const shapes = [];
    runs.forEach((r) => {
      let x0 = `${r.start - 1}-10-01`;
      let x1 = `${r.end}-10-01`;
      if (x1 <= minD || x0 >= maxD) return;   // no overlap with plotted data
      if (x0 < minD) x0 = minD;               // clip to data edges
      if (x1 > maxD) x1 = maxD;
      shapes.push({
        type: "rect", xref: "x", yref: "paper",
        x0, x1, y0: 0, y1: 1,
        fillcolor: DROUGHT_FILL[r.cls], line: { width: 0 }, layer: "below",
      });
    });
    return shapes;
  }

  function renderHydrograph(poly, insideWells) {
    const mode = currentSelection?.displayMode || "gwe";  // "gwe" or "dtw"
    const isDtw = mode === "dtw";
    const traces = [];
    const traceIndices = {};
    let tIdx = 0;

    insideWells.forEach((w, idx) => {
      const color = currentSelection
        ? currentSelection.wellsWithColor.find((wc) => wc.well.swn === w.swn).color
        : TRACE_COLORS[idx % TRACE_COLORS.length];
      const ms = MEASUREMENTS[w.site_code];
      const visible = currentSelection ? (currentSelection.visibility[w.swn] ? true : "legendonly") : true;
      const here = [];

      if (ms && ms.length) {
        // For DTW mode: use the `dtw` field if present, else fall back to (gse - gwe)
        const gse = w.gse != null ? +w.gse : null;
        const toYval = (m) => {
          if (!isDtw) return m.gwe;
          if (m.dtw != null) return m.dtw;
          if (m.gwe != null && gse != null) return gse - m.gwe;
          return null;
        };
        // QA-Good readings only — the population every stat on this page
        // (LML trigger counts, AGWL mirror, exceedance tables) is computed
        // from, and the same convention as the GSA consultant hydrographs
        // and the strawman's SMC method ("excluding questionable
        // measurements"). DWR-flagged questionable readings (e.g. the
        // pumping-influenced recorder series at 05M001M) are not plotted,
        // except via the flagged recorder-derived bridge series below.
        const isGood = (m) => m.qa && m.qa.toLowerCase().includes("good");
        const msGood = ms.filter(isGood);
        if (msGood.length) {
          traces.push({
            x: msGood.map((m) => m.d), y: msGood.map(toYval),
            type: "scatter", mode: "lines+markers",
            name: w.swn + (w.is_2027_gwl_rms ? " (RMS)" : ""),
            line: { color, width: w.is_2027_gwl_rms ? 2.2 : 1.4 },
            marker: { size: w.is_2027_gwl_rms ? 4 : 3, color },
            hovertemplate: isDtw
              ? `<b>${w.swn}</b><br>%{x}<br>%{y:.1f} ft below GSE<extra></extra>`
              : `<b>${w.swn}</b><br>%{x}<br>%{y:.1f} ft msl<extra></extra>`,
            visible,
          });
          here.push(tIdx++);
        }
        // Recorder-derived bridge (05M001M): manual QA-Good measurements
        // lapsed 2005-2019 while the county operated a continuous recorder
        // there; DWR's periodic dataset grades recorder readings
        // "Questionable" as a class. To avoid a misleading 15-year hole —
        // and consistent with the county's own hydrograph practice of using
        // its recorder record — we bridge the gap with the HIGHEST recorder
        // reading of each calendar month (a static-water-level proxy that
        // matches overlapping manual readings within ~0.1-2 ft). Months
        // need >=8 readings to qualify, which isolates the recorder era.
        // Display-only: excluded from every statistic on this page.
        if (RECORDER_DERIVED_SWNS.includes(w.swn)) {
          const byMonth = {};
          ms.forEach((m) => {
            if (isGood(m) || m.gwe == null) return;
            const k = m.d.slice(0, 7);
            (byMonth[k] = byMonth[k] || []).push(m);
          });
          const derived = Object.values(byMonth)
            .filter((arr) => arr.length >= 8)
            .map((arr) => arr.reduce((a, b) => (b.gwe > a.gwe ? b : a)))
            .sort((a, b) => a.d.localeCompare(b.d));
          if (derived.length >= 12) {
            traces.push({
              x: derived.map((m) => m.d), y: derived.map(toYval),
              type: "scatter", mode: "lines+markers",
              name: `${w.swn} (recorder-derived)`,
              line: { color, width: 1.1, dash: "dot" },
              marker: { size: 3.5, symbol: "circle-open", color },
              hovertemplate:
                `<b>${w.swn}</b> recorder-derived<br>%{x}<br>%{y:.1f} ${isDtw ? "ft below GSE" : "ft msl"}` +
                `<br><span style="font-size:11px;">monthly high of county recorder readings ` +
                `(DWR-flagged questionable); static-level proxy, excluded from stats</span><extra></extra>`,
              visible,
            });
            here.push(tIdx++);
          }
        }
      }

      // Per-well thresholds for 2027 RMS wells.
      // Values are groundwater ELEVATIONS in ft msl, NOT depth-below-RPE.
      // Two sources are distinguished in the legend and line style:
      //   "2022 GSP"         — adopted carry-over (dashed, no suffix)
      //   "Strawman Table 3" — county-published proposed values from the
      //                        GWL Strawman memo (6/18/2026), dotted line,
      //                        "(Strawman T3)" suffix in legend
      const gse = w.gse != null ? +w.gse : null;
      const toY = (val) => {
        if (val == null) return null;
        if (!isDtw) return { y: val, unitLabel: `${val.toFixed(1)} ft msl` };
        if (gse == null) return null;
        const y = gse - val;
        return { y, unitLabel: `${y.toFixed(1)} ft below GSE` };
      };
      const pushLine = (val, label, lineColor, dash, width) => {
        const conv = toY(val);
        if (!conv) return;
        traces.push({
          x: ["1980-01-01", new Date().toISOString().slice(0, 10)],
          y: [conv.y, conv.y],
          mode: "lines", type: "scatter",
          name: `${w.swn} ${label}: ${conv.unitLabel}`,
          line: { color: lineColor, width: width || 1.6, dash },
          hovertemplate: `${w.swn} ${label}: ${conv.unitLabel}<extra></extra>`,
          visible,
        });
        here.push(tIdx++);
      };
      if (w.is_2027_gwl_rms) {
        const isAdopted = w.threshold_source === "2022 GSP";
        const sfx = isAdopted ? "" : " (Strawman T3)";
        const addThr = (val, label, lineColor, dashAdopted, dashProposed) =>
          pushLine(val, label + sfx, lineColor, isAdopted ? dashAdopted : dashProposed);
        // MO and MT: adopted=dash, county-proposed=dot
        addThr(w.mo_ft, "MO", "#2a7", "dash", "dot");
        addThr(w.mt_ft, "MT", "#c00", "dash", "dot");
        // IM-2027 keeps dot in both modes (matches existing convention)
        addThr(w.im_2027_ft, "IM-2027", "#6a3aa1", "dot", "dot");
        // Raised MT (sensitivity slider). Only drawn when slider > 0 and
        // only for the polygon's seed RMS well so the hydrograph doesn't
        // accumulate one raised line per well.
        const isPolySeed = (poly.rms_well_swn === w.swn) ||
          (poly.is_aggregate && (poly.rms_primary_swns || []).includes(w.swn));
        if (mtRaiseFt > 0 && w.mt_ft != null && isPolySeed) {
          pushLine(w.mt_ft + mtRaiseFt, `MT + ${mtRaiseFt} ft (sensitivity)`,
                   "#ff8c00", "dash");
        }
        // Proposed LML line — only the 14 LML-designated
        // wells; level follows the §5.3 LML slider (MO minus offset).
        if (LML_SWNS.includes(w.swn) && w.mo_ft != null) {
          pushLine(w.mo_ft - lmlOffsetFt,
                   `proposed LML (MO − ${lmlOffsetFt} ft)`,
                   LML_COLOR, "dashdot", 2.2);
        }
      }
      traceIndices[w.swn] = here;
    });
    if (currentSelection) currentSelection.traceIndices = traceIndices;

    // Drought shading (lowest layer): Dry/Critical water years from the
    // Sacramento Valley Index, clipped to the plotted record and memoized per
    // polygon selection (independent of the DTW toggle and LML slider).
    let shapes;
    if (currentSelection && currentSelection._droughtShapes) {
      shapes = currentSelection._droughtShapes;
    } else {
      shapes = droughtShapes(insideWells);
      if (currentSelection) currentSelection._droughtShapes = shapes;
    }

    const yTitle = isDtw ? "Depth to Groundwater (ft below GSE)" : "Groundwater Elevation (ft msl)";
    const titleText = isDtw
      ? `Depth to Groundwater — ${poly.zone_label} (${insideWells.length} well${insideWells.length === 1 ? "" : "s"})`
      : `Groundwater Elevation — ${poly.zone_label} (${insideWells.length} well${insideWells.length === 1 ? "" : "s"})`;

    const layout = {
      title: { text: titleText, font: { size: 14 } },
      margin: { t: 40, l: 60, r: 16, b: 60 },
      xaxis: { title: "Date", type: "date", showgrid: true, gridcolor: "#eee" },
      yaxis: {
        title: yTitle,
        showgrid: true, gridcolor: "#eee",
        autorange: isDtw ? "reversed" : true,  // flip so MO is up, MT is down
      },
      hovermode: "closest",
      legend: { orientation: "h", y: -0.18, font: { size: 11 } },
      shapes,
      plot_bgcolor: "#fff", paper_bgcolor: "#fff",
    };
    Plotly.react("hydro", traces, layout, { responsive: true, displaylogo: false });

    // Sync the mode buttons' active state
    document.querySelectorAll(".hydro-controls .ctrl-btn[data-mode]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-mode") === mode);
    });
  }

  function setDisplayMode(mode) {
    if (!currentSelection) return;
    currentSelection.displayMode = mode;
    const insideWells = currentSelection.wellsWithColor.map((wc) => wc.well);
    renderHydrograph(currentSelection.poly, insideWells);
    updateLmlControls();  // keep the §5.3 LML green bar in the same units
  }

  /* -------------- §5.3 sortable well detail table (cosmo-style) -------- */
  const TABLE_COLUMNS = [
    { key: "__show",  label: "Show",                  sortable: false, className: "show-col" },
    { key: "name",    label: "Well Name" },
    { key: "rms27",   label: "2027 RMS" },
    { key: "cont",    label: "Continuous" },
    { key: "record",  label: "Record" },
    { key: "flags",   label: "Quality Flags" },
    { key: "use",     label: "Well Use" },
    { key: "depth",   label: "Depth" },
    { key: "gse",     label: "GSE (ft msl)" },
    { key: "wse",     label: "Most Recent Reading" },
  ];

  function buildSortKeys(wc) {
    const w = wc.well;
    const stats = measurementSummary(getMeas(w));
    return {
      well: w,
      color: wc.color,
      stats,
      sort: {
        name: w.swn,
        rms27: w.is_2027_gwl_rms ? 0 : 1,          // RMS first
        cont: isContinuous(w) ? 0 : 1,             // Continuous first
        record: stats.firstYear ? parseInt(stats.firstYear, 10) : 9999,
        flags: stats.questionable + stats.missing, // fewer flags first
        use: w.well_use || "",
        depth: w.well_depth != null ? +w.well_depth : -1,
        gse: w.gse != null ? +w.gse : -1,
        wse: stats.lastGoodGwe != null ? stats.lastGoodGwe : -99999,
      },
    };
  }

  function sortRows(rows, col, dir) {
    const sign = dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = a.sort[col], vb = b.sort[col];
      if (typeof va === "number" && typeof vb === "number") return (va - vb) * sign;
      return String(va).localeCompare(String(vb)) * sign;
    });
  }

  function renderWellDetailTable() {
    const sel = currentSelection;
    if (!sel) return;
    const rows = sel.wellsWithColor.map(buildSortKeys);
    const sorted = sortRows(rows, sel.sortCol, sel.sortDir);

    const headerHtml = TABLE_COLUMNS.map((c) => {
      if (c.sortable === false || c.key === "__show") {
        return `<th class="${c.className || ""}">${c.label}</th>`;
      }
      const active = sel.sortCol === c.key;
      const arrow = active ? (sel.sortDir === "asc" ? "▲" : "▼") : "▲";
      const cls = active ? "sort-arrow" : "sort-arrow inactive";
      return `<th class="sortable" data-col="${c.key}">${c.label}<span class="${cls}">${arrow}</span></th>`;
    }).join("");

    const bodyHtml = sorted.map(({ well: w, color, stats }) => {
      const noDwr = !w.site_code;
      const checked = sel.visibility[w.swn] ? "checked" : "";
      const rmsPill = w.is_2027_gwl_rms
        ? '<span class="pill pill-rms">Yes</span>'
        : '<span class="pill pill-supp">No</span>';
      const contPill = isContinuous(w)
        ? '<span class="pill pill-cont">' + (w.monitor_freq || "Hourly") + '</span>'
        : '<span class="pill pill-supp">' + (w.monitor_freq || "—") + '</span>';
      const recordTxt = noDwr
        ? '<em style="color:#999;">no DWR data</em>'
        : (stats.firstYear ? `${stats.firstYear}–${stats.lastYear}` : "—");
      const goodTxt = noDwr ? "" : `${stats.good.toLocaleString()} good`;
      const flagsTxt = noDwr
        ? '<span style="color:#999;">—</span>'
        : ((stats.questionable + stats.missing) > 0
          ? `<span class="pill pill-flag">${stats.questionable} Q / ${stats.missing} M</span>`
          : '<span style="color:#999;">—</span>');
      const depth = w.well_depth != null ? `${Math.round(w.well_depth)} ft` : "—";
      const gse = w.gse != null ? (+w.gse).toFixed(2) : "—";
      const lastReading = noDwr
        ? '<em style="color:#999;">—</em>'
        : (stats.lastGoodGwe != null
          ? `${stats.lastGoodGwe.toFixed(2)} ft<br><span style="color:#888; font-size:11px;">${stats.lastGoodDate}</span>`
          : (() => {
            const wse = currentWSE(w);
            return wse
              ? `${wse.gwe.toFixed(2)} ft<br><span style="color:#888; font-size:11px;">${wse.date}${wse.qa ? ` (${wse.qa})` : ""}</span>`
              : "—";
          })());
      const nC = nestedCount(w);
      const nestedPill = nC > 1
        ? ` <span class="pill pill-nested" title="This site has ${nC} wells screened at different depths.">Nested ×${nC}</span>`
        : "";
      let thresholdPill = "";
      if (w.is_2027_gwl_rms && w.threshold_source) {
        const isAdopted = w.threshold_source === "2022 GSP";
        const cls = isAdopted ? "pill-thr-gsp" : "pill-thr-mirror";
        const label = isAdopted ? "GSP-adopted MT/MO" : "Strawman Table 3 MT/MO";
        const tip = isAdopted
          ? "Thresholds carried over unchanged from the adopted 2022 Vina GSP."
          : "County-published PROPOSED values from Table 3 of the GWL Strawman (Vina GSA memo, 6/18/2026), derived with the county's Comparable ASGWL method. Not adopted SMC. The dashboard's independently computed AGWL Mirror reproduces these exactly for 27 of 29 wells.";
        thresholdPill = ` <span class="pill ${cls}" title="${tip}">${label}</span>`;
        if (w.table3_divergence) {
          thresholdPill += ` <span class="pill pill-flag" title="${w.table3_divergence.replace(/"/g, "&quot;")}">&#9888; T3 &ne; Mirror</span>`;
        }
      }
      const lmlPill = (w.is_2027_gwl_rms && LML_SWNS.includes(w.swn))
        ? ` <span class="pill pill-lml" title="One of the 14 RMS wells proposed for a non-regulatory Local Management Level in GDE-sensitive areas — 5 designated in the GWL Strawman (6/18/2026), 9 added in the revised strawman (under discussion).">LML proposed</span>`
        : "";
      const bcReason = (w.butte_co_reasoning || "").trim();
      // Show BC reasoning for ANY well that has it (not just RMS).
      // Use the well's SWN explicitly in the label so it's unambiguous which
      // row the note refers to.
      const reasoningRow = bcReason
        ? `<tr class="reasoning-row"><td colspan="${TABLE_COLUMNS.length}">
             <span class="reasoning-label" style="color:${color};">${w.swn}</span>
             — <span class="reasoning-text">${bcReason}</span>
           </td></tr>`
        : "";
      return `
        <tr>
          <td class="show-col">
            <input type="checkbox" data-well-toggle data-swn="${w.swn}" ${checked}>
          </td>
          <td class="well-name-cell" style="color:${color};">
            <span class="color-swatch" style="background:${color};"></span>${w.swn}${nestedPill}${thresholdPill}${lmlPill}
          </td>
          <td>${rmsPill}</td>
          <td>${contPill}</td>
          <td>${recordTxt}${goodTxt ? `<br><span style="color:#888; font-size:11px;">${goodTxt}</span>` : ""}</td>
          <td>${flagsTxt}</td>
          <td>${w.well_use || "—"}</td>
          <td>${depth}</td>
          <td>${gse}</td>
          <td>${lastReading}</td>
        </tr>${reasoningRow}`;
    }).join("");

    $("#well-detail-table-container").innerHTML =
      `<table class="well-detail-table"><thead><tr>${headerHtml}</tr></thead><tbody>${bodyHtml}</tbody></table>`;

    // Wire up column sort
    document.querySelectorAll(".well-detail-table th.sortable").forEach((th) => {
      th.addEventListener("click", () => {
        const col = th.getAttribute("data-col");
        if (sel.sortCol === col) sel.sortDir = sel.sortDir === "asc" ? "desc" : "asc";
        else { sel.sortCol = col; sel.sortDir = "asc"; }
        renderWellDetailTable();
      });
    });
    // Wire up per-row checkbox
    document.querySelectorAll(".well-detail-table input[data-well-toggle]").forEach((cb) => {
      cb.addEventListener("change", () => toggleWell(cb.getAttribute("data-swn"), cb.checked));
    });
  }

  function toggleWell(swn, visible) {
    const sel = currentSelection;
    if (!sel) return;
    sel.visibility[swn] = visible;
    const vis = visible ? true : "legendonly";
    const hIdx = sel.traceIndices[swn] || [];
    if (hIdx.length) Plotly.restyle("hydro", { visible: vis }, hIdx);
    const sIdx = (sel.scatterTraceIndices || {})[swn] || [];
    if (sIdx.length && document.querySelector("#scatter .main-svg")) {
      Plotly.restyle("scatter", { visible: vis }, sIdx);
    }
  }

  function toggleAllWells(visible) {
    const sel = currentSelection;
    if (!sel) return;
    Object.keys(sel.visibility).forEach((k) => { sel.visibility[k] = visible; });
    const vis = visible ? true : "legendonly";
    const allHydroIdx = [];
    Object.values(sel.traceIndices).forEach((arr) => arr.forEach((i) => allHydroIdx.push(i)));
    if (allHydroIdx.length) Plotly.restyle("hydro", { visible: vis }, allHydroIdx);
    const allScatterIdx = [];
    Object.values(sel.scatterTraceIndices || {}).forEach((arr) => arr.forEach((i) => allScatterIdx.push(i)));
    if (allScatterIdx.length && document.querySelector("#scatter .main-svg")) {
      Plotly.restyle("scatter", { visible: vis }, allScatterIdx);
    }
    document.querySelectorAll(".well-detail-table input[data-well-toggle]").forEach((cb) => { cb.checked = visible; });
  }

  /* -------------- 5.4 scatter ------------------------------------------ */
  function populateRMSPicker(poly) {
    const sel = $("#picker-rms");
    sel.innerHTML = "";
    const insideWells = polygonWells(poly);
    let rmsInside = insideWells.filter((w) => w.is_2027_gwl_rms);
    if (rmsInside.length === 0) {
      // Fall back to the seed well
      const seed = WELLS.find((w) => w.swn === poly.rms_well_swn);
      if (seed) rmsInside = [seed];
    }
    rmsInside.forEach((w) => {
      const opt = document.createElement("option");
      opt.value = w.swn;
      opt.textContent = w.swn;
      sel.appendChild(opt);
    });
    sel.value = rmsInside[0]?.swn || "";
    sel.onchange = () => renderScatter(poly, sel.value);
    renderScatter(poly, sel.value);
  }

  function renderScatter(poly, rmsSwn) {
    const ref = WELLS.find((w) => w.swn === rmsSwn);
    if (!ref) { Plotly.purge("scatter"); return; }
    const refMs = MEASUREMENTS[ref.site_code] || [];
    // index ref measurements by YYYY-MM — QA-Good only, like every other
    // graph/statistic on the page (questionable readings, e.g. pumping-
    // influenced recorder data, would distort the pairing and R²).
    const refByMonth = {};
    refMs.forEach((m) => {
      if (m.gwe == null || !(m.qa && m.qa.toLowerCase().includes("good"))) return;
      const k = (m.d || "").slice(0, 7);
      if (!refByMonth[k]) refByMonth[k] = m.gwe;
    });

    // Use the same well order (and colors) as §5.3 hydrograph
    const wellsWithColor = currentSelection?.wellsWithColor
      || polygonWells(poly).map((w, i) => ({ well: w, color: TRACE_COLORS[i % TRACE_COLORS.length] }));

    const traces = [];
    const scatterTraceIndices = {};
    const stats = [];
    let tIdx = 0;

    wellsWithColor.forEach(({ well: w, color }) => {
      if (w.swn === rmsSwn) return;   // skip the reference well itself
      const ms = MEASUREMENTS[w.site_code] || [];
      const xs = [], ys = [], dates = [];
      ms.forEach((m) => {
        if (m.gwe == null || !(m.qa && m.qa.toLowerCase().includes("good"))) return;
        const k = (m.d || "").slice(0, 7);
        const refVal = refByMonth[k];
        if (refVal == null) return;
        xs.push(refVal);
        ys.push(m.gwe);
        dates.push(m.d);
      });
      if (xs.length === 0) return;
      const r = pearson(xs, ys);
      const r2 = r != null ? r * r : null;
      const label = `${w.swn} (n=${xs.length}${r2 != null ? `, R²=${r2.toFixed(2)}` : ""})`;
      const visible = currentSelection ? (currentSelection.visibility[w.swn] ? true : "legendonly") : true;
      traces.push({
        x: xs, y: ys,
        type: "scatter", mode: "markers",
        name: label,
        marker: { color, size: 6, opacity: 0.75, line: { width: 0.5, color: "#fff" } },
        text: dates,
        hovertemplate: `<b>${w.swn}</b><br>%{text}<br>ref=%{x:.1f}, this=%{y:.1f}<extra></extra>`,
        visible,
      });
      scatterTraceIndices[w.swn] = [tIdx++];
      stats.push({ swn: w.swn, n: xs.length, r2 });
    });

    // 1:1 line spanning union range
    let allX = [], allY = [];
    traces.forEach((t) => { allX = allX.concat(t.x); allY = allY.concat(t.y); });
    if (allX.length > 0) {
      const lo = Math.min(...allX, ...allY);
      const hi = Math.max(...allX, ...allY);
      traces.push({
        x: [lo, hi], y: [lo, hi],
        type: "scatter", mode: "lines",
        name: "1:1",
        line: { color: "#888", width: 1.5, dash: "dash" },
        hoverinfo: "skip", showlegend: true,
      });
      // 1:1 line is not tracked in scatterTraceIndices (it's always shown)
    }

    if (currentSelection) currentSelection.scatterTraceIndices = scatterTraceIndices;

    const layout = {
      title: { text: `RMS reference: ${rmsSwn} · ${stats.length} comparison well(s)`, font: { size: 14 } },
      margin: { t: 40, l: 60, r: 20, b: 60 },
      xaxis: { title: `Reference GWE — ${rmsSwn} (ft msl)`, gridcolor: "#eee" },
      yaxis: { title: "Comparison well GWE (ft msl)", gridcolor: "#eee" },
      legend: { orientation: "v", x: 1.02, y: 1, font: { size: 11 } },
      hovermode: "closest",
      plot_bgcolor: "#fff", paper_bgcolor: "#fff",
    };
    Plotly.react("scatter", traces, layout, { responsive: true, displaylogo: false });

    const summary = stats.length
      ? `${stats.length} comparison well(s) paired by month. Best R²: ${
          Math.max(...stats.map((s) => s.r2 || 0)).toFixed(2)
        }`
      : "No paired same-month measurements available for this polygon.";
    $("#scatter-info").textContent = summary;
  }

  /* -------------- §5.3 MT-sensitivity widget wiring -------------------- */
  function renderSensitivityTable() {
    if (!currentSelection) return;
    const poly = currentSelection.poly;
    const polyMT = polygonMT(poly);
    const polyGSE = polygonRmsGSE(poly);
    const polyWells = DOMESTIC_BY_POLYGON[poly.zone_label] || [];
    const polyTotal = polyWells.length;
    const polyLabel = poly.is_aggregate
      ? `Chico polygon (n=${polyTotal})`
      : `${poly.zone_label} (n=${polyTotal})`;

    // Active column: closest 5-ft step to the slider value
    const activeRaise = SENS_RAISES.reduce((best, r) =>
      Math.abs(r - mtRaiseFt) < Math.abs(best - mtRaiseFt) ? r : best, 0);

    const cellHtml = (cnt, total, isActive) => {
      const pct = total > 0 ? (100 * cnt / total) : 0;
      return `<td class="${isActive ? 'sens-current' : ''}">
        <span class="sens-pct">${pct.toFixed(0)}%</span>
        <span class="sens-count">${cnt} of ${total}</span>
      </td>`;
    };

    // Subbasin row
    const basinRow = SENS_RAISES.map((r) => {
      const c = basinDryCount(r, elevCorrectionOn);
      return cellHtml(c.dry, c.total, r === activeRaise);
    }).join("");
    $("#sens-row-basin").innerHTML =
      `<td class="sens-scope">Subbasin (n=${DOMESTIC_ACTIVE.length} domestic wells)</td>` + basinRow;

    // Per-polygon row
    if (polyTotal === 0) {
      const empty = SENS_RAISES.map(() => `<td style="color:#888;">—</td>`).join("");
      $("#sens-row-polygon").innerHTML =
        `<td class="sens-scope">${polyLabel} (no domestic wells)</td>` + empty;
    } else {
      const polyRow = SENS_RAISES.map((r) => {
        const c = countDryDomestic(polyWells, polyMT, polyGSE, r, elevCorrectionOn);
        return cellHtml(c.dry, c.total, r === activeRaise);
      }).join("");
      $("#sens-row-polygon").innerHTML =
        `<td class="sens-scope">${polyLabel}</td>` + polyRow;
    }
  }

  function onSensitivityChange() {
    renderSensitivityTable();
    // Re-render the hydrograph to show/move the raised MT line.
    if (currentSelection) {
      const insideWells = currentSelection.wellsWithColor.map((wc) => wc.well);
      renderHydrograph(currentSelection.poly, insideWells);
    }
  }

  /* -------------- bootstrap --------------------------------------------- */
  function bootstrap() {
    buildDomesticCaches();
    renderKPIs();
    renderMap();
    populatePolygonPicker();
    $("#show-all-wells").addEventListener("click", () => toggleAllWells(true));
    $("#hide-all-wells").addEventListener("click", () => toggleAllWells(false));
    $("#mode-gwe").addEventListener("click", () => setDisplayMode("gwe"));
    $("#mode-dtw").addEventListener("click", () => setDisplayMode("dtw"));
    // MT sensitivity wiring
    $("#mt-raise-slider").addEventListener("input", (e) => {
      mtRaiseFt = +e.target.value;
      $("#mt-raise-display").textContent = `+${mtRaiseFt} ft`;
      onSensitivityChange();
    });
    $("#tog-elev-correction").addEventListener("change", (e) => {
      elevCorrectionOn = e.target.checked;
      onSensitivityChange();
    });
    // Proposed-LML slider wiring (strawman overlay). Re-renders the LML
    // readout + trigger stats, and the hydrograph when an LML polygon is
    // on screen so the LML line tracks the slider.
    $("#lml-offset-slider").addEventListener("input", (e) => {
      lmlOffsetFt = +e.target.value;
      updateLmlControls();
      if (currentSelection && selectedLmlWell()) {
        const insideWells = currentSelection.wellsWithColor.map((wc) => wc.well);
        renderHydrograph(currentSelection.poly, insideWells);
      }
    });
    // Auto-select first polygon
    if (RMS_POLYGONS.length > 0) {
      const first = RMS_POLYGONS.slice().sort((a, b) => a.zone_label.localeCompare(b.zone_label))[0];
      selectPolygon(first.zone_label);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap);
  } else {
    bootstrap();
  }
})();
