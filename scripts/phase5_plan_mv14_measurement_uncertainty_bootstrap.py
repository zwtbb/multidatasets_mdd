#!/usr/bin/env python3
"""Predeclare MV14 measurement-uncertainty/bootstrap.

This is a design contract, not a bootstrap run. It converts the MV13 external
R/mirt replication caveat into a bounded uncertainty plan: resample
manifest-governed PHQ item-response rows locally, refit the same psychometric
model ladder, and export only aggregate stability summaries.

The script reads only aggregate MV10/MV11/MV13/full-gate artifacts. Future
bootstrap input matrices, subject-resampling indices, fitted parameters,
factor/theta scores, model objects, and per-resample logs remain local-only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap_design"

MV10_DIR = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
MV13_DIR = PHASE5_DIR / "p5_mv13_external_psychometric_replication"
FULL_GATE_DIR = PHASE5_DIR / "full_method_gate_audit"

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "bootstrap_ladder_contract.csv",
    "implementation_queue.csv",
    "input_boundary_contract.csv",
    "local_only_boundary_contract.csv",
    "method_source_refs.csv",
    "pass_fail_gate_contract.csv",
    "report.md",
    "run_summary.json",
    "runtime_preflight.csv",
    "source_evidence_summary.csv",
    "stability_metric_contract.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "mirt_jss_2012",
        "url": "https://www.jstatsoft.org/article/view/v048i06",
        "source_type": "primary_package_paper",
        "use_in_mv14": "Use mirt as the version-captured external IRT runtime already used in MV13.",
        "key_takeaway": "mirt estimates exploratory and confirmatory IRT models using maximum-likelihood methods.",
    },
    {
        "source_id": "mirt_multipleGroup_docs",
        "url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
        "source_type": "official_package_documentation",
        "use_in_mv14": "Use multipleGroup for the same E-DAIC/CMDC PHQ multi-group graded-response ladder as MV13.",
        "key_takeaway": "multipleGroup supports dichotomous and polytomous multi-group IRT, constraints, anchor items, and DIF workflows.",
    },
    {
        "source_id": "mirt_DIF_docs",
        "url": "https://rdrr.io/cran/mirt/man/DIF.html",
        "source_type": "official_package_documentation",
        "use_in_mv14": "Use the documented anchor-item logic to frame DIF stability under resampling.",
        "key_takeaway": "The DIF workflow should start from a baseline model with anchor items and freely estimated focal-group hyper-parameters.",
    },
    {
        "source_id": "mirt_boot_mirt_docs",
        "url": "https://philchalmers.github.io/mirt/html/boot.mirt.html",
        "source_type": "official_package_documentation",
        "use_in_mv14": "Declare boot.mirt as an optional parameter-SE sensitivity route while keeping parameter values local-only.",
        "key_takeaway": "boot.mirt computes bootstrap SEs from fitted mirt objects and supports user-defined extraction functions.",
    },
    {
        "source_id": "mirt_boot_lr_docs",
        "url": "https://rdrr.io/cran/mirt/man/boot.LR.html",
        "source_type": "official_package_documentation",
        "use_in_mv14": "Declare boot.LR as an optional parametric LRT sensitivity when nested-model LRT p-values are unstable.",
        "key_takeaway": "boot.LR computes a parametric bootstrap p-value for comparing nested fitted mirt models.",
    },
    {
        "source_id": "mirt_cluster_docs",
        "url": "https://rdrr.io/cran/mirt/man/mirtCluster.html",
        "source_type": "official_package_documentation",
        "use_in_mv14": "Use only for bounded runtime acceleration after confirming deterministic seeds and safe local-only logs.",
        "key_takeaway": "mirtCluster can define a parallel object used internally by mirt functions.",
    },
]


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


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def first_row(frame: pd.DataFrame, column: str, value: str) -> dict[str, Any]:
    rows = frame[frame[column].astype(str) == value]
    if rows.empty:
        raise ValueError(f"missing {column}={value}")
    return rows.iloc[0].to_dict()


def runtime_preflight() -> pd.DataFrame:
    rscript_available = shutil.which("Rscript") is not None
    observed = {
        "R": "missing",
        "mirt": "not_checked_no_rscript",
        "multipleGroup": "not_checked_no_rscript",
        "DIF": "not_checked_no_rscript",
        "boot.mirt": "not_checked_no_rscript",
        "boot.LR": "not_checked_no_rscript",
        "mirtCluster": "not_checked_no_rscript",
    }
    if rscript_available:
        probe = (
            "has <- function(fn) requireNamespace('mirt', quietly=TRUE) && "
            "exists(fn, envir=asNamespace('mirt'), mode='function'); "
            "vals <- c("
            "paste0('R=', R.version.string), "
            "paste0('mirt=', if (requireNamespace('mirt', quietly=TRUE)) as.character(packageVersion('mirt')) else 'missing'), "
            "paste0('multipleGroup=', if (has('multipleGroup')) 'available' else 'missing'), "
            "paste0('DIF=', if (has('DIF')) 'available' else 'missing'), "
            "paste0('boot.mirt=', if (has('boot.mirt')) 'available' else 'missing'), "
            "paste0('boot.LR=', if (has('boot.LR')) 'available' else 'missing'), "
            "paste0('mirtCluster=', if (has('mirtCluster')) 'available' else 'missing')"
            "); cat(paste(vals, collapse=';'))"
        )
        result = subprocess.run(
            ["Rscript", "-e", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            for item in result.stdout.strip().split(";"):
                if "=" in item:
                    key, value = item.split("=", 1)
                    observed[key.strip()] = value.strip()
        else:
            for key in observed:
                if key != "R":
                    observed[key] = "probe_failed"

    core_functions_ready = all(
        observed[name] == "available"
        for name in ["multipleGroup", "DIF", "boot.mirt", "boot.LR"]
    )
    rows = [
        {
            "check_id": "Rscript_on_path",
            "status": "pass" if rscript_available else "blocked_runtime_missing",
            "observed": "available" if rscript_available else "missing",
            "decision": "MV14 execution requires the existing version-captured R runtime.",
        },
        {
            "check_id": "mirt_package",
            "status": "pass" if observed["mirt"] not in {"missing", "not_checked_no_rscript", "probe_failed"} else "blocked_package_missing",
            "observed": observed["mirt"],
            "decision": "mirt remains the primary external psychometric runtime.",
        },
        {
            "check_id": "multipleGroup_function",
            "status": "pass" if observed["multipleGroup"] == "available" else "blocked_function_missing",
            "observed": observed["multipleGroup"],
            "decision": "multipleGroup is required for the core E-DAIC/CMDC model ladder.",
        },
        {
            "check_id": "DIF_function",
            "status": "pass" if observed["DIF"] == "available" else "optional_missing",
            "observed": observed["DIF"],
            "decision": "DIF is useful as a documented reference path; the MV13 one-free model ladder remains acceptable if DIF is unavailable.",
        },
        {
            "check_id": "boot_mirt_function",
            "status": "pass" if observed["boot.mirt"] == "available" else "optional_missing",
            "observed": observed["boot.mirt"],
            "decision": "boot.mirt enables optional aggregate SE-availability sensitivity.",
        },
        {
            "check_id": "boot_LR_function",
            "status": "pass" if observed["boot.LR"] == "available" else "optional_missing",
            "observed": observed["boot.LR"],
            "decision": "boot.LR enables optional parametric LRT sensitivity.",
        },
        {
            "check_id": "mv14_runtime_ready",
            "status": "pass" if rscript_available and observed["mirt"] not in {"missing", "not_checked_no_rscript", "probe_failed"} and core_functions_ready else "ready_with_optional_or_runtime_caveat",
            "observed": "ready" if core_functions_ready else "core_runtime_or_optional_function_caveat",
            "decision": "The design can be complete even if optional bootstrap helpers are missing, but the execution run must version-capture any fallback.",
        },
    ]
    return pd.DataFrame(rows)


def source_evidence_summary(preflight: pd.DataFrame) -> pd.DataFrame:
    mv10 = read_json(MV10_DIR / "run_summary.json")
    mv11 = read_json(MV11_DIR / "run_summary.json")
    mv13 = read_json(MV13_DIR / "run_summary.json")
    full_gate_path = FULL_GATE_DIR / "run_summary.json"
    next_actions_path = FULL_GATE_DIR / "next_action_queue.csv"
    if full_gate_path.exists() and next_actions_path.exists():
        full_gate = read_json(full_gate_path)
        next_actions = read_csv(next_actions_path)
        top_action = next_actions.sort_values("rank").iloc[0].to_dict()
    else:
        full_gate = {
            "gate_status": "pending_refresh",
            "full_method_allowed": False,
        }
        top_action = {
            "action_id": "FULL_GATE_PENDING_REFRESH_AFTER_MV14_DESIGN",
        }
    input_audit = read_csv(MV13_DIR / "psychometric_input_audit.csv")
    fit = read_csv(MV13_DIR / "fit_model_summary.csv")
    anchors = read_csv(MV13_DIR / "anchor_confirmation_summary.csv")
    dif = read_csv(MV13_DIR / "item_dif_lrt_summary.csv")
    ci = read_csv(MV13_DIR / "parameter_ci_availability_summary.csv")

    mv10_v = mv10.get("verdict") or {}
    mv11_v = mv11.get("verdict") or {}
    mv13_v = mv13.get("verdict") or {}
    runtime = first_row(preflight, "check_id", "mv14_runtime_ready")
    core = fit[fit["model_id"].isin(["configural", "metric", "scalar", "partial_mv10"])].copy()
    configural = first_row(core, "model_id", "configural")
    loading_flags = sorted(dif.loc[(dif["dif_type"] == "loading") & bool_series(dif["strong_dif_flag"]), "construct_id"].astype(str))
    threshold_flags = sorted(dif.loc[(dif["dif_type"] == "threshold") & bool_series(dif["strong_dif_flag"]), "construct_id"].astype(str))
    confirmed = sorted(anchors.loc[bool_series(anchors["mv10_anchor_confirmed"]), "construct_id"].astype(str))
    ci_row = ci.iloc[0].to_dict() if not ci.empty else {}

    rows = [
        {
            "source_id": "MV10_approximate_phq_screen",
            "artifact": rel(MV10_DIR / "run_summary.json"),
            "status": mv10_v.get("status"),
            "observation": (
                f"loading_congruence={fmt(mv10_v.get('loading_congruence'))}; "
                f"metric_items={mv10_v.get('metric_invariant_items')}/8; "
                f"threshold_items={mv10_v.get('threshold_invariant_items')}/8; "
                f"candidate_anchors=C01;C04;C05;C07"
            ),
            "implication_for_mv14": "Bootstrap should quantify whether the approximate MV10 anchor pattern is stable under group-wise subject resampling.",
        },
        {
            "source_id": "MV11_formal_phq_confirmation",
            "artifact": rel(MV11_DIR / "run_summary.json"),
            "status": mv11_v.get("status"),
            "observation": (
                f"confirmed_anchors={mv11_v.get('confirmed_mv10_anchor_items')}; "
                f"loading_DIF_flags={mv11_v.get('loading_dif_flagged_items')}; "
                f"threshold_DIF_flags={mv11_v.get('threshold_dif_flagged_items')}; "
                f"AIC_BIC_split={mv11_v.get('core_model_aic_bic_split')}"
            ),
            "implication_for_mv14": "MV14 should report uncertainty around anchor preservation, threshold DIF localization, and AIC/BIC model preference.",
        },
        {
            "source_id": "MV13_external_mirt_replication",
            "artifact": rel(MV13_DIR / "run_summary.json"),
            "status": mv13_v.get("status"),
            "observation": (
                f"subjects_edaic={mv13_v.get('subjects', {}).get('edaic')}; "
                f"subjects_cmdc={mv13_v.get('subjects', {}).get('cmdc')}; "
                f"confirmed_anchors={';'.join(confirmed)}; "
                f"loading_DIF={';'.join(loading_flags) or 'none'}; "
                f"threshold_DIF={';'.join(threshold_flags) or 'none'}"
            ),
            "implication_for_mv14": "Use the MV13 R/mirt ladder as the default bootstrap refit family and keep all bootstrap rows local-only.",
        },
        {
            "source_id": "MV13_convergence_caveat",
            "artifact": rel(MV13_DIR / "fit_model_summary.csv"),
            "status": "needs_uncertainty_context",
            "observation": (
                f"configural_fit_success={configural.get('fit_success')}; "
                f"configural_converged={configural.get('converged')}; "
                f"configural_iterations={configural.get('iterations')}; "
                f"core_converged={mv13_v.get('core_converged')}"
            ),
            "implication_for_mv14": "Convergence frequency must be a first-class result, not a hidden runtime detail.",
        },
        {
            "source_id": "MV13_model_selection",
            "artifact": rel(MV13_DIR / "fit_model_summary.csv"),
            "status": "single_fit_reference",
            "observation": (
                f"best_AIC={mv13_v.get('best_aic_model')}; "
                f"best_BIC={mv13_v.get('best_bic_model')}; "
                f"core_models={len(core)}"
            ),
            "implication_for_mv14": "Bootstrap should report selection frequencies and interval summaries rather than a single model winner.",
        },
        {
            "source_id": "MV13_parameter_and_itemfit_availability",
            "artifact": rel(MV13_DIR / "parameter_ci_availability_summary.csv"),
            "status": mv13_v.get("parameter_ci_status"),
            "observation": (
                f"se_fit_success={ci_row.get('se_fit_success')}; "
                f"finite_SE_count={ci_row.get('finite_se_count')}; "
                f"itemfit_status={mv13_v.get('itemfit_status')}"
            ),
            "implication_for_mv14": "Track only SE/CI availability counts and item-fit flag frequencies; keep parameter values local-only.",
        },
        {
            "source_id": "MV13_input_counts",
            "artifact": rel(MV13_DIR / "psychometric_input_audit.csv"),
            "status": "groupwise_resampling_basis",
            "observation": "; ".join(
                f"{row['dataset']}={int(row['complete_item_subjects'])}"
                for _, row in input_audit.iterrows()
            ),
            "implication_for_mv14": "Bootstrap resampling unit is subject row within each dataset group, preserving original group sizes.",
        },
        {
            "source_id": "full_method_gate_next_action",
            "artifact": rel(FULL_GATE_DIR / "next_action_queue.csv"),
            "status": str(top_action.get("action_id")),
            "observation": (
                f"full_gate_status={full_gate.get('gate_status')}; "
                f"full_method_allowed={full_gate.get('full_method_allowed')}; "
                f"top_next_action={top_action.get('action_id')}"
            ),
            "implication_for_mv14": "MV14 can strengthen measurement wording but cannot authorize full multimodal method work by itself.",
        },
        {
            "source_id": "runtime_preflight",
            "artifact": "runtime_preflight.csv",
            "status": runtime["status"],
            "observation": f"runtime={runtime['observed']}",
            "implication_for_mv14": "Execution must version-capture the exact R/mirt bootstrap path and any fallback.",
        },
    ]
    return pd.DataFrame(rows)


def input_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "input_id": "local_phq_item_response_matrix",
            "scope": "E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 ordinal item labels",
            "allowed_source": "Manifest-governed item loader reused from MV10/MV13.",
            "bootstrap_unit": "subject row within dataset group",
            "tracked_surrogate": "dataset-level group sizes, item coverage, response-category support, and convergence summaries",
            "forbidden_public_outputs": "participant-grain response rows; local R input matrices; resampled row lists",
        },
        {
            "input_id": "bootstrap_resampling_indices",
            "scope": "Group-wise subject-row draws with replacement for E-DAIC and CMDC",
            "allowed_source": "Generated only inside the MV14 execution workspace with a recorded random seed.",
            "bootstrap_unit": "within-group subject row",
            "tracked_surrogate": "random seed, R count, group sizes, and aggregate convergence counts",
            "forbidden_public_outputs": "row indices; subject identifiers; duplicated-row traces; per-resample response matrices",
        },
        {
            "input_id": "mv10_mv11_mv13_reference_map",
            "scope": "C01/C04/C05/C07 anchors; C02/C06 threshold-DIF; C03/C08 sensitivity",
            "allowed_source": "Tracked aggregate anchor, DIF, and model-comparison summaries only.",
            "bootstrap_unit": "not resampled",
            "tracked_surrogate": "reference item roles and qualitative alignment categories",
            "forbidden_public_outputs": "post-hoc anchor reclassification chosen after seeing bootstrap outcomes",
        },
        {
            "input_id": "runtime_versions_and_logs",
            "scope": "R, mirt, optional bootstrap helper functions, thread counts, seeds, and timeouts",
            "allowed_source": "Execution-time version probes and bounded aggregate status logs.",
            "bootstrap_unit": "run-level",
            "tracked_surrogate": "runtime_versions, timing quantiles, warning-count summaries, and failure categories",
            "forbidden_public_outputs": "local library paths; full console logs containing row-level diagnostics; credentials",
        },
    ]
    return pd.DataFrame(rows)


def local_only_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "artifact_class": "bootstrap_item_response_inputs",
            "git_policy": "ignored_local_only",
            "reason": "Each bootstrap input is participant-grain label data even if identifiers are removed.",
            "allowed_tracked_derivative": "aggregate counts by dataset, item, model, and convergence category",
        },
        {
            "artifact_class": "bootstrap_resampling_indices",
            "git_policy": "ignored_local_only",
            "reason": "Resampling draws can reveal participant-grain multiplicities and row linkage.",
            "allowed_tracked_derivative": "seed, bootstrap count, and group-size summary",
        },
        {
            "artifact_class": "fitted_mirt_model_objects",
            "git_policy": "do_not_track",
            "reason": "Fitted objects contain full psychometric parameters and internals.",
            "allowed_tracked_derivative": "fit success, convergence, information-criterion, and warning-count summaries",
        },
        {
            "artifact_class": "full_parameter_or_ci_values",
            "git_policy": "local_only_if_generated",
            "reason": "Parameter estimates and CI values are fitted measurement outputs.",
            "allowed_tracked_derivative": "finite SE/CI availability counts and missingness reasons",
        },
        {
            "artifact_class": "factor_or_theta_scores",
            "git_policy": "do_not_track",
            "reason": "Latent scores are participant-grain outputs.",
            "allowed_tracked_derivative": "none in MV14; later MV15/MV16 may export aggregate identity or calibration summaries only",
        },
        {
            "artifact_class": "per_resample_row_logs",
            "git_policy": "ignored_local_only",
            "reason": "Detailed logs can contain row counts, sampled patterns, or failure traces tied to small groups.",
            "allowed_tracked_derivative": "failure-rate summaries and bounded warning-category counts",
        },
    ]
    return pd.DataFrame(rows)


def bootstrap_ladder_contract() -> pd.DataFrame:
    rows = [
        {
            "tier_id": "MV14_A_smoke_runtime",
            "default_R": 10,
            "purpose": "Confirm local-only bootstrap plumbing, deterministic seeds, runtime limits, and output hygiene before any claimable run.",
            "model_refits_per_draw": "core_ladder_only",
            "models": "configural;metric;scalar;partial_mv10",
            "claim_status": "not_claimable_smoke",
            "advance_rule": "All tracked outputs pass hygiene and at least metric/scalar/partial_mv10 can be attempted in most draws.",
        },
        {
            "tier_id": "MV14_B_core_model_stability",
            "default_R": 200,
            "purpose": "Estimate convergence and AIC/BIC model-selection stability for the MV13 core ladder.",
            "model_refits_per_draw": "4",
            "models": "configural;metric;scalar;partial_mv10",
            "claim_status": "primary_core_stability",
            "advance_rule": "Report convergence by model and AIC/BIC selection frequencies, even if the configural caveat persists.",
        },
        {
            "tier_id": "MV14_C_item_DIF_stability",
            "default_R": 100,
            "purpose": "Estimate loading-DIF and threshold-DIF selection frequencies for C01-C08.",
            "model_refits_per_draw": "up_to_20",
            "models": "core_ladder_plus_loading_free_one_item_and_threshold_free_one_item_models",
            "claim_status": "primary_anchor_and_DIF_stability",
            "advance_rule": "Run after smoke; if runtime is excessive, keep R fixed by predeclared timeout and report reduced effective R.",
        },
        {
            "tier_id": "MV14_D_boot_mirt_SE_availability",
            "default_R": 100,
            "purpose": "Optional boot.mirt sensitivity for aggregate SE/CI availability on the partial MV10 model.",
            "model_refits_per_draw": "handled_by_boot_mirt",
            "models": "partial_mv10_with_boot_fun_returning_aggregate_counts_only",
            "claim_status": "optional_parameter_uncertainty_availability",
            "advance_rule": "Track availability counts only; do not track bootstrapped parameter values or CIs.",
        },
        {
            "tier_id": "MV14_E_parametric_LR_sensitivity",
            "default_R": 100,
            "purpose": "Optional boot.LR sensitivity for nested-model p-values when asymptotic LRT decisions are unstable.",
            "model_refits_per_draw": "handled_by_boot_LR",
            "models": "metric_vs_configural;scalar_vs_metric;partial_mv10_vs_configural_where_valid",
            "claim_status": "optional_nested_LRT_uncertainty",
            "advance_rule": "Use only for valid nested pairs that converge; otherwise document skip reason aggregate-only.",
        },
    ]
    return pd.DataFrame(rows)


def stability_metric_contract() -> pd.DataFrame:
    rows = [
        {
            "metric_id": "core_convergence_frequency",
            "bootstrap_tier": "MV14_B_core_model_stability",
            "definition": "For each core model, successful converged fits divided by attempted bootstrap draws.",
            "tracked_output": "core model, attempted R, converged R, convergence rate, Wilson interval, warning categories",
            "interpretation_rule": "Low or uneven convergence downgrades item-level wording before any anchor/DIF interpretation.",
        },
        {
            "metric_id": "model_selection_frequency",
            "bootstrap_tier": "MV14_B_core_model_stability",
            "definition": "Frequency that configural, metric, scalar, or partial_mv10 is selected by AIC and by BIC among successful core fits.",
            "tracked_output": "selection frequencies and uncertainty intervals by criterion",
            "interpretation_rule": "Report AIC/BIC disagreement as part of the result; do not force a single winner.",
        },
        {
            "metric_id": "anchor_support_frequency",
            "bootstrap_tier": "MV14_C_item_DIF_stability",
            "definition": "For each C01-C08 item, frequency of no loading-DIF and no threshold-DIF flag under the MV13 one-free item rule.",
            "tracked_output": "item-level support frequency and interval, aggregate-only",
            "interpretation_rule": "MV10 anchors C01/C04/C05/C07 need high support before being described as stable anchors.",
        },
        {
            "metric_id": "loading_DIF_flag_frequency",
            "bootstrap_tier": "MV14_C_item_DIF_stability",
            "definition": "For each C01-C08 item, frequency that freeing the loading is supported by both LRT alpha 0.01 and BIC improvement greater than 2.",
            "tracked_output": "item-level loading-DIF frequency, effective R, and interval",
            "interpretation_rule": "Loading DIF should remain sparse; diffuse loading DIF downgrades the common-metric claim.",
        },
        {
            "metric_id": "threshold_DIF_flag_frequency",
            "bootstrap_tier": "MV14_C_item_DIF_stability",
            "definition": "For each C01-C08 item, frequency that freeing thresholds is supported by both LRT alpha 0.01 and BIC improvement greater than 2.",
            "tracked_output": "item-level threshold-DIF frequency, rank, effective R, and interval",
            "interpretation_rule": "Strong wording about C02/C06 is allowed only if threshold-DIF frequency remains concentrated there.",
        },
        {
            "metric_id": "CI_or_SE_availability",
            "bootstrap_tier": "MV14_D_boot_mirt_SE_availability",
            "definition": "Availability of finite bootstrap or model-based SEs, counted without exporting parameter values.",
            "tracked_output": "finite-SE count distribution and failure reasons only",
            "interpretation_rule": "Use as uncertainty availability, not as a public parameter appendix unless separately approved.",
        },
        {
            "metric_id": "itemfit_flag_frequency",
            "bootstrap_tier": "MV14_C_item_DIF_stability",
            "definition": "Frequency that item-fit diagnostics are available and flag p less than 0.01 for each dataset-item aggregate.",
            "tracked_output": "dataset-item flag frequencies and availability counts",
            "interpretation_rule": "Item-fit instability is a caveat on item-level DIF interpretation.",
        },
        {
            "metric_id": "mv11_mv13_mv14_alignment",
            "bootstrap_tier": "MV14_B_core_model_stability;MV14_C_item_DIF_stability",
            "definition": "Aggregate agreement between MV11/MV13 single-fit decisions and MV14 frequency-based decisions.",
            "tracked_output": "alignment rows for anchors, loading DIF, threshold DIF, and model preference",
            "interpretation_rule": "Disagreement revises manuscript wording rather than being hidden.",
        },
    ]
    return pd.DataFrame(rows)


def pass_fail_gate_contract(preflight: pd.DataFrame) -> pd.DataFrame:
    runtime_ready = first_row(preflight, "check_id", "mv14_runtime_ready")["status"] == "pass"
    rows = [
        {
            "gate_id": "G0_predeclaration_complete",
            "status": "pass",
            "current_evidence": "MV14 defines bootstrap tiers, local-only boundaries, stability metrics, and claim downgrades before execution.",
            "future_execution_rule": "Execution must either follow this contract or supersede it with a newer dated predeclaration before running.",
            "claim_effect": "Design pass only; no measurement-uncertainty result yet.",
        },
        {
            "gate_id": "G1_runtime_ready",
            "status": "pass" if runtime_ready else "pass_with_optional_runtime_caveat",
            "current_evidence": "runtime_preflight records Rscript, mirt, multipleGroup, DIF, boot.mirt, and boot.LR availability.",
            "future_execution_rule": "Any missing optional function must be replaced by the MV13 one-free refit ladder or documented as skipped aggregate-only.",
            "claim_effect": "Runtime readiness allows implementation, but does not strengthen measurement claims until bootstrap completes.",
        },
        {
            "gate_id": "G2_local_only_boundary",
            "status": "pass_for_design",
            "current_evidence": "Local item matrices, bootstrap draws, model objects, parameter values, factor scores, and detailed logs are declared non-public.",
            "future_execution_rule": "Artifact hygiene must fail if these artifacts enter tracked outputs.",
            "claim_effect": "Boundary failure blocks commit and publication.",
        },
        {
            "gate_id": "G3_convergence_visibility",
            "status": "pending_bootstrap_run",
            "current_evidence": "MV13 configural fit succeeded but did not converge within 3000 EM cycles.",
            "future_execution_rule": "Report convergence frequency for every core model and use effective R after convergence filters.",
            "claim_effect": "Low convergence downgrades anchor/DIF wording to exploratory stability evidence.",
        },
        {
            "gate_id": "G4_anchor_stability",
            "status": "pending_bootstrap_run",
            "current_evidence": "MV10/MV11/MV13 agree on C01/C04/C05/C07 as anchors.",
            "future_execution_rule": "All four MV10 anchors should show support frequency >=0.70 for stable-anchor wording; any anchor <0.60 requires downgrade.",
            "claim_effect": "Stable anchors support bounded PHQ partial-invariance wording, not full scalar invariance.",
        },
        {
            "gate_id": "G5_loading_DIF_sparsity",
            "status": "pending_bootstrap_run",
            "current_evidence": "MV11/MV13 flag zero strong loading-DIF items.",
            "future_execution_rule": "No more than one item should exceed loading-DIF frequency 0.50; MV10 anchors should remain below 0.30.",
            "claim_effect": "Diffuse loading DIF blocks common-metric wording.",
        },
        {
            "gate_id": "G6_threshold_DIF_localization",
            "status": "pending_bootstrap_run",
            "current_evidence": "MV11/MV13 flag C02 and C06 threshold DIF.",
            "future_execution_rule": "C02 and C06 should be the top two threshold-DIF frequencies or both exceed 0.50 while non-target items remain clearly lower.",
            "claim_effect": "If unstable, describe threshold DIF as suggestive rather than item-specific.",
        },
        {
            "gate_id": "G7_model_selection_uncertainty",
            "status": "pending_bootstrap_run",
            "current_evidence": "MV11/MV13 split AIC partial versus BIC scalar.",
            "future_execution_rule": "Report AIC and BIC selection frequencies separately; do not require them to agree.",
            "claim_effect": "Model-selection instability narrows manuscript wording but does not by itself block a diagnostic paper.",
        },
        {
            "gate_id": "G8_no_full_method_authorization",
            "status": "pass_for_design",
            "current_evidence": "The Phase 5 full-method gate remains blocked.",
            "future_execution_rule": "MV14 can support measurement uncertainty language only; it cannot start M0/M1/M2/M3 by itself.",
            "claim_effect": "Full method remains blocked until later predeclared MV15/MV16 or another gate changes.",
        },
    ]
    return pd.DataFrame(rows)


def implementation_queue(preflight: pd.DataFrame) -> pd.DataFrame:
    runtime_status = first_row(preflight, "check_id", "mv14_runtime_ready")["status"]
    rows = [
        {
            "rank": 1,
            "action_id": "IMPLEMENT_MV14_R_BOOTSTRAP_RUNNER",
            "action": "Create a Python orchestration runner plus R bootstrap script reusing the MV13 item loader and model syntax.",
            "success_gate": "Smoke tier completes with aggregate-only outputs and no local-only artifacts tracked.",
            "version_policy": "Track runner code and aggregate contract outputs; keep R input and bootstrap workspaces ignored.",
        },
        {
            "rank": 2,
            "action_id": "RUN_MV14_SMOKE_RUNTIME_TIER",
            "action": "Run MV14_A with R=10 to verify deterministic seeds, timeouts, and warning categorization.",
            "success_gate": f"Runtime status is {runtime_status}; smoke results produce only aggregate diagnostics and hygiene passes.",
            "version_policy": "Track smoke aggregate only if it is explicitly marked not-claimable.",
        },
        {
            "rank": 3,
            "action_id": "RUN_MV14_CORE_MODEL_STABILITY",
            "action": "Run MV14_B with default R=200 for core convergence and model-selection frequencies.",
            "success_gate": "Core stability table reports attempted R, effective R, convergence rates, AIC/BIC frequencies, and uncertainty intervals.",
            "version_policy": "Track aggregate stability summaries only.",
        },
        {
            "rank": 4,
            "action_id": "RUN_MV14_ITEM_DIF_STABILITY",
            "action": "Run MV14_C with default R=100 for anchor, loading-DIF, and threshold-DIF selection frequencies.",
            "success_gate": "Item-level stability table reports support frequencies and explicitly downgrades unstable items.",
            "version_policy": "Track item aggregate summaries only; no per-resample tables.",
        },
        {
            "rank": 5,
            "action_id": "RUN_OPTIONAL_BOOT_MIRT_OR_BOOT_LR_SENSITIVITY",
            "action": "Run MV14_D/E only if runtime permits and functions are available; otherwise record aggregate skip reasons.",
            "success_gate": "Optional tiers either finish with aggregate availability summaries or are skipped with predeclared reasons.",
            "version_policy": "Do not track parameter values, CI values, fitted objects, or full bootstrap draws.",
        },
        {
            "rank": 6,
            "action_id": "REFRESH_GATE_AND_MANUSCRIPT_BOUNDARY",
            "action": "After MV14 run, refresh full-method gate, issue log, memory, README, and paper scaffolds.",
            "success_gate": "Next action moves from MV14 implementation to MV15/MV16 only if uncertainty wording is coherent.",
            "version_policy": "Commit scripts, aggregate summaries, docs, and memory through the clean GitHub publish workflow.",
        },
    ]
    return pd.DataFrame(rows)


def method_source_refs() -> pd.DataFrame:
    return pd.DataFrame(METHOD_SOURCE_REFS)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"source_locator",
        r"local_annotation_workbook",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw prompt",
        r"raw response",
        r"parameter_value",
        r"factor_score_value",
        r"theta_score_value",
        r"posterior_score",
        r"resampling_index",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in TRACKED_FILES:
        path = out_dir / name
        if not path.exists() or not path.is_file():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": name, "pattern": pattern})
    return {
        "audit_id": "P5_MV14_measurement_uncertainty_bootstrap_design_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    decision = run_summary["decision"]
    evidence = read_csv(out_dir / "source_evidence_summary.csv")
    tiers = read_csv(out_dir / "bootstrap_ladder_contract.csv")
    gates = read_csv(out_dir / "pass_fail_gate_contract.csv")
    metrics = read_csv(out_dir / "stability_metric_contract.csv")
    queue = read_csv(out_dir / "implementation_queue.csv")

    lines = [
        "# P5 MV14 Measurement-Uncertainty Bootstrap Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Design status: `{decision['design_status']}`.",
        f"- MV14 runtime ready: `{decision['mv14_runtime_ready']}`.",
        f"- Full method allowed: `{decision['full_method_allowed']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "MV14 is predeclared as a measurement-stability audit for the PHQ E-DAIC/CMDC anchor and DIF story. It is not a multimodal model and it does not authorize the full method.",
        "",
        "## Source Evidence",
        "",
        "| source | status | observation |",
        "| --- | --- | --- |",
    ]
    for _, row in evidence.iterrows():
        lines.append(f"| {row['source_id']} | `{row['status']}` | {md_escape(row['observation'])} |")

    lines.extend(
        [
            "",
            "## Bootstrap Ladder",
            "",
            "| tier | R | role | models |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for _, row in tiers.iterrows():
        lines.append(f"| {row['tier_id']} | {int(row['default_R'])} | {row['claim_status']} | {md_escape(row['models'])} |")

    lines.extend(
        [
            "",
            "## Stability Metrics",
            "",
            "| metric | tier | interpretation rule |",
            "| --- | --- | --- |",
        ]
    )
    for _, row in metrics.iterrows():
        lines.append(f"| {row['metric_id']} | {row['bootstrap_tier']} | {md_escape(row['interpretation_rule'])} |")

    lines.extend(
        [
            "",
            "## Gates",
            "",
            "| gate | status | future execution rule |",
            "| --- | --- | --- |",
        ]
    )
    for _, row in gates.iterrows():
        lines.append(f"| {row['gate_id']} | `{row['status']}` | {md_escape(row['future_execution_rule'])} |")

    lines.extend(
        [
            "",
            "## Implementation Queue",
            "",
            "| rank | action | success gate |",
            "| ---: | --- | --- |",
        ]
    )
    for _, row in queue.sort_values("rank").iterrows():
        lines.append(f"| {int(row['rank'])} | {md_escape(row['action'])} | {md_escape(row['success_gate'])} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- Track only aggregate convergence, selection-frequency, stability, and hygiene outputs.",
            "- Keep bootstrap inputs, draw indices, fitted parameters, model objects, scores, and detailed logs local-only.",
            "- If anchor or DIF stability is weak, downgrade item-level DIF language before manuscript drafting.",
            "- Even a successful MV14 keeps full method work blocked until later predeclared MV15/MV16 gates change the boundary.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, generated_at: str, overwrite: bool) -> dict[str, Any]:
    if out_dir.exists() and overwrite:
        for name in TRACKED_FILES:
            path = out_dir / name
            if path.exists() and path.is_file():
                path.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    preflight = runtime_preflight()
    evidence = source_evidence_summary(preflight)
    inputs = input_boundary_contract()
    local_only = local_only_boundary_contract()
    tiers = bootstrap_ladder_contract()
    metrics = stability_metric_contract()
    gates = pass_fail_gate_contract(preflight)
    queue = implementation_queue(preflight)
    refs = method_source_refs()

    preflight.to_csv(out_dir / "runtime_preflight.csv", index=False)
    evidence.to_csv(out_dir / "source_evidence_summary.csv", index=False)
    inputs.to_csv(out_dir / "input_boundary_contract.csv", index=False)
    local_only.to_csv(out_dir / "local_only_boundary_contract.csv", index=False)
    tiers.to_csv(out_dir / "bootstrap_ladder_contract.csv", index=False)
    metrics.to_csv(out_dir / "stability_metric_contract.csv", index=False)
    gates.to_csv(out_dir / "pass_fail_gate_contract.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    runtime_ready = first_row(preflight, "check_id", "mv14_runtime_ready")["status"] == "pass"
    run_summary = {
        "run_id": "P5_MV14_measurement_uncertainty_bootstrap_design",
        "generated_at": generated_at,
        "scope": "measurement_uncertainty_bootstrap_predeclaration",
        "status": "complete",
        "input_contract": {
            "label_only": True,
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"],
            "bootstrap_unit": "subject_row_within_dataset_group",
            "multimodal_features_read": False,
            "media_or_transcripts_read": False,
            "row_level_predictions_read": False,
            "participant_grain_outputs_written": False,
            "external_bootstrap_run_performed": False,
        },
        "runtime_preflight": {
            "rscript_available": bool(first_row(preflight, "check_id", "Rscript_on_path")["status"] == "pass"),
            "mirt_status": first_row(preflight, "check_id", "mirt_package")["observed"],
            "multipleGroup_status": first_row(preflight, "check_id", "multipleGroup_function")["observed"],
            "DIF_status": first_row(preflight, "check_id", "DIF_function")["observed"],
            "boot_mirt_status": first_row(preflight, "check_id", "boot_mirt_function")["observed"],
            "boot_LR_status": first_row(preflight, "check_id", "boot_LR_function")["observed"],
            "mv14_runtime_ready": bool(runtime_ready),
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "source_evidence_rows": int(len(evidence)),
            "input_contract_rows": int(len(inputs)),
            "local_only_boundary_rows": int(len(local_only)),
            "bootstrap_tier_rows": int(len(tiers)),
            "stability_metric_rows": int(len(metrics)),
            "gate_rows": int(len(gates)),
            "implementation_rows": int(len(queue)),
            "method_source_rows": int(len(refs)),
        },
        "decision": {
            "design_status": (
                "ready_to_implement_mv14_measurement_uncertainty_bootstrap"
                if runtime_ready
                else "complete_predeclared_mv14_runtime_caveat"
            ),
            "mv14_runtime_ready": bool(runtime_ready),
            "full_method_allowed": False,
            "short_read": (
                "MV14 is predeclared as an aggregate-only bootstrap stability audit for PHQ anchors, "
                "DIF flags, model selection, convergence, and uncertainty availability."
            ),
            "next_action": "IMPLEMENT_MV14_R_BOOTSTRAP_RUNNER",
        },
        "local_only_files": {
            "bootstrap_item_response_inputs": "group-wise resampled participant-grain item matrices",
            "bootstrap_resampling_draws": "within-dataset draw indices and row multiplicities",
            "fitted_mirt_model_objects": "all fitted bootstrap model objects",
            "fitted_parameters_or_ci_values": "full item parameters and confidence interval values",
            "factor_or_theta_scores": "all latent/factor scores",
            "per_resample_logs": "detailed warnings and fit traces",
        },
        "artifact_hygiene_passed": False,
    }

    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    write_json(out_dir / "artifact_hygiene_audit.json", hygiene)
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    summary = build_outputs(args.out_dir, utc_now(), args.overwrite)
    display_out = args.out_dir.resolve().relative_to(ROOT) if args.out_dir.is_absolute() else args.out_dir
    print(
        json.dumps(
            {
                "out_dir": str(display_out),
                "design_status": summary["decision"]["design_status"],
                "mv14_runtime_ready": summary["decision"]["mv14_runtime_ready"],
                "artifact_hygiene_passed": summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
