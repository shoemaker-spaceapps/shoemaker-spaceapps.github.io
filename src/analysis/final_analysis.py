#!/usr/bin/env python3
"""Final evaluation and candidate lists for the submission (writes out_final/).

Official score: genel_skor from evaluate.py (AHP weights). Pipeline sim is a robustness check.
Usage: python src/analysis/final_analysis.py [--out-moon results/pipeline] [--out results]
"""
import argparse
import os

import numpy as np
import pandas as pd

import evaluate as A

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")
PIPE = os.path.join(ROOT, "results", "pipeline")
SEED = 20260101
N_BOOT = 2000
K_ROBUST = 100
N_ROBUST = 5
MIN_SEP_KM = 30.0
EVAL_TARGETS = ["T_mare", "T_imbrium", "T_highland"]
ARTEMIS = ["T_n2", "T_mm", "T_ma", "T_g2", "T_mp", "T_sp", "T_cb", "T_n1", "T_hw"]
POLAR = ["T_nobile"] + ARTEMIS
WELL_STUDIED = {"Antarctica": (-90, -60, -180, 180), "Atacama": (-27, -18, -71, -68),
                "Iceland": (63, 67, -25, -13), "Hawaii": (18.5, 22.5, -160.5, -154.5)}
N14_NOTE = "ophiolite gabbro, not anorthosite; we first used this area as a hard negative"
LITO_EN = {"bazaltik": "basaltic", "plutonik_bazik": "basic plutonic", "sedimanter": "sedimentary",
           "kristalen": "crystalline", "volkanik_asidik": "acid volcanic", "piroklastik": "pyroclastic",
           "su": "water", "buz": "ice", "bilinmiyor": "unknown"}
KARA = "Karacadağ lava field, southeastern Türkiye"
ROI_EN = {"anatolia_kula": "Kula volcanic field, western Türkiye", "anatolia_karacadag": KARA,
          "anatolia_kapadokya": "Cappadocia, central Türkiye", "arizona_sfvf": "San Francisco volcanic field, Arizona",
          "iceland_central": "Central Iceland", "devon_haughton": "Haughton crater, Devon Island",
          "labrador_mistastin": "Mistastin, Labrador", "lanzarote": "Lanzarote", "hawaii_maunakea": "Mauna Kea, Hawaii",
          "atacama": "Atacama", "chad_tibesti": "Tibesti, Chad", "namib": "Namib",
          "amazon_ctrl": "Amazon (control)", "bavaria_ctrl": "Bavaria (control)",
          "taos_plateau": "Taos Plateau, New Mexico", "sudbury": "Sudbury, Ontario", "stillwater": "Stillwater, Montana",
          "tenerife": "Tenerife", "hawaii_kau": "Ka'u Desert, Hawaii", "lonar": "Lonar, India", "ries": "Ries, Germany"}
# coarse boxes for auto cells, first match wins; no country borders are used
REGION_BOXES = [("Galapagos", -2, 1, -92, -89), ("Cape Verde", 14, 18, -26, -22), ("Hawaii", 18, 23, -161, -154), ("Iceland", 63, 67, -25, -13),
                ("Afar and East Africa", -12, 18, 33, 52), ("Iran, Afghanistan and Pakistan", 24, 40, 47, 72),
                ("Arabia and the Levant", 12, 34, 34, 60),
                ("Deccan (India)", 8, 28, 68, 88), ("Europe and Anatolia", 35.8, 42.2, 25.6, 45),
                ("Sahara", 12, 37.5, -18, 34),
                ("Central and West Africa", -12, 12, -20, 33), ("Southern Africa", -36, -12, 10, 42),
                ("Greenland and Arctic", 60, 90, -75, -10), ("Arctic islands", 75, 90, -180, 180),
                ("Siberia and North Asia", 50, 80, 60, 180),
                ("Central Asia and Tibet", 25, 56, 45, 105), ("East Asia", 18, 50, 105, 145),
                ("Australia", -45, -10, 110, 155), ("Patagonia", -56, -38, -76, -60), ("Andes", -40, 12, -82, -64),
                ("Eastern South America", -40, 12, -64, -34), ("Western US and Mexico", 14, 49, -125, -100),
                ("Central and Eastern US", 14, 49, -100, -60), ("Canada and Alaska", 49, 75, -170, -50),
                ("Europe and Anatolia", 35, 72, -25, 45)]
