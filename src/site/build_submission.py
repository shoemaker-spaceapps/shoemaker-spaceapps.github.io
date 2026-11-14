#!/usr/bin/env python3
"""Render README.md and the submission texts from templates, results/ and src/team.json.

Usage: python src/site/build_submission.py
"""
import json
import os
import string

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TPL = os.path.join(os.path.dirname(__file__), "templates")
NAMES = {"T_mare": "Mare (Apollo 11)", "T_imbrium": "Imbrium rim (Apollo 15)", "T_highland": "Highlands (Apollo 16), low confidence",
         "T_nobile": "Nobile crater area"}
ARTEMIS = ["T_n2", "T_mm", "T_ma", "T_g2", "T_mp", "T_sp", "T_cb", "T_n1", "T_hw"]


def robust_lines(rb):
    out = []
    for tid, label in NAMES.items():
        g = rb[rb.target_id == tid].sort_values("rank_sum").head(3)
        out.append(f"  - {label}: " + "; ".join(f"{r.region} ({r.lat:.3f}, {r.lon:.3f})" for r in g.itertuples()))
    art = rb[rb.target_id.isin(ARTEMIS)].region.value_counts()
    out.append(f"  - Artemis III regions, terrain only: {art.index[0]} ({art.iloc[0]} of {art.sum()} candidates), "
               "then " + "; ".join(art.index[1:5]))
    return "\n".join(out)


def water_line(w):
    w = w[(w.target_id == "T_nobile") & (w.lesser_known == 1)]
    part = []
    for grp, what in [("Dry-surface analog", "dry-surface analogs"), ("Ice-bearing analog", "ice-bearing analogs"),
                      ("Terrain analog", "terrain analogs")]:
        regs = w[w.group == grp].sort_values("best_score", ascending=False).region.head(2).tolist()
        if regs:
            part.append(f"{what} such as {' and '.join(regs)}")
    return "; ".join(part) + ". Each region comes with a one-line reading and a concrete ISRU test."


def main():
    nums = json.load(open(os.path.join(ROOT, "docs", "data", "numbers.json"), encoding="utf-8"))
    team = json.load(open(os.path.join(ROOT, "src", "team.json"), encoding="utf-8"))
    rb = pd.read_csv(os.path.join(ROOT, "results", "robust_candidates.csv"))
    w = pd.read_csv(os.path.join(ROOT, "results", "water_ice.csv"))
    vals = dict(nums, team_md="\n".join(f"- {m['name']}: {m['role']}" for m in team["members"]),
                demo_pdf=team["site_url"] + "demo/demo.pdf", site_host=team["site_url"].replace("https://", "").rstrip("/"),
                robust_md=robust_lines(rb), water_md=water_line(w))
    out = {"readme.md": os.path.join(ROOT, "README.md"),
           "project_page.md": os.path.join(ROOT, "submission", "project_page.md"),
           "judge_faq.md": os.path.join(ROOT, "submission", "judge_faq.md"),
           "video_script_30s.md": os.path.join(ROOT, "submission", "video_script_30s.md")}
    for src, dst in out.items():
        tpl = string.Template(open(os.path.join(TPL, src), encoding="utf-8").read())
        open(dst, "w", encoding="utf-8").write(tpl.substitute(vals))
    print("written:", ", ".join(os.path.relpath(p, ROOT) for p in out.values()))


if __name__ == "__main__":
    main()
