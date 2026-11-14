#!/usr/bin/env python3
"""Earth windows and lunar targets: build T1/T2 (--stage tables), then score and evaluate (--stage full).

Stages:
  --stage tables   download Earth rasters, write T1 (Earth windows), T2 (lunar targets) and qc_report.txt
  --stage full     score, evaluate and list candidates from existing T1/T2 (no downloads)
  --synthetic      offline test with fake elevation
  --auto-rois      add half-degree cells that are basaltic (GLiM vb/pb) and dry (aridity < 0.5)

Local rasters are passed by environment variable: MOON_DEM (SLDEM2015 .LBL tiles, comma separated),
MOON_POLAR_DEM (LOLA south pole DEM), GLIM_PATH (GLiM geodatabase), ARIDITY_TIF (Global Aridity Index v3).
"""
import argparse
import hashlib
import json
import math
import os
import re
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

WIN_M = 10_000.0
RES = 120.0            # common grid (m/px), close to global LOLA at 118 m
R_MOON = 1737400.0
FEATS = ["slope_p50", "slope_p90", "TRI_p90"]
WEIGHTS = {"slope_p50": 0.25, "slope_p90": 0.35, "TRI_p90": 0.40}   # pipeline score; official AHP weights are in data/ahp_weights.csv
W_LITO = 0.40
TOP_K = 20
MIN_SEP_KM = 30.0      # minimum distance between listed candidates
BARE_MIN = 0.30        # bare or sparse share (WorldCover class 60)
AI_MAX = 0.20          # or dry: Global Aridity Index below this

# Apollo targets; Artemis III targets are appended from data/artemis_targets.csv
TARGETS = [
    dict(target_id="T_mare", terrain_class="mare", lito="bazaltik",
         lat=0.674, lon=23.473, note="Apollo 11, Mare Tranquillitatis"),
    dict(target_id="T_imbrium", terrain_class="mare", lito="bazaltik",
         lat=26.132, lon=3.634, note="Apollo 15, Hadley Rille / Imbrium kenari"),
    dict(target_id="T_highland", terrain_class="highland", lito="plutonik_bazik",
         lat=-8.973, lon=15.500, note="Apollo 16, Descartes yaylasi (anortozit)"),
    dict(target_id="T_nobile", terrain_class="polar", lito="plutonik_bazik",
         lat=-85.28, lon=53.46, note="Nobile krateri civari; Artemis 'Nobile Rim' koordinatina guncellenmeli"),
]

ROIS = [
    ("anatolia_kula",        38.30, 38.90,   28.20,   29.00),
    ("anatolia_karacadag",   37.40, 38.00,   39.40,   40.20),
    ("anatolia_kapadokya",   38.20, 38.80,   34.40,   35.20),
    ("arizona_sfvf",         34.95, 35.90, -111.90, -110.90),
    ("iceland_central",      64.60, 65.40,  -18.60,  -16.20),
    ("devon_haughton",       75.10, 75.60,  -90.80,  -88.60),
    ("labrador_mistastin",   55.60, 56.20,  -63.80,  -62.80),
    ("lanzarote",            28.85, 29.25,  -13.95,  -13.40),
    ("hawaii_maunakea",      19.55, 20.05, -155.75, -155.25),
    ("atacama",             -24.60, -23.40, -70.40,  -69.20),
    ("chad_tibesti",         20.50, 21.50,   17.00,   18.00),
    ("namib",               -24.50, -23.50,   15.00,   16.00),
    ("amazon_ctrl",          -3.50,  -2.50,  -60.50,  -59.50),
    ("bavaria_ctrl",         47.80,  48.40,   11.00,   12.00),
    ("taos_plateau",         36.20,  37.00, -106.10, -105.50),
    ("sudbury",              46.20,  47.00,  -81.90,  -80.50),
    ("stillwater",           45.15,  45.65, -110.30, -109.30),
    ("tenerife",             28.05,  28.45,  -16.85,  -16.35),
    ("hawaii_kau",           19.20,  19.50, -155.50, -155.10),
    ("lonar",                19.85,  20.10,   76.35,   76.65),
    ("ries",                 48.65,  49.10,   10.25,   10.85),
]

GLIM_MAP = {
    "vb": "bazaltik", "pb": "plutonik_bazik",
    "su": "sedimanter", "ss": "sedimanter", "sm": "sedimanter", "sc": "sedimanter", "ev": "sedimanter",
    "py": "piroklastik", "va": "volkanik_asidik", "vi": "volkanik_asidik",
    "pa": "kristalen", "pi": "kristalen", "mt": "kristalen", "ig": "buz", "wb": "su",
}
GLIM_FIELD = os.environ.get("GLIM_FIELD", "xx")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
NEG_CSV = os.environ.get("NEG_CSV", os.path.join(DATA, "hard_negatives.csv"))
ARTEMIS_CSV = os.environ.get("ARTEMIS_CSV", os.path.join(DATA, "artemis_targets.csv"))
GLIM_GRID = os.environ.get("GLIM_GRID", os.path.join(DATA, "raw", "glim_0p5", "glim_wgs84_0point5deg.txt.asc"))
AUTO_AI_MAX = 0.5          # --auto-rois: mean aridity of the cell
AUTO_CODES = ("vb", "pb")  # --auto-rois: GLiM classes kept
AUTO_MIN_SEP_KM = 5.0      # auto windows closer than this to an existing window are skipped
AUTO_MAX = 25_000          # stop before downloading if T1 would be larger


def _load_artemis(path):
    if not os.path.exists(path):
        return []
    d = pd.read_csv(path)
    return [dict(target_id=r.target_id, terrain_class=r.terrain_class, lito=r.lito, lat=float(r.lat),
                 lon=float(r.lon), note=r.note, region=r.region, area_km2=float(r.area_km2),
                 quickmap_slope_deg=float(r.quickmap_slope_deg)) for r in d.itertuples()]