CLIMATE = ["sicaklik_yillik_ort_C", "sicaklik_en_soguk_ay_min_C", "sicaklik_en_sicak_ay_max_C", "gunluk_fark_C",
           "yagis_mm_yil", "ruzgar_10m_ms", "bagil_nem_yuzde", "gunes_kWh_m2_gun"]


# place names given by the team for single windows; everything else is the Natural Earth country
OVERRIDE = {"E_005847": "northwestern Iran (Khoy ophiolite belt)", "E_000072": KARA, "E_006081": KARA,
            "E_007356": "Harrat ash Shaam, Jordan", "E_005865": "Doğanşehir, Malatya, eastern Türkiye",
            "E_006049": "Karaman, central Türkiye"}


def area_name(lat, lon):
    """Coarse area box, used only for counts such as 'mostly Andean'."""
    for name, la0, la1, lo0, lo1 in REGION_BOXES:
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return name
    return "Other"


def region_name(roi, lat, lon, country="", window_id="", lito=""):
    """One label per window, used in every table, card and text."""
    if window_id in OVERRIDE:
        return OVERRIDE[window_id]
    if roi in ROI_EN:
        return ROI_EN[roi]
    area = area_name(lat, lon)
    if not country:
        return area
    if area == "Arabia and the Levant" and lito == "bazaltik":
        return f"harrat basalt field, {country}"
    if area in ("Galapagos", "Hawaii", "Iceland") and area != country:
        return f"{area}, {country}"
    if lat >= 74 and country in ("Canada", "Russia", "Norway"):
        return f"Arctic islands, {country}"
    if country == "China" and 27 <= lat <= 39.5 and 73 <= lon <= 104:
        return "Tibetan Plateau, China"
    return country


def well_studied(lat, lon):
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    m = np.zeros(len(lat), bool)
    for la0, la1, lo0, lo1 in WELL_STUDIED.values():
        m |= (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
    return m


def haversine(la1, lo1, la2, lo2):
    p1, p2 = np.radians(la1), np.radians(la2)
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(np.minimum(h, 1.0)))


def spaced(df, n, min_sep=MIN_SEP_KM):
    kept = []
    for i, r in df.iterrows():
        if all(haversine(r.lat, r.lon, df.at[j, "lat"], df.at[j, "lon"]) >= min_sep for j in kept):
            kept.append(i)
        if len(kept) >= n:
            break
    return df.loc[kept]


def pool_rank(score, pool):
    """Rank (1 = best) of score among pool windows; NaN outside the pool or for missing scores."""
    r = np.full(len(score), np.nan)
    idx = np.where(pool & np.isfinite(score))[0]
    order = idx[np.argsort(-score[idx], kind="stable")]
    r[order] = np.arange(1, len(order) + 1)
    return r


def load(out_moon):
    P = lambda n: os.path.join(out_moon, n)
    t1 = pd.read_csv(P("T1_earth_windows.csv")).reset_index(drop=True)
    t2 = pd.read_csv(P("T2_target_windows.csv")).set_index("target_id")
    t3 = pd.read_csv(os.path.join(DATA, "known_analogs_moon.csv"))
    neg = pd.read_csv(os.path.join(DATA, "hard_negatives.csv"))
    neg["durum"] = neg.get("durum", pd.Series("", index=neg.index)).fillna("")
    ahp = pd.read_csv(os.path.join(DATA, "ahp_weights.csv")).set_index("kriter")["agirlik"].to_dict()
    sim = pd.read_csv(P("T4_scores.csv"), usecols=["target_id", "window_id", "sim"])
    cpath = P("window_countries.csv")
    t1["country"] = t1.window_id.map(pd.read_csv(cpath).fillna("").set_index("window_id").country) if os.path.exists(cpath) else ""
    t1["country"] = t1.country.fillna("")
    clim_path = os.path.join(out_moon, "iklim_power.csv")
    if os.path.exists(clim_path):
        t1 = t1.merge(pd.read_csv(clim_path)[["window_id"] + CLIMATE], on="window_id", how="left")
    else:
        for c in CLIMATE:
            t1[c] = np.nan
    return t1, t2, t3, neg, ahp, sim


