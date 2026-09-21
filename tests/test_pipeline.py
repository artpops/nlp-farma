from sda.config import MENTAL_HEALTH_DISEASES
from sda.pipeline import analyze_text


def test_ceo_tok_offline():
    res = analyze_text("boli me grlo i imam temperaturu 38", no_embeddings=True)
    assert any(m.symptom_id == "bol_u_grlu" for m in res.symptoms)
    assert 1 <= len(res.candidates) <= 10
    assert "NIJE DIJAGNOZA" in res.disclaimer
    assert len(res.drugs) >= 1


def test_crvena_zastavica_preskace_lekove():
    res = analyze_text("Imam jak bol u grudima i gušenje", no_embeddings=True)
    assert len(res.red_flags) >= 1 and res.drugs == [] and "194" in res.disclaimer


def test_negacija_iskljucena():
    ids = {m.symptom_id for m in analyze_text(
        "nemam temperaturu ali me boli grlo", no_embeddings=True).symptoms}
    assert "bol_u_grlu" in ids and "temperatura" not in ids


def test_anksioznost_bez_lekova():
    res = analyze_text("osećam stalnu anksioznost i brinem non stop, ne mogu da spavam",
                       no_embeddings=True)
    assert "anksioznost" in {m.symptom_id for m in res.symptoms}
    assert res.candidates and res.candidates[0].disease_id in MENTAL_HEALTH_DISEASES
    assert res.drugs == [] and "mentalnog zdravlja" in res.disclaimer


def test_depresija_uput():
    res = analyze_text("sve mi je sivo, ništa me ne raduje i povlačim se od ljudi",
                       no_embeddings=True)
    assert res.candidates and res.candidates[0].disease_id == "D_DEPRESIJA"
    assert res.drugs == []


def test_samoubistvo_je_hitno():
    res = analyze_text("imam misli da se ubijem", no_embeddings=True)
    assert len(res.red_flags) >= 1 and res.drugs == [] and "194" in res.disclaimer


def test_somatsko_i_dalje_daje_lekove():
    res = analyze_text("boli me grlo i imam temperaturu 38", no_embeddings=True)
    assert res.candidates[0].disease_id not in MENTAL_HEALTH_DISEASES
    assert len(res.drugs) >= 1
