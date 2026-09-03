#!/usr/bin/env python3
"""Run MV31 Qwen3 prompt/protocol proxy sensitivity for E-DAIC.

The audit answers a narrow reviewer concern: whether the Qwen3 text pathway can
derive depression signal from repeated prompt-like or position-specific
transcript content. E-DAIC transcripts do not expose speaker roles, so this is a
prompt/protocol proxy sensitivity rather than a participant-only control.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"


normalize_thread_env()

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase3_protocol_controls as phase3_protocol
import phase5_run_mv17a_multilingual_feature_contract as mv17a
import phase5_run_mv22_foundation_backbone_validation as mv22
from phase2_metrics import metric_records


DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv31_qwen_prompt_proxy_sensitivity"
DEFAULT_MANIFEST = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
SEEDS = [0, 1, 2, 3, 4]
FEATURE_PREFIX = mv17a.FEATURE_PREFIX
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "feasibility_audit.csv",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "protocol_proxy_deltas.csv",
    "report.md",
    "run_summary.json",
    "variant_coverage_summary.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return path.name


def qwen_spec(max_length: int, chunk_batch_size: int) -> mv17a.EncoderSpec:
    payload = asdict(mv22.QWEN_SPEC)
    payload["default_max_length"] = int(max_length)
    payload["default_chunk_batch_size"] = int(chunk_batch_size)
    return mv17a.EncoderSpec(**payload)


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def build_variant_table(manifest_path: Path, repeat_min_subjects: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = pd.read_csv(manifest_path)
    base_table, structure_audit = phase3_protocol.build_edaic_base_table(manifest)
    repeated_vocab, repeated_audit = phase3_protocol.build_repeated_turn_vocab(base_table, repeat_min_subjects)
    expanded = phase3_protocol.expand_edaic_controls(base_table, repeated_vocab)
    keep = {
        "full_dialogue",
        "front_25",
        "middle_50",
        "back_25",
        "train_repeated_turns_removed",
        "train_repeated_turns_only",
    }
    expanded = expanded[expanded["control_id"].isin(keep)].copy()
    audit = {
        **structure_audit,
        **repeated_audit,
        "variant_count": int(expanded["control_id"].nunique()),
        "variant_rows": int(len(expanded)),
    }
    return expanded.sort_values(["control_id", "subject_id"]).reset_index(drop=True), audit


def read_complete_variant_cache(
    cache_path: Path,
    required_keys: set[tuple[str, str]],
    expected_dimension: int,
) -> pd.DataFrame | None:
    if not cache_path.exists():
        return None
    frame = pd.read_csv(cache_path)
    required = {"subject_id", "control_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"variant cache missing columns: {sorted(missing)}")
    feature_cols = [col for col in frame.columns if col.startswith(FEATURE_PREFIX)]
    if len(feature_cols) != expected_dimension:
        raise ValueError(f"variant cache has {len(feature_cols)} feature columns, expected {expected_dimension}")
    frame["subject_id"] = frame["subject_id"].astype(str)
    frame["control_id"] = frame["control_id"].astype(str)
    observed = set(zip(frame["subject_id"], frame["control_id"], strict=True))
    if required_keys.issubset(observed):
        return frame[
            [
                key in required_keys
                for key in zip(frame["subject_id"], frame["control_id"], strict=True)
            ]
        ].copy()
    return None


def write_variant_cache(cache_path: Path, rows: list[dict[str, Any]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["control_id", "subject_id"]).reset_index(drop=True)
    frame.to_csv(cache_path, index=False)


def generate_variant_features(
    table: pd.DataFrame,
    cache_path: Path,
    encoder: mv17a.EncoderSpec,
    *,
    device_name: str,
    allow_download: bool,
    force: bool,
) -> pd.DataFrame:
    required_keys = set(zip(table["subject_id"].astype(str), table["control_id"].astype(str), strict=True))
    cached_rows: list[dict[str, Any]] = []
    cached_keys: set[tuple[str, str]] = set()
    if not force and cache_path.exists():
        cached = pd.read_csv(cache_path)
        cached["subject_id"] = cached["subject_id"].astype(str)
        cached["control_id"] = cached["control_id"].astype(str)
        selected = cached[
            [
                key in required_keys
                for key in zip(cached["subject_id"], cached["control_id"], strict=True)
            ]
        ].copy()
        cached_rows = selected.to_dict("records")
        cached_keys = set(zip(selected["subject_id"], selected["control_id"], strict=True))

    missing = table[
        [
            key not in cached_keys
            for key in zip(table["subject_id"].astype(str), table["control_id"].astype(str), strict=True)
        ]
    ].reset_index(drop=True)

    rows = cached_rows
    columns = mv17a.feature_columns(encoder.expected_dimension)
    print(
        f"Generating {encoder.slug} E-DAIC prompt-proxy variant features: "
        f"{len(missing)} missing / {len(table)} variants",
        flush=True,
    )
    if not missing.empty:
        tokenizer, model, device, _hidden = mv17a.load_encoder(
            encoder,
            device_name=device_name,
            allow_download=allow_download,
        )
        for idx, row in missing.iterrows():
            if idx == 0 or (idx + 1) % 25 == 0 or (idx + 1) == len(missing):
                print(f"  [{encoder.slug}:edaic_mv31] {idx + 1}/{len(missing)}", flush=True)
            embedding, chunk_count, token_count, empty_text = mv17a.embed_text(
                str(row["text"]),
                encoder,
                tokenizer,
                model,
                device,
                max_length=encoder.default_max_length,
                chunk_batch_size=encoder.default_chunk_batch_size,
            )
            rows.append(
                {
                    "subject_id": str(row["subject_id"]),
                    "split": str(row["split"]),
                    "control_id": str(row["control_id"]),
                    "text_unit_count": int(row["text_unit_count"]),
                    "retained_text_unit_count": int(row["retained_text_unit_count"]),
                    "removed_text_unit_count": int(row["removed_text_unit_count"]),
                    "empty_text_units": int(row["empty_text_units"]),
                    "token_count_sum": int(token_count),
                    "chunk_count_sum": int(chunk_count),
                    "empty_text_segments": int(empty_text),
                    **{column: float(value) for column, value in zip(columns, embedding, strict=True)},
                }
            )
            if (idx + 1) % 25 == 0:
                write_variant_cache(cache_path, rows)

    write_variant_cache(cache_path, rows)
    complete = read_complete_variant_cache(cache_path, required_keys, encoder.expected_dimension)
    if complete is None:
        raise ValueError("variant feature cache is incomplete after generation")
    return complete.sort_values(["control_id", "subject_id"]).reset_index(drop=True)


def fit_predict(features: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [col for col in features.columns if col.startswith(FEATURE_PREFIX)]
    label_cols = ["subject_id", "split", "control_id", "phq8_total", "binary_label"]
    frame = features[label_cols + feature_cols].copy()
    predictions: list[dict[str, Any]] = []
    for control_id, control_frame in frame.groupby("control_id", sort=True):
        train = control_frame[control_frame["split"] == "train"].reset_index(drop=True)
        dev = control_frame[control_frame["split"] == "dev"].reset_index(drop=True)
        x_train = train[feature_cols].to_numpy(dtype=np.float32)
        x_dev = dev[feature_cols].to_numpy(dtype=np.float32)
        for seed in SEEDS:
            ridge = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            ridge.fit(x_train, train["phq8_total"].astype(float).to_numpy())
            y_reg = ridge.predict(x_dev)
            low = float(train["phq8_total"].min())
            high = float(train["phq8_total"].max())
            y_reg = np.clip(y_reg, low, high)
            for idx, row in dev.iterrows():
                predictions.append(
                    {
                        "run_id": f"mv31_qwen_prompt_proxy_{control_id}_phq8_total",
                        "dataset": "E-DAIC",
                        "modality": "Text",
                        "task": "PHQ-8 regression",
                        "model": f"Qwen3 + Ridge ({control_id})",
                        "task_type": "severity_regression",
                        "control_id": control_id,
                        "seed": seed,
                        "fold": "official_dev",
                        "subject_id": str(row["subject_id"]),
                        "y_true": float(row["phq8_total"]),
                        "y_pred": float(y_reg[idx]),
                        "y_score": "",
                    }
                )

            logistic = make_pipeline(
                StandardScaler(),
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=seed,
                    solver="liblinear",
                ),
            )
            logistic.fit(x_train, train["binary_label"].astype(int).to_numpy())
            y_cls = logistic.predict(x_dev)
            y_score = logistic.predict_proba(x_dev)[:, 1]
            for idx, row in dev.iterrows():
                predictions.append(
                    {
                        "run_id": f"mv31_qwen_prompt_proxy_{control_id}_binary",
                        "dataset": "E-DAIC",
                        "modality": "Text",
                        "task": "binary depression classification",
                        "model": f"Qwen3 + Logistic ({control_id})",
                        "task_type": "binary_classification",
                        "control_id": control_id,
                        "seed": seed,
                        "fold": "official_dev",
                        "subject_id": str(row["subject_id"]),
                        "y_true": int(row["binary_label"]),
                        "y_pred": int(y_cls[idx]),
                        "y_score": float(y_score[idx]),
                    }
                )
    return pd.DataFrame(predictions).sort_values(["run_id", "seed", "subject_id"]).reset_index(drop=True)


def coverage_summary(features: pd.DataFrame) -> pd.DataFrame:
    grouped = features.groupby("control_id", sort=True)
    rows = []
    for control_id, group in grouped:
        rows.append(
            {
                "control_id": str(control_id),
                "subject_count": int(group["subject_id"].nunique()),
                "train_subjects": int(group.loc[group["split"] == "train", "subject_id"].nunique()),
                "dev_subjects": int(group.loc[group["split"] == "dev", "subject_id"].nunique()),
                "retained_text_unit_mean": float(group["retained_text_unit_count"].mean()),
                "removed_text_unit_mean": float(group["removed_text_unit_count"].mean()),
                "token_count_sum": int(group["token_count_sum"].sum()),
                "chunk_count_sum": int(group["chunk_count_sum"].sum()),
                "empty_text_segments": int(group["empty_text_segments"].sum()),
            }
        )
    return pd.DataFrame(rows)


def delta_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    metric_summary = metric_summary.copy()
    if "control_id" not in metric_summary.columns:
        metric_summary["control_id"] = metric_summary["run_id"].map(control_id_from_run_id)
    primary = {
        "PHQ-8 regression": ("MAE", "lower_is_better"),
        "binary depression classification": ("Macro-F1", "higher_is_better"),
    }
    rows: list[dict[str, Any]] = []
    for task, (metric, direction) in primary.items():
        task_rows = metric_summary[
            (metric_summary["task"].astype(str) == task)
            & (metric_summary["metric"].astype(str) == metric)
        ].copy()
        full = task_rows[task_rows["control_id"].astype(str) == "full_dialogue"]
        if full.empty:
            continue
        full_value = float(full.iloc[0]["mean"])
        for _, row in task_rows.iterrows():
            value = float(row["mean"])
            raw_delta = value - full_value
            rows.append(
                {
                    "task": task,
                    "metric": metric,
                    "control_id": str(row["control_id"]),
                    "mean": value,
                    "full_dialogue_mean": full_value,
                    "delta_vs_full_dialogue": raw_delta,
                    "better_than_full": bool(raw_delta < 0.0) if direction == "lower_is_better" else bool(raw_delta > 0.0),
                    "direction": direction,
                    "ci95_low": row.get("ci95_low"),
                    "ci95_high": row.get("ci95_high"),
                }
            )
    return pd.DataFrame(rows)


def control_id_from_run_id(run_id: Any) -> str:
    text = str(run_id)
    prefix = "mv31_qwen_prompt_proxy_"
    if not text.startswith(prefix):
        raise ValueError(f"unexpected MV31 run id: {text}")
    text = text[len(prefix) :]
    for suffix in ["_phq8_total", "_binary"]:
        if text.endswith(suffix):
            return text[: -len(suffix)]
    raise ValueError(f"unexpected MV31 run id suffix: {run_id}")


def feasibility_rows(audit: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset": "E-DAIC",
                "diagnostic": "speaker_resolved_controls",
                "status": "blocked_no_speaker_role",
                "detail": (
                    "The manifest speaker field is empty and transcript CSV column sets are "
                    "Start_Time/End_Time/Text/Confidence, so participant-only and "
                    "interviewer-only transcript controls are not identifiable."
                ),
                "count_1_name": "manifest_speaker_non_null_rows",
                "count_1_value": int(audit["manifest_speaker_non_null_rows"]),
                "count_2_name": "transcript_speaker_column_sets",
                "count_2_value": int(audit["transcript_speaker_column_sets"]),
            },
            {
                "dataset": "E-DAIC",
                "diagnostic": "qwen3_prompt_proxy_controls",
                "status": "completed_proxy_not_speaker_resolved",
                "detail": (
                    "Qwen3 embeddings were regenerated for full transcript, position slices, "
                    "train repeated-turn removal, and train repeated-turn-only proxy variants."
                ),
                "count_1_name": "train_repeated_turn_types",
                "count_1_value": int(audit["train_repeated_turn_types"]),
                "count_2_name": "variant_rows",
                "count_2_value": int(audit["variant_rows"]),
            },
        ]
    )


def finite_or_blank(value: Any) -> bool:
    if value is None or value == "":
        return True
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return True


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    issues: list[str] = []
    for name in TRACKED_FILES - {"artifact_hygiene_audit.json"}:
        path = out_dir / name
        if not path.exists():
            issues.append(f"missing:{name}")
    for path in sorted(out_dir.glob("*")):
        if path.name in TRACKED_FILES:
            continue
        if "features" in path.name or "predictions" in path.name:
            continue
        if path.is_file():
            issues.append(f"unexpected_tracked_candidate:{path.name}")
    return {
        "audit_id": "P5_MV31_qwen_prompt_proxy_sensitivity_hygiene",
        "generated_at": utc_now(),
        "artifact_hygiene_passed": not issues,
        "issues": issues,
        "raw_text_written": False,
        "raw_prompt_text_written": False,
        "source_paths_written": False,
        "participant_level_feature_cache": "local_only_ignored_by_git",
        "row_level_predictions": "local_only_ignored_by_git",
    }


def fmt(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if not math.isfinite(number):
        return ""
    return f"{number:.3f}"


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    coverage: pd.DataFrame,
    deltas: pd.DataFrame,
    feasibility: pd.DataFrame,
) -> None:
    lines = [
        "# P5 MV31 Qwen3 Prompt-Proxy Sensitivity",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV31 re-embeds E-DAIC transcript variants with Qwen3-Embedding-0.6B and fits fixed Ridge/Logistic heads on the official train/dev split. It is a protocol/prompt-proxy stress test, not a participant-only or interviewer-only control.",
        "",
        "## Feasibility",
        "",
        "| dataset | diagnostic | status | count 1 | count 2 |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for _, row in feasibility.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['diagnostic']} | `{row['status']}` | "
            f"{row['count_1_value']} | {row['count_2_value']} |"
        )
    lines.extend(
        [
            "",
            "## Variant Coverage",
            "",
            "| control | subjects | train | dev | retained units mean | removed units mean | chunks |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in coverage.iterrows():
        lines.append(
            f"| `{row['control_id']}` | {int(row['subject_count'])} | {int(row['train_subjects'])} | "
            f"{int(row['dev_subjects'])} | {fmt(row['retained_text_unit_mean'])} | "
            f"{fmt(row['removed_text_unit_mean'])} | {int(row['chunk_count_sum'])} |"
        )
    lines.extend(
        [
            "",
            "## Primary Deltas",
            "",
            "| task | metric | control | mean | full mean | delta vs full |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    primary = deltas[
        deltas["control_id"].isin(
            ["full_dialogue", "front_25", "train_repeated_turns_removed", "train_repeated_turns_only"]
        )
    ].copy()
    for _, row in primary.sort_values(["task", "control_id"]).iterrows():
        lines.append(
            f"| {row['task']} | {row['metric']} | `{row['control_id']}` | "
            f"{fmt(row['mean'])} | {fmt(row['full_dialogue_mean'])} | "
            f"{fmt(row['delta_vs_full_dialogue'])} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Status: `{run_summary['status']}`.",
            f"- Speaker-resolved controls: `{run_summary['speaker_resolved_controls']}`.",
            f"- Prompt-proxy reading: `{run_summary['prompt_proxy_reading']}`.",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_run_summary(
    args: argparse.Namespace,
    audit: dict[str, Any],
    deltas: pd.DataFrame,
) -> dict[str, Any]:
    def primary_delta(task: str, control_id: str) -> float | None:
        row = deltas[(deltas["task"] == task) & (deltas["control_id"] == control_id)]
        if row.empty:
            return None
        return float(row.iloc[0]["delta_vs_full_dialogue"])

    binary_repeat_only = primary_delta("binary depression classification", "train_repeated_turns_only")
    severity_repeat_removed = primary_delta("PHQ-8 regression", "train_repeated_turns_removed")
    if binary_repeat_only is not None and binary_repeat_only > 0.05:
        reading = "repeated_turn_proxy_has_binary_predictive_signal"
    elif severity_repeat_removed is not None and severity_repeat_removed > 0.25:
        reading = "removing_repeated_turn_proxy_hurts_severity_prediction"
    else:
        reading = "no_clear_qwen3_excess_loss_from_repeated_turn_removal"
    return {
        "run_id": "P5_MV31_qwen_prompt_proxy_sensitivity",
        "generated_at": utc_now(),
        "status": "complete_qwen3_prompt_proxy_sensitivity",
        "manifest_ref": "datasets/manifests/edaic_subjects.csv",
        "encoder": {
            "slug": mv22.QWEN_SPEC.slug,
            "model_name": mv22.QWEN_SPEC.model_name,
            "pooling": mv22.QWEN_SPEC.pooling,
            "max_length": int(args.qwen_max_length),
            "chunk_batch_size": int(args.qwen_chunk_batch_size),
        },
        "seeds": SEEDS,
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "speaker_resolved_controls": "blocked_no_speaker_role_in_manifest_or_transcript_csv",
        "prompt_proxy_reading": reading,
        "train_subjects": int(audit["train_subjects"]),
        "dev_subjects": int(audit["dev_subjects"]),
        "train_repeated_turn_types": int(audit["train_repeated_turn_types"]),
        "variant_rows": int(audit["variant_rows"]),
        "local_only_outputs": [
            "local_qwen_variant_subject_features.csv",
            "mv31_qwen_prompt_proxy_predictions.csv",
        ],
        "artifact_hygiene_passed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--qwen-max-length", type=int, default=2048)
    parser.add_argument("--qwen-chunk-batch-size", type=int, default=4)
    parser.add_argument("--edaic-repeat-min-subjects", type=int, default=10)
    parser.add_argument("--bootstrap-resamples", type=int, default=200)
    args = parser.parse_args()

    clean_tracked_outputs(args.out_dir)
    variant_table, audit = build_variant_table(args.manifest, args.edaic_repeat_min_subjects)
    encoder = qwen_spec(args.qwen_max_length, args.qwen_chunk_batch_size)
    feature_cache = args.out_dir / "local_qwen_variant_subject_features.csv"
    features = generate_variant_features(
        variant_table,
        feature_cache,
        encoder,
        device_name=args.device,
        allow_download=args.allow_download,
        force=args.force_features,
    )

    label_cols = variant_table[["subject_id", "split", "control_id", "phq8_total", "binary_label"]].copy()
    features = features.merge(label_cols, on=["subject_id", "split", "control_id"], how="inner")
    predictions = fit_predict(features)
    predictions.to_csv(args.out_dir / "mv31_qwen_prompt_proxy_predictions.csv", index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260904,
    )
    metrics_by_seed["control_id"] = metrics_by_seed["run_id"].map(control_id_from_run_id)
    metric_summary["control_id"] = metric_summary["run_id"].map(control_id_from_run_id)
    metrics_by_seed.to_csv(args.out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "metric_summary.csv", index=False)

    deltas = delta_summary(metric_summary)
    deltas.to_csv(args.out_dir / "protocol_proxy_deltas.csv", index=False)
    coverage = coverage_summary(features)
    coverage.to_csv(args.out_dir / "variant_coverage_summary.csv", index=False)
    feasibility = feasibility_rows(audit)
    feasibility.to_csv(args.out_dir / "feasibility_audit.csv", index=False)

    run_summary = build_run_summary(args, audit, deltas)
    (args.out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary, coverage, deltas, feasibility)
    hygiene = artifact_hygiene(args.out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (args.out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(args.out_dir, run_summary, coverage, deltas, feasibility)
    (args.out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")

    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "status": run_summary["status"],
                "prompt_proxy_reading": run_summary["prompt_proxy_reading"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
