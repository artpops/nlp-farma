"""Registar lekova (puni lekovi.json ili uzorak) + ATC filtriranje."""
from __future__ import annotations

import json
import re
from pathlib import Path

from sda.config import OTC_REZIMI, active_lekovi_path
from sda.models import DrugRecord

_ATC_CLEAN_RE = re.compile(r"[^A-Z0-9]")


def normalize_atc(code: str) -> str:
    return _ATC_CLEAN_RE.sub("", (code or "").strip().upper())


def atc_matches(code: str, prefix: str) -> bool:
    c, p = normalize_atc(code), normalize_atc(prefix)
    return bool(c and p) and c.startswith(p)


def is_otc(record: DrugRecord) -> bool:
    return (record.rezim or "").strip().upper() in OTC_REZIMI


def filter_by_atc(drugs: list[DrugRecord], prefixes: list[str]) -> list[DrugRecord]:
    want = [p for p in (normalize_atc(x) for x in prefixes) if p]
    if not want:
        return []
    return [d for d in drugs if any(normalize_atc(d.atc).startswith(p) for p in want)]


def _get(d: dict, *keys: str) -> str:
    for k in keys:
        if d.get(k) not in (None, ""):
            return str(d[k]).strip()
    return ""


def record_from_raw(raw: dict) -> DrugRecord:
    return DrugRecord(
        naziv_leka=_get(raw, "nazivLeka", "naziv_leka", "naziv", "name"),
        inn=_get(raw, "inn", "INN", "genericki_naziv"),
        rezim=_get(raw, "rezimIzdavanjaLeka", "rezim", "rezim_izdavanja").upper(),
        oblik_doza=_get(raw, "oblikIDozaLeka", "oblik_doza", "oblikDoza"),
        broj_resenja=_get(raw, "brojResenjaOStavljanjuLekaUPromet", "broj_resenja", "brojResenja"),
        datum_resenja=_get(raw, "datumResenjaOStavljanjuLekaUPromet", "datum_resenja", "datumResenja"),
        datum_vazenja=_get(raw, "datumVazenjaResenja", "datum_vazenja", "datumVazenja"),
        proizvodjac=_get(raw, "proizvodjac", "manufacturer"),
        nosilac=_get(raw, "nosilacDozvole", "nosilac", "nosilac_dozvole"),
        atc=_get(raw, "atc", "ATC", "atc_kod").upper(),
        ean=_get(raw, "ean", "EAN"),
        jkl=_get(raw, "jkl", "JKL"),
        vrsta_leka=_get(raw, "vrstaLeka", "vrsta_leka", "vrsta"),
    )


class DrugRegistry:
    def __init__(self, records: list[DrugRecord], source: str = "") -> None:
        self._records = list(records)
        self.source = source

    def __len__(self) -> int:
        return len(self._records)

    def all(self) -> list[DrugRecord]:
        return list(self._records)

    def find_by_atc(self, prefix: str) -> list[DrugRecord]:
        return [r for r in self._records if atc_matches(r.atc, prefix or "")]

    @classmethod
    def from_json(cls, path: str | Path) -> "DrugRegistry":
        path = Path(path)
        with open(path, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, dict) and "lekovi" in data:
            raw_list = data["lekovi"]
        elif isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict) and "drugs" in data:
            raw_list = data["drugs"]
        else:
            raise ValueError(f"Nepoznat format registra: {path}")
        records = [r for r in (record_from_raw(x) for x in raw_list if isinstance(x, dict))
                   if r.naziv_leka and r.atc]
        if not records:
            raise ValueError(f"Registar bez upotrebljivih zapisa: {path}")
        return cls(records, source=str(path))


def load_registry(path: str | Path | None = None) -> DrugRegistry:
    return DrugRegistry.from_json(Path(path) if path is not None else active_lekovi_path())
