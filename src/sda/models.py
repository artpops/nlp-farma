"""Tipovi podataka."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SymptomEntry:
    symptom_id: str
    canonical_sr: str
    synonyms: tuple[str, ...] = ()
    colloquial: tuple[str, ...] = ()
    icd10_hint: str = ""
    body_system: str = ""

    def all_forms(self) -> list[str]:
        out: list[str] = []
        for f in (self.canonical_sr, *self.synonyms, *self.colloquial):
            f = (f or "").strip()
            if f and f not in out:
                out.append(f)
        return out


@dataclass(frozen=True)
class DiseaseSymptomWeight:
    disease_id: str
    disease_sr: str
    symptom_id: str
    weight: float
    is_typical: bool


@dataclass(frozen=True)
class DiseaseAtcMap:
    disease_id: str
    atc_prefix: str
    therapy_role: str  # symptomatic | causal
    otc_preferred: bool
    note: str


@dataclass(frozen=True)
class RedFlagRule:
    pattern_sr: str
    severity: str
    action_message_sr: str


@dataclass
class SymptomMention:
    symptom_id: str
    canonical_sr: str
    matched_text: str
    negated: bool = False
    score: float = 1.0
    method: str = "gazetteer"  # gazetteer | fuzzy | semantic


@dataclass
class ConditionCandidate:
    disease_id: str
    disease_sr: str
    score: float
    matched_symptoms: list[str] = field(default_factory=list)
    typical_matched: int = 0
    total_weight: float = 0.0


@dataclass
class ExplanationItem:
    symptom_id: str
    contribution: float
    weight: float
    note: str


@dataclass
class RedFlagHit:
    pattern_sr: str
    severity: str
    action_message_sr: str
    matched_text: str


@dataclass
class DrugRecord:
    naziv_leka: str
    inn: str
    rezim: str
    oblik_doza: str
    broj_resenja: str
    datum_resenja: str
    datum_vazenja: str
    proizvodjac: str
    nosilac: str
    atc: str
    ean: str
    jkl: str
    vrsta_leka: str

    def is_otc(self) -> bool:
        from sda.config import OTC_REZIMI

        return (self.rezim or "").strip().upper() in OTC_REZIMI

    def is_valid(self) -> bool:
        from datetime import date, datetime

        raw = (self.datum_vazenja or "").strip()
        if not raw:
            return False
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                if datetime.strptime(raw[:10], fmt).date() >= date.today():
                    return True
                return False
            except ValueError:
                continue
        return bool(self.broj_resenja)


@dataclass
class DrugCandidate:
    record: DrugRecord
    score: float
    reason: str


@dataclass
class PipelineResult:
    input_text: str
    normalized_text: str
    symptoms: list[SymptomMention] = field(default_factory=list)
    negated_symptoms: list[SymptomMention] = field(default_factory=list)
    candidates: list[ConditionCandidate] = field(default_factory=list)
    explanations: dict[str, list[ExplanationItem]] = field(default_factory=dict)
    red_flags: list[RedFlagHit] = field(default_factory=list)
    drugs: list[DrugCandidate] = field(default_factory=list)
    disclaimer: str = ""
    used_embeddings: bool = False
