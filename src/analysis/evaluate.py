#!/usr/bin/env python3
"""Analog profile and per-dimension evaluation from T1/T2/T3 (no downloads, runs in seconds).

genel_skor is the official score: w_lito * rock match + (1 - w_lito) * terrain similarity, with AHP weights.
Known sites are judged on the dimensions they are known for (dims column): arazi (terrain) is ranked against
chance, kayac (rock) checks GLiM labels, surec and operasyon are listed only. AUC compares windows of sites
with arazi or kayac against hard negative windows. Output names keep their v4_ prefix.

Usage: python src/analysis/evaluate.py --out results/pipeline --t3 data/known_analogs_moon.csv \
         --negatives data/hard_negatives.csv --ahp data/ahp_weights.csv
"""
import argparse
import os

import numpy as np
import pandas as pd

HALF_DEG = 10 / 2 / 111.195
K = 20
N_RAND = 20000
SEED = 20260101


def in_window(t1, b):
    dl = HALF_DEG / np.cos(np.radians(t1.lat.values))
    return ((t1.lat.values + HALF_DEG >= b.lat_min) & (t1.lat.values - HALF_DEG <= b.lat_max) &
            (t1.lon.values + dl >= b.lon_min) & (t1.lon.values - dl <= b.lon_max))


def terrain_distance(t1, t, feats, weights=None):
    w = weights or {f: 1 / len(feats) for f in feats}
    d = np.zeros(len(t1))
    for f in feats:
        iqr = np.subtract(*np.nanpercentile(t1[f], [75, 25])) or 1.0
        d += w[f] * np.abs(t1[f].values - t[f]) / iqr
    return d


def ranks(score_desc):
    order = np.argsort(-score_desc, kind="stable")
    r = np.empty(len(order), int)
    r[order] = np.arange(1, len(order) + 1)
    return r


def random_best(N, n, rng):
    return np.array([rng.choice(N, n, replace=False).min() + 1 for _ in range(N_RAND)])


