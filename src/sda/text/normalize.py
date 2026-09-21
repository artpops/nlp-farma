"""Srpski tekst: ćirilica/latinica, dijakritici, čišćenje."""
from __future__ import annotations

import re
import unicodedata

_CYR_TO_LAT: dict[str, str] = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ",
    "е": "e", "ж": "ž", "з": "z", "и": "i", "ј": "j", "к": "k",
    "л": "l", "љ": "lj", "м": "m", "н": "n", "њ": "nj", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "ћ": "ć", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "č", "џ": "dž", "ш": "š",
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Ђ": "Đ",
    "Е": "E", "Ж": "Ž", "З": "Z", "И": "I", "Ј": "J", "К": "K",
    "Л": "L", "Љ": "Lj", "М": "M", "Н": "N", "Њ": "Nj", "О": "O",
    "П": "P", "Р": "R", "С": "S", "Т": "T", "Ћ": "Ć", "У": "U",
    "Ф": "F", "Х": "H", "Ц": "C", "Ч": "Č", "Џ": "Dž", "Ш": "Š",
}

_LAT_TO_CYR_MULTI = (("dž", "џ"), ("Dž", "Џ"), ("DŽ", "Џ"), ("lj", "љ"),
                     ("Lj", "Љ"), ("LJ", "Љ"), ("nj", "њ"), ("Nj", "Њ"), ("NJ", "Њ"))

_LAT_TO_CYR: dict[str, str] = {
    "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "đ": "ђ",
    "e": "е", "ž": "ж", "z": "з", "i": "и", "j": "ј", "k": "к",
    "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "r": "р",
    "s": "с", "t": "т", "ć": "ћ", "u": "у", "f": "ф", "h": "х",
    "c": "ц", "č": "ч", "š": "ш",
    "A": "А", "B": "Б", "V": "В", "G": "Г", "D": "Д", "Đ": "Ђ",
    "E": "Е", "Ž": "Ж", "Z": "З", "I": "И", "J": "Ј", "K": "К",
    "L": "Л", "M": "М", "N": "Н", "O": "О", "P": "П", "R": "Р",
    "S": "С", "T": "Т", "Ć": "Ћ", "U": "У", "F": "Ф", "H": "Х",
    "C": "Ц", "Č": "Ч", "Š": "Ш",
}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def cyrillic_to_latin(text: str) -> str:
    return "".join(_CYR_TO_LAT.get(ch, ch) for ch in (text or ""))


def latin_to_cyrillic(text: str) -> str:
    res = text or ""
    for lat, cyr in _LAT_TO_CYR_MULTI:
        res = res.replace(lat, cyr)
    return "".join(_LAT_TO_CYR.get(ch, ch) for ch in res)


def strip_diacritics(text: str) -> str:
    text = (text or "").replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_text(text: str) -> str:
    t = strip_diacritics(cyrillic_to_latin(text or "").lower())
    return _WS_RE.sub(" ", _NON_ALNUM_RE.sub(" ", t)).strip()
