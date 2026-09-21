"""Validacija i sanity-check knowledge fajlova. Izlaz 0 = sve OK."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from sda.config import (
    DISEASE_ATC_CSV,
    DISEASE_SYMPTOMS_CSV,
    LEKOVI_SAMPLE_JSON,
    RED_FLAGS_CSV,
    SYMPTOMS_CSV,
    TEST_CASES_JSONL,
)

ATC_RE = re.compile(r"^[A-Z]([0-9]{2}[A-Z]{0,2})?([A-Z]{0,2}[0-9]{0,2})?$")
ERRORS: list[str] = []


def fail(msg: str) -> None:
    ERRORS.append(msg)
    print(f"FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"OK: {msg}")


def check_csv(path: Path, required: set[str], minimum: int, name: str) -> list[dict]:
    if not path.is_file():
        fail(f"{name} ne postoji: {path}")
        return []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            fail(f"{name} nedostaju kolone {sorted(missing)}")
            return []
        rows = [r for r in reader if any((v or "").strip() for v in r.values())]
    if len(rows) < minimum:
        fail(f"{name} ima {len(rows)} redova, minimum {minimum}")
    else:
        ok(f"{name}: {len(rows)} redova")
    return rows


def main() -> int:
    s = check_csv(
        SYMPTOMS_CSV,
        {"symptom_id", "canonical_sr", "synonyms_sr", "colloquial_sr",
         "icd10_hint", "body_system"},
        60, "symptoms_sr.csv",
    )
    ds = check_csv(
        DISEASE_SYMPTOMS_CSV,
        {"disease_id", "disease_sr", "symptom_id", "weight", "is_typical"},
        100, "disease_symptoms.csv",
    )
    da = check_csv(
        DISEASE_ATC_CSV,
        {"disease_id", "atc_prefix", "therapy_role", "otc_preferred", "note"},
        25, "disease_atc.csv",
    )
    rf = check_csv(
        RED_FLAGS_CSV, {"pattern_sr", "severity", "action_message_sr"},
        15, "red_flags.csv",
    )
    # test cases
    if not TEST_CASES_JSONL.is_file():
        fail(f"test_cases.jsonl ne postoji: {TEST_CASES_JSONL}")
        tc: list[dict] = []
    else:
        tc = []
        with open(TEST_CASES_JSONL, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    fail(f"test_cases.jsonl linija {i}: {exc}")
                    continue
                if not obj.get("text_sr") or not obj.get("gold_disease"):
                    fail(f"test_cases.jsonl linija {i}: prazan text/gold_disease")
                    continue
                tc.append(obj)
        if len(tc) < 60:
            fail(f"test_cases.jsonl ima {len(tc)} slučajeva, minimum 60")
        else:
            ok(f"test_cases.jsonl: {len(tc)} slučajeva")
    # referencijalni integritet
    sids = {r["symptom_id"] for r in s}
    dids = {r["disease_id"] for r in ds}
    for r in ds:
        if r["symptom_id"] not in sids:
            fail(f"disease_symptoms: nepoznat simptom {r['symptom_id']}")
            break
    else:
        if ds:
            ok("disease_symptoms: svi symptom_id postoje")
    for r in da:
        if r["disease_id"] not in dids:
            fail(f"disease_atc: nepoznata bolest {r['disease_id']}")
            break
        if not ATC_RE.match((r["atc_prefix"] or "").strip().upper()):
            fail(f"disease_atc: sumnjiv ATC {r['atc_prefix']}")
            break
    else:
        if da:
            ok("disease_atc: bolesti i ATC format OK")
    for t in tc:
        for g in t.get("gold_symptoms", []):
            if g not in sids:
                fail(f"test_cases: nepoznat gold simptom {g}")
                break
        if t.get("gold_disease") not in dids:
            fail(f"test_cases: nepoznat gold disease {t.get('gold_disease')}")
            break
    else:
        if tc:
            ok("test_cases: gold reference OK")
    # prosek simptoma po bolesti
    if ds:
        from collections import Counter
        c = Counter(r["disease_id"] for r in ds)
        avg = sum(c.values()) / len(c)
        ok(f"prosek simptoma/stanje: {avg:.2f} ({len(c)} stanja)")
        if avg < 5.0:
            fail(f"prosek {avg:.2f} < 5.0")
    # lekovi uzorak
    if not LEKOVI_SAMPLE_JSON.is_file():
        fail(f"lekovi_sample.json ne postoji: {LEKOVI_SAMPLE_JSON}")
    else:
        with open(LEKOVI_SAMPLE_JSON, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        lst = data.get("lekovi") if isinstance(data, dict) else data
        if not isinstance(lst, list) or len(lst) < 30:
            fail(f"lekovi_sample.json: {len(lst) if isinstance(lst, list) else '?'} zapisa, minimum 30")
        else:
            need = {"nazivLeka", "inn", "rezimIzdavanjaLeka", "atc"}
            bad = [r for r in lst if not need.issubset(set(r.keys()))]
            if bad:
                fail("lekovi_sample.json: nedostaju ključevi registra")
            else:
                ok(f"lekovi_sample.json: {len(lst)} zapisa, shema registra OK")
    if ERRORS:
        print(f"\nSANITY: {len(ERRORS)} grešaka")
        return 1
    print("\nSANITY: sve provere prošle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