def scores(t1, t2, ahp, sim):
    """genel_skor, arazi_benzerligi and kayac_eslesmesi exactly as analysis_v4.py, plus pipeline sim."""
    feats = ["slope_p50", "slope_p90", "relief"]
    w_lito = ahp.get("lito", 0.4)
    tw = {f: ahp[f] / sum(ahp[g] for g in feats) for f in feats}
    out = {}
    for tid, t in t2.iterrows():
        arazi = np.exp(-A.terrain_distance(t1, t, feats, tw))
        kayac = ((t1.lito.values == t.lito) & (t.lito != "bilinmiyor")).astype(float)
        genel = (w_lito * kayac + (1 - w_lito) * arazi) if t.lito != "bilinmiyor" else arazi
        s = sim[sim.target_id == tid].set_index("window_id").sim.reindex(t1.window_id).to_numpy()
        out[tid] = dict(genel_skor=genel, arazi_benzerligi=arazi, kayac_eslesmesi=kayac, sim=s)
    return out


def clusters(t1, t3, neg, tid):
    pos = [(b.site_id, np.where(A.in_window(t1, b))[0]) for _, b in t3[t3.analog_to == tid].iterrows()
           if {x.strip() for x in str(b.get("dims", "")).split(",")} & {"arazi", "kayac"}]
    ngs = [(b.site_id, np.where(A.in_window(t1, b))[0]) for _, b in neg[(neg.negative_for == tid) & (neg.durum == "")].iterrows()]
    return [c for c in pos if len(c[1])], [c for c in ngs if len(c[1])]


def auc_table(t1, t3, neg, S):
    rng = np.random.default_rng(SEED)
    rows = []
    for tid in EVAL_TARGETS:
        pos, ngs = clusters(t1, t3, neg, tid)
        p_all = np.unique(np.concatenate([c for _, c in pos]))
        n_all = np.unique(np.concatenate([c for _, c in ngs]))
        draws = [(rng.integers(len(pos), size=len(pos)), rng.integers(len(ngs), size=len(ngs))) for _ in range(N_BOOT)]
        for name in ["genel_skor", "arazi_benzerligi", "kayac_eslesmesi", "sim"]:
            s = S[tid][name]
            est = A.auc(s[p_all], s[n_all])
            lo = hi = np.nan
            if len(pos) > 1 and len(ngs) > 1:
                boot = [A.auc(s[np.concatenate([pos[i][1] for i in pi])], s[np.concatenate([ngs[j][1] for j in nj])])
                        for pi, nj in draws]
                lo, hi = np.nanpercentile(boot, [2.5, 97.5])
            rows.append(dict(target_id=tid, score=name, auc=round(est, 4),
                             ci_low=round(lo, 4) if lo == lo else np.nan, ci_high=round(hi, 4) if hi == hi else np.nan,
                             pos_sites=",".join(c for c, _ in pos), neg_regions=",".join(c for c, _ in ngs),
                             n_pos_windows=len(p_all), n_neg_windows=len(n_all),
                             note="" if len(pos) > 1 else "one positive site, no interval"))
    return pd.DataFrame(rows)


def negatives_table(t1, neg, S):
    rows = []
    for _, n in neg.iterrows():
        idx = np.where(A.in_window(t1, n))[0]
        g, sm, ar = S[n.negative_for]["genel_skor"], S[n.negative_for]["sim"], S[n.negative_for]["arazi_benzerligi"]
        rg, rs = A.ranks(np.nan_to_num(g, nan=-1)), A.ranks(np.nan_to_num(sm, nan=-1))
        ra = A.ranks(np.nan_to_num(ar, nan=-1))
        rows.append(dict(negative_id=n.site_id, name=n.site_name, target_id=n.negative_for, status=n.durum or "used",
                         n_windows=len(idx), best_rank_ahp=int(rg[idx].min()) if len(idx) else np.nan,
                         best_rank_pipeline=int(rs[idx].min()) if len(idx) else np.nan,
                         best_rank_terrain=int(ra[idx].min()) if len(idx) else np.nan, of_windows=len(t1)))
    return pd.DataFrame(rows)


def known_sites_table(t1, t3, t2, S):
    rows = []
    for _, b in t3.iterrows():
        idx = np.where(A.in_window(t1, b))[0]
        g = S[b.analog_to]["genel_skor"]
        r_all = A.ranks(np.nan_to_num(g, nan=-1))
        bare = pool_rank(g, t1.aday_maskesi.values == 1)
        tl = t2.loc[b.analog_to].lito
        r_ter = A.ranks(np.nan_to_num(S[b.analog_to]["arazi_benzerligi"], nan=-1))
        rows.append(dict(site_id=b.site_id, site_name=b.site_name, target_id=b.analog_to, dims=b.dims,
                         n_windows=len(idx), best_rank_ahp=int(r_all[idx].min()) if len(idx) else np.nan,
                         best_rank_terrain=int(r_ter[idx].min()) if len(idx) else np.nan,
                         best_rank_bare_pool=np.nanmin(bare[idx]) if len(idx) and np.isfinite(bare[idx]).any() else np.nan,
                         glim_label_correct=round(float((t1.lito.values[idx] == tl).mean()), 2) if len(idx) and tl != "bilinmiyor" else np.nan))
    return pd.DataFrame(rows)


