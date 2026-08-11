#!/usr/bin/env python3
"""Run P5_MV09 conditional dataset-identity audit.

This diagnostic addresses a gate-definition risk raised after MV08b: high
unconditional dataset identifiability can be confounded by real label-scale,
severity, population, or protocol differences. MV09 therefore estimates
dataset identifiability before and after conditioning on available target and
covariate information. It is an audit of the identity gate, not a deployable
model and not a full-method authorization.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
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
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase5_run_mv07_aligned_bge_shared_symptom as mv07


ROOT = mv07.ROOT
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv09_conditional_identity_audit"
DEFAULT_MANIFEST_DIR = mv07.DEFAULT_MANIFEST_DIR
DEFAULT_PHASE2_ROOT = mv07.DEFAULT_PHASE2_ROOT

RUN_ID = "P5_MV09_conditional_dataset_identity_audit"
SEEDS = mv07.SEEDS
CONSTRUCTS = mv07.CONSTRUCTS
SEVERITY_BINS = [-1e-9, 0.2, 0.4, 0.6, 0.8, 1.000000001]
SEVERITY_LABELS = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]

TRACKED_FILES = {
    "accuracy_invariance_pareto_summary.csv",
    "artifact_hygiene_audit.json",
    "condition_balance_summary.csv",
    "conditional_identity_by_seed.csv",
    "conditional_identity_summary.csv",
    "conditional_identity_within_severity_bin.csv",
    "gate_revision_recommendations.csv",
    "report.md",
    "run_summary.json",
    "source_context_conditional_identity.csv",
}

SOURCE_ROWS = [
    {
        "source_id": "multi_probe_audit_2026",
        "topic": "nearby benchmark audit risk",
        "citation_hint": "Ishikawa and Duke 2026, arXiv:2605.23977",
        "url": "https://arxiv.org/abs/2605.23977",
        "use_in_mv09": "Motivates moving beyond a general clinical-interview benchmark audit toward measurement shift and conditional identity.",
    },
    {
        "source_id": "interviewer_bias_emnlp_2025",
        "topic": "interviewer/protocol invariance prior work",
        "citation_hint": "Zhang and Poellabauer 2025, Findings of EMNLP",
        "url": "https://aclanthology.org/2025.findings-emnlp.650/",
        "use_in_mv09": "Supports treating protocol/question identity as a known nuisance rather than the main novelty.",
    },
    {
        "source_id": "phq_hamd_irt_2021",
        "topic": "PHQ/HAMD measurement differences",
        "citation_hint": "Ma et al. 2021, Frontiers in Psychiatry",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "use_in_mv09": "Supports separating feature/domain shift from target measurement shift.",
    },
    {
        "source_id": "scale_linking_jclinepi_2026",
        "topic": "cross-scale linking and systematic scale differences",
        "citation_hint": "Zhou et al. 2026, Journal of Clinical Epidemiology",
        "url": "https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",
        "use_in_mv09": "Supports the claim that correlated depression scales are not automatically interchangeable targets.",
    },
    {
        "source_id": "phq9_invariance_helius_2017",
        "topic": "classical measurement invariance",
        "citation_hint": "Galenkamp et al. 2017, BMC Psychiatry",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "use_in_mv09": "Motivates formal configural/metric/scalar/partial-invariance baselines before another multimodal head iteration.",
    },
    {
        "source_id": "questionnaire_grounding_acl_2022",
        "topic": "symptom grounding for OOD depression detection",
        "citation_hint": "Nguyen et al. 2022, ACL",
        "url": "https://aclanthology.org/2022.acl-long.578/",
        "use_in_mv09": "Positions symptom grounding as related work; MV09 instead audits target-measurement equivalence and conditional dataset identity.",
    },
]


@dataclass(frozen=True)
class ProbeSpec:
    probe_id: str
    datasets: tuple[str, ...]
    description: str
    strategies: tuple[str, ...]


PROBES = [
    ProbeSpec(
        probe_id="edaic_cmdc_phq_core",
        datasets=("edaic", "cmdc"),
        description="E-DAIC versus CMDC over aligned PHQ C01-C08 BGE subjects.",
        strategies=(
            "raw_bge_unconditional",
            "severity_residualized_bge",
            "severity_gender_residualized_bge",
            "phq_core_items_residualized_bge",
            "severity_common_support_raw_bge",
            "severity_only_control",
            "phq_core_items_control",
        ),
    ),
    ProbeSpec(
        probe_id="cmdc_pdch_same_language_total",
        datasets=("cmdc", "pdch"),
        description="Chinese CMDC versus PDCH over normalized PHQ/HAMD total severity.",
        strategies=(
            "raw_bge_unconditional",
            "normalized_total_residualized_bge",
            "severity_common_support_raw_bge",
            "severity_only_control",
        ),
    ),
    ProbeSpec(
        probe_id="edaic_cmdc_pdch_total_norm",
        datasets=("edaic", "cmdc", "pdch"),
        description="Three-way E-DAIC/CMDC/PDCH BGE identity with normalized total severity.",
        strategies=(
            "raw_bge_unconditional",
            "normalized_total_residualized_bge",
            "severity_common_support_raw_bge",
            "severity_only_control",
        ),
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def bool_series(series: pd.Series) -> pd.Series:
    return mv07.bool_series(series)


def natural_key(value: Any) -> list[Any]:
    return mv07.natural_key(value)


def encode_gender(value: Any) -> float | None:
    text = str(value).strip().lower()
    if text in {"m", "male", "man"}:
        return 1.0
    if text in {"f", "female", "woman"}:
        return 0.0
    return None


def load_covariates(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_dir / f"{dataset}_subjects.csv", usecols=["subject_id", "file_valid", "age", "gender"])
    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    manifest["subject_id"] = manifest["subject_id"].astype(str)
    rows = []
    for subject, group in manifest.groupby("subject_id", sort=False):
        first = group.iloc[0]
        rows.append(
            {
                "subject_id": str(subject),
                "age_numeric": safe_float(first["age"]),
                "gender_numeric": encode_gender(first["gender"]),
            }
        )
    return pd.DataFrame(rows)


def add_dataset_measurement_fields(frame: pd.DataFrame, dataset: str) -> pd.DataFrame:
    out = frame.copy()
    if dataset in {"edaic", "cmdc"}:
        out["measurement_family"] = "PHQ-core"
        out["scale"] = "PHQ-8" if dataset == "edaic" else "PHQ-9"
        out["severity_total_for_conditioning"] = out[CONSTRUCTS].sum(axis=1)
        out["severity_norm"] = out["severity_total_for_conditioning"] / 24.0
    elif dataset == "pdch":
        out["measurement_family"] = "HAMD-17"
        out["scale"] = "HAMD-17"
        out["severity_total_for_conditioning"] = out["target_total"]
        out["severity_norm"] = out["severity_total_for_conditioning"] / 52.0
    else:
        raise ValueError(dataset)
    out["severity_norm"] = out["severity_norm"].clip(lower=0.0, upper=1.0)
    out["severity_bin"] = pd.cut(
        out["severity_norm"],
        bins=SEVERITY_BINS,
        labels=SEVERITY_LABELS,
        include_lowest=True,
    ).astype(str)
    return out


def prepare_tables(manifest_dir: Path, phase2_root: Path) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    features, feature_cols, feature_audit = mv07.load_bge_features(phase2_root)
    labels = {
        "edaic": mv07.load_phq_labels(manifest_dir, "edaic"),
        "cmdc": mv07.load_phq_labels(manifest_dir, "cmdc"),
        "pdch": mv07.load_pdch_hamd_proxy_labels(manifest_dir),
    }
    frames: list[pd.DataFrame] = []
    for dataset in ["edaic", "cmdc", "pdch"]:
        joined = mv07.join_labels_features(labels[dataset], features[dataset])
        joined = add_dataset_measurement_fields(joined, dataset)
        covariates = load_covariates(manifest_dir, dataset)
        joined = joined.merge(covariates, on="subject_id", how="left", validate="one_to_one")
        frames.append(joined)
    table = pd.concat(frames, ignore_index=True)
    return table, feature_cols, feature_audit


def condition_columns_for_strategy(strategy: str, datasets: tuple[str, ...]) -> tuple[list[str], str | None]:
    if strategy in {"severity_residualized_bge", "normalized_total_residualized_bge", "severity_only_control"}:
        return ["severity_norm"], None
    if strategy in {"phq_core_items_residualized_bge", "phq_core_items_control"}:
        if set(datasets) == {"edaic", "cmdc"}:
            return CONSTRUCTS, None
        return [], "PHQ core item conditioning is only defined for E-DAIC/CMDC."
    if strategy == "severity_gender_residualized_bge":
        if set(datasets) == {"edaic", "cmdc"}:
            return ["severity_norm", "gender_numeric"], None
        return [], "Gender conditioning is unavailable for PDCH in the current manifest."
    return [], None


def restrict_common_severity_support(data: pd.DataFrame, datasets: tuple[str, ...], min_per_dataset_bin: int = 3) -> tuple[pd.DataFrame, str]:
    keep_bins: list[str] = []
    for label in SEVERITY_LABELS:
        subset = data[data["severity_bin"] == label]
        counts = subset["dataset"].value_counts().to_dict()
        if all(counts.get(dataset, 0) >= min_per_dataset_bin for dataset in datasets):
            keep_bins.append(label)
    if not keep_bins:
        return data.iloc[0:0].copy(), ""
    return data[data["severity_bin"].isin(keep_bins)].copy(), ";".join(keep_bins)


def build_condition_matrix(train: pd.DataFrame, eval_frame: pd.DataFrame, columns: list[str]) -> tuple[np.ndarray, np.ndarray]:
    if not columns:
        raise ValueError("condition columns are empty")
    c_train_raw = train[columns].to_numpy(dtype=float)
    c_eval_raw = eval_frame[columns].to_numpy(dtype=float)
    valid_columns = []
    for idx, column in enumerate(columns):
        train_values = c_train_raw[:, idx]
        eval_values = c_eval_raw[:, idx]
        if np.isfinite(train_values).mean() >= 0.80 and np.isfinite(eval_values).mean() >= 0.80:
            valid_columns.append(idx)
    if not valid_columns:
        raise ValueError("no condition column has sufficient train/eval coverage")
    c_train_raw = c_train_raw[:, valid_columns]
    c_eval_raw = c_eval_raw[:, valid_columns]
    imputer = SimpleImputer(strategy="median")
    scaler = StandardScaler()
    c_train = scaler.fit_transform(imputer.fit_transform(c_train_raw))
    c_eval = scaler.transform(imputer.transform(c_eval_raw))
    return c_train, c_eval


def residualize_features(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_cols: list[str],
    condition_cols: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    x_imputer = SimpleImputer(strategy="median")
    x_train = x_imputer.fit_transform(train[feature_cols].to_numpy(dtype=float))
    x_eval = x_imputer.transform(eval_frame[feature_cols].to_numpy(dtype=float))
    c_train, c_eval = build_condition_matrix(train, eval_frame, condition_cols)
    residual_model = Ridge(alpha=1.0)
    residual_model.fit(c_train, x_train)
    return x_train - residual_model.predict(c_train), x_eval - residual_model.predict(c_eval)


def classifier(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed),
            ),
        ]
    )


def balanced_accuracy_present_classes(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    recalls: list[float] = []
    for label in sorted(set(y_true.tolist())):
        mask = y_true == label
        if int(mask.sum()) == 0:
            continue
        recalls.append(float(np.mean(y_pred[mask] == label)))
    return float(np.mean(recalls)) if recalls else float("nan")


def run_strategy_probe(
    table: pd.DataFrame,
    feature_cols: list[str],
    spec: ProbeSpec,
    strategy: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    data = table[table["dataset"].isin(spec.datasets)].copy()
    common_bins = ""
    if strategy == "severity_common_support_raw_bge":
        data, common_bins = restrict_common_severity_support(data, spec.datasets)

    condition_cols, skip_reason = condition_columns_for_strategy(strategy, spec.datasets)
    if skip_reason is not None:
        return [], [], {"strategy": strategy, "status": "skipped", "skip_reason": skip_reason}
    if data.empty:
        return [], [], {"strategy": strategy, "status": "skipped", "skip_reason": "No common severity-support subjects."}

    labels = list(spec.datasets)
    y = data["dataset"].map({dataset: idx for idx, dataset in enumerate(labels)}).to_numpy(dtype=int)
    bincount = np.bincount(y, minlength=len(labels))
    if len(labels) < 2 or np.min(bincount) < 3:
        return [], [], {"strategy": strategy, "status": "skipped", "skip_reason": "Insufficient per-dataset samples."}

    by_seed_rows: list[dict[str, Any]] = []
    by_bin_rows: list[dict[str, Any]] = []
    n_splits = int(min(5, np.min(bincount)))
    for seed in SEEDS:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        fold_scores: list[float] = []
        bin_records: list[dict[str, Any]] = []
        for fold_idx, (train_idx, eval_idx) in enumerate(splitter.split(data, y)):
            train = data.iloc[train_idx].copy()
            eval_frame = data.iloc[eval_idx].copy()
            y_train = train["dataset"].map({dataset: idx for idx, dataset in enumerate(labels)}).to_numpy(dtype=int)
            y_eval = eval_frame["dataset"].map({dataset: idx for idx, dataset in enumerate(labels)}).to_numpy(dtype=int)
            try:
                if strategy.endswith("_control"):
                    x_train, x_eval = build_condition_matrix(train, eval_frame, condition_cols)
                    representation = ";".join(condition_cols)
                    residualized = False
                    control_only = True
                elif "residualized" in strategy:
                    x_train, x_eval = residualize_features(train, eval_frame, feature_cols, condition_cols)
                    representation = "text_bge_residualized"
                    residualized = True
                    control_only = False
                else:
                    x_train = train[feature_cols].to_numpy(dtype=float)
                    x_eval = eval_frame[feature_cols].to_numpy(dtype=float)
                    representation = "text_bge_raw"
                    residualized = False
                    control_only = False
            except ValueError:
                continue
            model = classifier(seed + 100 * fold_idx)
            model.fit(x_train, y_train)
            pred = model.predict(x_eval)
            fold_scores.append(float(balanced_accuracy_score(y_eval, pred)))
            for severity_bin, bin_group in eval_frame.assign(_y=y_eval, _pred=pred).groupby("severity_bin", sort=False):
                if len(set(bin_group["_y"].tolist())) >= 2:
                    bin_records.append(
                        {
                            "probe_id": spec.probe_id,
                            "strategy": strategy,
                            "severity_bin": str(severity_bin),
                            "seed": seed,
                            "fold": fold_idx,
                            "eval_samples": int(len(bin_group)),
                            "balanced_accuracy": balanced_accuracy_present_classes(
                                bin_group["_y"].to_numpy(dtype=int),
                                bin_group["_pred"].to_numpy(dtype=int),
                            ),
                        }
                    )
        if not fold_scores:
            continue
        by_seed_rows.append(
            {
                "run_id": RUN_ID,
                "probe_id": spec.probe_id,
                "datasets": ";".join(spec.datasets),
                "strategy": strategy,
                "representation": representation,
                "condition_columns": ";".join(condition_cols),
                "residualized_features": residualized,
                "control_only": control_only,
                "common_severity_bins": common_bins,
                "metric": "Balanced Accuracy",
                "seed": seed,
                "fold_count": int(len(fold_scores)),
                "sample_count": int(len(data)),
                "min_dataset_count": int(np.min(bincount)),
                "mean_fold_value": float(np.mean(fold_scores)),
            }
        )
        if bin_records:
            bin_frame = pd.DataFrame(bin_records)
            for severity_bin, group in bin_frame.groupby("severity_bin", sort=False):
                by_bin_rows.append(
                    {
                        "probe_id": spec.probe_id,
                        "datasets": ";".join(spec.datasets),
                        "strategy": strategy,
                        "severity_bin": severity_bin,
                        "seed": seed,
                        "fold_count": int(group["fold"].nunique()),
                        "eval_samples": int(group["eval_samples"].sum()),
                        "metric": "Balanced Accuracy",
                        "mean_fold_value": float(group["balanced_accuracy"].mean()),
                    }
                )

    if not by_seed_rows:
        return [], [], {"strategy": strategy, "status": "skipped", "skip_reason": "No valid folds after conditioning coverage checks."}
    return by_seed_rows, by_bin_rows, {"strategy": strategy, "status": "complete", "skip_reason": ""}


def summarize_seed_rows(rows: pd.DataFrame) -> pd.DataFrame:
    return (
        rows.groupby(
            [
                "probe_id",
                "datasets",
                "strategy",
                "representation",
                "condition_columns",
                "residualized_features",
                "control_only",
                "common_severity_bins",
                "metric",
            ],
            dropna=False,
        )
        .agg(
            mean=("mean_fold_value", "mean"),
            std=("mean_fold_value", "std"),
            seed_count=("seed", "nunique"),
            sample_count_mean=("sample_count", "mean"),
            min_dataset_count_mean=("min_dataset_count", "mean"),
            fold_count_mean=("fold_count", "mean"),
        )
        .reset_index()
        .fillna({"std": 0.0})
    )


def build_balance_summary(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for spec in PROBES:
        data = table[table["dataset"].isin(spec.datasets)].copy()
        common, common_bins = restrict_common_severity_support(data, spec.datasets)
        for dataset, group in data.groupby("dataset", sort=False):
            bin_counts = group["severity_bin"].value_counts().reindex(SEVERITY_LABELS, fill_value=0)
            rows.append(
                {
                    "probe_id": spec.probe_id,
                    "dataset": dataset,
                    "samples": int(len(group)),
                    "scale": str(group["scale"].iloc[0]),
                    "severity_norm_mean": float(group["severity_norm"].mean()),
                    "severity_norm_std": float(group["severity_norm"].std(ddof=0)),
                    "severity_norm_min": float(group["severity_norm"].min()),
                    "severity_norm_max": float(group["severity_norm"].max()),
                    "severity_bin_counts": ";".join(f"{label}:{int(bin_counts[label])}" for label in SEVERITY_LABELS),
                    "common_severity_bins": common_bins,
                    "common_support_samples": int((common["dataset"] == dataset).sum()),
                    "age_coverage": float(group["age_numeric"].notna().mean()),
                    "gender_coverage": float(group["gender_numeric"].notna().mean()),
                }
            )
    return pd.DataFrame(rows)


def lookup(summary: pd.DataFrame, probe_id: str, strategy: str) -> float | None:
    row = summary[(summary["probe_id"] == probe_id) & (summary["strategy"] == strategy)]
    if row.empty:
        return None
    return safe_float(row.iloc[0]["mean"])


def build_gate_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    edaic_cmdc_raw = lookup(summary, "edaic_cmdc_phq_core", "raw_bge_unconditional")
    edaic_cmdc_item = lookup(summary, "edaic_cmdc_phq_core", "phq_core_items_residualized_bge")
    edaic_cmdc_sev = lookup(summary, "edaic_cmdc_phq_core", "severity_residualized_bge")
    cmdc_pdch_raw = lookup(summary, "cmdc_pdch_same_language_total", "raw_bge_unconditional")
    cmdc_pdch_sev = lookup(summary, "cmdc_pdch_same_language_total", "normalized_total_residualized_bge")
    all_raw = lookup(summary, "edaic_cmdc_pdch_total_norm", "raw_bge_unconditional")
    all_sev = lookup(summary, "edaic_cmdc_pdch_total_norm", "normalized_total_residualized_bge")

    if edaic_cmdc_item is None:
        conditional_status = "conditional_probe_incomplete"
    elif edaic_cmdc_item >= 0.75:
        conditional_status = "conditional_identity_remains_high"
    elif edaic_cmdc_item >= 0.60:
        conditional_status = "conditional_identity_reduced_but_nontrivial"
    else:
        conditional_status = "conditional_identity_near_chance_or_mild"

    rows = [
        {
            "recommendation_id": "identity_gate_scope",
            "status": "revise_future_gate",
            "recommendation": "Use unconditional dataset identity as a shortcut-risk screen, not as a standalone hard-failure criterion.",
            "evidence": f"E-DAIC/CMDC raw BA={fmt(edaic_cmdc_raw)}; item-conditioned BA={fmt(edaic_cmdc_item)}; severity-conditioned BA={fmt(edaic_cmdc_sev)}.",
        },
        {
            "recommendation_id": "conditional_identity_gate",
            "status": conditional_status,
            "recommendation": "For future shared-latent claims, report dataset identity after conditioning on target severity, item labels where aligned, and available legitimate covariates.",
            "evidence": f"CMDC/PDCH raw BA={fmt(cmdc_pdch_raw)} and severity-conditioned BA={fmt(cmdc_pdch_sev)}; three-way raw BA={fmt(all_raw)} and severity-conditioned BA={fmt(all_sev)}.",
        },
        {
            "recommendation_id": "prediction_identity_gate",
            "status": "demote_post_head_hard_gate",
            "recommendation": "Treat post-head prediction identity as diagnostic when outputs are scale-specific; reserve hard identity gates for shared latent representations or explicitly shared prediction spaces.",
            "evidence": "MV08/MV08b prediction probes operate after scale-specific measurement heads, so their identity BA should not be interpreted the same way as shared-latent identity.",
        },
        {
            "recommendation_id": "mv08b_interpretation",
            "status": "still_not_positive_rq1",
            "recommendation": "Do not rescue MV08b as a positive RQ1 result: its item-MAE gains are tiny and it still lacks an independently fitted psychometric latent target.",
            "evidence": "MV08b should be reframed as a measurement-gate diagnostic result, not as a transferable shared-measurement success.",
        },
        {
            "recommendation_id": "next_experiment",
            "status": "plan_psychometric_baseline",
            "recommendation": "Add a classical psychometric invariance baseline before any MV08c-like multimodal head iteration.",
            "evidence": "PHQ/HAMD psychometric and scale-linking literature supports separating measurement model Y->theta from multimodal prediction X->theta.",
        },
    ]
    return pd.DataFrame(rows)


def first_row(frame: pd.DataFrame, **filters: Any) -> dict[str, Any] | None:
    selected = frame.copy()
    for column, value in filters.items():
        selected = selected[selected[column].astype(str) == str(value)]
    if selected.empty:
        return None
    return selected.iloc[0].to_dict()


def build_pareto_summary() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    def add_point(
        source_run: str,
        family: str,
        model: str,
        macro_values: list[float | None],
        feature_identity_ba: float | None,
        prediction_identity_ba: float | None,
        notes: str,
    ) -> None:
        values = [value for value in macro_values if value is not None and math.isfinite(float(value))]
        rows.append(
            {
                "source_run": source_run,
                "family": family,
                "model": model,
                "mean_macro_mae": float(np.mean(values)) if values else None,
                "dataset_identity_ba_feature": feature_identity_ba,
                "dataset_identity_ba_prediction": prediction_identity_ba,
                "notes": notes,
            }
        )

    mv07_comp = pd.read_csv(ROOT / "analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/comparison_summary.csv")
    mv07_id = pd.read_csv(ROOT / "analysis/phase5_minimal_validation/p5_mv07_aligned_bge_shared_symptom/identity_probe_summary.csv")
    mv07_feat = first_row(mv07_id, probe_id="feature_identity_bge_edaic_cmdc_pdch")
    mv07_pred = first_row(mv07_id, probe_id="prediction_identity_pooled_phq_edaic_cmdc")
    add_point(
        "P5_MV07",
        "aligned_bge_phq",
        "raw_bge_itemwise_ridge",
        [
            first_row(mv07_comp, protocol="pooled_shared_phq", dataset_slice="edaic", model="bge_itemwise_ridge")["macro_mae"],
            first_row(mv07_comp, protocol="pooled_shared_phq", dataset_slice="cmdc", model="bge_itemwise_ridge")["macro_mae"],
        ],
        safe_float(mv07_feat["mean"]) if mv07_feat else None,
        safe_float(mv07_pred["mean"]) if mv07_pred else None,
        "Raw aligned-BGE pooled PHQ itemwise head.",
    )

    mv07b_comp = pd.read_csv(ROOT / "analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/comparison_summary.csv")
    mv07b_id = pd.read_csv(ROOT / "analysis/phase5_minimal_validation/p5_mv07b_bge_identity_projection/identity_probe_summary.csv")
    for model in sorted(mv07b_comp["model"].unique(), key=natural_key):
        if model not in {"bge_itemwise_ridge_raw", "bge_logit_projection_k1_itemwise_ridge", "bge_logit_projection_k3_itemwise_ridge", "bge_logit_projection_k5_itemwise_ridge", "bge_logit_projection_k10_itemwise_ridge"}:
            continue
        rep_suffix = "raw_bge" if model == "bge_itemwise_ridge_raw" else model.replace("_itemwise_ridge", "")
        feature_rep = "raw_bge_features" if model == "bge_itemwise_ridge_raw" else f"{rep_suffix}_features"
        pred_rep = "raw_bge_predictions" if model == "bge_itemwise_ridge_raw" else f"{rep_suffix}_predictions"
        feat = first_row(mv07b_id, probe_id="edaic_vs_cmdc_identity_train_fold_to_eval_fold", probe_layer="feature", representation=feature_rep)
        pred = first_row(mv07b_id, probe_id="edaic_vs_cmdc_identity_train_fold_to_eval_fold", probe_layer="prediction", representation=pred_rep)
        add_point(
            "P5_MV07b",
            "aligned_bge_phq",
            model,
            [
                first_row(mv07b_comp, dataset_slice="edaic", model=model)["macro_mae"],
                first_row(mv07b_comp, dataset_slice="cmdc", model=model)["macro_mae"],
            ],
            safe_float(feat["mean"]) if feat else None,
            safe_float(pred["mean"]) if pred else None,
            "Train-fold dataset-logit nuisance projection sweep.",
        )

    mv07c_comp = pd.read_csv(ROOT / "analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/comparison_summary.csv")
    mv07c_id = pd.read_csv(ROOT / "analysis/phase5_minimal_validation/p5_mv07c_bge_total_anchor/identity_probe_summary.csv")
    for model in sorted(mv07c_comp["model"].unique(), key=natural_key):
        feat_rep = "raw_bge_features" if model in {"raw_bge_itemwise_ridge", "raw_total_alloc_ridge", "train_mean"} else "cvselected_projected_bge_features"
        pred_rep = "cvselected_total_anchor_predictions" if model == "cvselected_projected_total_anchor_itemwise" else None
        feat = first_row(mv07c_id, probe_id="edaic_vs_cmdc_identity_train_fold_to_eval_fold", probe_layer="feature", representation=feat_rep)
        pred = first_row(mv07c_id, probe_id="edaic_vs_cmdc_identity_train_fold_to_eval_fold", probe_layer="prediction", representation=pred_rep) if pred_rep else None
        add_point(
            "P5_MV07c",
            "aligned_bge_total_anchor",
            model,
            [
                first_row(mv07c_comp, dataset_slice="edaic", model=model)["macro_mae"],
                first_row(mv07c_comp, dataset_slice="cmdc", model=model)["macro_mae"],
            ],
            safe_float(feat["mean"]) if feat else None,
            safe_float(pred["mean"]) if pred else None,
            "Total-anchor follow-up; prediction identity available for selected total-anchor output only.",
        )

    for run_id, rel_dir in [
        ("P5_MV08", "p5_mv08_partial_invariance_measurement"),
        ("P5_MV08b", "p5_mv08b_total_anchored_residual_measurement"),
    ]:
        comp = pd.read_csv(ROOT / f"analysis/phase5_minimal_validation/{rel_dir}/comparison_summary.csv")
        ident = pd.read_csv(ROOT / f"analysis/phase5_minimal_validation/{rel_dir}/identity_probe_summary.csv")
        pooled = comp[comp["protocol"] == "pooled_partial_invariance"].copy()
        for model in sorted(pooled["model"].unique(), key=natural_key):
            model_rows = pooled[pooled["model"] == model]
            feat = first_row(ident, probe_id="feature_identity_bge_edaic_cmdc_pdch")
            pred = first_row(ident, probe_id="prediction_identity_pooled_eval_dataset", model=model)
            add_point(
                run_id,
                "partial_invariance_measurement",
                model,
                model_rows["macro_item_mae"].astype(float).tolist(),
                safe_float(feat["mean"]) if feat else None,
                safe_float(pred["mean"]) if pred else None,
                "Cross-scale measurement row; MAE averages E-DAIC, CMDC, and PDCH pooled slices.",
            )

    return pd.DataFrame(rows)


def source_context() -> pd.DataFrame:
    return pd.DataFrame(SOURCE_ROWS)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsession_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"source_locator",
        r"local_.*predictions",
        r"raw snippet",
        r"raw evidence snippet",
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
        "audit_id": "P5_MV09_conditional_identity_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    summary: pd.DataFrame,
    recommendations: pd.DataFrame,
    pareto: pd.DataFrame,
    run_summary: dict[str, Any],
) -> None:
    lines = [
        "# P5 MV09 Conditional Dataset-Identity Audit",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV09 checks whether dataset identifiability remains after conditioning on available severity, aligned item labels, and usable covariates. It is a diagnostic audit of the identity gate, not a deployable method.",
        "",
        "## Headline Conditional Identity",
        "",
        "| probe | strategy | BA | condition | interpretation |",
        "| --- | --- | ---: | --- | --- |",
    ]
    key_rows = summary[
        summary["strategy"].isin(
            [
                "raw_bge_unconditional",
                "severity_residualized_bge",
                "phq_core_items_residualized_bge",
                "normalized_total_residualized_bge",
                "severity_common_support_raw_bge",
            ]
        )
    ].copy()
    for _, row in key_rows.iterrows():
        interpretation = "screen only" if row["strategy"] == "raw_bge_unconditional" else "conditional identity diagnostic"
        lines.append(
            f"| {row['probe_id']} | {row['strategy']} | {fmt(row['mean'])} | {row['condition_columns'] or 'none'} | {interpretation} |"
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
        lines.append(f"| {row['recommendation_id']} | `{row['status']}` | {row['evidence']} |")
    lines.extend(
        [
            "",
            "## Accuracy-Invariance Trade-Off",
            "",
            "| source | model | mean macro MAE | feature identity BA | prediction identity BA |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    compact = pareto.sort_values(["source_run", "model"], key=lambda s: s.map(lambda x: tuple(natural_key(x)))).copy()
    for _, row in compact.iterrows():
        lines.append(
            f"| {row['source_run']} | {row['model']} | {fmt(row['mean_macro_mae'])} | {fmt(row['dataset_identity_ba_feature'])} | {fmt(row['dataset_identity_ba_prediction'])} |"
        )
    lines.extend(
        [
            "",
            "## Release Rule",
            "",
            "- Tracked outputs are aggregate only.",
            "- No subject-level predictions, learned parameters, local source locators, media paths, or raw text are exported.",
            "- Future full-method gates should distinguish unconditional feature identity, conditional shared-latent identity, and scale-specific post-head prediction identity.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, manifest_dir: Path, phase2_root: Path, generated_at: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    table, feature_cols, feature_audit = prepare_tables(manifest_dir, phase2_root)

    seed_rows: list[dict[str, Any]] = []
    bin_rows: list[dict[str, Any]] = []
    strategy_status: list[dict[str, Any]] = []
    for spec in PROBES:
        for strategy in spec.strategies:
            rows, bins, status = run_strategy_probe(table, feature_cols, spec, strategy)
            seed_rows.extend(rows)
            bin_rows.extend(bins)
            strategy_status.append({"probe_id": spec.probe_id, **status})

    if not seed_rows:
        raise RuntimeError("No MV09 conditional identity probes completed.")
    by_seed = pd.DataFrame(seed_rows)
    summary = summarize_seed_rows(by_seed)
    within_bin = pd.DataFrame(bin_rows)
    if within_bin.empty:
        within_bin = pd.DataFrame(
            columns=["probe_id", "datasets", "strategy", "severity_bin", "seed", "fold_count", "eval_samples", "metric", "mean_fold_value"]
        )
    balance = build_balance_summary(table)
    recommendations = build_gate_recommendations(summary)
    pareto = build_pareto_summary()
    sources = source_context()

    by_seed.to_csv(out_dir / "conditional_identity_by_seed.csv", index=False)
    summary.to_csv(out_dir / "conditional_identity_summary.csv", index=False)
    within_bin.to_csv(out_dir / "conditional_identity_within_severity_bin.csv", index=False)
    balance.to_csv(out_dir / "condition_balance_summary.csv", index=False)
    recommendations.to_csv(out_dir / "gate_revision_recommendations.csv", index=False)
    pareto.to_csv(out_dir / "accuracy_invariance_pareto_summary.csv", index=False)
    sources.to_csv(out_dir / "source_context_conditional_identity.csv", index=False)

    completed = [row for row in strategy_status if row["status"] == "complete"]
    skipped = [row for row in strategy_status if row["status"] == "skipped"]
    verdict = {
        "status": "complete_identity_gate_revision_needed",
        "edaic_cmdc_raw_ba": lookup(summary, "edaic_cmdc_phq_core", "raw_bge_unconditional"),
        "edaic_cmdc_severity_residualized_ba": lookup(summary, "edaic_cmdc_phq_core", "severity_residualized_bge"),
        "edaic_cmdc_item_residualized_ba": lookup(summary, "edaic_cmdc_phq_core", "phq_core_items_residualized_bge"),
        "cmdc_pdch_raw_ba": lookup(summary, "cmdc_pdch_same_language_total", "raw_bge_unconditional"),
        "cmdc_pdch_severity_residualized_ba": lookup(summary, "cmdc_pdch_same_language_total", "normalized_total_residualized_bge"),
        "three_way_raw_ba": lookup(summary, "edaic_cmdc_pdch_total_norm", "raw_bge_unconditional"),
        "three_way_severity_residualized_ba": lookup(summary, "edaic_cmdc_pdch_total_norm", "normalized_total_residualized_bge"),
        "short_read": "Unconditional dataset identity should be treated as a shortcut-risk screen; future gates need conditional identity for shared latent claims.",
    }

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "status": "complete",
        "scope": "conditional_dataset_identity_gate_audit",
        "input_contract": {
            "feature_family": "text_bge",
            "datasets": ["edaic", "cmdc", "pdch"],
            "raw_text_or_media_read": False,
            "row_level_predictions_written": False,
            "labels_used_for_diagnostic_conditioning": True,
            "deployable_model_claim": False,
            "full_method_allowed": False,
        },
        "data_contract": {
            "joined_subjects": {dataset: int((table["dataset"] == dataset).sum()) for dataset in ["edaic", "cmdc", "pdch"]},
            "model_input_columns": int(len(feature_cols)),
            "covariate_controls": {
                "edaic_cmdc_gender_available": True,
                "edaic_cmdc_age_available": False,
                "pdch_age_gender_available": False,
            },
        },
        "outputs": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "conditional_identity_rows": int(len(summary)),
            "conditional_identity_seed_rows": int(len(by_seed)),
            "within_severity_bin_rows": int(len(within_bin)),
            "pareto_rows": int(len(pareto)),
            "completed_strategy_rows": int(len(completed)),
            "skipped_strategy_rows": int(len(skipped)),
        },
        "strategy_status": strategy_status,
        "verdict": verdict,
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, summary, recommendations, pareto, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, summary, recommendations, pareto, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--phase2-root", type=Path, default=DEFAULT_PHASE2_ROOT)
    args = parser.parse_args()

    generated_at = utc_now()
    run_summary = build_outputs(args.out_dir, args.manifest_dir, args.phase2_root, generated_at)
    print(
        "Wrote conditional identity audit to "
        f"{args.out_dir.relative_to(ROOT)} with status {run_summary['verdict']['status']}"
    )


if __name__ == "__main__":
    main()
