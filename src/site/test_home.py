#!/usr/bin/env python3
"""Test the homepage globes: visible word count, target selection, comparison card, link to the explore page,
and load time.

Usage: python src/site/test_home.py [--docs docs | --url https://...]
"""
import argparse
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from capture import GL_ARGS, ROOT, open_best_card, serve  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--url", default="")
    a = ap.parse_args()
    srv, base = (None, a.url.rstrip("/")) if a.url else serve(a.docs)
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(args=GL_ARGS)
        pg = b.new_page(viewport=dict(width=1440, height=900))
        t0 = time.time()
        pg.goto(base + "/", wait_until="domcontentloaded")
        pg.wait_for_selector("#earth-globe[data-view]", timeout=60000)
        ready = time.time() - t0
        nav = pg.evaluate("(() => { const n = performance.getEntriesByType('navigation')[0]; return [n.domContentLoadedEventEnd, n.loadEventEnd]; })()")
        words = pg.evaluate("document.body.innerText.split(/\\s+/).filter(w => /[A-Za-z0-9]/.test(w)).length")
        print(f"load: DOMContentLoaded {nav[0] / 1000:.2f} s, load {nav[1] / 1000:.2f} s, globes ready {ready:.2f} s")
        print(f"visible words on the homepage: {words}")
        data = pg.evaluate("window.__globes.data()")
        for tid in ["T_mare", "T_ma"]:
            t = next(d for d in data if d["id"] == tid)
            pg.click(f"#targets button[data-id={tid}]")
            pg.wait_for_function(f"document.querySelector('#earth-globe').dataset.target === '{tid}'", timeout=10000)
            view = pg.locator("#earth-globe").get_attribute("data-view")
            pov = pg.evaluate("window.__globes.earth.pointOfView()")
            exp = (t["best"][0]["lat"], t["best"][0]["lon"])
            turned = abs(pov["lat"] - exp[0]) < 1 and abs(((pov["lng"] - exp[1] + 180) % 360) - 180) < 1
            print(f"{tid}: earth turned to best candidate {exp}: {turned} (view {view})")
            ok &= turned
        pg.click("#targets button[data-id=T_mare]")
        pg.wait_for_function("document.querySelector('#earth-globe').dataset.target === 'T_mare'", timeout=10000)
        pg.wait_for_timeout(300)
        open_best_card(pg)
        card = pg.locator("#card")
        has = card.is_visible() and "Where it breaks" in card.inner_text()
        href = card.locator("a", has_text="See on detailed map").get_attribute("href")
        print(f"card opens on click: {has}; link: {href}")
        ok &= has
        ex = b.new_page(viewport=dict(width=1440, height=900))
        ex.goto(base + "/" + href, wait_until="networkidle")
        ex.wait_for_selector(".leaflet-popup-content", timeout=15000)
        win = href.split("win=")[1]
        popup = ex.locator(".leaflet-popup-content").inner_text()
        opened = win in popup
        print(f"explore link opens window {win} in a popup: {opened}")
        ok &= opened
        b.close()
    if srv:
        srv.shutdown()
    print("all homepage tests passed" if ok else "SOME HOMEPAGE TESTS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
