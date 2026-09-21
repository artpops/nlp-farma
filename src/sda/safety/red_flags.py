"""Red-flagovi: hitna stanja prekidaju predlog terapije."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from sda.models import RedFlagHit, RedFlagRule
from sda.text.normalize import normalize_text


class RedFlagGuard:
    def __init__(self, csv_path: str | Path) -> None:
        self.path = Path(csv_path)
        self.rules: list[RedFlagRule] = []
        with open(self.path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            missing = {"pattern_sr", "severity", "action_message_sr"} - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"red_flags.csv nedostaju kolone: {sorted(missing)}")
            for row in reader:
                pat = (row.get("pattern_sr") or "").strip()
                if pat:
                    self.rules.append(RedFlagRule(pat, (row.get("severity") or "urgent").strip().lower(),
                                                  (row.get("action_message_sr") or "").strip()))
        if not self.rules:
            raise ValueError(f"Prazan red_flags.csv: {self.path}")
        self._norm = [normalize_text(r.pattern_sr) for r in self.rules]

    def check(self, text: str) -> list[RedFlagHit]:
        norm_text = normalize_text(text or "")
        if not norm_text:
            return []
        hits: list[RedFlagHit] = []
        for rule, pat in zip(self.rules, self._norm):
            if not pat:
                continue
            found = (pat in norm_text) if " " in pat else re.search(
                r"(?<![a-z0-9])" + re.escape(pat) + r"(?![a-z0-9])", norm_text) is not None
            if found:
                hits.append(RedFlagHit(rule.pattern_sr, rule.severity,
                                       rule.action_message_sr, rule.pattern_sr))
        return hits
