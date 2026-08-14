"""Export stimulus tables for PsychoPy and jsPsych AXB designs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Literal, Sequence

from phonosim.pairs import MinimalPair

Format = Literal["psychopy", "jspsych"]


def _axb_rows(
    pairs: Sequence[MinimalPair],
    *,
    contrast_label: str | None = None,
) -> list[dict]:
    """Build AXB trial rows: A and B are the contrast endpoints; X matches A or B."""
    rows: list[dict] = []
    for i, pair in enumerate(pairs):
        label = contrast_label or f"{pair.contrast[0]}-{pair.contrast[1]}"
        # Two trial types: X=A (correct=A) and X=B (correct=B)
        for x_is_a in (True, False):
            rows.append(
                {
                    "trial_id": f"{i}_{'A' if x_is_a else 'B'}",
                    "contrast": label,
                    "word_a": pair.word_a,
                    "word_b": pair.word_b,
                    "ipa_a": pair.ipa_a,
                    "ipa_b": pair.ipa_b,
                    "stim_a": pair.word_a,
                    "stim_b": pair.word_b,
                    "stim_x": pair.word_a if x_is_a else pair.word_b,
                    "correct": "A" if x_is_a else "B",
                    "audio_a": f"{pair.word_a}.wav",
                    "audio_b": f"{pair.word_b}.wav",
                    "audio_x": f"{(pair.word_a if x_is_a else pair.word_b)}.wav",
                }
            )
    return rows


def stimulus_export(
    pairs: Sequence[MinimalPair],
    path: str | Path,
    *,
    format: Format = "psychopy",
    contrast_label: str | None = None,
) -> Path:
    """Write AXB stimulus table to CSV (PsychoPy) or JSON (jsPsych)."""
    path = Path(path)
    rows = _axb_rows(pairs, contrast_label=contrast_label)
    path.parent.mkdir(parents=True, exist_ok=True)

    if format == "psychopy":
        if not rows:
            path.write_text("", encoding="utf-8")
            return path
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return path

    if format == "jspsych":
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    raise ValueError(f"Unknown format: {format!r}")


def export_contrast_set(
    pair_groups: Iterable[tuple[str, Sequence[MinimalPair]]],
    out_dir: str | Path,
) -> dict[str, Path]:
    """Export multiple contrasts to both PsychoPy and jsPsych files."""
    out_dir = Path(out_dir)
    written: dict[str, Path] = {}
    for label, pairs in pair_groups:
        safe = label.replace("/", "-").replace(" ", "_")
        written[f"{safe}_psychopy"] = stimulus_export(
            pairs, out_dir / f"{safe}_axb_psychopy.csv", format="psychopy", contrast_label=label
        )
        written[f"{safe}_jspsych"] = stimulus_export(
            pairs, out_dir / f"{safe}_axb_jspsych.json", format="jspsych", contrast_label=label
        )
    return written