def window_frame(t1, t3, neg):
    w = t1.copy()
    w["area"] = [area_name(a, o) for a, o in zip(w.lat, w.lon)]
    w["region"] = [region_name(*x) for x in zip(w.roi, w.lat, w.lon, w.country, w.window_id, w.lito)]
    w["well_studied"] = well_studied(w.lat, w.lon).astype(int)
    active_neg = {f"neg_{s}" for s in neg[neg.durum == ""].site_id}
    w["hard_negative"] = w.roi.isin(active_neg).astype(int)
    w["n14_note"] = np.where(w.roi == "neg_N14", N14_NOTE, "")
    in_site = np.zeros(len(w), bool)
    for _, b in t3.iterrows():
        in_site |= A.in_window(w, b)
    w["in_known_site"] = in_site.astype(int)
    w["lesser_known"] = ((w.aday_maskesi == 1) & (w.well_studied == 0) & (w.hard_negative == 0) & ~in_site).astype(int)
    w["inis_uygun"] = ((w.slope_p50 < 5) & (w.slope_p90 < 10)).astype(int)
    w["rover_uygun"] = (w.slope_p90 < 20).astype(int)
    return w


def badge(tid, n14):
    if n14:
        return "low confidence"
    if tid in ("T_mare", "T_imbrium"):
        return "tested against known sites"
    if tid == "T_highland":
        return "low confidence"
    if tid in ARTEMIS:
        return "terrain only"
    return "not tested against known sites"


def use_for(tid):
    if tid == "T_mare":
        return ("Rover and equipment tests on basaltic ground, and a possible source of basalt "
                "for regolith simulant (lunar soil copy).")
    if tid == "T_imbrium":
        return "Navigation and operations beside rift and fault edges, and driving on sloped ground."
    if tid == "T_highland":
        return "Field geology practice on plutonic rock, with low confidence in the rock match."
    return "Landing hazard detection and rover mobility on rough ground, plus cold-weather equipment tests."


def profile(r, t, tid):
    lito_known = t.lito != "bilinmiyor"
    why = (f"Median slope {r.slope_p50:.1f}° here and {t.slope_p50:.1f}° on the target; steep-end slope "
           f"(90th percentile) {r.slope_p90:.1f}° and {t.slope_p90:.1f}°; relief {r.relief:.0f} m and {t.relief:.0f} m. "
           f"Rock is {LITO_EN.get(r.lito, r.lito)} with {r.bazalt_frac * 100:.0f}% basalt cover; "
           f"{r.bare_frac * 100:.0f}% of the 10 km window is bare.")
    if not lito_known:
        why += " Rock is not compared for this target, because its lunar rock type is not set."
    # shared limits (gravity, air, permanent shadow) are stated once above the cards; here only what is specific
    breaks = []
    if t.relief > 0 and abs(r.relief - t.relief) / t.relief > 0.5:
        breaks.append(f"{'Rougher' if r.relief > t.relief else 'Gentler'} relief: {r.relief:.0f} m here, {t.relief:.0f} m on the target.")
    if lito_known and r.lito != t.lito:
        breaks.append(f"The rock ({LITO_EN.get(r.lito, r.lito)}) does not match the target ({LITO_EN.get(t.lito, t.lito)}).")
    if r.bare_frac < 0.5:
        breaks.append(f"Partly vegetated: only {r.bare_frac * 100:.0f}% of the window is bare.")
    if r.yagis_mm_yil == r.yagis_mm_yil and r.yagis_mm_yil > 250:
        breaks.append(f"It gets {r.yagis_mm_yil:.0f} mm of rain a year, so the surface weathers.")
    if tid in ("T_highland", "T_nobile") and r.lito == "plutonik_bazik":
        breaks.append("Low confidence rock label: the global map's basic plutonic class may be gabbro or ophiolite, not anorthosite.")
    if r.n14_note:
        breaks.append(f"Note: {r.n14_note}.")
    if not breaks and tid in POLAR and r.sicaklik_en_soguk_ay_min_C == r.sicaklik_en_soguk_ay_min_C:
        breaks.append(f"Even its coldest hour in 2001 to 2025 ({r.sicaklik_en_soguk_ay_min_C:.0f} °C) is far warmer than a lunar cold trap.")
    if not breaks:
        breaks.append("Few differences beyond the shared limits: bare, dry and close in slope and relief.")
    climate = (f"Climate (NASA POWER, 2001 to 2025): lowest hourly temperature {r.sicaklik_en_soguk_ay_min_C:.1f} °C, "
               f"daily range {r.gunluk_fark_C:.1f} °C, {r.yagis_mm_yil:.0f} mm rain a year, wind {r.ruzgar_10m_ms:.1f} m/s."
               if r.sicaklik_en_soguk_ay_min_C == r.sicaklik_en_soguk_ay_min_C else "Climate: not available.")
    return why, " ".join(breaks), use_for(tid), climate