def _load_negatives(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


TARGETS += _load_artemis(ARTEMIS_CSV)
NEGATIVES = _load_negatives(NEG_CSV)
N_BASE_ROIS = len(ROIS)
ROIS += [(f"neg_{r.site_id}", float(r.lat_min), float(r.lat_max), float(r.lon_min), float(r.lon_max))
         for r in NEGATIVES.itertuples()]
AUTO_STATS = {}

SRC = {
    "earth_dem": "/vsicurl/https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif",
    "worldcover": "/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
                  "ESA_WorldCover_10m_2021_v200_{t}_Map.tif",
    "moon_dem": os.environ.get("MOON_DEM", "/vsicurl/https://planetarymaps.usgs.gov/mosaic/"
                               "Lunar_LRO_LOLA_Global_LDEM_118m_Mar2014.tif"),
    "moon_polar_dem": os.environ.get("MOON_POLAR_DEM", ""),
    "aridity": os.environ.get("ARIDITY_TIF", ""),
    "glim": os.environ.get("GLIM_PATH", ""),
}
AI_SCALE = float(os.environ.get("AI_SCALE", "1e-4"))
os.environ.update(dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.TIF,.img,.IMG,.lbl,.LBL",
                       GDAL_HTTP_MAX_RETRY="4", GDAL_HTTP_RETRY_DELAY="2", VSI_CACHE="TRUE",
                       PROJ_IGNORE_CELESTIAL_BODY="YES"))
SYNTHETIC = False


def terrain_feats(z, res=RES):
    out = {f: np.nan for f in FEATS}
    out["relief"] = np.nan
    out["valid_frac"] = 0.0 if z is None else float(np.isfinite(z).mean())
    if z is None or out["valid_frac"] < 0.8:
        return out
    gy, gx = np.gradient(z, res)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    c = z[1:-1, 1:-1]
    h, w = z.shape
    tri = np.mean([np.abs(z[1 + dy:h - 1 + dy, 1 + dx:w - 1 + dx] - c)
                   for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)], axis=0)
    out.update(slope_p50=float(np.nanpercentile(slope, 50)), slope_p90=float(np.nanpercentile(slope, 90)),
               TRI_p90=float(np.nanpercentile(tri, 90)), relief=float(np.nanmax(z) - np.nanmin(z)))
    return out


def local_crs(lat, lon, body):
    if body == "earth":
        return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
    return f"+proj=aeqd +lat_0={lat} +lon_0={lon} +R={R_MOON} +units=m +no_defs"


def dn_to_m(ds, path):
    # SLDEM2015 labels are in kilometres and OFFSET is the reference radius, not a height offset
    mul, add = (ds.scales[0] or 1.0), (ds.offsets[0] or 0.0)
    if ds.driver == "PDS":
        lbl = path if path.lower().endswith(".lbl") else os.path.splitext(path)[0] + ".LBL"
        try:
            txt = open(lbl, errors="ignore").read()
        except OSError:
            txt = ""
        if re.search(r"UNIT\s*=\s*KILOMETER", txt, re.I):
            return mul * 1000.0, 0.0
    return mul, add


def warp_into(paths, lat, lon, body, res, resampling, categorical=False):
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import reproject
    n = int(round(WIN_M / res))
    tr = from_origin(-n * res / 2, n * res / 2, res, res)
    fill = 0 if categorical else np.nan
    dst = np.full((n, n), fill, dtype="uint8" if categorical else "float32")
    got = False
    for p in paths:
        try:
            with rasterio.open(p) as ds:
                tmp = np.full_like(dst, fill)
                reproject(source=rasterio.band(ds, 1), destination=tmp, src_nodata=ds.nodata,
                          dst_nodata=fill, dst_transform=tr, dst_crs=local_crs(lat, lon, body),
                          resampling=resampling)
                if not categorical:
                    mul, add = dn_to_m(ds, p)
                    tmp = tmp * mul + add
                m = (tmp > 0) if categorical else np.isfinite(tmp)
                dst[m] = tmp[m]
                got = got or bool(m.any())
        except Exception:
            continue
    return dst if got else None


def haversine_km(la1, lo1, la2, lo2, R=6371.0):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _seed(*a):
    return int(hashlib.md5(repr(a).encode()).hexdigest()[:8], 16)


def synth_dem(lat, lon, body):
    rng = np.random.default_rng(_seed(round(lat, 3), round(lon, 3), body))
    n = int(round(WIN_M / RES))
    beta, amp = rng.uniform(2.0, 3.2), rng.uniform(20, 600)
    k = np.hypot(np.fft.fftfreq(n)[:, None], np.fft.fftfreq(n)[None, :]); k[0, 0] = 1
    noise = np.fft.ifft2((rng.normal(size=(n, n)) + 1j * rng.normal(size=(n, n))) / k ** (beta / 2)).real
    return (noise / noise.std() * amp).astype("float32")


def make_windows():
    rows, step_lat = [], WIN_M / 1000 / 111.195
    for name, la0, la1, lo0, lo1 in ROIS:
        n0 = len(rows)
        lat = la0 + step_lat / 2
        while lat < la1:
            step_lon = step_lat / max(math.cos(math.radians(lat)), 0.05)
            lon = lo0 + step_lon / 2
            while lon < lo1:
                rows.append(dict(roi=name, lat=round(lat, 4), lon=round(lon, 4)))
                lon += step_lon
            lat += step_lat
        if name.startswith("neg_") and len(rows) == n0:
            # a negative box smaller than one window still gets one window at its centre
            rows.append(dict(roi=name, lat=round((la0 + la1) / 2, 4), lon=round((lo0 + lo1) / 2, 4)))
            AUTO_STATS.setdefault("neg_merkez", []).append(name)
    df = pd.DataFrame(rows)
    if df.roi.str.startswith("auto_").any():
        df = _filter_auto_windows(df)
    df.insert(0, "window_id", [f"E_{i:06d}" for i in range(len(df))])
    return df


