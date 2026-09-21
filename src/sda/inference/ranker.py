"""Rangiranje hipoteza stanja: skor = Σ(w·skor simptoma) / Σ(svih w)."""
from __future__ import annotations

import csv
from pathlib import Path

from sda.config import MIN_CONDITION_SCORE, TOP_K_CONDITIONS
from sda.models import ConditionCandidate, DiseaseSymptomWeight, SymptomMention


class ConditionRanker:
    def __init__(self, disease_symptoms_path: str | Path) -> None:
        self.path = Path(disease_symptoms_path)
        self._diseases: dict[str, dict] = {}
        with open(self.path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing = {"disease_id", "disease_sr", "symptom_id", "weight", "is_typical"} - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"disease_symptoms.csv nedostaju kolone: {sorted(missing)}")
            for row in reader:
                did, sid = (row.get("disease_id") or "").strip(), (row.get("symptom_id") or "").strip()
                if not did or not sid:
                    continue
                try:
                    w = max(0.0, min(1.0, float((row.get("weight") or "0.5").replace(",", "."))))
                except ValueError:
                    w = 0.5
                rec = DiseaseSymptomWeight(did, (row.get("disease_sr") or "").strip(), sid, w,
                    (row.get("is_typical") or "").strip().lower() in {"1", "true", "da", "yes", "y", "t"})
                d = self._diseases.setdefault(did, {"disease_sr": rec.disease_sr, "weights": {}})
                if sid not in d["weights"] or rec.weight > d["weights"][sid].weight:
                    d["weights"][sid] = rec
        if not self._diseases:
            raise ValueError(f"Prazna matrica: {self.path}")

    def all_diseases(self) -> list[tuple[str, str]]:
        return [(did, v["disease_sr"]) for did, v in self._diseases.items()]

    def weight(self, disease_id: str, symptom_id: str) -> DiseaseSymptomWeight | None:
        d = self._diseases.get(disease_id)
        return d["weights"].get(symptom_id) if d else None

    def total_weight(self, disease_id: str) -> float:
        d = self._diseases.get(disease_id)
        return float(sum(w.weight for w in d["weights"].values())) if d else 0.0

    def rank(self, symptoms: list[SymptomMention],
             top_k: int = TOP_K_CONDITIONS) -> list[ConditionCandidate]:
        scores: dict[str, float] = {}
        for m in symptoms:
            if not m.negated and m.score > scores.get(m.symptom_id, 0.0):
                scores[m.symptom_id] = m.score
        out: list[ConditionCandidate] = []
        for did, data in self._diseases.items():
            weights = data["weights"]
            total = sum(w.weight for w in weights.values())
            matched = [sid for sid in scores if sid in weights]
            if not matched or total <= 0:
                continue
            raw = sum(weights[s].weight * scores[s] for s in matched)
            typ = sum(1 for s in matched if weights[s].is_typical)
            score = min(1.0, raw / total + 0.01 * typ)
            if score >= MIN_CONDITION_SCORE:
                out.append(ConditionCandidate(did, data["disease_sr"], round(score, 4),
                                              sorted(matched), typ, round(raw, 4)))
        return sorted(out, key=lambda c: (-c.score, -c.typical_matched, c.disease_id))[:max(1, int(top_k))]
