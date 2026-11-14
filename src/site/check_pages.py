#!/usr/bin/env python3
"""Open the homepage, the explore page and the demo at desktop and phone width; report console errors,
horizontal overflow and broken images.

Usage: python src/site/check_pages.py [--docs docs | --url https://...] [--shots DIR]
"""
import argparse
import os
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from capture import GL_ARGS, ROOT, serve  # noqa: E402


def label_check(problems):
    """No place label says Türkiye for a window whose Natural Earth country is another one."""
    import json
    import pandas as pd
    sys.path.insert(0, os.path.join(ROOT, "src", "analysis"))
    import final_analysis as F
    t1, t2, t3, neg, ahp, sim = F.load(F.PIPE)
    w = F.window_frame(t1, t3, neg).set_index("window_id")
    bad = w[w.region.str.contains("Türkiye") & (w.country != "Türkiye")]
    problems += [f"label {i}: '{r.region}' but country {r.country}" for i, r in bad.iterrows()]
    seen = 0
    for f, col, idc in [("robust_candidates", "region", "window_id"), ("lesser_known_top20", "region", "window_id"),
                        ("climate_extremes", "region", "window_id"), ("rock_analogs", "place", "window_id"),
                        ("water_ice", "region", "best_window")]:
        d = pd.read_csv(os.path.join(ROOT, "results", f + ".csv"))
        for lab, wid in zip(d[col], d[idc]):
            seen += 1
            if "Türkiye" in str(lab) and w.loc[wid, "country"] != "Türkiye":
                problems.append(f"{f}: '{lab}' on {wid} in {w.loc[wid, 'country']}")
    for t in json.load(open(os.path.join(ROOT, "docs", "data", "home.json"), encoding="utf-8")):
        for k in ("best", "top", "rock", "any"):
            for p in t[k]:
                seen += 1
                if "Türkiye" in p["reg"] and w.loc[p["w"], "country"] != "Türkiye":
                    problems.append(f"home.json {t['id']}: '{p['reg']}' on {p['w']}")
    print(f"label check: {seen} labels in tables and globe data, {len(w)} windows")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--url", default="", help="check a live site instead of the local docs folder")
    ap.add_argument("--shots", default="", help="optional folder for screenshots (kept out of the repo)")
    a = ap.parse_args()
    srv, base = (None, a.url.rstrip("/")) if a.url else serve(a.docs)
    problems = []
    if not a.url:
        label_check(problems)
    with sync_playwright() as p:
        b = p.chromium.launch(args=GL_ARGS)
        # "narrow" is a plain 390 px window: a phone browser may zoom out and hide overflow that this one shows
        for name, vp in [("desktop", dict(width=1440, height=900)), ("phone", dict(width=390, height=844)),
                         ("narrow", dict(width=390, height=844))]:
            for page_name, path in [("home", "/"), ("explore", "/explore/"), ("demo", "/demo/")]:
                pg = b.new_page(viewport=vp, is_mobile=name == "phone", has_touch=name == "phone")
                # GL driver messages come from the software GPU of headless Chromium, not from the page
                pg.on("console", lambda m, t=f"{page_name}/{name}": problems.append(f"{t} console {m.type}: {m.text}")
                      if m.type in ("error", "warning") and "GL Driver Message" not in m.text else None)
                pg.on("pageerror", lambda e, t=f"{page_name}/{name}": problems.append(f"{t} page error: {e}"))
                resp = pg.goto(base + path, wait_until="networkidle")
                pg.wait_for_timeout(2500)
                if resp is None or resp.status != 200:
                    problems.append(f"{page_name}/{name} HTTP {resp.status if resp else 'none'}")
                over = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 2:
                    problems.append(f"{page_name}/{name} horizontal overflow {over}px")
                broken = pg.evaluate("Array.from(document.images).filter(i => i.complete && i.naturalWidth === 0).map(i => i.src)")
                problems += [f"{page_name}/{name} broken image {s}" for s in broken]
                if a.shots:
                    os.makedirs(a.shots, exist_ok=True)
                    pg.screenshot(path=os.path.join(a.shots, f"{page_name}_{name}.png"))
                pg.close()
        b.close()
    if srv:
        srv.shutdown()
    print("\n".join(problems) if problems else "no problems found")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
