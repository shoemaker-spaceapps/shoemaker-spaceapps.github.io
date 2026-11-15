"use strict";
(function () {
  const $ = (s) => document.querySelector(s);
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const T = reduce ? 0 : 1400;
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const worldview = (lat, lon) => "https://worldview.earthdata.nasa.gov/?v=" + [lon - 0.3, lat - 0.2, lon + 0.3, lat + 0.2].map((x) => x.toFixed(3)).join(",") +
    "&l=MODIS_Terra_CorrectedReflectance_TrueColor,Coastlines_15m&t=2024-06-15";
  let DATA = [], byId = {}, moon, earth, current = null, mode = "bare";

  function setupTheme() {
    const btn = $("#theme");
    const cur = () => document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const label = () => { btn.textContent = cur() === "dark" ? "Light" : "Dark"; };
    label();
    btn.addEventListener("click", () => {
      const next = cur() === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem("theme", next); } catch (e) { /* storage blocked */ }
      label();
    });
  }

  function webglOk() {
    try {
      const c = document.createElement("canvas");
      if (!(c.getContext("webgl2") || c.getContext("webgl"))) return false;
    } catch (e) { return false; }
    return !(navigator.deviceMemory && navigator.deviceMemory < 2);
  }

  // seeded star field, drawn once and used as the section background
  function stars(el) {
    const c = document.createElement("canvas"), w = 1600, h = 900, g = c.getContext("2d");
    c.width = w; c.height = h;
    let s = 7;
    const rnd = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let k = 0; k < 900; k++) {
      const r = rnd() < 0.96 ? 0.6 : 1.3;
      g.fillStyle = `rgba(255,250,240,${0.25 + rnd() * 0.6})`;
      g.beginPath(); g.arc(rnd() * w, rnd() * h, r, 0, Math.PI * 2); g.fill();
    }
    el.style.backgroundImage = `url(${c.toDataURL("image/png")})`;
  }

  // light both globes from the side so the terminator shows, like a view from orbit
  function sunlight(globe, ambient) {
    const ls = typeof globe.lights === "function" ? globe.lights() : [];
    ls.forEach((l) => {
      if (l.isAmbientLight) l.intensity = ambient;
      if (l.isDirectionalLight) { l.intensity = 3.6; l.position.set(-2.2, 0.8, 1.0); }
    });
    if (typeof globe.lights === "function") globe.lights(ls);
  }

  // keep the Earth's sunlit side facing the viewer, turned 25 degrees so a soft terminator stays near the limb
  function followCamera(globe) {
    const light = globe.lights().find((l) => l.isDirectionalLight), cam = globe.camera();
    const c = Math.cos(0.44), s = Math.sin(0.44);
    const tick = () => {
      const p = cam.position;
      light.position.set(p.x * c + p.z * s, p.y + 0.15 * Math.hypot(p.x, p.z), -p.x * s + p.z * c);
      requestAnimationFrame(tick);
    };
    tick();
  }

  function makeGlobe(el, tex, atmosphere, ambient) {
    const g = Globe({ animateIn: false })(el)
      .globeImageUrl(tex).backgroundColor("rgba(0,0,0,0)")
      .showAtmosphere(atmosphere).atmosphereColor("#9cc0ea").atmosphereAltitude(0.13)
      .width(el.clientWidth).height(el.clientHeight);
    const ctl = g.controls();
    ctl.autoRotate = !reduce; ctl.autoRotateSpeed = 0.25; ctl.enableZoom = true;
    ctl.addEventListener("start", () => { ctl.autoRotate = false; });
    sunlight(g, ambient);
    return g;
  }

  function color(score, lo, hi) {
    const t = Math.max(0, Math.min(1, (score - lo) / ((hi - lo) || 1)));
    const a = [214, 196, 160], b = [240, 120, 60];
    return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(",")})`;
  }

  function moonPins() {
    moon.pointsData(DATA).pointLat("lat").pointLng("lon").pointAltitude((d) => (d === current ? 0.06 : 0.02))
      .pointRadius((d) => (d === current ? 1.4 : d.kind === "artemis" ? 0.45 : 0.9))
      .pointColor((d) => (d === current ? "#f0915f" : d.kind === "artemis" ? "#e8d3a8" : "#fff4dc"))
      .pointLabel((d) => `<b>${esc(d.name)}</b>`).onPointClick((d) => select(d.id, true));
    moon.labelsData(DATA.filter((d) => d.kind !== "artemis" || d === current)).labelLat("lat").labelLng("lon")
      .labelText((d) => d.name.split(" (")[0]).labelSize((d) => (d === current ? 2.6 : 2.0)).labelDotRadius(0).labelAltitude(0.03)
      .labelColor((d) => (d === current ? "#ffffff" : "rgba(255,244,220,0.9)")).labelResolution(3);
  }

  // bare: robust candidates and top 100 lesser-known bare windows; any: rock analogs and top 100 of all windows
  function pointsFor(t) {
    if (mode === "any") {
      const hi = t.rock.length ? t.rock : t.any.slice(0, 5);
      return hi.map((p) => Object.assign({ best: true }, p)).concat(t.any.filter((p) => !hi.includes(p)).map((p) => Object.assign({ best: false }, p)));
    }
    return t.best.map((p) => Object.assign({ best: true }, p)).concat(t.top.map((p) => Object.assign({ best: false }, p)));
  }

  function earthPoints(t) {
    const all = pointsFor(t);
    const scores = all.map((p) => p.g), lo = Math.min(...scores), hi = Math.max(...scores);
    earth.pointsData(all).pointLat("lat").pointLng("lon").pointAltitude((d) => (d.best ? 0.06 : 0.012))
      .pointRadius((d) => (d.best ? 1.2 : 0.45)).pointColor((d) => (d.best ? (d.mask ? "#f0915f" : "#9fd3c7") : color(d.g, lo, hi)))
      .pointLabel((d) => `${esc(d.reg)}<br>rank ${d.r ?? ""}${d.mask ? "" : "<br>not bare (fails the surface mask)"}`).onPointClick((d) => showCard(t, d));
  }

  function row(label, m, e) { return `<tr><th scope="row">${label}</th><td>${m}</td><td>${e}</td></tr>`; }

  function showCard(t, p) {
    const m = t.moon, card = $("#card");
    const moonCold = m.cold != null ? `${Math.round(m.cold - 273.15)} °C yearly mean (${m.cold} K), coldest spot (Diviner)` : "not in our data (Diviner polar product only)";
    const link = `explore/?target=${t.id}&pool=${mode === "any" ? "all" : "lesser"}&view=${p.lat},${p.lon},9&win=${p.w}`;
    card.innerHTML = `<button type="button" class="close" aria-label="Close comparison">×</button>
      <h3>${esc(p.reg)}</h3>
      <p class="small">${p.lat.toFixed(3)}, ${p.lon.toFixed(3)} · rank ${p.r} ${mode === "any" ? "among all windows" : "among lesser-known places"}${p.mask ? "" : " · not bare (fails the surface mask), " + p.bare + "% bare"}${p.note ? " · " + esc(p.note) : ""}${p.n14 ? " · low confidence: ophiolite gabbro, not anorthosite; we first used this area as a hard negative" : ""}</p>
      <table><thead><tr><th></th><th>${esc(t.name.split(" (")[0])}</th><th>This place</th></tr></thead><tbody>
      ${row("Median slope", m.s50 + "°", p.s50 + "°")}${row("Steep-end slope", m.s90 + "°", p.s90 + "°")}
      ${row("Relief", m.rel.toLocaleString("en-US") + " m", p.rel.toLocaleString("en-US") + " m")}
      ${row("Rock", m.lito, p.lito)}${row("Coldest", moonCold, p.tmin + " °C lowest hourly, 2001 to 2025")}</tbody></table>
      <p><b>Where it breaks:</b> ${esc(p.br)}</p>
      <p class="links"><a href="${worldview(p.lat, p.lon)}" target="_blank" rel="noopener">NASA Worldview</a> <a href="${link}">See on detailed map</a></p>`;
    card.hidden = false;
    card.querySelector(".close").addEventListener("click", () => { card.hidden = true; });
  }

  function select(id, fromGlobe, focus) {
    const t = byId[id];
    if (!t) return;
    current = t;
    document.querySelectorAll("#targets button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === id)));
    $("#earth-label").textContent = `best matches for ${t.name}`;
    $("#card").hidden = true;
    if (moon) {
      moonPins();
      moon.controls().autoRotate = false;
      moon.pointOfView({ lat: t.lat, lng: t.lon, altitude: t.lat < -75 ? 1.5 : 1.9 }, fromGlobe ? T / 2 : T);
    }
    if (earth) {
      earthPoints(t);
      earth.controls().autoRotate = false;
      const pts = pointsFor(t), b = focus || pts[0];
      earth.pointOfView({ lat: b.lat, lng: b.lon, altitude: 1.25 }, T);
      setTimeout(() => { $("#earth-globe").dataset.view = `${b.lat},${b.lon}`; $("#earth-globe").dataset.target = t.id; }, T + 50);
    }
  }

  function setMode(m) {
    mode = m;
    document.querySelectorAll("#surface button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.mode === m)));
    $("#earth-globe").dataset.mode = m;
    if (current) select(current.id, false);
  }

  function findTable() {
    document.querySelectorAll("#found-table .rowbtn, #task-table .rowbtn").forEach((b) => b.addEventListener("click", () => {
      const lat = +b.dataset.lat, lon = +b.dataset.lon;
      mode = b.dataset.mode;
      document.querySelectorAll("#surface button").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.mode === mode)));
      $("#earth-globe").dataset.mode = mode;
      select(b.dataset.target, false, { lat, lon });
      $("#globes").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }));
  }

  function targetButtons() {
    const groups = [["Apollo and Nobile", DATA.filter((d) => d.kind !== "artemis")], ["Artemis III", DATA.filter((d) => d.kind === "artemis")]];
    $("#targets").innerHTML = groups.map(([name, list]) => `<div class="tgroup"><span class="tlabel">${name}</span>` +
      list.map((d) => `<button type="button" data-id="${d.id}" aria-pressed="false">${esc(d.name.replace(/ \(.*\)$/, ""))}</button>`).join("") + "</div>").join("");
    document.querySelectorAll("#targets button").forEach((b) => b.addEventListener("click", () => select(b.dataset.id, false)));
  }

  async function init() {
    setupTheme();
    stars($(".space"));
    DATA = await fetch("data/home.json").then((r) => r.json());
    DATA.forEach((d) => (byId[d.id] = d));
    targetButtons();
    document.querySelectorAll("#surface button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
    findTable();
    if (typeof Globe !== "function" || !webglOk()) {
      $("#globes").hidden = true; $("#fallback").hidden = false;
      select("T_mare");
      return;
    }
    moon = makeGlobe($("#moon-globe"), "assets/moon_2k.jpg", false, 1.1);
    earth = makeGlobe($("#earth-globe"), "assets/earth_2k.jpg", true, 0.9);
    followCamera(earth);
    moon.pointOfView({ lat: 0.7, lng: 23.5, altitude: 1.9 }, 0);
    earth.pointOfView({ lat: 25, lng: 40, altitude: 1.6 }, 0);
    $("#pole").addEventListener("click", () => { moon.controls().autoRotate = false; moon.pointOfView({ lat: -82, lng: 40, altitude: 1.45 }, T); });
    window.addEventListener("resize", () => {
      for (const [g, id] of [[moon, "#moon-globe"], [earth, "#earth-globe"]]) g.width($(id).clientWidth).height($(id).clientHeight);
    });
    select("T_mare");
    window.__globes = { moon, earth, select, setMode, mode: () => mode, points: () => earth.pointsData(), data: () => DATA };
  }

  init().catch((e) => {
    console.error(e);
    $("#globes").hidden = true; $("#fallback").hidden = false;
  });
})();
