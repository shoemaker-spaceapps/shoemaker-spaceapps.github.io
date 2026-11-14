"use strict";
(function () {
  const slides = Array.from(document.querySelectorAll(".slide"));
  const count = document.getElementById("count");
  let i = Math.min(Math.max(parseInt(location.hash.slice(1), 10) - 1 || 0, 0), slides.length - 1);
  function show(n) {
    i = Math.min(Math.max(n, 0), slides.length - 1);
    slides.forEach((s, k) => s.classList.toggle("on", k === i));
    count.textContent = (i + 1) + " / " + slides.length;
    history.replaceState(null, "", "#" + (i + 1));
  }
  document.addEventListener("keydown", (e) => {
    if (["ArrowRight", "PageDown", " "].includes(e.key)) { e.preventDefault(); show(i + 1); }
    if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); show(i - 1); }
    if (e.key === "Home") show(0);
    if (e.key === "End") show(slides.length - 1);
  });
  window.addEventListener("hashchange", () => {
    const n = parseInt(location.hash.slice(1), 10) - 1;
    if (Number.isFinite(n) && n !== i) show(n);
  });
  document.getElementById("next").addEventListener("click", () => show(i + 1));
  document.getElementById("prev").addEventListener("click", () => show(i - 1));
  show(i);
})();