def worldview(lat, lon):
    return ("https://worldview.earthdata.nasa.gov/?v="
            f"{lon - 0.3:.3f},{lat - 0.2:.3f},{lon + 0.3:.3f},{lat + 0.2:.3f}"
            "&l=MODIS_Terra_CorrectedReflectance_TrueColor,Coastlines_15m&t=2024-06-15")


CAND_COLS = ["target_id", "rank_ahp", "rank_pipeline", "window_id", "region", "country", "area", "roi", "lat", "lon", "genel_skor",
             "arazi_benzerligi", "kayac_eslesmesi", "sim", "slope_p50", "slope_p90", "relief", "lito", "bazalt_frac",
             "bazik_plutonik_frac", "bare_frac", "aridity_index"] + CLIMATE + [
             "inis_uygun", "rover_uygun", "n14_note", "confidence"]


def candidates(w, t2, S):
    robust, top20, extremes = [], [], []
    pool = w.lesser_known.values == 1
    for tid, t in t2.iterrows():
        d = w.copy()
        for k, v in S[tid].items():
            d[k] = v
        d["rank_ahp"] = pool_rank(d.genel_skor.values, pool)
        d["rank_pipeline"] = pool_rank(d.sim.values, pool)
        d["target_id"] = tid
        d["confidence"] = [badge(tid, bool(n)) for n in d.n14_note]
        top = spaced(d[d.rank_ahp.notna()].sort_values("rank_ahp"), 20)
        top20.append(top[CAND_COLS])
        both = d[(d.rank_ahp <= K_ROBUST) & (d.rank_pipeline <= K_ROBUST)].copy()
        both["rank_sum"] = both.rank_ahp + both.rank_pipeline
        rb = spaced(both.sort_values(["rank_sum", "rank_ahp"]), N_ROBUST).copy()
        prof = [profile(r, t, tid) for r in rb.itertuples()]
        rb["why_similar"], rb["where_it_breaks"], rb["exploration_use"], rb["climate"] = zip(*prof) if prof else ([],) * 4
        rb["worldview_url"] = [worldview(a, o) for a, o in zip(rb.lat, rb.lon)]
        robust.append(rb[CAND_COLS + ["rank_sum", "why_similar", "where_it_breaks", "exploration_use", "climate", "worldview_url"]])
        terr = d[pool].assign(rank_terrain=pool_rank(d.arazi_benzerligi.values, pool)[pool])
        terr = terr[terr.rank_terrain <= 100]
        for crit, col, asc in [("coldest", "sicaklik_en_soguk_ay_min_C", True), ("largest_daily_range", "gunluk_fark_C", False)]:
            x = terr.dropna(subset=[col]).sort_values(col, ascending=asc)
            x = spaced(x, 3).assign(criterion=crit)
            extremes.append(x[["target_id", "criterion", "rank_terrain", "window_id", "region", "lat", "lon",
                               "slope_p50", "slope_p90", "relief"] + CLIMATE + ["n14_note"]])
    return pd.concat(robust, ignore_index=True), pd.concat(top20, ignore_index=True), pd.concat(extremes, ignore_index=True)


TURKIYE = (35.8, 42.2, 25.6, 44.9)   # rough box for the ophiolite note (Anatolian and Khoy belts)
LAND_MIN = 0.8   # rock analogs need at least 80% land in the window
ROCK_TARGETS = ["T_mare", "T_imbrium", "T_highland", "T_nobile"]


