"""Leksikon simptoma iz CSV-a."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from sda.models import SymptomEntry
from sda.text.normalize import normalize_text


@dataclass
class SymptomLexicon:
    entries: list[SymptomEntry] = field(default_factory=list)
    index: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    by_id: dict[str, SymptomEntry] = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.entries)

    def all_entries(self) -> list[SymptomEntry]:
        return list(self.entries)

    def get(self, symptom_id: str) -> SymptomEntry | None:
        return self.by_id.get(symptom_id)

    def forms_for(self, symptom_id: str) -> list[str]:
        e = self.by_id.get(symptom_id)
        return e.all_forms() if e else []


def _split(raw: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in (raw or "").replace(";", "|").split("|") if p.strip())


def load_symptom_lexicon(path: str | Path) -> SymptomLexicon:
    lex = SymptomLexicon()
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = {"symptom_id", "canonical_sr", "synonyms_sr", "colloquial_sr",
                   "icd10_hint", "body_system"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"symptoms_sr.csv nedostaju kolone: {sorted(missing)}")
        for row in reader:
            sid, canon = (row.get("symptom_id") or "").strip(), (row.get("canonical_sr") or "").strip()
            if not sid or not canon:
                continue
            entry = SymptomEntry(sid, canon, _split(row.get("synonyms_sr") or ""),
                                 _split(row.get("colloquial_sr") or ""),
                                 (row.get("icd10_hint") or "").strip(),
                                 (row.get("body_system") or "").strip())
            lex.entries.append(entry)
            lex.by_id[sid] = entry
            for form in entry.all_forms():
                key = normalize_text(form)
                if key and key not in lex.index:
                    lex.index[key] = (sid, canon, form)
    if not lex.entries:
        raise ValueError(f"Prazan leksikon: {path}")
    return lex
