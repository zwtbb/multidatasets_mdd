#!/usr/bin/env python3
"""Run P5_MV05 MPDD context-calibration minimal validation.

This Phase 5 row tests whether MPDD age and personality-bin context can
calibrate a frozen audio-video severity predictor without turning personality,
age, or gait into a generic shortcut feature stream. The proposed head consumes
only out-of-fold AV probabilities plus fold-local aggregate context bins. Raw
personality text is parsed in memory for bins but is never written.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
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
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import phase3_mpdd_individual_differences as p3
from phase2_metrics import compute_metrics, parse_probability_vector, safe_float, spearman


ROOT = p3.ROOT
DATASET_DISPLAY = p3.DATASET_DISPLAY
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv05_mpdd_context_calibration"
DEFAULT_MANIFEST_PATH = p3.MANIFEST_PATH

SEEDS = [0, 1, 2, 3, 4]
CLASS_LABELS = [0, 1, 2]
TRAITS = p3.TRAITS
PERSONALITY_CONTEXT_COLUMNS = [f"{trait}_bin" for trait in TRAITS] + ["financial_stress_bin"]
CONTEXT_COLUMNS = ["age_group", *PERSONALITY_CONTEXT_COLUMNS]
REQUIRED_METRICS = ["QWK", "Ordinal MAE", "Macro-F1", "ECE", "Brier Score"]

RUN_ID = "P5_MV05_mpdd_context_calibration"
BASELINE_MODEL = "av_baseline_logistic"
AV_PROB_MODEL = "av_probability_recalibrated"
PROPOSED_MODEL = "av_context_calibrated_age_personality_bins"
SHUFFLED_PERSONALITY_MODEL = "av_context_calibrated_shuffled_personality_bins"
SHUFFLED_AGE_MODEL = "av_context_calibrated_shuffled_age"
CONTEXT_ONLY_MODEL = "context_only_age_personality_bins"

MODEL_ORDER = [
    BASELINE_MODEL,
    AV_PROB_MODEL,
    PROPOSED_MODEL,
    SHUFFLED_PERSONALITY_MODEL,
    SHUFFLED_AGE_MODEL,
    CONTEXT_ONLY_MODEL,
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_value(value: Any, digits: int = 4) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def probability_json(probabilities: np.ndarray, idx: int) -> str:
    return json.dumps([float(value) for value in probabilities[idx]], ensure_ascii=True)


def stable_rng(seed: int, fold: int, salt: str) -> np.random.Generator:
    salt_value = sum((index + 1) * ord(char) for index, char in enumerate(salt))
    return np.random.default_rng((seed + 1) * 1_000_003 + fold * 10_007 + salt_value)


def classifier_pipeline(seed: int, class_weight: str | None = "balanced") -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    C=1.0,
                    class_weight=class_weight,
                    max_iter=1200,
                    random_state=seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )


def fit_predict_probabilities(
    train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
    class_weight: str | None = "balanced",
) -> np.ndarray:
    model = classifier_pipeline(seed, class_weight=class_weight)
    model.fit(train[feature_columns].to_numpy(dtype=float), train["severity_label"].astype(int))
    raw_prob = model.predict_proba(eval_frame[feature_columns].to_numpy(dtype=float))
    return p3.align_probabilities(raw_prob, model.named_steps["classifier"].classes_)


def inner_oof_av_probabilities(
    train: pd.DataFrame,
    feature_columns: list[str],
    seed: int,
    outer_fold: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    labels = train["severity_label"].astype(int).to_numpy()
    counts = pd.Series(labels).value_counts()
    n_splits = int(min(5, counts.min()))
    if n_splits < 2:
        raise ValueError("not enough class support for inner AV probability calibration folds")
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed * 101 + outer_fold)
    probs = np.zeros((len(train), len(CLASS_LABELS)), dtype=np.float64)
    rows: list[dict[str, Any]] = []
    for inner_fold, (inner_train_idx, inner_eval_idx) in enumerate(splitter.split(train, labels), start=1):
        inner_train = train.iloc[inner_train_idx].reset_index(drop=True)
        inner_eval = train.iloc[inner_eval_idx].reset_index(drop=True)
        fold_prob = fit_predict_probabilities(
            inner_train,
            inner_eval,
            feature_columns,
            seed=seed * 10_000 + outer_fold * 100 + inner_fold,
            class_weight="balanced",
        )
        probs[inner_eval_idx] = fold_prob
        rows.append(
            {
                "seed": int(seed),
                "outer_fold": int(outer_fold),
                "inner_fold": int(inner_fold),
                "train_subjects": int(inner_train["subject_id"].nunique()),
                "heldout_subjects": int(inner_eval["subject_id"].nunique()),
                "subject_overlap_count": int(
                    len(set(inner_train["subject_id"].astype(str)) & set(inner_eval["subject_id"].astype(str)))
                ),
            }
        )
    return probs, rows


def probability_features(probabilities: np.ndarray) -> pd.DataFrame:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float64), 1.0e-6, 1.0)
    clipped = clipped / clipped.sum(axis=1, keepdims=True)
    labels = np.asarray(CLASS_LABELS, dtype=np.float64)
    entropy = -np.sum(clipped * np.log(clipped), axis=1) / math.log(len(CLASS_LABELS))
    frame = pd.DataFrame(
        {
            "av_prob_0": clipped[:, 0],
            "av_prob_1": clipped[:, 1],
            "av_prob_2": clipped[:, 2],
            "av_logit_0": np.log(clipped[:, 0] / (1.0 - clipped[:, 0] + 1.0e-6)),
            "av_logit_1": np.log(clipped[:, 1] / (1.0 - clipped[:, 1] + 1.0e-6)),
            "av_logit_2": np.log(clipped[:, 2] / (1.0 - clipped[:, 2] + 1.0e-6)),
            "av_expected_severity": clipped @ labels,
            "av_confidence": np.max(clipped, axis=1),
            "av_entropy": entropy,
        }
    )
    return frame


def normalized_context(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame[CONTEXT_COLUMNS].copy()
    for column in CONTEXT_COLUMNS:
        out[column] = out[column].fillna("missing").astype(str).str.strip().replace({"": "missing"})
    return out


def permute_series(values: pd.Series, seed: int, fold: int, salt: str) -> pd.Series:
    arr = values.to_numpy(dtype=object).copy()
    if len(arr) > 1:
        stable_rng(seed, fold, salt).shuffle(arr)
    return pd.Series(arr, index=values.index, dtype=object)


def context_for_mode(frame: pd.DataFrame, mode: str, seed: int, fold: int) -> pd.DataFrame:
    context = normalized_context(frame)
    if mode == "shuffled_personality":
        for column in PERSONALITY_CONTEXT_COLUMNS:
            context[column] = permute_series(context[column], seed, fold, f"{mode}_{column}")
    elif mode == "shuffled_age":
        context["age_group"] = permute_series(context["age_group"], seed, fold, mode)
    elif mode != "observed":
        raise ValueError(f"unknown context mode: {mode}")
    return context


def fit_context_encoder(train_context: pd.DataFrame) -> list[str]:
    encoded = pd.get_dummies(train_context, prefix=train_context.columns.tolist(), dtype=float)
    return sorted(encoded.columns.tolist())


def transform_context(context: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    encoded = pd.get_dummies(context, prefix=context.columns.tolist(), dtype=float)
    return encoded.reindex(columns=columns, fill_value=0.0)


def design_matrices(
    train_probabilities: np.ndarray,
    eval_probabilities: np.ndarray,
    train_context: pd.DataFrame,
    eval_context: pd.DataFrame,
    include_probabilities: bool,
    include_context: bool,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    parts_train: list[pd.DataFrame] = []
    parts_eval: list[pd.DataFrame] = []
    columns: list[str] = []
    if include_probabilities:
        train_prob_frame = probability_features(train_probabilities)
        eval_prob_frame = probability_features(eval_probabilities)
        parts_train.append(train_prob_frame)
        parts_eval.append(eval_prob_frame)
        columns.extend(train_prob_frame.columns.tolist())
    if include_context:
        context_columns = fit_context_encoder(train_context)
        train_context_frame = transform_context(train_context, context_columns)
        eval_context_frame = transform_context(eval_context, context_columns)
        parts_train.append(train_context_frame)
        parts_eval.append(eval_context_frame)
        columns.extend(context_columns)
    if not parts_train:
        raise ValueError("empty calibration design matrix")
    train_matrix = pd.concat(parts_train, axis=1).to_numpy(dtype=float)
    eval_matrix = pd.concat(parts_eval, axis=1).to_numpy(dtype=float)
    return train_matrix, eval_matrix, columns


def fit_calibrator(
    train_matrix: np.ndarray,
    y_train: pd.Series,
    eval_matrix: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, LogisticRegression]:
    model = LogisticRegression(C=1.0, class_weight=None, max_iter=1200, random_state=seed, solver="lbfgs")
    model.fit(train_matrix, y_train.astype(int))
    raw_prob = model.predict_proba(eval_matrix)
    return p3.align_probabilities(raw_prob, model.classes_), model


def add_prediction_rows(
    rows: list[dict[str, Any]],
    heldout: pd.DataFrame,
    probabilities: np.ndarray,
    model_name: str,
    seed: int,
    fold: int,
    input_contract: str,
    calibration_context: str,
) -> None:
    y_pred = np.argmax(probabilities, axis=1)
    for idx, row in heldout.reset_index(drop=True).iterrows():
        prediction_row: dict[str, Any] = {
            "run_id": RUN_ID,
            "dataset": DATASET_DISPLAY,
            "modality": "Audio+Video",
            "task": "PHQ-9 ordinal severity prediction",
            "model": model_name,
            "seed": int(seed),
            "fold": int(fold),
            "task_type": "ordinal_prediction",
            "subject_id": str(row["subject_id"]),
            "split": "train_oof",
            "input_contract": input_contract,
            "calibration_context": calibration_context,
            "y_true": int(row["severity_label"]),
            "y_pred": int(y_pred[idx]),
            "y_prob": probability_json(probabilities, idx),
            "age_group": str(row["age_group"]),
            "financial_stress_bin": str(row["financial_stress_bin"]),
            "gender_group": str(row["gender_group"]),
            "health_group": str(row["health_group"]),
        }
        for trait in TRAITS:
            prediction_row[f"{trait}_bin"] = str(row[f"{trait}_bin"])
        rows.append(prediction_row)


def swapped_age_context(context: pd.DataFrame) -> pd.DataFrame:
    out = context.copy()
    out["age_group"] = out["age_group"].map({"elder": "young", "young": "elder"}).fillna(out["age_group"])
    return out


def personality_counterfactual_context(
    heldout_context: pd.DataFrame,
    train_context: pd.DataFrame,
    seed: int,
    fold: int,
) -> pd.DataFrame:
    out = heldout_context.copy()
    ordered = train_context.reset_index(drop=True)
    if ordered.empty:
        return out
    offset = int(stable_rng(seed, fold, "personality_counterfactual").integers(0, len(ordered)))
    for idx in range(len(out)):
        donor = ordered.iloc[(idx + offset) % len(ordered)]
        for column in PERSONALITY_CONTEXT_COLUMNS:
            out.iat[idx, out.columns.get_loc(column)] = donor[column]
    return out


def expected_severity(probabilities: np.ndarray) -> np.ndarray:
    return np.asarray(probabilities, dtype=np.float64) @ np.asarray(CLASS_LABELS, dtype=np.float64)


def add_counterfactual_rows(
    rows: list[dict[str, Any]],
    heldout: pd.DataFrame,
    actual_probabilities: np.ndarray,
    counter_probabilities: np.ndarray,
    seed: int,
    fold: int,
    counterfactual_type: str,
) -> None:
    actual_pred = np.argmax(actual_probabilities, axis=1)
    counter_pred = np.argmax(counter_probabilities, axis=1)
    actual_expected = expected_severity(actual_probabilities)
    counter_expected = expected_severity(counter_probabilities)
    for idx, row in heldout.reset_index(drop=True).iterrows():
        rows.append(
            {
                "seed": int(seed),
                "fold": int(fold),
                "subject_id": str(row["subject_id"]),
                "counterfactual_type": counterfactual_type,
                "age_group": str(row["age_group"]),
                "true_severity": int(row["severity_label"]),
                "actual_pred": int(actual_pred[idx]),
                "counterfactual_pred": int(counter_pred[idx]),
                "changed_pred": bool(int(actual_pred[idx]) != int(counter_pred[idx])),
                "actual_expected_severity": float(actual_expected[idx]),
                "counterfactual_expected_severity": float(counter_expected[idx]),
                "delta_expected_severity": float(counter_expected[idx] - actual_expected[idx]),
            }
        )


def calibration_context_probabilities(
    train: pd.DataFrame,
    heldout: pd.DataFrame,
    train_av_probabilities: np.ndarray,
    heldout_av_probabilities: np.ndarray,
    seed: int,
    fold: int,
    mode: str,
    include_probabilities: bool,
    include_context: bool,
) -> tuple[np.ndarray, LogisticRegression, list[str], pd.DataFrame, pd.DataFrame]:
    train_context = context_for_mode(train, mode, seed, fold)
    heldout_context = context_for_mode(heldout, mode, seed, fold)
    x_train, x_heldout, design_columns = design_matrices(
        train_av_probabilities,
        heldout_av_probabilities,
        train_context,
        heldout_context,
        include_probabilities=include_probabilities,
        include_context=include_context,
    )
    probabilities, model = fit_calibrator(
        x_train,
        train["severity_label"],
        x_heldout,
        seed=seed * 10_000 + fold * 100 + len(design_columns),
    )
    return probabilities, model, design_columns, train_context, heldout_context


def counterfactual_probabilities(
    model: LogisticRegression,
    design_columns: list[str],
    train_context: pd.DataFrame,
    counter_context: pd.DataFrame,
    heldout_av_probabilities: np.ndarray,
) -> np.ndarray:
    context_design_columns = [column for column in design_columns if not column.startswith("av_")]
    parts: list[pd.DataFrame] = []
    if any(column.startswith("av_") for column in design_columns):
        parts.append(probability_features(heldout_av_probabilities))
    if context_design_columns:
        context_columns = fit_context_encoder(train_context)
        context_frame = transform_context(counter_context, context_columns)
        parts.append(context_frame)
    matrix = pd.concat(parts, axis=1).reindex(columns=design_columns, fill_value=0.0).to_numpy(dtype=float)
    raw_prob = model.predict_proba(matrix)
    return p3.align_probabilities(raw_prob, model.classes_)


def run_experiment(
    table: pd.DataFrame,
    audio_columns: list[str],
    video_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    feature_columns = audio_columns + video_columns
    labels = table["severity_label"].astype(int).to_numpy()
    predictions: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    counterfactual_rows: list[dict[str, Any]] = []
    for seed in SEEDS:
        outer = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, heldout_idx) in enumerate(outer.split(table, labels), start=1):
            train = table.iloc[train_idx].reset_index(drop=True)
            heldout = table.iloc[heldout_idx].reset_index(drop=True)
            train_subjects = set(train["subject_id"].astype(str))
            heldout_subjects = set(heldout["subject_id"].astype(str))
            overlap = train_subjects & heldout_subjects
            if overlap:
                raise ValueError(f"outer split overlap: {sorted(overlap, key=p3.natural_key)[:5]}")

            train_av_probabilities, inner_rows = inner_oof_av_probabilities(train, feature_columns, seed, fold)
            heldout_av_probabilities = fit_predict_probabilities(
                train,
                heldout,
                feature_columns,
                seed=seed * 1000 + fold,
                class_weight="balanced",
            )
            add_prediction_rows(
                predictions,
                heldout,
                heldout_av_probabilities,
                BASELINE_MODEL,
                seed,
                fold,
                "frozen_wavlm_resnet_subject_features",
                "none",
            )

            for inner in inner_rows:
                audit_rows.append(
                    {
                        **inner,
                        "audit_level": "inner_av_oof_for_calibrator",
                        "model": BASELINE_MODEL,
                        "outer_train_subjects": int(len(train_subjects)),
                        "outer_heldout_subjects": int(len(heldout_subjects)),
                        "outer_subject_overlap_count": int(len(overlap)),
                        "input_contract": "frozen_wavlm_resnet_subject_features",
                        "calibration_context": "none",
                        "raw_text_used_for_model_input": False,
                        "encoder_finetuning": False,
                    }
                )

            model_specs = [
                (
                    AV_PROB_MODEL,
                    "observed",
                    True,
                    False,
                    "av_probabilities_only",
                    "none",
                ),
                (
                    PROPOSED_MODEL,
                    "observed",
                    True,
                    True,
                    "av_probabilities_primary_plus_context_bins",
                    "observed_age_personality_bins",
                ),
                (
                    SHUFFLED_PERSONALITY_MODEL,
                    "shuffled_personality",
                    True,
                    True,
                    "av_probabilities_primary_plus_context_bins",
                    "observed_age_shuffled_personality_bins",
                ),
                (
                    SHUFFLED_AGE_MODEL,
                    "shuffled_age",
                    True,
                    True,
                    "av_probabilities_primary_plus_context_bins",
                    "shuffled_age_observed_personality_bins",
                ),
                (
                    CONTEXT_ONLY_MODEL,
                    "observed",
                    False,
                    True,
                    "context_bins_only_sanity_check",
                    "observed_age_personality_bins",
                ),
            ]
            proposed_details: tuple[LogisticRegression, list[str], pd.DataFrame, pd.DataFrame, np.ndarray] | None = None
            for (
                model_name,
                mode,
                include_probabilities,
                include_context,
                input_contract,
                calibration_context,
            ) in model_specs:
                probabilities, model, design_columns, train_context, heldout_context = calibration_context_probabilities(
                    train,
                    heldout,
                    train_av_probabilities,
                    heldout_av_probabilities,
                    seed,
                    fold,
                    mode,
                    include_probabilities=include_probabilities,
                    include_context=include_context,
                )
                add_prediction_rows(
                    predictions,
                    heldout,
                    probabilities,
                    model_name,
                    seed,
                    fold,
                    input_contract,
                    calibration_context,
                )
                audit_rows.append(
                    {
                        "audit_level": "outer_model",
                        "model": model_name,
                        "seed": int(seed),
                        "outer_fold": int(fold),
                        "inner_fold": None,
                        "train_subjects": int(len(train_subjects)),
                        "heldout_subjects": int(len(heldout_subjects)),
                        "subject_overlap_count": int(len(overlap)),
                        "outer_train_subjects": int(len(train_subjects)),
                        "outer_heldout_subjects": int(len(heldout_subjects)),
                        "outer_subject_overlap_count": int(len(overlap)),
                        "input_contract": input_contract,
                        "calibration_context": calibration_context,
                        "design_feature_count": int(len(design_columns)),
                        "av_probability_feature_count": int(sum(column.startswith("av_") for column in design_columns)),
                        "context_bin_feature_count": int(sum(not column.startswith("av_") for column in design_columns)),
                        "raw_text_used_for_model_input": False,
                        "personality_bins_used": bool(include_context and "personality" in calibration_context),
                        "age_bins_used": bool(include_context and "age" in calibration_context),
                        "gait_used_as_model_input": False,
                        "encoder_finetuning": False,
                        "raw_audio_scan": False,
                        "raw_video_scan": False,
                        "model_parameters_written": False,
                    }
                )
                if model_name == PROPOSED_MODEL:
                    proposed_details = (model, design_columns, train_context, heldout_context, probabilities)

            if proposed_details is not None:
                model, design_columns, train_context, heldout_context, actual_probabilities = proposed_details
                age_context = swapped_age_context(heldout_context)
                age_prob = counterfactual_probabilities(
                    model,
                    design_columns,
                    train_context,
                    age_context,
                    heldout_av_probabilities,
                )
                add_counterfactual_rows(
                    counterfactual_rows,
                    heldout,
                    actual_probabilities,
                    age_prob,
                    seed,
                    fold,
                    "age_group_swap",
                )
                personality_context = personality_counterfactual_context(heldout_context, train_context, seed, fold)
                personality_prob = counterfactual_probabilities(
                    model,
                    design_columns,
                    train_context,
                    personality_context,
                    heldout_av_probabilities,
                )
                add_counterfactual_rows(
                    counterfactual_rows,
                    heldout,
                    actual_probabilities,
                    personality_prob,
                    seed,
                    fold,
                    "personality_bin_swap",
                )

            audit_rows.append(
                {
                    "audit_level": "outer_split",
                    "model": "split_contract",
                    "seed": int(seed),
                    "outer_fold": int(fold),
                    "inner_fold": None,
                    "train_subjects": int(len(train_subjects)),
                    "heldout_subjects": int(len(heldout_subjects)),
                    "subject_overlap_count": int(len(overlap)),
                    "outer_train_subjects": int(len(train_subjects)),
                    "outer_heldout_subjects": int(len(heldout_subjects)),
                    "outer_subject_overlap_count": int(len(overlap)),
                    "input_contract": "labeled_train_subjects_only",
                    "calibration_context": "split_audit",
                    "raw_text_used_for_model_input": False,
                    "encoder_finetuning": False,
                    "raw_audio_scan": False,
                    "raw_video_scan": False,
                    "model_parameters_written": False,
                }
            )

    return pd.DataFrame(predictions), pd.DataFrame(audit_rows), pd.DataFrame(counterfactual_rows)


def metric_tables(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for (model, seed), group in predictions.groupby(["model", "seed"], sort=False):
        metrics = compute_metrics(group, "ordinal_prediction")
        for metric in REQUIRED_METRICS:
            rows.append(
                {
                    "run_id": RUN_ID,
                    "dataset": DATASET_DISPLAY,
                    "target": "phq9_severity_label",
                    "model": str(model),
                    "seed": int(seed),
                    "metric": metric,
                    "value": metrics.get(metric),
                    "sample_count": int(len(group)),
                    "subject_count": int(group["subject_id"].nunique()),
                }
            )
    by_seed = pd.DataFrame(rows)
    summary_rows: list[dict[str, Any]] = []
    for (run_id, dataset, target, model, metric), group in by_seed.groupby(
        ["run_id", "dataset", "target", "model", "metric"],
        sort=False,
        dropna=False,
    ):
        values = [safe_float(value) for value in group["value"]]
        values = [value for value in values if value is not None]
        if not values:
            continue
        summary_rows.append(
            {
                "run_id": run_id,
                "dataset": dataset,
                "target": target,
                "model": model,
                "metric": metric,
                "mean": safe_float(float(np.mean(values))),
                "std": safe_float(float(np.std(values, ddof=0))),
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(float(np.mean(group["sample_count"].astype(float)))),
                "subject_count_mean": safe_float(float(np.mean(group["subject_count"].astype(float)))),
            }
        )
    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary["model"] = pd.Categorical(summary["model"], MODEL_ORDER, ordered=True)
        summary = summary.sort_values(["model", "metric"]).reset_index(drop=True)
        summary["model"] = summary["model"].astype(str)
    return by_seed, summary


def subgroup_metric_tables(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_specs = [("age_group", "age_group"), ("financial_stress_bin", "financial_stress_bin")]
    group_specs.extend((f"personality_{trait}_bin", f"{trait}_bin") for trait in TRAITS)
    metric_rows: list[dict[str, Any]] = []
    for group_type, column in group_specs:
        if column not in predictions.columns:
            continue
        for (model, seed, group_value), group in predictions.groupby(["model", "seed", column], dropna=False):
            group_value = str(group_value)
            if group_value in {"nan", "None", "", "missing"}:
                continue
            metrics = compute_metrics(group, "ordinal_prediction")
            for metric in REQUIRED_METRICS:
                metric_rows.append(
                    {
                        "run_id": RUN_ID,
                        "dataset": DATASET_DISPLAY,
                        "target": "phq9_severity_label",
                        "model": str(model),
                        "seed": int(seed),
                        "group_type": group_type,
                        "group_value": group_value,
                        "metric": metric,
                        "value": metrics.get(metric),
                        "sample_count": int(len(group)),
                        "subject_count": int(group["subject_id"].nunique()),
                    }
                )
    by_seed = pd.DataFrame(metric_rows)
    summary_rows: list[dict[str, Any]] = []
    summary_keys = ["run_id", "dataset", "target", "model", "group_type", "group_value", "metric"]
    for key, group in by_seed.groupby(summary_keys, sort=False, dropna=False):
        values = [safe_float(value) for value in group["value"]]
        values = [value for value in values if value is not None]
        if not values:
            continue
        summary_rows.append(
            {
                **dict(zip(summary_keys, key, strict=True)),
                "mean": safe_float(float(np.mean(values))),
                "std": safe_float(float(np.std(values, ddof=0))),
                "seed_count": int(len(values)),
                "sample_count_mean": safe_float(float(np.mean(group["sample_count"].astype(float)))),
                "subject_count_mean": safe_float(float(np.mean(group["subject_count"].astype(float)))),
            }
        )
    summary = pd.DataFrame(summary_rows)
    gap_rows: list[dict[str, Any]] = []
    if not summary.empty:
        for (model, group_type, metric), group in summary.groupby(["model", "group_type", "metric"], dropna=False):
            if group["group_value"].nunique() < 2:
                continue
            ordered = group.sort_values("mean")
            low = ordered.iloc[0]
            high = ordered.iloc[-1]
            gap_rows.append(
                {
                    "run_id": RUN_ID,
                    "dataset": DATASET_DISPLAY,
                    "target": "phq9_severity_label",
                    "model": str(model),
                    "group_type": str(group_type),
                    "metric": str(metric),
                    "min_group": str(low["group_value"]),
                    "min_mean": safe_float(low["mean"]),
                    "max_group": str(high["group_value"]),
                    "max_mean": safe_float(high["mean"]),
                    "absolute_gap": safe_float(abs(float(high["mean"]) - float(low["mean"]))),
                }
            )
    gaps = pd.DataFrame(gap_rows)
    if not gaps.empty:
        gaps["model"] = pd.Categorical(gaps["model"], MODEL_ORDER, ordered=True)
        gaps = gaps.sort_values(["metric", "group_type", "model"]).reset_index(drop=True)
        gaps["model"] = gaps["model"].astype(str)
    return by_seed, summary, gaps


def context_control_summary(metric_summary: pd.DataFrame, subgroup_gaps: pd.DataFrame) -> pd.DataFrame:
    metric_lookup = metric_summary.set_index(["model", "metric"])["mean"].to_dict()
    gap_lookup = subgroup_gaps.set_index(["model", "group_type", "metric"])["absolute_gap"].to_dict() if not subgroup_gaps.empty else {}
    rows: list[dict[str, Any]] = []
    for model in MODEL_ORDER:
        for metric in REQUIRED_METRICS:
            current = metric_lookup.get((model, metric))
            baseline = metric_lookup.get((BASELINE_MODEL, metric))
            prob_only = metric_lookup.get((AV_PROB_MODEL, metric))
            proposed = metric_lookup.get((PROPOSED_MODEL, metric))
            rows.append(
                {
                    "summary_type": "overall_metric",
                    "model": model,
                    "metric": metric,
                    "value": safe_float(current),
                    "delta_vs_av_baseline": safe_float(current - baseline)
                    if current is not None and baseline is not None
                    else None,
                    "delta_vs_av_probability_recalibrated": safe_float(current - prob_only)
                    if current is not None and prob_only is not None
                    else None,
                    "delta_vs_proposed_context": safe_float(current - proposed)
                    if current is not None and proposed is not None
                    else None,
                }
            )
    for group_type in ["age_group", *[f"personality_{trait}_bin" for trait in TRAITS], "financial_stress_bin"]:
        for model in MODEL_ORDER:
            current = gap_lookup.get((model, group_type, "ECE"))
            baseline = gap_lookup.get((BASELINE_MODEL, group_type, "ECE"))
            prob_only = gap_lookup.get((AV_PROB_MODEL, group_type, "ECE"))
            proposed = gap_lookup.get((PROPOSED_MODEL, group_type, "ECE"))
            rows.append(
                {
                    "summary_type": "subgroup_ece_gap",
                    "model": model,
                    "metric": f"{group_type}_ECE_gap",
                    "value": safe_float(current),
                    "delta_vs_av_baseline": safe_float(current - baseline)
                    if current is not None and baseline is not None
                    else None,
                    "delta_vs_av_probability_recalibrated": safe_float(current - prob_only)
                    if current is not None and prob_only is not None
                    else None,
                    "delta_vs_proposed_context": safe_float(current - proposed)
                    if current is not None and proposed is not None
                    else None,
                }
            )
    return pd.DataFrame(rows)


def summarize_counterfactual(counterfactual: pd.DataFrame) -> pd.DataFrame:
    if counterfactual.empty:
        return pd.DataFrame(
            columns=[
                "counterfactual_type",
                "age_group",
                "metric",
                "mean",
                "std",
                "seed_count",
                "subject_count_mean",
            ]
        )
    rows: list[dict[str, Any]] = []
    per_seed_rows: list[dict[str, Any]] = []
    for (counterfactual_type, seed, age_group), group in counterfactual.groupby(
        ["counterfactual_type", "seed", "age_group"],
        dropna=False,
    ):
        delta = group["delta_expected_severity"].astype(float)
        per_seed_rows.extend(
            [
                {
                    "counterfactual_type": str(counterfactual_type),
                    "seed": int(seed),
                    "age_group": str(age_group),
                    "metric": "changed_pred_rate",
                    "value": safe_float(float(group["changed_pred"].astype(bool).mean())),
                    "subject_count": int(group["subject_id"].nunique()),
                },
                {
                    "counterfactual_type": str(counterfactual_type),
                    "seed": int(seed),
                    "age_group": str(age_group),
                    "metric": "mean_delta_expected_severity",
                    "value": safe_float(float(delta.mean())),
                    "subject_count": int(group["subject_id"].nunique()),
                },
                {
                    "counterfactual_type": str(counterfactual_type),
                    "seed": int(seed),
                    "age_group": str(age_group),
                    "metric": "mean_abs_delta_expected_severity",
                    "value": safe_float(float(delta.abs().mean())),
                    "subject_count": int(group["subject_id"].nunique()),
                },
            ]
        )
    per_seed = pd.DataFrame(per_seed_rows)
    for (counterfactual_type, age_group, metric), group in per_seed.groupby(
        ["counterfactual_type", "age_group", "metric"],
        dropna=False,
    ):
        values = [safe_float(value) for value in group["value"]]
        values = [value for value in values if value is not None]
        if not values:
            continue
        rows.append(
            {
                "counterfactual_type": str(counterfactual_type),
                "age_group": str(age_group),
                "metric": str(metric),
                "mean": safe_float(float(np.mean(values))),
                "std": safe_float(float(np.std(values, ddof=0))),
                "seed_count": int(len(values)),
                "subject_count_mean": safe_float(float(np.mean(group["subject_count"].astype(float)))),
            }
        )
    return pd.DataFrame(rows)


def cohort_context_summary(subjects: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_specs: list[tuple[str, str | None]] = [
        ("overall", None),
        ("age_group", "age_group"),
        ("financial_stress_bin", "financial_stress_bin"),
    ]
    group_specs.extend((f"personality_{trait}_bin", f"{trait}_bin") for trait in TRAITS)
    for group_type, column in group_specs:
        groups = [("all", subjects)] if column is None else list(subjects.groupby(column, dropna=False))
        for group_value, group in groups:
            group_value = str(group_value)
            if group_value in {"nan", "None", "", "missing"}:
                continue
            severity_counts = group["severity_label"].astype(int).value_counts().sort_index()
            rows.append(
                {
                    "group_type": group_type,
                    "group_value": group_value,
                    "subject_count": int(group["subject_id"].nunique()),
                    "phq9_total_mean": safe_float(float(group["phq9_total"].mean())),
                    "phq9_total_std": safe_float(float(group["phq9_total"].std(ddof=0))),
                    "binary_positive_rate": safe_float(float(group["binary_label"].astype(float).mean())),
                    "severity_0_count": int(severity_counts.get(0, 0)),
                    "severity_1_count": int(severity_counts.get(1, 0)),
                    "severity_2_count": int(severity_counts.get(2, 0)),
                }
            )
    return pd.DataFrame(rows)


def prediction_error_frame(predictions: pd.DataFrame, model_name: str) -> pd.DataFrame:
    subset = predictions[predictions["model"].eq(model_name)].copy()
    expected_values: list[float | None] = []
    for value in subset["y_prob"]:
        probs = parse_probability_vector(value)
        if probs is None:
            expected_values.append(None)
        else:
            expected_values.append(float(np.dot(np.asarray(probs, dtype=float), np.asarray(CLASS_LABELS, dtype=float))))
    subset["expected_severity"] = expected_values
    subset["abs_error"] = (subset["expected_severity"].astype(float) - subset["y_true"].astype(float)).abs()
    return subset[["subject_id", "seed", "fold", "expected_severity", "abs_error", "y_true", "y_pred"]]


def gait_psychomotor_context_summary(
    subjects: pd.DataFrame,
    predictions: pd.DataFrame,
    gait_top_n: int,
) -> pd.DataFrame:
    gait = p3.build_gait_feature_frame(subjects)
    if gait.empty:
        return pd.DataFrame(
            [
                {
                    "summary_type": "availability",
                    "metric": "gait_subjects",
                    "feature": "all",
                    "value": 0,
                    "abs_value": 0,
                    "subject_count": 0,
                    "notes": "no gait rows available",
                }
            ]
        )
    rows: list[dict[str, Any]] = []
    feature_cols = [
        column
        for column in gait.columns
        if column not in {"subject_id", "age_group", "severity_label", "binary_label", "phq9_total"}
    ]
    for target in ["phq9_total", "severity_label", "binary_label"]:
        for feature in feature_cols:
            value = spearman(gait[target], gait[feature])
            if value is None:
                continue
            rows.append(
                {
                    "summary_type": "gait_target_correlation",
                    "metric": f"spearman_with_{target}",
                    "feature": feature,
                    "value": safe_float(value),
                    "abs_value": abs(float(value)),
                    "subject_count": int(gait["subject_id"].nunique()),
                    "notes": "gait summary is context validation only, not a model input",
                }
            )
    for model in [BASELINE_MODEL, PROPOSED_MODEL]:
        errors = prediction_error_frame(predictions, model)
        per_subject = (
            errors.groupby("subject_id", as_index=False)
            .agg(abs_error=("abs_error", "mean"), expected_severity=("expected_severity", "mean"))
        )
        joined = gait.merge(per_subject, on="subject_id", how="inner")
        if joined.empty:
            continue
        for error_target in ["abs_error", "expected_severity"]:
            for feature in feature_cols:
                value = spearman(joined[error_target], joined[feature])
                if value is None:
                    continue
                rows.append(
                    {
                        "summary_type": "gait_prediction_diagnostic",
                        "metric": f"{model}_{error_target}_spearman",
                        "feature": feature,
                        "value": safe_float(value),
                        "abs_value": abs(float(value)),
                        "subject_count": int(joined["subject_id"].nunique()),
                        "notes": "gait summary is context validation only, not a model input",
                    }
                )
    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    return (
        summary.sort_values(["summary_type", "metric", "abs_value"], ascending=[True, True, False])
        .groupby(["summary_type", "metric"], as_index=False)
        .head(gait_top_n)
        .reset_index(drop=True)
    )


def diagnostic_availability(subjects: pd.DataFrame, audio_columns: list[str], video_columns: list[str]) -> pd.DataFrame:
    rows = [
        {
            "diagnostic": "labeled_train_subjects",
            "status": "available",
            "usable_subjects": int(subjects["subject_id"].nunique()),
            "notes": "MPDD official train rows with PHQ-9 total, severity, and binary labels",
        },
        {
            "diagnostic": "audio_video_baseline",
            "status": "available",
            "usable_subjects": int(subjects["subject_id"].nunique()),
            "notes": f"cached WavLM columns={len(audio_columns)}; cached ResNet columns={len(video_columns)}",
        },
        {
            "diagnostic": "age_group_calibration",
            "status": "available",
            "usable_subjects": int(subjects["age_group"].ne("missing").sum()),
            "notes": "age group is used only as a context calibration/subgroup axis",
        },
        {
            "diagnostic": "personality_bin_calibration",
            "status": "available",
            "usable_subjects": int(subjects["personality_available"].sum()),
            "notes": "personality text is parsed in memory into bins; raw text is never written",
        },
        {
            "diagnostic": "gait_psychomotor_context_validation",
            "status": "available",
            "usable_subjects": int(subjects["gait_available"].sum()),
            "notes": "gait summaries are diagnostics only and are not model inputs",
        },
        {
            "diagnostic": "gender_subgroup_calibration",
            "status": "blocked",
            "usable_subjects": int(subjects["gender_group"].ne("missing").sum()),
            "notes": "structured gender metadata is empty in the MPDD manifest",
        },
        {
            "diagnostic": "health_subgroup_calibration",
            "status": "blocked",
            "usable_subjects": int(subjects["health_group"].ne("missing").sum()),
            "notes": "structured health_condition metadata is empty in the MPDD manifest",
        },
    ]
    return pd.DataFrame(rows)


def feature_availability(
    subjects: pd.DataFrame,
    audio_columns: list[str],
    video_columns: list[str],
    inventory: list[dict[str, Any]],
) -> pd.DataFrame:
    rows = []
    for item in inventory:
        rows.append(
            {
                "artifact": item["artifact"],
                "source_scope": item["source_scope"],
                "row_count": int(item["row_count"]),
                "joined_subjects": int(subjects["subject_id"].nunique()),
                "feature_count": int(item["feature_count"]),
                "new_encoder_extraction": False,
            }
        )
    rows.append(
        {
            "artifact": "calibration_context_bins",
            "source_scope": "manifest_train_rows_in_memory",
            "row_count": int(subjects["subject_id"].nunique()),
            "joined_subjects": int(subjects["subject_id"].nunique()),
            "feature_count": int(len(CONTEXT_COLUMNS)),
            "new_encoder_extraction": False,
        }
    )
    rows.append(
        {
            "artifact": "audio_video_feature_union",
            "source_scope": "derived_from_cached_phase2_subject_features",
            "row_count": int(subjects["subject_id"].nunique()),
            "joined_subjects": int(subjects["subject_id"].nunique()),
            "feature_count": int(len(audio_columns) + len(video_columns)),
            "new_encoder_extraction": False,
        }
    )
    return pd.DataFrame(rows)


def metric_lookup(frame: pd.DataFrame) -> dict[tuple[str, str], float]:
    return frame.set_index(["model", "metric"])["mean"].to_dict() if not frame.empty else {}


def ece_gap_lookup(frame: pd.DataFrame) -> dict[tuple[str, str], float]:
    if frame.empty:
        return {}
    subset = frame[frame["metric"].eq("ECE")].copy()
    return subset.set_index(["model", "group_type"])["absolute_gap"].to_dict()


def best_personality_ece_gap(gap_values: dict[tuple[str, str], float], model: str) -> float | None:
    values = [
        safe_float(value)
        for (model_name, group_type), value in gap_values.items()
        if model_name == model and (group_type.startswith("personality_") or group_type == "financial_stress_bin")
    ]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def build_verdict(
    metric_summary: pd.DataFrame,
    subgroup_gaps: pd.DataFrame,
    model_audit: pd.DataFrame,
) -> dict[str, Any]:
    metrics = metric_lookup(metric_summary)
    gaps = ece_gap_lookup(subgroup_gaps)
    proposed_ece = metrics.get((PROPOSED_MODEL, "ECE"))
    baseline_ece = metrics.get((BASELINE_MODEL, "ECE"))
    prob_ece = metrics.get((AV_PROB_MODEL, "ECE"))
    shuffled_personality_ece = metrics.get((SHUFFLED_PERSONALITY_MODEL, "ECE"))
    context_only_qwk = metrics.get((CONTEXT_ONLY_MODEL, "QWK"))
    proposed_qwk = metrics.get((PROPOSED_MODEL, "QWK"))
    baseline_qwk = metrics.get((BASELINE_MODEL, "QWK"))
    proposed_age_gap = gaps.get((PROPOSED_MODEL, "age_group"))
    baseline_age_gap = gaps.get((BASELINE_MODEL, "age_group"))
    prob_age_gap = gaps.get((AV_PROB_MODEL, "age_group"))
    shuffled_age_gap = gaps.get((SHUFFLED_AGE_MODEL, "age_group"))
    proposed_personality_gap = best_personality_ece_gap(gaps, PROPOSED_MODEL)
    baseline_personality_gap = best_personality_ece_gap(gaps, BASELINE_MODEL)
    prob_personality_gap = best_personality_ece_gap(gaps, AV_PROB_MODEL)
    shuffled_personality_gap = best_personality_ece_gap(gaps, SHUFFLED_PERSONALITY_MODEL)

    subject_overlap_violations = int(
        model_audit.get("subject_overlap_count", pd.Series(dtype=int)).fillna(0).astype(int).sum()
    ) + int(model_audit.get("outer_subject_overlap_count", pd.Series(dtype=int)).fillna(0).astype(int).sum())
    context_only_close = bool(
        proposed_qwk is not None and context_only_qwk is not None and context_only_qwk >= proposed_qwk - 0.02
    )
    overall_ece_not_worse = bool(
        proposed_ece is not None
        and baseline_ece is not None
        and proposed_ece <= baseline_ece + 0.01
    )
    age_gap_improved = bool(
        proposed_age_gap is not None
        and baseline_age_gap is not None
        and proposed_age_gap < baseline_age_gap
        and (prob_age_gap is None or proposed_age_gap <= prob_age_gap + 0.01)
    )
    personality_gap_improved = bool(
        proposed_personality_gap is not None
        and baseline_personality_gap is not None
        and proposed_personality_gap < baseline_personality_gap
        and (prob_personality_gap is None or proposed_personality_gap <= prob_personality_gap + 0.01)
    )
    shuffled_personality_unchanged = bool(
        proposed_ece is not None
        and shuffled_personality_ece is not None
        and abs(proposed_ece - shuffled_personality_ece) <= 0.005
        and (
            proposed_personality_gap is None
            or shuffled_personality_gap is None
            or abs(proposed_personality_gap - shuffled_personality_gap) <= 0.005
        )
    )
    shuffled_age_unchanged = bool(
        proposed_age_gap is not None
        and shuffled_age_gap is not None
        and abs(proposed_age_gap - shuffled_age_gap) <= 0.005
    )
    main_task_not_collapsed = bool(
        proposed_qwk is not None
        and baseline_qwk is not None
        and proposed_qwk >= baseline_qwk - 0.05
    )
    calibration_gain = bool(overall_ece_not_worse and (age_gap_improved or personality_gap_improved))

    if subject_overlap_violations > 0:
        status = "blocked_subject_overlap"
        short_read = "P5_MV05 is blocked because the model split audit found subject overlap."
    elif not calibration_gain:
        status = "blocked_no_context_calibration_gain"
        short_read = (
            "The MPDD context-calibration row is runnable, but the proposed AV-probability-plus-context calibrator does not improve age/personality subgroup ECE gaps over the AV baseline strongly enough for a positive RQ3 claim."
        )
    elif context_only_close:
        status = "blocked_context_only_shortcut_risk"
        short_read = (
            "The context calibrator improves calibration, but the context-only sanity check is too close to the proposed model, so the result risks relying on context shortcuts rather than AV evidence."
        )
    elif personality_gap_improved and shuffled_personality_unchanged:
        status = "blocked_personality_shuffle_unchanged"
        short_read = (
            "The personality-bin calibration signal is not distinguishable from the shuffled-personality control, so the row cannot support a personality-context mechanism."
        )
    elif age_gap_improved and shuffled_age_unchanged and not personality_gap_improved:
        status = "blocked_shuffled_age_unchanged"
        short_read = (
            "The apparent age calibration gain is not distinguishable from the shuffled-age control."
        )
    elif not main_task_not_collapsed:
        status = "blocked_main_task_degradation"
        short_read = (
            "The context calibrator improves a calibration slice but degrades the main ordinal QWK beyond the minimal tolerance."
        )
    else:
        status = "pass_context_calibration"
        short_read = (
            "The AV-probability-plus-context calibrator improves subgroup calibration while preserving the ordinal task and remaining stronger than context-only and shuffled controls."
        )

    return {
        "pass_rule_status": status,
        "pass_rule_met": status == "pass_context_calibration",
        "short_read": short_read,
        "subject_overlap_violations": int(subject_overlap_violations),
        "overall_ece_baseline": safe_float(baseline_ece),
        "overall_ece_av_probability_recalibrated": safe_float(prob_ece),
        "overall_ece_proposed": safe_float(proposed_ece),
        "overall_ece_shuffled_personality": safe_float(shuffled_personality_ece),
        "qwk_baseline": safe_float(baseline_qwk),
        "qwk_proposed": safe_float(proposed_qwk),
        "qwk_context_only": safe_float(context_only_qwk),
        "age_ece_gap_baseline": safe_float(baseline_age_gap),
        "age_ece_gap_av_probability_recalibrated": safe_float(prob_age_gap),
        "age_ece_gap_proposed": safe_float(proposed_age_gap),
        "age_ece_gap_shuffled_age": safe_float(shuffled_age_gap),
        "personality_ece_gap_baseline_max": safe_float(baseline_personality_gap),
        "personality_ece_gap_av_probability_recalibrated_max": safe_float(prob_personality_gap),
        "personality_ece_gap_proposed_max": safe_float(proposed_personality_gap),
        "personality_ece_gap_shuffled_personality_max": safe_float(shuffled_personality_gap),
        "overall_ece_not_worse": overall_ece_not_worse,
        "age_gap_improved": age_gap_improved,
        "personality_gap_improved": personality_gap_improved,
        "context_only_close_to_proposed": context_only_close,
        "shuffled_personality_unchanged": shuffled_personality_unchanged,
        "shuffled_age_unchanged": shuffled_age_unchanged,
        "main_task_not_collapsed": main_task_not_collapsed,
    }


def markdown_table(frame: pd.DataFrame, max_rows: int | None = None) -> str:
    if frame.empty:
        return "_No rows available._"
    display = frame.copy()
    if max_rows is not None:
        display = display.head(max_rows)
    columns = [str(column) for column in display.columns]

    def render(value: Any) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.4f}"
        return str(value).replace("\n", " ")

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in display.iterrows():
        lines.append("| " + " | ".join(render(row[column]) for column in display.columns) + " |")
    return "\n".join(lines)


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    metric_summary: pd.DataFrame,
    context_summary: pd.DataFrame,
    subgroup_gaps: pd.DataFrame,
    counter_summary: pd.DataFrame,
    gait_summary: pd.DataFrame,
) -> None:
    metrics = metric_summary[metric_summary["metric"].isin(REQUIRED_METRICS)].copy()
    pivot = metrics.pivot(index="model", columns="metric", values="mean").reindex(MODEL_ORDER).reset_index()
    selected_context = context_summary[
        context_summary["metric"].isin(
            [
                "ECE",
                "Brier Score",
                "age_group_ECE_gap",
                "personality_neuroticism_bin_ECE_gap",
                "personality_conscientiousness_bin_ECE_gap",
                "financial_stress_bin_ECE_gap",
            ]
        )
    ].copy()
    selected_gaps = subgroup_gaps[
        subgroup_gaps["metric"].eq("ECE")
        & subgroup_gaps["model"].isin([BASELINE_MODEL, AV_PROB_MODEL, PROPOSED_MODEL])
    ].sort_values("absolute_gap", ascending=False)
    selected_gait = gait_summary.sort_values("abs_value", ascending=False).head(12) if not gait_summary.empty else gait_summary
    verdict = run_summary["verdict"]
    lines = [
        "# P5_MV05 MPDD Context Calibration",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This row tests MPDD RQ3 context calibration on labeled train subjects only. The baseline is a frozen WavLM-audio plus ResNet-video ordinal severity classifier. The proposed mechanism is a second-stage calibrator whose primary inputs are fold-local AV probabilities/logits; age group and personality bins are allowed only as calibration context. It is not generic AVP concatenation: raw AV features train the baseline only, and raw personality text is never a model input or output.",
        "",
        "## Feature And Split Contract",
        "",
        f"- Labeled MPDD train subjects: `{run_summary['split_audit']['labeled_train_subjects']}`.",
        f"- Repeated OOF policy: `{run_summary['split_audit']['repeated_oof_policy']}`.",
        f"- Subject-overlap violations: `{run_summary['split_audit']['subject_overlap_violations']}`.",
        f"- MPDD test labels used: `{run_summary['split_audit']['mpdd_test_labels_used']}`.",
        f"- AV feature columns: `{run_summary['feature_contract']['audio_feature_count']}` WavLM + `{run_summary['feature_contract']['video_feature_count']}` ResNet.",
        f"- Context columns: `{', '.join(run_summary['feature_contract']['context_columns'])}`.",
        "",
        "## Main Metrics",
        "",
        markdown_table(pivot.round(4)),
        "",
        "## Context Controls",
        "",
        markdown_table(selected_context.round(4), max_rows=40),
        "",
        "## Subgroup ECE Gaps",
        "",
        markdown_table(selected_gaps[["model", "group_type", "min_group", "max_group", "absolute_gap"]].round(4), max_rows=24),
        "",
        "## Counterfactual Sensitivity",
        "",
        markdown_table(counter_summary.round(4)),
        "",
        "## Gait Psychomotor Context",
        "",
        markdown_table(selected_gait[["summary_type", "metric", "feature", "value", "subject_count"]].round(4), max_rows=12)
        if not selected_gait.empty
        else "_No gait diagnostic rows available._",
        "",
        "## Verdict",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- Baseline/proposed ECE: `{format_value(verdict['overall_ece_baseline'])}` -> `{format_value(verdict['overall_ece_proposed'])}`.",
        f"- Baseline/proposed QWK: `{format_value(verdict['qwk_baseline'])}` -> `{format_value(verdict['qwk_proposed'])}`.",
        f"- Age ECE gap baseline/proposed: `{format_value(verdict['age_ece_gap_baseline'])}` -> `{format_value(verdict['age_ece_gap_proposed'])}`.",
        f"- Personality ECE gap max baseline/proposed: `{format_value(verdict['personality_ece_gap_baseline_max'])}` -> `{format_value(verdict['personality_ece_gap_proposed_max'])}`.",
        "",
        verdict["short_read"],
        "",
        "## Hygiene",
        "",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "- Subject-level prediction and counterfactual prediction rows are local-only ignored CSVs.",
        "- Cached feature matrices are read but not copied into this output directory.",
        "- Source media, source paths, personality descriptions, learned embeddings, model weights, and motion arrays are not written.",
    ]
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene_audit(out_dir: Path, local_only_files: list[str]) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/autodl-tmp/datasets/",
        r"audio_path",
        r"video_path",
        r"text_path",
        r"gait_path",
        r"personality_text",
        r"personality_hash",
        r"\.wav\b",
        r"\.WAV\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"\.npy\b",
        r"The patient has",
        r"personalized_descriptions",
        r"raw prompt",
        r"raw response",
    ]
    local_only_set = set(local_only_files)
    violations: list[dict[str, Any]] = []
    tracked_policy_violations: list[dict[str, Any]] = []
    files_checked = 0
    tracked_files_checked = 0
    for path in sorted(out_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(out_dir))
        if path.suffix.lower() not in {".csv", ".json", ".md", ".txt"}:
            continue
        files_checked += 1
        is_local_only = relative in local_only_set or "predictions" in path.name
        if not is_local_only:
            tracked_files_checked += 1
            lowered = path.name.lower()
            if "prediction" in lowered or "counterfactual_rows" in lowered:
                tracked_policy_violations.append(
                    {"file": relative, "reason": "row-level prediction-like artifact is not local-only"}
                )
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text):
                violations.append({"file": relative, "pattern": pattern})
    return {
        "audit_id": "P5_MV05_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": files_checked,
        "tracked_files_checked": tracked_files_checked,
        "forbidden_content_violation_count": len(violations),
        "tracked_policy_violation_count": len(tracked_policy_violations),
        "violations": violations,
        "tracked_policy_violations": tracked_policy_violations,
        "artifact_hygiene_passed": len(violations) == 0 and len(tracked_policy_violations) == 0,
        "tracked_output_assertions": {
            "raw_personality_descriptions_in_tracked_outputs": False,
            "raw_source_paths_in_tracked_outputs": False,
            "row_level_predictions_in_tracked_outputs": False,
            "large_embeddings_in_tracked_outputs": False,
            "model_weights_in_tracked_outputs": False,
            "raw_audio_video_or_motion_arrays_in_tracked_outputs": False,
        },
        "local_only_patterns": [
            "analysis/phase5_minimal_validation/**/*predictions*.csv",
            "analysis/phase5_minimal_validation/**/*features*.csv",
            "analysis/phase5_minimal_validation/**/*embeddings*.csv",
            "analysis/phase5_minimal_validation/**/*model*.joblib",
            "analysis/phase5_minimal_validation/**/*model*.pkl",
            "analysis/phase5_minimal_validation/**/*weights*.csv",
        ],
    }


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--gait-top-n", type=int, default=8)
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    subjects = p3.read_manifest_subjects(args.manifest)
    model_table, audio_columns, video_columns, feature_inventory = p3.build_model_table(subjects)
    predictions, model_audit, counterfactual_rows = run_experiment(model_table, audio_columns, video_columns)
    metrics_by_seed, metric_summary = metric_tables(predictions)
    subgroup_by_seed, subgroup_summary, subgroup_gaps = subgroup_metric_tables(predictions)
    controls = context_control_summary(metric_summary, subgroup_gaps)
    counter_summary = summarize_counterfactual(counterfactual_rows)
    cohort_summary = cohort_context_summary(subjects)
    gait_summary = gait_psychomotor_context_summary(subjects, predictions, args.gait_top_n)
    availability = diagnostic_availability(subjects, audio_columns, video_columns)
    features = feature_availability(subjects, audio_columns, video_columns, feature_inventory)
    verdict = build_verdict(metric_summary, subgroup_gaps, model_audit)

    local_only_files = [
        "p5_mv05_local_predictions.csv",
        "p5_mv05_local_counterfactual_predictions.csv",
    ]
    predictions.to_csv(out_dir / local_only_files[0], index=False)
    counterfactual_rows.to_csv(out_dir / local_only_files[1], index=False)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    subgroup_by_seed.to_csv(out_dir / "subgroup_metrics_by_seed.csv", index=False)
    subgroup_summary.to_csv(out_dir / "subgroup_metric_summary.csv", index=False)
    subgroup_gaps.to_csv(out_dir / "subgroup_gap_summary.csv", index=False)
    controls.to_csv(out_dir / "context_control_summary.csv", index=False)
    counter_summary.to_csv(out_dir / "counterfactual_sensitivity_summary.csv", index=False)
    cohort_summary.to_csv(out_dir / "cohort_context_summary.csv", index=False)
    gait_summary.to_csv(out_dir / "gait_psychomotor_context_summary.csv", index=False)
    availability.to_csv(out_dir / "diagnostic_availability.csv", index=False)
    features.to_csv(out_dir / "feature_availability.csv", index=False)
    model_audit.to_csv(out_dir / "model_split_audit.csv", index=False)

    age_counts = subjects["age_group"].value_counts(dropna=False).sort_index().to_dict()
    personality_counts = {
        trait: {
            str(key): int(value)
            for key, value in subjects[f"{trait}_bin"].value_counts(dropna=False).sort_index().items()
        }
        for trait in TRAITS
    }
    gender_non_missing = int(subjects["gender_group"].ne("missing").sum())
    health_non_missing = int(subjects["health_group"].ne("missing").sum())
    split_subjects = set(subjects["subject_id"].astype(str))
    test_label_rows = pd.read_csv(args.manifest, usecols=["subject_id", "official_split", "severity_label"])
    labeled_test_subjects = test_label_rows[
        test_label_rows["official_split"].astype(str).eq("test") & test_label_rows["severity_label"].notna()
    ]["subject_id"].astype(str)
    run_summary: dict[str, Any] = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "status": "complete",
        "dataset": DATASET_DISPLAY,
        "feature_contract": {
            "audio_feature_space": "frozen_wavlm_subject_features",
            "video_feature_space": "frozen_resnet_video_subject_features",
            "audio_feature_count": int(len(audio_columns)),
            "video_feature_count": int(len(video_columns)),
            "phase2_cache_scopes": sorted({item["source_scope"] for item in feature_inventory}),
            "new_encoder_extraction": False,
            "context_columns": CONTEXT_COLUMNS,
            "raw_personality_descriptions_written": False,
            "personality_description_hashes_written": False,
            "gait_used_as_model_input": False,
        },
        "target_contract": {
            "target": "phq9_severity_label",
            "source_scale": "PHQ-9",
            "ordinal_classes": CLASS_LABELS,
            "phq9_total_available_for_context_profile": True,
        },
        "model_contract": {
            "baseline": BASELINE_MODEL,
            "proposed": PROPOSED_MODEL,
            "controls": [AV_PROB_MODEL, SHUFFLED_PERSONALITY_MODEL, SHUFFLED_AGE_MODEL, CONTEXT_ONLY_MODEL],
            "seeds": SEEDS,
            "outer_folds": 5,
            "inner_folds_for_calibrator_av_probabilities": 5,
            "proposed_is_calibration_context_not_avp_concatenation": True,
            "proposed_primary_inputs": "AV probabilities/logits from fold-local frozen AV baseline",
            "context_inputs": "age group and personality bins only",
            "raw_personality_descriptions_model_input": False,
            "age_or_personality_direct_av_bypass": False,
            "encoder_finetuning": False,
            "model_weights_written": False,
        },
        "split_audit": {
            "subject_level": True,
            "repeated_oof_policy": "5 seeds x stratified 5-fold over labeled MPDD train subjects",
            "labeled_train_subjects": int(len(split_subjects)),
            "mpdd_test_labels_used": False,
            "labeled_test_subjects_seen_by_training": 0,
            "manifest_labeled_test_subjects_available": int(labeled_test_subjects.nunique()),
            "subject_overlap_violations": int(verdict["subject_overlap_violations"]),
        },
        "subgroup_contract": {
            "age_group_counts": {str(key): int(value) for key, value in age_counts.items()},
            "personality_trait_bin_counts": personality_counts,
            "gender_status": "blocked_empty_manifest_field" if gender_non_missing == 0 else "available",
            "gender_non_missing_subjects": gender_non_missing,
            "health_status": "blocked_empty_manifest_field" if health_non_missing == 0 else "available",
            "health_non_missing_subjects": health_non_missing,
        },
        "output_policy": {
            "row_level_predictions": "local_only_ignored",
            "counterfactual_rows": "local_only_ignored",
            "learned_embeddings": "not_written",
            "model_weights": "not_written",
            "raw_personality_descriptions": "not_written",
            "raw_audio": "not_written",
            "raw_video": "not_written",
            "raw_motion_arrays": "not_written",
            "source_paths": "not_written",
        },
        "artifact_hygiene_passed": False,
        "verdict": verdict,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "metric_summary.csv",
            "metrics_by_seed.csv",
            "subgroup_metric_summary.csv",
            "subgroup_metrics_by_seed.csv",
            "subgroup_gap_summary.csv",
            "context_control_summary.csv",
            "counterfactual_sensitivity_summary.csv",
            "cohort_context_summary.csv",
            "gait_psychomotor_context_summary.csv",
            "diagnostic_availability.csv",
            "feature_availability.csv",
            "model_split_audit.csv",
        ],
        "local_only_files": local_only_files,
    }
    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, metric_summary, controls, subgroup_gaps, counter_summary, gait_summary)
    hygiene = artifact_hygiene_audit(out_dir, local_only_files)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, metric_summary, controls, subgroup_gaps, counter_summary, gait_summary)
    write_json(out_dir / "artifact_hygiene_audit.json", hygiene)
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(f"Wrote P5_MV05 MPDD context calibration to {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
