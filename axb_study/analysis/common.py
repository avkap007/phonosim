"""Shared definitions for the AXB analysis."""
import json
from pathlib import Path

EXP = Path(__file__).resolve().parents[1] / "experiment"
REPO = Path(__file__).resolve().parents[2]

# consonant codes used in file names -> IPA
CODE_IPA = {"v": "v", "w": "w", "f": "f", "th": "θ", "t": "t", "dh": "ð", "d": "d",
            "zh": "ʒ", "dzh": "d͡ʒ", "r": "ɹ", "rx": "ɽ", "p": "p", "ph": "pʰ"}
# contrast name -> the two consonant codes (also the sound-matching phone names)
CONTRAST_CODES = {c: tuple(c.split("-")) for c in
                  ["v-w", "zh-dzh", "th-t", "dh-d", "v-f", "w-r", "p-ph", "r-rx"]}
# Devanagari response options -> IPA (Hindi category)
DEVANAGARI_IPA = {"व": "ʋ", "ब": "b", "भ": "b̤", "प": "p", "फ": "pʰ", "फ़": "f", "त": "t̪",
                  "थ": "t̪ʰ", "ट": "ʈ", "द": "d̪", "ध": "d̪̤", "ड": "ɖ", "ड़": "ɽ", "र": "r",
                  "ज": "d͡ʒ", "ज़": "z", "झ": "d͡ʒ̤", "स": "s", "श": "ʃ", "य": "j",
                  "None of these": "none"}


def load_stim():
    txt = (EXP / "stimuli" / "trials.js").read_text(encoding="utf-8")
    return json.loads(txt.split("=", 1)[1].strip().rstrip(";"))


def l1_maps():
    """English consonant -> Hindi category under the hand-built v2 table and the
    automatic projection. Hindi phonemes (pʰ, ɽ) map to themselves in both."""
    import yaml
    from phonosim.l1.project import load_inventory, project
    v2 = yaml.safe_load((REPO / "icphs2027" / "data" / "hindi_inventory_v2.yaml").read_text())
    table = v2.get("english_to_hindi", v2)
    inv = load_inventory("hindi", REPO / "crossl1" / "data" / "inventories.yaml")
    hand, auto = {}, {}
    for code, ipa in CODE_IPA.items():
        entry = table.get(ipa)
        hand[code] = entry["hindi"] if isinstance(entry, dict) else ipa
        p = project(ipa, inv)
        auto[code] = p[0] if len(p) == 1 else "/".join(p)
    return hand, auto
