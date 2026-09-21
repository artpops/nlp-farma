"""Lekovi iz registra za rangirane hipoteze (OTC-first, raznovrsno)."""
from __future__ import annotations

import csv
from pathlib import Path

from sda.config import TOP_K_DRUGS
from sda.drugs.registry import (
    DrugRegistry,
    atc_matches,
    filter_by_atc,
    normalize_atc,
)
from sda.models import ConditionCandidate, DiseaseAtcMap, DrugCandidate


class DrugRecommender:
    def __init__(self, registry: DrugRegistry, disease_atc_path: str | Path) -> None:
        self.registry = registry
        self.path = Path(disease_atc_path)
        self._map: dict[str, list[DiseaseAtcMap]] = {}
        with open(self.path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing = {"disease_id", "atc_prefix", "therapy_role", "otc_preferred", "note"} - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"disease_atc.csv nedostaju kolone: {sorted(missing)}")
            for row in reader:
                did = (row.get("disease_id") or "").strip()
                prefix = (row.get("atc_prefix") or "").strip().upper()
                if not did or not prefix:
                    continue
                role = (row.get("therapy_role") or "symptomatic").strip().lower()
                self._map.setdefault(did, []).append(DiseaseAtcMap(
                    disease_id=did,
                    atc_prefix=prefix,
                    therapy_role=role if role in {"symptomatic", "causal"} else "symptomatic",
                    otc_preferred=(row.get("otc_preferred") or "").strip().lower() in {"1", "true", "da", "yes", "y", "t"},
                    note=(row.get("note") or "").strip(),
                ))
        if not self._map:
            raise ValueError(f"Prazan disease_atc.csv: {self.path}")

    def prefixes_for(self, disease_id: str) -> list[str]:
        return [m.atc_prefix for m in self._map.get(disease_id, [])]

    def recommend(self, candidates: list[ConditionCandidate],
                  top_k: int = TOP_K_DRUGS) -> list[DrugCandidate]:
        # Dedup po proizvodu (pakovanje se ignoriše) + max 2 po ATC grupi,
        # inače brojni N02BE zapisi preplave top listu.
        if not candidates:
            return []
        scored: dict[tuple[str, str], DrugCandidate] = {}
        group_of: dict[tuple[str, str], str] = {}
        for rank_pos, cond in enumerate(candidates):
            maps = self._map.get(cond.disease_id, [])
            if not maps:
                continue
            roles = {m.atc_prefix: m.therapy_role for m in maps}
            otc_any = any(m.otc_preferred for m in maps)
            for drug in filter_by_atc(self.registry.all(), [m.atc_prefix for m in maps]):
                otc, valid = drug.is_otc(), drug.is_valid()
                base = float(cond.score) / (1.0 + 0.3 * rank_pos)
                otc_bonus = (0.20 if otc else -0.15) if otc_any else (0.05 if otc else 0.0)
                role, hit = "", ""
                for pfx, r in roles.items():
                    if atc_matches(drug.atc, pfx):
                        role, hit = r, normalize_atc(pfx)
                        break
                score = round(base + otc_bonus + (0.10 if valid else -1.0)
                              + (0.03 if role == "symptomatic" else 0.0), 4)
                reason = (
                    f"Za hipotezu '{cond.disease_sr}' ({cond.disease_id}, "
                    f"skor {cond.score:.2f}), ATC {drug.atc} "
                    f"({'OTC' if otc else 'Rx, izdaje se na recept'}; "
                    f"{'rešenje važi' if valid else 'proveriti važenje rešenja'}"
                    f"{'; ' + role if role else ''})"
                )
                key = (drug.naziv_leka.strip().lower(), normalize_atc(drug.atc))
                if key not in scored or score > scored[key].score:
                    scored[key] = DrugCandidate(record=drug, score=score, reason=reason)
                    group_of[key] = hit or normalize_atc(drug.atc)[:5]
        ranked = sorted(scored.values(), key=lambda d: (-d.score, d.record.naziv_leka))
        by_group: dict[str, list[DrugCandidate]] = {}
        for d in ranked:
            g = group_of[(d.record.naziv_leka.strip().lower(), normalize_atc(d.record.atc))]
            by_group.setdefault(g, []).append(d)
        out: list[DrugCandidate] = []
        k = max(1, int(top_k))
        used = {g: 0 for g in by_group}
        while len(out) < k:
            progressed = False
            for g, lst in by_group.items():
                if len(out) >= k or used[g] >= 2 or used[g] >= len(lst):
                    continue
                out.append(lst[used[g]])
                used[g] += 1
                progressed = True
            if not progressed:
                break
        if len(out) < k:
            seen = {(d.record.naziv_leka, d.record.atc) for d in out}
            for d in ranked:
                if len(out) >= k:
                    break
                if (d.record.naziv_leka, d.record.atc) not in seen:
                    out.append(d)
                    seen.add((d.record.naziv_leka, d.record.atc))
        return out
