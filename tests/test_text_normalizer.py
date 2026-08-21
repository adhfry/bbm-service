from app.services.text_normalizer import case_fold, normalize_diacritics, tokenize_words


def test_case_fold_preserves_diacritics_and_glottal_apostrophe():
    assert case_fold("Â") == "â"
    assert case_fold("A'") == "a'"
    assert case_fold("Bhâ'") == "bhâ'"


def test_normalizes_madura_diacritics():
    assert normalize_diacritics("Bâbâ") == "baba"
    assert normalize_diacritics("nasè'") == "nase"
    assert normalize_diacritics("SALAMET") == "salamet"


def test_normalize_is_idempotent():
    once = normalize_diacritics("Dâteng")
    twice = normalize_diacritics(once)
    assert once == twice


def test_tokenize_words_splits_on_whitespace_and_drops_empties():
    assert tokenize_words("  selamat   pagi ") == ["selamat", "pagi"]
    assert tokenize_words("") == []
    assert tokenize_words("satu") == ["satu"]
