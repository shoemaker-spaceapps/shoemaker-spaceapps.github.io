#!/usr/bin/env python3
"""Build data/known_analogs_moon.csv from the source catalogue tables.

Converts the catalogue export (semicolon separated, decimal commas, BOM, CRLF), maps free-text analog_to
values to target ids, adds four sites from the first-round table, applies box corrections, and adds the
eval_track and dims columns. Scoring never reads this table; it is used for evaluation only.
Usage: python src/pipeline/prepare_known_sites.py [--catalogue ...] [--first-round ...] [--dims ...] [--out ...]
"""
import argparse
import csv
import os
import re
from collections import Counter

NUM_COLS = ["center_lat", "center_lon", "lat_min", "lat_max", "lon_min", "lon_max"]

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(ROOT, "data")

# free-text analog_to -> target id, matched at the start of the text
ANALOG_TO_MAP = [
    (r"^imbrium\b", "T_imbrium"),
    (r"^mare\b", "T_mare"),
    (r"^highlands?\b", "T_highland"),
    (r"^nobile\b|^polar\b", "T_nobile"),
]

# sites taken from the first-round table; "Iceland (general)" is left out because Askja replaces it
MERGE_SITES = ["Cinder Lake", "Black Point", "Haughton", "Mistastin"]
MERGE_ID_START = 12          # renumbered from S12 when ids clash

# Box corrections by site_id: (lat_min, lat_max, lon_min, lon_max).
# S02 Merriam: the source box sat ~24 km east of the crater; now centre (35.33, -111.283) +/- 0.05 deg.
BOX_OVERRIDES = {"S02": (35.28, 35.38, -111.333, -111.233)}

# evaluation track -> keywords searched in site_name (case-insensitive)
EVAL_TRACK = {
    "yuzey": ["Askja", "Kaʻū", "Kīlauea", "Teide", "Merriam", "Rio Grande",
              "Cinder Lake", "Black Point", "Haughton", "Peñas de Tao"],
    "malzeme": ["Mistastin", "Stillwater", "Lonar"],
    "surec": ["Meteor Crater", "Ries", "Sudbury"],
}


def norm_analog_to(raw):
    s = (raw or "").strip()
    if re.fullmatch(r"T_\w+", s):
        return s, False
    for pat, tid in ANALOG_TO_MAP:
        if re.search(pat, s, re.I):
            return tid, True
    return s, False


def track_of(site_name):
    name = (site_name or "").lower()
    hits = {tr for tr, keys in EVAL_TRACK.items() if any(k.lower() in name for k in keys)}
    if len(hits) != 1:
        raise SystemExit(f"[hata] eval_track belirsiz: {site_name!r} -> {sorted(hits) or 'eslesme yok'}. "
                         "prepare_t3.py icindeki EVAL_TRACK'i duzelt.")
    return hits.pop()


def read_rows(path, delim):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig", newline=""), delimiter=delim))
    return [r for r in rows if any((v or "").strip() for v in r.values())]


def main(src, dst, old=None, dims=None):
    rows = read_rows(src, ";")
    hdr = list(rows[0].keys())
    remapped = []
    for r in rows:
        for c in NUM_COLS:
            if c in r and r[c]:
                r[c] = r[c].strip().replace(",", ".")
        new, changed = norm_analog_to(r.get("analog_to"))
        if changed:
            remapped.append((r["site_id"], r["analog_to"], new))
        r["analog_to"] = new

    merged = []
    if old:
        taken = {r["site_id"] for r in rows}
        nxt = MERGE_ID_START
        for r in read_rows(old, ","):
            if not any(k.lower() in (r.get("site_name") or "").lower() for k in MERGE_SITES):
                continue
            old_id = r["site_id"]
            if old_id in taken:
                r["site_id"] = f"S{nxt:02d}"
                nxt += 1
            taken.add(r["site_id"])
            merged.append((old_id, r["site_id"], r["site_name"]))
            rows.append({c: r.get(c, "") for c in hdr})

    for r in rows:
        if r["site_id"] in BOX_OVERRIDES:
            r["lat_min"], r["lat_max"], r["lon_min"], r["lon_max"] = (str(x) for x in BOX_OVERRIDES[r["site_id"]])
            print(f"  kutu duzeltildi: {r['site_id']} {r['site_name'][:30]} -> {BOX_OVERRIDES[r['site_id']]}")

    hdr = hdr + ["eval_track"]
    for r in rows:
        r["eval_track"] = track_of(r.get("site_name"))

    dim_changes = []
    if dims:
        drows = {r["site_id"]: r for r in read_rows(dims, ",")}
        missing = [r["site_id"] for r in rows if r["site_id"] not in drows]
        if missing:
            raise SystemExit(f"[hata] boyut dosyasinda olmayan site_id: {missing}")
        hdr = hdr + ["dims"]
        for r in rows:
            d = drows[r["site_id"]]
            if d["analog_to"] != r["analog_to"]:
                dim_changes.append((r["site_id"], r["site_name"], r["analog_to"], d["analog_to"]))
                r["analog_to"] = d["analog_to"]
            if d.get("eval_track") and d["eval_track"] != r["eval_track"]:
                raise SystemExit(f"[hata] {r['site_id']} eval_track uyusmuyor: {r['eval_track']} vs {d['eval_track']}")
            r["dims"] = d["dims"]

    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    print(f"{src}" + (f" + {old}" if old else "") + f" -> {dst}")
    print(f"  {len(rows)} saha yazildi ({len(rows) - len(merged)} yeni tablo, {len(merged)} eski tablodan)")
    if remapped:
        print("  analog_to yeniden eslendi:")
        for sid, o, n in remapped:
            print(f"    {sid}: {o!r} -> {n}")
    if merged:
        print("  eski tablodan eklenenler:")
        for o, n, nm in merged:
            print(f"    {o} -> {n}  {nm}")
    if dims:
        print(f"  {dims}: dims eklendi; analog_to degisen: " + ("; ".join(f"{a} {n[:24]}: {o} -> {w}" for a, n, o, w in dim_changes) or "yok"))
    print("  analog_to dagilimi:", dict(Counter(r["analog_to"] for r in rows)))
    print("  eval_track dagilimi:", dict(Counter(r["eval_track"] for r in rows)))
    for tr in EVAL_TRACK:
        names = [r["site_name"][:34] for r in rows if r["eval_track"] == tr]
        print(f"    {tr:<8} ({len(names)}): {'; '.join(names)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default=os.path.join(DATA, "sources", "known_analogs_catalogue.csv"))
    ap.add_argument("--out", default=os.path.join(DATA, "known_analogs_moon.csv"))
    ap.add_argument("--first-round", default=os.path.join(DATA, "sources", "known_analogs_first_round.csv"))
    ap.add_argument("--dims", default=os.path.join(DATA, "known_site_dims.csv"))
    a = ap.parse_args()
    main(a.catalogue, a.out, a.first_round, a.dims)
