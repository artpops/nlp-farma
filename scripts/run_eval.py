"""Evaluacija nad test skupom: metrike + CSV + PNG (offline, bez mreže)."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sda.config import (
    REPORTS_FIGURES_DIR,
    REPORTS_RESULTS_DIR,
    TEST_CASES_JSONL,
    ensure_dirs,
)
from sda.pipeline import SymptomDrugAdvisor


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return round(p, 4), round(r, 4), round(f, 4)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Eval: simptomi (P/R/F1) + bolest (top1/top3).")
    ap.add_argument("--no-embeddings", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="0 = ceo skup")
    ap.add_argument("--cases", type=str, default=str(TEST_CASES_JSONL))
    args = ap.parse_args(argv)
    ensure_dirs()
    cases = []
    with open(args.cases, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    if args.limit and args.limit > 0:
        cases = cases[: args.limit]
    advisor = SymptomDrugAdvisor(
        use_embeddings=not args.no_embeddings,
        no_embeddings=bool(args.no_embeddings),
    )
    per_case: list[dict] = []
    tp = fp = fn = 0
    top1 = top3 = 0
    for i, c in enumerate(cases):
        text = c.get("text_sr", "")
        gold_s = set(c.get("gold_symptoms", []))
        gold_d = c.get("gold_disease", "")
        try:
            res = advisor.analyze(text)
        except Exception as exc:
            per_case.append({
                "id": i, "text_sr": text, "gold_disease": gold_d,
                "gold_symptoms": "|".join(sorted(gold_s)),
                "pred_symptoms": "", "pred_top1": "", "pred_top3": "",
                "sym_hit": 0, "sym_pred": 0, "sym_gold": len(gold_s),
                "top1_hit": 0, "top3_hit": 0, "error": str(exc),
            })
            fn += len(gold_s)
            continue
        pred_s = {m.symptom_id for m in res.symptoms}
        hit = len(pred_s & gold_s)
        tp += hit
        fp += len(pred_s - gold_s)
        fn += len(gold_s - pred_s)
        top1_pred = res.candidates[0].disease_id if res.candidates else ""
        top3_pred = [x.disease_id for x in res.candidates[:3]]
        h1 = 1 if top1_pred == gold_d else 0
        h3 = 1 if gold_d in top3_pred else 0
        top1 += h1
        top3 += h3
        per_case.append({
            "id": i, "text_sr": text, "gold_disease": gold_d,
            "gold_symptoms": "|".join(sorted(gold_s)),
            "pred_symptoms": "|".join(sorted(pred_s)),
            "pred_top1": top1_pred, "pred_top3": "|".join(top3_pred),
            "sym_hit": hit, "sym_pred": len(pred_s), "sym_gold": len(gold_s),
            "top1_hit": h1, "top3_hit": h3, "error": "",
        })
    n = max(1, len(cases))
    p, r, f = prf(tp, fp, fn)
    acc1 = round(top1 / n, 4)
    acc3 = round(top3 / n, 4)
    mode = "tfidf-offline"
    summary = [{
        "n": n, "mode": mode,
        "sym_precision": p, "sym_recall": r, "sym_f1": f,
        "disease_top1": acc1, "disease_top3": acc3,
        "sym_tp": tp, "sym_fp": fp, "sym_fn": fn,
    }]
    per_path = REPORTS_RESULTS_DIR / "per_case.csv"
    sum_path = REPORTS_RESULTS_DIR / "summary.csv"
    with open(per_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_case[0].keys()))
        w.writeheader()
        w.writerows(per_case)
    with open(sum_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)
    # figure 1: metrike
    fig1 = REPORTS_FIGURES_DIR / "metrics.png"
    labels = ["P(sym)", "R(sym)", "F1(sym)", "Top-1", "Top-3"]
    vals = [p, r, f, acc1, acc3]
    plt.figure(figsize=(7, 4))
    bars = plt.bar(labels, vals)
    plt.ylim(0, 1.0)
    plt.title(f"Eval metrike ({mode}, n={n})")
    for b, v in zip(bars, vals):
        plt.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02,
                 f"{v:.2f}", ha="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(fig1, dpi=150)
    plt.close()
    # figure 2: raspodela broja prediktovanih simptoma
    fig2 = REPORTS_FIGURES_DIR / "pred_counts.png"
    counts = [len(str(x["pred_symptoms"]).split("|")) if x["pred_symptoms"] else 0 for x in per_case]
    plt.figure(figsize=(7, 4))
    plt.hist(counts, bins=range(0, max(8, max(counts + [1]) + 1)), align="left", rwidth=0.8)
    plt.xlabel("br. prediktovanih simptoma / slučaj")
    plt.ylabel("br. slučajeva")
    plt.title("Raspodela ekstrakcije")
    plt.tight_layout()
    plt.savefig(fig2, dpi=150)
    plt.close()
    print(f"Eval ({mode}) n={n}: P={p} R={r} F1={f} top1={acc1} top3={acc3}")
    print(f"CSV: {per_path}, {sum_path}")
    print(f"PNG: {fig1}, {fig2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
