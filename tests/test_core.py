from phonosim.features import get_features, normalize_ipa
from phonosim.g2p import to_ipa
from phonosim.predict import predict_difficulty
from phonosim.similarity import get_similarity


def test_normalize_affricate_tiebar():
    assert normalize_ipa("tʃ") == "t͡ʃ"
    assert normalize_ipa("t͡ʃ") == "t͡ʃ"


def test_p_ph_one_feature():
    r = get_similarity("p", "pʰ", mode="hamming")
    assert r.n_differ == 1
    assert r.differing == ["sg"]
    assert r.n_features == 24


def test_v_w_seven_features():
    r = get_similarity("v", "w", mode="hamming")
    assert r.n_differ == 7
    assert set(r.differing) == {"son", "cons", "strid", "ant", "hi", "back", "round"}


def test_retroflex_vs_english_r():
    r = get_similarity("ɽ", "ɹ", mode="hamming")
    assert r.n_differ == 6


def test_get_features_ph():
    feats = get_features("pʰ")
    assert feats["sg"] == 1
    assert feats["voi"] == -1


def test_hindi_modes_run():
    h = get_similarity("p", "pʰ", mode="hindi")
    p = get_similarity("p", "pʰ", mode="panphon")
    assert h.similarity != p.similarity or h.weighted_distance != p.weighted_distance
    assert 0.0 <= h.similarity <= 1.0


def test_predict_v_w_merged_high():
    pred = predict_difficulty("v", "w", l1="hindi")
    assert pred.same_l1_category is True
    assert pred.l1_relation == "merged"
    assert pred.expected_confusion == "high"
    assert pred.featural.n_differ == 7


def test_predict_p_ph_close():
    pred = predict_difficulty("p", "pʰ", l1="hindi")
    assert pred.featural.n_differ == 1
    assert pred.expected_confusion in {"moderate-high", "moderate"}


def test_predict_retroflex_not_false_merger():
    pred = predict_difficulty("ɽ", "ɹ", l1="hindi")
    assert pred.same_l1_category is False
    assert pred.l1_relation == "no_equivalent"
    assert pred.featural.n_differ == 6
    assert pred.expected_confusion == "moderate-high"


def test_english_g2p_vine_wine():
    vine = to_ipa("vine", lang="eng-Latn")
    wine = to_ipa("wine", lang="eng-Latn")
    assert "v" in vine
    assert "w" in wine
    assert vine != wine


def test_hindi_g2p_epitran():
    ipa = to_ipa("वन", lang="hin-Deva")
    assert ipa  # Epitran returns something non-empty