def auc(pos, neg):
    if len(pos) == 0 or len(neg) == 0:
        return np.nan
    pos, neg = np.asarray(pos), np.asarray(neg)
    return float(((pos[:, None] > neg[None, :]).mean() + 0.5 * (pos[:, None] == neg[None, :]).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out_moon")
    ap.add_argument("--t3", required=True, help="T3 + 'dims' kolonu (arazi,kayac,surec,operasyon)")
    ap.add_argument("--negatives", default="")
    ap.add_argument("--ahp", default="", help="kriter,agirlik CSV (lito dahil)")
    ap.add_argument("--feats", default="slope_p50,slope_p90,relief")
    a = ap.parse_args()
    P = lambda n: os.path.join(a.out, n)
    t1 = pd.read_csv(P("T1_earth_windows.csv")).reset_index(drop=True)
    t2 = pd.read_csv(P("T2_target_windows.csv")).set_index("target_id")
    t3 = pd.read_csv(a.t3)
    feats = a.feats.split(",")
    rng = np.random.default_rng(SEED)
    N = len(t1)

    if a.ahp:
        w = pd.read_csv(a.ahp).set_index("kriter")["agirlik"].to_dict()
    else:
        w = {f: 0.6 / len(feats) for f in feats} | {"lito": 0.4}
    w_lito = w.get("lito", 0.4)
    tw = {f: w[f] / sum(w[f] for f in feats) for f in feats}

    # profile: every window, dimensions kept apart
    prof = []
    T_rank = {}
    for tid, t in t2.iterrows():
        d = terrain_distance(t1, t, feats, tw)
        arazi = np.exp(-d)
        # unknown target rock (Artemis III): terrain only
        kayac = ((t1.lito.values == t.lito) & (t.lito != "bilinmiyor")).astype(float)
        genel = (w_lito * kayac + (1 - w_lito) * arazi) if t.lito != "bilinmiyor" else arazi
        T_rank[tid] = ranks(arazi)
        df = t1[["window_id", "roi", "lat", "lon", "lito", "bare_frac", "aday_maskesi"] + feats].copy()
        df.insert(0, "target_id", tid)
        df["arazi_benzerligi"] = arazi.round(4)
        df["kayac_eslesmesi"] = kayac.astype(int)
        df["yuzey_acik"] = df.aday_maskesi
        df["genel_skor"] = genel.round(4)
        df["genel_sira"] = ranks(genel)
        df["arazi_sira"] = T_rank[tid]
        prof.append(df)
    prof = pd.concat(prof, ignore_index=True)
    prof.to_csv(P("v4_analog_profili.csv"), index=False)

    rows_a, rows_k, rows_o = [], [], []
    for _, b in t3.iterrows():
        dims = [x.strip() for x in str(b.get("dims", "")).split(",") if x.strip()]
        m = in_window(t1, b)
        n = int(m.sum())
        if n == 0:
            continue
        if "arazi" in dims:
            best = int(T_rank[b.analog_to][m].min())
            sims = random_best(N, n, rng)
            other = {t: int(T_rank[t][m].min()) for t in t2.index if t != b.analog_to}
            rows_a.append(dict(site_id=b.site_id, site_name=b.site_name, hedef=b.analog_to, pencere=n, sira=best,
                               rastgele_medyan=int(np.median(sims)), p=round(float((sims <= best).mean()), 4),
                               rastgele_ilk20=round(float((sims <= K).mean()), 3),
                               hedefe_ozgu=bool(best < min(other.values())),
                               en_yakin_diger_hedef=min(other, key=other.get)))
        if "kayac" in dims:
            tl = t2.loc[b.analog_to].lito
            if tl == "bilinmiyor":
                continue
            lab = t1.lito.values[m]
            rows_k.append(dict(site_id=b.site_id, site_name=b.site_name, hedef_lito=tl, pencere=n,
                               dogru_oran=round(float((lab == tl).mean()), 2),
                               etiketler="; ".join(f"{k}:{v}" for k, v in pd.Series(lab).value_counts().items())))
        rest = [x for x in dims if x in ("surec", "operasyon")]
        if rest:
            rows_o.append(dict(site_id=b.site_id, site_name=b.site_name, boyutlar=",".join(rest),
                               not_="Bu boyut mevcut ozelliklerle olculmuyor; nitel olarak raporlanir."))
    A, Kt, O = pd.DataFrame(rows_a), pd.DataFrame(rows_k), pd.DataFrame(rows_o)
    A.to_csv(P("v4_eval_arazi.csv"), index=False)
    Kt.to_csv(P("v4_eval_kayac.csv"), index=False)
    O.to_csv(P("v4_eval_nitel.csv"), index=False)

    # target specificity: is a site ranked best for its own target?
    spec = []
    for _, b in t3.iterrows():
        m = in_window(t1, b)
        if m.sum():
            r = {t: T_rank[t][m].min() for t in t2.index}
            spec.append(min(r, key=r.get) == b.analog_to)

    auc_rows = []
    if a.negatives and os.path.exists(a.negatives):
        neg = pd.read_csv(a.negatives)
        for tid in t2.index:
            sc = prof[prof.target_id == tid].set_index("window_id")
            pos_ids, neg_ids, pos_sites = set(), set(), []
            for _, b in t3[t3.analog_to == tid].iterrows():
                dims = {x.strip() for x in str(b.get("dims", "")).split(",")}
                if dims & {"arazi", "kayac"}:
                    w = set(t1.window_id[in_window(t1, b)])
                    if w:
                        pos_ids |= w
                        pos_sites.append(b.site_id)
            for _, b in neg[neg.negative_for == tid].iterrows():
                neg_ids |= set(t1.window_id[in_window(t1, b)])
            P_, N_ = list(pos_ids), list(neg_ids)
            auc_rows.append(dict(hedef=tid, pozitif_saha=",".join(pos_sites), pozitif=len(P_), negatif=len(N_),
                                 AUC=auc(sc.loc[P_, "genel_skor"] if P_ else [], sc.loc[N_, "genel_skor"] if N_ else []),
                                 AUC_arazi=auc(sc.loc[P_, "arazi_benzerligi"] if P_ else [],
                                               sc.loc[N_, "arazi_benzerligi"] if N_ else [])))
    AUC = pd.DataFrame(auc_rows)
    AUC.to_csv(P("v4_auc.csv"), index=False)

    print(f"\n[arazi boyutu] {len(A)} saha, ozellikler: {feats}")
    if len(A):
        print(A[["site_name", "hedef", "pencere", "sira", "rastgele_medyan", "p", "hedefe_ozgu"]].to_string(index=False))
        rr = A.rastgele_ilk20.mean()
        print(f"  recall@{K} = {(A.sira <= K).mean():.2f} (rastgele {rr:.2f})   MRR = {(1 / A.sira).mean():.3f}")
    if len(Kt):
        print(f"\n[kayac boyutu] GLiM etiket dogrulugu ortalamasi: {Kt.dogru_oran.mean():.2f}")
        print(Kt[["site_name", "hedef_lito", "pencere", "dogru_oran"]].to_string(index=False))
    print(f"\n[ozgulluk] kendi hedefinde en iyi siralanan saha orani: {np.mean(spec):.2f} (rastgele 1/{len(t2)})")
    if len(AUC):
        print("\n[AUC]")
        print(AUC.to_string(index=False))
    else:
        print("\n[AUC] negatif saha penceresi yok; --negatives ile ve T1'de negatif bolgeler varken calistir.")


if __name__ == "__main__":
    main()