def _filter_auto_windows(df):
    # drop auto windows whose centre is inside a named or negative box, or near an existing window
    auto = df.roi.str.startswith("auto_").to_numpy()
    base, cand = df[~auto], df[auto]
    la, lo = cand.lat.to_numpy(), cand.lon.to_numpy()
    in_box_ = np.zeros(len(cand), bool)
    for name, la0, la1, lo0, lo1 in ROIS:
        if not name.startswith("auto_"):
            in_box_ |= (la >= la0) & (la <= la1) & (lo >= lo0) & (lo <= lo1)
    near = np.zeros(len(cand), bool)
    bla, blo = np.radians(base.lat.to_numpy()), np.radians(base.lon.to_numpy())
    for i in range(0, len(cand), 2000):
        a, o = np.radians(la[i:i + 2000])[:, None], np.radians(lo[i:i + 2000])[:, None]
        h = np.sin((bla - a) / 2) ** 2 + np.cos(a) * np.cos(bla) * np.sin((blo - o) / 2) ** 2
        d = 2 * 6371.0 * np.arcsin(np.sqrt(np.minimum(h, 1.0)))
        near[i:i + 2000] = (d < AUTO_MIN_SEP_KM).any(axis=1)
    keep = ~(in_box_ | near)
    AUTO_STATS.update(auto_ham=int(len(cand)), atlanan_kutu_ici=int(in_box_.sum()),
                      atlanan_5km=int((near & ~in_box_).sum()), auto_kalan=int(keep.sum()))
    return pd.concat([base, cand[keep]], ignore_index=True)


def auto_rois(grid_path=GLIM_GRID, ai_max=AUTO_AI_MAX, codes=AUTO_CODES):
    import rasterio
    from rasterio.windows import from_bounds
    lines = open(grid_path).read().splitlines()
    hdr = {l.split()[0].lower(): float(l.split()[1]) for l in lines[:6]}
    g = np.array([l.split() for l in lines[6:]], dtype=float)
    cn = os.path.join(os.path.dirname(grid_path), "Classnames.txt")      # grid value -> GLiM code
    val = {ln.split(";")[3].strip().strip('"'): int(ln.split(";")[1]) for ln in open(cn).read().splitlines()[1:] if ln.strip()}
    cs, x0 = hdr["cellsize"], hdr["xllcorner"]
    ytop = hdr["yllcorner"] + hdr["nrows"] * cs
    want = {val[c]: c for c in codes}
    rr, cc = np.where(np.isin(g, list(want)))
    out, n_code = [], {c: 0 for c in codes}
    with rasterio.open(SRC["aridity"]) as ds:
        for r, c in zip(rr, cc):
            la1 = ytop - r * cs; la0 = la1 - cs; lo0 = x0 + c * cs; lo1 = lo0 + cs
            a = ds.read(1, window=from_bounds(lo0, la0, lo1, la1, ds.transform), boundless=True, fill_value=0).astype(float)
            a = a[a > 0]
            if a.size and a.mean() * AI_SCALE < ai_max:
                code = want[int(g[r, c])]
                n_code[code] += 1
                out.append((f"auto_{la0 + cs / 2:+06.2f}_{lo0 + cs / 2:+07.2f}", la0, la1, lo0, lo1))
    AUTO_STATS.update(grid_hucre=int(len(rr)), secilen_hucre=len(out), hucre_sinif=n_code)
    return out


def tiles(bbox, step, fmt):
    lo0, la0, lo1, la1 = bbox
    out = []
    for la in range(math.floor(la0 / step) * step, math.floor(la1 / step) * step + 1, step):
        for lo in range(math.floor(lo0 / step) * step, math.floor(lo1 / step) * step + 1, step):
            out.append(fmt(la, lo))
    return out


def cop_name(la, lo):
    n = f"Copernicus_DSM_COG_10_{'N' if la >= 0 else 'S'}{abs(la):02d}_00_{'E' if lo >= 0 else 'W'}{abs(lo):03d}_00_DEM"
    return SRC["earth_dem"].format(n=n)


def wc_name(la, lo):
    t = f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"
    return SRC["worldcover"].format(t=t)


def window_bbox(lat, lon):
    from pyproj import Transformer
    t = Transformer.from_crs(local_crs(lat, lon, "earth"), "EPSG:4326", always_xy=True)
    h = WIN_M / 2
    xs, ys = zip(*[t.transform(x, y) for x in (-h, 0, h) for y in (-h, 0, h)])
    return min(xs), min(ys), max(xs), max(ys)


def earth_window(row):
    lat, lon = row["lat"], row["lon"]
    rec = {"window_id": row["window_id"]}
    if SYNTHETIC:
        rec.update(terrain_feats(synth_dem(lat, lon, "earth")))
        rec["bare_frac"] = float(np.random.default_rng(_seed(lat, lon, "wc")).beta(0.6, 0.9))
        rec["snow_frac"] = 0.0
        return rec
    from rasterio.enums import Resampling
    bbox = window_bbox(lat, lon)
    rec.update(terrain_feats(warp_into(tiles(bbox, 1, cop_name), lat, lon, "earth", RES, Resampling.average)))
    wc = warp_into(tiles(bbox, 3, wc_name), lat, lon, "earth", 30.0, Resampling.nearest, categorical=True)
    if wc is not None and (wc > 0).any():
        v = wc[wc > 0]
        rec["bare_frac"], rec["snow_frac"] = float((v == 60).mean()), float((v == 70).mean())
    else:
        rec["bare_frac"] = rec["snow_frac"] = np.nan
    return rec


def add_aridity(df):
    if SYNTHETIC:
        df["aridity_index"] = np.round(np.random.default_rng(1).uniform(0.01, 1.2, len(df)), 3)
        return df
    if not (SRC["aridity"] and os.path.exists(SRC["aridity"])):
        print("  [uyari] ARIDITY_TIF yok -> aridity_index NaN")
        df["aridity_index"] = np.nan
        return df
    import rasterio
    with rasterio.open(SRC["aridity"]) as ds:
        vals = [v[0] for v in ds.sample(list(zip(df.lon, df.lat)))]
    df["aridity_index"] = [v * AI_SCALE if v and v > 0 else np.nan for v in vals]
    return df


def _window_squares(df):
    import shapely
    hlon = HALF_LAT / np.maximum(np.cos(np.radians(df.lat.to_numpy())), 0.05)
    la, lo = df.lat.to_numpy(), df.lon.to_numpy()
    return shapely.box(lo - hlon, la - HALF_LAT, lo + hlon, la + HALF_LAT)


