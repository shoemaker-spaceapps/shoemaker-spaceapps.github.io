#!/usr/bin/env python3
"""Water, ice and ISRU reading of the Earth regions for the polar lunar targets (writes out_final/water_ice.csv).

Each window gets a group from its own values (fixed thresholds on v4 windows and NASA POWER climate); a row is the
best-scoring window of one group in one region, so every number in a row belongs to the window it points to.
Usage: python src/analysis/water_ice.py [--out-moon results/pipeline] [--out results]
"""
import argparse
import os

import numpy as np
import pandas as pd

import final_analysis as F

DRY_ARIDITY, DRY_BARE = 0.05, 0.8
ICE_SNOW, ICE_MAAT_C = 0.05, -2.0   # mean annual air temperature below -2 C is a common proxy for likely permafrost
RULES = {
    "Dry-surface analog": f"aridity < {DRY_ARIDITY} and bare > {DRY_BARE}",
    "Ice-bearing analog": "passes the bare-surface mask, and snow or ice covers more than 5% of the window or the mean annual air "
                          "temperature is below -2 °C (a common proxy for likely permafrost)",
    "Terrain analog": "passes the bare-surface mask, but is neither dry-surface nor ice-bearing",
    "Rock-closest (fails bare-surface mask)": "fails the bare-surface mask, but its rock matches the target",
    "Not a surface analog": "fails the bare-surface mask and its rock does not match the target",
}
ISRU = {
    "Dry-surface analog": "Bury ice in dry regolith to test excavation, heating and water extraction, and measure equipment wear in dusty ground.",
    "Ice-bearing analog": "Drill and sample icy ground, then melt and separate water, with equipment going through freeze and thaw cycles.",
    "Rock-closest (fails bare-surface mask)": "Source rock for regolith simulant; not a place for ice or water tests.",
    "Terrain analog": "Plan rover routes for carrying ice and water across rough and sloped ground.",
    "Not a surface analog": "Not suited to water or ice tests.",
}


def comment(g, r):
    a, bare, snow, maat, rain = r.aridity, r.bare, r.snow, r.mean_annual_C, r.rain_mm
    if g == "Dry-surface analog":
        s = (f"Hyper-arid (aridity {a:.3f}) and {bare:.0%} bare, close to the dryness of lunar regolith. "
             "No natural ice, so buried ice must be emplaced to test extraction.")
    elif g == "Ice-bearing analog":
        cover = f"{snow:.0%} snow or ice cover" if snow >= 0.01 else "no lasting snow; cold from mean annual temperature"
        s = (f"Cold, bare ground (mean annual air temperature {maat:.1f} °C) with {cover}. Useful for ice drilling "
             "and melting trials, but liquid water has no lunar counterpart.")
    elif g == "Rock-closest (fails bare-surface mask)":
        cover = f"only {bare:.0%} bare" if bare >= 0.01 else "almost no bare ground"
        s = (f"Closest on rock, but {cover} with aridity {a:.2f}, so it fails the bare-surface mask. "
             "Poor water analog, valuable as a rock analog.")
    elif g == "Terrain analog":
        s = f"Relevant for terrain and surface operations, not for water (aridity {a:.2f}, {rain:.0f} mm rain a year)."
    elif maat < ICE_MAAT_C:
        s = f"Cold ground (mean annual {maat:.1f} °C), likely permafrost, but vegetated: useful for drilling trials only."
    else:
        s = f"Too vegetated or humid for a surface analog (aridity {a:.2f}, {bare:.0%} bare)."
    if r.region == F.ROI_EN["devon_haughton"]:
        s += " High index reflects low evaporative demand, not abundant rain. Carbonate rock, so not a geological analog."
    return s


def window_group(w, rock_match):
    """Group of every window, from its own values (not from a regional median)."""
    dry = (w.aridity_index < DRY_ARIDITY) & (w.bare_frac > DRY_BARE)
    ice = ((w.snow_frac > ICE_SNOW) | (w.sicaklik_yillik_ort_C < ICE_MAAT_C)) & (w.aday_maskesi == 1)
    g = np.where(dry, "Dry-surface analog", np.where(ice, "Ice-bearing analog", np.where(
        w.aday_maskesi == 1, "Terrain analog", np.where(rock_match, "Rock-closest (fails bare-surface mask)", "Not a surface analog"))))
    return pd.Series(g, index=w.index)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-moon", default=F.PIPE)
    ap.add_argument("--out", default=os.path.join(F.ROOT, "results"))
    a = ap.parse_args()
    t1, t2, t3, neg, ahp, sim = F.load(a.out_moon)
    S = F.scores(t1, t2, ahp, sim)
    w = F.window_frame(t1, t3, neg)
    w = w[~w.roi.str.startswith("neg_")]
    named = ~w.roi.str.startswith(("auto_", "neg_"))
    known_regions = set(w.loc[named & (w.in_known_site == 1), "region"])
    rows = []
    for tid in F.POLAR:
        t = t2.loc[tid]
        rock = (S[tid]["kayac_eslesmesi"][w.index] == 1) & (t.lito != "bilinmiyor")
        d = w.assign(score=S[tid]["genel_skor"][w.index], group=window_group(w, rock).values)
        d = d[np.isfinite(d.score)]
        for (reg, grp), g in d.groupby(["region", "group"]):
            b = g.loc[g.score.idxmax()]
            reg_all = d[d.region == reg]
            rows.append(dict(target_id=tid, region=reg, group=grp, n_windows=len(g), n_region=len(reg_all),
                             best_score=round(float(b.score), 4), best_window=b.window_id, best_lat=b.lat, best_lon=b.lon,
                             aridity=round(float(b.aridity_index), 3), bare=round(float(b.bare_frac), 3),
                             snow=round(float(b.snow_frac), 3), mean_annual_C=round(float(b.sicaklik_yillik_ort_C), 1),
                             coldest_min_C=round(float(b.sicaklik_en_soguk_ay_min_C), 1), rain_mm=round(float(b.yagis_mm_yil), 0),
                             region_median_aridity=round(float(reg_all.aridity_index.median()), 3),
                             region_median_bare=round(float(reg_all.bare_frac.median()), 3),
                             well_studied=int(b.well_studied), known_site=int(reg in known_regions),
                             control=int(reg in (F.ROI_EN["amazon_ctrl"], F.ROI_EN["bavaria_ctrl"]))))
    W = pd.DataFrame(rows)
    W["group_rule"] = W.group.map(RULES)
    W["reading"] = [comment(g, r) for g, r in zip(W.group, W.itertuples())]
    W["isru_test_use"] = W.group.map(ISRU)
    W["lesser_known"] = ((W.well_studied == 0) & (W.control == 0) & (W.known_site == 0)).astype(int)
    W = W.sort_values(["target_id", "best_score"], ascending=[True, False])
    W.to_csv(os.path.join(a.out, "water_ice.csv"), index=False)
    print(W.groupby(["target_id", "group"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
