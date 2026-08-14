"""Combine featural distance with Hindi L1 assimilation into a difficulty prediction."""

from __future__ import annotations

from dataclasses import dataclass

from phonosim.l1.hindi import contrast_assimilation
from phonosim.similarity import SimilarityResult, get_similarity


@dataclass(frozen=True)
class DifficultyPrediction:
    a: str
    b: str
    l1: str
    featural: SimilarityResult
    l1_relation: str
    same_l1_category: bool
    expected_confusion: str
    rationale: str

    def as_dict(self) -> dict:
        return {
            "a": self.a,
            "b": self.b,
            "l1": self.l1,
            "featural": self.featural.as_dict(),
            "l1_relation": self.l1_relation,
            "same_l1_category": self.same_l1_category,
            "expected_confusion": self.expected_confusion,
            "rationale": self.rationale,
        }


def predict_difficulty(
    a: str,
    b: str,
    *,
    l1: str = "hindi",
    mode: str = "hamming",
) -> DifficultyPrediction:
    """Predict discrimination difficulty for an English contrast for an L1 listener.

    Combines:
    - featural distance (PanPhon / our cue weights)
    - L1 category mapping (e.g. Hindi merger of v/w)

    This is the researcher-facing answer: raw distance alone misleads on L1 mergers.
    """
    feat = get_similarity(a, b, mode=mode)  # type: ignore[arg-type]
    assim = contrast_assimilation(a, b, l1=l1)
    relation = assim["relation"]
    same = assim["same_l1_category"]
    close = feat.n_differ <= 2
    far = feat.n_differ >= 5

    if same or relation == "merged":
        expected = "high"
        rationale = (
            f"Featural distance is {feat.n_differ}/{feat.n_features} "
            f"({'far' if far else 'moderate' if not close else 'close'}), but both map to the "
            f"same {l1} category → L1 single-category assimilation predicts confusion "
            f"even when PanPhon says the sounds are distinct."
        )
    elif relation == "exists_different_cues" and close:
        expected = "moderate-high"
        rationale = (
            f"Featural distance is small ({feat.n_differ}/{feat.n_features}: "
            f"{', '.join(feat.differing)}). The contrast exists in {l1} but with different "
            f"cue implementation → score and L1 both predict difficulty."
        )
    elif relation == "exists_different_cues":
        expected = "moderate"
        rationale = (
            f"Contrast exists in {l1} with different cues; featural distance "
            f"{feat.n_differ}/{feat.n_features}."
        )
    elif relation == "no_equivalent" and far:
        expected = "moderate-high"
        rationale = (
            f"Featural distance is far ({feat.n_differ}/{feat.n_features}) and at least one "
            f"phone lacks a direct {l1} equivalent → L1-driven miscategorization likely."
        )
    elif close:
        expected = "moderate"
        rationale = (
            f"Featural distance is small ({feat.n_differ}/{feat.n_features}); "
            f"L1 relation={relation}."
        )
    else:
        expected = "low-moderate"
        rationale = (
            f"Featural distance {feat.n_differ}/{feat.n_features}; L1 relation={relation}. "
            f"Raw score alone would predict relatively easy discrimination."
        )

    return DifficultyPrediction(
        a=feat.a,
        b=feat.b,
        l1=l1,
        featural=feat,
        l1_relation=relation,
        same_l1_category=same,
        expected_confusion=expected,
        rationale=rationale,
    )