def _read_glim(df, step=5.0):
    import geopandas as gpd
    from shapely.geometry import box
    hlon = HALF_LAT / np.maximum(np.cos(np.radians(df.lat.to_numpy())), 0.05)
    key = list(zip(np.floor(df.lat.to_numpy() / step), np.floor(df.lon.to_numpy() / step)))
    ext = pd.DataFrame(dict(k=key, x0=df.lon.to_numpy() - hlon, x1=df.lon.to_numpy() + hlon,
                            y0=df.lat.to_numpy() - HALF_LAT, y1=df.lat.to_numpy() + HALF_LAT))
    parts = []
    for _, e in ext.groupby("k").agg(x0=("x0", "min"), y0=("y0", "min"), x1=("x1", "max"), y1=("y1", "max")).iterrows():
        bb = gpd.GeoSeries([box(e.x0, e.y0, e.x1, e.y1)], crs="EPSG:4326")   # a plain tuple bbox would be read in Eckert IV
        g = gpd.read_file(SRC["glim"], bbox=bb, columns=[GLIM_FIELD], fid_as_index=True)
        if len(g):
            parts.append(g)
    if not parts:
        return None
    glim = pd.concat(parts)
    return gpd.GeoDataFrame(glim[~glim.index.duplicated()], crs=parts[0].crs)


