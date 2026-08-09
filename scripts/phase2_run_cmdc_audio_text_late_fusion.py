#!/usr/bin/env python3
"""Run Phase 2 CMDC audio/text late-fusion baseline.

The runner combines already-audited CMDC text TF-IDF and audio eGeMAPS
out-of-fold probabilities by unweighted averaging. It does not read raw text,
raw audio, or source paths.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
DEFAULT_TEXT_PREDICTIONS = (
    ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_text_tfidf" / "cmdc_pdch_text_tfidf_predictions.csv"
)
DEFAULT_AUDIO_PREDICTIONS = (
    ROOT / "analysis" / "phase2_baselines" / "cmdc_pdch_audio_egemaps" / "cmdc_pdch_audio_egemaps_predictions.csv"
)
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "cmdc_audio_text_late_fusion"
TEXT_RUN_ID = "cmdc_text_binary_tfidf_logistic"
AUDIO_RUN_ID = "cmdc_audio_binary_egemaps_svm"
FUSION_RUN_ID = "cmdc_audio_text_binary_late_fusion"
SEEDS = [0, 1, 2, 3, 4]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_predictions(path: Path, run_id: str, score_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"prediction file missing: {path}")
    frame = pd.read_csv(path)
    required = {"run_id", "seed", "fold", "subject_id", "y_true", "y_score"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"{path} has no rows for {run_id}")
    selected = selected[["seed", "fold", "subject_id", "y_true", "y_score"]].copy()
    selected = selected.rename(columns={"y_true": f"y_true_{score_name}", "y_score": f"y_score_{score_name}"})
    duplicate_count = int(selected.duplicated(["seed", "fold", "subject_id"]).sum())
    if duplicate_count:
        raise ValueError(f"{run_id} has duplicate seed/fold/subject rows: {duplicate_count}")
    return selected


def build_fusion_predictions(text_path: Path, audio_path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    text = load_predictions(text_path, TEXT_RUN_ID, "text")
    audio = load_predictions(audio_path, AUDIO_RUN_ID, "audio")
    merged = text.merge(audio, on=["seed", "fold", "subject_id"], how="outer", indicator=True)
    merge_counts = merged["_merge"].value_counts().to_dict()
    if merge_counts.get("left_only", 0) or merge_counts.get("right_only", 0):
        raise ValueError(f"text/audio prediction keys are not aligned: {merge_counts}")
    merged = merged.drop(columns=["_merge"])
    label_mismatches = int((merged["y_true_text"].astype(float) != merged["y_true_audio"].astype(float)).sum())
    if label_mismatches:
        raise ValueError(f"text/audio prediction labels disagree on {label_mismatches} rows")
    scores = merged[["y_score_text", "y_score_audio"]].astype(float)
    if not np.isfinite(scores.to_numpy()).all():
        raise ValueError("text/audio scores must be finite for late fusion")
    fused_score = scores.mean(axis=1)
    predictions = pd.DataFrame(
        {
            "run_id": FUSION_RUN_ID,
            "dataset": "CMDC",
            "modality": "Audio/Text",
            "task": "MDD classification",
            "model": "Late Fusion",
            "seed": merged["seed"].astype(int),
            "fold": merged["fold"].astype(str),
            "protocol_id": "cmdc_binary_subject_cv",
            "task_type": "binary_classification",
            "subject_id": merged["subject_id"].astype(str),
            "split": "validation",
            "y_true": merged["y_true_text"].astype(int),
            "y_pred": (fused_score >= 0.5).astype(int),
            "y_score": fused_score.astype(float),
            "text_run_id": TEXT_RUN_ID,
            "audio_run_id": AUDIO_RUN_ID,
            "fusion_rule": "unweighted_probability_average",
        }
    )
    summary = {
        "text_rows": int(len(text)),
        "audio_rows": int(len(audio)),
        "prediction_rows": int(len(predictions)),
        "merge_counts": {str(key): int(value) for key, value in merge_counts.items()},
        "subject_count": int(predictions["subject_id"].nunique()),
        "seed_count": int(predictions["seed"].nunique()),
        "fold_count": int(predictions["fold"].nunique()),
        "label_mismatches": label_mismatches,
    }
    return predictions, summary


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# CMDC Audio/Text Late Fusion Phase 2 Baseline",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: audited out-of-fold prediction files from CMDC text TF-IDF and audio eGeMAPS baselines.",
        "- Fusion rule: unweighted average of text and audio positive-class probabilities.",
        "- Prediction threshold: 0.5.",
        "- Unit of prediction: one row per subject per seed after subject-level CV.",
        "- No raw text, raw audio, feature paths, or source paths are read or written.",
        "- No validation or test labels are used for fusion weighting.",
        "- No test split is used.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Source runs: `{summary['source_runs']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Label mismatches: `{summary['label_mismatches']}`",
        f"- Raw inputs written: `{summary['raw_inputs_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `cmdc_audio_text_late_fusion_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `cmdc_audio_text_late_fusion_run_summary.json`",
    ]
    (out_dir / "cmdc_audio_text_late_fusion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-predictions", type=Path, default=DEFAULT_TEXT_PREDICTIONS)
    parser.add_argument("--audio-predictions", type=Path, default=DEFAULT_AUDIO_PREDICTIONS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    args = parser.parse_args()

    predictions, alignment_summary = build_fusion_predictions(args.text_predictions, args.audio_predictions)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.out_dir / "cmdc_audio_text_late_fusion_predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    run_summary = {
        "generated_at": utc_now(),
        "text_predictions": str(args.text_predictions),
        "audio_predictions": str(args.audio_predictions),
        "runs": [FUSION_RUN_ID],
        "source_runs": [TEXT_RUN_ID, AUDIO_RUN_ID],
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "no_test_split_used": True,
        "raw_inputs_written": False,
        "source_paths_written": False,
        **alignment_summary,
    }
    (args.out_dir / "cmdc_audio_text_late_fusion_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
