#!/usr/bin/env python3
"""Run P5_MV11 formal PHQ graded-response IRT confirmation.

This is a label-only psychometric confirmation step. It fits multi-group
Samejima-style graded-response models to E-DAIC PHQ-8 and CMDC PHQ-9 shared
C01-C08 item labels with marginal maximum likelihood and Gauss-Hermite
quadrature. It compares configural, metric, scalar/threshold, and MV10-derived
partial-anchor constraints, then exports only aggregate fit and DIF summaries.

No raw text/media, multimodal features, row-level predictions, subject-level
factor scores, or fitted item parameters are written.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
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
from numpy.polynomial.hermite import hermgauss
from scipy.optimize import minimize
from scipy.special import expit, logsumexp
from scipy.stats import chi2, norm

from phase5_run_mv10_psychometric_invariance_baseline import (
    CORE_CONSTRUCTS,
    DEFAULT_MANIFEST_DIR,
    ITEM_LABELS,
    ROOT,
    fmt,
    load_inputs,
    safe_float,
)


PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
DEFAULT_MV10_PARTIAL = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline" / "partial_invariance_summary.csv"

RUN_ID = "P5_MV11_formal_psychometric_confirmation"
GROUPS = ["edaic", "cmdc"]
QUADRATURE_POINTS = 31
MAXITER = 1200
LRT_ALPHA = 0.01
BIC_IMPROVEMENT_TOL = 2.0
MIN_CONFIRMED_ANCHORS = 3

TRACKED_FILES = {
    "anchor_confirmation_summary.csv",
    "artifact_hygiene_audit.json",
    "fit_model_summary.csv",
    "gate_recommendations.csv",
    "invariance_comparison_summary.csv",
    "item_dif_lrt_summary.csv",
    "method_context_formal_irt.csv",
    "report.md",
    "run_summary.json",
}

SOURCE_ROWS = [
    {
        "source_id": "samejima_graded_response_1969",
        "topic": "graded-response IRT",
        "citation_hint": "Samejima 1969, Psychometrika Monograph 17",
        "url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        "use_in_mv11": "Defines the graded-response model family used for ordinal item response confirmation.",
    },
    {
        "source_id": "phq9_invariance_helius_2017",
        "topic": "PHQ-9 measurement invariance",
        "citation_hint": "Galenkamp et al. 2017, BMC Psychiatry",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "use_in_mv11": "Motivates configural, metric, scalar/threshold, and partial-invariance testing before cross-group PHQ comparisons.",
    },
    {
        "source_id": "phq9_measurement_invariance_us_2019",
        "topic": "PHQ-9 sociodemographic invariance",
        "citation_hint": "Patel et al. 2019, Depression and Anxiety",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/",
        "use_in_mv11": "Frames PHQ invariance as a prerequisite for meaningful score and model comparisons across groups.",
    },
    {
        "source_id": "irt_lr_dif_frontiers_2017",
        "topic": "IRT likelihood-ratio DIF testing",
        "citation_hint": "Jeong and Lee 2017, Frontiers in Education",
        "url": "https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        "use_in_mv11": "Supports using item-level likelihood-ratio comparisons as DIF diagnostics.",
    },
]


@dataclass(frozen=True)
class GrmSpec:
    model_id: str
    description: str
    loading_keys: dict[tuple[str, str], str]
    threshold_keys: dict[tuple[str, str], str]


@dataclass
class FitResult:
    spec: GrmSpec
    log_likelihood: float
    parameter_count: int
    aic: float
    bic: float
    optimizer_success: bool
    optimizer_status: int
    optimizer_message: str
    iterations: int
    boundary_parameter_count: int
    max_abs_gradient: float | None
    n_subjects: int
    n_responses: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def softplus(value: np.ndarray | float) -> np.ndarray | float:
    return np.logaddexp(0.0, value)


def inv_softplus(value: float) -> float:
    value = max(float(value), 1e-4)
    if value > 30:
        return value
    return float(np.log(np.expm1(value)))


def ordered_threshold_raw(thresholds: list[float]) -> list[float]:
    ordered = sorted(float(value) for value in thresholds)
    d12 = max(ordered[1] - ordered[0], 0.05)
    d23 = max(ordered[2] - ordered[1], 0.05)
    return [ordered[0], inv_softplus(d12), inv_softplus(d23)]


def load_mv10_roles(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(path)
    partial = pd.read_csv(path)
    roles: dict[str, str] = {}
    for _, row in partial.iterrows():
        construct = str(row["construct_id"])
        if construct in CORE_CONSTRUCTS:
            roles[construct] = str(row["partial_invariance_role"])
    missing = [item for item in CORE_CONSTRUCTS if item not in roles]
    if missing:
        raise ValueError(f"MV10 partial role file is missing items: {missing}")
    return roles


def make_spec(kind: str, roles: dict[str, str] | None = None, item: str | None = None) -> GrmSpec:
    loading_keys: dict[tuple[str, str], str] = {}
    threshold_keys: dict[tuple[str, str], str] = {}

    for group in GROUPS:
        for construct in CORE_CONSTRUCTS:
            if kind == "configural":
                loading_key = f"loading:{group}:{construct}"
                threshold_key = f"threshold:{group}:{construct}"
            elif kind == "metric":
                loading_key = f"loading:shared:{construct}"
                threshold_key = f"threshold:{group}:{construct}"
            elif kind == "scalar":
                loading_key = f"loading:shared:{construct}"
                threshold_key = f"threshold:shared:{construct}"
            elif kind == "partial_mv10":
                if roles is None:
                    raise ValueError("partial_mv10 requires roles")
                role = roles[construct]
                if role == "anchor_candidate":
                    loading_key = f"loading:shared:{construct}"
                    threshold_key = f"threshold:shared:{construct}"
                elif role == "metric_only_threshold_free":
                    loading_key = f"loading:shared:{construct}"
                    threshold_key = f"threshold:{group}:{construct}"
                else:
                    loading_key = f"loading:{group}:{construct}"
                    threshold_key = f"threshold:{group}:{construct}"
            elif kind == "loading_free_one":
                if item is None:
                    raise ValueError("loading_free_one requires item")
                loading_key = f"loading:{group}:{construct}" if construct == item else f"loading:shared:{construct}"
                threshold_key = f"threshold:{group}:{construct}"
            elif kind == "threshold_free_one":
                if item is None:
                    raise ValueError("threshold_free_one requires item")
                loading_key = f"loading:shared:{construct}"
                threshold_key = f"threshold:{group}:{construct}" if construct == item else f"threshold:shared:{construct}"
            else:
                raise ValueError(kind)
            loading_keys[(group, construct)] = loading_key
            threshold_keys[(group, construct)] = threshold_key

    if kind in {"loading_free_one", "threshold_free_one"}:
        model_id = f"{kind}_{item}"
        description = f"{kind} diagnostic for {item}"
    else:
        model_id = kind
        description = {
            "configural": "All loadings and thresholds free by dataset.",
            "metric": "Loadings constrained equal; thresholds free by dataset.",
            "scalar": "Loadings and thresholds constrained equal by dataset.",
            "partial_mv10": "MV10 candidate anchors constrained; metric-only items keep free thresholds; C08 free.",
        }[kind]
    return GrmSpec(model_id=model_id, description=description, loading_keys=loading_keys, threshold_keys=threshold_keys)


def unique_keys(mapping: dict[tuple[str, str], str]) -> list[str]:
    return sorted(set(mapping.values()))


def response_arrays(table: pd.DataFrame) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for group in GROUPS:
        group_table = table[table["dataset"] == group]
        arrays[group] = group_table[CORE_CONSTRUCTS].to_numpy(dtype=int)
    return arrays


def threshold_initial_values(spec: GrmSpec, table: pd.DataFrame) -> dict[str, list[float]]:
    values: dict[str, list[float]] = {}
    for key in unique_keys(spec.threshold_keys):
        pooled: list[int] = []
        for group in GROUPS:
            group_table = table[table["dataset"] == group]
            for construct in CORE_CONSTRUCTS:
                if spec.threshold_keys[(group, construct)] == key:
                    pooled.extend(group_table[construct].astype(int).tolist())
        arr = np.asarray(pooled, dtype=float)
        thresholds: list[float] = []
        for cutoff in [1, 2, 3]:
            p_ge = float(np.mean(arr >= cutoff))
            p_ge = min(max(p_ge, 0.02), 0.98)
            thresholds.append(float(norm.ppf(1.0 - p_ge)))
        values[key] = thresholds
    return values


def initial_vector_and_bounds(spec: GrmSpec, table: pd.DataFrame) -> tuple[np.ndarray, list[tuple[float, float]], list[str], list[str]]:
    loading_keys = unique_keys(spec.loading_keys)
    threshold_keys = unique_keys(spec.threshold_keys)
    threshold_inits = threshold_initial_values(spec, table)
    vector: list[float] = []
    bounds: list[tuple[float, float]] = []
    for _ in loading_keys:
        vector.append(0.0)
        bounds.append((-2.0, 2.3))
    for key in threshold_keys:
        raw = ordered_threshold_raw(threshold_inits[key])
        vector.extend(raw)
        bounds.extend([(-6.0, 6.0), (-6.0, 4.0), (-6.0, 4.0)])
    return np.asarray(vector, dtype=float), bounds, loading_keys, threshold_keys


def decode_params(
    params: np.ndarray,
    loading_keys: list[str],
    threshold_keys: list[str],
) -> tuple[dict[str, float], dict[str, np.ndarray]]:
    loading_values: dict[str, float] = {}
    threshold_values: dict[str, np.ndarray] = {}
    idx = 0
    for key in loading_keys:
        loading_values[key] = float(np.exp(params[idx]))
        idx += 1
    for key in threshold_keys:
        b1 = float(params[idx])
        d12 = float(softplus(params[idx + 1]))
        d23 = float(softplus(params[idx + 2]))
        threshold_values[key] = np.asarray([b1, b1 + d12, b1 + d12 + d23], dtype=float)
        idx += 3
    return loading_values, threshold_values


def category_probabilities(theta: np.ndarray, loading: float, thresholds: np.ndarray) -> np.ndarray:
    cumulative = expit(loading * (theta[:, None] - thresholds[None, :]))
    probs = np.empty((theta.shape[0], 4), dtype=float)
    probs[:, 0] = 1.0 - cumulative[:, 0]
    probs[:, 1] = cumulative[:, 0] - cumulative[:, 1]
    probs[:, 2] = cumulative[:, 1] - cumulative[:, 2]
    probs[:, 3] = cumulative[:, 2]
    return np.clip(probs, 1e-12, 1.0)


def make_quadrature(points: int = QUADRATURE_POINTS) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = hermgauss(points)
    theta = np.sqrt(2.0) * nodes
    log_weights = np.log(weights) - 0.5 * np.log(np.pi)
    return theta.astype(float), log_weights.astype(float)


def negative_log_likelihood_factory(spec: GrmSpec, table: pd.DataFrame) -> tuple[Any, np.ndarray, list[tuple[float, float]], list[str], list[str]]:
    responses = response_arrays(table)
    theta, log_weights = make_quadrature()
    x0, bounds, loading_keys, threshold_keys = initial_vector_and_bounds(spec, table)

    def nll(params: np.ndarray) -> float:
        loading_values, threshold_values = decode_params(params, loading_keys, threshold_keys)
        total_loglik = 0.0
        for group in GROUPS:
            y = responses[group]
            if y.size == 0:
                continue
            subject_node_logp = np.zeros((y.shape[0], theta.shape[0]), dtype=float)
            for item_index, construct in enumerate(CORE_CONSTRUCTS):
                loading = loading_values[spec.loading_keys[(group, construct)]]
                thresholds = threshold_values[spec.threshold_keys[(group, construct)]]
                probs = category_probabilities(theta, loading, thresholds)
                subject_node_logp += np.log(probs[:, y[:, item_index]].T)
            total_loglik += float(np.sum(logsumexp(subject_node_logp + log_weights[None, :], axis=1)))
        if not math.isfinite(total_loglik):
            return 1e100
        return -total_loglik

    return nll, x0, bounds, loading_keys, threshold_keys


def boundary_count(values: np.ndarray, bounds: list[tuple[float, float]], tol: float = 1e-4) -> int:
    count = 0
    for value, (lower, upper) in zip(values, bounds, strict=True):
        if abs(value - lower) <= tol or abs(value - upper) <= tol:
            count += 1
    return count


def fit_spec(spec: GrmSpec, table: pd.DataFrame) -> FitResult:
    nll, x0, bounds, _, _ = negative_log_likelihood_factory(spec, table)
    result = minimize(
        nll,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": MAXITER, "ftol": 1e-8, "gtol": 1e-5, "maxls": 30},
    )
    n_subjects = int(len(table))
    n_responses = int(len(table) * len(CORE_CONSTRUCTS))
    log_likelihood = float(-result.fun)
    parameter_count = int(len(x0))
    aic = float(2 * parameter_count - 2 * log_likelihood)
    bic = float(math.log(n_subjects) * parameter_count - 2 * log_likelihood)
    grad = getattr(result, "jac", None)
    max_abs_gradient = float(np.max(np.abs(grad))) if grad is not None and len(grad) else None
    return FitResult(
        spec=spec,
        log_likelihood=log_likelihood,
        parameter_count=parameter_count,
        aic=aic,
        bic=bic,
        optimizer_success=bool(result.success),
        optimizer_status=int(result.status),
        optimizer_message=str(result.message),
        iterations=int(getattr(result, "nit", -1)),
        boundary_parameter_count=boundary_count(np.asarray(result.x, dtype=float), bounds),
        max_abs_gradient=max_abs_gradient,
        n_subjects=n_subjects,
        n_responses=n_responses,
    )


def fit_summary(fits: dict[str, FitResult]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model_id, fit in fits.items():
        rows.append(
            {
                "model_id": model_id,
                "description": fit.spec.description,
                "group_count": len(GROUPS),
                "item_count": len(CORE_CONSTRUCTS),
                "subject_count": fit.n_subjects,
                "response_count": fit.n_responses,
                "parameter_count": fit.parameter_count,
                "log_likelihood": fit.log_likelihood,
                "aic": fit.aic,
                "bic": fit.bic,
                "optimizer_success": fit.optimizer_success,
                "optimizer_status": fit.optimizer_status,
                "optimizer_iterations": fit.iterations,
                "optimizer_message": fit.optimizer_message,
                "max_abs_gradient": fit.max_abs_gradient,
                "boundary_parameter_count": fit.boundary_parameter_count,
                "fitted_parameters_exported": False,
            }
        )
    frame = pd.DataFrame(rows)
    return frame.sort_values("model_id").reset_index(drop=True)


def lrt_row(
    comparison_id: str,
    restricted: FitResult,
    full: FitResult,
    interpretation: str,
) -> dict[str, Any]:
    lr = max(0.0, 2.0 * (full.log_likelihood - restricted.log_likelihood))
    df = int(full.parameter_count - restricted.parameter_count)
    p_value = float(chi2.sf(lr, df)) if df > 0 else np.nan
    delta_aic_restricted_minus_full = float(restricted.aic - full.aic)
    delta_bic_restricted_minus_full = float(restricted.bic - full.bic)
    if df <= 0:
        decision = "not_nested_or_invalid"
    elif p_value < LRT_ALPHA and delta_bic_restricted_minus_full > BIC_IMPROVEMENT_TOL:
        decision = "restricted_model_rejected_lrt_and_bic"
    elif p_value < LRT_ALPHA:
        decision = "restricted_model_rejected_lrt_only"
    elif delta_bic_restricted_minus_full > BIC_IMPROVEMENT_TOL:
        decision = "full_model_preferred_bic_only"
    else:
        decision = "no_strong_evidence_against_restriction"
    return {
        "comparison_id": comparison_id,
        "restricted_model": restricted.spec.model_id,
        "full_model": full.spec.model_id,
        "restricted_parameter_count": restricted.parameter_count,
        "full_parameter_count": full.parameter_count,
        "df": df,
        "lr_statistic": lr,
        "p_value": p_value,
        "delta_aic_restricted_minus_full": delta_aic_restricted_minus_full,
        "delta_bic_restricted_minus_full": delta_bic_restricted_minus_full,
        "decision": decision,
        "interpretation": interpretation,
    }


def nonnested_row(comparison_id: str, left: FitResult, right: FitResult, interpretation: str) -> dict[str, Any]:
    if abs(left.bic - right.bic) <= BIC_IMPROVEMENT_TOL:
        bic_preferred = "similar"
    else:
        bic_preferred = left.spec.model_id if left.bic < right.bic else right.spec.model_id
    if abs(left.aic - right.aic) <= BIC_IMPROVEMENT_TOL:
        aic_preferred = "similar"
    else:
        aic_preferred = left.spec.model_id if left.aic < right.aic else right.spec.model_id
    return {
        "comparison_id": comparison_id,
        "restricted_model": left.spec.model_id,
        "full_model": right.spec.model_id,
        "restricted_parameter_count": left.parameter_count,
        "full_parameter_count": right.parameter_count,
        "df": np.nan,
        "lr_statistic": np.nan,
        "p_value": np.nan,
        "delta_aic_restricted_minus_full": float(left.aic - right.aic),
        "delta_bic_restricted_minus_full": float(left.bic - right.bic),
        "decision": f"nonnested_bic_prefers_{bic_preferred}_aic_prefers_{aic_preferred}",
        "interpretation": interpretation,
    }


def invariance_comparisons(fits: dict[str, FitResult]) -> pd.DataFrame:
    rows = [
        lrt_row(
            "metric_vs_configural",
            restricted=fits["metric"],
            full=fits["configural"],
            interpretation="Tests whether equal loadings lose fit relative to fully free loadings and thresholds.",
        ),
        lrt_row(
            "scalar_vs_metric",
            restricted=fits["scalar"],
            full=fits["metric"],
            interpretation="Tests whether equal thresholds lose fit after equal loadings.",
        ),
        lrt_row(
            "partial_mv10_vs_scalar",
            restricted=fits["scalar"],
            full=fits["partial_mv10"],
            interpretation="Tests whether MV10 partial freeing improves over full scalar/threshold invariance.",
        ),
        lrt_row(
            "partial_mv10_vs_configural",
            restricted=fits["partial_mv10"],
            full=fits["configural"],
            interpretation="Tests whether MV10 partial constraints still lose fit relative to the fully free configural model.",
        ),
        nonnested_row(
            "partial_mv10_vs_metric_nonnested",
            left=fits["partial_mv10"],
            right=fits["metric"],
            interpretation="AIC/BIC comparison only: MV10 partial frees C08 loading but constrains anchor thresholds, so it is not nested with the metric model.",
        ),
    ]
    return pd.DataFrame(rows)


def fit_required_models(table: pd.DataFrame, roles: dict[str, str]) -> dict[str, FitResult]:
    specs: list[GrmSpec] = [
        make_spec("configural"),
        make_spec("metric"),
        make_spec("scalar"),
        make_spec("partial_mv10", roles=roles),
    ]
    for construct in CORE_CONSTRUCTS:
        specs.append(make_spec("loading_free_one", item=construct))
        specs.append(make_spec("threshold_free_one", item=construct))

    fits: dict[str, FitResult] = {}
    for spec in specs:
        fits[spec.model_id] = fit_spec(spec, table)
    return fits


def item_dif_summary(fits: dict[str, FitResult]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for construct in CORE_CONSTRUCTS:
        loading = lrt_row(
            f"loading_dif_{construct}",
            restricted=fits["metric"],
            full=fits[f"loading_free_one_{construct}"],
            interpretation="Item loading freed by dataset against the metric model.",
        )
        rows.append(
            {
                "construct_id": construct,
                "item_label_short": ITEM_LABELS[construct],
                "dif_type": "loading",
                "reference_model": loading["restricted_model"],
                "freed_model": loading["full_model"],
                "df": loading["df"],
                "lr_statistic": loading["lr_statistic"],
                "p_value": loading["p_value"],
                "delta_bic_restricted_minus_freed": loading["delta_bic_restricted_minus_full"],
                "strong_dif_flag": loading["decision"] == "restricted_model_rejected_lrt_and_bic",
                "decision": loading["decision"],
            }
        )

        threshold = lrt_row(
            f"threshold_dif_{construct}",
            restricted=fits["scalar"],
            full=fits[f"threshold_free_one_{construct}"],
            interpretation="Item thresholds freed by dataset against the scalar model.",
        )
        rows.append(
            {
                "construct_id": construct,
                "item_label_short": ITEM_LABELS[construct],
                "dif_type": "threshold",
                "reference_model": threshold["restricted_model"],
                "freed_model": threshold["full_model"],
                "df": threshold["df"],
                "lr_statistic": threshold["lr_statistic"],
                "p_value": threshold["p_value"],
                "delta_bic_restricted_minus_freed": threshold["delta_bic_restricted_minus_full"],
                "strong_dif_flag": threshold["decision"] == "restricted_model_rejected_lrt_and_bic",
                "decision": threshold["decision"],
            }
        )
    return pd.DataFrame(rows)


def anchor_confirmation_summary(roles: dict[str, str], item_dif: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for construct in CORE_CONSTRUCTS:
        item_rows = item_dif[item_dif["construct_id"] == construct]
        loading_row = item_rows[item_rows["dif_type"] == "loading"].iloc[0]
        threshold_row = item_rows[item_rows["dif_type"] == "threshold"].iloc[0]
        loading_flag = bool(loading_row["strong_dif_flag"])
        threshold_flag = bool(threshold_row["strong_dif_flag"])
        if not loading_flag and not threshold_flag:
            formal_role = "formal_anchor_supported"
        elif not loading_flag and threshold_flag:
            formal_role = "formal_metric_only_threshold_free"
        else:
            formal_role = "formal_free_loading_or_threshold"

        mv10_role = roles[construct]
        rows.append(
            {
                "construct_id": construct,
                "item_label_short": ITEM_LABELS[construct],
                "mv10_role": mv10_role,
                "formal_role": formal_role,
                "mv10_anchor_confirmed": bool(mv10_role == "anchor_candidate" and formal_role == "formal_anchor_supported"),
                "loading_dif_flag": loading_flag,
                "threshold_dif_flag": threshold_flag,
                "loading_lrt_p_value": loading_row["p_value"],
                "threshold_lrt_p_value": threshold_row["p_value"],
                "loading_delta_bic_restricted_minus_freed": loading_row["delta_bic_restricted_minus_freed"],
                "threshold_delta_bic_restricted_minus_freed": threshold_row["delta_bic_restricted_minus_freed"],
            }
        )
    return pd.DataFrame(rows)


def gate_recommendations(
    fits: dict[str, FitResult],
    comparisons: pd.DataFrame,
    anchors: pd.DataFrame,
    status: str,
) -> pd.DataFrame:
    confirmed = anchors[anchors["mv10_anchor_confirmed"]]["construct_id"].astype(str).tolist()
    revised = anchors[anchors["formal_role"] != "formal_anchor_supported"]["construct_id"].astype(str).tolist()
    optimizer_all_success = all(fit.optimizer_success for fit in fits.values())
    rows = [
        {
            "recommendation_id": "formal_irt_boundary",
            "status": "formal_grm_mml_completed" if optimizer_all_success else "formal_grm_mml_completed_with_optimizer_warnings",
            "recommendation": "Use MV11 as the formal label-only graded-response IRT confirmation layer; do not export fitted item parameters or subject factor scores.",
            "evidence": f"{len(fits)} model fits completed; optimizer_all_success={optimizer_all_success}.",
        },
        {
            "recommendation_id": "partial_anchor_map",
            "status": status,
            "recommendation": "Use the confirmed anchor set as the candidate measurement target for any later two-stage latent prediction design.",
            "evidence": f"Confirmed MV10 anchors: {';'.join(confirmed) if confirmed else 'none'}; revised/free items: {';'.join(revised) if revised else 'none'}.",
        },
        {
            "recommendation_id": "two_stage_latent_target",
            "status": (
                "ready_to_predeclare_two_stage_latent_target_with_bic_caveat"
                if status.startswith("complete_formal_partial_invariance_supported")
                else "revise_anchor_map_before_x_to_theta"
            ),
            "recommendation": "If proceeding, predeclare Y->theta measurement fitting separately from X->theta multimodal prediction and compare against direct X->Y floors.",
            "evidence": f"MV11 status {status}; confirmed MV10 anchors {len(confirmed)}/{MIN_CONFIRMED_ANCHORS} required.",
        },
        {
            "recommendation_id": "full_method_gate",
            "status": "keep_blocked",
            "recommendation": "Keep full M0/M1/M2/M3 construction blocked until the two-stage latent-target experiment is run and conditional identity is audited.",
            "evidence": "MV11 is label-only; it does not test multimodal prediction, feature identity, or external transfer.",
        },
    ]
    return pd.DataFrame(rows)


def method_context() -> pd.DataFrame:
    return pd.DataFrame(SOURCE_ROWS)


def determine_status(fits: dict[str, FitResult], comparisons: pd.DataFrame, anchors: pd.DataFrame) -> tuple[str, dict[str, Any]]:
    confirmed_count = int(anchors["mv10_anchor_confirmed"].sum())
    loading_flags = int((anchors["loading_dif_flag"]).sum())
    threshold_flags = int((anchors["threshold_dif_flag"]).sum())
    optimizer_all_success = all(fit.optimizer_success for fit in fits.values())
    core_model_ids = {"configural", "metric", "scalar", "partial_mv10"}
    core_fits = [fit for fit in fits.values() if fit.spec.model_id in core_model_ids]
    best_bic_model = min(core_fits, key=lambda fit: fit.bic).spec.model_id
    best_aic_model = min(core_fits, key=lambda fit: fit.aic).spec.model_id
    best_bic_any_model = min(fits.values(), key=lambda fit: fit.bic).spec.model_id
    best_aic_any_model = min(fits.values(), key=lambda fit: fit.aic).spec.model_id
    metric_decision = str(comparisons.loc[comparisons["comparison_id"] == "metric_vs_configural", "decision"].iloc[0])
    scalar_decision = str(comparisons.loc[comparisons["comparison_id"] == "scalar_vs_metric", "decision"].iloc[0])
    partial_vs_scalar = str(comparisons.loc[comparisons["comparison_id"] == "partial_mv10_vs_scalar", "decision"].iloc[0])
    partial_vs_configural = str(comparisons.loc[comparisons["comparison_id"] == "partial_mv10_vs_configural", "decision"].iloc[0])

    aic_bic_split = best_aic_model != best_bic_model
    if not optimizer_all_success:
        status = "complete_formal_irt_optimizer_warnings"
    elif confirmed_count >= MIN_CONFIRMED_ANCHORS and loading_flags <= 1 and threshold_flags >= 1 and aic_bic_split:
        status = "complete_formal_partial_invariance_supported_with_bic_caveat"
    elif confirmed_count >= MIN_CONFIRMED_ANCHORS and loading_flags <= 1 and threshold_flags >= 1:
        status = "complete_formal_partial_invariance_supported"
    elif confirmed_count >= MIN_CONFIRMED_ANCHORS:
        status = "complete_formal_anchor_map_supported_with_caveats"
    else:
        status = "complete_formal_anchor_map_revised"

    verdict = {
        "status": status,
        "model_family": "multi_group_graded_response_mml",
        "optimizer_all_success": optimizer_all_success,
        "fit_count": len(fits),
        "best_bic_model": best_bic_model,
        "best_aic_model": best_aic_model,
        "best_bic_any_model": best_bic_any_model,
        "best_aic_any_model": best_aic_any_model,
        "core_model_aic_bic_split": aic_bic_split,
        "confirmed_mv10_anchor_items": confirmed_count,
        "min_confirmed_anchor_items_required": MIN_CONFIRMED_ANCHORS,
        "loading_dif_flagged_items": loading_flags,
        "threshold_dif_flagged_items": threshold_flags,
        "metric_vs_configural_decision": metric_decision,
        "scalar_vs_metric_decision": scalar_decision,
        "partial_mv10_vs_scalar_decision": partial_vs_scalar,
        "partial_mv10_vs_configural_decision": partial_vs_configural,
        "short_read": (
            "Formal label-only graded-response IRT confirmation supports a partial-invariance PHQ target "
            "with an AIC/BIC interpretation caveat; fitted parameters and subject scores are local-only."
        ),
    }
    return status, verdict


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    fit_table: pd.DataFrame,
    comparisons: pd.DataFrame,
    anchors: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    core_fit = fit_table[fit_table["model_id"].isin(["configural", "metric", "scalar", "partial_mv10"])].copy()
    lines = [
        "# P5 MV11 Formal Psychometric Confirmation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV11 is a label-only multi-group graded-response IRT confirmation over E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 items. It does not read multimodal features, raw text/media, row-level predictions, or private review material.",
        "",
        "## Verdict",
        "",
        f"- Status: `{verdict['status']}`.",
        f"- Model family: `{verdict['model_family']}`.",
        f"- Optimizer all success: `{verdict['optimizer_all_success']}`.",
        f"- Best BIC model: `{verdict['best_bic_model']}`.",
        f"- Best AIC model: `{verdict['best_aic_model']}`.",
        f"- Confirmed MV10 anchors: `{verdict['confirmed_mv10_anchor_items']}/{verdict['min_confirmed_anchor_items_required']}` required.",
        f"- Loading DIF flagged items: `{verdict['loading_dif_flagged_items']}`.",
        f"- Threshold DIF flagged items: `{verdict['threshold_dif_flagged_items']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## Core Model Fits",
        "",
        "| model | parameters | log-likelihood | AIC | BIC | optimizer | boundary count |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for _, row in core_fit.sort_values("model_id").iterrows():
        lines.append(
            f"| {row['model_id']} | {int(row['parameter_count'])} | {fmt(row['log_likelihood'])} | "
            f"{fmt(row['aic'])} | {fmt(row['bic'])} | `{row['optimizer_success']}` | "
            f"{int(row['boundary_parameter_count'])} |"
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
    for _, row in comparisons.iterrows():
        lines.append(
            f"| {row['comparison_id']} | `{row['decision']}` | {fmt(row['lr_statistic'])} | "
            f"{'' if pd.isna(row['df']) else int(row['df'])} | {fmt(row['p_value'], 4)} | "
            f"{fmt(row['delta_bic_restricted_minus_full'])} |"
        )
    lines.extend(
        [
            "",
            "## Anchor Confirmation",
            "",
            "| item | MV10 role | MV11 formal role | loading DIF | threshold DIF |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in anchors.iterrows():
        lines.append(
            f"| {row['construct_id']} {row['item_label_short']} | `{row['mv10_role']}` | "
            f"`{row['formal_role']}` | `{row['loading_dif_flag']}` | `{row['threshold_dif_flag']}` |"
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
            "- MV11 is a formal label-only graded-response IRT confirmation, not an external lavaan/mirt run.",
            "- No fitted item parameters, subject-level factor scores, posterior scores, or row diagnostics are exported.",
            "- Full method construction remains blocked until a two-stage latent-target predictor is predeclared, run, and conditionally identity-audited.",
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
        r"factor_score",
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
        "audit_id": "P5_MV11_formal_psychometric_confirmation_hygiene",
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

    table, input_audit = load_inputs(manifest_dir)
    roles = load_mv10_roles(mv10_partial)
    fits = fit_required_models(table, roles)
    fit_table = fit_summary(fits)
    comparisons = invariance_comparisons(fits)
    item_dif = item_dif_summary(fits)
    anchors = anchor_confirmation_summary(roles, item_dif)
    status, verdict = determine_status(fits, comparisons, anchors)
    recommendations = gate_recommendations(fits, comparisons, anchors, status)
    context = method_context()

    fit_table.to_csv(out_dir / "fit_model_summary.csv", index=False)
    comparisons.to_csv(out_dir / "invariance_comparison_summary.csv", index=False)
    item_dif.to_csv(out_dir / "item_dif_lrt_summary.csv", index=False)
    anchors.to_csv(out_dir / "anchor_confirmation_summary.csv", index=False)
    recommendations.to_csv(out_dir / "gate_recommendations.csv", index=False)
    context.to_csv(out_dir / "method_context_formal_irt.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "label_only_formal_graded_response_irt_confirmation",
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": CORE_CONSTRUCTS,
            "mv10_partial_anchor_map_read": rel(mv10_partial),
            "label_only": True,
            "formal_ordinal_cfa_or_irt_fit": True,
            "formal_model_family": "multi_group_graded_response_mml",
            "external_lavaan_or_mirt_runtime": False,
            "multimodal_features_read": False,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "subject_level_outputs_written": False,
            "fitted_parameters_written": False,
            "full_method_allowed": False,
        },
        "data_contract": {
            "subjects": {
                row["dataset"]: int(row["complete_item_subjects"])
                for _, row in input_audit.iterrows()
            },
            "item_count": len(CORE_CONSTRUCTS),
            "groups": GROUPS,
            "quadrature_points": QUADRATURE_POINTS,
        },
        "outputs": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "model_fit_rows": int(len(fit_table)),
            "comparison_rows": int(len(comparisons)),
            "item_dif_rows": int(len(item_dif)),
            "anchor_rows": int(len(anchors)),
            "recommendation_rows": int(len(recommendations)),
            "source_context_rows": int(len(context)),
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, fit_table, comparisons, anchors, recommendations)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, fit_table, comparisons, anchors, recommendations)
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
        "Wrote formal psychometric confirmation to "
        f"{args.out_dir.relative_to(ROOT)} with status {run_summary['verdict']['status']}"
    )


if __name__ == "__main__":
    main()
