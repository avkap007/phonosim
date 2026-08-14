"""phonosim — Epitran → PanPhon → Hindi L1 cue-weighting → perception stimuli."""

from phonosim.features import get_features, normalize_ipa
from phonosim.g2p import to_ipa
from phonosim.l1.hindi import map_to_l1
from phonosim.predict import predict_difficulty
from phonosim.similarity import get_similarity

__all__ = [
    "to_ipa",
    "normalize_ipa",
    "get_features",
    "get_similarity",
    "map_to_l1",
    "predict_difficulty",
]

__version__ = "0.1.0"
