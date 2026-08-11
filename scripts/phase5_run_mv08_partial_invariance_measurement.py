#!/usr/bin/env python3
"""Run P5_MV08 partial-invariance ordinal measurement pilot.

This is a bounded Phase 5 minimal-validation row, not the full method. It uses
aligned frozen BGE subject features and item labels for E-DAIC PHQ-8, CMDC
PHQ-9, and PDCH HAMD-17, then compares:

- item train means;
- total-score floor with item allocation;
- fixed construct-map heads;
- partial-invariance ordinal heads with shared PHQ anchors and HAMD item DIF.

Row-level predictions stay local-only.
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
from typing import Any, Iterable


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
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv08_partial_invariance_measurement"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
DEFAULT_PHASE2_ROOT = ROOT / "analysis" / "phase2_baselines"
PHASE4_DIR = ROOT / "analysis" / "phase4_symptom_ontology"

RUN_ID = "P5_MV08_partial_invariance_measurement"
SEEDS = [0, 1, 2, 3, 4]
RIDGE_ALPHA_GRID = [0.1, 1.0, 10.0, 100.0, 1000.0]
FEATURE_PREFIX = "bge_"
BOOTSTRAP_RESAMPLES = 200

CORE_CONSTRUCTS = [f"C{idx:02d}" for idx in range(1, 10)]
AUX_CONSTRUCTS = [f"C{idx:02d}" for idx in range(10, 14)]
CONSTRUCTS = CORE_CONSTRUCTS + AUX_CONSTRUCTS
PHQ_SHARED_ANCHOR_CONSTRUCTS = [f"C{idx:02d}" for idx in range(1, 9)]
HAMD_KEYS = [f"HAMD{idx:02d}" for idx in range(1, 18)]
HAMD_CODE_9 = 9.0

LOCAL_PREDICTIONS_NAME = "p5_mv08_local_row_predictions.csv"

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "comparison_summary.csv",
    "construct_target_map.csv",
    "dif_sparsity_summary.csv",
    "identity_probe_by_seed.csv",
    "identity_probe_summary.csv",
    "label_feature_audit.csv",
    "metric_summary.csv",
    "metrics_by_seed.csv",
    "model_split_audit.csv",
    "report.md",
    "run_summary.json",
}


@dataclass(frozen=True)
class BgeFeatureSpec:
    dataset: str
    relative_path: str


@dataclass(frozen=True)
class ItemSpec:
    dataset: str
    scale: str
    item_code: str
    manifest_key: str
    item_label_short: str
    primary_construct: str
    secondary_constructs: tuple[str, ...]
    item_max: int
    mapping_strength: str
    head_group: str
    dif_policy: str

    @property
    def item_id(self) -> str:
        return f"{self.dataset}:{self.scale}:{self.item_code}"


FEATURE_SPECS = {
    "edaic": BgeFeatureSpec("edaic", "edaic_text_bge/edaic_bge_subject_features.csv"),
    "cmdc": BgeFeatureSpec("cmdc", "cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv"),
    "pdch": BgeFeatureSpec("pdch", "cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


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


def spearman(values_true: Iterable[Any], values_pred: Iterable[Any]) -> float | None:
    true = np.asarray(list(values_true), dtype=np.float64)
    pred = np.asarray(list(values_pred), dtype=np.float64)
    mask = np.isfinite(true) & np.isfinite(pred)
    true = true[mask]
    pred = pred[mask]
    if true.size < 3 or len(np.unique(true)) < 2 or len(np.unique(pred)) < 2:
        return None
    true_rank = pd.Series(true).rank(method="average").to_numpy(dtype=np.float64)
    pred_rank = pd.Series(pred).rank(method="average").to_numpy(dtype=np.float64)
    return safe_float(np.corrcoef(true_rank, pred_rank)[0, 1])


def format_value(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def manifest_item_key(row: pd.Series) -> str:
    aliases = clean_value(row.get("project_aliases"))
    if aliases:
        return aliases.split(";")[0]
    return clean_value(row.get("item_code"))


def parse_secondary(value: Any) -> tuple[str, ...]:
    text = clean_value(value)
    if not text:
        return ()
    return tuple(part for part in (clean_value(item) for item in text.split(";")) if part)


def build_item_specs(catalog_path: Path) -> list[ItemSpec]:
    catalog = pd.read_csv(catalog_path)
    rows: list[ItemSpec] = []
    active = [
        ("edaic", "PHQ-8"),
        ("cmdc", "PHQ-9"),
        ("pdch", "HAMD-17"),
    ]
    for dataset, scale in active:
        selected = catalog[catalog["scale"] == scale].copy()
        for _, row in selected.iterrows():
            primary = clean_value(row["primary_construct_id"])
            item_code = clean_value(row["item_code"])
            if not primary:
                continue
            item_max = 3 if scale.startswith("PHQ") else 4
            if scale in {"PHQ-8", "PHQ-9"} and primary in PHQ_SHARED_ANCHOR_CONSTRUCTS:
                head_group = f"shared_phq_{primary}"
                dif_policy = "shared_phq_anchor"
            elif scale == "PHQ-9" and primary == "C09":
                head_group = "phq9_safety_c09"
                dif_policy = "scale_specific_safety"
            else:
                head_group = f"{scale}_{item_code}_dif"
                dif_policy = "scale_or_item_specific_dif"
            rows.append(
                ItemSpec(
                    dataset=dataset,
                    scale=scale,
                    item_code=item_code,
                    manifest_key=manifest_item_key(row),
                    item_label_short=clean_value(row["item_label_short"]),
                    primary_construct=primary,
                    secondary_constructs=parse_secondary(row.get("secondary_construct_ids")),
                    item_max=item_max,
                    mapping_strength=clean_value(row.get("mapping_strength")),
                    head_group=head_group,
                    dif_policy=dif_policy,
                )
            )
    return sorted(rows, key=lambda spec: (spec.dataset, spec.scale, natural_key(spec.item_code)))


def load_bge_features(phase2_root: Path) -> tuple[dict[str, pd.DataFrame], list[str], pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    column_sets: list[set[str]] = []
    rows: list[dict[str, Any]] = []
    for dataset, spec in FEATURE_SPECS.items():
        path = phase2_root / spec.relative_path
        if not path.exists():
            raise FileNotFoundError(f"BGE feature cache missing for {dataset}: {path}")
        frame = pd.read_csv(path)
        if "subject_id" not in frame.columns:
            raise ValueError(f"{dataset} BGE cache missing subject_id")
        path_like = [column for column in frame.columns if "path" in column.lower()]
        if path_like:
            raise ValueError(f"{dataset} BGE cache has path-like columns: {path_like[:5]}")
        frame["subject_id"] = frame["subject_id"].astype(str)
        bge_cols = [
            column
            for column in frame.columns
            if column.startswith(FEATURE_PREFIX) and pd.api.types.is_numeric_dtype(frame[column])
        ]
        if not bge_cols:
            raise ValueError(f"{dataset} BGE cache has no numeric {FEATURE_PREFIX} columns")
        bge_cols = sorted(bge_cols, key=natural_key)
        tables[dataset] = frame[["subject_id", *bge_cols]].copy()
        column_sets.append(set(bge_cols))
        rows.append(
            {
                "dataset": dataset,
                "feature_family": "text_bge",
                "feature_ref": spec.relative_path,
                "feature_subjects": int(frame["subject_id"].nunique()),
                "model_input_columns": int(len(bge_cols)),
                "path_like_columns": ";".join(path_like),
            }
        )
    common = sorted(set.intersection(*column_sets), key=natural_key)
    if not common:
        raise ValueError("no common BGE columns across E-DAIC, CMDC, and PDCH")
    return {dataset: table[["subject_id", *common]].copy() for dataset, table in tables.items()}, common, pd.DataFrame(rows)


def payload_items(payload: dict[str, Any], specs: list[ItemSpec]) -> dict[str, float]:
    values: dict[str, float] = {}
    for spec in specs:
        raw = safe_float(payload.get(spec.manifest_key))
        if raw is None:
            continue
        if spec.scale == "HAMD-17" and raw == HAMD_CODE_9:
            continue
        values[spec.item_id] = float(np.clip(raw, 0.0, spec.item_max))
    return values


def active_specs_for(dataset: str, item_specs: list[ItemSpec]) -> list[ItemSpec]:
    return [spec for spec in item_specs if spec.dataset == dataset]


def load_subjects(manifest_dir: Path, features: dict[str, pd.DataFrame], item_specs: list[ItemSpec]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    manifest_specs = [
        ("edaic", "PHQ-8", "edaic_subjects.csv", "phq8_total", "phq8_items", ["subject_id", "file_valid", "official_split", "phq8_total", "phq8_items"]),
        ("cmdc", "PHQ-9", "cmdc_subjects.csv", "phq9_total", "phq9_items", ["subject_id", "file_valid", "phq9_total", "phq9_items"]),
        ("pdch", "HAMD-17", "pdch_subjects.csv", "hamd17_total", "hamd17_items", ["subject_id", "file_valid", "hamd17_total", "hamd17_items"]),
    ]

    for dataset, scale, manifest_name, total_col, item_col, usecols in manifest_specs:
        frame = pd.read_csv(manifest_dir / manifest_name, usecols=usecols)
        frame = frame[bool_series(frame["file_valid"])].copy()
        frame["subject_id"] = frame["subject_id"].astype(str)
        if dataset == "edaic":
            frame = frame[frame["official_split"].astype(str).isin(["train", "dev"])].copy()
        specs = active_specs_for(dataset, item_specs)
        label_subjects = 0
        for subject_id, group in frame.groupby("subject_id", sort=False):
            first = group.iloc[0]
            total = safe_float(first[total_col])
            if total is None:
                continue
            payloads = [read_json_dict(value) for value in group[item_col].tolist()]
            candidate_items = [payload_items(payload, specs) for payload in payloads]
            item_values = max(candidate_items, key=len) if candidate_items else {}
            required = {spec.item_id for spec in specs}
            if not required or not required.issubset(item_values):
                continue
            label_subjects += 1
            rows.append(
                {
                    "dataset": dataset,
                    "scale": scale,
                    "subject_id": str(subject_id),
                    "subject_key": f"{dataset}::{subject_id}",
                    "official_split": clean_value(first.get("official_split")),
                    "total_score": float(total),
                    "item_values": item_values,
                }
            )
        feature_subjects = int(features[dataset]["subject_id"].nunique())
        audit_rows.append(
            {
                "dataset": dataset,
                "scale": scale,
                "label_subjects": int(label_subjects),
                "feature_subjects": feature_subjects,
                "joined_subjects": 0,
                "model_input_columns": int(len([column for column in features[dataset].columns if column.startswith(FEATURE_PREFIX)])),
            }
        )

    subjects = pd.DataFrame(rows)
    merged_frames: list[pd.DataFrame] = []
    for dataset, group in subjects.groupby("dataset", sort=False):
        merged = group.merge(features[dataset], on="subject_id", how="inner", validate="one_to_one")
        merged_frames.append(merged)
        for row in audit_rows:
            if row["dataset"] == dataset:
                row["joined_subjects"] = int(merged["subject_id"].nunique())
    table = pd.concat(merged_frames, ignore_index=True)
    table = table.sort_values(["dataset", "subject_id"], key=lambda s: s.map(lambda x: tuple(natural_key(x)))).reset_index(drop=True)
    return table, pd.DataFrame(audit_rows)


def item_observations(subjects: pd.DataFrame, item_specs: list[ItemSpec]) -> pd.DataFrame:
    spec_by_id = {spec.item_id: spec for spec in item_specs}
    rows: list[dict[str, Any]] = []
    for _, subject in subjects.iterrows():
        for item_id, value in subject["item_values"].items():
            spec = spec_by_id[item_id]
            rows.append(
                {
                    "subject_key": subject["subject_key"],
                    "subject_id": subject["subject_id"],
                    "dataset": subject["dataset"],
                    "scale": subject["scale"],
                    "item_id": item_id,
                    "item_code": spec.item_code,
                    "item_label_short": spec.item_label_short,
                    "construct_id": spec.primary_construct,
                    "secondary_constructs": ";".join(spec.secondary_constructs),
                    "head_group": spec.head_group,
                    "dif_policy": spec.dif_policy,
                    "mapping_strength": spec.mapping_strength,
                    "item_max": int(spec.item_max),
                    "y_true": float(value),
                    "y_true_norm": float(value) / float(spec.item_max),
                }
            )
    return pd.DataFrame(rows)


def load_subject_folds(split_path: Path, dataset: str, protocol_id: str, target: str) -> dict[int, dict[str, set[str]]]:
    splits = pd.read_csv(split_path)
    selected = splits[
        (splits["dataset"].astype(str) == dataset)
        & (splits["protocol_id"].astype(str) == protocol_id)
        & (splits["target"].astype(str) == target)
    ].copy()
    if selected.empty:
        raise ValueError(f"no split rows for {dataset}/{protocol_id}/{target}")
    folds: dict[int, dict[str, set[str]]] = {}
    for idx, fold_name in enumerate(sorted(selected["fold"].astype(str).unique(), key=natural_key)):
        fold = selected[selected["fold"].astype(str) == fold_name]
        train = set(fold.loc[fold["role"].astype(str) == "train", "subject_id"].astype(str))
        validation = set(fold.loc[fold["role"].astype(str) == "validation", "subject_id"].astype(str))
        overlap = train & validation
        if overlap:
            raise ValueError(f"{dataset}/{protocol_id}/{fold_name} train/validation overlap")
        if not train or not validation:
            raise ValueError(f"{dataset}/{protocol_id}/{fold_name} has empty train or validation")
        folds[idx] = {"train": train, "validation": validation, "fold_name": {fold_name}}
    return folds


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def choose_alpha(x: np.ndarray, y: np.ndarray, seed: int) -> float:
    y_arr = np.asarray(y, dtype=np.float64)
    mask = np.all(np.isfinite(y_arr), axis=1) if y_arr.ndim == 2 else np.isfinite(y_arr)
    x_arr = np.asarray(x, dtype=np.float64)[mask]
    y_arr = y_arr[mask]
    if x_arr.shape[0] < 12:
        return 100.0
    n_splits = min(5, max(2, x_arr.shape[0] // 10))
    splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    best_alpha = RIDGE_ALPHA_GRID[0]
    best_mae = float("inf")
    for alpha in RIDGE_ALPHA_GRID:
        scores: list[float] = []
        for train_idx, dev_idx in splitter.split(x_arr):
            model = ridge_pipeline(alpha)
            model.fit(x_arr[train_idx], y_arr[train_idx])
            pred = np.asarray(model.predict(x_arr[dev_idx]), dtype=float)
            scores.append(float(np.mean(np.abs(pred - y_arr[dev_idx]))))
        score = float(np.mean(scores))
        if score < best_mae:
            best_alpha = float(alpha)
            best_mae = score
    return best_alpha


def construct_targets(subjects: pd.DataFrame, item_specs: list[ItemSpec]) -> pd.DataFrame:
    obs = item_observations(subjects, item_specs)
    rows: list[dict[str, Any]] = []
    for subject_key, group in obs.groupby("subject_key", sort=False):
        subject = subjects[subjects["subject_key"] == subject_key].iloc[0]
        row: dict[str, Any] = {
            "subject_key": subject_key,
            "subject_id": subject["subject_id"],
            "dataset": subject["dataset"],
            "scale": subject["scale"],
        }
        for construct in CONSTRUCTS:
            values = group.loc[group["construct_id"] == construct, "y_true_norm"].to_numpy(dtype=float)
            row[construct] = float(np.mean(values)) if values.size else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def fit_latent_models(train: pd.DataFrame, feature_cols: list[str], item_specs: list[ItemSpec], seed: int) -> dict[str, Any]:
    targets = construct_targets(train, item_specs)
    train_with_targets = train.merge(targets[["subject_key", *CONSTRUCTS]], on="subject_key", how="left", validate="one_to_one")
    models: dict[str, Any] = {}
    x_all = train_with_targets[feature_cols].to_numpy(dtype=float)
    for construct in CONSTRUCTS:
        y = train_with_targets[construct].to_numpy(dtype=float)
        mask = np.isfinite(y)
        if int(mask.sum()) < 8 or len(np.unique(y[mask])) < 2:
            models[construct] = {"kind": "constant", "value": float(np.nanmean(y[mask])) if int(mask.sum()) else 0.0}
            continue
        alpha = choose_alpha(x_all[mask], y[mask], seed)
        model = ridge_pipeline(alpha)
        model.fit(x_all[mask], y[mask])
        models[construct] = {"kind": "ridge", "model": model, "alpha": alpha, "train_rows": int(mask.sum())}
    return models


def predict_latent(models: dict[str, Any], subjects: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    x = subjects[feature_cols].to_numpy(dtype=float)
    rows: dict[str, Any] = {
        "subject_key": subjects["subject_key"].astype(str).tolist(),
        "dataset": subjects["dataset"].astype(str).tolist(),
        "scale": subjects["scale"].astype(str).tolist(),
    }
    for construct, spec in models.items():
        if spec["kind"] == "constant":
            values = np.repeat(float(spec["value"]), len(subjects))
        else:
            values = np.asarray(spec["model"].predict(x), dtype=float).reshape(-1)
        rows[construct] = np.clip(values, 0.0, 1.0)
    return pd.DataFrame(rows)


def item_mean_predictions(train: pd.DataFrame, eval_frame: pd.DataFrame, item_specs: list[ItemSpec], seed: int, fold: str, protocol: str) -> pd.DataFrame:
    train_obs = item_observations(train, item_specs)
    means = train_obs.groupby("item_id")["y_true"].mean().to_dict()
    rows: list[dict[str, Any]] = []
    spec_by_id = {spec.item_id: spec for spec in item_specs}
    for _, subject in eval_frame.iterrows():
        for item_id, y_true in subject["item_values"].items():
            spec = spec_by_id[item_id]
            pred = float(np.clip(means.get(item_id, train_obs["y_true"].mean()), 0.0, spec.item_max))
            rows.append(prediction_row(subject, spec, y_true, pred, seed, fold, protocol, "M0_train_mean_items"))
    return pd.DataFrame(rows)


def total_score_predictions(train: pd.DataFrame, eval_frame: pd.DataFrame, feature_cols: list[str], item_specs: list[ItemSpec], seed: int, fold: str, protocol: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    spec_by_id = {spec.item_id: spec for spec in item_specs}
    for (dataset, scale), eval_group in eval_frame.groupby(["dataset", "scale"], sort=False):
        train_group = train[(train["dataset"] == dataset) & (train["scale"] == scale)].copy()
        if train_group.empty:
            continue
        x_train = train_group[feature_cols].to_numpy(dtype=float)
        y_train = train_group["total_score"].to_numpy(dtype=float)
        alpha = choose_alpha(x_train, y_train, seed)
        model = ridge_pipeline(alpha)
        model.fit(x_train, y_train)
        total_pred = np.asarray(model.predict(eval_group[feature_cols].to_numpy(dtype=float)), dtype=float).reshape(-1)
        train_obs = item_observations(train_group, item_specs)
        item_means = train_obs.groupby("item_id")["y_true"].mean().to_dict()
        denom = float(sum(item_means.values()))
        item_ids = [spec.item_id for spec in item_specs if spec.dataset == dataset and spec.scale == scale]
        fallback_prop = 1.0 / len(item_ids) if item_ids else 0.0
        for row_idx, (_, subject) in enumerate(eval_group.iterrows()):
            for item_id, y_true in subject["item_values"].items():
                spec = spec_by_id[item_id]
                prop = (float(item_means.get(item_id, 0.0)) / denom) if denom > 0 else fallback_prop
                pred = float(np.clip(total_pred[row_idx] * prop, 0.0, spec.item_max))
                rows.append(prediction_row(subject, spec, y_true, pred, seed, fold, protocol, "M0_total_score_floor"))
    return pd.DataFrame(rows)


def fixed_map_predictions(train: pd.DataFrame, eval_frame: pd.DataFrame, feature_cols: list[str], item_specs: list[ItemSpec], seed: int, fold: str, protocol: str) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    models = fit_latent_models(train, feature_cols, item_specs, seed)
    latent = predict_latent(models, eval_frame, feature_cols)
    latent_by_key = latent.set_index("subject_key")
    rows: list[dict[str, Any]] = []
    spec_by_id = {spec.item_id: spec for spec in item_specs}
    for _, subject in eval_frame.iterrows():
        z = latent_by_key.loc[str(subject["subject_key"])]
        for item_id, y_true in subject["item_values"].items():
            spec = spec_by_id[item_id]
            pred = float(np.clip(float(z[spec.primary_construct]) * spec.item_max, 0.0, spec.item_max))
            rows.append(prediction_row(subject, spec, y_true, pred, seed, fold, protocol, "M1_fixed_construct_map"))
    latent_audit = pd.DataFrame(
        [
            {
                "seed": seed,
                "fold": fold,
                "protocol": protocol,
                "construct_id": construct,
                "latent_model_kind": spec["kind"],
                "train_rows": int(spec.get("train_rows", 0)),
                "selected_alpha": spec.get("alpha"),
            }
            for construct, spec in models.items()
        ]
    )
    return pd.DataFrame(rows), models, latent_audit


@dataclass
class ThresholdModel:
    threshold: int
    kind: str
    constant_prob: float | None
    model: Pipeline | None


@dataclass
class OrdinalHead:
    head_group: str
    constructs: list[str]
    item_max: int
    thresholds: list[ThresholdModel]
    train_rows: int
    item_count: int
    dif_policy: str

    def predict(self, latent: pd.DataFrame) -> np.ndarray:
        x = latent[self.constructs].to_numpy(dtype=float)
        values = np.zeros(len(latent), dtype=float)
        for threshold in self.thresholds:
            if threshold.kind == "constant":
                prob = np.repeat(float(threshold.constant_prob), len(latent))
            elif threshold.model is not None:
                prob = threshold.model.predict_proba(x)[:, 1]
            else:
                prob = np.zeros(len(latent), dtype=float)
            values += prob
        return np.clip(values, 0.0, float(self.item_max))


def logistic_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed)),
        ]
    )


def head_constructs(specs: list[ItemSpec]) -> list[str]:
    constructs: list[str] = []
    for spec in specs:
        constructs.append(spec.primary_construct)
        constructs.extend(spec.secondary_constructs)
    unique = sorted({construct for construct in constructs if construct in CONSTRUCTS}, key=natural_key)
    return unique or [specs[0].primary_construct]


def fit_ordinal_heads(train: pd.DataFrame, train_latent: pd.DataFrame, item_specs: list[ItemSpec], seed: int) -> tuple[dict[str, OrdinalHead], pd.DataFrame]:
    spec_by_id = {spec.item_id: spec for spec in item_specs}
    train_obs = item_observations(train, item_specs)
    train_obs = train_obs.merge(train_latent[["subject_key", *CONSTRUCTS]], on="subject_key", how="left", validate="many_to_one")
    heads: dict[str, OrdinalHead] = {}
    audit_rows: list[dict[str, Any]] = []
    for head_group, group in train_obs.groupby("head_group", sort=True):
        specs = [spec_by_id[item_id] for item_id in sorted(group["item_id"].unique(), key=natural_key)]
        constructs = head_constructs(specs)
        item_max = int(max(spec.item_max for spec in specs))
        x = group[constructs].to_numpy(dtype=float)
        y = np.rint(group["y_true"].to_numpy(dtype=float)).astype(int)
        thresholds: list[ThresholdModel] = []
        learned = 0
        constants = 0
        for threshold in range(item_max):
            target = (y > threshold).astype(int)
            if len(np.unique(target)) < 2 or len(target) < 8:
                thresholds.append(
                    ThresholdModel(
                        threshold=threshold,
                        kind="constant",
                        constant_prob=float(np.mean(target)) if len(target) else 0.0,
                        model=None,
                    )
                )
                constants += 1
                continue
            model = logistic_pipeline(seed)
            model.fit(x, target)
            thresholds.append(ThresholdModel(threshold=threshold, kind="logistic", constant_prob=None, model=model))
            learned += 1
        dif_policy = ";".join(sorted(set(spec.dif_policy for spec in specs)))
        head = OrdinalHead(
            head_group=head_group,
            constructs=constructs,
            item_max=item_max,
            thresholds=thresholds,
            train_rows=int(len(group)),
            item_count=int(len(specs)),
            dif_policy=dif_policy,
        )
        heads[head_group] = head
        audit_rows.append(
            {
                "head_group": head_group,
                "dif_policy": dif_policy,
                "constructs": ";".join(constructs),
                "item_count": int(len(specs)),
                "train_observations": int(len(group)),
                "threshold_count": int(len(thresholds)),
                "learned_threshold_models": int(learned),
                "constant_threshold_models": int(constants),
                "dataset_count": int(group["dataset"].nunique()),
                "scale_count": int(group["scale"].nunique()),
            }
        )
    return heads, pd.DataFrame(audit_rows)


def partial_invariance_predictions(train: pd.DataFrame, eval_frame: pd.DataFrame, feature_cols: list[str], item_specs: list[ItemSpec], seed: int, fold: str, protocol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    latent_models = fit_latent_models(train, feature_cols, item_specs, seed)
    train_latent = predict_latent(latent_models, train, feature_cols)
    eval_latent = predict_latent(latent_models, eval_frame, feature_cols)
    heads, head_audit = fit_ordinal_heads(train, train_latent, item_specs, seed)
    eval_latent_by_key = eval_latent.set_index("subject_key")
    rows: list[dict[str, Any]] = []
    spec_by_id = {spec.item_id: spec for spec in item_specs}
    for _, subject in eval_frame.iterrows():
        latent_row = eval_latent_by_key.loc[str(subject["subject_key"])].to_frame().T
        for item_id, y_true in subject["item_values"].items():
            spec = spec_by_id[item_id]
            head = heads.get(spec.head_group)
            if head is None:
                pred = 0.0
            else:
                pred = float(head.predict(latent_row)[0])
            rows.append(prediction_row(subject, spec, y_true, pred, seed, fold, protocol, "M2_partial_invariance_ordinal"))
    head_audit.insert(0, "protocol", protocol)
    head_audit.insert(0, "fold", fold)
    head_audit.insert(0, "seed", seed)
    return pd.DataFrame(rows), head_audit


def prediction_row(subject: pd.Series, spec: ItemSpec, y_true: float, y_pred: float, seed: int, fold: str, protocol: str, model: str) -> dict[str, Any]:
    rounded = int(np.rint(float(np.clip(y_pred, 0.0, spec.item_max))))
    return {
        "run_id": RUN_ID,
        "protocol": protocol,
        "model": model,
        "seed": int(seed),
        "fold": fold,
        "eval_dataset": subject["dataset"],
        "scale": subject["scale"],
        "subject_key": subject["subject_key"],
        "subject_id": subject["subject_id"],
        "item_id": spec.item_id,
        "item_code": spec.item_code,
        "construct_id": spec.primary_construct,
        "head_group": spec.head_group,
        "dif_policy": spec.dif_policy,
        "item_max": int(spec.item_max),
        "scale_total_true": float(subject["total_score"]),
        "y_true": float(y_true),
        "y_pred": float(np.clip(y_pred, 0.0, spec.item_max)),
        "y_pred_rounded": rounded,
    }


def sort_subject_frame(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sort_values(
        ["dataset", "subject_id"],
        key=lambda series: series.map(lambda item: tuple(natural_key(item))),
    ).reset_index(drop=True)


def protocol_splits(subjects: pd.DataFrame, split_path: Path) -> list[tuple[int, str, str, pd.DataFrame, pd.DataFrame]]:
    cmdc_folds = load_subject_folds(split_path, "cmdc", "cmdc_phq9_subject_cv", "phq9_total")
    pdch_folds = load_subject_folds(split_path, "pdch", "pdch_hamd17_subject_cv_fallback", "hamd17_total")
    rows: list[tuple[int, str, str, pd.DataFrame, pd.DataFrame]] = []
    edaic_train = subjects[(subjects["dataset"] == "edaic") & (subjects["official_split"] == "train")].copy()
    edaic_dev = subjects[(subjects["dataset"] == "edaic") & (subjects["official_split"] == "dev")].copy()
    if set(edaic_train["subject_key"]) & set(edaic_dev["subject_key"]):
        raise ValueError("E-DAIC official train/dev subject overlap")
    for seed in SEEDS:
        cmdc_fold = cmdc_folds[seed % len(cmdc_folds)]
        pdch_fold = pdch_folds[seed % len(pdch_folds)]
        cmdc_fold_name = next(iter(cmdc_fold["fold_name"]))
        pdch_fold_name = next(iter(pdch_fold["fold_name"]))
        cmdc_train = subjects[(subjects["dataset"] == "cmdc") & subjects["subject_id"].isin(cmdc_fold["train"])].copy()
        cmdc_eval = subjects[(subjects["dataset"] == "cmdc") & subjects["subject_id"].isin(cmdc_fold["validation"])].copy()
        pdch_train = subjects[(subjects["dataset"] == "pdch") & subjects["subject_id"].isin(pdch_fold["train"])].copy()
        pdch_eval = subjects[(subjects["dataset"] == "pdch") & subjects["subject_id"].isin(pdch_fold["validation"])].copy()
        rows.extend(
            [
                (seed, "edaic_train_dev", "official_train_dev", sort_subject_frame(edaic_train), sort_subject_frame(edaic_dev)),
                (seed, "cmdc_phq_subject_cv", cmdc_fold_name, sort_subject_frame(cmdc_train), sort_subject_frame(cmdc_eval)),
                (seed, "pdch_hamd_subject_cv", pdch_fold_name, sort_subject_frame(pdch_train), sort_subject_frame(pdch_eval)),
                (
                    seed,
                    "pooled_partial_invariance",
                    f"edaic_train_dev__cmdc_{cmdc_fold_name}__pdch_{pdch_fold_name}",
                    sort_subject_frame(pd.concat([edaic_train, cmdc_train, pdch_train], ignore_index=True)),
                    sort_subject_frame(pd.concat([edaic_dev, cmdc_eval, pdch_eval], ignore_index=True)),
                ),
            ]
        )
    return rows


def split_audit_row(seed: int, protocol: str, fold: str, train: pd.DataFrame, eval_frame: pd.DataFrame) -> dict[str, Any]:
    train_keys = set(train["subject_key"].astype(str))
    eval_keys = set(eval_frame["subject_key"].astype(str))
    overlap = train_keys & eval_keys
    if overlap:
        raise ValueError(f"{protocol}/{seed}/{fold} train/eval overlap: {sorted(overlap)[:5]}")
    return {
        "seed": seed,
        "protocol": protocol,
        "fold": fold,
        "train_subjects": int(len(train)),
        "eval_subjects": int(len(eval_frame)),
        "train_datasets": ";".join(sorted(train["dataset"].unique())),
        "eval_datasets": ";".join(sorted(eval_frame["dataset"].unique())),
        "train_eval_subject_overlap": int(len(overlap)),
    }


def run_experiments(subjects: pd.DataFrame, feature_cols: list[str], item_specs: list[ItemSpec], split_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    prediction_frames: list[pd.DataFrame] = []
    split_rows: list[dict[str, Any]] = []
    dif_rows: list[pd.DataFrame] = []
    for seed, protocol, fold, train, eval_frame in protocol_splits(subjects, split_path):
        split_rows.append(split_audit_row(seed, protocol, fold, train, eval_frame))
        prediction_frames.extend(
            [
                item_mean_predictions(train, eval_frame, item_specs, seed, fold, protocol),
                total_score_predictions(train, eval_frame, feature_cols, item_specs, seed, fold, protocol),
                fixed_map_predictions(train, eval_frame, feature_cols, item_specs, seed, fold, protocol)[0],
            ]
        )
        partial_pred, dif_summary = partial_invariance_predictions(train, eval_frame, feature_cols, item_specs, seed, fold, protocol)
        prediction_frames.append(partial_pred)
        dif_rows.append(dif_summary)
    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(split_rows), pd.concat(dif_rows, ignore_index=True)


def total_metric_rows(predictions: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group_key, group in predictions.groupby(["seed", "protocol", "model", "eval_dataset", "scale"], sort=False):
        seed, protocol, model, dataset, scale = group_key
        subject_rows = (
            group.groupby("subject_key", sort=False)
            .agg(y_true_total=("scale_total_true", "first"), y_pred_total=("y_pred", "sum"))
            .reset_index()
        )
        if subject_rows.empty:
            continue
        err = subject_rows["y_pred_total"].to_numpy(dtype=float) - subject_rows["y_true_total"].to_numpy(dtype=float)
        rows.extend(
            [
                {
                    "seed": int(seed),
                    "protocol": protocol,
                    "model": model,
                    "dataset_slice": dataset,
                    "scale": scale,
                    "target_id": "scale_total",
                    "construct_id": "total",
                    "metric": "Item-derived Total MAE",
                    "value": safe_float(np.mean(np.abs(err))),
                    "subject_count": int(len(subject_rows)),
                },
                {
                    "seed": int(seed),
                    "protocol": protocol,
                    "model": model,
                    "dataset_slice": dataset,
                    "scale": scale,
                    "target_id": "scale_total",
                    "construct_id": "total",
                    "metric": "Item-derived Total RMSE",
                    "value": safe_float(np.sqrt(np.mean(err**2))),
                    "subject_count": int(len(subject_rows)),
                },
                {
                    "seed": int(seed),
                    "protocol": protocol,
                    "model": model,
                    "dataset_slice": dataset,
                    "scale": scale,
                    "target_id": "scale_total",
                    "construct_id": "total",
                    "metric": "Item-derived Total Spearman",
                    "value": spearman(subject_rows["y_true_total"], subject_rows["y_pred_total"]),
                    "subject_count": int(len(subject_rows)),
                },
            ]
        )
    return rows


def metric_rows_for_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for group_key, group in predictions.groupby(["seed", "protocol", "model", "eval_dataset", "scale"], sort=False):
        seed, protocol, model, dataset, scale = group_key
        item_maes: list[float] = []
        construct_maes: list[float] = []
        for item_id, item_group in group.groupby("item_id", sort=False):
            y_true = item_group["y_true"].to_numpy(dtype=float)
            y_pred = item_group["y_pred"].to_numpy(dtype=float)
            err = y_pred - y_true
            mae = safe_float(np.mean(np.abs(err)))
            rmse = safe_float(np.sqrt(np.mean(err**2)))
            rounded_within_1 = safe_float(np.mean(np.abs(np.rint(y_pred) - y_true) <= 1.0))
            if mae is not None:
                item_maes.append(mae)
            for metric, value in [
                ("Item MAE", mae),
                ("Item RMSE", rmse),
                ("Rounded Within 1", rounded_within_1),
                ("Item Spearman", spearman(y_true, y_pred)),
            ]:
                rows.append(
                    {
                        "seed": int(seed),
                        "protocol": protocol,
                        "model": model,
                        "dataset_slice": dataset,
                        "scale": scale,
                        "target_id": item_id,
                        "construct_id": str(item_group["construct_id"].iloc[0]),
                        "metric": metric,
                        "value": value,
                        "subject_count": int(item_group["subject_key"].nunique()),
                    }
                )
        for construct, construct_group in group.groupby("construct_id", sort=False):
            construct_subjects = (
                construct_group.groupby("subject_key", sort=False)
                .agg(y_true=("y_true", "mean"), y_pred=("y_pred", "mean"))
                .reset_index()
            )
            err = construct_subjects["y_pred"].to_numpy(dtype=float) - construct_subjects["y_true"].to_numpy(dtype=float)
            mae = safe_float(np.mean(np.abs(err)))
            if mae is not None:
                construct_maes.append(mae)
            rows.append(
                {
                    "seed": int(seed),
                    "protocol": protocol,
                    "model": model,
                    "dataset_slice": dataset,
                    "scale": scale,
                    "target_id": f"{construct}_construct_proxy",
                    "construct_id": construct,
                    "metric": "Construct Proxy MAE",
                    "value": mae,
                    "subject_count": int(construct_subjects["subject_key"].nunique()),
                }
            )
        for metric, value in [
            ("Macro Item MAE", safe_float(np.mean(item_maes)) if item_maes else None),
            ("Macro Construct Proxy MAE", safe_float(np.mean(construct_maes)) if construct_maes else None),
        ]:
            rows.append(
                {
                    "seed": int(seed),
                    "protocol": protocol,
                    "model": model,
                    "dataset_slice": dataset,
                    "scale": scale,
                    "target_id": "macro",
                    "construct_id": "macro",
                    "metric": metric,
                    "value": value,
                    "subject_count": int(group["subject_key"].nunique()),
                }
            )
    rows.extend(total_metric_rows(predictions))
    return pd.DataFrame(rows)


def bootstrap_metric(predictions: pd.DataFrame, protocol: str, model: str, dataset: str, scale: str, metric: str, seed: int) -> tuple[float | None, float | None]:
    subset = predictions[
        (predictions["protocol"] == protocol)
        & (predictions["model"] == model)
        & (predictions["eval_dataset"] == dataset)
        & (predictions["scale"] == scale)
    ].copy()
    if subset.empty:
        return None, None
    rng = np.random.default_rng(seed)
    subjects = np.asarray(sorted(subset["subject_key"].astype(str).unique(), key=natural_key))
    grouped = {subject: subset.index[subset["subject_key"].astype(str) == subject].to_numpy() for subject in subjects}
    values: list[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        sampled = rng.choice(subjects, size=len(subjects), replace=True)
        sample_idx = np.concatenate([grouped[subject] for subject in sampled])
        sample = subset.loc[sample_idx]
        if metric == "Macro Item MAE":
            item_values = [
                float(np.mean(np.abs(item_group["y_pred"] - item_group["y_true"])))
                for _, item_group in sample.groupby("item_id", sort=False)
            ]
            if item_values:
                values.append(float(np.mean(item_values)))
        elif metric == "Item-derived Total MAE":
            totals = (
                sample.groupby("subject_key", sort=False)
                .agg(y_true_total=("scale_total_true", "first"), y_pred_total=("y_pred", "sum"))
                .reset_index()
            )
            if not totals.empty:
                values.append(float(np.mean(np.abs(totals["y_pred_total"] - totals["y_true_total"]))))
    if not values:
        return None, None
    return safe_float(np.percentile(values, 2.5)), safe_float(np.percentile(values, 97.5))


def summarize_metrics(metrics: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    summary = (
        metrics.groupby(["protocol", "model", "dataset_slice", "scale", "target_id", "construct_id", "metric"], dropna=False)
        .agg(mean=("value", "mean"), std=("value", "std"), seed_count=("seed", "nunique"), subject_count_mean=("subject_count", "mean"))
        .reset_index()
    )
    summary["std"] = summary["std"].fillna(0.0)
    summary["ci95_low"] = summary["mean"] - 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))
    summary["ci95_high"] = summary["mean"] + 1.96 * summary["std"] / np.sqrt(summary["seed_count"].clip(lower=1))

    boot_rows: list[dict[str, Any]] = []
    macro = summary[
        (summary["target_id"] == "macro")
        & (summary["metric"].isin(["Macro Item MAE"]))
    ].copy()
    total = summary[(summary["target_id"] == "scale_total") & (summary["metric"] == "Item-derived Total MAE")].copy()
    for _, row in pd.concat([macro, total], ignore_index=True).iterrows():
        low, high = bootstrap_metric(
            predictions,
            str(row["protocol"]),
            str(row["model"]),
            str(row["dataset_slice"]),
            str(row["scale"]),
            str(row["metric"]),
            seed=20260811,
        )
        boot_rows.append(
            {
                "protocol": row["protocol"],
                "model": row["model"],
                "dataset_slice": row["dataset_slice"],
                "scale": row["scale"],
                "target_id": row["target_id"],
                "construct_id": row["construct_id"],
                "metric": row["metric"],
                "bootstrap_ci95_low": low,
                "bootstrap_ci95_high": high,
            }
        )
    if boot_rows:
        summary = summary.merge(pd.DataFrame(boot_rows), how="left")
    else:
        summary["bootstrap_ci95_low"] = np.nan
        summary["bootstrap_ci95_high"] = np.nan
    return summary


def comparison_summary(metric_summary: pd.DataFrame) -> pd.DataFrame:
    macro = metric_summary[
        (metric_summary["target_id"] == "macro")
        & (metric_summary["metric"] == "Macro Item MAE")
    ].copy()
    rows: list[dict[str, Any]] = []
    for (protocol, dataset, scale), group in macro.groupby(["protocol", "dataset_slice", "scale"], sort=False):
        values = group.set_index("model")["mean"].to_dict()
        train_mean = values.get("M0_train_mean_items")
        total = values.get("M0_total_score_floor")
        fixed = values.get("M1_fixed_construct_map")
        for model, value in values.items():
            rows.append(
                {
                    "protocol": protocol,
                    "dataset_slice": dataset,
                    "scale": scale,
                    "model": model,
                    "macro_item_mae": value,
                    "delta_vs_train_mean_items": safe_float(value - train_mean) if train_mean is not None else None,
                    "delta_vs_total_score_floor": safe_float(value - total) if total is not None else None,
                    "delta_vs_fixed_construct_map": safe_float(value - fixed) if fixed is not None else None,
                }
            )
    return pd.DataFrame(rows)


def run_feature_identity_probe(subjects: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    table = subjects[["dataset", *feature_cols]].copy()
    x = table[feature_cols].to_numpy(dtype=float)
    labels = sorted(table["dataset"].unique())
    y = table["dataset"].map({label: idx for idx, label in enumerate(labels)}).to_numpy(dtype=int)
    n_splits = min(5, min(np.bincount(y)))
    for seed in SEEDS:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        scores: list[float] = []
        for train_idx, eval_idx in splitter.split(x, y):
            model = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("classifier", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=seed)),
                ]
            )
            model.fit(x[train_idx], y[train_idx])
            scores.append(float(balanced_accuracy_score(y[eval_idx], model.predict(x[eval_idx]))))
        rows.append(
            {
                "seed": seed,
                "probe_id": "feature_identity_bge_edaic_cmdc_pdch",
                "model": "feature_bge",
                "metric": "Balanced Accuracy",
                "value": safe_float(np.mean(scores)),
                "sample_count": int(len(table)),
                "dataset_count": int(len(labels)),
            }
        )
    return pd.DataFrame(rows)


def run_prediction_identity_probe(predictions: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    source = predictions[predictions["protocol"] == "pooled_partial_invariance"].copy()
    for (seed, model_name), group in source.groupby(["seed", "model"], sort=False):
        grouped = group.copy()
        grouped["y_pred_norm"] = grouped["y_pred"] / grouped["item_max"].clip(lower=1)
        wide = grouped.pivot_table(
            index=["subject_key", "eval_dataset"],
            columns="construct_id",
            values="y_pred_norm",
            aggfunc="mean",
        ).reset_index()
        construct_cols = [column for column in CONSTRUCTS if column in wide.columns]
        if len(construct_cols) < 3:
            continue
        x = wide[construct_cols].to_numpy(dtype=float)
        labels = sorted(wide["eval_dataset"].unique())
        y = wide["eval_dataset"].map({label: idx for idx, label in enumerate(labels)}).to_numpy(dtype=int)
        counts = np.bincount(y)
        if len(labels) < 2 or min(counts) < 3:
            continue
        n_splits = min(5, min(counts))
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=int(seed))
        scores: list[float] = []
        for train_idx, eval_idx in splitter.split(x, y):
            clf = Pipeline(
                [
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                    ("classifier", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, random_state=int(seed))),
                ]
            )
            clf.fit(x[train_idx], y[train_idx])
            scores.append(float(balanced_accuracy_score(y[eval_idx], clf.predict(x[eval_idx]))))
        rows.append(
            {
                "seed": int(seed),
                "probe_id": "prediction_identity_pooled_eval_dataset",
                "model": model_name,
                "metric": "Balanced Accuracy",
                "value": safe_float(np.mean(scores)),
                "sample_count": int(len(wide)),
                "dataset_count": int(len(labels)),
            }
        )
    return pd.DataFrame(rows)


def summarize_identity(probes: pd.DataFrame) -> pd.DataFrame:
    if probes.empty:
        return pd.DataFrame()
    return (
        probes.groupby(["probe_id", "model", "metric"], dropna=False)
        .agg(mean=("value", "mean"), std=("value", "std"), seed_count=("seed", "nunique"), sample_count_mean=("sample_count", "mean"))
        .reset_index()
        .fillna({"std": 0.0})
    )


def build_construct_target_map(item_specs: list[ItemSpec]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "dataset": spec.dataset,
                "scale": spec.scale,
                "item_code": spec.item_code,
                "item_label_short": spec.item_label_short,
                "primary_construct": spec.primary_construct,
                "secondary_constructs": ";".join(spec.secondary_constructs),
                "head_group": spec.head_group,
                "dif_policy": spec.dif_policy,
                "mapping_strength": spec.mapping_strength,
                "item_max": spec.item_max,
            }
            for spec in item_specs
        ]
    )


def verdict_from_outputs(comparison: pd.DataFrame, identity_summary: pd.DataFrame) -> dict[str, Any]:
    pooled = comparison[
        (comparison["protocol"] == "pooled_partial_invariance")
        & (comparison["model"] == "M2_partial_invariance_ordinal")
    ].copy()
    active = pooled[pooled["dataset_slice"].isin(["edaic", "cmdc", "pdch"])]
    total_deltas = [safe_float(value) for value in active["delta_vs_total_score_floor"].tolist()]
    fixed_deltas = [safe_float(value) for value in active["delta_vs_fixed_construct_map"].tolist()]
    total_deltas = [value for value in total_deltas if value is not None]
    fixed_deltas = [value for value in fixed_deltas if value is not None]
    improved_vs_total = sum(1 for value in total_deltas if value < 0.0)
    improved_vs_fixed = sum(1 for value in fixed_deltas if value < 0.0)
    worst_vs_total = max(total_deltas) if total_deltas else None
    worst_vs_fixed = max(fixed_deltas) if fixed_deltas else None

    pred_identity = None
    if not identity_summary.empty:
        row = identity_summary[
            (identity_summary["probe_id"] == "prediction_identity_pooled_eval_dataset")
            & (identity_summary["model"] == "M2_partial_invariance_ordinal")
        ]
        if not row.empty:
            pred_identity = safe_float(row.iloc[0]["mean"])
    feature_identity = None
    if not identity_summary.empty:
        row = identity_summary[identity_summary["probe_id"] == "feature_identity_bge_edaic_cmdc_pdch"]
        if not row.empty:
            feature_identity = safe_float(row.iloc[0]["mean"])

    if improved_vs_total < 2:
        status = "blocked_not_better_than_total_score_floor"
    elif improved_vs_fixed < 2:
        status = "blocked_not_better_than_fixed_construct_map"
    elif pred_identity is not None and pred_identity > 0.80:
        status = "partial_measurement_gain_prediction_identity_high"
    else:
        status = "pass_partial_invariance_measurement_candidate"

    return {
        "pass_rule_status": status,
        "pass_rule_met": status.startswith("pass_"),
        "pooled_active_slices": int(len(active)),
        "pooled_m2_improved_vs_total_score_floor_slices": int(improved_vs_total),
        "pooled_m2_improved_vs_fixed_map_slices": int(improved_vs_fixed),
        "pooled_m2_worst_delta_vs_total_score_floor": safe_float(worst_vs_total),
        "pooled_m2_worst_delta_vs_fixed_construct_map": safe_float(worst_vs_fixed),
        "feature_identity_ba": feature_identity,
        "prediction_identity_ba_m2": pred_identity,
        "short_read": (
            "MV08 tests whether an explicitly partial measurement-invariance contract improves over total-score and fixed-map floors. Treat a pass as bounded RQ1 measurement evidence only, not full-method authorization."
        ),
    }


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
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw_snippet",
        r"local_text_locators_json",
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
        "audit_id": "P5_MV08_partial_invariance_measurement_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(out_dir: Path, run_summary: dict[str, Any], comparison: pd.DataFrame, identity: pd.DataFrame, split_audit: pd.DataFrame) -> None:
    verdict = run_summary["verdict"]
    pooled = comparison[
        (comparison["protocol"] == "pooled_partial_invariance")
        & (comparison["model"].isin(["M0_total_score_floor", "M1_fixed_construct_map", "M2_partial_invariance_ordinal"]))
    ].copy()
    lines = [
        "# P5_MV08 Partial-Invariance Measurement Pilot",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Pass-rule status: `{verdict['pass_rule_status']}`.",
        f"- Full-method allowed: `False`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        verdict["short_read"],
        "",
        "## Pooled Protocol Macro Item MAE",
        "",
        "| dataset | scale | model | macro item MAE | delta vs total | delta vs fixed |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for _, row in pooled.iterrows():
        lines.append(
            f"| {row['dataset_slice']} | {row['scale']} | {row['model']} | "
            f"{format_value(row['macro_item_mae'])} | {format_value(row['delta_vs_total_score_floor'])} | "
            f"{format_value(row['delta_vs_fixed_construct_map'])} |"
        )
    lines.extend(
        [
            "",
            "## Identity Probes",
            "",
            "| probe | model | mean BA | seeds |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    if identity.empty:
        lines.append("| none | none |  |  |")
    else:
        for _, row in identity.iterrows():
            lines.append(f"| {row['probe_id']} | {row['model']} | {format_value(row['mean'])} | {int(row['seed_count'])} |")
    lines.extend(
        [
            "",
            "## Split Audit",
            "",
            "| protocol | train subjects | eval subjects | overlap |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    split_summary = (
        split_audit.groupby("protocol")
        .agg(train_subjects_mean=("train_subjects", "mean"), eval_subjects_mean=("eval_subjects", "mean"), overlap_max=("train_eval_subject_overlap", "max"))
        .reset_index()
    )
    for _, row in split_summary.iterrows():
        lines.append(
            f"| {row['protocol']} | {row['train_subjects_mean']:.1f} | {row['eval_subjects_mean']:.1f} | {int(row['overlap_max'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This is a minimal-validation pilot over frozen BGE features and shallow measurement heads.",
            "- A positive result would support only a bounded partial-invariance RQ1 claim.",
            "- Row predictions and any latent or learned-parameter details remain local-only.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2-root", type=Path, default=DEFAULT_PHASE2_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists() and args.overwrite:
        for child in out_dir.iterdir():
            if child.is_file():
                child.unlink()
            else:
                shutil.rmtree(child)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    item_specs = build_item_specs(PHASE4_DIR / "scale_item_catalog.csv")
    features, feature_cols, feature_audit = load_bge_features(args.phase2_root)
    subjects, label_feature_audit = load_subjects(args.manifest_dir, features, item_specs)
    predictions, split_audit, dif_summary = run_experiments(subjects, feature_cols, item_specs, args.split_path)
    metrics_by_seed = metric_rows_for_predictions(predictions)
    metric_summary = summarize_metrics(metrics_by_seed, predictions)
    comparison = comparison_summary(metric_summary)
    identity_by_seed = pd.concat(
        [run_feature_identity_probe(subjects, feature_cols), run_prediction_identity_probe(predictions)],
        ignore_index=True,
    )
    identity_summary = summarize_identity(identity_by_seed)
    verdict = verdict_from_outputs(comparison, identity_summary)

    local_predictions_path = out_dir / LOCAL_PREDICTIONS_NAME
    predictions.to_csv(local_predictions_path, index=False)
    metrics_by_seed.to_csv(out_dir / "metrics_by_seed.csv", index=False)
    metric_summary.to_csv(out_dir / "metric_summary.csv", index=False)
    comparison.to_csv(out_dir / "comparison_summary.csv", index=False)
    identity_by_seed.to_csv(out_dir / "identity_probe_by_seed.csv", index=False)
    identity_summary.to_csv(out_dir / "identity_probe_summary.csv", index=False)
    split_audit.to_csv(out_dir / "model_split_audit.csv", index=False)
    label_feature_audit.to_csv(out_dir / "label_feature_audit.csv", index=False)
    build_construct_target_map(item_specs).to_csv(out_dir / "construct_target_map.csv", index=False)
    dif_summary.to_csv(out_dir / "dif_sparsity_summary.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "status": "complete",
        "scope": "minimal_validation_partial_invariance_no_full_method",
        "input_contract": {
            "datasets": ["edaic", "cmdc", "pdch"],
            "feature_family": "text_bge",
            "model_input_columns": int(len(feature_cols)),
            "raw_data_scanned": False,
            "raw_text_read": False,
            "manifest_label_fields_read": True,
            "phase4_ontology_read": True,
        },
        "label_feature_audit": label_feature_audit.to_dict(orient="records"),
        "split_audit": {
            "rows": int(len(split_audit)),
            "max_train_eval_subject_overlap": int(split_audit["train_eval_subject_overlap"].max()),
        },
        "models_compared": [
            "M0_train_mean_items",
            "M0_total_score_floor",
            "M1_fixed_construct_map",
            "M2_partial_invariance_ordinal",
        ],
        "verdict": verdict,
        "output_policy": {
            "tracked_outputs": sorted(TRACKED_FILES),
            "local_only_files": [LOCAL_PREDICTIONS_NAME],
            "row_level_predictions_written": True,
            "learned_parameters_written": False,
            "latent_scores_written": False,
            "raw_paths_written": False,
            "raw_text_written": False,
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, comparison, identity_summary, split_audit)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, comparison, identity_summary, split_audit)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")

    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "pass_rule_status": verdict["pass_rule_status"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
