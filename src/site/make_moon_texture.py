#!/usr/bin/env python3
"""Moon globe texture with shaded relief: docs/assets/moon_relief.jpg.

Colour: the NASA SVS CGI Moon Kit texture (docs/assets/moon_2k.jpg).
Relief: the CGI Moon Kit elevation map (ldem_4.tif, 4 px per degree) everywhere, and the LOLA south pole
elevation model (LDEM_80S_80MPP_ADJ, 80 m) south of 79 S, so the Artemis III craters show.

Usage: CGI_LDEM=data/raw/ldem_4.tif MOON_POLAR_DEM=data/raw/LDEM_80S_80MPP_ADJ.TIF python src/site/make_moon_texture.py
"""
import os

import numpy as np
import rasterio
from PIL import Image
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
W, H = 4096, 2048
R = 1737.4  # km
SUN_AZ, SUN_ALT, EXAG = 300.0, 30.0, 3.0


def hillshade(z, dx, dy, az_deg):
    """Lambert shade of a grid (rows go north to south), 1 on flat ground."""
    gz_e = (np.roll(z, -1, 1) - np.roll(z, 1, 1)) / (2 * dx) * EXAG
    gz_n = (np.vstack([z[:1], z[:-1]]) - np.vstack([z[1:], z[-1:]])) / (2 * dy) * EXAG
    az, alt = np.radians(az_deg), np.radians(SUN_ALT)
    sx, sy, sz = np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)
    s = (-gz_e * sx - gz_n * sy + sz) / np.sqrt(gz_e ** 2 + gz_n ** 2 + 1)
    return np.clip(s / sz, 0, 2)


def main():
    ldem = os.environ.get("CGI_LDEM", os.path.join(ROOT, "data", "raw", "ldem_4.tif"))
    polar = os.environ.get("MOON_POLAR_DEM", os.path.join(ROOT, "data", "raw", "LDEM_80S_80MPP_ADJ.TIF"))
    out = os.path.join(ROOT, "docs", "assets", "moon_relief.jpg")

    with rasterio.open(ldem) as r:  # equirectangular, columns from 180 W, rows from 90 N, km
        z = r.read(1, out_shape=(H, W), resampling=Resampling.cubic).astype(np.float64)

    # global shade; near the poles the east step is held at its 70 degree value to avoid streaks
    lat = np.radians(90 - (np.arange(H) + 0.5) * 180 / H)[:, None]
    shade = hillshade(z, np.maximum(np.cos(lat), np.cos(np.radians(70))) * 2 * np.pi * R / W, np.pi * R / H, SUN_AZ)

    # south pole: shade the LOLA model in its own polar stereographic grid, then warp the shade onto the globe grid
    lat0 = -79.0
    row0 = int((90 - lat0) / 180 * H)
    with rasterio.open(polar) as p:
        n = 1520  # 400 m cells
        pz = p.read(1, out_shape=(n, n), resampling=Resampling.average).astype(np.float64) / 1000.0
        pz = np.where(np.isfinite(pz), pz, np.nanmedian(pz))
        cell = (p.bounds.right - p.bounds.left) / n / 1000.0
        # one fixed light direction in the polar grid (the light direction on the globe turns with longitude here)
        pshade = hillshade(pz, cell, cell, SUN_AZ).astype(np.float32)
        dst = np.full((H - row0, W), np.nan, np.float32)
        gcrs = CRS.from_wkt('GEOGCS["Moon 2015",DATUM["Moon",SPHEROID["Moon",1737400,0]],PRIMEM["Reference Meridian",0],UNIT["degree",0.0174532925199433]]')
        src_t = rasterio.transform.from_bounds(*p.bounds, n, n)
        reproject(pshade, dst, src_transform=src_t, src_crs=p.crs, dst_crs=gcrs,
                  dst_transform=from_origin(-180, 90 - row0 * 180 / H, 360 / W, 180 / H),
                  resampling=Resampling.bilinear, src_nodata=np.nan, dst_nodata=np.nan)
    lat_rows = 90 - (np.arange(row0, H) + 0.5) * 180 / H
    w = np.clip((lat0 - lat_rows) / 1.5, 0, 1)[:, None] * np.isfinite(dst)
    shade[row0:] = (1 - w) * shade[row0:] + w * np.nan_to_num(dst, nan=1.0)

    col = np.asarray(Image.open(os.path.join(ROOT, "docs", "assets", "moon_2k.jpg")).convert("RGB").resize((W, H), Image.BICUBIC), np.float64)
    # the colour texture smears near the south pole; there the relief alone carries the detail
    latd = np.degrees(lat[:, 0])
    cw = np.clip((-78 - latd) / 2, 0, 1)[:, None, None]
    flat = col[(latd < -76) & (latd > -78)].reshape(-1, 3).mean(0)
    col = (1 - cw) * col + cw * flat
    img = np.clip(col * (0.25 + 0.75 * shade)[:, :, None], 0, 255).astype(np.uint8)
    Image.fromarray(img).save(out, quality=84, optimize=True)
    print(f"written {out} ({os.path.getsize(out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
