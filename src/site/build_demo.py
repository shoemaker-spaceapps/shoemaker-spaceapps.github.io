#!/usr/bin/env python3
"""Build the 7-slide demo page (docs/demo/index.html) and fetch its two NASA GIBS satellite images.

Numbers come from docs/data/numbers.json (written by build_site.py); names from src/team.json.
Usage: python src/site/build_demo.py [--docs docs]
"""
import argparse
import json
import math
import os
import ssl
import string
import urllib.request

import certifi

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WMS = ("https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0"
       "&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor&STYLES=&CRS=EPSG:4326&BBOX={b}"
       "&WIDTH=900&HEIGHT=700&FORMAT=image/jpeg&TIME={t}")


def gibs(lat, lon, path, date="2024-06-15", half_lat=0.45):
    half_lon = half_lat * 900 / 700 / max(math.cos(math.radians(lat)), 0.2)
    b = f"{lat - half_lat:.4f},{lon - half_lon:.4f},{lat + half_lat:.4f},{lon + half_lon:.4f}"
    ctx = ssl.create_default_context(cafile=certifi.where())
    data = urllib.request.urlopen(WMS.format(b=b, t=date), timeout=120, context=ctx).read()
    if not data[:3] == b"\xff\xd8\xff":
        raise RuntimeError(f"GIBS did not return a JPEG for {lat},{lon}")
    open(path, "wb").write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--team", default=os.path.join(ROOT, "src", "team.json"))
    ap.add_argument("--date", default="2024-06-15")
    a = ap.parse_args()
    nums = json.load(open(os.path.join(a.docs, "data", "numbers.json"), encoding="utf-8"))
    team = json.load(open(a.team, encoding="utf-8"))
    img = os.path.join(a.docs, "demo", "img")
    os.makedirs(img, exist_ok=True)
    gibs(float(nums["salt_lat"]), float(nums["salt_lon"]), os.path.join(img, "salt.jpg"), a.date)
    gibs(float(nums["mare1_lat"]), float(nums["mare1_lon"]), os.path.join(img, "basalt.jpg"), a.date)
    vals = dict(nums, member_names=", ".join(m["name"] for m in team["members"]),
                site_host=team["site_url"].replace("https://", "").rstrip("/"))
    tpl = string.Template(open(os.path.join(os.path.dirname(__file__), "templates", "demo.html"), encoding="utf-8").read())
    open(os.path.join(a.docs, "demo", "index.html"), "w", encoding="utf-8").write(tpl.substitute(vals))
    print("demo written")


if __name__ == "__main__":
    main()
