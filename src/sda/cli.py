"""CLI: python -m sda.cli --text '...' [--no-embeddings]."""
from __future__ import annotations

import argparse
import sys

from sda.config import MENTAL_HEALTH_DISEASES, TOP_K_CONDITIONS, TOP_K_DRUGS
from sda.inference.explain import format_explanation
from sda.pipeline import SymptomDrugAdvisor


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sda", description="Simptom-drug savetnik (nije dijagnoza).")
    p.add_argument("--text", default="", help="Opis simptoma na srpskom.")
    p.add_argument("--file", default="", help="Put do .txt fajla sa opisom.")
    p.add_argument("--no-embeddings", action="store_true", help="Offline TF-IDF put.")
    p.add_argument("--top-k-conditions", type=int, default=TOP_K_CONDITIONS)
    p.add_argument("--top-k-drugs", type=int, default=TOP_K_DRUGS)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = args.text.strip()
    if not text and args.file:
        try:
            with open(args.file, encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
        except OSError as exc:
            print(f"Greška pri čitanju fajla: {exc}", file=sys.stderr)
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        print('Primer: python -m sda.cli --text "boli me grlo i imam temperaturu 38"')
        return 2
    res = SymptomDrugAdvisor(not args.no_embeddings, args.no_embeddings).analyze(text)
    cands = res.candidates[:max(1, args.top_k_conditions)]
    drugs = res.drugs[:max(1, args.top_k_drugs)]

    print(f"Ulaz: {res.input_text}")
    print(f"Normalizovano: {res.normalized_text}")
    print(f"Režim: {'TF-IDF (offline)' if not res.used_embeddings else 'embeddings'}")
    print(f"\nEkstrahovani simptomi ({len(res.symptoms)}):")
    for m in res.symptoms or [None]:
        print("  (nema prepoznatih simptoma)" if m is None else
              f"  - {m.symptom_id} ({m.canonical_sr}) [metoda={m.method}, skor={m.score:.2f}] :: '{m.matched_text}'")
    if res.negated_symptoms:
        print(f"Negirani simptomi ({len(res.negated_symptoms)}):")
        for m in res.negated_symptoms:
            print(f"  - {m.symptom_id} ({m.canonical_sr}) :: '{m.matched_text}'")
    if res.red_flags:
        print("\nCRVENA ZASTAVICA — moguće hitno stanje:")
        for h in res.red_flags:
            print(f"  ! [{h.severity}] '{h.pattern_sr}' -> {h.action_message_sr}")
    print(f"\nTop-{len(cands)} rangirane hipoteze (condition_candidate):")
    if cands:
        for i, c in enumerate(cands, 1):
            print(f"  {i}. {c.disease_sr} [{c.disease_id}] — skor {c.score:.3f} "
                  f"(tipičnih: {c.typical_matched}, pogodaka: {len(c.matched_symptoms)})")
            print(f"     Obrazloženje: {format_explanation(c, res.explanations.get(c.disease_id, []))}")
    else:
        print("  (nema hipoteza)")
    print(f"\nPredloženi lekovi iz registra ({len(drugs)}):")
    if drugs:
        for i, d in enumerate(drugs, 1):
            r = d.record
            print(f"  {i}. {r.naziv_leka} | INN: {r.inn} | ATC: {r.atc} | "
                  f"{'OTC (bez recepta)' if r.is_otc() else 'Rx (na recept)'} | "
                  f"{'rešenje važi' if r.is_valid() else 'proveriti važenje'}")
            print(f"     Oblik/doza: {r.oblik_doza} | Nosilac: {r.nosilac} | Broj rešenja: {r.broj_resenja}")
            print(f"     Zašto: {d.reason} (skor {d.score:.3f})")
    elif res.red_flags:
        print("  (preskočeno zbog crvene zastavice — javite se lekaru / 194)")
    elif cands and cands[0].disease_id in MENTAL_HEALTH_DISEASES:
        print("  (za hipoteze iz područja mentalnog zdravlja lekovi se ne predlažu — javite se lekaru/psihologu)")
    else:
        print("  (nema predloga)")
    print(f"\nDisclaimer: {res.disclaimer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
