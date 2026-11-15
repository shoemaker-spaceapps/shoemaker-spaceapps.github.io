#!/usr/bin/env python3
"""Build the static site: docs/index.html (globes), docs/explore/index.html (map and tables) and JSON in docs/data/.

All numbers come from the final results (results/) and the pipeline tables (results/pipeline/).
Usage: python src/site/build_site.py [--pipeline-dir results/pipeline] [--final-dir results] [--docs docs]
"""
import argparse
import json
import os
import string
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TARGET_NAMES = {
    "T_mare": ("Mare Tranquillitatis (Apollo 11)", "mare"), "T_imbrium": ("Hadley Rille, Imbrium rim (Apollo 15)", "imbrium"),
    "T_highland": ("Descartes highlands (Apollo 16)", "highland"), "T_nobile": ("Nobile crater area (south pole)", "polar"),
    "T_n2": ("Nobile Rim 2", "artemis"), "T_mm": ("Mons Mouton", "artemis"), "T_ma": ("Malapert Massif", "artemis"),
    "T_g2": ("de Gerlache Rim 2", "artemis"), "T_mp": ("Mons Mouton Plateau", "artemis"), "T_sp": ("Slater Plain", "artemis"),
    "T_cb": ("Peak Near Cabeus B", "artemis"), "T_n1": ("Nobile Rim 1", "artemis"), "T_hw": ("Haworth", "artemis")}
NEG_EN = {"Salar de Uyuni (orta)": "Salar de Uyuni (central)", "Spitzkoppe-Erongo granitleri": "Spitzkoppe-Erongo granites",
          "Tassili n'Ajjer kumtaşı platosu": "Tassili n'Ajjer"}
NEG_KIND = {"N01": "salt flat", "N02": "salt flat", "N03": "salt flat", "N04": "sand sea", "N05": "limestone plain",
            "N06": "granite", "N07": "sandstone plateau", "N08": "gypsum dunes", "N09": "salt pan", "N10": "salt pan",
            "N11": "salt lake", "N12": "salt and clay desert", "N13": "sandstone", "N14": "ophiolite",
            "N15": "granite dome", "N16": "badlands", "N17": "sandstone"}
LITO_CODES = ["bazaltik", "plutonik_bazik", "sedimanter", "kristalen", "volkanik_asidik", "piroklastik", "su", "buz", "bilinmiyor"]
SCALE = 10000
SALT_PLAYA = ["N01", "N02", "N03", "N09", "N11", "N12"]   # salt flats and playas among the mare negatives


LITO_EN = {"bazaltik": "basalt", "plutonik_bazik": "basic plutonic", "sedimanter": "sedimentary", "kristalen": "crystalline",
           "volkanik_asidik": "acid volcanic", "piroklastik": "pyroclastic", "su": "water", "buz": "ice", "bilinmiyor": "unknown"}
POLAR = {"T_nobile", "T_n2", "T_mm", "T_ma", "T_g2", "T_mp", "T_sp", "T_cb", "T_n1", "T_hw"}


def short_break(r, t, tid):
    """One line on where the analogy fails, for the homepage card."""
    if tid in POLAR:
        return f"No permanent shadow here; the lowest hourly temperature in 2001 to 2025 was {r.sicaklik_en_soguk_ay_min_C:.0f} °C."
    if t.lito != "bilinmiyor" and r.lito != t.lito:
        return f"Different rock: {LITO_EN.get(r.lito, r.lito)} instead of {LITO_EN.get(t.lito, t.lito)}."
    if r.yagis_mm_yil > 250:
        return f"It rains {r.yagis_mm_yil:.0f} mm a year, so the ground weathers."
    if r.bare_frac < 0.5:
        return "Covered by vegetation: almost no bare ground." if r.bare_frac < 0.01 else f"Only {r.bare_frac:.0%} of the ground is bare."
    return "Earth gravity, air and weather; no vacuum or space radiation."