def place(roi, region, lat, lon):
    return region


def ophiolite(region, lat, lon):
    """Basic plutonic windows in the Anatolian and Zagros belts: most likely ophiolite, not anorthosite."""
    la0, la1, lo0, lo1 = TURKIYE
    return la0 <= lat <= la1 and lo0 <= lon <= lo1 and region != KARA


def rock_analogs(w, t2, S, k=5):
    """Windows that fail the bare-surface mask but share the target rock, best first, at least 30 km apart."""
    out = []
    for tid in ROCK_TARGETS:
        t = t2.loc[tid]
        g = S[tid]["genel_skor"]
        pool = ((w.aday_maskesi.values == 0) & (w.lito.values == t.lito) & (w.hard_negative.values == 0)
                & (w.in_known_site.values == 0) & (w.glim_kapsama.values >= LAND_MIN))
        d = w.copy()
        d["genel_skor"], d["target_id"] = g, tid
        d["rank_all"] = A.ranks(np.nan_to_num(g, nan=-1)).astype(float)
        d.loc[~np.isfinite(g), "rank_all"] = np.nan
        d["rank_rock_pool"] = pool_rank(g, pool)
        top = spaced(d[d.rank_rock_pool.notna()].sort_values("rank_rock_pool"), k).copy()
        top["place"] = [place(*x) for x in zip(top.roi, top.region, top.lat, top.lon)]
        tr = np.array([ophiolite(*x) for x in zip(top.region, top.lat, top.lon)], bool)
        note = np.where(tr & top.target_id.isin(["T_highland", "T_nobile"]), "low confidence, likely ophiolite", top.n14_note)
        top["note"] = [("; ".join(x for x in [n, f"window is partly sea (land {c:.0%})" if c < 0.75 else ""] if x)) for n, c in zip(note, top.glim_kapsama)]
        top["confidence"] = ["low confidence" if (tid in ("T_highland", "T_nobile") or n) else "tested against known sites"
                             for n in top.note]
        out.append(top[["target_id", "rank_rock_pool", "rank_all", "window_id", "place", "region", "roi", "lat", "lon", "lito",
                        "bazalt_frac", "bazik_plutonik_frac", "bare_frac", "aridity_index", "slope_p50", "slope_p90", "relief",
                        "genel_skor", "sicaklik_yillik_ort_C", "yagis_mm_yil", "note", "confidence"]])
    R = pd.concat(out, ignore_index=True)
    R[["rank_rock_pool", "rank_all"]] = R[["rank_rock_pool", "rank_all"]].astype(int)
    return R


def targets_table(t2, out_moon=PIPE):
    t = t2.reset_index()
    t["quickmap_ratio_p50"] = (t.slope_p50 / t.quickmap_slope_deg).round(2)
    div = os.path.join(out_moon, "diviner_targets.csv")
    if os.path.exists(div):
        t = t.merge(pd.read_csv(div), on="target_id", how="left")
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-moon", default=PIPE)
    ap.add_argument("--out", default=os.path.join(ROOT, "results"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t1, t2, t3, neg, ahp, sim = load(a.out_moon)
    S = scores(t1, t2, ahp, sim)
    w = window_frame(t1, t3, neg)
    tables = {"auc_ci": auc_table(t1, t3, neg, S), "negatives": negatives_table(t1, neg, S),
              "known_sites": known_sites_table(t1, t3, t2, S), "targets": targets_table(t2, a.out_moon)}
    tables["robust_candidates"], tables["lesser_known_top20"], tables["climate_extremes"] = candidates(w, t2, S)
    tables["rock_analogs"] = rock_analogs(w, t2, S)
    for n, df in tables.items():
        df.to_csv(os.path.join(a.out, f"{n}.csv"), index=False)
    with pd.ExcelWriter(os.path.join(a.out, "results.xlsx")) as xw:
        for n, df in tables.items():
            df.to_excel(xw, sheet_name=n[:31], index=False)
    pd.set_option("display.width", 220)
    print(tables["auc_ci"][["target_id", "score", "auc", "ci_low", "ci_high", "n_pos_windows", "n_neg_windows", "note"]].to_string(index=False))
    print(tables["robust_candidates"][["target_id", "rank_ahp", "rank_pipeline", "region", "lat", "lon", "lito", "confidence"]].to_string(index=False))


if __name__ == "__main__":
    main()
