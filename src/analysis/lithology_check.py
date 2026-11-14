#!/usr/bin/env python3
"""GLiM rock check at selected known sites (diagnosis only; nothing is written to T1).

For each site: the GLiM polygon at the site centre, the area share of every GLiM class inside the site box
(Eckert IV, equal area), and the Macrostrat units at the centre.
Usage: python src/analysis/lithology_check.py [output.csv]
"""
import json
import os
import ssl
import sys
import urllib.request
import warnings

import certifi
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, box

warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GLIM = os.environ.get("GLIM_PATH", os.path.join(ROOT, "data", "raw", "LiMW_GIS 2015.gdb"))
SITES = {"Merriam": "bazaltik", "Black Point": "bazaltik", "Stillwater": "plutonik_bazik", "Mistastin": "plutonik_bazik"}
EXPECT_CODE = {"bazaltik": "vb", "plutonik_bazik": "pb"}
SSL_CTX = ssl.create_default_context(cafile=certifi.where())   # python.org Python on macOS has no system CA store
MACRO = "https://macrostrat.org/api/v2/geologic_units/map?lat={lat}&lng={lon}"


def macrostrat(lat, lon):
    try:
        req = urllib.request.Request(MACRO.format(lat=lat, lon=lon), headers={"User-Agent": "moon-analog-diag"})
        d = json.load(urllib.request.urlopen(req, timeout=30, context=SSL_CTX))
        units = d.get("success", {}).get("data", [])
        return [(u.get("name", ""), u.get("lith", "")) for u in units]
    except Exception as e:
        return [("HATA", str(e))]


def main(out):
    t3 = pd.read_csv(os.path.join(ROOT, "data", "known_analogs_moon.csv"))
    rows, detail = [], []
    for key, exp in SITES.items():
        b = t3[t3.site_name.str.contains(key)].iloc[0]
        bb = gpd.GeoSeries([box(b.lon_min, b.lat_min, b.lon_max, b.lat_max)], crs="EPSG:4326")
        g = gpd.read_file(GLIM, bbox=bb.buffer(0.05))
        eck = g.crs
        boxe = bb.to_crs(eck).iloc[0]
        cen = gpd.GeoSeries([Point(b.center_lon, b.center_lat)], crs="EPSG:4326").to_crs(eck).iloc[0]
        hit = g[g.contains(cen)]
        if len(hit):
            h = hit.iloc[0]
            c_xx, c_litho, c_area = h.xx, h.Litho, h.geometry.area / 1e6
        else:
            c_xx, c_litho, c_area = "-", "-", float("nan")
        gi = g[g.intersects(boxe)].copy()
        gi["pay"] = gi.geometry.intersection(boxe).area / boxe.area
        shares = gi.groupby(["xx", "Litho"]).pay.sum().sort_values(ascending=False)
        xxshare = gi.groupby("xx").pay.sum().sort_values(ascending=False)
        for (xx, lit), v in shares.items():
            detail.append(dict(saha=b.site_name, xx=xx, Litho=lit, kutu_payi=round(v, 4)))
        ms = macrostrat(b.center_lat, b.center_lon)
        exp_code = EXPECT_CODE[exp]
        exp_share = float(xxshare.get(exp_code, 0.0))
        in_box = (b.lat_min <= b.center_lat <= b.lat_max) and (b.lon_min <= b.center_lon <= b.lon_max)
        if not in_box and c_xx == exp_code:
            yorum = (f"GLiM gosteriyor (merkez {exp_code}); ama Tablo 3 kutusu merkezi icermiyor, "
                     f"kutu baska birimin uzerinde ({exp_code} kutu payi %{exp_share*100:.1f})")
        elif exp_share < 0.02:
            yorum = f"GLiM haritasi bu birimi hic gostermiyor ({exp_code} kutu payi %{exp_share*100:.1f})"
        elif c_xx != exp_code:
            yorum = f"GLiM gosteriyor (%{exp_share*100:.1f} {exp_code}), merkez yontemi kaciriyor"
        else:
            yorum = f"GLiM ve merkez dogru ({exp_code} %{exp_share*100:.1f})"
        rows.append(dict(saha=b.site_name, beklenen=exp, kutu_km2=round(boxe.area / 1e6, 1), merkez_kutuda=in_box,
                         merkez_xx=c_xx, merkez_Litho=c_litho, merkez_poligon_km2=round(c_area, 1),
                         kutu_paylari="; ".join(f"{k}:{v*100:.1f}%" for k, v in xxshare.items()),
                         beklenen_pay=round(exp_share, 4),
                         macrostrat="; ".join(f"{n} [{l}]" for n, l in ms[:3]) or "(birim yok)",
                         yorum=yorum))
    R = pd.DataFrame(rows)
    R.to_csv(out, index=False)
    pd.DataFrame(detail).to_csv(out.replace(".csv", "_detay.csv"), index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 200)
    for r in rows:
        print(f"\n=== {r['saha']}  (beklenen {r['beklenen']}, kutu {r['kutu_km2']} km2)")
        for k in ("merkez_kutuda", "merkez_xx", "merkez_Litho", "merkez_poligon_km2", "kutu_paylari", "macrostrat", "yorum"):
            print(f"  {k:<20} {r[k]}")
    print("\nkutu ici Litho alt kodlari:")
    print(pd.DataFrame(detail).to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "pipeline", "diag_lito_v4.csv"))
