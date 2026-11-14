#!/usr/bin/env python3
"""Climate per Earth window from the NASA POWER climatology API (no account needed).

Windows are grouped by POWER's native grid cell (0.5 x 0.625 deg, MERRA-2), one request per cell.
Finished cells are cached, so a rerun continues where it stopped.

Usage: python src/pipeline/power_climate.py [--t1 results/pipeline/T1_earth_windows.csv] [--out results/pipeline/iklim_power.csv]
"""
import argparse
import csv
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

import certifi
import numpy as np
import pandas as pd

PIPE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "results", "pipeline"))

API = ("https://power.larc.nasa.gov/api/temporal/climatology/point?parameters={p}"
       "&community=RE&longitude={lon}&latitude={lat}&format=JSON")
PARAMS = ["T2M", "T2M_MIN", "T2M_MAX", "T2M_RANGE", "PRECTOTCORR", "WS10M", "RH2M", "ALLSKY_SFC_SW_DWN"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
CELL_LAT, CELL_LON = 0.5, 0.625
CTX = ssl.create_default_context(cafile=certifi.where())   # python.org Python on macOS has no system CA store
COLS = ["power_hucre", "cell_lat", "cell_lon", "sicaklik_yillik_ort_C", "sicaklik_en_soguk_ay_min_C",
        "sicaklik_en_sicak_ay_max_C", "gunluk_fark_C", "yagis_mm_yil", "ruzgar_10m_ms", "bagil_nem_yuzde",
        "gunes_kWh_m2_gun"]


def cell_of(lat, lon):
    la = np.round(np.asarray(lat) / CELL_LAT) * CELL_LAT
    lo = np.round(np.asarray(lon) / CELL_LON) * CELL_LON
    return la, lo


def fetch(lat, lon, tries=8, pause=0.5):
    url = API.format(p=",".join(PARAMS), lat=f"{lat:.4f}", lon=f"{lon:.4f}")
    err = None
    for i in range(tries):
        try:
            time.sleep(pause)
            req = urllib.request.Request(url, headers={"User-Agent": "moon-analog-climate"})
            d = json.load(urllib.request.urlopen(req, timeout=90, context=CTX))
            return d["properties"]["parameter"]
        except urllib.error.HTTPError as e:
            err = e
            wait = int(e.headers.get("Retry-After") or 0) if e.code == 429 else 0
            time.sleep(max(wait, min(120, 5 * 2 ** i)))
        except Exception as e:
            err = e
            time.sleep(min(120, 5 * 2 ** i))
    print(f"  skipped {lat},{lon}: {err}", flush=True)
    return None


def summarize(key, lat, lon, p):
    def v(x):
        return np.nan if x is None or x <= -998 else float(x)
    monthly = lambda name: [v(p[name].get(m)) for m in MONTHS]
    return dict(power_hucre=key, cell_lat=lat, cell_lon=lon,
                sicaklik_yillik_ort_C=v(p["T2M"].get("ANN")),
                sicaklik_en_soguk_ay_min_C=np.nanmin(monthly("T2M_MIN")),
                sicaklik_en_sicak_ay_max_C=np.nanmax(monthly("T2M_MAX")),
                gunluk_fark_C=v(p["T2M_RANGE"].get("ANN")),
                yagis_mm_yil=round(v(p["PRECTOTCORR"].get("ANN")) * 365.25, 1),
                ruzgar_10m_ms=v(p["WS10M"].get("ANN")),
                bagil_nem_yuzde=v(p["RH2M"].get("ANN")),
                gunes_kWh_m2_gun=v(p["ALLSKY_SFC_SW_DWN"].get("ANN")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t1", default=os.path.join(PIPE, "T1_earth_windows.csv"))
    ap.add_argument("--out", default=os.path.join(PIPE, "iklim_power.csv"))
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    t1 = pd.read_csv(a.t1, usecols=["window_id", "lat", "lon"])
    la, lo = cell_of(t1.lat, t1.lon)
    t1["power_hucre"] = [f"{x:+.2f}_{y:+.3f}" for x, y in zip(la, lo)]
    cells = t1.drop_duplicates("power_hucre").assign(cell_lat=la[~t1.power_hucre.duplicated()],
                                                     cell_lon=lo[~t1.power_hucre.duplicated()])
    cache = os.path.splitext(a.out)[0] + "_cells.csv"
    done = set(pd.read_csv(cache).power_hucre) if os.path.exists(cache) else set()
    todo = cells[~cells.power_hucre.isin(done)]
    print(f"{len(t1)} windows, {len(cells)} POWER cells, {len(done)} cached, {len(todo)} to fetch", flush=True)
    new = not os.path.exists(cache)
    with open(cache, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if new:
            w.writeheader()
        with ThreadPoolExecutor(a.workers) as ex:
            futs = {ex.submit(fetch, r.cell_lat, r.cell_lon): r for r in todo.itertuples()}
            for i, f in enumerate(as_completed(futs), 1):
                r, p = futs[f], f.result()
                if p is None:
                    continue
                w.writerow(summarize(r.power_hucre, r.cell_lat, r.cell_lon, p))
                fh.flush()
                if i % 50 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
    c = pd.read_csv(cache).drop_duplicates("power_hucre")
    out = t1[["window_id", "power_hucre"]].merge(c, on="power_hucre", how="left")
    out.to_csv(a.out, index=False)
    print(f"wrote {a.out}: {len(out)} windows, missing climate: {int(out.sicaklik_yillik_ort_C.isna().sum())}")


if __name__ == "__main__":
    main()