def home_data(w, t2, S, targets, robust, rock, F):
    """Per target: Moon values, the 5 robust candidates and the top 100 lesser-known windows."""
    pool = w.lesser_known.values == 1
    tg = targets.set_index("target_id")
    out = []
    for tid, (name, kind) in TARGET_NAMES.items():
        t, tr = t2.loc[tid], tg.loc[tid]
        rank = F.pool_rank(S[tid]["genel_skor"], pool)
        top = np.where(rank <= 100)[0]
        top = top[np.argsort(rank[top])]
        rank_all = F.pool_rank(S[tid]["genel_skor"], np.ones(len(w), bool))
        anyt = np.where(rank_all <= 100)[0]
        anyt = anyt[np.argsort(rank_all[anyt])]
        rock_ix = [int(x[2:]) for x in rock[rock.target_id == tid].sort_values("rank_rock_pool").window_id]
        best = [int(x[2:]) for x in robust[robust.target_id == tid].sort_values("rank_sum").window_id]

        def item(ix, rk=rank):
            r = w.iloc[ix]
            pl = F.place(r.roi, r.region, r.lat, r.lon)
            oph = F.ophiolite(pl, r.lat, r.lon) and r.lito == "plutonik_bazik" and tid in ("T_highland", "T_nobile")
            return dict(w=r.window_id, lat=round(float(r.lat), 3), lon=round(float(r.lon), 3), reg=pl,
                        g=round(float(S[tid]["genel_skor"][ix]), 3), r=int(rk[ix]) if rk[ix] == rk[ix] else None,
                        mask=int(r.aday_maskesi), note="low confidence, likely ophiolite" if oph else "",
                        s50=round(float(r.slope_p50), 1), s90=round(float(r.slope_p90), 1), rel=int(round(r.relief)),
                        lito=LITO_EN.get(r.lito, r.lito), tmin=round(float(r.sicaklik_en_soguk_ay_min_C), 1),
                        bare=int(round(r.bare_frac * 100)), br=short_break(r, t, tid),
                        n14=bool(r.n14_note))
        div = {k: (None if tr.get(c, np.nan) != tr.get(c, np.nan) else round(float(tr[c]), 0))
               for k, c in [("avg", "diviner_ort_K"), ("cold", "diviner_ort_K_en_soguk")]}
        out.append(dict(id=tid, name=name, kind=kind, lat=float(t.lat), lon=float(t.lon), badge=F.badge(tid, False),
                        moon=dict(s50=round(float(t.slope_p50), 1), s90=round(float(t.slope_p90), 1), rel=int(round(t.relief)),
                                  lito=LITO_EN.get(t.lito, t.lito), **div),
                        best=[item(ix) for ix in best], top=[item(ix) for ix in top if ix not in best],
                        rock=[item(ix, rank_all) for ix in rock_ix],
                        any=[item(ix, rank_all) for ix in anyt if ix not in rock_ix]))
    return out


def find_rows(t2, robust, rock, targets, art_rb, F):
    """Rows of the homepage table: best bare-rock match and best rock analog for each lunar target."""
    conf = {"T_mare": "tested", "T_imbrium": "tested", "T_highland": "low confidence", "T_nobile": "low confidence"}
    out = []
    for tid in ["T_mare", "T_imbrium", "T_highland", "T_nobile"]:
        t = t2.loc[tid]
        b = robust[robust.target_id == tid].sort_values("rank_sum").iloc[0]
        k = rock[rock.target_id == tid].sort_values("rank_rock_pool").iloc[0]
        why = f"{LITO_EN[b.lito]}; slope {b.slope_p50:.1f}°/{b.slope_p90:.0f}° vs {t.slope_p50:.1f}°/{t.slope_p90:.0f}°"
        out.append(f'<tr><th scope="row"><button type="button" class="rowbtn" data-target="{tid}" data-mode="bare" '
                   f'data-lat="{b.lat:.3f}" data-lon="{b.lon:.3f}">{TARGET_NAMES[tid][0].split(" (")[0]}</button></th>'
                   f'<td data-l="Bare rock">{b.region}</td><td data-l="Rock analog"><button type="button" class="rowbtn sub" data-target="{tid}" data-mode="any" '
                   f'data-lat="{k.lat:.3f}" data-lon="{k.lon:.3f}">{k.place}</button></td><td data-l="Why">{why}</td><td data-l="Confidence">{conf[tid]}</td></tr>')
    first = robust[robust.target_id.isin(F.ARTEMIS)].sort_values("rank_sum").iloc[0]
    out.append(f'<tr><th scope="row"><button type="button" class="rowbtn" data-target="{first.target_id}" data-mode="bare" '
               f'data-lat="{first.lat:.3f}" data-lon="{first.lon:.3f}">Artemis III (9 regions)</button></th>'
               f'<td data-l="Bare rock">Andes</td><td data-l="Rock analog">none: lunar rock type not set</td>'
               f'<td data-l="Why">rough terrain</td><td data-l="Confidence">terrain only</td></tr>')
    return "\n".join(out)


