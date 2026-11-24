# phonosim

Python toolkit for L2 speech perception research: spelling to IPA, PanPhon feature lookup, phoneme similarity, and an L1 layer that maps English sounds onto a listener's first-language categories. Built for a COGS Honours thesis at SFU (supervisor: Dr. Yue Wang), with a focus on Hindi-L1 listeners.

phonosim is an integration layer over [PanPhon](https://github.com/dmort27/panphon), [Epitran](https://github.com/dmort27/epitran) and [g2p_en](https://github.com/Kyubyong/g2p). It does not reimplement them.

![tests](https://github.com/avkap007/phonosim/actions/workflows/tests.yml/badge.svg)

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# once: NLTK data that g2p_en needs for English
python -c "import nltk; [nltk.download(p) for p in ('cmudict', 'averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger')]"
```

PanPhon is pinned to 0.22.2 because a new release can change feature values, and with them the locked distances. For the corpus studies, use `pip install -e ".[analysis]"`, or `-r requirements-analysis.txt` for the exact versions used.

## Quick start

```python
from phonosim import get_features, get_similarity, predict_difficulty, to_ipa

get_similarity("p", "pʰ", mode="hamming")   # 1/24 features (spread glottis)
get_similarity("v", "w", mode="hamming")    # 7/24, featurally far
predict_difficulty("v", "w", l1="hindi")    # far, but merged into one Hindi category
to_ipa("vine")

# Automatic L1 layer: nearest L1 phoneme by feature distance, for any inventory
from phonosim.l1.project import load_inventory, project
inv = load_inventory("hindi", "crossl1/data/inventories.yaml")
project("v", inv)                            # ['f']
```

Similarity modes: `hamming` (flat count), `panphon` (library weights), `hindi` (cue profile in `phonosim/data/hindi_cue_weights.yaml`).

## What's in the repo

| Folder | What | Status |
|---|---|---|
| `phonosim/` | The package. `l1/hindi.py` is the hand-built Hindi table, `l1/project.py` the automatic projection. | Term 1 + Nov 2026 |
| `icphs2027/` | Study 1: hand-built Hindi layer vs L2-ARCTIC substitutions. Code, Hindi tables v1/v2, paper draft. | Run Oct 7, 2026 |
| `crossl1/` | Study 2: automatic layer across all six L2-ARCTIC L1s. Frozen plan, inventories, code, PHOIBLE check (`INVENTORY_CHECK.md`). | Run Nov 17, 2026 |
| `axb_study/` | Study 3: online AXB + sound-matching experiment (jsPsych for JATOS/Prolific) and the power simulation. | Built, not run |
| `tests/` | Unit tests, including the locked distances and the frozen Study 2 projections. | |

Results folders and the L2-ARCTIC corpus are not committed (the corpus is CC BY-NC and about 7.5 GB). Each study folder's README says how to rerun it.

## Tests

```bash
pytest -q
```

The tests fail if the locked distances (/p/ vs /pʰ/ 1/24, /v/ vs /w/ 7/24, /ɽ/ vs /ɹ/ 6/24) or any of the Study 2 projections change. GitHub Actions runs them on every push.

## Try the experiment locally

```bash
cd axb_study/experiment
python3 build_stimuli.py --placeholders
python3 -m http.server 8765
# open http://localhost:8765/index.html?quick=1
```

See [axb_study/experiment/README.md](axb_study/experiment/README.md) for the design and the steps before launch.