def add_lito(df):
    # lito_merkez: class at the window centre; lito and the shares: area of the 10 km square, in Eckert IV (equal area)
    lito_cols = ["lito", "lito_merkez", "bazalt_frac", "bazik_plutonik_frac", "glim_kapsama"]
    if SYNTHETIC:
        df["lito"] = np.random.default_rng(2).choice(
            ["bazaltik", "sedimanter", "kristalen", "plutonik_bazik", "volkanik_asidik"], len(df), p=[.3, .35, .15, .1, .1])
        df["lito_merkez"] = df["lito"]
        df["bazalt_frac"] = (df.lito == "bazaltik").astype(float)
        df["bazik_plutonik_frac"] = (df.lito == "plutonik_bazik").astype(float)
        df["glim_kapsama"] = 1.0
        return df
    if not (SRC["glim"] and os.path.exists(SRC["glim"])):
        print("  [uyari] GLIM_PATH yok -> lito 'bilinmiyor'")
        for c in lito_cols:
            df[c] = "bilinmiyor" if c.startswith("lito") else np.nan
        return df
    import geopandas as gpd
    import shapely
    glim = _read_glim(df)
    if glim is None:
        for c in lito_cols:
            df[c] = "bilinmiyor" if c.startswith("lito") else 0.0
        return df
    code_all = glim[GLIM_FIELD].astype(str).str[:2].str.lower()

    pts = gpd.GeoDataFrame(df[["window_id"]].copy(), geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    g4326 = gpd.GeoDataFrame({GLIM_FIELD: glim[GLIM_FIELD].to_numpy()}, geometry=glim.geometry.to_crs("EPSG:4326").to_numpy(),
                             crs="EPSG:4326")
    j = gpd.sjoin(pts, g4326, how="left", predicate="within").drop_duplicates("window_id")
    code = j.set_index("window_id")[GLIM_FIELD].astype(str).str[:2].str.lower()
    df["lito_merkez"] = df.window_id.map(code).map(GLIM_MAP).fillna("bilinmiyor")

    # edges are densified so the square keeps its shape after projection
    sq = shapely.segmentize(_window_squares(df), 0.005)
    win = gpd.GeoDataFrame({"wi": np.arange(len(df))}, geometry=gpd.GeoSeries(sq, crs="EPSG:4326").to_crs(glim.crs).to_numpy(),
                           crs=glim.crs)
    gg = glim.geometry.to_numpy()
    bad = ~shapely.is_valid(gg)
    if bad.any():
        gg[bad] = shapely.make_valid(gg[bad])
    gdf = gpd.GeoDataFrame({"code": code_all.to_numpy()}, geometry=gg, crs=glim.crs)
    pairs = gpd.sjoin(win, gdf, how="inner", predicate="intersects")
    li, ri = pairs.wi.to_numpy(), pairs.index_right.to_numpy()
    inter = shapely.area(shapely.intersection(win.geometry.to_numpy()[li], gg[ri]))
    share = pd.DataFrame(dict(wi=li, code=gdf.code.to_numpy()[ri],
                              pay=inter / shapely.area(win.geometry.to_numpy())[li]))
    by_code = share.groupby(["wi", "code"]).pay.sum().unstack(fill_value=0.0)
    n = len(df)
    kaps = by_code.sum(axis=1).reindex(range(n), fill_value=0.0).clip(upper=1.0)
    df["bazalt_frac"] = by_code.get("vb", pd.Series(dtype=float)).reindex(range(n), fill_value=0.0).round(4).to_numpy()
    df["bazik_plutonik_frac"] = by_code.get("pb", pd.Series(dtype=float)).reindex(range(n), fill_value=0.0).round(4).to_numpy()
    df["glim_kapsama"] = kaps.round(4).to_numpy()
    cls = share.assign(cls=share.code.map(GLIM_MAP)).dropna(subset=["cls"]).groupby(["wi", "cls"]).pay.sum()
    best = cls.reset_index().sort_values("pay", ascending=False).drop_duplicates("wi").set_index("wi").cls
    df["lito"] = best.reindex(range(n)).fillna("bilinmiyor").to_numpy()
    return df


def build_t1(workers, win=None):
    win = make_windows() if win is None else win
    print(f"[A] {len(win)} Dunya penceresi, {len(ROIS)} bolge")
    rows = win.to_dict("records")
    if workers > 1:
        with ProcessPoolExecutor(workers) as ex:
            feats = list(ex.map(earth_window, rows, chunksize=8))
    else:
        feats = [earth_window(r) for r in rows]
    t1 = add_lito(add_aridity(win.merge(pd.DataFrame(feats), on="window_id")))
    t1["aday_maskesi"] = ((t1.bare_frac.fillna(0) >= BARE_MIN) | (t1.aridity_index.fillna(9) < AI_MAX)
                          | t1.bare_frac.isna()).astype(int)
    return t1


def build_t2():
    rows = []
    for t in TARGETS:
        polar = abs(t["lat"]) >= 60
        if SYNTHETIC:
            z, src = synth_dem(t["lat"], t["lon"], "moon"), "synthetic"
        else:
            from rasterio.enums import Resampling
            if polar and SRC["moon_polar_dem"]:
                srcs = [SRC["moon_polar_dem"]]
            else:
                srcs = [x.strip() for x in SRC["moon_dem"].split(",") if x.strip()]
                if polar:
                    print(f"  [uyari] {t['target_id']}: MOON_POLAR_DEM yok, global DEM kullaniliyor (kutupta guvenilmez)")
            z = warp_into(srcs, t["lat"], t["lon"], "moon", RES, Resampling.bilinear)
            src = ";".join(os.path.basename(x) for x in srcs)
        rows.append({**t, "dem_source": os.path.basename(src), **terrain_feats(z)})
    return pd.DataFrame(rows)


HALF_LAT = WIN_M / 2 / 1000 / 111.195      # half window in degrees of latitude


def in_box(lat, lon, b):
    # the whole 10 km square, not just its centre, must touch the site box (small craters)
    hlat = HALF_LAT
    hlon = HALF_LAT / max(math.cos(math.radians(lat)), 0.05)
    return not (lat + hlat < b.lat_min or lat - hlat > b.lat_max or
                lon + hlon < b.lon_min or lon - hlon > b.lon_max)


def in_box_mask(lat, lon, b):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    hlon = HALF_LAT / np.maximum(np.cos(np.radians(lat)), 0.05)
    return ~((lat + HALF_LAT < b.lat_min) | (lat - HALF_LAT > b.lat_max) |
             (lon + hlon < b.lon_min) | (lon - hlon > b.lon_max))


def qc_report(t1, t2, t3, path):
    L = []
    p = L.append
    p("=== QC RAPORU: T4'ten once kontrol et ===\n")
    p("[T1] Bolge bazinda ozet (medyan degerler)")
    n_auto = t1.roi.str.startswith("auto_")
    grp = t1.roi.where(~n_auto, f"auto_* ({t1.roi[n_auto].nunique()} hucre)")
    agg = t1.groupby(grp).agg(n=("window_id", "size"), valid=("valid_frac", "mean"),
                                slope_p90=("slope_p90", "median"), TRI_p90=("TRI_p90", "median"),
                                bare=("bare_frac", "median"), maske=("aday_maskesi", "mean"))
    p(agg.round(2).to_string())
    p("\n[T1] Eksik veri oranlari")
    p(t1[FEATS + ["bare_frac", "aridity_index"]].isna().mean().round(3).to_string())
    p("\n[T1] Litoloji dagilimi (alan bazli 'lito'; merkez etiketi 'lito_merkez')")
    p(pd.DataFrame({"lito (alan)": t1.lito.value_counts(), "lito_merkez": t1.lito_merkez.value_counts()}
                   ).fillna(0).astype(int).to_string() if "lito_merkez" in t1 else t1.lito.value_counts().to_string())
    if "lito_merkez" in t1:
        p(f"  alan bazli etiket merkezden farkli: {(t1.lito != t1.lito_merkez).sum()} / {len(t1)} pencere")
    neg = t1.roi.str.startswith("neg_")
    if neg.any():
        p("\n[T1] Negatif bolgeler: pencere sayisi")
        cnt = t1[neg].roi.value_counts()
        for name, *_ in ROIS:
            if name.startswith("neg_"):
                tag = "  (kutu pencereden kucuk -> merkez penceresi)" if name in AUTO_STATS.get("neg_merkez", []) else ""
                warn = "  !!! 0 pencere" if cnt.get(name, 0) == 0 else ""
                p(f"  {name:<9} {cnt.get(name, 0):>3}{tag}{warn}")
    if (t1.lito == "bilinmiyor").mean() > 0.5:
        p("  !!! Litolojinin yarisindan fazlasi 'bilinmiyor': GLIM_PATH veya GLIM_FIELD yanlis olabilir.")
    p("\n[T2] Ay hedefleri")
    p(t2[["target_id", "dem_source", "valid_frac"] + FEATS + ["relief"]].round(2).to_string(index=False))
    for _, r in t2.iterrows():
        if not (r.relief == r.relief) or r.relief < 30 or r.relief > 15000:
            p(f"  !!! {r.target_id}: relief={r.relief} beklenmedik. DEM olcek carpanini / dosya yolunu kontrol et.")
    if "quickmap_slope_deg" in t2:
        a = t2[t2.quickmap_slope_deg.notna()]
        if len(a):
            p("\n[T2] Artemis III: LDEM egimi ile QuickMap egimi (birebir ayni beklenmez, buyukluk mertebesi tutmali)")
            q = a[["target_id", "region", "dem_source", "slope_p50", "slope_p90", "quickmap_slope_deg"]].copy()
            q["p50/qm"] = (q.slope_p50 / q.quickmap_slope_deg).round(2)
            q["p90/qm"] = (q.slope_p90 / q.quickmap_slope_deg).round(2)
            p(q.round(2).to_string(index=False))
            for _, r in a.iterrows():
                if "LDEM" not in str(r.dem_source):
                    p(f"  !!! {r.target_id}: dem_source={r.dem_source} (LDEM bekleniyordu)")
    p("\n[T3] Bilinen sahalar -> pencere ve maske durumu")
    for _, b in t3.iterrows():
        ids = t1[in_box_mask(t1.lat, t1.lon, b)]
        msg = f"  {b.site_name:<30} pencere={len(ids):>3}  maskeden gecen={int(ids.aday_maskesi.sum()):>3}"
        if len(ids) == 0:
            msg += "  !!! kutu hicbir ROI'ye dusmuyor -> ROIS'e ekle"
        elif ids.aday_maskesi.sum() == 0:
            msg += "  -> ISTISNA (maskeye takiliyor, T5_exceptions'ta raporlanacak)"
        p(msg)
    p("\n[T1 x T2] Hedef degerleri Dunya dagiliminin hangi yuzdeliginde?")
    cand = t1[t1.aday_maskesi == 1]
    for _, r in t2.iterrows():
        pcts = {f: round(float((cand[f] < r[f]).mean() * 100), 1) for f in FEATS}
        warn = "  !!! hedef Dunya dagiliminin disinda, bu hedef icin analog bulmak zor" if any(v > 99 for v in pcts.values()) else ""
        p(f"  {r.target_id:<11} {pcts}{warn}")
    open(path, "w").write("\n".join(L))
    print("\n".join(L))


def norm_iqr(t1):
    cand = t1[t1.aday_maskesi == 1]
    return {f: float(np.subtract(*np.nanpercentile(cand[f], [75, 25])) or 1.0) for f in FEATS}


def score(t1, t2, iqr, weights=WEIGHTS, w_lito=W_LITO):
    E0 = t1.dropna(subset=FEATS)
    out = []
    for _, t in t2.iterrows():
        E = E0[["window_id", "roi", "lat", "lon", "lito", "aday_maskesi"] + FEATS].copy()
        lito_on = t.lito != "bilinmiyor"     # unknown target rock turns the rock term off
        dist = np.zeros(len(E))
        for f in FEATS:
            E[f"d_{f}"] = (E[f] - t[f]).abs()
            dist += weights[f] * E[f"d_{f}"].to_numpy() / iqr[f]
        E["lito_match"] = ((E.lito == t.lito) & lito_on).astype(int)
        E["mesafe"] = dist
        E["sim"] = w_lito * E.lito_match + (1 - w_lito) * np.exp(-E.mesafe)
        E = E.sort_values("sim", ascending=False)
        E["rank_all"] = np.arange(1, len(E) + 1)
        m = E.aday_maskesi == 1
        E["rank"] = np.nan
        E.loc[m, "rank"] = np.arange(1, int(m.sum()) + 1)
        # material track: windows that fail the mask but share the target rock
        mm = (E.aday_maskesi == 0) & (E.lito == t.lito) & lito_on
        E["material_track"] = np.nan
        E.loc[mm, "material_track"] = np.arange(1, int(mm.sum()) + 1)
        E["negatif_bolge"] = E.roi.str.startswith("neg_").astype(int)
        E["negatif_id"] = np.where(E.negatif_bolge == 1, E.roi.str[4:], "")
        E.insert(0, "target_id", t.target_id)
        out.append(E)
    return pd.concat(out, ignore_index=True)


# rank column per evaluation track; the process track is reported but not counted in recall
TRACK_RANK_COL = {"yuzey": "rank", "malzeme": "material_track", "surec": "rank"}


def _track(b):
    return b["eval_track"] if "eval_track" in b.index and b["eval_track"] == b["eval_track"] else "yuzey"


def site_windows(t1, b):
    return t1[in_box_mask(t1.lat, t1.lon, b)].window_id


def evaluate(t1, t4, t3, k=TOP_K):
    rows, exc, proc = [], [], []
    for _, b in t3.iterrows():
        track = _track(b)
        col = TRACK_RANK_COL[track]
        ids = site_windows(t1, b)
        sub = t4[(t4.target_id == b.analog_to) & t4.window_id.isin(ids)]
        best = sub[col].min() if len(sub) else np.nan
        scored = best == best
        all_best = int(sub.rank_all.min()) if len(sub) else np.nan
        row = dict(site_id=b.site_id, site_name=b.site_name, analog_to=b.analog_to,
                   eval_track=track, rank_col=col, n_windows=len(ids), best_rank=best)
        if track == "surec":
            row.update(recall_at_k=np.nan, reciprocal_rank=np.nan, status="surec izi (recall disi)")
            proc.append(dict(site_id=b.site_id, site_name=b.site_name, analog_to=b.analog_to,
                             n_windows=len(ids), best_rank=best, best_rank_all=all_best, note=b.note))
        else:
            row.update(recall_at_k=int(best <= k) if scored else 0,
                       reciprocal_rank=(1 / best) if scored else 0.0)
            if len(ids) == 0:
                row["status"] = "kutu ROI disinda"
            elif not scored:
                row["status"] = "istisna"
                if track == "yuzey":   # failing the mask is only an exception on the surface track
                    exc.append(dict(site_id=b.site_id, site_name=b.site_name, analog_to=b.analog_to,
                                    best_rank_if_unmasked=all_best,
                                    neden="aday maskesine takildi (bitki ortusu / yagis)", note=b.note))
            else:
                row["status"] = "degerlendirildi"
        rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(exc), pd.DataFrame(proc)


RAND_TRIALS = 20_000
RAND_SEED = 20260101


def random_baseline(t1, t4, t3, k=TOP_K, trials=RAND_TRIALS, seed=RAND_SEED):
    # chance level: best rank of a site's windows under random orderings of its pool
    rng = np.random.default_rng(seed)
    rows = []
    for _, b in t3.iterrows():
        track = _track(b)
        col = TRACK_RANK_COL[track]
        g = t4[t4.target_id == b.analog_to]
        pool = int(g[col].notna().sum())
        own = g[g.window_id.isin(set(site_windows(t1, b)))]
        n_s = int(own[col].notna().sum())
        obs = own[col].min() if n_s else np.nan
        rec = dict(site_id=b.site_id, site_name=b.site_name, eval_track=track,
                   pool=pool, n_in_pool=n_s, best_rank=obs)
        if n_s == 0 or pool == 0:
            rec.update(rand_p_topk=np.nan, rand_median_rank=np.nan, rand_mrr=np.nan, p_value=np.nan)
        else:
            mins = np.fromiter((rng.choice(pool, size=n_s, replace=False).min() + 1
                                for _ in range(trials)), dtype=np.int64, count=trials)
            rec.update(rand_p_topk=float((mins <= k).mean()),
                       rand_median_rank=float(np.median(mins)),
                       rand_mrr=float((1.0 / mins).mean()),
                       p_value=float((mins <= obs).mean()) if obs == obs else np.nan)
        rows.append(rec)
    return pd.DataFrame(rows)


def track_summary(t5, base, k=TOP_K):
    rows = []
    for track in ["yuzey", "malzeme", "surec"]:
        g, bg = t5[t5.eval_track == track], base[base.eval_track == track]
        if not len(g):
            continue
        rows.append(dict(eval_track=track, n_sites=len(g),
                         recall_at_k=g.recall_at_k.mean(), rand_recall_at_k=bg.rand_p_topk.mean(),
                         mrr=g.reciprocal_rank.mean(), rand_mrr=bg.rand_mrr.mean(),
                         medyan_best_rank=g.best_rank.median(),
                         rand_medyan_rank=bg.rand_median_rank.median(),
                         havuz_medyan=bg.pool.median()))
    return pd.DataFrame(rows)


# areas the challenge calls well studied: (lat_min, lat_max, lon_min, lon_max)
COK_CALISILMIS = {"Antarktika": (-90.0, -60.0, -180.0, 180.0), "Atacama": (-27.0, -18.0, -71.0, -68.0),
                  "Izlanda": (63.0, 67.0, -25.0, -13.0), "Hawaii": (18.5, 22.5, -160.5, -154.5)}
# coarse labels for auto cells, first match wins (reporting only)
KABA_BOLGE = [("Kuzey Afrika / Sahra", 12, 37.5, -20, 35), ("Arabistan / Orta Dogu", 12, 42, 35, 63),
              ("Dogu Afrika / Etiyopya", -12, 15, 30, 52), ("Bati-Orta Afrika", -12, 12, -20, 30),
              ("Guney Afrika", -35, -12, 10, 41), ("Hindistan (Deccan)", 5, 36, 63, 92),
              ("Sibirya / Kuzey Asya", 50, 80, 60, 180), ("Orta-Dogu Asya", 20, 56, 63, 135),
              ("Avustralya", -45, -10, 110, 155), ("Kanada / Alaska", 49, 75, -170, -50),
              ("ABD / Meksika", 14, 49, -125, -85), ("Patagonya", -56, -38, -76, -60),
              ("Guney Amerika", -38, 13, -82, -34), ("Avrupa / Anadolu", 35, 72, -25, 45)]


def cok_calisilmis(lat, lon):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    m = np.zeros(len(lat), bool)
    for la0, la1, lo0, lo1 in COK_CALISILMIS.values():
        m |= (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
    return m.astype(int)


def bilinen_sahaya_km(lat, lon, t3):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    best = np.full(len(lat), np.inf)
    for _, b in t3.iterrows():
        cl, co = np.clip(lat, b.lat_min, b.lat_max), np.clip(lon, b.lon_min, b.lon_max)
        p1, p2 = np.radians(lat), np.radians(cl)
        h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(co - lon) / 2) ** 2
        best = np.minimum(best, 2 * 6371.0 * np.arcsin(np.sqrt(np.minimum(h, 1.0))))
    return best.round(1)


def bolge_grubu(roi, lat, lon):
    if not str(roi).startswith("auto_"):
        return roi
    for name, la0, la1, lo0, lo1 in KABA_BOLGE:
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return f"auto: {name}"
    return "auto: diger"


def new_candidates(t4, t3, k=TOP_K, min_sep=MIN_SEP_KM, az_bilinen=False):
    # negative windows stay ranked in T4 but are left out of candidate lists
    pool = t4[t4["rank"].notna() & (t4.get("negatif_bolge", 0) == 0)]
    if az_bilinen:
        pool = pool[cok_calisilmis(pool.lat, pool.lon) == 0]
    out = []
    for tid, g in pool.sort_values("rank").groupby("target_id", sort=False):
        kept = []
        for _, r in g.iterrows():
            if all(haversine_km(r.lat, r.lon, q.lat, q.lon) >= min_sep for q in kept):
                kept.append(r)
            if len(kept) >= k:
                break
        for r in kept:
            own = t3[t3.analog_to == tid]
            if any(in_box(r.lat, r.lon, b) for _, b in own.iterrows()):
                s = "bilinen analog (bu hedef)"
            elif any(in_box(r.lat, r.lon, b) for _, b in t3.iterrows()):
                s = "baska hedefin bilinen analogu"
            else:
                s = "YENI ADAY"
            out.append({**r.to_dict(), "durum": s})
    nc = pd.DataFrame(out)
    if len(nc):
        nc["cok_calisilmis"] = cok_calisilmis(nc.lat, nc.lon)
        nc["bilinen_sahaya_km"] = bilinen_sahaya_km(nc.lat, nc.lon, t3)
        nc["bolge_grubu"] = [bolge_grubu(r, a, o) for r, a, o in zip(nc.roi, nc.lat, nc.lon)]
    return nc


def negatives_report(t4, k=TOP_K):
    rows = []
    if not len(NEGATIVES):
        return pd.DataFrame()
    for _, n in NEGATIVES.iterrows():
        g = t4[(t4.target_id == n.negative_for) & (t4.negatif_id == n.site_id)]
        rows.append(dict(hedef=n.negative_for, negatif=n.site_id, ad=n.site_name, pencere=len(g),
                         maskeden_gecen=int(g["rank"].notna().sum()),
                         ilk20=int((g["rank"] <= k).sum()), ilk100=int((g["rank"] <= 100).sum()),
                         en_iyi_rank=g["rank"].min(),
                         ilk20_all=int((g.rank_all <= k).sum()), ilk100_all=int((g.rank_all <= 100).sum()),
                         en_iyi_rank_all=g.rank_all.min(),
                         havuz=int(t4[(t4.target_id == n.negative_for)]["rank"].notna().sum())))
    return pd.DataFrame(rows)


def sensitivity(t1, t2, t3, iqr, base_t4, k=TOP_K):
    base_top = {t: set(g[g["rank"] <= k].window_id) for t, g in base_t4.groupby("target_id")}
    variants = [("base", WEIGHTS, W_LITO)]
    for f in FEATS:
        for m in (0.5, 1.5):
            w = dict(WEIGHTS); w[f] *= m; s = sum(w.values())
            variants.append((f"{f}x{m}", {a: v / s for a, v in w.items()}, W_LITO))
    variants += [(f"w_litox{m}", WEIGHTS, min(W_LITO * m, 0.9)) for m in (0.5, 1.5)]
    rows = []
    for name, w, wl in variants:
        t4 = score(t1, t2, iqr, w, wl)
        ev, _, _ = evaluate(t1, t4, t3, k)
        ov = np.mean([len(base_top[t] & set(g[g["rank"] <= k].window_id)) / k for t, g in t4.groupby("target_id")])
        rows.append(dict(variant=name, recall_at_k=ev.recall_at_k.mean(), mrr=ev.reciprocal_rank.mean(),
                         topk_overlap_with_base=round(ov, 3)))
    return pd.DataFrame(rows)


def main():
    global SYNTHETIC
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["tables", "full"], default="tables")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--rois", default="", help="comma-separated region names (smoke test)")
    ap.add_argument("--t3", default=os.path.join(DATA, "known_analogs_moon.csv"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "pipeline"))
    ap.add_argument("--auto-rois", action="store_true",
                    help="add half-degree GLiM vb/pb cells with aridity below 0.5 as regions")
    a = ap.parse_args()
    SYNTHETIC = a.synthetic
    if a.rois:
        keep = set(a.rois.split(","))
        ROIS[:] = [r for r in ROIS if r[0] in keep]
    os.makedirs(a.out, exist_ok=True)
    P = lambda n: os.path.join(a.out, n)
    t3 = pd.read_csv(a.t3)

    if a.stage == "tables" or not os.path.exists(P("T1_earth_windows.csv")):
        if a.auto_rois:
            ROIS.extend(auto_rois())
        win = make_windows()
        n_auto = int(win.roi.str.startswith("auto_").sum())
        print(f"[A] ROI: {N_BASE_ROIS} mevcut + {len(NEGATIVES)} negatif + "
              f"{AUTO_STATS.get('secilen_hucre', 0)} auto hucre; pencere: "
              f"{int((~win.roi.str.startswith(('neg_', 'auto_'))).sum())} mevcut + "
              f"{int(win.roi.str.startswith('neg_').sum())} negatif + {n_auto} auto = {len(win)}")
        if a.auto_rois:
            print(f"    auto: grid vb/pb hucre={AUTO_STATS['grid_hucre']}, secilen={AUTO_STATS['secilen_hucre']} "
                  f"{AUTO_STATS['hucre_sinif']}, ham pencere={AUTO_STATS.get('auto_ham', 0)}, "
                  f"atlanan (kutu ici)={AUTO_STATS.get('atlanan_kutu_ici', 0)}, "
                  f"atlanan (<{AUTO_MIN_SEP_KM:g} km)={AUTO_STATS.get('atlanan_5km', 0)}, kalan={n_auto}")
        if AUTO_STATS.get("neg_merkez"):
            print(f"    kutu merkezinde tek pencere alan negatifler: {AUTO_STATS['neg_merkez']}")
        json.dump(AUTO_STATS, open(P("auto_rois_stats.json"), "w"), indent=2)
        if len(win) > AUTO_MAX:
            print(f"\n!!! toplam {len(win)} pencere > {AUTO_MAX}: yerel calistirma durduruldu.")
            raise SystemExit(2)
        t1, t2 = build_t1(a.workers, win), build_t2()
        t1.to_csv(P("T1_earth_windows.csv"), index=False)
        t2.to_csv(P("T2_target_windows.csv"), index=False)
        t3.to_csv(P("T3_known_analogs.csv"), index=False)
        qc_report(t1, t2, t3, P("qc_report.txt"))
        if a.stage == "tables":
            print(f"\nTablolar hazir: {os.path.abspath(a.out)}. qc_report.txt'yi kontrol et, sonra --stage full calistir.")
            return
    t1, t2 = pd.read_csv(P("T1_earth_windows.csv")), pd.read_csv(P("T2_target_windows.csv"))

    iqr = norm_iqr(t1)
    json.dump(dict(iqr=iqr, weights=WEIGHTS, w_lito=W_LITO), open(P("normalization.json"), "w"), indent=2)
    t4 = score(t1, t2, iqr)
    t5, exc, proc = evaluate(t1, t4, t3)
    base = random_baseline(t1, t4, t3)
    tsum = track_summary(t5, base)
    nc = new_candidates(t4, t3)
    nc_az = new_candidates(t4, t3, az_bilinen=True)
    negr = negatives_report(t4)
    sens = sensitivity(t1, t2, t3, iqr, t4)
    tables = {"T1_earth_windows": t1, "T2_target_windows": t2, "T3_known_analogs": t3, "T4_scores": t4,
              "T5_evaluation": t5, "T5_exceptions": exc, "T5_process_track": proc,
              "T5_random_baseline": base, "T5_track_summary": tsum,
              "T5_negatives": negr, "new_candidates": nc, "new_candidates_az_bilinen": nc_az,
              "sensitivity": sens}
    for n, df in tables.items():
        df.to_csv(P(f"{n}.csv"), index=False)
    with pd.ExcelWriter(P("analog_tables.xlsx")) as xw:
        for n, df in tables.items():
            (df[df["rank"] <= 200] if n == "T4_scores" else df).to_excel(xw, sheet_name=n[:31], index=False)
    print(f"\n[D] iz bazinda recall@{TOP_K} ve MRR, rastgele tabanla karsilastirma "
          f"({RAND_TRIALS} deneme, seed={RAND_SEED}):")
    print(tsum.round(3).to_string(index=False))
    print(f"\n[D] recall@{TOP_K} = {t5.recall_at_k.mean():.2f}  MRR = {t5.reciprocal_rank.mean():.3f}  "
          "(surec izi disinda)")
    print(t5[["site_name", "analog_to", "eval_track", "n_windows", "best_rank", "status"]].to_string(index=False))
    if len(proc):
        print("\n[D] Surec izi (recall disi, en iyi siralar):")
        print(proc[["site_name", "analog_to", "n_windows", "best_rank", "best_rank_all"]].to_string(index=False))
    if len(exc):
        print("\n[D] Istisnalar (maskeye takilan bilinen sahalar):")
        print(exc[["site_name", "analog_to", "best_rank_if_unmasked"]].to_string(index=False))
    if len(negr):
        print(f"\n[D] Zor negatifler: kendi hedefinde ilk {TOP_K} / ilk 100 (rank = maskeden gecen havuz)")
        print(negr[["hedef", "negatif", "ad", "pencere", "maskeden_gecen", "ilk20", "ilk100", "en_iyi_rank",
                    "ilk20_all", "ilk100_all", "en_iyi_rank_all"]].to_string(index=False))
    print(f"\n[D] Yeni aday sayisi: {(nc.durum == 'YENI ADAY').sum()} (az bilinen listede "
          f"{(nc_az.durum == 'YENI ADAY').sum() if len(nc_az) else 0})  ->  {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()
