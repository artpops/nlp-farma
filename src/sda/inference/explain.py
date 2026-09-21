"""Obrazloženje: koliko je koji simptom doprineo hipotezi."""
from __future__ import annotations

from sda.models import ConditionCandidate, ExplanationItem, SymptomMention


def explain_candidates(candidates: list[ConditionCandidate],
                       symptoms: list[SymptomMention],
                       ranker=None) -> dict[str, list[ExplanationItem]]:
    scores: dict[str, float] = {}
    for m in symptoms:
        if not m.negated and m.score > scores.get(m.symptom_id, 0.0):
            scores[m.symptom_id] = m.score
    out: dict[str, list[ExplanationItem]] = {}
    for c in candidates:
        items: list[ExplanationItem] = []
        for sid in c.matched_symptoms:
            weight, note = 0.5, "doprinos bez matrice težina (aproksimacija)"
            try:
                rec = ranker.weight(c.disease_id, sid) if ranker is not None else None
            except Exception:
                rec = None
            if rec is not None:
                weight = float(rec.weight)
                note = "tipičan simptom za ovo stanje" if rec.is_typical else "prateći simptom za ovo stanje"
            else:
                weight = round(c.total_weight / max(1, len(c.matched_symptoms)), 4)
            items.append(ExplanationItem(
                sid, round(weight * scores.get(sid, 1.0) / (c.total_weight or 1.0) * c.score, 4),
                weight, note))
        out[c.disease_id] = sorted(items, key=lambda e: -e.contribution)
    return out


def format_explanation(candidate: ConditionCandidate, items: list[ExplanationItem]) -> str:
    if not items:
        return f"Hipoteza '{candidate.disease_sr}' nema mapirane doprinose (skor {candidate.score:.2f})."
    parts = ", ".join(f"{e.symptom_id} (w={e.weight:.2f})" for e in items[:4])
    return (f"Hipoteza '{candidate.disease_sr}' (skor {candidate.score:.2f}) "
            f"podržana je simptomima: {parts}. "
            f"Pogodaka tipičnih simptoma: {candidate.typical_matched}.")
