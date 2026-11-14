#!/usr/bin/env python3
"""Browser captures with Playwright: globe and map images, submission images, demo.pdf, and slide thumbnails.

Usage: python src/site/capture.py [--docs docs] [--submission submission] [--sheet slides_sheet.png]
"""
import argparse
import base64
import functools
import http.server
import os
import threading

from playwright.sync_api import sync_playwright

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
HIDE_HEADER = ".top, .skip { display: none !important; }"
GL_ARGS = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]   # WebGL in headless Chromium


def open_best_card(page):
    """Click the best Earth candidate of the selected target and wait for the comparison card."""
    page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
    page.wait_for_timeout(200)
    xy = page.evaluate("""() => { const g = window.__globes, t = g.data().find(d => d.id === document.querySelector('#earth-globe').dataset.target);
        const b = t.best[0], c = g.earth.getScreenCoords(b.lat, b.lon, 0.06), r = document.querySelector('#earth-globe').getBoundingClientRect();
        return [r.left + c.x, r.top + c.y]; }""")
    page.mouse.click(xy[0], xy[1])
    page.wait_for_selector("#card:not([hidden])", timeout=5000)


def serve(directory):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=directory)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--submission", default=os.path.join(ROOT, "submission"))
    ap.add_argument("--sheet", default="", help="optional path for a 7-thumbnail contact sheet (kept out of the repo)")
    a = ap.parse_args()
    img, sub = os.path.join(a.docs, "demo", "img"), os.path.join(a.submission, "images")
    os.makedirs(img, exist_ok=True)
    os.makedirs(sub, exist_ok=True)
    srv, base = serve(a.docs)
    with sync_playwright() as p:
        b = p.chromium.launch(args=GL_ARGS)
        h = b.new_page(viewport=dict(width=1600, height=900), device_scale_factor=1)
        h.goto(f"{base}/", wait_until="networkidle")
        h.wait_for_selector("#earth-globe[data-view]", timeout=30000)
        h.wait_for_timeout(1500)
        h.locator("#globes").screenshot(path=os.path.join(a.docs, "assets", "globes_static.jpg"), type="jpeg", quality=80)
        open_best_card(h)
        h.wait_for_timeout(600)
        h.locator("#globes").screenshot(path=os.path.join(img, "globes_mare.jpg"), type="jpeg", quality=84)
        h.locator("#globes").screenshot(path=os.path.join(sub, "globes.png"))
        pg = b.new_page(viewport=dict(width=1600, height=900), device_scale_factor=1)
        pg.add_init_script("document.addEventListener('DOMContentLoaded', () => { const s = document.createElement('style');"
                           f" s.textContent = '{HIDE_HEADER} #map {{ height: 900px !important; }}'; document.head.appendChild(s); }});")
        pg.goto(f"{base}/explore/?target=T_mare&pool=lesser&view=21.5,42,5", wait_until="networkidle")
        pg.wait_for_timeout(4000)
        hi = b.new_page(viewport=dict(width=1440, height=900), device_scale_factor=2)
        hi.add_init_script(f"document.addEventListener('DOMContentLoaded', () => {{ const s = document.createElement('style'); s.textContent = '{HIDE_HEADER}'; document.head.appendChild(s); }});")
        hi.goto(f"{base}/explore/?target=T_mare", wait_until="networkidle")
        hi.wait_for_timeout(1500)
        hi.locator("#cards .card").first.screenshot(path=os.path.join(sub, "candidate_card.png"))
        pg.locator("#checked .split").first.screenshot(path=os.path.join(sub, "auc_chart.png"))
        pg.locator("#artemis .split").first.screenshot(path=os.path.join(sub, "artemis_chart.png"))

        d = b.new_page(viewport=dict(width=1280, height=720))
        d.goto(f"{base}/demo/", wait_until="networkidle")
        d.wait_for_timeout(800)
        n = d.locator(".slide").count()
        thumbs = []
        for k in range(1, n + 1):
            d.evaluate("n => { location.hash = '#' + n; }", k)
            d.wait_for_timeout(400)
            path = os.path.join(os.path.dirname(a.sheet) or ".", f"slide_{k}.png") if a.sheet else None
            if path:
                d.screenshot(path=path)
                thumbs.append(path)
        d.emulate_media(media="print")
        d.pdf(path=os.path.join(a.docs, "demo", "demo.pdf"), width="1280px", height="720px", print_background=True)
        if a.sheet:
            uri = lambda t: "data:image/png;base64," + base64.b64encode(open(t, "rb").read()).decode()
            html = "<body style='margin:0;background:#ddd;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;padding:10px'>" + \
                "".join(f"<div><img src='{uri(t)}' style='width:100%;border:1px solid #999'><div style='font:14px sans-serif'>Slide {i}</div></div>"
                        for i, t in enumerate(thumbs, 1)) + "</body>"
            s = b.new_page(viewport=dict(width=1600, height=560))
            s.set_content(html)
            s.wait_for_timeout(500)
            s.screenshot(path=a.sheet, full_page=True)
        b.close()
    srv.shutdown()
    print("captures written:", sorted(os.listdir(sub)), sorted(os.listdir(img)))


if __name__ == "__main__":
    main()
