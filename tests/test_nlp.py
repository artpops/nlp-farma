from sda.config import KNOWLEDGE_DIR
from sda.inference.explain import explain_candidates, format_explanation
from sda.inference.ranker import ConditionRanker
from sda.models import SymptomMention
from sda.nlp.extractor import HybridExtractor
from sda.nlp.lexicon import load_symptom_lexicon
from sda.nlp.negation import mark_negations

LEX = load_symptom_lexicon(KNOWLEDGE_DIR / "symptoms_sr.csv")
RANKER = ConditionRanker(KNOWLEDGE_DIR / "disease_symptoms.csv")


def _ms(*sids):
    return [SymptomMention(s, s, s, False, 1.0, "gazetteer") for s in sids]


def test_extractor_grlo_temperatura():
    ids = {m.symptom_id for m in HybridExtractor(LEX, no_embeddings=True).extract(
        "boli me grlo i imam temperaturu 38")}
    assert "bol_u_grlu" in ids and "temperatura" in ids


def test_extractor_cirilica():
    ids = {m.symptom_id for m in HybridExtractor(LEX, no_embeddings=True).extract(
        "боли ме грло и имам температуру")}
    assert "bol_u_grlu" in ids and "temperatura" in ids


def test_extractor_greska_u_kucanju():
    ids = {m.symptom_id for m in HybridExtractor(LEX, no_embeddings=True).extract(
        "boli me grlo i imam tempraturu 38")}
    assert "temperatura" in ids


def test_extractor_bez_laznih_pozitiva():
    assert len(HybridExtractor(LEX, no_embeddings=True).extract(
        "boli me grlo i imam temperaturu 38")) <= 6


def test_extractor_prazno():
    ext = HybridExtractor(LEX, no_embeddings=True)
    assert ext.extract("") == [] and ext.extract("   ") == []


def test_negacija_nemam():
    pos, neg = mark_negations(
        "nemam temperaturu",
        [SymptomMention("temperatura", "temperatura", "temperaturu", False, 1.0, "gazetteer")])
    assert len(pos) == 0 and len(neg) == 1 and neg[0].negated


def test_negacija_ne_boli_me_glava():
    pos, neg = mark_negations(
        "ne boli me glava",
        [SymptomMention("glavobolja", "glavobolja", "glava", False, 1.0, "gazetteer")])
    assert len(pos) == 1 and len(neg) == 0


def test_ranker_faringitis_u_vrhu():
    cs = RANKER.rank(_ms("bol_u_grlu", "temperatura"), top_k=3)
    assert cs and cs[0].disease_id in {"D_FARINGITIS", "D_TONZILITIS", "D_PREHLADA", "D_GRIP"}


def test_ranker_prazno_i_negirano():
    assert RANKER.rank([]) == []
    assert RANKER.rank([SymptomMention("temperatura", "temperatura", "temperaturu", True, 1.0, "gazetteer")]) == []


def test_obrazlozenje():
    cs = RANKER.rank(_ms("bol_u_grlu", "temperatura"), top_k=1)
    ex = explain_candidates(cs, _ms("bol_u_grlu", "temperatura"), ranker=RANKER)
    assert len(ex[cs[0].disease_id]) >= 1
    assert cs[0].disease_sr in format_explanation(cs[0], ex[cs[0].disease_id])
