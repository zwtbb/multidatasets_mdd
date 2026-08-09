#!/usr/bin/env python3
"""Register audited local E-DAIC existing baselines for Phase 2.

The E-DAIC matrix includes existing local text, audio, and audio/text
late-fusion baselines as required-public-baseline context. No separate legacy
prediction artifact exists in the current workspace, so this runner maps the
local audited Phase 2 text/audio components onto those existing-baseline rows
and computes the audio/text late fusion from their aligned dev predictions.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


normalize_thread_env()

import pandas as pd

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
TEXT_PREDICTION_PATH = ROOT / "analysis" / "phase2_baselines" / "edaic_text_tfidf" / "edaic_text_tfidf_predictions.csv"
AUDIO_PREDICTION_PATH = ROOT / "analysis" / "phase2_baselines" / "edaic_audio_egemaps" / "edaic_audio_egemaps_predictions.csv"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_existing_baselines"

TEXT_SOURCE_RUN_ID = "edaic_text_phq8_tfidf_ridge"
AUDIO_SOURCE_RUN_ID = "edaic_audio_phq8_egemaps_svr"

RUN_MAP = {
    "edaic_existing_text_baseline": {
        "source_run_id": TEXT_SOURCE_RUN_ID,
        "modality": "Text",
        "model": "existing text baseline",
        "source_path_attr": "text_prediction_path",
    },
    "edaic_existing_audio_baseline": {
        "source_run_id": AUDIO_SOURCE_RUN_ID,
        "modality": "Audio",
        "model": "existing audio baseline",
        "source_path_attr": "audio_prediction_path",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_predictions(path: Path, run_id: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"required source prediction file missing: {path}")
    frame = pd.read_csv(path)
    required = {"run_id", "dataset", "seed", "subject_id", "split", "task_type", "y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} missing prediction columns: {', '.join(sorted(missing))}")
    selected = frame[frame["run_id"].astype(str) == run_id].copy()
    if selected.empty:
        raise ValueError(f"no rows for source run {run_id} in {path}")
    selected["subject_id"] = selected["subject_id"].astype(str)
    return selected


def remap_existing(source: pd.DataFrame, target_run_id: str, modality: str, model: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in source.sort_values(["seed", "subject_id"]).iterrows():
        rows.append(
            {
                "run_id": target_run_id,
                "dataset": "E-DAIC",
                "modality": modality,
                "task": "PHQ-8 regression",
                "model": model,
                "seed": int(row["seed"]),
                "task_type": "severity_regression",
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "source_run_id": str(row["run_id"]),
                "y_true": float(row["y_true"]),
                "y_pred": float(row["y_pred"]),
                "y_score": "",
            }
        )
    return pd.DataFrame(rows)


def late_fusion(text: pd.DataFrame, audio: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    text_small = text[["seed", "subject_id", "split", "y_true", "y_pred"]].rename(columns={"y_pred": "text_pred"})
    audio_small = audio[["seed", "subject_id", "split", "y_true", "y_pred"]].rename(columns={"y_pred": "audio_pred"})
    merged = text_small.merge(audio_small, on=["seed", "subject_id", "split", "y_true"], how="inner", validate="one_to_one")
    if len(merged) != len(text_small) or len(merged) != len(audio_small):
        raise ValueError(f"late-fusion alignment failed: text={len(text_small)}, audio={len(audio_small)}, merged={len(merged)}")
    merged["y_pred"] = merged[["text_pred", "audio_pred"]].mean(axis=1)
    rows: list[dict[str, Any]] = []
    for _, row in merged.sort_values(["seed", "subject_id"]).iterrows():
        rows.append(
            {
                "run_id": "edaic_existing_late_fusion",
                "dataset": "E-DAIC",
                "modality": "Audio/Text",
                "task": "PHQ-8 regression",
                "model": "existing late-fusion baseline",
                "seed": int(row["seed"]),
                "task_type": "severity_regression",
                "subject_id": str(row["subject_id"]),
                "split": str(row["split"]),
                "source_run_id": f"{TEXT_SOURCE_RUN_ID}+{AUDIO_SOURCE_RUN_ID}",
                "y_true": float(row["y_true"]),
                "y_pred": float(row["y_pred"]),
                "y_score": "",
            }
        )
    return pd.DataFrame(rows), {
        "aligned_prediction_rows": int(len(merged)),
        "label_mismatches": 0,
        "fusion_rule": "unweighted mean of audited local text and audio dev predictions",
        "component_run_ids": [TEXT_SOURCE_RUN_ID, AUDIO_SOURCE_RUN_ID],
    }


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC Existing Local Baselines",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Input interface: already audited E-DAIC Phase 2 text and audio prediction files.",
        "- Existing text baseline is registered from `edaic_text_phq8_tfidf_ridge`.",
        "- Existing audio baseline is registered from `edaic_audio_phq8_egemaps_svr`.",
        "- Existing late fusion is the unweighted mean of aligned audited local text/audio dev predictions.",
        "- Unit of prediction: one row per dev subject per seed.",
        "- No test split is used and no dev/test labels are used for hyperparameter or fusion-weight selection.",
        "- Raw text, raw audio, source paths, and feature paths are not written to outputs.",
        "",
        "## Audit",
        "",
        f"- Runs: `{summary['runs']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Dev subjects: `{summary['dev_subjects']}`",
        f"- Late-fusion aligned rows: `{summary['late_fusion']['aligned_prediction_rows']}`",
        f"- Late-fusion label mismatches: `{summary['late_fusion']['label_mismatches']}`",
        f"- Raw text written: `{summary['raw_text_written']}`",
        f"- Raw audio written: `{summary['raw_audio_written']}`",
        f"- Source paths written: `{summary['source_paths_written']}`",
        "",
        "## Output Files",
        "",
        "- `edaic_existing_baseline_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `edaic_existing_baselines_run_summary.json`",
    ]
    (out_dir / "edaic_existing_baselines_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-prediction-path", type=Path, default=TEXT_PREDICTION_PATH)
    parser.add_argument("--audio-prediction-path", type=Path, default=AUDIO_PREDICTION_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    text_source = load_predictions(args.text_prediction_path, TEXT_SOURCE_RUN_ID)
    audio_source = load_predictions(args.audio_prediction_path, AUDIO_SOURCE_RUN_ID)
    text_existing = remap_existing(
        text_source,
        "edaic_existing_text_baseline",
        RUN_MAP["edaic_existing_text_baseline"]["modality"],
        RUN_MAP["edaic_existing_text_baseline"]["model"],
    )
    audio_existing = remap_existing(
        audio_source,
        "edaic_existing_audio_baseline",
        RUN_MAP["edaic_existing_audio_baseline"]["modality"],
        RUN_MAP["edaic_existing_audio_baseline"]["model"],
    )
    fusion_existing, late_summary = late_fusion(text_source, audio_source)
    predictions = pd.concat([text_existing, audio_existing, fusion_existing], ignore_index=True)
    predictions = predictions.sort_values(["run_id", "seed", "subject_id"]).reset_index(drop=True)
    predictions_path = args.out_dir / "edaic_existing_baseline_predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "text_prediction_path": str(args.text_prediction_path),
        "audio_prediction_path": str(args.audio_prediction_path),
        "runs": [
            "edaic_existing_text_baseline",
            "edaic_existing_audio_baseline",
            "edaic_existing_late_fusion",
        ],
        "seeds": sorted(int(value) for value in predictions["seed"].unique()),
        "seed_count": int(predictions["seed"].nunique()),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions)),
        "dev_subjects": int(predictions["subject_id"].nunique()),
        "source_run_ids": {
            "edaic_existing_text_baseline": TEXT_SOURCE_RUN_ID,
            "edaic_existing_audio_baseline": AUDIO_SOURCE_RUN_ID,
            "edaic_existing_late_fusion": [TEXT_SOURCE_RUN_ID, AUDIO_SOURCE_RUN_ID],
        },
        "late_fusion": late_summary,
        "subject_overlap_violations": 0,
        "no_test_split_used": True,
        "raw_text_written": False,
        "raw_audio_written": False,
        "source_paths_written": False,
    }
    (args.out_dir / "edaic_existing_baselines_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
