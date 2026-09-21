from sda.config import KNOWLEDGE_DIR
from sda.safety.red_flags import RedFlagGuard

G = RedFlagGuard(KNOWLEDGE_DIR / "red_flags.csv")


def test_redflag_hit():
    hits = G.check("Imam jak bol u grudima i gušenje")
    assert len(hits) >= 1
    assert any(h.severity == "urgent" for h in hits)


def test_redflag_clean():
    assert G.check("boli me grlo i imam temperaturu 38") == []


def test_redflag_empty():
    assert G.check("") == []
