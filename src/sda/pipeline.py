"""End-to-end: tekst -> simptomi -> hipoteze -> lekovi."""
from __future__ import annotations

from pathlib import Path

from sda import config as C
from sda.config import DISEASE_ATC_CSV, DISEASE_SYMPTOMS_CSV, RED_FLAGS_CSV, SYMPTOMS_CSV
from sda.drugs.recommender import DrugRecommender
from sda.drugs.registry import load_registry
from sda.inference.explain import explain_candidates
from sda.inference.ranker import ConditionRanker
from sda.models import PipelineResult
from sda.nlp.extractor import HybridExtractor
from sda.nlp.lexicon import load_symptom_lexicon
from sda.nlp.negation import mark_negations
from sda.safety.red_flags import RedFlagGuard
from sda.text.normalize import normalize_text

_CACHE: dict[bool, "SymptomDrugAdvisor"] = {}


class SymptomDrugAdvisor:
    def __init__(self, use_embeddings: bool = True, no_embeddings: bool = False,
                 symptoms_csv: str | Path = SYMPTOMS_CSV,
                 disease_symptoms_csv: str | Path = DISEASE_SYMPTOMS_CSV,
                 disease_atc_csv: str | Path = DISEASE_ATC_CSV,
                 red_flags_csv: str | Path = RED_FLAGS_CSV,
                 lekovi_path: str | Path | None = None) -> None:
        self.lexicon = load_symptom_lexicon(symptoms_csv)
        self.extractor = HybridExtractor(self.lexicon, use_embeddings, no_embeddings)
        self.ranker = ConditionRanker(disease_symptoms_csv)
        self.guard = RedFlagGuard(red_flags_csv)
        self.registry = load_registry(lekovi_path)
        self.recommender = DrugRecommender(self.registry, disease_atc_csv)

    @property
    def used_embeddings(self) -> bool:
        return False

    def analyze(self, text: str) -> PipelineResult:
        raw, norm = text or "", normalize_text(text or "")
        mentions = self.extractor.extract(raw) if raw.strip() else []
        positive, negated = mark_negations(raw, mentions)
        flags = self.guard.check(raw)
        candidates = self.ranker.rank(positive)
        explanations = explain_candidates(candidates, positive, ranker=self.ranker)
        mental = bool(candidates and candidates[0].disease_id in C.MENTAL_HEALTH_DISEASES)
        drugs = [] if (flags or mental) else self._drugs(candidates)
        disclaimer = C.DISCLAIMER_SR
        if flags:
            disclaimer = C.RED_FLAG_BANNER_SR + " " + disclaimer
        if mental and not flags:
            disclaimer = C.MENTAL_REFERRAL_SR + " " + disclaimer
        return PipelineResult(raw, norm, positive, negated, candidates,
                              explanations, flags, drugs, disclaimer, False)

    def _drugs(self, candidates):
        try:
            return self.recommender.recommend(candidates)
        except Exception:
            return []


def analyze_text(text: str, no_embeddings: bool = False) -> PipelineResult:
    key = bool(no_embeddings)
    if key not in _CACHE:
        _CACHE[key] = SymptomDrugAdvisor(not key, key)
    return _CACHE[key].analyze(text)


def clear_cache() -> None:
    _CACHE.clear()
