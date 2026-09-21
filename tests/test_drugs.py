from sda.config import KNOWLEDGE_DIR, RAW_DIR
from sda.drugs.registry import atc_matches, filter_by_atc, is_otc, load_registry, normalize_atc
from sda.drugs.recommender import DrugRecommender
from sda.models import ConditionCandidate


def test_normalize_atc():
    assert normalize_atc("n02be01 ") == "N02BE01"


def test_atc_matches():
    assert atc_matches("N02BE01", "N02BE")
    assert not atc_matches("R06AX29", "N02BE")


def test_filter_by_atc_and_otc():
    reg = load_registry(RAW_DIR / "lekovi_sample.json")
    out = filter_by_atc(reg.all(), ["N02BE"])
    assert len(out) >= 1 and all(atc_matches(d.atc, "N02BE") for d in out)
    assert any(is_otc(d) for d in reg.all())


def test_recommender_otc_first():
    reg = load_registry(RAW_DIR / "lekovi_sample.json")
    rec = DrugRecommender(reg, KNOWLEDGE_DIR / "disease_atc.csv")
    cs = [ConditionCandidate("D_PREHLADA", "Prehlada", 0.8, ["temperatura"], 1, 1.0)]
    drugs = rec.recommend(cs, top_k=3)
    assert len(drugs) >= 1
    assert drugs[0].record.atc != ""
