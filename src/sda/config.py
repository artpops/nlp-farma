"""Putanje, pragovi i poruke. Sve putanje su apsolutne, izvedene iz korena repoa."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
SRC_DIR: Path = REPO_ROOT / "src"
DATA_DIR: Path = REPO_ROOT / "data"
KNOWLEDGE_DIR: Path = DATA_DIR / "knowledge"
RAW_DIR: Path = DATA_DIR / "raw"
EVAL_DIR: Path = DATA_DIR / "eval"
REPORTS_DIR: Path = REPO_ROOT / "reports"
REPORTS_RESULTS_DIR: Path = REPORTS_DIR / "results"
REPORTS_FIGURES_DIR: Path = REPORTS_DIR / "figures"
PAPER_DIR: Path = REPO_ROOT / "paper"

SYMPTOMS_CSV: Path = KNOWLEDGE_DIR / "symptoms_sr.csv"
DISEASE_SYMPTOMS_CSV: Path = KNOWLEDGE_DIR / "disease_symptoms.csv"
DISEASE_ATC_CSV: Path = KNOWLEDGE_DIR / "disease_atc.csv"
RED_FLAGS_CSV: Path = KNOWLEDGE_DIR / "red_flags.csv"
TEST_CASES_JSONL: Path = KNOWLEDGE_DIR / "test_cases.jsonl"
LEKOVI_SAMPLE_JSON: Path = RAW_DIR / "lekovi_sample.json"

# Pun lekovi.json (6809 zapisa) ima prednost; ako ga nema, koristi se uzorak.
LEKOVI_FULL_CANDIDATES: tuple[Path, ...] = (
    RAW_DIR / "lekovi.json",
    REPO_ROOT / "lekovi.json",
    REPO_ROOT.parent / "lekovi.json",
    Path(r"C:/Users/Damjan/Documents/Deepseek/lekovi.json"),
)

RANDOM_SEED: int = 42
FUZZY_THRESHOLD: int = 85
SEMANTIC_THRESHOLD: float = 0.35
TOP_K_CONDITIONS: int = 3
TOP_K_DRUGS: int = 5
MIN_CONDITION_SCORE: float = 0.0
NEGATION_WINDOW: int = 4

# BR = bez recepta (jedini OTC signal); ostalo je Rx.
OTC_REZIMI: frozenset[str] = frozenset({"BR"})

DISCLAIMER_SR: str = (
    "INFORMATIVNI PREDLOG, NIJE DIJAGNOZA. "
    "Ovaj sistem ne postavlja dijagnozu i ne zamenjuje lekara ili farmaceuta. "
    "Simptomi su mapirani u rangirane hipoteze stanja (condition_candidate), "
    "a lekovi su informativni predlozi iz registra, prvenstveno OTC. "
    "Ako simptomi traju, pogoršavaju se ili postoje znaci hitnosti, "
    "javite se lekaru ili Hitnoj pomoći (194)."
)

RED_FLAG_BANNER_SR: str = (
    "UPOZORENJE: opis sadrži moguće znake hitnog stanja. "
    "Odmah se javite lekaru / Hitnoj pomoći (194). Predlog terapije se preskače."
)

# Za ove hipoteze lekovi se nikada ne predlažu, samo uput stručnjaku.
MENTAL_HEALTH_DISEASES: frozenset[str] = frozenset({
    "D_ANKSIOZNOST", "D_DEPRESIJA", "D_PANIKA", "D_STRES", "D_BURNOUT",
})

MENTAL_REFERRAL_SR: str = (
    "Napomena: vodeća hipoteza spada u područje mentalnog zdravlja. "
    "Sistem za ove hipoteze ne predlaže lekove — javite se izabranom lekaru, "
    "psihologu ili psihijatru. Tehnike samopomoći (san, kretanje, razgovor sa "
    "bliskom osobom) su dopuna, ne zamena za stručnu procenu. "
    "Ako imate misli o samopovređivanju, odmah pozovite Hitnu pomoć (194)."
)


def ensure_dirs() -> None:
    REPORTS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def resolve_lekovi_path() -> Path | None:
    for cand in LEKOVI_FULL_CANDIDATES:
        try:
            if cand.is_file() and cand.stat().st_size > 0:
                return cand
        except OSError:
            continue
    return None


def active_lekovi_path() -> Path:
    return resolve_lekovi_path() or LEKOVI_SAMPLE_JSON
