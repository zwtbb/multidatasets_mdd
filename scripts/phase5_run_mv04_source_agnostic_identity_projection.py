#!/usr/bin/env python3
"""Run P5_MV04b source-agnostic identity projection controls.

This follow-up keeps the P5_MV04 PHQ C01-C08 and frozen WavLM contract, but
replaces known-eval-dataset centering with train-fold nuisance-direction
projection. The learned projection uses only training-fold dataset labels and is
applied to evaluation subjects without reading their dataset label. It is still
only a lightweight diagnostic control, not a full method.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from dataclasses import dataclass
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

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase5_run_mv01_phq_bridge as mv01
import phase5_run_mv04_dataset_identity_control as mv04


WORKTREE_ROOT = mv01.WORKTREE_ROOT
DEFAULT_OUT_DIR = (
    WORKTREE_ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv04_source_agnostic_identity_projection"
)
DEFAULT_MANIFEST_DIR = mv01.DEFAULT_MANIFEST_DIR
DEFAULT_SPLIT_PATH = mv01.DEFAULT_SPLIT_PATH

SEEDS = mv01.SEEDS
CONSTRUCTS = mv01.CONSTRUCTS
PROJECTION_COMPONENTS = [1, 3, 5, 10]
BASELINE_MODEL = "baseline_pooled_shared_ridge"
TOTAL_ALLOC_MODEL = "total_alloc_ridge"
TRAIN_MEAN_MODEL = "train_mean"
CONTROL_MODEL_PREFIX = "source_agnostic_logit_projection"
PROTOCOL_ID = "pooled_shared_source_agnostic_identity_projection"


@dataclass(frozen=True)
class ProjectionTransform:
    """Train-fold source-agnostic nuisance projection.

    Logistic directions are fitted on training-fold dataset labels, then applied
    to train and evaluation features without using evaluation dataset labels or
    target labels. The fitted directions are not written to disk.
    """

    component_count: int
    fitted_component_count: int
    feature_cols: list[str]
    train_counts: dict[str, int]
    direction_norms: list[float]
    imputer: SimpleImputer
    scaler: StandardScaler
    directions: list[np.ndarray]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    return mv01.safe_float(value)


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def control_model_name(component_count: int) -> str:
    return f"{CONTROL_MODEL_PREFIX}_k{component_count}_shared_ridge"


def feature_representation_name(component_count: int) -> str:
    return f"{CONTROL_MODEL_PREFIX}_k{component_count}_after_control"


def prediction_representation_name(component_count: int) -> str:
    return f"{control_model_name(component_count)}_predictions"


def build_projection_transform(
    train: pd.DataFrame,
    feature_cols: list[str],
    component_count: int,
    seed: int,
) -> tuple[ProjectionTransform, np.ndarray]:
    x_train = train[feature_cols].to_numpy(dtype=float)
    y_train = (train["dataset"].astype(str) == "cmdc").astype(int).to_numpy()
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    z_train = scaler.fit_transform(imputer.fit_transform(x_train))
    directions: list[np.ndarray] = []
    direction_norms: list[float] = []

    for index in range(component_count):
        if len(set(y_train)) < 2:
            break
        classifier = LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=2000,
            random_state=seed + index,
        )
        classifier.fit(z_train, y_train)
        direction = classifier.coef_.reshape(-1).astype(float)
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm < 1e-12:
            break
        unit = direction / norm
        z_train = z_train - np.outer(z_train @ unit, unit)
        directions.append(unit)
        direction_norms.append(norm)

    train_counts = {
        str(dataset): int(group["subject_key"].nunique())
        for dataset, group in train.groupby("dataset", sort=True)
    }
    transform = ProjectionTransform(
        component_count=component_count,
        fitted_component_count=len(directions),
        feature_cols=list(feature_cols),
        train_counts=train_counts,
        direction_norms=direction_norms,
        imputer=imputer,
        scaler=scaler,
        directions=directions,
    )
    return transform, z_train


def apply_projection_transform(frame: pd.DataFrame, transform: ProjectionTransform) -> pd.DataFrame:
    z_values = transform.scaler.transform(
        transform.imputer.transform(frame[transform.feature_cols].to_numpy(dtype=float))
    )
    for unit in transform.directions:
        z_values = z_values - np.outer(z_values @ unit, unit)
    out = frame.copy()
    out.loc[:, transform.feature_cols] = z_values
    return out


def projection_audit_row(seed: int, transform: ProjectionTransform) -> dict[str, Any]:
    return {
        "seed": seed,
        "requested_component_count": transform.component_count,
        "fitted_component_count": transform.fitted_component_count,
        "direction_norm_min": safe_float(min(transform.direction_norms)) if transform.direction_norms else None,
        "direction_norm_max": safe_float(max(transform.direction_norms)) if transform.direction_norms else None,
        "train_edaic_subjects": transform.train_counts.get("edaic", 0),
        "train_cmdc_subjects": transform.train_counts.get("cmdc", 0),
        "control_uses_eval_target_labels": False,
        "control_uses_eval_dataset_labels": False,
        "control_parameters_written": False,
        "transformed_features_written": False,
    }


def add_prediction_metrics(
    predictions: pd.DataFrame,
    seed: int,
    model_name: str,
    prediction_frames: list[pd.DataFrame],
    metric_rows: list[dict[str, Any]],
) -> None:
    predictions = predictions.copy()
    predictions["seed"] = seed
    predictions["protocol"] = PROTOCOL_ID
    prediction_frames.append(predictions)
    metric_rows.extend(mv01.metric_rows_for_predictions(predictions, model_name, PROTOCOL_ID, seed))


def run_experiment(
    table: pd.DataFrame,
    feature_cols: list[str],
    cmdc_folds: dict[int, dict[str, set[str]]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict[str, Any]] = []
    identity_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []

    for seed in SEEDS:
        train, eval_frame, base_audit = mv04.pooled_train_eval_for_seed(table, cmdc_folds, seed)

        train_mean_pred = mv01.predict_train_mean(train, eval_frame, TRAIN_MEAN_MODEL)
        add_prediction_metrics(train_mean_pred, seed, TRAIN_MEAN_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": TRAIN_MEAN_MODEL,
                "feature_transform": "none",
                "selected_alpha": None,
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        total_alloc_pred, total_details = mv01.fit_predict_total_alloc(
            train, eval_frame, feature_cols, seed, TOTAL_ALLOC_MODEL
        )
        add_prediction_metrics(total_alloc_pred, seed, TOTAL_ALLOC_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": TOTAL_ALLOC_MODEL,
                "feature_transform": "none",
                "selected_alpha": total_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        baseline_train_pred, baseline_eval_pred, baseline_details = mv04.fit_predict_constructs_for_train_and_eval(
            train, eval_frame, feature_cols, seed, BASELINE_MODEL
        )
        add_prediction_metrics(baseline_eval_pred, seed, BASELINE_MODEL, prediction_frames, metric_rows)
        audit_rows.append(
            {
                **base_audit,
                "protocol": PROTOCOL_ID,
                "model": BASELINE_MODEL,
                "feature_transform": "raw_frozen_wavlm",
                "selected_alpha": baseline_details.get("selected_alpha"),
                "control_uses_eval_target_labels": False,
                "control_uses_eval_dataset_labels": False,
            }
        )

        identity_rows.append(
            mv04.run_identity_probe(
                train,
                eval_frame,
                feature_cols,
                seed,
                "feature",
                "raw_frozen_wavlm_before_control",
            )
        )
        baseline_train_repr = mv04.prediction_representation(train, baseline_train_pred)
        baseline_eval_repr = mv04.prediction_representation(eval_frame, baseline_eval_pred)
        identity_rows.append(
            mv04.run_identity_probe(
                baseline_train_repr,
                baseline_eval_repr,
                CONSTRUCTS,
                seed,
                "prediction",
                "baseline_pooled_shared_ridge_predictions",
            )
        )

        for component_count in PROJECTION_COMPONENTS:
            transform, projected_train_values = build_projection_transform(
                train, feature_cols, component_count, seed
            )
            projected_train = train.copy()
            projected_train.loc[:, feature_cols] = projected_train_values
            projected_eval = apply_projection_transform(eval_frame, transform)
            model_name = control_model_name(component_count)

            control_train_pred, control_eval_pred, control_details = mv04.fit_predict_constructs_for_train_and_eval(
                projected_train,
                projected_eval,
                feature_cols,
                seed,
                model_name,
            )
            add_prediction_metrics(control_eval_pred, seed, model_name, prediction_frames, metric_rows)
            audit_rows.append(
                {
                    **base_audit,
                    "protocol": PROTOCOL_ID,
                    "model": model_name,
                    "feature_transform": f"source_agnostic_logit_projection_k{component_count}",
                    "selected_alpha": control_details.get("selected_alpha"),
                    "control_uses_eval_target_labels": False,
                    "control_uses_eval_dataset_labels": False,
                    "control_parameters_written": False,
                    "transformed_features_written": False,
                }
            )
            projection_rows.append(projection_audit_row(seed, transform))
            identity_rows.append(
                mv04.run_identity_probe(
                    projected_train,
                    projected_eval,
                    feature_cols,
                    seed,
                    "feature",
                    feature_representation_name(component_count),
                )
            )
            control_train_repr = mv04.prediction_representation(train, control_train_pred)
            control_eval_repr = mv04.prediction_representation(eval_frame, control_eval_pred)
            identity_rows.append(
                mv04.run_identity_probe(
                    control_train_repr,
                    control_eval_repr,
                    CONSTRUCTS,
                    seed,
                    "prediction",
                    prediction_representation_name(component_count),
                )
            )

    return (
        pd.concat(prediction_frames, ignore_index=True),
        pd.DataFrame(metric_rows),
        pd.DataFrame(identity_rows),
        pd.DataFrame(audit_rows),
        pd.DataFrame(projection_rows),
    )


def build_verdict(
    comparison_summary: pd.DataFrame,
    identity_summary: pd.DataFrame,
    worst_slice_summary: pd.DataFrame,
    subject_overlap_violations: int,
) -> dict[str, Any]:
    identity_lookup = identity_summary.set_index(["probe_layer", "representation"])["mean"].to_dict()
    raw_feature_ba = identity_lookup.get(("feature", "raw_frozen_wavlm_before_control"))
    baseline_prediction_ba = identity_lookup.get(("prediction", "baseline_pooled_shared_ridge_predictions"))
    worst_lookup = worst_slice_summary.set_index("model")["relative_delta_vs_baseline"].to_dict()

    rows: list[dict[str, Any]] = []
    for component_count in PROJECTION_COMPONENTS:
        model_name = control_model_name(component_count)
        feature_after = identity_lookup.get(("feature", feature_representation_name(component_count)))
        prediction_after = identity_lookup.get(("prediction", prediction_representation_name(component_count)))
        control_rows = comparison_summary[comparison_summary["model"] == model_name].copy()
        main_within = bool(
            not control_rows.empty
            and (control_rows["relative_delta_vs_baseline"].fillna(float("inf")) <= 0.05).all()
        )
        worst_within = bool(worst_lookup.get(model_name, float("inf")) <= 0.05)
        feature_reduced = bool(
            raw_feature_ba is not None and feature_after is not None and feature_after < raw_feature_ba
        )
        prediction_reduced = bool(
            baseline_prediction_ba is not None
            and prediction_after is not None
            and prediction_after < baseline_prediction_ba
        )
        pass_model = bool(
            subject_overlap_violations == 0
            and main_within
            and worst_within
            and feature_reduced
            and prediction_reduced
        )
        rows.append(
            {
                "model": model_name,
                "component_count": component_count,
                "feature_identity_ba_after": safe_float(feature_after),
                "prediction_identity_ba_after": safe_float(prediction_after),
                "main_task_within_5pct_all_slices": main_within,
                "worst_slice_within_5pct": worst_within,
                "feature_identity_reduced": feature_reduced,
                "prediction_identity_reduced": prediction_reduced,
                "pass_model": pass_model,
            }
        )

    passing = [row for row in rows if row["pass_model"]]
    if passing:
        best = sorted(
            passing,
            key=lambda row: (
                row["prediction_identity_ba_after"]
                if row["prediction_identity_ba_after"] is not None
                else float("inf"),
                row["feature_identity_ba_after"]
                if row["feature_identity_ba_after"] is not None
                else float("inf"),
            ),
        )[0]
    else:
        best = sorted(
            rows,
            key=lambda row: (
                row["prediction_identity_ba_after"]
                if row["prediction_identity_ba_after"] is not None
                else float("inf"),
                row["feature_identity_ba_after"]
                if row["feature_identity_ba_after"] is not None
                else float("inf"),
            ),
        )[0]

    residual_feature_identity_high = bool(
        best["feature_identity_ba_after"] is None or best["feature_identity_ba_after"] > 0.75
    )
    if passing and residual_feature_identity_high:
        status = "partial_pass_identity_reduced_not_removed"
        short_read = (
            "The source-agnostic projection reduces held-out prediction identity and preserves PHQ C01-C08 Macro MAE within tolerance, but feature-layer dataset identity remains high; treat it as a partial diagnostic control and keep full-method claims blocked."
        )
    elif passing:
        status = "pass_source_agnostic_control"
        short_read = (
            "The source-agnostic projection reduces held-out identity probes while preserving PHQ C01-C08 Macro MAE within tolerance."
        )
    else:
        status = "blocked_source_agnostic_control"
        short_read = (
            "The source-agnostic projection is runnable, but no tested projection variant satisfies identity-reduction and main-task preservation gates together."
        )

    return {
        "pass_rule_status": status,
        "pass_rule_met": bool(passing),
        "short_read": short_read,
        "raw_feature_identity_ba": safe_float(raw_feature_ba),
        "baseline_prediction_identity_ba": safe_float(baseline_prediction_ba),
        "best_control_model": best["model"],
        "best_control_component_count": best["component_count"],
        "best_feature_identity_ba_after": safe_float(best["feature_identity_ba_after"]),
        "best_prediction_identity_ba_after": safe_float(best["prediction_identity_ba_after"]),
        "residual_feature_identity_high": residual_feature_identity_high,
        "subject_overlap_violations": subject_overlap_violations,
        "model_verdicts": rows,
    }


def artifact_hygiene_audit(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"\.wav\b",
        r"\.WAV\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"Transcript",
        r"raw prompt",
        r"raw response",
        r"PHQ_8Depressed",
        r"PHQ_8NoInterest",
        r"PHQ_8Sleep",
        r"PHQ_8Tired",
        r"PHQ_8Appetite",
        r"PHQ_8Failure",
        r"PHQ_8Concentrating",
        r"PHQ_8Moving",
    ]
    violations: list[dict[str, Any]] = []
    files_checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                violations.append({"file": str(path.relative_to(out_dir)), "pattern": pattern})
    return {
        "audit_id": "P5_MV04b_source_agnostic_projection_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": files_checked,
        "violation_count": len(violations),
        "violations": violations,
        "artifact_hygiene_passed": len(violations) == 0,
        "local_only_patterns": [
            "analysis/phase5_minimal_validation/**/*predictions*.csv",
            "analysis/phase5_minimal_validation/**/*features*.csv",
            "analysis/phase5_minimal_validation/**/*embeddings*.csv",
            "analysis/phase5_minimal_validation/**/*model*.joblib",
            "analysis/phase5_minimal_validation/**/*model*.pkl",
            "analysis/phase5_minimal_validation/**/*weights*.csv",
        ],
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    metric_summary: pd.DataFrame,
    comparison_summary: pd.DataFrame,
    identity_summary: pd.DataFrame,
    worst_slice_summary: pd.DataFrame,
) -> None:
    macro = metric_summary[
        (metric_summary["construct_id"] == "macro")
        & (metric_summary["metric"] == "Macro Construct MAE")
        & (metric_summary["dataset_slice"] != "pooled")
    ].sort_values(["model", "dataset_slice"])
    comparison = comparison_summary.sort_values(["dataset_slice", "model"])
    identity = identity_summary.sort_values(["probe_layer", "representation"])
    worst = worst_slice_summary.sort_values("model")

    lines = [
        "# P5_MV04b Source-Agnostic Identity Projection",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This follow-up targets the remaining P5_MV04 caveat: train-fold dataset centering reduced identity but used known evaluation dataset labels. Here, iterative logistic nuisance directions are fitted on training-fold dataset labels and applied to held-out subjects without using evaluation dataset labels or targets. No encoder fine-tuning, raw-directory scan, transformed feature export, learned representation export, or model checkpoint export is used.",
        "",
        "## Feature And Split Contract",
        "",
        f"- Common frozen WavLM columns: `{run_summary['feature_contract']['common_feature_column_count']}`.",
        f"- E-DAIC subjects joined: `{run_summary['feature_contract']['joined_subjects']['edaic']}`; official train/dev only.",
        f"- CMDC subjects joined: `{run_summary['feature_contract']['joined_subjects']['cmdc']}`; Phase 2 subject CV folds.",
        f"- Subject-overlap violations: `{run_summary['split_audit']['subject_overlap_violations']}`.",
        f"- Control uses eval target labels: `{run_summary['model_contract']['control_uses_eval_target_labels']}`.",
        f"- Control uses eval dataset labels: `{run_summary['model_contract']['control_uses_eval_dataset_labels']}`.",
        f"- Projection component counts tested: `{', '.join(map(str, run_summary['model_contract']['projection_component_counts']))}`.",
        "",
        "## Dataset-Stratified Macro MAE",
        "",
        "| model | dataset | macro MAE | seed count |",
        "| --- | --- | ---: | ---: |",
    ]
    for _, row in macro.iterrows():
        lines.append(
            f"| {row['model']} | {row['dataset_slice']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )

    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "Negative MAE deltas are improvements. Relative delta is versus the raw pooled shared Ridge baseline.",
            "",
            "| dataset | model | delta vs train_mean | delta vs total_alloc | delta vs baseline | relative delta vs baseline |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['dataset_slice']} | {row['model']} | {format_value(row['delta_vs_train_mean'])} | {format_value(row['delta_vs_total_alloc_ridge'])} | {format_value(row['delta_vs_baseline_pooled_shared_ridge'])} | {format_value(row['relative_delta_vs_baseline'])} |"
        )

    lines.extend(
        [
            "",
            "## Worst Slice",
            "",
            "| model | worst-slice Macro MAE | delta vs baseline | relative delta vs baseline |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in worst.iterrows():
        lines.append(
            f"| {row['model']} | {format_value(row['mean'])} | {format_value(row['delta_vs_baseline_pooled_shared_ridge'])} | {format_value(row['relative_delta_vs_baseline'])} |"
        )

    lines.extend(
        [
            "",
            "## Dataset Identity Probes",
            "",
            "| layer | representation | identity balanced accuracy | seed count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for _, row in identity.iterrows():
        lines.append(
            f"| {row['probe_layer']} | {row['representation']} | {format_value(row['mean'])} | {int(row['seed_count'])} |"
        )

    verdict = run_summary["verdict"]
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
            f"- Best control model: `{verdict['best_control_model']}`.",
            f"- Feature identity BA before/best-after: `{format_value(verdict['raw_feature_identity_ba'])}` -> `{format_value(verdict['best_feature_identity_ba_after'])}`.",
            f"- Prediction identity BA baseline/best-control: `{format_value(verdict['baseline_prediction_identity_ba'])}` -> `{format_value(verdict['best_prediction_identity_ba_after'])}`.",
            f"- Residual feature identity remains high: `{verdict['residual_feature_identity_high']}`.",
            "",
            verdict["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Row-level predictions are written as a local-only ignored CSV.",
            "- Transformed features, learned projection directions, model weights, source snippets, prompt/response text, audio, and video are not written.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--phase2-root", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    phase2_root, phase2_root_source = mv01.resolve_phase2_root(args.phase2_root)
    table, feature_cols, availability = mv01.build_model_table(args.manifest_dir, phase2_root)
    cmdc_folds = mv01.load_cmdc_folds(args.split_path)
    predictions, metrics_by_seed, identity_by_seed, model_audit, projection_audit = run_experiment(
        table, feature_cols, cmdc_folds
    )

    metric_summary = mv04.summarize_metrics(metrics_by_seed)
    comparison_summary = mv04.build_comparison_summary(metric_summary)
    worst_slice_by_seed, worst_slice_summary = mv04.build_worst_slice_tables(metrics_by_seed)
    identity_summary = mv04.summarize_identity(identity_by_seed)
    subject_overlap_violations = int(model_audit["subject_overlap_count"].sum()) + int(
        identity_by_seed["subject_overlap_count"].sum()
    )
    verdict = build_verdict(comparison_summary, identity_summary, worst_slice_summary, subject_overlap_violations)

    safe_predictions = predictions.copy()
    safe_predictions["item_code"] = (
        safe_predictions["eval_dataset"].map({"edaic": "PHQ8_", "cmdc": "PHQ9_"})
        + safe_predictions["construct_id"]
    )

    target_map = mv04.target_map_frame()
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison_summary.to_csv(out_dir / "comparison_summary.csv", index=False)
    worst_slice_by_seed.to_csv(out_dir / "worst_slice_by_seed.csv", index=False)
    worst_slice_summary.to_csv(out_dir / "worst_slice_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "dataset_identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "dataset_identity_probe_summary.csv", index=False)
    availability.to_csv(out_dir / "feature_availability.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    projection_audit.to_csv(out_dir / "projection_audit.csv", index=False)
    target_map.to_csv(out_dir / "construct_target_map.csv", index=False)
    safe_predictions.to_csv(out_dir / "p5_mv04b_local_predictions.csv", index=False)

    run_summary: dict[str, Any] = {
        "run_id": "P5_MV04b_source_agnostic_identity_projection",
        "generated_at": utc_now(),
        "status": "complete",
        "phase2_feature_root_source": phase2_root_source,
        "feature_contract": {
            "feature_space": "frozen_wavlm_subject_mean",
            "common_feature_column_count": len(feature_cols),
            "joined_subjects": availability.set_index("dataset")["joined_subjects"].astype(int).to_dict(),
        },
        "target_contract": {
            "constructs": CONSTRUCTS,
            "source_scales": {"edaic": "PHQ-8", "cmdc": "PHQ-9"},
            "c09_policy": "excluded_from_core_bridge_safety_sensitive_phq9_only",
        },
        "model_contract": {
            "models": [TRAIN_MEAN_MODEL, TOTAL_ALLOC_MODEL, BASELINE_MODEL]
            + [control_model_name(component_count) for component_count in PROJECTION_COMPONENTS],
            "seeds": SEEDS,
            "encoder_finetuning": False,
            "raw_audio_scan": False,
            "control_variant": "train_fold_source_agnostic_iterative_logit_projection",
            "projection_component_counts": PROJECTION_COMPONENTS,
            "control_uses_eval_target_labels": False,
            "control_uses_eval_dataset_labels": False,
            "control_parameters_written": False,
        },
        "split_audit": {
            "subject_level": True,
            "edaic_official_test_used": False,
            "cmdc_phase2_subject_cv_used": True,
            "subject_overlap_violations": subject_overlap_violations,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "learned_embeddings": "not_written",
            "transformed_features": "not_written",
            "model_weights": "not_written",
            "projection_directions": "not_written",
            "raw_clinical_text": "not_written",
            "raw_prompts_or_responses": "not_written",
        },
        "artifact_hygiene_passed": False,
        "verdict": verdict,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "metric_summary.csv",
            "metrics_by_seed.csv",
            "comparison_summary.csv",
            "worst_slice_summary.csv",
            "worst_slice_by_seed.csv",
            "dataset_identity_probe_summary.csv",
            "dataset_identity_probe_by_seed.csv",
            "feature_availability.csv",
            "model_split_audit.csv",
            "projection_audit.csv",
            "construct_target_map.csv",
        ],
        "local_only_files": ["p5_mv04b_local_predictions.csv"],
    }

    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary, worst_slice_summary)
    hygiene = artifact_hygiene_audit(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, metric_summary, comparison_summary, identity_summary, worst_slice_summary)
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")


if __name__ == "__main__":
    main()
