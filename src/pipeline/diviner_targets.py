#!/usr/bin/env python3
"""Diviner polar temperatures for the polar lunar targets (10 km window, same as T2).

Source: Diviner Polar Resource Product, south (PDS, LRO-L-DLRE-5-PRP-V2.0). The 605 MB table is
streamed, not saved; only triangles inside each target window are kept.
temp_avg is the annual mean at 2 cm depth; temp_max is the annual surface maximum. The product has
no annual minimum, so diviner_min_K stays empty.
Usage: python src/pipeline/diviner_targets.py [--t2 results/pipeline/T2_target_windows.csv] [--out results/pipeline/diviner_targets.csv]
"""
import argparse
import os
import ssl
import urllib.request

import certifi
import numpy as np
import pandas as pd
from pyproj import Transformer

URL = ("https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
       "data_derived_prp/dlre_prp_south.tab")
R_MOON_KM = 1737.4
HALF_M = 5000.0
PIPE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "results", "pipeline"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t2", default=os.path.join(PIPE, "T2_target_windows.csv"))
    ap.add_argument("--out", default=os.path.join(PIPE, "diviner_targets.csv"))
    a = ap.parse_args()
    t2 = pd.read_csv(a.t2)
    t2 = t2[t2.lat <= -75].reset_index(drop=True)
    tl = np.radians(t2.lat.values)[:, None]
    tn = np.radians(t2.lon.values)[:, None]
    keep = {tid: [] for tid in t2.target_id}
    ctx = ssl.create_default_context(cafile=certifi.where())
    resp = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "moon-analog-diviner"}),
                                  timeout=600, context=ctx)
    resp.readline()
    n = 0
    while True:
        lines = resp.readlines(8 << 20)
        if not lines:
            break
        arr = np.array([l.split(b",")[9:15] for l in lines], dtype=float)   # clon, clat, calt, avg, max, ice
        n += len(arr)
        la, lo = np.radians(arr[:, 1])[None, :], np.radians(arr[:, 0])[None, :]
        h = np.sin((la - tl) / 2) ** 2 + np.cos(tl) * np.cos(la) * np.sin((lo - tn) / 2) ** 2
        d_km = 2 * R_MOON_KM * np.arcsin(np.sqrt(np.minimum(h, 1)))
        for i, tid in enumerate(t2.target_id):
            m = d_km[i] < 7.5
            if m.any():
                keep[tid].append(arr[m])
    rows = []
    for i, t in t2.iterrows():
        x = np.vstack(keep[t.target_id]) if keep[t.target_id] else np.empty((0, 6))
        tr = Transformer.from_crs(f"+proj=longlat +R={R_MOON_KM * 1000} +no_defs",
                                  f"+proj=aeqd +lat_0={t.lat} +lon_0={t.lon} +R={R_MOON_KM * 1000} +units=m +no_defs",
                                  always_xy=True)
        if len(x):
            px, py = tr.transform(x[:, 0], x[:, 1])
            x = x[(np.abs(px) <= HALF_M) & (np.abs(py) <= HALF_M)]
        avg, mx, ice = x[:, 3], x[:, 4], x[:, 5]
        ok = ice > -998
        rows.append(dict(target_id=t.target_id, diviner_n=len(x),
                         diviner_ort_K=round(float(avg.mean()), 1) if len(x) else np.nan,
                         diviner_min_K=np.nan,
                         diviner_max_K=round(float(mx.mean()), 1) if len(x) else np.nan,
                         diviner_ort_K_en_soguk=round(float(avg.min()), 1) if len(x) else np.nan,
                         diviner_max_K_en_sicak=round(float(mx.max()), 1) if len(x) else np.nan,
                         diviner_buz_pay=round(float(ok.mean()), 3) if len(x) else np.nan,
                         diviner_buz_derinlik_med_m=round(float(np.median(ice[ok])), 3) if ok.any() else np.nan))
    out = pd.DataFrame(rows)
    out.to_csv(a.out, index=False)
    print(f"rows read: {n}")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
