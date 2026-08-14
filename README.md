# phonosim

Python toolkit for L2 perception research: spelling to IPA, articulatory feature lookup, phoneme similarity, and a first-pass Hindi L1 layer, plus simple AXB stimulus export.

Built for a COGS Honours project (SFU). Term 1 is the toolkit core. Term 2 is a fuller Hindi-aware layer and the AXB study.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

English G2P uses Epitran when flite (`lex_lookup`) is installed. Otherwise `to_ipa` falls back to g2p_en. Hindi uses Epitran (`hin-Deva`).

## Quick start

```python
from phonosim import get_features, get_similarity, predict_difficulty, to_ipa

get_features("pʰ")
get_similarity("p", "pʰ", mode="hamming")   # 1/24, spread glottis
get_similarity("v", "w", mode="hamming")    # 7/24, featurally far
predict_difficulty("v", "w", l1="hindi")    # far + merged L1 category
to_ipa("vine")
```

Similarity modes: `hamming` (flat count), `panphon` (library weights), `hindi` (first-pass cue profile in `data/hindi_cue_weights.yaml`).

Locked study contrasts: /p/–/pʰ/, /v/–/w/, /ɽ/–/ɹ/. See [TERM1_WRITEUP.md](TERM1_WRITEUP.md).

## Layout

```
phonosim/     package
data/         hindi_inventory.yaml, hindi_cue_weights.yaml
tests/
examples/demo.py
```

PanPhon and Epitran are installed as dependencies. Do not commit a local PanPhon clone or `.venv`.

## Tests

```bash
pytest -q
python examples/demo.py
```
