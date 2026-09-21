"""Negacija: 'nemam temperaturu' -> negiran simptom."""
from __future__ import annotations

import re

from sda.config import NEGATION_WINDOW
from sda.models import SymptomMention
from sda.text.normalize import normalize_text

CUES: frozenset[str] = frozenset(normalize_text(c) for c in (
    "ne", "nemam", "nemaš", "nema", "nemamo", "nemate", "nemaju",
    "nisam", "nisi", "nije", "nismo", "niste", "nisu",
    "bez", "negiram", "negira", "niti", "nikakav", "nikakva", "nikakve",
    "prestao", "prestala", "prošao", "prošla", "nestao", "nestala",
))

_PHRASES: tuple[str, ...] = tuple(
    normalize_text(p) for p in
    ("nema više", "ne osećam", "ne osjećam", "nemam više", "bez znakova")
)

_CLAUSE_BOUNDS = {"ali", "a", "nego", "vec", "dok", "medjutim", "pak"}


def _tokens(text: str) -> list[str]:
    return normalize_text(text).split()


def is_negated_context(text: str, matched_text: str,
                       window: int = NEGATION_WINDOW, method: str = "") -> bool:
    toks = _tokens(text)
    m_toks = _tokens(matched_text)
    if not toks or not m_toks:
        return False
    idx = -1
    for i in range(len(toks) - len(m_toks) + 1):
        if toks[i:i + len(m_toks)] == m_toks:
            idx = i
            break
    if idx == -1:
        try:
            idx = toks.index(m_toks[0])
        except ValueError:
            return False
    # Okidač progutan u kratkom fuzzy prozoru ('nemam temperaturu').
    # Ne važi za duge semantičke odsečke ('anksioznost ... ne spavam').
    if method != "semantic" and len(m_toks) <= window + 2:
        if any(c in CUES for c in m_toks):
            return True
    # 'ali' resetuje doseg: 'nemam temperaturu ALI me boli grlo'.
    start = 0
    for i in range(idx - 1, -1, -1):
        if toks[i] in _CLAUSE_BOUNDS:
            start = i + 1
            break
    if any(c in CUES for c in toks[max(start, idx - window):idx]):
        return True
    joined = " " + " ".join(toks[max(0, idx - window - 1):idx + 1]) + " "
    return any(ph and ph in joined for ph in _PHRASES)


def _is_pain_affirmation(text: str, mention: SymptomMention) -> bool:
    # 'ne boli me glava' znači da glava boli — nije negacija.
    if re.search(r"\bne\s+(me\s+)?boli\b", normalize_text(text)):
        return "boli" in normalize_text(mention.matched_text) or "bol" in mention.symptom_id
    return False


def mark_negations(text: str, mentions: list[SymptomMention],
                   window: int = NEGATION_WINDOW
                   ) -> tuple[list[SymptomMention], list[SymptomMention]]:
    positive, negated = [], []
    for m in mentions:
        neg = is_negated_context(text, m.matched_text, window=window, method=m.method)
        if neg and _is_pain_affirmation(text, m):
            neg = False
        (negated if neg else positive).append(SymptomMention(
            m.symptom_id, m.canonical_sr, m.matched_text, neg, m.score, m.method))
    return positive, negated
