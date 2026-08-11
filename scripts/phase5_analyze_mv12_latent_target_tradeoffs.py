#!/usr/bin/env python3
"""Analyze MV12 latent-target trade-offs from aggregate artifacts only.

This is a post-run diagnostic, not a trainer. It reads aggregate summaries
from MV07/MV07b/MV07c/MV08/MV08b/MV09/MV12, decomposes the MV12 gate failure,
extends the accuracy-identity Pareto table with MV12 rows, and recommends
whether the current latent-target line should be frozen before manuscript
drafting.

It does not read row-level predictions, theta target tables, fitted
measurement parameters, transformed features, raw text/media, or private
annotation workbooks.
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
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis"

MV09_PARETO = PHASE5_DIR / "p5_mv09_conditional_identity_audit" / "accuracy_invariance_pareto_summary.csv"
MV09_SUMMARY = PHASE5_DIR / "p5_mv09_conditional_identity_audit" / "run_summary.json"
MV12_DIR = PHASE5_DIR / "p5_mv12_two_stage_latent_target"
MV12_SUMMARY = MV12_DIR / "run_summary.json"
MV12_COMPARISON = MV12_DIR / "comparison_summary.csv"
MV12_IDENTITY = MV12_DIR / "identity_probe_summary.csv"
MV12_TRANSFER = MV12_DIR / "transfer_summary.csv"
MV12_TARGET_GENERATION = MV12_DIR / "target_generation_summary.csv"
MV12_TARGET_RELIABILITY = MV12_DIR / "target_reliability_summary.csv"

RUN_ID = "P5_MV12_latent_target_tradeoff_analysis"

TRACKED_FILES = [
    "accuracy_identity_tradeoff_summary.csv",
    "artifact_hygiene_audit.json",
    "failure_mode_summary.csv",
    "gate_decomposition.csv",
    "mechanism_recommendation_queue.csv",
    "mv12_dataset_slice_diagnostics.csv",
    "report.md",
    "run_summary.json",
    "source_artifact_summary.csv",
]

MV12_M12A = "M12a_BGE_Ridge_X_to_theta"
MV12_M12B = "M12b_projected_BGE_X_to_theta"
MV12_B3 = "B3_direct_itemwise_ridge"
MV12_B2 = "B2_direct_total_allocation_ridge"
MV12_B1 = "B1_train_mean_observed_total"
MV12_B0 = "B0_train_mean_theta"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def require_inputs() -> None:
    for path in [
        MV09_PARETO,
        MV09_SUMMARY,
        MV12_SUMMARY,
        MV12_COMPARISON,
        MV12_IDENTITY,
        MV12_TRANSFER,
        MV12_TARGET_GENERATION,
        MV12_TARGET_RELIABILITY,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)


def identity_lookup(identity: pd.DataFrame, probe_id: str, model: str) -> float | None:
    rows = identity[(identity["probe_id"] == probe_id) & (identity["model"] == model)]
    if rows.empty:
        return None
    return safe_float(rows.iloc[0]["mean"])


def mv12_pooled_model_rows(comparison: pd.DataFrame, identity: pd.DataFrame) -> pd.DataFrame:
    pooled = comparison[
        (comparison["protocol"] == "pooled_shared_phq")
        & comparison["dataset_slice"].isin(["edaic", "cmdc"])
    ].copy()
    rows: list[dict[str, Any]] = []
    for model, group in pooled.groupby("model", sort=True):
        feature_identity = None
        feature_identity_source = "not_estimated_in_mv12"
        if model in {MV12_B2, MV12_B3, MV12_M12A}:
            feature_identity = 1.0
            feature_identity_source = "MV07_raw_BGE_reference"
        elif model == MV12_M12B:
            feature_identity = 0.7094642857142857
            feature_identity_source = "MV07b_k10_projected_BGE_reference"
        rows.append(
            {
                "source_run": "P5_MV12",
                "family": "two_stage_latent_target_phq",
                "model": model,
                "evaluation_scope": "pooled_shared_phq_edaic_cmdc_mean",
                "mean_observed_macro_mae": safe_float(group["observed_macro_item_mae"].mean()),
                "mean_theta_mae": safe_float(group["theta_mae"].mean()),
                "mean_delta_theta_mae_vs_B0": safe_float(group["delta_theta_mae_vs_B0"].mean()),
                "mean_delta_theta_mae_vs_B3": safe_float(group["delta_theta_mae_vs_B3"].mean()),
                "mean_delta_observed_macro_mae_vs_B3": safe_float(group["delta_observed_macro_mae_vs_B3"].mean()),
                "dataset_identity_ba_feature": feature_identity,
                "feature_identity_source": feature_identity_source,
                "dataset_identity_ba_prediction_unconditional": identity_lookup(
                    identity,
                    "ID0_unconditional_predicted_theta_identity",
                    model,
                ),
                "dataset_identity_ba_conditional_latent": identity_lookup(
                    identity,
                    "ID1_conditional_predicted_theta_identity",
                    model,
                ),
                "dataset_identity_ba_post_mapping": identity_lookup(
                    identity,
                    "ID2_conditional_post_mapping_identity",
                    model,
                ),
                "notes": (
                    "MV12 PHQ-only pooled E-DAIC/CMDC mean; conditional identity is computed on predicted theta after "
                    "conditioning on true theta and observed total."
                ),
            }
        )
    return pd.DataFrame(rows)


def legacy_pareto_rows(mv09_pareto: pd.DataFrame) -> pd.DataFrame:
    rows = mv09_pareto.copy()
    rows = rows.rename(
        columns={
            "mean_macro_mae": "mean_observed_macro_mae",
            "dataset_identity_ba_prediction": "dataset_identity_ba_prediction_unconditional",
        }
    )
    rows["evaluation_scope"] = np.where(
        rows["source_run"].isin(["P5_MV07", "P5_MV07b", "P5_MV07c"]),
        "pooled_phq_edaic_cmdc_mean",
        "cross_scale_pooled_active_slice_mean",
    )
    rows["mean_theta_mae"] = np.nan
    rows["mean_delta_theta_mae_vs_B0"] = np.nan
    rows["mean_delta_theta_mae_vs_B3"] = np.nan
    rows["mean_delta_observed_macro_mae_vs_B3"] = np.nan
    rows["dataset_identity_ba_conditional_latent"] = np.nan
    rows["dataset_identity_ba_post_mapping"] = np.nan
    rows["feature_identity_source"] = "reported_by_source_run"
    keep = [
        "source_run",
        "family",
        "model",
        "evaluation_scope",
        "mean_observed_macro_mae",
        "mean_theta_mae",
        "mean_delta_theta_mae_vs_B0",
        "mean_delta_theta_mae_vs_B3",
        "mean_delta_observed_macro_mae_vs_B3",
        "dataset_identity_ba_feature",
        "feature_identity_source",
        "dataset_identity_ba_prediction_unconditional",
        "dataset_identity_ba_conditional_latent",
        "dataset_identity_ba_post_mapping",
        "notes",
    ]
    return rows[keep]


def mark_pareto_frontier(tradeoff: pd.DataFrame) -> pd.DataFrame:
    out = tradeoff.copy()
    out["is_observed_macro_pareto_frontier"] = False
    for scope, group in out.dropna(subset=["mean_observed_macro_mae"]).groupby("evaluation_scope", sort=True):
        identity = group["dataset_identity_ba_conditional_latent"].where(
            group["dataset_identity_ba_conditional_latent"].notna(),
            group["dataset_identity_ba_prediction_unconditional"],
        )
        values = group.assign(_identity=identity)
        values = values.dropna(subset=["_identity", "mean_observed_macro_mae"])
        frontier_idx: list[int] = []
        for idx, row in values.iterrows():
            dominated = values[
                (values["mean_observed_macro_mae"] <= row["mean_observed_macro_mae"])
                & (values["_identity"] <= row["_identity"])
                & (
                    (values["mean_observed_macro_mae"] < row["mean_observed_macro_mae"])
                    | (values["_identity"] < row["_identity"])
                )
            ]
            if dominated.empty:
                frontier_idx.append(idx)
        out.loc[frontier_idx, "is_observed_macro_pareto_frontier"] = True
    return out


def build_gate_decomposition(summary: dict[str, Any]) -> pd.DataFrame:
    verdict = summary["verdict"]
    rows = [
        {
            "gate_id": "G0_measurement_optimization",
            "gate_passed": verdict["measurement_optimizer_all_success"],
            "primary_value": verdict["measurement_optimizer_all_success"],
            "threshold_or_reference": "all fold measurement optimizers successful",
            "interpretation": "Label-only target generation is numerically usable.",
        },
        {
            "gate_id": "G1_same_dataset_theta_utility",
            "gate_passed": verdict["same_dataset_theta_gate_passed"],
            "primary_value": f"edaic {fmt(verdict['m12a_edaic_delta_theta_mae_vs_B0'])}; cmdc {fmt(verdict['m12a_cmdc_delta_theta_mae_vs_B0'])}",
            "threshold_or_reference": "M12a theta MAE below train-mean theta floor on both same-dataset slices",
            "interpretation": "The latent target is predictable within each PHQ dataset.",
        },
        {
            "gate_id": "G2_same_dataset_observed_scale_safety",
            "gate_passed": verdict["same_dataset_observed_gate_passed"],
            "primary_value": f"edaic {fmt(verdict['m12a_edaic_delta_observed_macro_mae_vs_B3'])}; cmdc {fmt(verdict['m12a_cmdc_delta_observed_macro_mae_vs_B3'])}",
            "threshold_or_reference": "M12a observed macro MAE no worse than direct itemwise Ridge on both slices",
            "interpretation": "This is the primary failure: theta gains do not safely map back to observed PHQ item scales.",
        },
        {
            "gate_id": "G3_external_theta_transfer",
            "gate_passed": verdict["external_transfer_theta_gate_passed"],
            "primary_value": verdict["external_transfer_theta_gate_passed"],
            "threshold_or_reference": "at least one held-out cross-dataset direction beats train-mean theta floor",
            "interpretation": "The latent target has not shown external theta transfer.",
        },
        {
            "gate_id": "G4_external_observed_scale_safety",
            "gate_passed": verdict["external_transfer_observed_gate_passed"],
            "primary_value": verdict["external_transfer_observed_gate_passed"],
            "threshold_or_reference": "at least one held-out cross-dataset direction is not worse than direct itemwise Ridge on observed macro MAE",
            "interpretation": "Observed transfer is not the limiting gate, but this does not rescue failed theta transfer.",
        },
        {
            "gate_id": "G5_conditional_shared_latent_identity",
            "gate_passed": verdict["conditional_identity_preferred_threshold_passed"],
            "primary_value": fmt(verdict["conditional_identity_ba_m12a"]),
            "threshold_or_reference": f"below preferred BA {fmt(verdict['preferred_conditional_identity_ba_threshold'])}; MV09 reference {fmt(verdict['mv09_conditional_identity_ba_reference'])}",
            "interpretation": "The shared-latent prediction layer is less dataset-identifiable after legitimate conditioning.",
        },
        {
            "gate_id": "G6_leakage_boundary",
            "gate_passed": verdict["leakage_gate_passed"],
            "primary_value": verdict["leakage_gate_passed"],
            "threshold_or_reference": "no eval target use, no test labels, no tracked row predictions or learned parameters",
            "interpretation": "The aggregate result is release-compatible.",
        },
        {
            "gate_id": "G7_artifact_hygiene",
            "gate_passed": summary["artifact_hygiene_passed"],
            "primary_value": summary["artifact_hygiene_passed"],
            "threshold_or_reference": "tracked outputs pass hygiene scan",
            "interpretation": "No public artifact hygiene issue was detected.",
        },
    ]
    return pd.DataFrame(rows)


def build_dataset_slice_diagnostics(comparison: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    selected = comparison[
        comparison["model"].isin([MV12_B3, MV12_M12A, MV12_M12B])
        & comparison["dataset_slice"].isin(["edaic", "cmdc"])
    ].copy()
    for _, row in selected.iterrows():
        theta_delta_b0 = safe_float(row["delta_theta_mae_vs_B0"])
        observed_delta_b3 = safe_float(row["delta_observed_macro_mae_vs_B3"])
        rows.append(
            {
                "protocol": row["protocol"],
                "dataset_slice": row["dataset_slice"],
                "model": row["model"],
                "theta_mae": row["theta_mae"],
                "observed_macro_item_mae": row["observed_macro_item_mae"],
                "observed_total_mae": row["observed_total_mae"],
                "delta_theta_mae_vs_B0": theta_delta_b0,
                "delta_theta_mae_vs_B3": safe_float(row["delta_theta_mae_vs_B3"]),
                "delta_observed_macro_mae_vs_B3": observed_delta_b3,
                "theta_beats_train_mean": bool(theta_delta_b0 is not None and theta_delta_b0 < 0),
                "observed_non_degraded_vs_direct_itemwise": bool(
                    observed_delta_b3 is not None and observed_delta_b3 <= 0
                ),
            }
        )
    return pd.DataFrame(rows)


def build_failure_modes(
    summary: dict[str, Any],
    transfer: pd.DataFrame,
    identity: pd.DataFrame,
    reliability: pd.DataFrame,
) -> pd.DataFrame:
    verdict = summary["verdict"]
    primary_reliability = reliability[reliability["item_group"] == "primary_measurement_items"]
    rows = [
        {
            "failure_mode_id": "latent_target_predictable_same_dataset",
            "status": "use_as_positive_subfinding",
            "evidence": f"M12a theta MAE deltas vs train mean are E-DAIC {fmt(verdict['m12a_edaic_delta_theta_mae_vs_B0'])} and CMDC {fmt(verdict['m12a_cmdc_delta_theta_mae_vs_B0'])}.",
            "interpretation": "The PHQ latent target is learnable from audited BGE features within each dataset.",
        },
        {
            "failure_mode_id": "theta_to_observed_mapping_loss",
            "status": "primary_blocker",
            "evidence": f"M12a observed macro deltas vs direct itemwise Ridge are E-DAIC {fmt(verdict['m12a_edaic_delta_observed_macro_mae_vs_B3'])} and CMDC {fmt(verdict['m12a_cmdc_delta_observed_macro_mae_vs_B3'])}.",
            "interpretation": "A cleaner latent output does not yet preserve dataset-specific item-scale information well enough.",
        },
        {
            "failure_mode_id": "external_theta_transfer_gap",
            "status": "primary_blocker",
            "evidence": "; ".join(
                f"{row.protocol} delta_theta_vs_B0 {fmt(row.m12a_delta_theta_mae_vs_B0)}"
                for row in transfer.itertuples(index=False)
            ),
            "interpretation": "The current source-only measurement target does not transfer as a theta target across E-DAIC and CMDC.",
        },
        {
            "failure_mode_id": "conditional_latent_identity_gain",
            "status": "use_as_positive_subfinding",
            "evidence": f"M12a conditional predicted-theta identity BA is {fmt(verdict['conditional_identity_ba_m12a'])}; MV09 conditional feature-identity reference is {fmt(verdict['mv09_conditional_identity_ba_reference'])}.",
            "interpretation": "The shared latent prediction layer is less dataset-identifiable than the upstream feature space.",
        },
        {
            "failure_mode_id": "post_mapping_identity_remains_scale_specific",
            "status": "interpret_with_caution",
            "evidence": f"M12a post-mapping conditional item identity BA is {fmt(identity_lookup(identity, 'ID2_conditional_post_mapping_identity', MV12_M12A))}.",
            "interpretation": "High identity after mapping to observed items should be described as scale-specific output structure, not as the same hard shared-latent failure.",
        },
        {
            "failure_mode_id": "measurement_target_reliability_not_main_blocker",
            "status": "supporting_context",
            "evidence": f"Primary-item Cronbach alpha averages train {fmt(primary_reliability['train_cronbach_alpha'].mean())} and eval {fmt(primary_reliability['eval_cronbach_alpha'].mean())}.",
            "interpretation": "Aggregate reliability is high enough that the main blocker is prediction/mapping/transfer, not an obviously unusable PHQ target.",
        },
    ]
    return pd.DataFrame(rows)


def build_recommendations(summary: dict[str, Any]) -> pd.DataFrame:
    verdict = summary["verdict"]
    freeze = not bool(verdict["pass_rule_met"])
    rows = [
        {
            "rank": 1,
            "recommendation_id": "FREEZE_CURRENT_MV12_LATENT_TARGET_LINE",
            "decision": "recommended" if freeze else "not_needed",
            "action": "Freeze MV12 as bounded measurement-shift evidence before manuscript drafting.",
            "why": "MV12 passes latent identity and same-dataset theta utility, but fails observed-scale safety and external theta transfer.",
            "required_before_reopening": "A new predeclared mechanism must preserve conditional latent identity while improving theta-to-observed mapping and external theta transfer.",
        },
        {
            "rank": 2,
            "recommendation_id": "WRITE_ACCURACY_INVARIANCE_RESULT",
            "decision": "recommended",
            "action": "Use the extended trade-off table as the paper-facing accuracy-invariance/measurement-shift result.",
            "why": "Across MV07-MV12, lower identity can be achieved, but predictive/measurement safety constraints decide whether it is claimable.",
            "required_before_reopening": "No row-level output release is needed; cite aggregate summaries only.",
        },
        {
            "rank": 3,
            "recommendation_id": "NO_FULL_METHOD_START",
            "decision": "required",
            "action": "Keep full M0/M1/M2/M3 blocked.",
            "why": "The current result does not satisfy the predeclared utility, observed-scale, and transfer gate combination.",
            "required_before_reopening": "Full gate must change after a future audited run, not from reinterpretation of this run alone.",
        },
        {
            "rank": 4,
            "recommendation_id": "OPTIONAL_MV06_OR_WRITING_NEXT",
            "decision": "recommended",
            "action": "Prefer manuscript drafting or E-DAIC MV06 agreement strengthening over another shallow BGE head iteration.",
            "why": "MV12 closes the most obvious psychometric-target follow-up and supports a diagnostic paper boundary.",
            "required_before_reopening": "Only reopen model iteration with genuinely new data, features, labels, or measurement machinery.",
        },
    ]
    return pd.DataFrame(rows)


def build_source_summary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source_id": "P5_MV09",
                "artifact": rel(MV09_PARETO),
                "read_scope": "aggregate accuracy-identity Pareto rows from MV07/MV07b/MV07c/MV08/MV08b",
                "row_level_data_read": False,
            },
            {
                "source_id": "P5_MV12",
                "artifact": rel(MV12_COMPARISON),
                "read_scope": "aggregate model comparison metrics",
                "row_level_data_read": False,
            },
            {
                "source_id": "P5_MV12_identity",
                "artifact": rel(MV12_IDENTITY),
                "read_scope": "aggregate identity-probe summaries",
                "row_level_data_read": False,
            },
            {
                "source_id": "P5_MV12_transfer",
                "artifact": rel(MV12_TRANSFER),
                "read_scope": "aggregate transfer summaries",
                "row_level_data_read": False,
            },
            {
                "source_id": "P5_MV12_target_generation",
                "artifact": rel(MV12_TARGET_GENERATION),
                "read_scope": "aggregate measurement optimizer and target summaries",
                "row_level_data_read": False,
            },
            {
                "source_id": "P5_MV12_target_reliability",
                "artifact": rel(MV12_TARGET_RELIABILITY),
                "read_scope": "aggregate target reliability summaries",
                "row_level_data_read": False,
            },
        ]
    )


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"source_locator",
        r"local_annotation_workbook",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
        r"raw clinical",
        r"posterior_score",
        r"factor_score",
        r"parameter_value",
        r"p5_mv12_local_predictions",
        r"local_row_predictions",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV12_latent_target_tradeoff_analysis_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    gate: pd.DataFrame,
    failures: pd.DataFrame,
    recommendations: pd.DataFrame,
    tradeoff: pd.DataFrame,
) -> None:
    verdict = run_summary["decision"]
    frontier = tradeoff[tradeoff["is_observed_macro_pareto_frontier"]]
    lines = [
        "# P5_MV12 Latent-Target Trade-Off Analysis",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This artifact reads aggregate MV07-MV12 summaries only. It decomposes the MV12 gate result and extends the accuracy-identity trade-off table without reading row-level predictions or learned parameters.",
        "",
        "## Decision",
        "",
        f"- Analysis status: `{verdict['analysis_status']}`.",
        f"- Freeze current latent-target line: `{verdict['freeze_current_latent_target_line']}`.",
        f"- Full method allowed: `{verdict['full_method_allowed']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Gate Decomposition",
        "",
        "| gate | passed | value | interpretation |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in gate.iterrows():
        lines.append(
            f"| {row['gate_id']} | `{row['gate_passed']}` | {row['primary_value']} | {row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Failure Modes",
            "",
            "| mode | status | evidence | interpretation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in failures.iterrows():
        lines.append(
            f"| {row['failure_mode_id']} | `{row['status']}` | {row['evidence']} | {row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Trade-Off Frontier",
            "",
            "| source | model | scope | observed macro MAE | prediction identity BA | conditional latent BA | frontier |",
            "| --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    display = tradeoff[
        tradeoff["source_run"].isin(["P5_MV07b", "P5_MV07c", "P5_MV08", "P5_MV08b", "P5_MV12"])
    ].copy()
    for _, row in display.sort_values(["evaluation_scope", "source_run", "mean_observed_macro_mae"]).iterrows():
        lines.append(
            f"| {row['source_run']} | {row['model']} | {row['evaluation_scope']} | {fmt(row['mean_observed_macro_mae'])} | {fmt(row['dataset_identity_ba_prediction_unconditional'])} | {fmt(row['dataset_identity_ba_conditional_latent'])} | `{row['is_observed_macro_pareto_frontier']}` |"
        )
    lines.extend(
        [
            "",
            "## Recommendations",
            "",
            "| rank | decision | action |",
            "| ---: | --- | --- |",
        ]
    )
    for _, row in recommendations.sort_values("rank").iterrows():
        lines.append(f"| {int(row['rank'])} | `{row['decision']}` | {row['action']} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- The MV12 latent layer is a useful diagnostic signal, but the full method remains blocked.",
            "- Do not treat post-mapping item identity as the same hard gate as shared-latent identity because observed outputs are intentionally scale-specific.",
            "- The current model line should be frozen unless a future predeclared change directly targets observed-scale mapping and external theta transfer.",
            f"- Pareto frontier rows reported in this aggregate table: `{len(frontier)}`.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mv09_pareto = pd.read_csv(MV09_PARETO)
    mv12_summary = read_json(MV12_SUMMARY)
    comparison = pd.read_csv(MV12_COMPARISON)
    identity = pd.read_csv(MV12_IDENTITY)
    transfer = pd.read_csv(MV12_TRANSFER)
    target_generation = pd.read_csv(MV12_TARGET_GENERATION)
    reliability = pd.read_csv(MV12_TARGET_RELIABILITY)

    gate = build_gate_decomposition(mv12_summary)
    dataset_slice = build_dataset_slice_diagnostics(comparison)
    failures = build_failure_modes(mv12_summary, transfer, identity, reliability)
    recommendations = build_recommendations(mv12_summary)
    tradeoff = pd.concat(
        [legacy_pareto_rows(mv09_pareto), mv12_pooled_model_rows(comparison, identity)],
        ignore_index=True,
    )
    tradeoff = mark_pareto_frontier(tradeoff)
    sources = build_source_summary()

    gate.to_csv(out_dir / "gate_decomposition.csv", index=False)
    dataset_slice.to_csv(out_dir / "mv12_dataset_slice_diagnostics.csv", index=False)
    failures.to_csv(out_dir / "failure_mode_summary.csv", index=False)
    recommendations.to_csv(out_dir / "mechanism_recommendation_queue.csv", index=False)
    tradeoff.to_csv(out_dir / "accuracy_identity_tradeoff_summary.csv", index=False)
    sources.to_csv(out_dir / "source_artifact_summary.csv", index=False)

    verdict = mv12_summary["verdict"]
    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "aggregate_only_mv12_error_and_pareto_analysis",
        "input_contract": {
            "aggregate_phase5_summaries_read": True,
            "row_level_predictions_read": False,
            "raw_data_scanned": False,
            "fitted_parameters_read": False,
            "theta_score_tables_read": False,
            "private_review_material_read": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "gate_rows": int(len(gate)),
            "failure_mode_rows": int(len(failures)),
            "tradeoff_rows": int(len(tradeoff)),
            "mv12_dataset_slice_rows": int(len(dataset_slice)),
            "recommendation_rows": int(len(recommendations)),
            "source_rows": int(len(sources)),
        },
        "decision": {
            "analysis_status": "complete_freeze_current_mv12_latent_target_line",
            "freeze_current_latent_target_line": True,
            "full_method_allowed": False,
            "mv12_pass_rule_status": verdict["pass_rule_status"],
            "same_dataset_theta_gate_passed": verdict["same_dataset_theta_gate_passed"],
            "same_dataset_observed_gate_passed": verdict["same_dataset_observed_gate_passed"],
            "external_transfer_theta_gate_passed": verdict["external_transfer_theta_gate_passed"],
            "conditional_identity_ba_m12a": verdict["conditional_identity_ba_m12a"],
            "short_read": (
                "Aggregate-only MV12 analysis recommends freezing the current latent-target line: "
                "latent theta utility and conditional identity improve, but observed-scale safety and "
                "external theta transfer remain the decisive blockers."
            ),
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, gate, failures, recommendations, tradeoff)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, gate, failures, recommendations, tradeoff)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    run_summary = build_outputs(args.out_dir)
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "analysis_status": run_summary["decision"]["analysis_status"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
