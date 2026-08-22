#!/usr/bin/env python3
"""Run P5_MV13 external psychometric replication with R mirt.

MV13 is a label-only external replication of the MV10/MV11 PHQ measurement
invariance conclusion. Python prepares a local-only item response matrix from
the manifest-governed MV10 loader, calls the tracked R/mirt runner, and exports
only aggregate fit, DIF, item-fit, runtime, alignment, and hygiene summaries.

The local R input contains participant-grain item responses and is ignored by
Git. Fitted item parameters, factor scores, theta scores, R model objects, and
full parameter CI tables are not tracked.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from phase5_run_mv10_psychometric_invariance_baseline import (
    CORE_CONSTRUCTS,
    DEFAULT_MANIFEST_DIR,
    ITEM_LABELS,
    ROOT,
    fmt,
    load_inputs,
)


PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv13_external_psychometric_replication"
DEFAULT_MV10_PARTIAL = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline" / "partial_invariance_summary.csv"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
R_RUNNER = ROOT / "scripts" / "phase5_run_mv13_external_psychometric_replication.R"

RUN_ID = "P5_MV13_external_psychometric_replication"
LRT_ALPHA = 0.01
BIC_IMPROVEMENT_TOL = 2.0
MIN_CONFIRMED_ANCHORS = 3

TRACKED_FILES = {
    "anchor_confirmation_summary.csv",
    "artifact_hygiene_audit.json",
    "external_model_syntax_summary.csv",
    "external_replication_alignment_summary.csv",
    "fit_model_summary.csv",
    "gate_recommendations.csv",
    "input_boundary_contract.csv",
    "invariance_comparison_summary.csv",
    "item_dif_lrt_summary.csv",
    "item_fit_summary.csv",
    "method_context_external_psychometric.csv",
    "parameter_ci_availability_summary.csv",
    "psychometric_input_audit.csv",
    "r_execution_summary.csv",
    "report.md",
    "run_summary.json",
    "runtime_versions.csv",
}

LOCAL_ONLY_FILES = {
    "ignored_local_item_response_matrix": "participant-grain PHQ item response matrix without subject IDs",
}

METHOD_CONTEXT = [
    {
        "source_id": "mirt_jss_2012",
        "source_type": "primary_package_paper",
        "url": "https://www.jstatsoft.org/article/view/v048i06",
        "use_in_mv13": "Primary external software family for multi-group graded-response IRT replication.",
        "key_takeaway": "mirt estimates unidimensional and multidimensional IRT models, including polytomous response data, with maximum-likelihood methods.",
    },
    {
        "source_id": "mirt_multipleGroup_docs",
        "source_type": "official_package_documentation",
        "url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
        "use_in_mv13": "Use multipleGroup to fit configural, metric, scalar, partial, and item-level DIF models.",
        "key_takeaway": "multipleGroup supports polytomous multi-group IRT, equality constraints, invariance keywords, and DIF workflows.",
    },
    {
        "source_id": "lavaan_categorical_docs",
        "source_type": "official_package_documentation",
        "url": "https://lavaan.ugent.be/tutorial/cat.html",
        "use_in_mv13": "Declare lavaan as an ordinal CFA sensitivity fallback for later replication if mirt and custom models diverge.",
        "key_takeaway": "lavaan supports ordered endogenous variables with categorical estimators such as WLSMV/DWLS-style estimation.",
    },
    {
        "source_id": "lavaan_multiple_groups_docs",
        "source_type": "official_package_documentation",
        "url": "https://lavaan.ugent.be/tutorial/groups.html",
        "use_in_mv13": "Declare lavaan multiple-group CFA as a sensitivity path, not the primary MV13 engine.",
        "key_takeaway": "lavaan supports multiple-group fitting and cross-group equality constraints.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.as_posix()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def first_value(frame: pd.DataFrame, key: str, value: str, field: str) -> Any:
    rows = frame[frame[key].astype(str) == value]
    if rows.empty:
        return None
    return rows.iloc[0].get(field)


def comparison_decision(
    p_value: Any,
    delta_bic_restricted_minus_full: Any,
    df: Any,
) -> str:
    p = safe_float(p_value)
    delta_bic = safe_float(delta_bic_restricted_minus_full)
    df_value = safe_float(df)
    if df_value is None or df_value <= 0:
        return "not_nested_or_invalid"
    if p is not None and delta_bic is not None and p < LRT_ALPHA and delta_bic > BIC_IMPROVEMENT_TOL:
        return "restricted_model_rejected_lrt_and_bic"
    if p is not None and p < LRT_ALPHA:
        return "restricted_model_rejected_lrt_only"
    if delta_bic is not None and delta_bic > BIC_IMPROVEMENT_TOL:
        return "full_model_preferred_bic_only"
    return "no_strong_evidence_against_restriction"


def write_local_r_input(out_dir: Path, manifest_dir: Path) -> pd.DataFrame:
    table, input_audit = load_inputs(manifest_dir)
    response = table[["dataset", *CORE_CONSTRUCTS]].copy()
    for item in CORE_CONSTRUCTS:
        response[item] = response[item].astype(int)
    response.to_csv(out_dir / "local_mirt_phq_response_matrix.csv", index=False)
    input_audit.to_csv(out_dir / "psychometric_input_audit.csv", index=False)
    return input_audit


def run_r_mirt(out_dir: Path, local_input: Path, mv10_partial: Path) -> dict[str, Any]:
    rscript = shutil.which("Rscript")
    if not rscript:
        raise RuntimeError("Rscript is not available on PATH")
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    result = subprocess.run(
        [
            rscript,
            str(R_RUNNER),
            str(local_input),
            str(mv10_partial),
            str(out_dir),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=1800,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "R mirt runner failed with return code "
            f"{result.returncode}: {result.stderr[-2000:]}"
        )
    return {
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-1000:],
        "stderr_tail": result.stderr[-1000:],
    }


def build_input_boundary() -> pd.DataFrame:
    rows = [
        {
            "artifact_class": "ignored_local_item_response_matrix",
            "git_policy": "ignored_local_only",
            "reason": "Participant-grain PHQ item response rows are analysis input, not a public aggregate artifact.",
            "allowed_tracked_derivative": "psychometric_input_audit.csv with dataset-level counts only",
        },
        {
            "artifact_class": "fitted_mirt_model_objects",
            "git_policy": "do_not_track",
            "reason": "Fitted model objects can contain full item parameters and reproducibility internals.",
            "allowed_tracked_derivative": "fit_model_summary.csv and r_execution_summary.csv",
        },
        {
            "artifact_class": "item_parameter_or_ci_tables",
            "git_policy": "local_only_if_generated",
            "reason": "Full item parameter values and confidence intervals are fitted psychometric parameters.",
            "allowed_tracked_derivative": "parameter_ci_availability_summary.csv with counts only",
        },
        {
            "artifact_class": "factor_or_theta_scores",
            "git_policy": "do_not_track",
            "reason": "Subject-level latent scores are participant-grain outputs.",
            "allowed_tracked_derivative": "none; later MV15/MV16 may export aggregate identity/calibration summaries only",
        },
    ]
    return pd.DataFrame(rows)


def build_alignment(out_dir: Path) -> pd.DataFrame:
    mv13_comp = read_csv(out_dir / "invariance_comparison_summary.csv")
    mv13_anchor = read_csv(out_dir / "anchor_confirmation_summary.csv")
    mv11_comp = read_csv(MV11_DIR / "invariance_comparison_summary.csv")
    mv11_anchor = read_csv(MV11_DIR / "anchor_confirmation_summary.csv")

    mv13_threshold = set(
        mv13_anchor.loc[bool_series(mv13_anchor["threshold_dif_flag"]), "construct_id"].astype(str)
    )
    mv11_threshold = set(
        mv11_anchor.loc[bool_series(mv11_anchor["threshold_dif_flag"]), "construct_id"].astype(str)
    )
    mv13_loading = set(
        mv13_anchor.loc[bool_series(mv13_anchor["loading_dif_flag"]), "construct_id"].astype(str)
    )
    mv11_loading = set(
        mv11_anchor.loc[bool_series(mv11_anchor["loading_dif_flag"]), "construct_id"].astype(str)
    )
    mv13_anchors = set(
        mv13_anchor.loc[bool_series(mv13_anchor["mv10_anchor_confirmed"]), "construct_id"].astype(str)
    )
    mv11_anchors = set(
        mv11_anchor.loc[bool_series(mv11_anchor["mv10_anchor_confirmed"]), "construct_id"].astype(str)
    )

    rows = [
        {
            "alignment_id": "anchor_set_overlap",
            "mv11_value": ";".join(sorted(mv11_anchors)) or "none",
            "mv13_value": ";".join(sorted(mv13_anchors)) or "none",
            "aligned": mv11_anchors == mv13_anchors,
            "interpretation": "Checks whether external mirt preserves the MV10/MV11 candidate anchor set.",
        },
        {
            "alignment_id": "loading_dif_overlap",
            "mv11_value": ";".join(sorted(mv11_loading)) or "none",
            "mv13_value": ";".join(sorted(mv13_loading)) or "none",
            "aligned": mv11_loading == mv13_loading,
            "interpretation": "Checks whether both implementations avoid strong loading DIF flags.",
        },
        {
            "alignment_id": "threshold_dif_overlap",
            "mv11_value": ";".join(sorted(mv11_threshold)) or "none",
            "mv13_value": ";".join(sorted(mv13_threshold)) or "none",
            "aligned": mv11_threshold == mv13_threshold,
            "interpretation": "Checks whether threshold DIF concentrates on the same symptoms.",
        },
    ]
    for comparison_id in [
        "metric_vs_configural",
        "scalar_vs_metric",
        "partial_mv10_vs_configural",
    ]:
        rows.append(
            {
                "alignment_id": comparison_id,
                "mv11_value": str(first_value(mv11_comp, "comparison_id", comparison_id, "decision")),
                "mv13_value": str(first_value(mv13_comp, "comparison_id", comparison_id, "decision")),
                "aligned": str(first_value(mv11_comp, "comparison_id", comparison_id, "decision"))
                == str(first_value(mv13_comp, "comparison_id", comparison_id, "decision")),
                "interpretation": "Compares the qualitative nested-model decision label.",
            }
        )
    return pd.DataFrame(rows)


def determine_verdict(out_dir: Path, input_audit: pd.DataFrame, r_meta: dict[str, Any]) -> dict[str, Any]:
    fit = read_csv(out_dir / "fit_model_summary.csv")
    comp = read_csv(out_dir / "invariance_comparison_summary.csv")
    anchors = read_csv(out_dir / "anchor_confirmation_summary.csv")
    ci = read_csv(out_dir / "parameter_ci_availability_summary.csv")
    execution = read_csv(out_dir / "r_execution_summary.csv")
    alignment = read_csv(out_dir / "external_replication_alignment_summary.csv")

    core_ids = {"configural", "metric", "scalar", "partial_mv10"}
    core = fit[fit["model_id"].isin(core_ids)].copy()
    core_fit_success = bool(bool_series(core["fit_success"]).all())
    core_converged = bool(bool_series(core["converged"]).all())
    confirmed_anchors = int(bool_series(anchors["mv10_anchor_confirmed"]).sum())
    loading_flags = int(bool_series(anchors["loading_dif_flag"]).sum())
    threshold_flags = int(bool_series(anchors["threshold_dif_flag"]).sum())
    best_aic_model = str(core.sort_values("aic", na_position="last").iloc[0]["model_id"]) if not core.empty else "NA"
    best_bic_model = str(core.sort_values("bic", na_position="last").iloc[0]["model_id"]) if not core.empty else "NA"
    aic_bic_split = best_aic_model != best_bic_model
    aligned_count = int(bool_series(alignment["aligned"]).sum())

    metric_decision = str(first_value(comp, "comparison_id", "metric_vs_configural", "decision"))
    scalar_decision = str(first_value(comp, "comparison_id", "scalar_vs_metric", "decision"))
    partial_configural_decision = str(first_value(comp, "comparison_id", "partial_mv10_vs_configural", "decision"))

    if not core_fit_success:
        status = "blocked_external_mirt_core_fit_failed"
    elif not core_converged:
        status = "complete_external_mirt_with_convergence_warnings"
    elif confirmed_anchors >= MIN_CONFIRMED_ANCHORS and loading_flags <= 1 and threshold_flags >= 1:
        status = "complete_external_mirt_partial_invariance_supported"
    elif confirmed_anchors >= MIN_CONFIRMED_ANCHORS and loading_flags <= 1:
        status = "complete_external_mirt_anchor_structure_supported_without_threshold_flags"
    else:
        status = "complete_external_mirt_revises_mv11_anchor_map"

    subjects = {
        str(row["dataset"]): int(row["complete_item_subjects"])
        for _, row in input_audit.iterrows()
    }
    ci_row = ci.iloc[0].to_dict() if not ci.empty else {}
    execution_row = execution.iloc[0].to_dict() if not execution.empty else {}
    anchor_linked_corrected = str(
        execution_row.get("anchor_linked_focal_hyperparameters_corrected", "")
    ).strip().lower() in {"true", "1", "yes", "y"}

    return {
        "status": status,
        "external_engine": "R mirt::multipleGroup",
        "parameterization_contract": "anchor_linked_focal_mean_variance_free"
        if anchor_linked_corrected
        else "fixed_group_hyperparameters",
        "anchor_linked_focal_hyperparameters_corrected": anchor_linked_corrected,
        "external_runtime_ready": True,
        "r_returncode": r_meta["returncode"],
        "subjects": subjects,
        "shared_items": CORE_CONSTRUCTS,
        "core_fit_success": core_fit_success,
        "core_converged": core_converged,
        "fit_count": int(len(fit)),
        "best_aic_model": best_aic_model,
        "best_bic_model": best_bic_model,
        "core_model_aic_bic_split": aic_bic_split,
        "confirmed_mv10_anchor_items": confirmed_anchors,
        "min_confirmed_anchor_items_required": MIN_CONFIRMED_ANCHORS,
        "loading_dif_flagged_items": loading_flags,
        "threshold_dif_flagged_items": threshold_flags,
        "metric_vs_configural_decision": metric_decision,
        "scalar_vs_metric_decision": scalar_decision,
        "partial_mv10_vs_configural_decision": partial_configural_decision,
        "parameter_ci_status": str(execution_row.get("parameter_ci_status", "unknown")),
        "parameter_ci_finite_se_count": int(ci_row.get("finite_se_count", 0))
        if pd.notna(ci_row.get("finite_se_count", float("nan")))
        else 0,
        "itemfit_status": str(execution_row.get("itemfit_status", "unknown")),
        "mv11_mv13_alignment_rows": int(len(alignment)),
        "mv11_mv13_aligned_rows": aligned_count,
        "short_read": (
            "External R mirt replication is complete with anchor-linked focal mean/variance "
            "freed for threshold-constrained models; full item parameters and factor scores remain local-only."
            if anchor_linked_corrected
            else "External R mirt replication is complete under fixed group hyperparameters; full item parameters and factor scores remain local-only."
        ),
    }


def gate_recommendations(verdict: dict[str, Any]) -> pd.DataFrame:
    if verdict["status"].startswith("complete_external_mirt_partial_invariance_supported"):
        mv14_status = "ready_to_predeclare_measurement_uncertainty_bootstrap"
        evidence = (
            f"Confirmed anchors {verdict['confirmed_mv10_anchor_items']}; "
            f"loading DIF flags {verdict['loading_dif_flagged_items']}; "
            f"threshold DIF flags {verdict['threshold_dif_flagged_items']}."
        )
    else:
        mv14_status = "review_external_mirt_before_bootstrap"
        evidence = f"MV13 status {verdict['status']}."

    rows = [
        {
            "recommendation_id": "external_replication_boundary",
            "status": verdict["status"],
            "recommendation": "Use MV13 as the external psychometric replication layer for MV10/MV11, with aggregate-only exports.",
            "evidence": evidence,
        },
        {
            "recommendation_id": "parameter_ci_boundary",
            "status": verdict["parameter_ci_status"],
            "recommendation": "Treat full parameter CI values as local-only; track only CI availability/counts unless a deidentified parameter appendix is explicitly approved.",
            "evidence": f"Finite SE count in aggregate audit: {verdict['parameter_ci_finite_se_count']}.",
        },
        {
            "recommendation_id": "mv14_measurement_uncertainty",
            "status": mv14_status,
            "recommendation": "Next psychometric step should bootstrap DIF and anchor stability under the same local-only item-response boundary.",
            "evidence": "CMDC has 77 PHQ item-labeled subjects, so item-level DIF wording needs uncertainty estimates.",
        },
        {
            "recommendation_id": "full_method_gate",
            "status": "keep_blocked",
            "recommendation": "Do not start full M0/M1/M2/M3 from MV13 alone; it is label-only measurement evidence.",
            "evidence": "MV13 checks the Y->theta measurement layer, not X->theta prediction or cross-dataset calibration.",
        },
    ]
    return pd.DataFrame(rows)


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    verdict = run_summary["verdict"]
    fit = read_csv(out_dir / "fit_model_summary.csv")
    comp = read_csv(out_dir / "invariance_comparison_summary.csv")
    anchors = read_csv(out_dir / "anchor_confirmation_summary.csv")
    alignment = read_csv(out_dir / "external_replication_alignment_summary.csv")
    recommendations = read_csv(out_dir / "gate_recommendations.csv")
    core = fit[fit["model_id"].isin(["configural", "metric", "scalar", "partial_mv10"])].copy()

    lines = [
        "# P5 MV13 External Psychometric Replication",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV13 uses R `mirt::multipleGroup` to externally replicate the E-DAIC PHQ-8 / CMDC PHQ-9 C01-C08 measurement-invariance conclusion from MV10/MV11. It reads only manifest-governed item labels and writes aggregate outputs.",
        "",
        "## Verdict",
        "",
        f"- Status: `{verdict['status']}`.",
        f"- External engine: `{verdict['external_engine']}`.",
        f"- Parameterization contract: `{verdict['parameterization_contract']}`.",
        f"- Core fits converged: `{verdict['core_converged']}`.",
        f"- Best AIC model: `{verdict['best_aic_model']}`.",
        f"- Best BIC model: `{verdict['best_bic_model']}`.",
        f"- Confirmed MV10 anchors: `{verdict['confirmed_mv10_anchor_items']}/{verdict['min_confirmed_anchor_items_required']}` required.",
        f"- Loading DIF flagged items: `{verdict['loading_dif_flagged_items']}`.",
        f"- Threshold DIF flagged items: `{verdict['threshold_dif_flagged_items']}`.",
        f"- Parameter CI status: `{verdict['parameter_ci_status']}`.",
        f"- Item-fit status: `{verdict['itemfit_status']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## Core Model Fits",
        "",
        "| model | parameters | log-likelihood | AIC | BIC | converged | iterations |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for _, row in core.sort_values("model_id").iterrows():
        lines.append(
            f"| {row['model_id']} | {int(row['parameter_count']) if pd.notna(row['parameter_count']) else ''} | "
            f"{fmt(row['log_likelihood'])} | {fmt(row['aic'])} | {fmt(row['bic'])} | "
            f"`{row['converged']}` | {int(row['iterations']) if pd.notna(row['iterations']) else ''} |"
        )

    lines.extend(
        [
            "",
            "## Invariance Comparisons",
            "",
            "| comparison | decision | LR | df | p | delta BIC restricted-minus-full |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in comp.iterrows():
        df = "" if pd.isna(row["df"]) else int(row["df"])
        lines.append(
            f"| {row['comparison_id']} | `{row['decision']}` | {fmt(row['lr_statistic'])} | "
            f"{df} | {fmt(row['p_value'], 4)} | {fmt(row['delta_bic_restricted_minus_full'])} |"
        )

    lines.extend(
        [
            "",
            "## External Anchor Map",
            "",
            "| item | MV10 role | external role | loading DIF | threshold DIF |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in anchors.iterrows():
        lines.append(
            f"| {row['construct_id']} {row['item_label_short']} | `{row['mv10_role']}` | "
            f"`{row['external_role']}` | `{row['loading_dif_flag']}` | `{row['threshold_dif_flag']}` |"
        )

    lines.extend(
        [
            "",
            "## MV11 Alignment",
            "",
            "| check | MV11 | MV13 | aligned |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in alignment.iterrows():
        lines.append(
            f"| {row['alignment_id']} | {md_escape(row['mv11_value'])} | "
            f"{md_escape(row['mv13_value'])} | `{row['aligned']}` |"
        )

    lines.extend(
        [
            "",
            "## Gate Recommendations",
            "",
            "| recommendation | status | evidence |",
            "| --- | --- | --- |",
        ]
    )
    for _, row in recommendations.iterrows():
        lines.append(f"| {row['recommendation_id']} | `{row['status']}` | {md_escape(row['evidence'])} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV13 is an external label-only psychometric replication, not multimodal prediction evidence.",
            "- The local item response matrix is ignored and does not include subject IDs, but still remains local-only because it is participant-grain label data.",
            "- Full item parameters, CI values, fitted mirt objects, factor scores, theta scores, and row diagnostics are not tracked.",
            "- Full method construction remains blocked; the next planned step is MV14 measurement-uncertainty bootstrap.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"source_locator",
        r"raw prompt",
        r"raw response",
        r"raw clinical",
        r"posterior_score",
        r"factor_score_value",
        r"theta_score_value",
        r"parameter_value",
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
        "audit_id": "P5_MV13_external_psychometric_replication_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def build_outputs(out_dir: Path, manifest_dir: Path, mv10_partial: Path) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_audit = write_local_r_input(out_dir, manifest_dir)
    pd.DataFrame(METHOD_CONTEXT).to_csv(out_dir / "method_context_external_psychometric.csv", index=False)
    build_input_boundary().to_csv(out_dir / "input_boundary_contract.csv", index=False)

    r_meta = run_r_mirt(out_dir, out_dir / "local_mirt_phq_response_matrix.csv", mv10_partial)
    alignment = build_alignment(out_dir)
    alignment.to_csv(out_dir / "external_replication_alignment_summary.csv", index=False)
    verdict = determine_verdict(out_dir, input_audit, r_meta)
    recommendations = gate_recommendations(verdict)
    recommendations.to_csv(out_dir / "gate_recommendations.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "label_only_external_mirt_psychometric_replication",
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": CORE_CONSTRUCTS,
            "label_only": True,
            "manifest_governed_item_loader": True,
            "external_mirt_runtime": True,
            "external_lavaan_runtime": True,
            "multimodal_features_read": False,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "subject_ids_exported": False,
            "full_method_allowed": False,
        },
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_files": LOCAL_ONLY_FILES,
            "fitted_parameters_exported": False,
            "factor_or_theta_scores_exported": False,
            "fitted_model_objects_exported": False,
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--mv10-partial", type=Path, default=DEFAULT_MV10_PARTIAL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    run_summary = build_outputs(args.out_dir, args.manifest_dir, args.mv10_partial)
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "status": run_summary["verdict"]["status"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
                "best_aic_model": run_summary["verdict"]["best_aic_model"],
                "best_bic_model": run_summary["verdict"]["best_bic_model"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
