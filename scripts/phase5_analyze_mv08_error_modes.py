#!/usr/bin/env python3
"""Aggregate-only error analysis for the negative P5_MV08 pilot.

This script may read the ignored local MV08 row-prediction file, but it exports
only aggregate diagnostics. No subject identifiers, local paths, raw text,
latent scores, learned parameters, or model files are written.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MV08_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv08_partial_invariance_measurement"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv08_error_analysis"
LOCAL_PREDICTIONS = MV08_DIR / "p5_mv08_local_row_predictions.csv"

RUN_ID = "P5_MV08_error_analysis"
MODELS = [
    "M0_train_mean_items",
    "M0_total_score_floor",
    "M1_fixed_construct_map",
    "M2_partial_invariance_ordinal",
]
MODEL_SHORT = {
    "M0_train_mean_items": "train_mean",
    "M0_total_score_floor": "total_floor",
    "M1_fixed_construct_map": "fixed_map",
    "M2_partial_invariance_ordinal": "m2_partial_invariance",
}
M2 = "M2_partial_invariance_ordinal"
TOTAL_FLOOR = "M0_total_score_floor"
FIXED_MAP = "M1_fixed_construct_map"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "construct_error_diagnostics.csv",
    "error_bin_summary.csv",
    "item_error_diagnostics.csv",
    "report.md",
    "revision_queue.csv",
    "run_summary.json",
    "slice_error_diagnostics.csv",
    "threshold_sparsity_diagnostics.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def load_required_csv(path: Path, required: set[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{rel(path)} missing required columns: {missing}")
    return frame


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    predictions = load_required_csv(
        LOCAL_PREDICTIONS,
        {
            "protocol",
            "model",
            "seed",
            "fold",
            "eval_dataset",
            "scale",
            "subject_key",
            "item_id",
            "item_code",
            "construct_id",
            "head_group",
            "dif_policy",
            "item_max",
            "y_true",
            "y_pred",
            "y_pred_rounded",
        },
    )
    comparison = load_required_csv(
        MV08_DIR / "comparison_summary.csv",
        {"protocol", "dataset_slice", "scale", "model", "macro_item_mae"},
    )
    construct_map = load_required_csv(
        MV08_DIR / "construct_target_map.csv",
        {
            "dataset",
            "scale",
            "item_code",
            "item_label_short",
            "primary_construct",
            "mapping_strength",
        },
    )
    thresholds = load_required_csv(
        MV08_DIR / "dif_sparsity_summary.csv",
        {
            "protocol",
            "head_group",
            "dif_policy",
            "train_observations",
            "threshold_count",
            "learned_threshold_models",
            "constant_threshold_models",
        },
    )
    return predictions, comparison, construct_map, thresholds


def wide_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    key_cols = [
        "protocol",
        "seed",
        "fold",
        "eval_dataset",
        "scale",
        "subject_key",
        "item_id",
        "item_code",
        "construct_id",
        "head_group",
        "dif_policy",
        "item_max",
        "y_true",
    ]
    selected = predictions[predictions["model"].isin(MODELS)].copy()
    wide = selected.pivot_table(
        index=key_cols,
        columns="model",
        values=["y_pred", "y_pred_rounded"],
        aggfunc="first",
    )
    wide.columns = [f"{MODEL_SHORT[model]}_{value}" for value, model in wide.columns]
    wide = wide.reset_index()
    required = [f"{MODEL_SHORT[model]}_y_pred" for model in MODELS]
    missing = [column for column in required if column not in wide.columns]
    if missing:
        raise ValueError(f"wide predictions missing model columns: {missing}")
    for model in MODELS:
        short = MODEL_SHORT[model]
        wide[f"{short}_abs_error"] = (wide[f"{short}_y_pred"] - wide["y_true"]).abs()
        rounded_col = f"{short}_y_pred_rounded"
        if rounded_col in wide.columns:
            wide[f"{short}_rounded_abs_error"] = (wide[rounded_col] - wide["y_true"]).abs()
            wide[f"{short}_rounded_over"] = (wide[rounded_col] > wide["y_true"]).astype(float)
            wide[f"{short}_rounded_under"] = (wide[rounded_col] < wide["y_true"]).astype(float)
            wide[f"{short}_rounded_within1"] = (wide[f"{short}_rounded_abs_error"] <= 1).astype(float)
    wide["m2_delta_abs_error_vs_total_floor"] = (
        wide["m2_partial_invariance_abs_error"] - wide["total_floor_abs_error"]
    )
    wide["m2_delta_abs_error_vs_fixed_map"] = (
        wide["m2_partial_invariance_abs_error"] - wide["fixed_map_abs_error"]
    )
    wide["m2_bias"] = wide["m2_partial_invariance_y_pred"] - wide["y_true"]
    wide["true_score_bin"] = wide["y_true"].round().astype(int).astype(str)
    return wide


def compression_ratio(pred: pd.Series, truth: pd.Series) -> float | None:
    pred_std = safe_float(pred.std(ddof=0))
    truth_std = safe_float(truth.std(ddof=0))
    if pred_std is None or truth_std is None or truth_std <= 1e-12:
        return None
    return pred_std / truth_std


def aggregate_group(group: pd.DataFrame) -> dict[str, Any]:
    row: dict[str, Any] = {
        "eval_row_count": int(len(group)),
        "eval_subject_count": int(group["subject_key"].nunique()),
        "y_true_mean": safe_float(group["y_true"].mean()),
        "y_true_sd": safe_float(group["y_true"].std(ddof=0)),
        "nonzero_true_rate": safe_float((group["y_true"] > 0).mean()),
        "max_true_rate": safe_float((group["y_true"] >= group["item_max"]).mean()),
        "m2_pred_mean": safe_float(group["m2_partial_invariance_y_pred"].mean()),
        "m2_pred_sd": safe_float(group["m2_partial_invariance_y_pred"].std(ddof=0)),
        "m2_bias_mean": safe_float(group["m2_bias"].mean()),
        "m2_bias_abs_mean": safe_float(group["m2_bias"].abs().mean()),
        "m2_large_rounded_error_rate": safe_float((group["m2_partial_invariance_rounded_abs_error"] > 1).mean()),
        "m2_rounded_within1_rate": safe_float(group["m2_partial_invariance_rounded_within1"].mean()),
        "m2_rounded_over_rate": safe_float(group["m2_partial_invariance_rounded_over"].mean()),
        "m2_rounded_under_rate": safe_float(group["m2_partial_invariance_rounded_under"].mean()),
        "m2_prediction_compression_ratio": compression_ratio(
            group["m2_partial_invariance_y_pred"], group["y_true"]
        ),
    }
    for model in MODELS:
        short = MODEL_SHORT[model]
        row[f"{short}_mae"] = safe_float(group[f"{short}_abs_error"].mean())
    row["m2_delta_mae_vs_total_floor"] = safe_float(group["m2_delta_abs_error_vs_total_floor"].mean())
    row["m2_delta_mae_vs_fixed_map"] = safe_float(group["m2_delta_abs_error_vs_fixed_map"].mean())
    return row


def aggregate_by(wide: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in wide.groupby(columns, sort=True, dropna=False):
        values = key if isinstance(key, tuple) else (key,)
        row = dict(zip(columns, values))
        row.update(aggregate_group(group))
        rows.append(row)
    return pd.DataFrame(rows)


def item_error_diagnostics(wide: pd.DataFrame, construct_map: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "protocol",
        "eval_dataset",
        "scale",
        "item_code",
        "construct_id",
        "head_group",
        "dif_policy",
    ]
    out = aggregate_by(wide, columns)
    labels = construct_map[
        [
            "dataset",
            "scale",
            "item_code",
            "item_label_short",
            "mapping_strength",
        ]
    ].rename(columns={"dataset": "eval_dataset"})
    out = out.merge(labels, on=["eval_dataset", "scale", "item_code"], how="left", validate="many_to_one")
    ordered = [
        "protocol",
        "eval_dataset",
        "scale",
        "item_code",
        "item_label_short",
        "construct_id",
        "head_group",
        "dif_policy",
        "mapping_strength",
    ]
    tail = [column for column in out.columns if column not in ordered]
    return out[ordered + tail].sort_values(
        ["protocol", "eval_dataset", "m2_delta_mae_vs_total_floor", "item_code"],
        ascending=[True, True, False, True],
    )


def construct_error_diagnostics(wide: pd.DataFrame) -> pd.DataFrame:
    out = aggregate_by(wide, ["protocol", "eval_dataset", "scale", "construct_id", "dif_policy"])
    return out.sort_values(
        ["protocol", "eval_dataset", "m2_delta_mae_vs_total_floor", "construct_id"],
        ascending=[True, True, False, True],
    )


def slice_error_diagnostics(wide: pd.DataFrame, comparison: pd.DataFrame) -> pd.DataFrame:
    out = aggregate_by(wide, ["protocol", "eval_dataset", "scale"])
    # comparison_summary has one row per model/slice; use only macro item MAE.
    pivot = comparison.pivot_table(
        index=["protocol", "dataset_slice", "scale"],
        columns="model",
        values="macro_item_mae",
        aggfunc="first",
    ).reset_index()
    pivot = pivot.rename(
        columns={
            "dataset_slice": "eval_dataset",
            TOTAL_FLOOR: "comparison_total_floor_macro_mae",
            FIXED_MAP: "comparison_fixed_map_macro_mae",
            M2: "comparison_m2_macro_mae",
        }
    )
    keep = [
        "protocol",
        "eval_dataset",
        "scale",
        "comparison_total_floor_macro_mae",
        "comparison_fixed_map_macro_mae",
        "comparison_m2_macro_mae",
    ]
    pivot = pivot[[column for column in keep if column in pivot.columns]]
    out = out.merge(pivot, on=["protocol", "eval_dataset", "scale"], how="left", validate="one_to_one")
    out["m2_failed_total_floor"] = out["m2_delta_mae_vs_total_floor"] > 0
    out["m2_failed_fixed_map"] = out["m2_delta_mae_vs_fixed_map"] > 0
    return out.sort_values(["protocol", "eval_dataset"])


def error_bin_summary(wide: pd.DataFrame) -> pd.DataFrame:
    out = aggregate_by(wide, ["protocol", "eval_dataset", "scale", "true_score_bin"])
    return out.sort_values(["protocol", "eval_dataset", "scale", "true_score_bin"])


def threshold_sparsity_diagnostics(thresholds: pd.DataFrame, item_errors: pd.DataFrame) -> pd.DataFrame:
    frame = thresholds.copy()
    frame["constant_threshold_fraction"] = np.where(
        frame["threshold_count"].astype(float) > 0,
        frame["constant_threshold_models"].astype(float) / frame["threshold_count"].astype(float),
        np.nan,
    )
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(["protocol", "dif_policy"], sort=True, dropna=False):
        protocol, dif_policy = key
        related = item_errors[(item_errors["protocol"] == protocol) & (item_errors["dif_policy"] == dif_policy)]
        rows.append(
            {
                "protocol": protocol,
                "dif_policy": dif_policy,
                "head_group_count": int(group["head_group"].nunique()),
                "min_train_observations": int(group["train_observations"].min()),
                "mean_train_observations": safe_float(group["train_observations"].mean()),
                "threshold_count": int(group["threshold_count"].sum()),
                "learned_threshold_models": int(group["learned_threshold_models"].sum()),
                "constant_threshold_models": int(group["constant_threshold_models"].sum()),
                "constant_threshold_fraction": safe_float(
                    group["constant_threshold_models"].sum() / group["threshold_count"].sum()
                    if group["threshold_count"].sum()
                    else np.nan
                ),
                "mean_head_constant_threshold_fraction": safe_float(group["constant_threshold_fraction"].mean()),
                "mean_m2_delta_mae_vs_total_floor": safe_float(
                    related["m2_delta_mae_vs_total_floor"].mean() if not related.empty else np.nan
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["protocol", "dif_policy"])


def revision_queue(
    slice_diag: pd.DataFrame,
    item_diag: pd.DataFrame,
    threshold_diag: pd.DataFrame,
) -> pd.DataFrame:
    pooled = slice_diag[slice_diag["protocol"] == "pooled_partial_invariance"].copy()
    top_items = item_diag[item_diag["protocol"] == "pooled_partial_invariance"].head(5)
    worst_slice = pooled.sort_values("m2_delta_mae_vs_total_floor", ascending=False).head(1)
    worst_slice_text = ""
    if not worst_slice.empty:
        row = worst_slice.iloc[0]
        worst_slice_text = (
            f"{row['eval_dataset']}/{row['scale']} delta_vs_total="
            f"{fmt(row['m2_delta_mae_vs_total_floor'])}"
        )
    top_item_text = "; ".join(
        f"{row.eval_dataset}/{row.item_code}({row.construct_id})={fmt(row.m2_delta_mae_vs_total_floor)}"
        for row in top_items.itertuples(index=False)
    )
    shared_phq = item_diag[
        (item_diag["protocol"] == "pooled_partial_invariance")
        & (item_diag["dif_policy"] == "shared_phq_anchor")
    ]
    hamd = item_diag[
        (item_diag["protocol"] == "pooled_partial_invariance")
        & (item_diag["scale"] == "HAMD-17")
    ]
    sparse = threshold_diag.sort_values("constant_threshold_fraction", ascending=False).head(1)
    sparse_text = ""
    if not sparse.empty:
        row = sparse.iloc[0]
        sparse_text = (
            f"{row['protocol']}/{row['dif_policy']} constant_threshold_fraction="
            f"{fmt(row['constant_threshold_fraction'])}"
        )

    rows = [
        {
            "priority": 1,
            "action_id": "FREEZE_MV08_CURRENT_CONTRACT_AS_NEGATIVE",
            "evidence_trigger": (
                "M2 failed the total-score floor on all pooled active slices; "
                f"worst slice: {worst_slice_text}; top item deltas: {top_item_text}."
            ),
            "recommended_change": "Do not claim partial-invariance measurement success from the current frozen-BGE ordinal head.",
            "success_gate": "Use MV08 as negative diagnostic evidence unless a new predeclared MV08b contract changes the measurement mechanism.",
            "version_policy": "Tracked aggregate evidence only; local row predictions remain ignored.",
        },
        {
            "priority": 2,
            "action_id": "MV08B_TOTAL_ANCHORED_RESIDUAL_ITEM_MODEL",
            "evidence_trigger": (
                "The total-score floor is the best or near-best comparator in every pooled active slice; "
                f"mean shared-PHQ delta_vs_total={fmt(shared_phq['m2_delta_mae_vs_total_floor'].mean())}."
            ),
            "recommended_change": (
                "If revising, predeclare a total-anchored measurement model that predicts severity first "
                "and models item residual structure only when it beats the total floor."
            ),
            "success_gate": "MV08b must beat total-score and fixed-map floors on at least two pooled active slices and avoid higher prediction identity.",
            "version_policy": "Track only scripts and aggregate diagnostics; keep residual predictions and fitted parameters local-only.",
        },
        {
            "priority": 3,
            "action_id": "MV08B_THRESHOLD_POOLING_OR_COLLAPSE",
            "evidence_trigger": sparse_text or "Several ordinal threshold heads are sparse or constant in the current pilot.",
            "recommended_change": (
                "Pool thresholds more aggressively, collapse rare score levels, or fit ordinal thresholds jointly "
                "instead of independent one-vs-threshold logistic heads."
            ),
            "success_gate": "Threshold diagnostics show fewer constant thresholds and improved item MAE without losing rounded-within-one accuracy.",
            "version_policy": "Do not export learned thresholds; export only aggregate sparsity and metric summaries.",
        },
        {
            "priority": 4,
            "action_id": "MV08B_HAMD_AS_SEPARATE_EXTERNAL_MEASUREMENT_TEST",
            "evidence_trigger": (
                f"Pooled HAMD mean delta_vs_total={fmt(hamd['m2_delta_mae_vs_total_floor'].mean())}; "
                "PDCH remains the only adequately sized HAMD item source."
            ),
            "recommended_change": (
                "Keep HAMD as a separate clinical measurement stress test unless a stronger HAMD-compatible "
                "feature/measurement contract is introduced."
            ),
            "success_gate": "Any HAMD revision must improve PDCH item and item-derived total metrics beyond total-score and train-mean floors.",
            "version_policy": "No CMDC HAMD transfer claim from the current 25-subject sanity subset.",
        },
    ]
    return pd.DataFrame(rows)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"subject_id",
        r"subject_key",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"local_text",
        r"local_excerpt",
        r"raw text",
        r"raw snippet",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": rel(path), "pattern": pattern})
    return {
        "audit_id": "P5_MV08_error_analysis_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "violation_count": len(violations),
        "violations": violations,
        "artifact_hygiene_passed": len(violations) == 0,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    slice_diag: pd.DataFrame,
    item_diag: pd.DataFrame,
    threshold_diag: pd.DataFrame,
    revision: pd.DataFrame,
) -> None:
    pooled = slice_diag[slice_diag["protocol"] == "pooled_partial_invariance"].copy()
    top_items = item_diag[item_diag["protocol"] == "pooled_partial_invariance"].head(8)
    threshold_top = threshold_diag.sort_values("constant_threshold_fraction", ascending=False).head(6)
    lines = [
        "# P5_MV08 Error Analysis",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Error-analysis status: `{run_summary['decision']['error_analysis_status']}`.",
        f"- Current MV08 claimable as positive RQ1 evidence: `{run_summary['decision']['current_mv08_claimable_positive_rq1']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Pooled Slice Failures",
        "",
        "| dataset | scale | M2 row-weighted MAE | delta vs total | delta vs fixed | M2 bias | rounded within 1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in pooled.iterrows():
        lines.append(
            f"| {row['eval_dataset']} | {row['scale']} | {fmt(row['m2_partial_invariance_mae'])} | "
            f"{fmt(row['m2_delta_mae_vs_total_floor'])} | {fmt(row['m2_delta_mae_vs_fixed_map'])} | "
            f"{fmt(row['m2_bias_mean'])} | {fmt(row['m2_rounded_within1_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Largest Pooled Item Deltas",
            "",
            "| dataset | item | construct | policy | delta vs total | M2 bias | true mean | M2 pred mean |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in top_items.iterrows():
        lines.append(
            f"| {row['eval_dataset']} | {row['item_code']} | {row['construct_id']} | {row['dif_policy']} | "
            f"{fmt(row['m2_delta_mae_vs_total_floor'])} | {fmt(row['m2_bias_mean'])} | "
            f"{fmt(row['y_true_mean'])} | {fmt(row['m2_pred_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Threshold Sparsity",
            "",
            "| protocol | DIF policy | heads | constant threshold fraction | mean M2 delta vs total |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in threshold_top.iterrows():
        lines.append(
            f"| {row['protocol']} | {row['dif_policy']} | {int(row['head_group_count'])} | "
            f"{fmt(row['constant_threshold_fraction'])} | {fmt(row['mean_m2_delta_mae_vs_total_floor'])} |"
        )
    lines.extend(
        [
            "",
            "## Revision Queue",
            "",
            "| priority | action | success gate |",
            "| ---: | --- | --- |",
        ]
    )
    for _, row in revision.iterrows():
        lines.append(f"| {int(row['priority'])} | {row['recommended_change']} | {row['success_gate']} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This analysis reads a local ignored row-prediction file but exports only aggregate diagnostics.",
            "- It does not authorize full-method construction or a positive shared-measurement claim.",
            "- Any MV08b revision must be predeclared and compared against the same simple floors.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists() and args.overwrite:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    predictions, comparison, construct_map, thresholds = load_inputs()
    wide = wide_predictions(predictions)
    item_diag = item_error_diagnostics(wide, construct_map)
    construct_diag = construct_error_diagnostics(wide)
    slice_diag = slice_error_diagnostics(wide, comparison)
    bin_diag = error_bin_summary(wide)
    threshold_diag = threshold_sparsity_diagnostics(thresholds, item_diag)
    revision = revision_queue(slice_diag, item_diag, threshold_diag)

    pooled = slice_diag[slice_diag["protocol"] == "pooled_partial_invariance"].copy()
    failed_total = int((pooled["m2_delta_mae_vs_total_floor"] > 0).sum())
    failed_fixed = int((pooled["m2_delta_mae_vs_fixed_map"] > 0).sum())
    active_slices = int(len(pooled))
    worst_total_delta = safe_float(pooled["m2_delta_mae_vs_total_floor"].max())
    worst_fixed_delta = safe_float(pooled["m2_delta_mae_vs_fixed_map"].max())
    status = (
        "complete_current_mv08_not_claimable_revision_or_freeze"
        if failed_total == active_slices
        else "complete_partial_failure_requires_review"
    )

    item_diag.to_csv(out_dir / "item_error_diagnostics.csv", index=False)
    construct_diag.to_csv(out_dir / "construct_error_diagnostics.csv", index=False)
    slice_diag.to_csv(out_dir / "slice_error_diagnostics.csv", index=False)
    bin_diag.to_csv(out_dir / "error_bin_summary.csv", index=False)
    threshold_diag.to_csv(out_dir / "threshold_sparsity_diagnostics.csv", index=False)
    revision.to_csv(out_dir / "revision_queue.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "aggregate_error_analysis_for_negative_mv08_no_new_model",
        "input_contract": {
            "local_row_predictions_read": True,
            "raw_data_scanned": False,
            "raw_text_read": False,
            "subject_level_rows_exported": False,
            "learned_parameters_written": False,
            "latent_scores_written": False,
        },
        "decision": {
            "error_analysis_status": status,
            "current_mv08_claimable_positive_rq1": False,
            "pooled_active_slices": active_slices,
            "pooled_slices_failed_total_floor": failed_total,
            "pooled_slices_failed_fixed_map": failed_fixed,
            "worst_pooled_delta_vs_total_floor": worst_total_delta,
            "worst_pooled_delta_vs_fixed_map": worst_fixed_delta,
            "short_read": (
                "MV08 error analysis confirms the current partial-invariance ordinal head should be frozen as negative evidence "
                "unless a predeclared MV08b revision changes the measurement mechanism. The total-score floor remains the key comparator."
            ),
        },
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_inputs": [LOCAL_PREDICTIONS.name],
            "private_identifiers_exported": False,
            "raw_paths_exported": False,
            "raw_text_exported": False,
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, slice_diag, item_diag, threshold_diag, revision)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, slice_diag, item_diag, threshold_diag, revision)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "error_analysis_status": status,
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