def rock_rows(rock):
    """Explore page table of rock analogs (windows that fail the bare-surface mask but match on rock)."""
    out = []
    for r in rock.sort_values(["target_id", "rank_rock_pool"], key=lambda c: c.map({"T_mare": 0, "T_imbrium": 1, "T_highland": 2, "T_nobile": 3}) if c.name == "target_id" else c).itertuples():
        note = r.note if isinstance(r.note, str) else ""
        out.append(f'<tr><td>{TARGET_NAMES[r.target_id][0].split(" (")[0]}</td><td>{r.place}{" <span class=\"tag warn\">" + note + "</span>" if note else ""}</td>'
                   f'<td>{r.lat:.3f}, {r.lon:.3f}</td><td class="n">{r.rank_all}</td><td class="n">{r.rank_rock_pool}</td>'
                   f'<td class="n">{r.bare_frac:.0%}</td><td class="n">{r.slope_p50:.2f}° / {r.slope_p90:.2f}°</td><td>{LITO_EN.get(r.lito, r.lito)}</td></tr>')
    return "\n".join(out)


def i(x, k=1):
    return None if x is None or x != x else int(round(float(x) * k))


def f2(x):
    return f"{x:.2f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline-dir", default=os.path.join(ROOT, "results", "pipeline"))
    ap.add_argument("--final-dir", default=os.path.join(ROOT, "results"))
    ap.add_argument("--analysis-dir", default=os.path.join(ROOT, "src", "analysis"))
    ap.add_argument("--docs", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--team", default=os.path.join(ROOT, "src", "team.json"))
    a = ap.parse_args()
    sys.path.insert(0, a.analysis_dir)
    import final_analysis as F

    t1, t2, t3, neg, ahp, sim = F.load(a.pipeline_dir)
    S = F.scores(t1, t2, ahp, sim)
    w = F.window_frame(t1, t3, neg)
    R = lambda n: pd.read_csv(os.path.join(a.final_dir, n))
    auc, negs, known, targets = R("auc_ci.csv"), R("negatives.csv"), R("known_sites.csv"), R("targets.csv")
    robust, top20, extremes, water = R("robust_candidates.csv"), R("lesser_known_top20.csv"), R("climate_extremes.csv"), R("water_ice.csv")
    rock = R("rock_analogs.csv")
    team = json.load(open(a.team, encoding="utf-8"))
    out = os.path.join(a.docs, "data")
    os.makedirs(out, exist_ok=True)

    regions = sorted(w.region.unique())
    flags = (w.lesser_known * 1 + w.well_studied * 2 + w.hard_negative * 4 + w.in_known_site * 8 +
             w.inis_uygun * 16 + w.rover_uygun * 32 + (w.n14_note != "") * 64 + (w.roi.str.startswith("auto_")) * 128)
    W = {"n": len(w), "regions": regions, "lito": LITO_CODES,
         "lat": [round(x, 3) for x in w.lat], "lon": [round(x, 3) for x in w.lon],
         "reg": [regions.index(r) for r in w.region], "li": [LITO_CODES.index(x) for x in w.lito],
         "bare": [i(x, 100) for x in w.bare_frac], "bas": [i(x, 100) for x in w.bazalt_frac],
         "s50": [i(x, 10) for x in w.slope_p50], "s90": [i(x, 10) for x in w.slope_p90], "rel": [i(x) for x in w.relief],
         "mask": [int(x) for x in w.aday_maskesi], "fl": [int(x) for x in flags],
         "tmin": [i(x, 10) for x in w.sicaklik_en_soguk_ay_min_C], "dr": [i(x, 10) for x in w.gunluk_fark_C],
         "rain": [i(x) for x in w.yagis_mm_yil], "wind": [i(x, 10) for x in w.ruzgar_10m_ms]}
    json.dump(W, open(os.path.join(out, "windows.json"), "w"), separators=(",", ":"))

    sc = {}
    for tid in TARGET_NAMES:
        g = S[tid]["genel_skor"]
        sc[tid] = {"g": [i(x, SCALE) for x in g]}
        if t2.loc[tid].lito != "bilinmiyor":
            sc[tid]["a"] = [i(x, SCALE) for x in S[tid]["arazi_benzerligi"]]
    json.dump(sc, open(os.path.join(out, "scores.json"), "w"), separators=(",", ":"))

    tg = []
    for tid, (name, kind) in TARGET_NAMES.items():
        r = targets.set_index("target_id").loc[tid]
        tg.append({k: (None if (isinstance(v, float) and v != v) else v) for k, v in dict(
            id=tid, name=name, kind=kind, lat=float(r.lat), lon=float(r.lon), lito=r.lito,
            s50=round(float(r.slope_p50), 2), s90=round(float(r.slope_p90), 2), rel=round(float(r.relief), 0),
            qm=float(r.quickmap_slope_deg) if r.quickmap_slope_deg == r.quickmap_slope_deg else None,
            div_avg=float(r.get("diviner_ort_K", np.nan)), div_max=float(r.get("diviner_max_K", np.nan)),
            div_cold=float(r.get("diviner_ort_K_en_soguk", np.nan)), div_ice=float(r.get("diviner_buz_pay", np.nan)),
            badge=F.badge(tid, False)).items()})
    json.dump(tg, open(os.path.join(out, "targets.json"), "w"), separators=(",", ":"))
    json.dump(home_data(w, t2, S, targets, robust, rock, F), open(os.path.join(out, "home.json"), "w"),
              separators=(",", ":"), ensure_ascii=False)

    def cand_rows(df):
        keep = ["target_id", "rank_ahp", "rank_pipeline", "window_id", "region", "lat", "lon", "genel_skor", "lito",
                "bazalt_frac", "bare_frac", "slope_p50", "slope_p90", "relief", "n14_note", "confidence",
                "inis_uygun", "rover_uygun"] + [c for c in ["why_similar", "where_it_breaks", "exploration_use", "climate",
                                                           "worldview_url"] if c in df]
        d = df[keep].copy().round(4)
        return json.loads(d.to_json(orient="records"))
    json.dump({"robust": cand_rows(robust), "top20": cand_rows(top20)}, open(os.path.join(out, "candidates.json"), "w"),
              separators=(",", ":"))

    plain = lambda x: str(x).replace(" \u2014 ", ", ").replace("\u2014", ",")
    known = known.assign(site_name=known.site_name.map(plain))
    boxes = {"known": [dict(id=b.site_id, name=plain(b.site_name), target=b.analog_to, dims=b.dims,
                            box=[b.lat_min, b.lat_max, b.lon_min, b.lon_max]) for b in t3.itertuples()],
             "neg": [dict(id=n.site_id, name=NEG_EN.get(n.site_name, n.site_name), kind=NEG_KIND.get(n.site_id, ""),
                          target=n.negative_for, removed=bool(n.durum), box=[n.lat_min, n.lat_max, n.lon_min, n.lon_max])
                     for n in neg.itertuples()]}
    json.dump(boxes, open(os.path.join(out, "boxes.json"), "w"), separators=(",", ":"))
    ev = {"auc": json.loads(auc.round(3).to_json(orient="records")),
          "negatives": json.loads(negs.assign(name=negs.name.map(lambda x: NEG_EN.get(x, x)),
                                              kind=negs.negative_id.map(NEG_KIND)).to_json(orient="records")),
          "known": json.loads(known.to_json(orient="records")),
          "extremes": json.loads(extremes.round(2).to_json(orient="records")),
          "water": json.loads(water.to_json(orient="records")),
          "rock": json.loads(rock.round(4).to_json(orient="records"))}
    json.dump(ev, open(os.path.join(out, "eval.json"), "w"), separators=(",", ":"))
    json.dump(team, open(os.path.join(out, "team.json"), "w"), separators=(",", ":"), ensure_ascii=False)

    A = auc.set_index(["target_id", "score"])
    used = negs[negs.status == "used"]
    mare_neg = used[used.target_id == "T_mare"]
    salt = mare_neg[mare_neg.negative_id.isin(SALT_PLAYA)]
    best_salt = salt.loc[salt.best_rank_terrain.idxmin()]
    mare_known = known[(known.target_id == "T_mare") & known.dims.str.contains("arazi|kayac")]
    qmr = targets.quickmap_ratio_p50.dropna()
    art = targets[targets.target_id.isin(F.ARTEMIS)]
    ter = F.A.ranks(np.nan_to_num(S["T_mare"]["arazi_benzerligi"], nan=-1))
    sb = neg.set_index("site_id").loc[best_salt.negative_id]
    sidx = np.where(F.A.in_window(t1, sb))[0]
    salt_i = sidx[np.argmin(ter[sidx])]
    m1 = robust[robust.target_id == "T_mare"].sort_values("rank_sum").iloc[0]
    m1_all = int(F.pool_rank(S["T_mare"]["genel_skor"], np.ones(len(w), bool))[int(w.index[w.window_id == m1.window_id][0])])
    ex_art = extremes[extremes.target_id.isin(F.ARTEMIS) & (extremes.criterion == "coldest")]
    cold = ex_art.loc[ex_art.sicaklik_en_soguk_ay_min_C.idxmin()] if len(ex_art) and ex_art.sicaklik_en_soguk_ay_min_C.notna().any() else None
    n_auto = int(w.roi.str.startswith("auto_").sum())
    valid = int(np.isfinite(S["T_mare"]["genel_skor"]).sum())
    bare_pool = (w.aday_maskesi.values == 1) & (w.hard_negative.values == 0)
    tops = [np.where(F.pool_rank(S[t]["genel_skor"], bare_pool) <= 100)[0] for t in t2.index]
    n_top = sum(len(x) for x in tops)
    n_out = sum(int((w.well_studied.values[x] == 0).sum()) for x in tops)
    r1 = rock[(rock.target_id == "T_mare") & (rock.rank_rock_pool == 1)].iloc[0]
    tr = robust[robust.target_id.isin(["T_mare", "T_imbrium"])]
    tr_name = {"Arabia and the Levant": "basalt fields (harrats)", "Afar and East Africa": "the Afar and East African rift"}
    trusted = " and ".join(f"{tr_name.get(a, a)} in {' and '.join(', '.join(g.country.unique()).rsplit(', ', 1))} ({len(g)})"
                           for a, g in tr.groupby("area", sort=False))
    am = auc[(auc.target_id == "T_mare") & (auc.score == "genel_skor")].iloc[0]
    art_rb = robust[robust.target_id.isin(F.ARTEMIS)].area.value_counts()
    oph = rock[rock.note.fillna("").str.contains("ophiolite")]
    tname = {"T_nobile": "Nobile", "T_highland": "the highland"}
    oph_list = "; ".join(f"{' and '.join(g.place)} for {tname[t]} (rank{'s' if len(g) > 1 else ''} {' and '.join(str(x) for x in g.rank_all)} of all windows)"
                         for t, g in oph.groupby("target_id", sort=False))
    nob = water[(water.target_id == "T_nobile") & (water.lesser_known == 1)].sort_values("best_score", ascending=False)
    vals = dict(
        n_valid=f"{valid:,}", n_top_bare=f"{n_top:,}", n_top_out=f"{n_out:,}", pct_top_out=f"{n_out / n_top:.0%}",
        n_robust=len(robust), n_robust_out=int((F.well_studied(robust.lat, robust.lon) == 0).sum()),
        n_trusted=len(tr), trusted=trusted, mare_pos_n=len(am.pos_sites.split(",")), mare_pos_w=int(am.n_pos_windows), mare_neg_n=len(am.neg_regions.split(",")),
        mare_neg_w=int(am.n_neg_windows), mare_pairs=f"{int(am.n_pos_windows) * int(am.n_neg_windows):,}", rock1_region=r1.region, rock1_rank=int(r1.rank_all), rock1_bare=f"{r1.bare_frac:.0%}", mare_s50=f"{t2.loc['T_mare'].slope_p50:.2f}",
        andes=f"{art_rb.get('Andes', 0)} of {art_rb.sum()}",
        nob_dry=nob[nob.group == "Dry-surface analog"].region.iloc[0], nob_ice=nob[nob.group == "Ice-bearing analog"].region.iloc[0],
        find_rows=find_rows(t2, robust, rock, targets, art_rb, F), rock_rows=rock_rows(rock), oph_list=oph_list,
        oph_sentence=f"Some windows sit on rock the global map calls basic plutonic: {oph_list}. There the rock is most likely ophiolite, not anorthosite, so we mark them low confidence.",
        n_windows=f"{len(w):,}", n_targets=len(t2), n_artemis=int(t2.index.isin(F.ARTEMIS).sum()),
        n_named=int(w.loc[~w.roi.str.startswith(("auto_", "neg_")), "roi"].nunique()),
        n_auto_windows=f"{n_auto:,}", n_auto_cells=int(w[w.roi.str.startswith('auto_')].roi.nunique()),
        n_neg=int((neg.durum == "").sum()), n_sites=len(t3),
        mare_auc=f2(A.loc[("T_mare", "genel_skor")].auc), mare_lo=f2(A.loc[("T_mare", "genel_skor")].ci_low),
        mare_hi=f2(A.loc[("T_mare", "genel_skor")].ci_high), terrain_auc=f2(A.loc[("T_mare", "arazi_benzerligi")].auc),
        rock_auc=f2(A.loc[("T_mare", "kayac_eslesmesi")].auc), pipe_auc=f2(A.loc[("T_mare", "sim")].auc),
        imb_auc=f2(A.loc[("T_imbrium", "genel_skor")].auc), imb_terrain=f2(A.loc[("T_imbrium", "arazi_benzerligi")].auc),
        high_auc=f2(A.loc[("T_highland", "genel_skor")].auc), high_lo=f2(A.loc[("T_highland", "genel_skor")].ci_low),
        high_hi=f2(A.loc[("T_highland", "genel_skor")].ci_high),
        best_neg_rank=f"{int(used.best_rank_ahp.min()):,}",
        best_neg_name=NEG_EN.get(used.loc[used.best_rank_ahp.idxmin(), "name"], used.loc[used.best_rank_ahp.idxmin(), "name"]),
        best_salt_name=NEG_EN.get(best_salt["name"], best_salt["name"]), best_salt_rank=f"{int(best_salt.best_rank_terrain):,}",
        best_salt_kind=NEG_KIND.get(best_salt.negative_id, ""),
        n_mare_known=len(mare_known),
        n_mare_known_below=int((mare_known.best_rank_terrain > best_salt.best_rank_terrain).sum()),
        qm_lo=f2(qmr.min()), qm_hi=f2(qmr.max()),
        div_cold_lo=f"{art.diviner_ort_K_en_soguk.min():.0f}", div_cold_hi=f"{art.diviner_ort_K_en_soguk.max():.0f}",
        div_cold_lo_c=f"{art.diviner_ort_K_en_soguk.min() - 273.15:.0f}", div_cold_hi_c=f"{art.diviner_ort_K_en_soguk.max() - 273.15:.0f}",
        div_ice_lo=f"{art.diviner_buz_pay.min():.0%}", div_ice_hi=f"{art.diviner_buz_pay.max():.0%}",
        div_mean_lo=f"{art.diviner_ort_K.min():.0f}", div_mean_hi=f"{art.diviner_ort_K.max():.0f}",
        salt_lat=f"{t1.lat[salt_i]:.3f}", salt_lon=f"{t1.lon[salt_i]:.3f}",
        mare1_lat=f"{m1.lat:.3f}", mare1_lon=f"{m1.lon:.3f}", mare1_region=m1.region, mare1_all=m1_all, mare1_ahp=int(m1.rank_ahp), mare1_pipe=int(m1.rank_pipeline),
        earth_cold_C=f"{cold.sicaklik_en_soguk_ay_min_C:.0f}" if cold is not None else "n/a",
        earth_cold_region=cold.region if cold is not None else "n/a",
        site_url=team["site_url"], demo_url=team["demo_url"], repo_url=team["repo_url"], org_url=team["org_url"],
        challenge=team["challenge"], team=team["team"],
        team_items="\n".join(f'<li><strong>{m["name"]}</strong>: {m["role"]}</li>' for m in team["members"]))
    tdir = os.path.join(os.path.dirname(__file__), "templates")
    for src, dst in [("home.html", "index.html"), ("explore.html", os.path.join("explore", "index.html"))]:
        os.makedirs(os.path.dirname(os.path.join(a.docs, dst)) or a.docs, exist_ok=True)
        tpl = string.Template(open(os.path.join(tdir, src), encoding="utf-8").read())
        open(os.path.join(a.docs, dst), "w", encoding="utf-8").write(tpl.substitute(vals))
    json.dump(vals, open(os.path.join(out, "numbers.json"), "w"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    size = sum(os.path.getsize(os.path.join(dp, fn)) for dp, _, fs in os.walk(a.docs) for fn in fs)
    print(f"site written to {a.docs} ({size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
