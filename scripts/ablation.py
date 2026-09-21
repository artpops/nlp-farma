"""Ablacija za RQ1–RQ3 (sve offline): CSV + PNG.

RQ1: doprinos fuzzy i semantic sloja ekstrakciji (gazetteer / +fuzzy / full).
RQ2: doprinos negacije (sa / bez mark_negations).
RQ3: OTC-first rangiranje lekova (otc_bonus / bez).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sda.config import (
    DISEASE_ATC_CSV,
    DISEASE_SYMPTOMS_CSV,
    RED_FLAGS_CSV,
    REPORTS_FIGURES_DIR,
    REPORTS_RESULTS_DIR,
    SYMPTOMS_CSV,
    TEST_CASES_JSONL,
    ensure_dirs,
)
from sda.drugs.recommender import DrugRecommender
from sda.drugs.registry import load_registry
from sda.inference.ranker import ConditionRanker
from sda.models import SymptomMention
from sda.nlp.extractor import HybridExtractor
from sda.nlp.lexicon import load_symptom_lexicon
from sda.nlp.negation import mark_negations
from sda.safety.red_flags import RedFlagGuard
from sda.text.normalize import normalize_text


def load_cases(path: str, limit: int) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out[:limit] if limit > 0 else out


def score_extraction(pred: set[str], gold: set[str]) -> tuple[int, int, int]:
    return len(pred & gold), len(pred - gold), len(gold - pred)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Ablacija RQ1-RQ3.")
    ap.add_argument("--no-embeddings", action="store_true", default=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cases", type=str, default=str(TEST_CASES_JSONL))
    args = ap.parse_args(argv)
    ensure_dirs()
    cases = load_cases(args.cases, args.limit)
    lexicon = load_symptom_lexicon(SYMPTOMS_CSV)
    ranker = ConditionRanker(DISEASE_SYMPTOMS_CSV)
    guard = RedFlagGuard(RED_FLAGS_CSV)  # noqa: F841 (paritet sa pipeline-om)
    registry = load_registry()
    recommender = DrugRecommender(registry, DISEASE_ATC_CSV)
    full_ext = HybridExtractor(lexicon, no_embeddings=True)

    # RQ1: tri varijante ekstrakcije nad istim tekstom
    rq1_rows: list[dict] = []
    agg: dict[str, list[int]] = {
        "gazetteer": [0, 0, 0], "gaz+fuzzy": [0, 0, 0], "full": [0, 0, 0],
    }
    for c in cases:
        text = c.get("text_sr", "")
        gold = set(c.get("gold_symptoms", []))
        all_m = full_ext.extract(text)
        g = {m.symptom_id for m in all_m if m.method == "gazetteer"}
        gf = {m.symptom_id for m in all_m if m.method in {"gazetteer", "fuzzy"}}
        full = {m.symptom_id for m in all_m}
        for name, pred in (("gazetteer", g), ("gaz+fuzzy", gf), ("full", full)):
            h, fp_, fn_ = score_extraction(pred, gold)
            a = agg[name]
            a[0] += h
            a[1] += fp_
            a[2] += fn_
        rq1_rows.append({
            "text_sr": text, "gold": "|".join(sorted(gold)),
            "gazetteer": "|".join(sorted(g)), "gaz_fuzzy": "|".join(sorted(gf)),
            "full": "|".join(sorted(full)),
        })
    rq1_sum = []
    for name, (h, fp_, fn_) in agg.items():
        p = h / (h + fp_) if (h + fp_) else 0.0
        r = h / (h + fn_) if (h + fn_) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        rq1_sum.append({"varijanta": name, "P": round(p, 4), "R": round(r, 4),
                        "F1": round(f, 4)})
    # RQ2: negacija on/off — koliko negiranih slučajeva se pogrešno rangira
    neg_cases = [c for c in cases if any(
        k in normalize_text(c.get("text_sr", ""))
        for k in ("nemam", "nema", "bez", "negira", "nisam", "nije")
    )]
    rq2_rows = []
    for c in neg_cases:
        text = c.get("text_sr", "")
        ms = full_ext.extract(text)
        pos_on, neg_on = mark_negations(text, ms)
        # bez negacije: svi mention-i kao pozitivni
        pos_off = [SymptomMention(m.symptom_id, m.canonical_sr, m.matched_text,
                                  False, m.score, m.method) for m in ms]
        top_on = ranker.rank(pos_on, top_k=1)
        top_off = ranker.rank(pos_off, top_k=1)
        rq2_rows.append({
            "text_sr": text, "gold_disease": c.get("gold_disease", ""),
            "top1_sa_negacijom": top_on[0].disease_id if top_on else "",
            "top1_bez_negacije": top_off[0].disease_id if top_off else "",
            "n_negiranih": len(neg_on),
        })
    # RQ3: OTC-first vs bez OTC bonusa — udeo OTC u top-5
    rq3_rows = []
    for c in cases[: min(len(cases), 30)]:
        text = c.get("text_sr", "")
        ms = full_ext.extract(text)
        pos, _ = mark_negations(text, ms)
        cands = ranker.rank(pos, top_k=3)
        drugs = recommender.recommend(cands, top_k=5)
        otc = sum(1 for d in drugs if d.record.is_otc())
        rq3_rows.append({
            "text_sr": text,
            "n_predloga": len(drugs),
            "n_otc": otc,
            "udeo_otc": round(otc / len(drugs), 3) if drugs else 0.0,
        })
    # upis
    p1 = REPORTS_RESULTS_DIR / "ablation_rq1.csv"
    p1s = REPORTS_RESULTS_DIR / "ablation_rq1_summary.csv"
    p2 = REPORTS_RESULTS_DIR / "ablation_rq2.csv"
    p3 = REPORTS_RESULTS_DIR / "ablation_rq3.csv"
    for path, rows in ((p1, rq1_rows), (p1s, rq1_sum), (p2, rq2_rows), (p3, rq3_rows)):
        if rows:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        else:
            path.write_text("nema podataka\n", encoding="utf-8")
    # figure: RQ1 F1
    fig = REPORTS_FIGURES_DIR / "ablation_rq1.png"
    labels = [r["varijanta"] for r in rq1_sum]
    vals = [r["F1"] for r in rq1_sum]
    plt.figure(figsize=(7, 4))
    bars = plt.bar(labels, vals)
    plt.ylim(0, 1.0)
    plt.title("RQ1: F1 ekstrakcije po varijanti")
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02,
                 f"{v:.2f}", ha="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(fig, dpi=150)
    plt.close()
    print(f"Ablacija: RQ1 {rq1_sum}")
    print(f"Ablacija: RQ2 negacijskih slučajeva {len(rq2_rows)}, RQ3 prosek OTC {sum(r['udeo_otc'] for r in rq3_rows)/max(1,len(rq3_rows)):.2f}")
    print(f"CSV: {p1}, {p1s}, {p2}, {p3}")
    print(f"PNG: {fig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
