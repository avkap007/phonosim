"""Quick smoke demo for the phonosim toolkit."""

from phonosim import get_features, get_similarity, predict_difficulty, to_ipa
from phonosim.export import stimulus_export
from phonosim.pairs import minimal_pair_generator
from phonosim.similarity import hamming_summary

print("=== Features ===")
print("pʰ:", get_features("pʰ"))

print("\n=== Distances (hamming) ===")
for a, b in [("p", "pʰ"), ("v", "w"), ("ɽ", "ɹ"), ("s", "ʃ")]:
    print(f"/{a}/–/{b}/:", hamming_summary(a, b))

print("\n=== Difficulty (Hindi L1) ===")
for a, b in [("p", "pʰ"), ("v", "w"), ("ɽ", "ɹ")]:
    pred = predict_difficulty(a, b, l1="hindi")
    print(f"/{a}/–/{b}/ → {pred.expected_confusion}")
    print(" ", pred.rationale)

print("\n=== G2P ===")
print("vine →", to_ipa("vine"))
print("wine →", to_ipa("wine"))

print("\n=== Minimal pairs + export ===")
pairs = minimal_pair_generator(
    ("v", "w"),
    wordlist=[],
    orthographic_pairs=[("vine", "wine"), ("vest", "west")],
)
print(pairs)
if pairs:
    path = stimulus_export(pairs, "examples/vw_axb_psychopy.csv", format="psychopy")
    print("wrote", path)
