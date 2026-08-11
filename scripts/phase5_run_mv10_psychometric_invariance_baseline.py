#!/usr/bin/env python3
"""Run P5_MV10 label-only psychometric invariance baseline.

This script is a measurement-layer diagnostic, not a multimodal model. It uses
only manifest-governed PHQ item labels from E-DAIC PHQ-8 and CMDC PHQ-9,
then reports approximate configural, metric, threshold/scalar, partial
invariance, and empirical score-linking diagnostics. It does not read raw
text/media, feature caches, row-level predictions, or write subject-level
factor scores/fitted parameters.

The current environment does not provide lavaan/mirt/semopy, so this is an
auditable label-only invariance screen rather than a formal multi-group ordinal
CFA or graded-response IRT fit.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
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
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv10_psychometric_invariance_baseline"

RUN_ID = "P5_MV10_psychometric_invariance_baseline"
CORE_CONSTRUCTS = [f"C{idx:02d}" for idx in range(1, 9)]
THRESHOLDS = [1, 2, 3]
BOOTSTRAP_RESAMPLES = 500
RANDOM_SEED = 20260811

METRIC_LOADING_DELTA_TOL = 0.20
THRESHOLD_LOCATION_DELTA_TOL = 0.35
MIN_ANCHOR_ITEMS_FOR_PARTIAL = 4

EDAIC_ITEM_MAP = {
    "C01": "PHQ_8Depressed",
    "C02": "PHQ_8NoInterest",
    "C03": "PHQ_8Sleep",
    "C04": "PHQ_8Tired",
    "C05": "PHQ_8Appetite",
    "C06": "PHQ_8Failure",
    "C07": "PHQ_8Concentrating",
    "C08": "PHQ_8Moving",
}

CMDC_ITEM_MAP = {
    "C01": "PHQ-2",
    "C02": "PHQ-1",
    "C03": "PHQ-3",
    "C04": "PHQ-4",
    "C05": "PHQ-5",
    "C06": "PHQ-6",
    "C07": "PHQ-7",
    "C08": "PHQ-8",
}

ITEM_LABELS = {
    "C01": "depressed_mood",
    "C02": "anhedonia",
    "C03": "sleep",
    "C04": "fatigue",
    "C05": "appetite",
    "C06": "self_worth",
    "C07": "concentration",
    "C08": "psychomotor",
}

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "bootstrap_reliability_summary.csv",
    "empirical_score_linking_summary.csv",
    "gate_recommendations.csv",
    "item_distribution_summary.csv",
    "loading_invariance_summary.csv",
    "partial_invariance_summary.csv",
    "psychometric_input_audit.csv",
    "reliability_dimensionality_summary.csv",
    "report.md",
    "run_summary.json",
    "source_context_psychometric_baseline.csv",
    "stage_summary.csv",
    "threshold_dif_summary.csv",
}

SOURCE_ROWS = [
    {
        "source_id": "phq9_invariance_helius_2017",
        "topic": "classical PHQ measurement invariance",
        "citation_hint": "Galenkamp et al. 2017, BMC Psychiatry",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "use_in_mv10": "Motivates configural, metric, scalar/threshold, and partial-invariance checks before cross-group PHQ comparisons.",
    },
    {
        "source_id": "phq9_measurement_invariance_us_2019",
        "topic": "PHQ-9 sociodemographic invariance",
        "citation_hint": "Patel et al. 2019, Depression and Anxiety",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/",
        "use_in_mv10": "Positions PHQ-9 invariance testing as a prerequisite for meaningful group comparisons.",
    },
    {
        "source_id": "phq_hamd_irt_2021",
        "topic": "PHQ/HAMD scale measurement differences",
        "citation_hint": "Ma et al. 2021, Frontiers in Psychiatry",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "use_in_mv10": "Supports separating scale measurement from multimodal prediction because PHQ and HAMD can differ psychometrically.",
    },
    {
        "source_id": "scale_linking_jclinepi_2026",
        "topic": "cross-scale linking",
        "citation_hint": "Zhou et al. 2026, Journal of Clinical Epidemiology",
        "url": "https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",
        "use_in_mv10": "Motivates reporting empirical score-linking as a measurement diagnostic rather than assuming correlated scales are interchangeable.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def read_json_dict(value: Any) -> dict[str, Any]:
    text = clean_value(value)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def load_phq_dataset(manifest_dir: Path, dataset: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    if dataset == "edaic":
        manifest_name = "edaic_subjects.csv"
        item_col = "phq8_items"
        total_col = "phq8_total"
        full_total_col = "phq8_total"
        item_map = EDAIC_ITEM_MAP
        scale = "PHQ-8"
        usecols = ["subject_id", "file_valid", "official_split", item_col, total_col]
    elif dataset == "cmdc":
        manifest_name = "cmdc_subjects.csv"
        item_col = "phq9_items"
        total_col = "phq9_total"
        full_total_col = "phq9_total"
        item_map = CMDC_ITEM_MAP
        scale = "PHQ-9"
        usecols = ["subject_id", "file_valid", item_col, total_col]
    else:
        raise ValueError(dataset)

    manifest = pd.read_csv(manifest_dir / manifest_name, usecols=usecols)
    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    raw_valid_subjects = int(manifest["subject_id"].astype(str).nunique())
    if dataset == "edaic":
        manifest = manifest[manifest["official_split"].astype(str).isin(["train", "dev"])].copy()
    eligible_subjects = int(manifest["subject_id"].astype(str).nunique())

    rows: list[dict[str, Any]] = []
    missing_payload_subjects = 0
    incomplete_item_subjects = 0
    for subject, group in manifest.groupby("subject_id", sort=False):
        first = group.iloc[0]
        payload = read_json_dict(first[item_col])
        if not payload:
            missing_payload_subjects += 1
            continue
        record: dict[str, Any] = {
            "dataset": dataset,
            "scale": scale,
            "subject_id": str(subject),
            "core_total": 0.0,
            "full_total": safe_float(first[full_total_col]),
        }
        complete = True
        for construct, key in item_map.items():
            value = safe_float(payload.get(key))
            if value is None:
                complete = False
                break
            value = float(np.clip(value, 0.0, 3.0))
            record[construct] = value
            record["core_total"] += value
        if not complete or record["full_total"] is None:
            incomplete_item_subjects += 1
            continue
        rows.append(record)

    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError(f"no complete PHQ item rows for {dataset}")
    table = table.sort_values("subject_id", key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)
    audit = {
        "dataset": dataset,
        "scale": scale,
        "raw_valid_subjects": raw_valid_subjects,
        "eligible_subjects": eligible_subjects,
        "complete_item_subjects": int(len(table)),
        "item_count": len(CORE_CONSTRUCTS),
        "missing_payload_subjects": int(missing_payload_subjects),
        "incomplete_item_subjects": int(incomplete_item_subjects),
        "total_score_field": full_total_col,
        "item_payload_field": item_col,
        "official_split_filter": "train;dev" if dataset == "edaic" else "all_valid",
    }
    return table, audit


def load_inputs(manifest_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    audit_rows: list[dict[str, Any]] = []
    for dataset in ["edaic", "cmdc"]:
        frame, audit = load_phq_dataset(manifest_dir, dataset)
        frames.append(frame)
        audit_rows.append(audit)
    table = pd.concat(frames, ignore_index=True)
    return table, pd.DataFrame(audit_rows)


def cronbach_alpha(x: np.ndarray) -> float:
    values = np.asarray(x, dtype=float)
    k = values.shape[1]
    if k < 2:
        return float("nan")
    item_variance = values.var(axis=0, ddof=1).sum()
    total_variance = values.sum(axis=1).var(ddof=1)
    if total_variance <= 0:
        return float("nan")
    return float(k / (k - 1) * (1 - item_variance / total_variance))


def correlation_matrix(x: np.ndarray) -> np.ndarray:
    values = np.asarray(x, dtype=float)
    corr = np.corrcoef(values, rowvar=False)
    corr = np.nan_to_num(corr, nan=0.0)
    np.fill_diagonal(corr, 1.0)
    return corr


def pca_loadings(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    corr = correlation_matrix(x)
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    first_vector = eigenvectors[:, order[0]]
    loadings = first_vector * math.sqrt(max(float(eigenvalues[0]), 0.0))
    if np.nanmean(loadings) < 0:
        loadings = -loadings
    return eigenvalues, loadings


def tucker_congruence(a: np.ndarray, b: np.ndarray) -> float:
    left = np.asarray(a, dtype=float)
    right = np.asarray(b, dtype=float)
    denom = math.sqrt(float(np.sum(left**2) * np.sum(right**2)))
    if denom <= 0:
        return float("nan")
    return float(np.sum(left * right) / denom)


def item_distribution_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=False):
        for construct in CORE_CONSTRUCTS:
            values = group[construct].to_numpy(dtype=float)
            counts = {category: int(np.sum(values == category)) for category in [0.0, 1.0, 2.0, 3.0]}
            rows.append(
                {
                    "dataset": dataset,
                    "scale": str(group["scale"].iloc[0]),
                    "construct_id": construct,
                    "item_label_short": ITEM_LABELS[construct],
                    "subjects": int(len(values)),
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values, ddof=1)),
                    "category_0": counts[0.0],
                    "category_1": counts[1.0],
                    "category_2": counts[2.0],
                    "category_3": counts[3.0],
                    "floor_rate": float(counts[0.0] / len(values)),
                    "ceiling_rate": float(counts[3.0] / len(values)),
                }
            )
    return pd.DataFrame(rows)


def reliability_dimensionality_summary(table: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    rows: list[dict[str, Any]] = []
    loadings: dict[str, np.ndarray] = {}
    for dataset, group in table.groupby("dataset", sort=False):
        x = group[CORE_CONSTRUCTS].to_numpy(dtype=float)
        eigenvalues, dataset_loadings = pca_loadings(x)
        loadings[dataset] = dataset_loadings
        first_to_second = float(eigenvalues[0] / eigenvalues[1]) if eigenvalues.size > 1 and eigenvalues[1] > 0 else float("nan")
        alpha = cronbach_alpha(x)
        configural_status = (
            "configural_screen_pass"
            if alpha >= 0.70 and first_to_second >= 2.0 and float(np.min(dataset_loadings)) >= 0.25
            else "configural_screen_flag"
        )
        rows.append(
            {
                "dataset": dataset,
                "scale": str(group["scale"].iloc[0]),
                "subjects": int(len(group)),
                "item_count": len(CORE_CONSTRUCTS),
                "cronbach_alpha": alpha,
                "first_eigenvalue": float(eigenvalues[0]),
                "second_eigenvalue": float(eigenvalues[1]) if eigenvalues.size > 1 else np.nan,
                "first_to_second_eigen_ratio": first_to_second,
                "first_factor_variance_share": float(eigenvalues[0] / len(CORE_CONSTRUCTS)),
                "min_first_factor_loading": float(np.min(dataset_loadings)),
                "max_first_factor_loading": float(np.max(dataset_loadings)),
                "configural_screen_status": configural_status,
            }
        )
    return pd.DataFrame(rows), loadings


def bootstrap_reliability_summary(table: pd.DataFrame, resamples: int = BOOTSTRAP_RESAMPLES) -> pd.DataFrame:
    rng = np.random.default_rng(RANDOM_SEED)
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=False):
        x = group[CORE_CONSTRUCTS].to_numpy(dtype=float)
        alpha_values: list[float] = []
        first_eigen_values: list[float] = []
        min_loading_values: list[float] = []
        for _ in range(resamples):
            idx = rng.integers(0, x.shape[0], size=x.shape[0])
            sample = x[idx]
            alpha_values.append(cronbach_alpha(sample))
            eigenvalues, loadings = pca_loadings(sample)
            first_eigen_values.append(float(eigenvalues[0]))
            min_loading_values.append(float(np.min(loadings)))
        for metric, values in [
            ("cronbach_alpha", alpha_values),
            ("first_eigenvalue", first_eigen_values),
            ("min_first_factor_loading", min_loading_values),
        ]:
            arr = np.asarray(values, dtype=float)
            arr = arr[np.isfinite(arr)]
            rows.append(
                {
                    "dataset": dataset,
                    "metric": metric,
                    "resamples": int(len(arr)),
                    "mean": float(np.mean(arr)),
                    "p025": float(np.quantile(arr, 0.025)),
                    "p500": float(np.quantile(arr, 0.500)),
                    "p975": float(np.quantile(arr, 0.975)),
                }
            )
    return pd.DataFrame(rows)


def loading_invariance_summary(loadings: dict[str, np.ndarray]) -> pd.DataFrame:
    edaic = loadings["edaic"]
    cmdc = loadings["cmdc"]
    rows: list[dict[str, Any]] = []
    for idx, construct in enumerate(CORE_CONSTRUCTS):
        delta = abs(float(edaic[idx] - cmdc[idx]))
        rows.append(
            {
                "construct_id": construct,
                "item_label_short": ITEM_LABELS[construct],
                "edaic_loading": float(edaic[idx]),
                "cmdc_loading": float(cmdc[idx]),
                "abs_loading_delta": delta,
                "metric_screen_status": "metric_anchor_candidate" if delta <= METRIC_LOADING_DELTA_TOL else "metric_dif_flag",
            }
        )
    return pd.DataFrame(rows)


def fit_binary_logit(x: np.ndarray, y: np.ndarray) -> dict[str, Any] | None:
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=int)
    if y_arr.size < 12 or len(np.unique(y_arr)) < 2:
        return None
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x_arr)
    try:
        model = LogisticRegression(C=1_000_000.0, solver="lbfgs", max_iter=2000)
        model.fit(x_scaled, y_arr)
        kind = "large_c_logistic"
    except Exception:
        model = LogisticRegression(C=1000.0, solver="lbfgs", max_iter=2000)
        model.fit(x_scaled, y_arr)
        kind = "weakly_penalized_logistic_fallback"
    probability = model.predict_proba(x_scaled)[:, 1]
    return {
        "kind": kind,
        "model": model,
        "scaler": scaler,
        "coef": np.asarray(model.coef_, dtype=float).reshape(-1),
        "intercept": float(model.intercept_[0]),
        "probability": probability,
        "log_loss": float(log_loss(y_arr, np.clip(probability, 1e-7, 1 - 1e-7), labels=[0, 1])),
        "auc": float(roc_auc_score(y_arr, probability)) if len(np.unique(y_arr)) == 2 else np.nan,
    }


def threshold_location(model: dict[str, Any] | None) -> float | None:
    if model is None:
        return None
    beta_scaled = safe_float(model["coef"][0])
    if beta_scaled is None or abs(beta_scaled) < 1e-8:
        return None
    scaler: StandardScaler = model["scaler"]
    mean = float(scaler.mean_[0])
    scale = float(scaler.scale_[0]) if float(scaler.scale_[0]) != 0 else 1.0
    intercept = float(model["intercept"])
    location_scaled = -intercept / beta_scaled
    return float(location_scaled * scale + mean)


def threshold_dif_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for construct in CORE_CONSTRUCTS:
        data = table[["dataset", *CORE_CONSTRUCTS]].copy()
        data["other_total_norm"] = (data[CORE_CONSTRUCTS].sum(axis=1) - data[construct]) / (3.0 * (len(CORE_CONSTRUCTS) - 1))
        pooled_mean = float(data["other_total_norm"].mean())
        pooled_std = float(data["other_total_norm"].std(ddof=0)) or 1.0
        data["theta_z"] = (data["other_total_norm"] - pooled_mean) / pooled_std
        data["dataset_indicator"] = (data["dataset"] == "cmdc").astype(float)
        data["theta_dataset_interaction"] = data["theta_z"] * data["dataset_indicator"]
        for threshold in THRESHOLDS:
            y = (data[construct].to_numpy(dtype=float) >= float(threshold)).astype(int)
            base = fit_binary_logit(data[["theta_z"]].to_numpy(dtype=float), y)
            threshold_dif = fit_binary_logit(data[["theta_z", "dataset_indicator"]].to_numpy(dtype=float), y)
            loading_dif = fit_binary_logit(
                data[["theta_z", "dataset_indicator", "theta_dataset_interaction"]].to_numpy(dtype=float),
                y,
            )

            dataset_locations: dict[str, float | None] = {}
            dataset_auc: dict[str, float | None] = {}
            for dataset, group in data.groupby("dataset", sort=False):
                group_y = (group[construct].to_numpy(dtype=float) >= float(threshold)).astype(int)
                model = fit_binary_logit(group[["theta_z"]].to_numpy(dtype=float), group_y)
                dataset_locations[dataset] = threshold_location(model)
                dataset_auc[dataset] = safe_float(model["auc"]) if model is not None else None

            location_delta = None
            if dataset_locations.get("edaic") is not None and dataset_locations.get("cmdc") is not None:
                location_delta = abs(float(dataset_locations["edaic"]) - float(dataset_locations["cmdc"]))

            dataset_coef = safe_float(threshold_dif["coef"][1]) if threshold_dif is not None and len(threshold_dif["coef"]) > 1 else None
            interaction_coef = safe_float(loading_dif["coef"][2]) if loading_dif is not None and len(loading_dif["coef"]) > 2 else None
            base_loss = safe_float(base["log_loss"]) if base is not None else None
            threshold_loss = safe_float(threshold_dif["log_loss"]) if threshold_dif is not None else None
            loading_loss = safe_float(loading_dif["log_loss"]) if loading_dif is not None else None
            threshold_gain = (
                float(base_loss - threshold_loss)
                if base_loss is not None and threshold_loss is not None
                else None
            )
            loading_gain = (
                float(threshold_loss - loading_loss)
                if threshold_loss is not None and loading_loss is not None
                else None
            )

            if location_delta is None:
                status = "threshold_location_unavailable"
            elif location_delta <= THRESHOLD_LOCATION_DELTA_TOL:
                status = "threshold_anchor_candidate"
            else:
                status = "threshold_dif_flag"

            rows.append(
                {
                    "construct_id": construct,
                    "item_label_short": ITEM_LABELS[construct],
                    "threshold": int(threshold),
                    "positive_rate_edaic": float(np.mean(data.loc[data["dataset"] == "edaic", construct] >= threshold)),
                    "positive_rate_cmdc": float(np.mean(data.loc[data["dataset"] == "cmdc", construct] >= threshold)),
                    "edaic_threshold_location_theta_z": dataset_locations.get("edaic"),
                    "cmdc_threshold_location_theta_z": dataset_locations.get("cmdc"),
                    "abs_threshold_location_delta": location_delta,
                    "dataset_logit_coef": dataset_coef,
                    "theta_dataset_interaction_coef": interaction_coef,
                    "base_log_loss": base_loss,
                    "threshold_dif_log_loss_gain": threshold_gain,
                    "loading_dif_log_loss_gain": loading_gain,
                    "edaic_auc": dataset_auc.get("edaic"),
                    "cmdc_auc": dataset_auc.get("cmdc"),
                    "threshold_screen_status": status,
                }
            )
    return pd.DataFrame(rows)


def partial_invariance_summary(loading: pd.DataFrame, threshold: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, load_row in loading.iterrows():
        construct = str(load_row["construct_id"])
        threshold_rows = threshold[threshold["construct_id"] == construct]
        valid_thresholds = threshold_rows["abs_threshold_location_delta"].dropna().astype(float)
        max_threshold_delta = float(valid_thresholds.max()) if not valid_thresholds.empty else np.nan
        mean_threshold_delta = float(valid_thresholds.mean()) if not valid_thresholds.empty else np.nan
        metric_invariant = float(load_row["abs_loading_delta"]) <= METRIC_LOADING_DELTA_TOL
        threshold_invariant = bool(np.isfinite(max_threshold_delta) and max_threshold_delta <= THRESHOLD_LOCATION_DELTA_TOL)
        if metric_invariant and threshold_invariant:
            role = "anchor_candidate"
        elif metric_invariant:
            role = "metric_only_threshold_free"
        else:
            role = "free_loading_or_threshold"
        rows.append(
            {
                "construct_id": construct,
                "item_label_short": load_row["item_label_short"],
                "abs_loading_delta": float(load_row["abs_loading_delta"]),
                "max_abs_threshold_location_delta": max_threshold_delta,
                "mean_abs_threshold_location_delta": mean_threshold_delta,
                "metric_invariant_screen": metric_invariant,
                "threshold_invariant_screen": threshold_invariant,
                "partial_invariance_role": role,
            }
        )
    return pd.DataFrame(rows)


def empirical_score_linking_summary(table: pd.DataFrame) -> pd.DataFrame:
    edaic = table[table["dataset"] == "edaic"].copy()
    cmdc = table[table["dataset"] == "cmdc"].copy()
    edaic_core = edaic["core_total"].to_numpy(dtype=float)
    cmdc_core = cmdc["core_total"].to_numpy(dtype=float)
    cmdc_full = cmdc["full_total"].to_numpy(dtype=float)
    rows: list[dict[str, Any]] = []
    for score in range(0, 25):
        percentile = float(np.mean(edaic_core <= score))
        percentile = min(max(percentile, 0.0), 1.0)
        rows.append(
            {
                "edaic_phq8_core_score": int(score),
                "edaic_empirical_percentile": percentile,
                "cmdc_core_score_at_same_percentile": float(np.quantile(cmdc_core, percentile, method="linear")),
                "cmdc_phq9_total_at_same_percentile": float(np.quantile(cmdc_full, percentile, method="linear")),
                "interpretation": "empirical_distribution_link_not_clinical_conversion",
            }
        )
    return pd.DataFrame(rows)


def score_distribution_stage_rows(table: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=False):
        rows.append(
            {
                "stage": f"{dataset}_score_distribution",
                "status": "complete",
                "evidence": (
                    f"n={len(group)}, core total mean={fmt(group['core_total'].mean())}, "
                    f"median={fmt(group['core_total'].median())}, full total mean={fmt(group['full_total'].mean())}."
                ),
                "claim_boundary": "Distribution differences are population/protocol confounded and are not clinical scale conversions.",
            }
        )
    return rows


def build_stage_summary(
    table: pd.DataFrame,
    reliability: pd.DataFrame,
    loadings: dict[str, np.ndarray],
    loading: pd.DataFrame,
    threshold: pd.DataFrame,
    partial: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    congruence = tucker_congruence(loadings["edaic"], loadings["cmdc"])
    configural_pass = bool(
        (reliability["configural_screen_status"] == "configural_screen_pass").all()
        and math.isfinite(congruence)
        and congruence >= 0.95
    )
    metric_items = int(partial["metric_invariant_screen"].sum())
    threshold_items = int(partial["threshold_invariant_screen"].sum())
    anchor_items = int((partial["partial_invariance_role"] == "anchor_candidate").sum())
    mean_loading_delta = float(loading["abs_loading_delta"].mean())
    max_loading_delta = float(loading["abs_loading_delta"].max())
    mean_threshold_delta = float(threshold["abs_threshold_location_delta"].dropna().mean())
    max_threshold_delta = float(threshold["abs_threshold_location_delta"].dropna().max())
    metric_status = (
        "metric_screen_pass"
        if metric_items >= 6 and mean_loading_delta <= 0.15 and max_loading_delta <= 0.25
        else "metric_screen_partial_or_flagged"
    )
    threshold_status = (
        "threshold_screen_pass"
        if threshold_items >= 6 and mean_threshold_delta <= 0.25 and max_threshold_delta <= 0.45
        else "threshold_screen_partial_or_flagged"
    )
    partial_status = (
        "partial_invariance_screen_pass"
        if configural_pass and anchor_items >= MIN_ANCHOR_ITEMS_FOR_PARTIAL
        else "partial_invariance_screen_flag"
    )

    if configural_pass and metric_status == "metric_screen_pass" and threshold_status == "threshold_screen_pass":
        overall_status = "complete_label_invariance_supported_approx"
    elif configural_pass and partial_status == "partial_invariance_screen_pass":
        overall_status = "complete_partial_invariance_supported_approx"
    else:
        overall_status = "complete_measurement_shift_detected_approx"

    rows = [
        {
            "stage": "configural_screen",
            "status": "pass" if configural_pass else "flag",
            "evidence": f"Both datasets pass one-factor screen; loading congruence={fmt(congruence)}.",
            "claim_boundary": "Approximate configural support only; not formal multi-group ordinal CFA.",
        },
        {
            "stage": "metric_loading_screen",
            "status": metric_status,
            "evidence": (
                f"{metric_items}/8 items within loading delta tolerance {METRIC_LOADING_DELTA_TOL}; "
                f"mean delta={fmt(mean_loading_delta)}, max delta={fmt(max_loading_delta)}."
            ),
            "claim_boundary": "Metric evidence is based on one-factor loading congruence, not formal equality constraints.",
        },
        {
            "stage": "threshold_scalar_screen",
            "status": threshold_status,
            "evidence": (
                f"{threshold_items}/8 items within threshold-location tolerance {THRESHOLD_LOCATION_DELTA_TOL}; "
                f"mean threshold delta={fmt(mean_threshold_delta)}, max={fmt(max_threshold_delta)}."
            ),
            "claim_boundary": "Threshold/scalar evidence is an ordinal logistic DIF screen using leave-one-item-out severity.",
        },
        {
            "stage": "partial_invariance_screen",
            "status": partial_status,
            "evidence": f"{anchor_items}/8 items are anchor candidates with both metric and threshold support.",
            "claim_boundary": "Use only as a candidate anchor map for a future formal measurement model.",
        },
        {
            "stage": "next_model_target",
            "status": "plan_two_stage_latent_target" if partial_status == "partial_invariance_screen_pass" else "formal_psychometric_followup_needed",
            "evidence": f"Overall MV10 status is {overall_status}.",
            "claim_boundary": "Do not start a full multimodal method from this screen alone.",
        },
        *score_distribution_stage_rows(table),
    ]
    verdict = {
        "status": overall_status,
        "configural_screen_pass": configural_pass,
        "metric_status": metric_status,
        "threshold_status": threshold_status,
        "partial_invariance_status": partial_status,
        "loading_congruence": congruence,
        "metric_invariant_items": metric_items,
        "threshold_invariant_items": threshold_items,
        "anchor_candidate_items": anchor_items,
        "mean_abs_loading_delta": mean_loading_delta,
        "max_abs_loading_delta": max_loading_delta,
        "mean_abs_threshold_delta": mean_threshold_delta,
        "max_abs_threshold_delta": max_threshold_delta,
        "short_read": (
            "Label-only PHQ screen supports a common one-factor structure and partial anchors, "
            "but threshold/scalar invariance remains approximate and must be treated as measurement-shift evidence."
        ),
    }
    return pd.DataFrame(rows), verdict


def gate_recommendations(verdict: dict[str, Any], partial: pd.DataFrame) -> pd.DataFrame:
    anchor_items = partial[partial["partial_invariance_role"] == "anchor_candidate"]["construct_id"].tolist()
    free_items = partial[partial["partial_invariance_role"] != "anchor_candidate"]["construct_id"].tolist()
    rows = [
        {
            "recommendation_id": "formal_cfa_boundary",
            "status": "formal_ordinal_cfa_not_run",
            "recommendation": "Treat MV10 as a reproducible label-only invariance screen; run lavaan/mirt/semopy or equivalent before making a formal psychometric invariance claim.",
            "evidence": "The current runtime has no R/lavaan, mirt, semopy, factor_analyzer, or statsmodels dependency.",
        },
        {
            "recommendation_id": "partial_anchor_map",
            "status": verdict["partial_invariance_status"],
            "recommendation": "Use anchor candidates only as a starting map for two-stage latent-target design.",
            "evidence": f"Anchor candidates: {';'.join(anchor_items) if anchor_items else 'none'}; DIF/free candidates: {';'.join(free_items) if free_items else 'none'}.",
        },
        {
            "recommendation_id": "two_stage_latent_target",
            "status": "plan_if_formal_fit_confirms",
            "recommendation": "Separate Y->theta measurement fitting from X->theta multimodal prediction, then map theta back to dataset-specific observed items.",
            "evidence": f"MV10 status {verdict['status']}; metric items {verdict['metric_invariant_items']}/8; threshold items {verdict['threshold_invariant_items']}/8.",
        },
        {
            "recommendation_id": "full_method_gate",
            "status": "keep_blocked",
            "recommendation": "Keep full M0/M1/M2/M3 method construction blocked until formal measurement and conditional identity gates are both satisfied.",
            "evidence": "MV10 is label-only and approximate; it does not address multimodal feature identity or external transfer by itself.",
        },
    ]
    return pd.DataFrame(rows)


def source_context() -> pd.DataFrame:
    return pd.DataFrame(SOURCE_ROWS)


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    reliability: pd.DataFrame,
    loading: pd.DataFrame,
    partial: pd.DataFrame,
    stage: pd.DataFrame,
) -> None:
    verdict = run_summary["verdict"]
    anchor_rows = partial[partial["partial_invariance_role"] == "anchor_candidate"]
    lines = [
        "# P5 MV10 Psychometric Invariance Baseline",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV10 is a label-only PHQ-8/PHQ-9 measurement screen. It does not read multimodal features, raw text/media, row-level predictions, or private review material.",
        "",
        "## Verdict",
        "",
        f"- Status: `{verdict['status']}`.",
        f"- Configural screen pass: `{verdict['configural_screen_pass']}`.",
        f"- Loading congruence: `{fmt(verdict['loading_congruence'])}`.",
        f"- Metric invariant items: `{verdict['metric_invariant_items']}/8`.",
        f"- Threshold invariant items: `{verdict['threshold_invariant_items']}/8`.",
        f"- Anchor candidate items: `{verdict['anchor_candidate_items']}/8`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        "## Reliability and Dimensionality",
        "",
        "| dataset | alpha | eig1/eig2 | min loading | status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for _, row in reliability.iterrows():
        lines.append(
            f"| {row['dataset']} | {fmt(row['cronbach_alpha'])} | "
            f"{fmt(row['first_to_second_eigen_ratio'])} | {fmt(row['min_first_factor_loading'])} | "
            f"`{row['configural_screen_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Loading Invariance",
            "",
            "| item | label | E-DAIC loading | CMDC loading | delta | status |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in loading.iterrows():
        lines.append(
            f"| {row['construct_id']} | {row['item_label_short']} | {fmt(row['edaic_loading'])} | "
            f"{fmt(row['cmdc_loading'])} | {fmt(row['abs_loading_delta'])} | `{row['metric_screen_status']}` |"
        )
    lines.extend(
        [
            "",
            "## Partial Anchor Candidates",
            "",
            "| item | role | max threshold delta |",
            "| --- | --- | ---: |",
        ]
    )
    for _, row in partial.iterrows():
        lines.append(
            f"| {row['construct_id']} {row['item_label_short']} | `{row['partial_invariance_role']}` | "
            f"{fmt(row['max_abs_threshold_location_delta'])} |"
        )
    lines.extend(
        [
            "",
            "## Stage Summary",
            "",
            "| stage | status | evidence |",
            "| --- | --- | --- |",
        ]
    )
    for _, row in stage.iterrows():
        lines.append(f"| {row['stage']} | `{row['status']}` | {md_escape(row['evidence'])} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This is not a formal multi-group ordinal CFA/IRT result.",
            "- Use the anchor set as a candidate measurement map only after formal psychometric confirmation.",
            "- Keep subject-level factor scores, fitted parameters, row diagnostics, and bootstraps local-only.",
        ]
    )
    if not anchor_rows.empty:
        anchors = ";".join(anchor_rows["construct_id"].astype(str).tolist())
        lines.append(f"- Current candidate anchors: `{anchors}`.")
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
        "audit_id": "P5_MV10_psychometric_invariance_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def build_outputs(out_dir: Path, manifest_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    table, input_audit = load_inputs(manifest_dir)
    distributions = item_distribution_summary(table)
    reliability, loadings = reliability_dimensionality_summary(table)
    bootstrap = bootstrap_reliability_summary(table)
    loading = loading_invariance_summary(loadings)
    threshold = threshold_dif_summary(table)
    partial = partial_invariance_summary(loading, threshold)
    stage, verdict = build_stage_summary(table, reliability, loadings, loading, threshold, partial)
    linking = empirical_score_linking_summary(table)
    recommendations = gate_recommendations(verdict, partial)
    sources = source_context()

    input_audit.to_csv(out_dir / "psychometric_input_audit.csv", index=False)
    distributions.to_csv(out_dir / "item_distribution_summary.csv", index=False)
    reliability.to_csv(out_dir / "reliability_dimensionality_summary.csv", index=False)
    bootstrap.to_csv(out_dir / "bootstrap_reliability_summary.csv", index=False)
    loading.to_csv(out_dir / "loading_invariance_summary.csv", index=False)
    threshold.to_csv(out_dir / "threshold_dif_summary.csv", index=False)
    partial.to_csv(out_dir / "partial_invariance_summary.csv", index=False)
    stage.to_csv(out_dir / "stage_summary.csv", index=False)
    linking.to_csv(out_dir / "empirical_score_linking_summary.csv", index=False)
    recommendations.to_csv(out_dir / "gate_recommendations.csv", index=False)
    sources.to_csv(out_dir / "source_context_psychometric_baseline.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "label_only_psychometric_invariance_screen",
        "input_contract": {
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": CORE_CONSTRUCTS,
            "label_only": True,
            "formal_ordinal_cfa_or_irt_fit": False,
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
            "thresholds_per_item": len(THRESHOLDS),
        },
        "outputs": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "input_audit_rows": int(len(input_audit)),
            "item_distribution_rows": int(len(distributions)),
            "reliability_rows": int(len(reliability)),
            "bootstrap_rows": int(len(bootstrap)),
            "loading_rows": int(len(loading)),
            "threshold_rows": int(len(threshold)),
            "partial_rows": int(len(partial)),
            "score_linking_rows": int(len(linking)),
            "stage_rows": int(len(stage)),
            "source_context_rows": int(len(sources)),
        },
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, reliability, loading, partial, stage)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, reliability, loading, partial, stage)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    run_summary = build_outputs(args.out_dir, args.manifest_dir)
    print(
        "Wrote psychometric invariance baseline to "
        f"{args.out_dir.relative_to(ROOT)} with status {run_summary['verdict']['status']}"
    )


if __name__ == "__main__":
    main()
