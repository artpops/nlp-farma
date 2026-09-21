"""Ekstrakcija simptoma: rečnik + fuzzy + TF-IDF. Sve radi offline."""
from __future__ import annotations

import re

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sda.config import FUZZY_THRESHOLD, SEMANTIC_THRESHOLD
from sda.models import SymptomMention
from sda.nlp.lexicon import SymptomLexicon
from sda.text.normalize import normalize_text


class HybridExtractor:
    def __init__(
        self,
        lexicon: SymptomLexicon,
        use_embeddings: bool = True,
        no_embeddings: bool = False,
        fuzzy_threshold: int = FUZZY_THRESHOLD,
        semantic_threshold: float = SEMANTIC_THRESHOLD,
    ) -> None:
        self.lexicon = lexicon
        self.fuzzy_threshold = int(fuzzy_threshold)
        self.semantic_threshold = float(semantic_threshold)
        self._forms: list[tuple[str, str, str, str]] = []
        for e in lexicon.all_entries():
            for form in e.all_forms():
                norm = normalize_text(form)
                if norm:
                    self._forms.append((e.symptom_id, e.canonical_sr, form, norm))
        reps = [" ".join(e.all_forms()[:4]) for e in lexicon.all_entries()]
        self._rep_ids = [e.symptom_id for e in lexicon.all_entries()]
        self._rep_canon = {e.symptom_id: e.canonical_sr for e in lexicon.all_entries()}
        self._vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1)
        self._rep_matrix = self._vectorizer.fit_transform(
            [normalize_text(r) or " " for r in reps]
        )

    @property
    def used_embeddings(self) -> bool:
        return False

    def _gazetteer(self, norm_text: str) -> list[SymptomMention]:
        found: dict[str, SymptomMention] = {}
        for sid, canon, form, norm_form in self._forms:
            if sid in found:
                continue
            pat = r"(?<![a-z0-9])" + re.escape(norm_form) + r"(?![a-z0-9])"
            if re.search(pat, norm_text):
                found[sid] = SymptomMention(sid, canon, form, False, 1.0, "gazetteer")
        return list(found.values())

    def _fuzzy(self, norm_text: str, already: set[str]) -> list[SymptomMention]:
        tokens = norm_text.split()
        if not tokens:
            return []
        windows: list[str] = []
        for n in (1, 2, 3, 4):
            for i in range(max(0, len(tokens) - n + 1)):
                w = " ".join(tokens[i : i + n])
                if len(w) >= 4:
                    windows.append(w)
        windows = windows[:120]
        if not windows:
            return []
        best: dict[str, SymptomMention] = {}
        for sid, canon, form, norm_form in self._forms:
            if sid in already or sid in best or len(norm_form) < 4:
                continue
            max_diff = max(4, len(norm_form) // 3)
            top, top_win = 0.0, ""
            for w in windows:
                if abs(len(w) - len(norm_form)) > max_diff:
                    continue
                s = fuzz.ratio(norm_form, w)
                if s > top:
                    top, top_win = float(s), w
                    if top >= 100.0:
                        break
            if top >= self.fuzzy_threshold:
                best[sid] = SymptomMention(
                    sid, canon, top_win or form, False, round(top / 100.0, 3), "fuzzy"
                )
        return list(best.values())

    def _semantic(self, norm_text: str, already: set[str]) -> list[SymptomMention]:
        idx = [i for i, sid in enumerate(self._rep_ids) if sid not in already]
        if not idx:
            return []
        try:
            q = self._vectorizer.transform([norm_text])
            sims = cosine_similarity(q, self._rep_matrix[idx])[0]
        except Exception:
            return []
        return [
            SymptomMention(sid, self._rep_canon[sid], norm_text[:60], False, round(float(s), 3), "semantic")
            for sid, s in zip([self._rep_ids[i] for i in idx], sims)
            if s >= self.semantic_threshold
        ]

    def extract(self, text: str) -> list[SymptomMention]:
        if not text or not text.strip():
            return []
        norm_text = normalize_text(text)
        if not norm_text:
            return []
        gaz = self._gazetteer(norm_text)
        already = {m.symptom_id for m in gaz}
        fuzzy = self._fuzzy(norm_text, already)
        already |= {m.symptom_id for m in fuzzy}
        sem = self._semantic(norm_text, already)
        merged: dict[str, SymptomMention] = {}
        for m in gaz + fuzzy + sem:
            prev = merged.get(m.symptom_id)
            if prev is None or m.score > prev.score:
                merged[m.symptom_id] = m
        return sorted(merged.values(), key=lambda m: (-m.score, m.symptom_id))
