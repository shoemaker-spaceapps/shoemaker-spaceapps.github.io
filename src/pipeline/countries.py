#!/usr/bin/env python3
"""Country of every Earth window from Natural Earth admin-0 polygons (1:10m, v5.1.1).

The window centre decides the country. A centre that falls in the sea takes the nearest country within 25 km.
Output: results/pipeline/window_countries.csv (window_id, country).

Usage: NE_COUNTRIES=data/raw/ne_10m_admin_0_countries.shp python src/pipeline/countries.py
"""
import os

import geopandas as gpd
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RENAME = {"Turkey": "Türkiye", "United States of America": "United States", "Somaliland": "Somaliland, Somalia", "Dem. Rep. Congo": "DR Congo", "Central African Rep.": "Central African Republic",
          "W. Sahara": "Western Sahara", "Bosnia and Herz.": "Bosnia and Herzegovina", "Eq. Guinea": "Equatorial Guinea",
          "S. Sudan": "South Sudan", "Solomon Is.": "Solomon Islands", "Falkland Is.": "Falkland Islands",
          "Fr. S. Antarctic Lands": "French Southern Lands", "Dominican Rep.": "Dominican Republic"}


def main():
    shp = os.environ.get("NE_COUNTRIES", os.path.join(ROOT, "data", "raw", "ne_10m_admin_0_countries.shp"))
    pipe = os.path.join(ROOT, "results", "pipeline")
    t1 = pd.read_csv(os.path.join(pipe, "T1_earth_windows.csv"), usecols=["window_id", "lat", "lon"])
    ne = gpd.read_file(shp)[["NAME", "geometry"]]
    ne["country"] = ne.NAME.replace(RENAME)
    pts = gpd.GeoDataFrame(t1, geometry=gpd.points_from_xy(t1.lon, t1.lat), crs="EPSG:4326")
    hit = gpd.sjoin(pts, ne[["country", "geometry"]], how="left", predicate="within").drop_duplicates("window_id")
    miss = hit.country.isna()
    if miss.any():
        m = pts[pts.window_id.isin(hit.loc[miss, "window_id"])].to_crs("EPSG:3857")
        near = gpd.sjoin_nearest(m, ne[["country", "geometry"]].to_crs("EPSG:3857"), how="left",
                                 max_distance=25_000 / 0.8).drop_duplicates("window_id").set_index("window_id").country
        hit.loc[miss, "country"] = hit.loc[miss, "window_id"].map(near)
    out = hit[["window_id", "country"]].fillna({"country": ""})
    out.to_csv(os.path.join(pipe, "window_countries.csv"), index=False)
    print(f"{len(out)} windows, {int((out.country == '').sum())} without a country (open sea)")


if __name__ == "__main__":
    main()
