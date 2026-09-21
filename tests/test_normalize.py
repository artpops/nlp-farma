from sda.text.normalize import (
    cyrillic_to_latin,
    latin_to_cyrillic,
    normalize_text,
    strip_diacritics,
)


def test_cyrillic_to_latin_basic():
    assert cyrillic_to_latin("боли ме грло") == "boli me grlo"


def test_cyrillic_digraphs():
    assert cyrillic_to_latin("Љубав и џем") == "Ljubav i džem"


def test_strip_diacritics():
    assert strip_diacritics("šđčćž") == "sdccz"


def test_normalize_text_cleans():
    assert normalize_text("Boli me GRLO, imam Temperaturu 38!") == "boli me grlo imam temperaturu 38"


def test_latin_to_cyrillic_roundtrip():
    assert latin_to_cyrillic("Ljubav") == "Љубав"
