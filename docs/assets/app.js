"use strict";
(function () {
  const $ = (s) => document.querySelector(s);
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const LITO = { bazaltik: "basalt", plutonik_bazik: "basic plutonic", sedimanter: "sedimentary", kristalen: "crystalline",
    volkanik_asidik: "acid volcanic", piroklastik: "pyroclastic", su: "water", buz: "ice", bilinmiyor: "unknown" };
  const SCORE = { genel_skor: "Combined (AHP)", arazi_benzerligi: "Terrain only", kayac_eslesmesi: "Rock only", sim: "Pipeline score" };
  const FL = { lesser: 1, well: 2, neg: 4, known: 8, land: 16, rover: 32, n14: 64 };
  const N14_NOTE = "ophiolite gabbro, not anorthosite; we first used this area as a hard negative";
  let W, SC, TG, CAND, BOX, EV, map, pointLayer, knownLayer, negLayer, tgById = {};
  const orderCache = {};

  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const num = (x, d = 1) => (x === null || x === undefined || Number.isNaN(x) ? "n/a" : Number(x).toFixed(d));
  const intf = (x) => (x === null || x === undefined ? "n/a" : Math.round(x).toLocaleString("en-US"));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const wid = (i) => "E_" + String(i).padStart(6, "0");
  const idxOf = (windowId) => parseInt(windowId.slice(2), 10);
  const worldview = (lat, lon) => "https://worldview.earthdata.nasa.gov/?v=" + [lon - 0.3, lat - 0.2, lon + 0.3, lat + 0.2].map((x) => x.toFixed(3)).join(",") +
    "&l=MODIS_Terra_CorrectedReflectance_TrueColor,Coastlines_15m&t=2024-06-15";

  function haversine(a1, o1, a2, o2) {
    const r = Math.PI / 180, p1 = a1 * r, p2 = a2 * r;
    const h = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(((o2 - o1) * r) / 2) ** 2;
    return 2 * 6371 * Math.asin(Math.sqrt(Math.min(h, 1)));
  }

  function setupTheme() {
    const btn = $("#theme");
    const current = () => document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const label = () => { btn.textContent = current() === "dark" ? "Light" : "Dark"; };
    label();
    btn.addEventListener("click", () => {
      const next = current() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) { /* storage blocked */ }
      label(); redrawAll();
    });
  }

  function order(tid) {
    if (orderCache[tid]) return orderCache[tid];
    const g = SC[tid].g, idx = [];
    for (let i = 0; i < g.length; i++) if (g[i] !== null) idx.push(i);
    idx.sort((a, b) => g[b] - g[a] || a - b);
    return (orderCache[tid] = idx);
  }

  function inPool(i, pool, showNeg) {
    const f = W.fl[i];
    if (pool === "lesser") return (f & FL.lesser) !== 0;
    if ((f & FL.neg) && !showNeg) return false;
    if (pool === "bare") return W.mask[i] === 1;
    return true;
  }

  function ranked(tid, pool, showNeg) {
    return order(tid).filter((i) => inPool(i, pool, showNeg));
  }

  function spacedTop(list, n, km) {
    const kept = [];
    for (const i of list) {
      if (kept.every((j) => haversine(W.lat[i], W.lon[i], W.lat[j], W.lon[j]) >= km)) kept.push(i);
      if (kept.length >= n) break;
    }
    return kept;
  }

  function tags(i) {
    const f = W.fl[i], out = [];
    if (f & FL.n14) out.push('<span class="tag warn">ophiolite, former negative</span>');
    if (f & FL.neg) out.push('<span class="tag warn">hard negative</span>');
    if (f & FL.well) out.push('<span class="tag">well-studied area</span>');
    if (f & FL.known) out.push('<span class="tag good">inside a known site</span>');
    return out.join(" ");
  }

  function popupHtml(i, tid, rank, poolName) {
    const t = tgById[tid], g = SC[tid].g[i], a = SC[tid].a ? SC[tid].a[i] : g;
    const lito = W.lito[W.li[i]], rockMatch = t.lito !== "bilinmiyor" ? (lito === t.lito ? "matches" : "differs") : "not compared";
    const clim = W.tmin[i] === null ? "<p>Climate: not available.</p>" :
      `<p>Climate (NASA POWER, 2001 to 2025): lowest hourly temperature ${num(W.tmin[i] / 10)} °C, mean daily swing ${num(W.dr[i] / 10)} °C, ${intf(W.rain[i])} mm rain a year.</p>`;
    const n14 = (W.fl[i] & FL.n14) ? `<p><strong>Note:</strong> ${N14_NOTE}.</p>` : "";
    return `<div class="pop-title">${esc(W.regions[W.reg[i]])}</div>
      <div>${wid(i)} · ${W.lat[i].toFixed(3)}, ${W.lon[i].toFixed(3)}${rank ? ` · rank ${rank} in ${poolName}` : ""}</div>
      <div>Score ${num(g / 1e4, 3)} · terrain similarity ${num(a / 1e4, 3)}</div>
      <table><tr><th></th><th>Earth</th><th>${esc(t.name.split(" (")[0])}</th></tr>
      <tr><td>Median slope</td><td>${num(W.s50[i] / 10)}°</td><td>${num(t.s50)}°</td></tr>
      <tr><td>Steep-end slope</td><td>${num(W.s90[i] / 10)}°</td><td>${num(t.s90)}°</td></tr>
      <tr><td>Relief</td><td>${intf(W.rel[i])} m</td><td>${intf(t.rel)} m</td></tr>
      <tr><td>Rock</td><td>${LITO[lito] || lito}</td><td>${LITO[t.lito] || t.lito}</td></tr></table>
      <div>Rock ${rockMatch}. ${W.bare[i] === null ? "" : W.bare[i] + "% bare ground"}${W.bas[i] ? `, ${W.bas[i]}% basalt cover` : ""}.</div>
      ${clim}${n14}<div>${tags(i)}</div>
      <p><a href="${worldview(W.lat[i], W.lon[i])}" target="_blank" rel="noopener">Open in NASA Worldview</a></p>`;
  }

  let state = { tid: "T_mare", pool: "lesser", spaced: true, showNeg: false, showKnown: true, list: [], top: [], drawn: new Map() };

  function poolName(p) { return { lesser: "lesser-known places", bare: "bare-surface windows", all: "all windows" }[p]; }

  function render() {
    state.tid = $("#target").value; state.pool = $("#pool").value; state.spaced = $("#spaced").checked;
    state.showNeg = $("#showneg").checked; state.showKnown = $("#showknown").checked;
    state.list = ranked(state.tid, state.pool, state.showNeg);
    state.top = state.spaced ? spacedTop(state.list, 20, 30) : state.list.slice(0, 20);
    $("#pool-note").textContent = `${state.list.length.toLocaleString("en-US")} windows in this pool. Showing the best 1,500 on the map.`;
    drawPoints(); drawBoxes(); drawTop();
  }

  function drawPoints() {
    pointLayer.clearLayers(); state.drawn.clear();
    const c1 = css("--dot1"), c2 = css("--dot2"), c3 = css("--dot3"), renderer = L.canvas({ padding: 0.5 });
    const topSet = new Set(state.top), n = Math.min(1500, state.list.length);
    for (let k = n - 1; k >= 0; k--) {
      const i = state.list[k], rank = k + 1, big = topSet.has(i), mid = rank <= 200;
      const neg = (W.fl[i] & FL.neg) !== 0;
      const m = L.circleMarker([W.lat[i], W.lon[i]], {
        renderer, radius: big ? 7 : mid ? 4.5 : 3, weight: neg ? 2 : big ? 1.5 : 0.5,
        color: neg ? "#b23a3a" : big ? "#fff" : "#00000055", fillColor: big ? c1 : mid ? c2 : c3, fillOpacity: big ? 0.95 : 0.8,
      });
      m.bindPopup(() => popupHtml(i, state.tid, rank, poolName(state.pool)), { maxWidth: 320 });
      m.addTo(pointLayer); state.drawn.set(i, m);
    }
  }

  function boxRect(b, style) { return L.rectangle([[b.box[0], b.box[2]], [b.box[1], b.box[3]]], style); }

  function drawBoxes() {
    knownLayer.clearLayers(); negLayer.clearLayers();
    if (state.showKnown) for (const b of BOX.known) {
      const own = b.target === state.tid;
      boxRect(b, { color: "#2b6cb0", weight: own ? 2.5 : 1, fill: false, opacity: own ? 1 : 0.6 })
        .bindTooltip(`${esc(b.name)} (known analog for ${tgById[b.target].name.split(" (")[0]})`).addTo(knownLayer);
    }
    if (state.showNeg) for (const b of BOX.neg) {
      boxRect(b, { color: "#b23a3a", weight: 2, dashArray: "5 4", fill: false })
        .bindTooltip(`${esc(b.name)}: hard negative (${esc(b.kind)}) for ${tgById[b.target].name.split(" (")[0]}${b.removed ? ", removed" : ""}`).addTo(negLayer);
    }
  }

  function drawTop() {
    const t = tgById[state.tid];
    $("#top-title").textContent = `Top 20 for ${t.name}, ${poolName(state.pool)}${state.spaced ? ", at least 30 km apart" : ""}`;
    const rankOf = new Map(state.list.map((i, k) => [i, k + 1]));
    let h = `<thead><tr><th class="n">Rank</th><th>Region</th><th>Lat, lon</th><th class="n">Score</th><th>Rock</th>
      <th class="n">Median slope</th><th class="n">Steep slope</th><th class="n">Relief (m)</th><th class="n">Bare</th></tr></thead><tbody>`;
    for (const i of state.top) {
      h += `<tr class="go" tabindex="0" data-i="${i}" aria-label="Show ${esc(W.regions[W.reg[i]])} on the map">
        <td class="n">${rankOf.get(i)}</td><td>${esc(W.regions[W.reg[i]])} ${tags(i)}</td><td>${W.lat[i].toFixed(3)}, ${W.lon[i].toFixed(3)}</td>
        <td class="n">${num(SC[state.tid].g[i] / 1e4, 3)}</td><td>${LITO[W.lito[W.li[i]]]}</td><td class="n">${num(W.s50[i] / 10)}°</td>
        <td class="n">${num(W.s90[i] / 10)}°</td><td class="n">${intf(W.rel[i])}</td><td class="n">${W.bare[i] === null ? "n/a" : W.bare[i] + "%"}</td></tr>`;
    }
    $("#top-table").innerHTML = '<caption class="sr">Top 20 windows</caption>' + h + "</tbody>";
    for (const tr of document.querySelectorAll("#top-table tr.go")) {
      const go = () => openWindow(+tr.dataset.i);
      tr.addEventListener("click", go);
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
    }
  }

  function openWindow(i) {
    const target = [W.lat[i], W.lon[i]];
    $("#map").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
    if (reduceMotion) map.setView(target, 9); else map.flyTo(target, 9, { duration: 0.8 });
    let m = state.drawn.get(i);
    if (!m) {
      const rank = state.list.indexOf(i) + 1 || null;
      m = L.circleMarker(target, { radius: 7, color: "#fff", fillColor: css("--dot1"), fillOpacity: 1 })
        .bindPopup(popupHtml(i, state.tid, rank, poolName(state.pool)), { maxWidth: 320 }).addTo(pointLayer);
      state.drawn.set(i, m);
    }
    setTimeout(() => m.openPopup(), reduceMotion ? 50 : 850);
  }

  function badgeClass(b) {
    return b === "tested against known sites" ? "tested" : b === "low confidence" ? "low" : b === "terrain only" ? "terrain" : "untested";
  }

  function drawCards() {
    const tid = $("#feat-target").value, t = tgById[tid];
    const rows = CAND.robust.filter((r) => r.target_id === tid);
    $("#cards").innerHTML = rows.map((r) => `
      <article class="card">
        <h3>${esc(r.region)}</h3>
        <div class="where">${r.lat.toFixed(3)}, ${r.lon.toFixed(3)} · rank ${r.rank_ahp} and ${r.rank_pipeline} in our two scores</div>
        <span class="badge ${badgeClass(r.confidence)}">${esc(r.confidence)}</span>
        <dl>
          <dt>Why it is similar</dt><dd>${esc(r.why_similar)}</dd>
          <dt>Where it breaks</dt><dd>${esc(r.where_it_breaks)}</dd>
          <dt>What it is good for</dt><dd>${esc(r.exploration_use)}</dd>
          <dt>Climate</dt><dd>${esc(r.climate)}</dd>
          <dt>Operations</dt><dd>${r.inis_uygun ? "Gentle enough for landing tests (median slope under 5°, steep end under 10°)." :
            r.rover_uygun ? "Rover-drivable (steep-end slope under 20°), too rough for landing tests." : "Too steep for most rovers (steep-end slope over 20°)."}</dd>
        </dl>
        <div class="actions"><button type="button" data-w="${r.window_id}">Show on map</button>
          <a href="${r.worldview_url}" target="_blank" rel="noopener">NASA Worldview</a></div>
      </article>`).join("") || `<p>No window passed both scores for ${esc(t.name)}.</p>`;
    for (const b of document.querySelectorAll("#cards button")) b.addEventListener("click", () => {
      $("#target").value = tid; $("#pool").value = "lesser"; render(); openWindow(idxOf(b.dataset.w));
    });
  }

  function plotLayout(extra) {
    const ink = css("--ink"), line = css("--line");
    return Object.assign({ paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { family: css("--sans"), color: ink, size: 13 },
      margin: { l: 56, r: 16, t: 10, b: 50 }, xaxis: { gridcolor: line, zerolinecolor: line }, yaxis: { gridcolor: line, zerolinecolor: line } }, extra);
  }

  function drawAuc() {
    const order = ["arazi_benzerligi", "kayac_eslesmesi", "genel_skor", "sim"], tg = ["T_mare", "T_imbrium", "T_highland"];
    let h = `<thead><tr><th>Target</th>${order.map((s) => `<th class="n">${SCORE[s]}</th>`).join("")}</tr></thead><tbody>`;
    for (const t of tg) {
      h += `<tr><td>${tgById[t].name.split(" (")[0]}</td>` + order.map((s) => {
        const r = EV.auc.find((x) => x.target_id === t && x.score === s);
        const ci = r.ci_low === null ? "" : `<br><span class="small">${num(r.ci_low, 2)} to ${num(r.ci_high, 2)}</span>`;
        return `<td class="n">${num(r.auc, 2)}${ci}</td>`;
      }).join("") + "</tr>";
    }
    $("#auc-table").innerHTML = '<caption>AUC by target and score (95% interval)</caption>' + h + "</tbody>";
    const colors = { T_mare: css("--accent"), T_imbrium: css("--ochre"), T_highland: css("--sage") };
    const traces = tg.map((t, k) => {
      const rs = order.map((s) => EV.auc.find((x) => x.target_id === t && x.score === s));
      return { type: "scatter", mode: "markers", name: tgById[t].name.split(" (")[0], x: order.map((s) => SCORE[s]), y: rs.map((r) => r.auc),
        marker: { size: 11, color: colors[t] }, offsetgroup: k,
        error_y: { type: "data", symmetric: false, array: rs.map((r) => (r.ci_high === null ? 0 : r.ci_high - r.auc)),
          arrayminus: rs.map((r) => (r.ci_low === null ? 0 : r.auc - r.ci_low)), color: colors[t], thickness: 1.5, width: 4 } };
    });
    Plotly.react("auc-chart", traces, plotLayout({ scattermode: "group", yaxis: { range: [0, 1.02], title: "AUC", gridcolor: css("--line") },
      shapes: [{ type: "line", xref: "paper", x0: 0, x1: 1, y0: 0.5, y1: 0.5, line: { dash: "dot", color: css("--muted"), width: 1 } }],
      annotations: [{ xref: "paper", x: 1, y: 0.5, text: "coin flip", showarrow: false, xanchor: "right", yanchor: "bottom", font: { size: 11, color: css("--muted") } }],
      legend: { orientation: "h", y: -0.2 } }), { displayModeBar: false, responsive: true });
  }

  function drawTables() {
    const nw = W.n.toLocaleString("en-US");
    $("#neg-table").innerHTML = `<thead><tr><th>Negative</th><th>Target</th><th class="n">Best rank</th><th class="n">Terrain only</th></tr></thead><tbody>` +
      EV.negatives.map((n) => `<tr><td>${esc(n.name)} <span class="tag">${esc(n.kind)}</span>${n.status !== "used" ? ' <span class="tag warn">removed: ophiolite gabbro</span>' : ""}</td>
        <td>${tgById[n.target_id].name.split(" (")[0]}</td><td class="n">${intf(n.best_rank_ahp)}</td><td class="n">${intf(n.best_rank_terrain)}</td></tr>`).join("") +
      `</tbody><caption class="small" style="caption-side:bottom">Rank among ${nw} windows. Lower is more similar.</caption>`;
    $("#known-table").innerHTML = `<thead><tr><th>Known site</th><th>Target</th><th class="n">Best rank</th><th class="n">Terrain only</th><th class="n">Rock label right</th></tr></thead><tbody>` +
      EV.known.map((k) => `<tr><td>${esc(k.site_name)}</td><td>${tgById[k.target_id].name.split(" (")[0]}</td><td class="n">${intf(k.best_rank_ahp)}</td>
        <td class="n">${intf(k.best_rank_terrain)}</td><td class="n">${k.glim_label_correct === null ? "n/a" : Math.round(k.glim_label_correct * 100) + "%"}</td></tr>`).join("") + "</tbody>";
    const art = TG.filter((t) => t.kind === "artemis");
    const div = TG.filter((t) => t.div_avg !== null && t.div_avg !== undefined);
    $("#diviner").innerHTML = div.length ? `<div class="table-scroll"><table class="data"><thead><tr><th>Target</th><th class="n">Annual mean (K)</th>
      <th class="n">Coldest spot (K)</th><th class="n">Mean yearly max (K)</th><th class="n">Ice-stable ground</th></tr></thead><tbody>` +
      div.map((t) => `<tr><td>${esc(t.name)}</td><td class="n">${num(t.div_avg, 0)}</td><td class="n">${num(t.div_cold, 0)}</td><td class="n">${num(t.div_max, 0)}</td>
        <td class="n">${Math.round(t.div_ice * 100)}%</td></tr>`).join("") +
      `</tbody></table></div><p class="small">Diviner Polar Resource Product (LRO). Annual mean is 2 cm below the surface, averaged over the 10 km window. "Coldest spot" is the coldest 0.5 km cell in the window. "Ice-stable ground" is the share of the window where water ice would stay stable (losing less than 1 kg per square metre per billion years) within 2.9 m of the surface, the depth limit of the product. The product has no yearly minimum.</p>`
      : "<p>Diviner values were not available.</p>";
    Plotly.react("qm-chart", [
      { type: "scatter", mode: "markers+text", x: art.map((t) => t.qm), y: art.map((t) => t.s50), text: art.map((t) => t.name), textposition: "top center",
        textfont: { size: 11, color: css("--muted") }, marker: { size: 10, color: css("--accent") }, name: "Artemis III regions",
        hovertemplate: "%{text}<br>QuickMap %{x:.1f}°, ours %{y:.1f}°<extra></extra>" },
      { type: "scatter", mode: "lines", x: [4, 18], y: [4, 18], line: { dash: "dot", color: css("--muted"), width: 1 }, name: "equal", hoverinfo: "skip" }],
      plotLayout({ showlegend: false, xaxis: { title: "LROC QuickMap region slope (°)", gridcolor: css("--line"), range: [4, 18] },
        yaxis: { title: "Our 10 km median slope (°)", gridcolor: css("--line"), range: [4, 19] } }), { displayModeBar: false, responsive: true });
    const ex = EV.extremes.filter((e) => tgById[e.target_id].kind === "artemis" || e.target_id === "T_nobile");
    const firsts = [];
    for (const t of TG.filter((t) => t.kind !== "mare" && t.kind !== "imbrium" && t.kind !== "highland"))
      for (const c of ["coldest", "largest_daily_range"]) { const r = ex.find((e) => e.target_id === t.id && e.criterion === c); if (r) firsts.push(r); }
    $("#ext-table").innerHTML = `<thead><tr><th>Target</th><th>Kind</th><th>Region</th><th>Lat, lon</th><th class="n">Lowest hourly temp.</th>
      <th class="n">Mean daily swing</th><th class="n">Rain</th><th class="n">Terrain rank</th></tr></thead><tbody>` +
      firsts.map((e) => `<tr><td>${tgById[e.target_id].name}</td><td>${e.criterion === "coldest" ? "coldest" : "largest swing"}</td>
        <td>${esc(e.region)}${e.n14_note ? ' <span class="tag warn">ophiolite, former negative</span>' : ""}</td><td>${e.lat.toFixed(3)}, ${e.lon.toFixed(3)}</td>
        <td class="n">${num(e.sicaklik_en_soguk_ay_min_C)} °C</td><td class="n">${num(e.gunluk_fark_C)} °C</td><td class="n">${intf(e.yagis_mm_yil)} mm</td>
        <td class="n">${e.rank_terrain}</td></tr>`).join("") + "</tbody>";
  }

  function drawWater() {
    const tid = $("#water-target").value;
    const rows = EV.water.filter((r) => r.target_id === tid).slice(0, 18);
    $("#water-table").innerHTML = `<thead><tr><th>Region</th><th>Group</th><th class="n">Best score</th><th class="n">Aridity</th><th class="n">Bare</th>
      <th class="n">Snow</th><th class="n">Lowest hourly temp.</th><th class="n">Rain</th><th>Reading</th><th>ISRU test use</th></tr></thead><tbody>` +
      rows.map((r) => `<tr class="${r.lesser_known ? "hl" : ""}"><td>${esc(r.region)}${r.well_studied ? ' <span class="tag">well-studied</span>' : ""}${r.lesser_known ? ' <span class="tag good">lesser-known</span>' : ""}</td>
        <td>${esc(r.group)}</td><td class="n">${num(r.best_score, 3)}</td><td class="n">${num(r.aridity, 2)}</td><td class="n">${Math.round(r.bare * 100)}%</td>
        <td class="n">${Math.round(r.snow * 100)}%</td><td class="n">${num(r.coldest_min_C)} °C</td><td class="n">${intf(r.rain_mm)} mm</td>
        <td>${esc(r.reading)}</td><td>${esc(r.isru_test_use)}</td></tr>`).join("") +
      `</tbody><caption class="small" style="caption-side:bottom">Top 18 regions by best score for this target. Aridity index: rain divided by evaporation demand; below 0.05 is hyper-arid.</caption>`;
  }

  function fillSelect(sel, list, value) {
    sel.innerHTML = list.map((t) => `<option value="${t.id}">${esc(t.name)}${t.kind === "artemis" ? " (Artemis III)" : ""}</option>`).join("");
    sel.value = value;
  }

  function redrawAll() {
    if (!W) return;
    drawPoints(); drawAuc(); drawTables();
  }

  async function init() {
    setupTheme();
    const base = document.body.dataset.base || "";
    const get = (n) => fetch(base + "data/" + n + ".json").then((r) => { if (!r.ok) throw new Error(n + " " + r.status); return r.json(); });
    [W, SC, TG, CAND, BOX, EV] = await Promise.all(["windows", "scores", "targets", "candidates", "boxes", "eval"].map(get));
    TG.forEach((t) => (tgById[t.id] = t));
    const q = new URLSearchParams(location.search);
    const startT = tgById[q.get("target")] ? q.get("target") : "T_mare";
    fillSelect($("#target"), TG, startT);
    if (["lesser", "bare", "all"].includes(q.get("pool"))) $("#pool").value = q.get("pool");
    fillSelect($("#feat-target"), TG, "T_mare");
    fillSelect($("#water-target"), TG.filter((t) => t.kind === "artemis" || t.kind === "polar"), "T_nobile");

    map = L.map("map", { worldCopyJump: true, minZoom: 2, zoomControl: true }).setView([18, 20], 2);
    const gibs = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/";
    const modis = L.tileLayer(gibs + "MODIS_Terra_CorrectedReflectance_TrueColor/default/2024-06-15/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
      { maxNativeZoom: 9, maxZoom: 13, attribution: 'Imagery: <a href="https://earthdata.nasa.gov/gibs">NASA GIBS</a>, MODIS Terra' });
    const marble = L.tileLayer(gibs + "BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg",
      { maxNativeZoom: 8, maxZoom: 13, attribution: 'Imagery: <a href="https://earthdata.nasa.gov/gibs">NASA GIBS</a>, Blue Marble' }).addTo(map);
    const esri = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 17, attribution: "Source: Esri, Vantor, Earthstar Geographics, and the GIS User Community" });
    const bases = { modis, marble, esri };
    if (bases[q.get("base")] && q.get("base") !== "marble") { map.removeLayer(marble); bases[q.get("base")].addTo(map); }
    L.control.layers({ "NASA Blue Marble": marble, "NASA MODIS true color (single day, may show gaps and clouds)": modis,
      "Esri high resolution": esri }, null, { collapsed: true }).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
    knownLayer = L.layerGroup().addTo(map); negLayer = L.layerGroup().addTo(map); pointLayer = L.layerGroup().addTo(map);

    for (const id of ["#target", "#pool", "#spaced", "#showneg", "#showknown"]) $(id).addEventListener("change", render);
    $("#feat-target").addEventListener("change", drawCards);
    $("#water-target").addEventListener("change", drawWater);
    const v = (q.get("view") || "").split(",").map(Number);
    if (v.length === 3 && v.every(Number.isFinite)) map.setView([v[0], v[1]], v[2]);
    render(); drawCards(); drawAuc(); drawTables(); drawWater();
    const win = q.get("win");
    if (win && /^E_\d{6}$/.test(win) && idxOf(win) < W.n) openWindow(idxOf(win));
  }

  init().catch((e) => {
    console.error(e);
    const p = document.createElement("p");
    p.textContent = "The data did not load. Please reload the page.";
    $("#explorer .wrap").appendChild(p);
  });
})();
