#!/usr/bin/env python3
"""Run MV21 descriptive measurement-discrepancy reinforcement.

This label-only reinforcement adds three bounded controls for the
target-measurement-validity manuscript:

1. PHQ shared-item item-level descriptive and severity-conditioned analysis
   for E-DAIC versus CMDC.
2. CMDC-HAMD versus PDCH-HAMD exploratory same-scale item, correlation, and
   severity-conditioned analysis.
3. DAIC-WOZ/E-DAIC same-PHQ-8 lineage control, treated as a highly overlapping
   benchmark/control view rather than an independent corpus.

The script reads only manifest-governed label payloads and official DAIC-WOZ
split CSVs. It exports aggregate tables only: no raw text/media, source paths,
subject rows, fitted psychometric parameters, model objects, or predictions.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
from collections import Counter
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_DAICWOZ_SPLIT_DIR = ROOT / "datasets" / "DAIC-WOZ" / "splits"
DEFAULT_OUT_DIR = (
    ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv21_measurement_discrepancy_gradient"
)

RUN_ID = "P5_MV21_measurement_discrepancy_gradient"

PHQ_CONSTRUCTS = [f"C{idx:02d}" for idx in range(1, 9)]
HAMD_ITEMS = [f"HAMD{idx:02d}" for idx in range(1, 18)]
MISSING_HAMD_CODES = {9.0}
MIN_CONDITION_BIN_N = 5

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

CMDC_PHQ_ITEM_MAP = {
    "C01": "PHQ-2",
    "C02": "PHQ-1",
    "C03": "PHQ-3",
    "C04": "PHQ-4",
    "C05": "PHQ-5",
    "C06": "PHQ-6",
    "C07": "PHQ-7",
    "C08": "PHQ-8",
}

DAICWOZ_ITEM_MAP = {
    "C01": "PHQ8_Depressed",
    "C02": "PHQ8_NoInterest",
    "C03": "PHQ8_Sleep",
    "C04": "PHQ8_Tired",
    "C05": "PHQ8_Appetite",
    "C06": "PHQ8_Failure",
    "C07": "PHQ8_Concentrating",
    "C08": "PHQ8_Moving",
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
    "daicwoz_edaic_conditioned_deltas.csv",
    "daicwoz_edaic_contract_distribution.csv",
    "daicwoz_edaic_paired_item_differences.csv",
    "daicwoz_edaic_severity_conditioned_response.csv",
    "daicwoz_edaic_scope_audit.csv",
    "hamd_conditioned_deltas.csv",
    "hamd_item_category_proportions.csv",
    "hamd_item_correlation_delta_summary.csv",
    "hamd_item_correlation_summary.csv",
    "hamd_item_distribution.csv",
    "hamd_scope_audit.csv",
    "hamd_severity_conditioned_response.csv",
    "phq_shared_conditioned_deltas.csv",
    "phq_shared_item_category_proportions.csv",
    "phq_shared_item_distribution.csv",
    "phq_shared_scope_audit.csv",
    "phq_shared_severity_conditioned_response.csv",
    "phq_shared_total_band_summary.csv",
    "report.md",
    "run_summary.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


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


def parse_json_dict(value: Any) -> dict[str, Any]:
    text = clean_value(value)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def phq_band(total: float) -> str:
    if total <= 4:
        return "none_minimal"
    if total <= 9:
        return "mild"
    if total <= 14:
        return "moderate"
    return "moderately_severe_or_severe"


def hamd_band(total: float) -> str:
    if total <= 7:
        return "normal"
    if total <= 17:
        return "mild"
    if total <= 24:
        return "moderate"
    return "severe"


def read_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, **kwargs)


def load_phq_manifest_dataset(
    manifest_dir: Path,
    dataset: str,
    item_map: dict[str, str],
    total_col: str,
    item_col: str,
    scale: str,
    official_split_filter: set[str] | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = read_csv(manifest_dir / f"{dataset}_subjects.csv")
    required = {"subject_id", "file_valid", total_col, item_col}
    if official_split_filter is not None:
        required.add("official_split")
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{dataset} manifest missing columns: {', '.join(sorted(missing))}")

    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    manifest["subject_id"] = manifest["subject_id"].astype(str)
    raw_valid_subjects = int(manifest["subject_id"].nunique())
    if official_split_filter is not None:
        manifest = manifest[manifest["official_split"].astype(str).isin(official_split_filter)].copy()
    eligible_subjects = int(manifest["subject_id"].nunique())

    rows: list[dict[str, Any]] = []
    missing_payload_subjects = 0
    incomplete_subjects = 0
    for subject_id, group in manifest.groupby("subject_id", sort=True):
        first = group.iloc[0]
        total = safe_float(first[total_col])
        payload = parse_json_dict(first[item_col])
        if not payload:
            missing_payload_subjects += 1
            continue
        record: dict[str, Any] = {
            "dataset": dataset,
            "scale": scale,
            "subject_id": str(subject_id),
            "shared_total": 0.0,
            "reported_total": total,
        }
        complete = total is not None
        for construct, payload_key in item_map.items():
            value = safe_float(payload.get(payload_key))
            if value is None:
                complete = False
                break
            value = float(np.clip(value, 0.0, 3.0))
            record[construct] = value
            record["shared_total"] += value
        if not complete:
            incomplete_subjects += 1
            continue
        record["severity_band"] = phq_band(float(record["shared_total"]))
        rows.append(record)

    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError(f"no PHQ item rows for {dataset}")
    table = table.sort_values("subject_id", key=lambda s: s.map(lambda value: tuple(natural_key(value)))).reset_index(drop=True)
    audit = {
        "analysis": "phq_shared_item",
        "dataset": dataset,
        "scale": scale,
        "raw_valid_subjects": raw_valid_subjects,
        "eligible_subjects": eligible_subjects,
        "complete_item_subjects": int(len(table)),
        "missing_payload_subjects": int(missing_payload_subjects),
        "incomplete_subjects": int(incomplete_subjects),
        "subject_collapse": "one_manifest_payload_per_subject",
        "split_filter": ";".join(sorted(official_split_filter)) if official_split_filter else "all_valid",
    }
    return table, audit


def load_daicwoz_split_phq8(split_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    frames: list[pd.DataFrame] = []
    for split, filename in [
        ("train", "train_split_Depression_AVEC2017.csv"),
        ("dev", "dev_split_Depression_AVEC2017.csv"),
    ]:
        data = read_csv(split_dir / filename)
        data["official_split"] = split
        frames.append(data)
    raw = pd.concat(frames, ignore_index=True)
    raw_rows = int(len(raw))
    incomplete_rows = 0
    rows: list[dict[str, Any]] = []
    for _, source in raw.iterrows():
        total = safe_float(source.get("PHQ8_Score"))
        if total is None:
            incomplete_rows += 1
            continue
        record: dict[str, Any] = {
            "dataset": "daicwoz",
            "scale": "PHQ-8",
            "subject_id": str(int(source["Participant_ID"])),
            "shared_total": 0.0,
            "reported_total": float(total),
            "official_split": str(source["official_split"]),
        }
        complete = True
        for construct, column in DAICWOZ_ITEM_MAP.items():
            value = safe_float(source.get(column))
            if value is None:
                complete = False
                break
            value = float(np.clip(value, 0.0, 3.0))
            record[construct] = value
            record["shared_total"] += value
        if complete:
            record["severity_band"] = phq_band(float(record["shared_total"]))
            rows.append(record)
        else:
            incomplete_rows += 1
    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError("no DAIC-WOZ train/dev PHQ-8 item rows")
    table = table.sort_values("subject_id", key=lambda s: s.map(lambda value: tuple(natural_key(value)))).reset_index(drop=True)
    audit = {
        "analysis": "daicwoz_edaic_same_phq8_lineage_control",
        "dataset": "daicwoz",
        "scale": "PHQ-8",
        "raw_train_dev_rows": raw_rows,
        "complete_item_subjects": int(len(table)),
        "incomplete_item_rows": int(incomplete_rows),
        "split_filter": "train;dev",
        "source": "official_AVEC2017_train_dev_split_csv",
    }
    return table, audit


def load_hamd_manifest_dataset(manifest_dir: Path, dataset: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = read_csv(manifest_dir / f"{dataset}_subjects.csv")
    required = {"subject_id", "file_valid", "hamd17_total", "hamd17_items"}
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"{dataset} manifest missing columns: {', '.join(sorted(missing))}")
    manifest = manifest[bool_series(manifest["file_valid"])].copy()
    manifest["subject_id"] = manifest["subject_id"].astype(str)
    raw_valid_subjects = int(manifest["subject_id"].nunique())

    rows: list[dict[str, Any]] = []
    skipped_subjects = 0
    code9_subjects = 0
    for subject_id, group in manifest.groupby("subject_id", sort=True):
        totals = sorted(
            {
                float(value)
                for value in pd.to_numeric(group["hamd17_total"], errors="coerce").dropna().tolist()
                if math.isfinite(float(value))
            }
        )
        payloads = [parse_json_dict(value) for value in group["hamd17_items"].tolist()]
        full_payloads = [payload for payload in payloads if all(item in payload for item in HAMD_ITEMS)]
        vectors = sorted(json.dumps({item: payload[item] for item in HAMD_ITEMS}, sort_keys=True) for payload in full_payloads)
        if len(totals) != 1 or not full_payloads or len(set(vectors)) != 1:
            skipped_subjects += 1
            continue
        payload = full_payloads[0]
        record: dict[str, Any] = {
            "dataset": dataset,
            "scale": "HAMD-17",
            "subject_id": str(subject_id),
            "hamd17_total": float(totals[0]),
            "severity_band": hamd_band(float(totals[0])),
            "scored_item_sum": 0.0,
            "raw_item_sum": 0.0,
            "contains_hamd_code_9": False,
        }
        for item in HAMD_ITEMS:
            value = safe_float(payload.get(item))
            if value is None:
                record[item] = np.nan
                continue
            record["raw_item_sum"] += value
            if value in MISSING_HAMD_CODES:
                record["contains_hamd_code_9"] = True
                record[item] = np.nan
            else:
                record["scored_item_sum"] += value
                record[item] = value
        if record["contains_hamd_code_9"]:
            code9_subjects += 1
        rows.append(record)

    table = pd.DataFrame(rows)
    if table.empty:
        raise ValueError(f"no HAMD item rows for {dataset}")
    table = table.sort_values("subject_id", key=lambda s: s.map(lambda value: tuple(natural_key(value)))).reset_index(drop=True)
    audit = {
        "analysis": "hamd_same_scale_exploratory",
        "dataset": dataset,
        "scale": "HAMD-17",
        "raw_valid_subjects": raw_valid_subjects,
        "complete_item_subjects": int(len(table)),
        "skipped_subjects": int(skipped_subjects),
        "code9_subjects": int(code9_subjects),
        "subject_collapse": "unique_subject_constant_label_payload",
        "code9_policy": "exclude item code 9 from item-level response and scored item sum",
    }
    return table, audit


def item_distribution(
    table: pd.DataFrame,
    item_cols: list[str],
    item_label_map: dict[str, str] | None,
    analysis: str,
    total_col: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=True):
        for item in item_cols:
            values = pd.to_numeric(group[item], errors="coerce").dropna()
            counts = Counter(values.astype(int).tolist())
            row = {
                "analysis": analysis,
                "dataset": dataset,
                "scale": str(group["scale"].iloc[0]) if "scale" in group else "",
                "item_id": item,
                "item_label_short": item_label_map.get(item, item) if item_label_map else item,
                "observed_subjects": int(values.size),
                "total_mean": safe_float(pd.to_numeric(group[total_col], errors="coerce").mean()),
                "mean": safe_float(values.mean()) if values.size else None,
                "variance": safe_float(values.var(ddof=1)) if values.size > 1 else None,
                "sd": safe_float(values.std(ddof=1)) if values.size > 1 else None,
                "min": safe_float(values.min()) if values.size else None,
                "max": safe_float(values.max()) if values.size else None,
                "nonzero_rate": safe_float((values > 0).mean()) if values.size else None,
            }
            max_category = int(max(3, values.max() if values.size else 3))
            for category in range(0, max_category + 1):
                count = int(counts.get(category, 0))
                row[f"category_{category}_count"] = count
                row[f"category_{category}_proportion"] = safe_float(count / values.size) if values.size else None
            rows.append(row)
    return pd.DataFrame(rows)


def category_proportions(
    table: pd.DataFrame,
    item_cols: list[str],
    item_label_map: dict[str, str] | None,
    analysis: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=True):
        for item in item_cols:
            values = pd.to_numeric(group[item], errors="coerce").dropna()
            if values.empty:
                continue
            max_category = int(max(3, values.max()))
            counts = Counter(values.astype(int).tolist())
            for category in range(0, max_category + 1):
                count = int(counts.get(category, 0))
                rows.append(
                    {
                        "analysis": analysis,
                        "dataset": dataset,
                        "scale": str(group["scale"].iloc[0]) if "scale" in group else "",
                        "item_id": item,
                        "item_label_short": item_label_map.get(item, item) if item_label_map else item,
                        "category": int(category),
                        "count": count,
                        "proportion": safe_float(count / values.size),
                        "observed_subjects": int(values.size),
                    }
                )
    return pd.DataFrame(rows)


def add_item_excluded_bins(table: pd.DataFrame, item_cols: list[str], total_col: str) -> pd.DataFrame:
    frame = table.copy()
    for item in item_cols:
        frame[f"{item}_severity_excluding_item"] = pd.to_numeric(frame[total_col], errors="coerce") - pd.to_numeric(
            frame[item], errors="coerce"
        )
    return frame


def tertile_bin_edges(values: pd.Series) -> tuple[float, float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return 0.0, 0.0
    low = float(np.quantile(numeric, 1 / 3))
    high = float(np.quantile(numeric, 2 / 3))
    if high < low:
        high = low
    return low, high


def assign_tertile(value: Any, low: float, high: float) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "missing"
    if numeric <= low:
        return "low"
    if numeric <= high:
        return "middle"
    return "high"


def severity_conditioned_response(
    table: pd.DataFrame,
    item_cols: list[str],
    item_label_map: dict[str, str] | None,
    analysis: str,
    total_col: str,
    scope_col: str | None = None,
) -> pd.DataFrame:
    frame = add_item_excluded_bins(table, item_cols, total_col)
    rows: list[dict[str, Any]] = []
    if scope_col is None:
        scope_iter = [("all_subjects", frame)]
    else:
        scope_iter = [(str(scope), group.copy()) for scope, group in frame.groupby(scope_col, sort=True)]

    for scope, scope_frame in scope_iter:
        for item in item_cols:
            score_col = f"{item}_severity_excluding_item"
            low, high = tertile_bin_edges(scope_frame[score_col])
            scope_frame = scope_frame.copy()
            scope_frame["condition_bin"] = scope_frame[score_col].map(lambda value: assign_tertile(value, low, high))
            for dataset, dataset_group in scope_frame.groupby("dataset", sort=True):
                for condition_bin, group in dataset_group.groupby("condition_bin", sort=True):
                    if condition_bin == "missing":
                        continue
                    values = pd.to_numeric(group[item], errors="coerce").dropna()
                    if values.empty:
                        continue
                    max_category = int(max(3, values.max()))
                    row = {
                        "analysis": analysis,
                        "scope": scope,
                        "dataset": dataset,
                        "scale": str(group["scale"].iloc[0]) if "scale" in group else "",
                        "item_id": item,
                        "item_label_short": item_label_map.get(item, item) if item_label_map else item,
                        "conditioning": "pooled_item_excluded_total_tertiles",
                        "condition_bin": condition_bin,
                        "condition_lower_cut": low,
                        "condition_upper_cut": high,
                        "subjects": int(values.size),
                        "sparse_bin": bool(values.size < MIN_CONDITION_BIN_N),
                        "item_mean": safe_float(values.mean()),
                        "item_variance": safe_float(values.var(ddof=1)) if values.size > 1 else None,
                    }
                    for threshold in [1, 2, 3]:
                        row[f"p_ge_{threshold}"] = safe_float((values >= threshold).mean())
                    for category in range(0, max_category + 1):
                        row[f"category_{category}_proportion"] = safe_float((values == category).mean())
                    rows.append(row)
    return pd.DataFrame(rows)


def conditioned_deltas(conditioned: pd.DataFrame, left_dataset: str, right_dataset: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    key_cols = ["analysis", "scope", "item_id", "item_label_short", "condition_bin", "conditioning"]
    for key, group in conditioned.groupby(key_cols, dropna=False, sort=True):
        records = {str(row["dataset"]): row for _, row in group.iterrows()}
        if left_dataset not in records or right_dataset not in records:
            continue
        left = records[left_dataset]
        right = records[right_dataset]
        left_n = int(left["subjects"])
        right_n = int(right["subjects"])
        rows.append(
            {
                "analysis": key[0],
                "scope": key[1],
                "item_id": key[2],
                "item_label_short": key[3],
                "condition_bin": key[4],
                "conditioning": key[5],
                "left_dataset": left_dataset,
                "right_dataset": right_dataset,
                "left_subjects": left_n,
                "right_subjects": right_n,
                "min_subjects": min(left_n, right_n),
                "sparse_comparison": bool(min(left_n, right_n) < MIN_CONDITION_BIN_N),
                "item_mean_diff_left_minus_right": safe_float(left["item_mean"] - right["item_mean"]),
                "p_ge_1_diff_left_minus_right": safe_float(left["p_ge_1"] - right["p_ge_1"]),
                "p_ge_2_diff_left_minus_right": safe_float(left["p_ge_2"] - right["p_ge_2"]),
                "p_ge_3_diff_left_minus_right": safe_float(left["p_ge_3"] - right["p_ge_3"]),
            }
        )
    return pd.DataFrame(rows)


def total_band_summary(table: pd.DataFrame, total_col: str, band_col: str, analysis: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in table.groupby("dataset", sort=True):
        total_values = pd.to_numeric(group[total_col], errors="coerce").dropna()
        counts = Counter(group[band_col].astype(str).tolist())
        for band, count in sorted(counts.items()):
            rows.append(
                {
                    "analysis": analysis,
                    "dataset": dataset,
                    "scale": str(group["scale"].iloc[0]) if "scale" in group else "",
                    "severity_band": band,
                    "subjects": int(count),
                    "proportion": safe_float(count / len(group)),
                    "total_mean": safe_float(total_values.mean()) if not total_values.empty else None,
                    "total_sd": safe_float(total_values.std(ddof=1)) if len(total_values) > 1 else None,
                }
            )
    return pd.DataFrame(rows)


def scope_hamd(table: pd.DataFrame) -> pd.DataFrame:
    frame = table.copy()
    frame["scope_all_subjects"] = "all_subjects"
    frame["scope_overlap_mild_moderate"] = np.where(
        frame["severity_band"].isin({"mild", "moderate"}),
        "overlap_mild_moderate",
        "not_in_overlap",
    )
    return frame


def hamd_scope_audit(table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope, group in [
        ("all_subjects", table),
        ("overlap_mild_moderate", table[table["severity_band"].isin({"mild", "moderate"})].copy()),
    ]:
        for dataset, dataset_group in group.groupby("dataset", sort=True):
            total = pd.to_numeric(dataset_group["hamd17_total"], errors="coerce")
            rows.append(
                {
                    "analysis": "hamd_same_scale_exploratory",
                    "scope": scope,
                    "dataset": dataset,
                    "scale": "HAMD-17",
                    "subjects": int(dataset_group["subject_id"].nunique()),
                    "hamd_total_mean": safe_float(total.mean()),
                    "hamd_total_sd": safe_float(total.std(ddof=1)) if len(total.dropna()) > 1 else None,
                    "severity_band_counts": json.dumps(dict(sorted(Counter(dataset_group["severity_band"]).items())), sort_keys=True),
                    "code9_subjects": int(dataset_group["contains_hamd_code_9"].sum()),
                    "min_observed_item_subjects": int(min(pd.to_numeric(dataset_group[item], errors="coerce").notna().sum() for item in HAMD_ITEMS)),
                    "max_observed_item_subjects": int(max(pd.to_numeric(dataset_group[item], errors="coerce").notna().sum() for item in HAMD_ITEMS)),
                }
            )
    return pd.DataFrame(rows)


def hamd_correlation_summary(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    for scope, group in [
        ("all_subjects", table),
        ("overlap_mild_moderate", table[table["severity_band"].isin({"mild", "moderate"})].copy()),
    ]:
        for dataset, dataset_group in group.groupby("dataset", sort=True):
            for idx, left in enumerate(HAMD_ITEMS):
                for right in HAMD_ITEMS[idx + 1 :]:
                    pair = dataset_group[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
                    if len(pair) < 4:
                        rho = None
                    else:
                        rho = safe_float(pair[left].corr(pair[right], method="spearman"))
                    rows.append(
                        {
                            "analysis": "hamd_same_scale_exploratory",
                            "scope": scope,
                            "dataset": dataset,
                            "left_item_id": left,
                            "right_item_id": right,
                            "pairwise_subjects": int(len(pair)),
                            "spearman_r": rho,
                        }
                    )
    summary = pd.DataFrame(rows)
    delta_rows: list[dict[str, Any]] = []
    for key, group in summary.groupby(["scope", "left_item_id", "right_item_id"], sort=True):
        records = {str(row["dataset"]): row for _, row in group.iterrows()}
        if "cmdc" not in records or "pdch" not in records:
            continue
        cmdc_r = safe_float(records["cmdc"]["spearman_r"])
        pdch_r = safe_float(records["pdch"]["spearman_r"])
        delta = abs(cmdc_r - pdch_r) if cmdc_r is not None and pdch_r is not None else None
        delta_rows.append(
            {
                "analysis": "hamd_same_scale_exploratory",
                "scope": key[0],
                "left_item_id": key[1],
                "right_item_id": key[2],
                "cmdc_pairwise_subjects": int(records["cmdc"]["pairwise_subjects"]),
                "pdch_pairwise_subjects": int(records["pdch"]["pairwise_subjects"]),
                "cmdc_spearman_r": cmdc_r,
                "pdch_spearman_r": pdch_r,
                "abs_spearman_delta": safe_float(delta),
                "interpretation": "descriptive_ordinal_pairwise_structure_not_formal_invariance_test",
            }
        )
    delta_summary = pd.DataFrame(delta_rows).sort_values(
        ["scope", "abs_spearman_delta"], ascending=[True, False], na_position="last"
    )
    return summary, delta_summary


def daicwoz_edaic_scope_audit(
    daicwoz: pd.DataFrame,
    edaic: pd.DataFrame,
    daicwoz_input_audit: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    daic_ids = set(daicwoz["subject_id"].astype(str))
    edaic_ids = set(edaic["subject_id"].astype(str))
    intersection = sorted(daic_ids & edaic_ids, key=natural_key)
    daic_only = sorted(daic_ids - edaic_ids, key=natural_key)
    edaic_only = sorted(edaic_ids - daic_ids, key=natural_key)

    paired_rows: list[dict[str, Any]] = []
    daic_index = daicwoz.set_index("subject_id")
    edaic_index = edaic.set_index("subject_id")
    for item in PHQ_CONSTRUCTS:
        diffs: list[float] = []
        exact = 0
        for subject_id in intersection:
            left = safe_float(daic_index.loc[subject_id, item])
            right = safe_float(edaic_index.loc[subject_id, item])
            if left is None or right is None:
                continue
            diff = left - right
            diffs.append(diff)
            if abs(diff) <= 1e-12:
                exact += 1
        arr = np.asarray(diffs, dtype=float)
        paired_rows.append(
            {
                "analysis": "daicwoz_edaic_same_phq8_lineage_control",
                "item_id": item,
                "item_label_short": ITEM_LABELS[item],
                "paired_subjects": int(arr.size),
                "exact_match_subjects": int(exact),
                "exact_match_rate": safe_float(exact / arr.size) if arr.size else None,
                "mean_daicwoz_minus_edaic": safe_float(arr.mean()) if arr.size else None,
                "mean_abs_difference": safe_float(np.abs(arr).mean()) if arr.size else None,
                "max_abs_difference": safe_float(np.abs(arr).max()) if arr.size else None,
                "interpretation": "paired_label_contract_check_on_overlapping_subject_ids",
            }
        )
    scope_rows = [
        {
            "analysis": "daicwoz_edaic_same_phq8_lineage_control",
            "scope": "official_train_dev_item_labeled",
            "daicwoz_raw_train_dev_rows": int(daicwoz_input_audit["raw_train_dev_rows"]),
            "daicwoz_incomplete_item_rows": int(daicwoz_input_audit["incomplete_item_rows"]),
            "daicwoz_subjects": int(len(daic_ids)),
            "edaic_subjects": int(len(edaic_ids)),
            "overlapping_subject_ids": int(len(intersection)),
            "daicwoz_only_subject_ids": int(len(daic_only)),
            "edaic_only_subject_ids": int(len(edaic_only)),
            "independence_claim": "not_independent_corpus_due_source_lineage_and_subject_overlap",
            "intended_role": "same_scale_language_protocol_lineage_control",
        }
    ]
    return pd.DataFrame(scope_rows), pd.DataFrame(paired_rows)


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    phq_audit: pd.DataFrame,
    hamd_audit: pd.DataFrame,
    daic_audit: pd.DataFrame,
    phq_delta: pd.DataFrame,
    hamd_delta: pd.DataFrame,
    hamd_corr_delta: pd.DataFrame,
    daic_paired: pd.DataFrame,
    daic_delta: pd.DataFrame,
) -> None:
    lines: list[str] = [
        "# MV21 Measurement-Discrepancy Gradient",
        "",
        f"- Run id: `{RUN_ID}`",
        f"- Generated: `{run_summary['generated_at_utc']}`",
        f"- Status: `{run_summary['status']}`",
        "",
        "## Scope",
        "",
        "This is a label-only descriptive reinforcement. It does not run HAMD MIM/IRT,",
        "does not fit a new formal psychometric model, and does not treat DAIC-WOZ as",
        "an independent corpus. Severity-conditioned tables use pooled item-excluded",
        "total-score tertiles to avoid the strongest part-whole artifact.",
        "",
        "## Input Counts",
        "",
        "| Analysis | Dataset | Scale | Complete subjects | Split/filter |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for _, row in phq_audit.iterrows():
        lines.append(
            f"| {row['analysis']} | {row['dataset']} | {row['scale']} | "
            f"{int(row['complete_item_subjects'])} | {row['split_filter']} |"
        )
    for _, row in hamd_audit.iterrows():
        lines.append(
            f"| {row['analysis']} | {row['dataset']} | {row['scale']} | "
            f"{int(row['complete_item_subjects'])} | all_valid |"
        )
    daic_row = daic_audit.iloc[0]
    lines.extend(
        [
            f"| daicwoz_edaic_same_phq8_lineage_control | daicwoz/edaic | PHQ-8 | "
            f"{int(daic_row['overlapping_subject_ids'])} paired overlap | train/dev item labels |",
            "",
            "## PHQ Shared Items",
            "",
        ]
    )
    phq_top = phq_delta[~phq_delta["sparse_comparison"]].copy()
    if not phq_top.empty:
        phq_top["abs_mean_diff"] = phq_top["item_mean_diff_left_minus_right"].abs()
        phq_top = phq_top.sort_values("abs_mean_diff", ascending=False).head(8)
        lines.extend(["Top non-sparse severity-conditioned E-DAIC minus CMDC item-mean deltas:", ""])
        lines.append("| Item | Bin | n min | Mean delta | P>=2 delta |")
        lines.append("| --- | --- | ---: | ---: | ---: |")
        for _, row in phq_top.iterrows():
            lines.append(
                f"| {row['item_id']} {row['item_label_short']} | {row['condition_bin']} | "
                f"{int(row['min_subjects'])} | {fmt(row['item_mean_diff_left_minus_right'])} | "
                f"{fmt(row['p_ge_2_diff_left_minus_right'])} |"
            )
    lines.extend(["", "## HAMD Same-Scale Control", ""])
    hamd_top = hamd_delta[~hamd_delta["sparse_comparison"]].copy()
    if not hamd_top.empty:
        hamd_top["abs_mean_diff"] = hamd_top["item_mean_diff_left_minus_right"].abs()
        hamd_top = hamd_top.sort_values("abs_mean_diff", ascending=False).head(8)
        lines.extend(["Top non-sparse severity-conditioned CMDC minus PDCH item-mean deltas:", ""])
        lines.append("| Scope | Item | Bin | n min | Mean delta | P>=2 delta |")
        lines.append("| --- | --- | --- | ---: | ---: | ---: |")
        for _, row in hamd_top.iterrows():
            lines.append(
                f"| {row['scope']} | {row['item_id']} | {row['condition_bin']} | "
                f"{int(row['min_subjects'])} | {fmt(row['item_mean_diff_left_minus_right'])} | "
                f"{fmt(row['p_ge_2_diff_left_minus_right'])} |"
            )
    corr_top = hamd_corr_delta.dropna(subset=["abs_spearman_delta"]).head(8)
    if not corr_top.empty:
        lines.extend(["", "Top descriptive HAMD correlation-structure deltas:", ""])
        lines.append("| Scope | Pair | CMDC rho | PDCH rho | Abs delta |")
        lines.append("| --- | --- | ---: | ---: | ---: |")
        for _, row in corr_top.iterrows():
            lines.append(
                f"| {row['scope']} | {row['left_item_id']}-{row['right_item_id']} | "
                f"{fmt(row['cmdc_spearman_r'])} | {fmt(row['pdch_spearman_r'])} | "
                f"{fmt(row['abs_spearman_delta'])} |"
            )
    lines.extend(["", "## DAIC-WOZ/E-DAIC Control", ""])
    exact_min = safe_float(daic_paired["exact_match_rate"].min())
    mean_abs_max = safe_float(daic_paired["mean_abs_difference"].max())
    daic_delta_top = daic_delta[~daic_delta["sparse_comparison"]].copy()
    daic_max_conditioned = None
    if not daic_delta_top.empty:
        daic_delta_top["abs_mean_diff"] = daic_delta_top["item_mean_diff_left_minus_right"].abs()
        daic_max_conditioned = safe_float(daic_delta_top["abs_mean_diff"].max())
    lines.append(
        "DAIC-WOZ and E-DAIC are treated as a same-lineage benchmark/control, not two independent corpora. "
        f"Across paired train/dev overlapping subjects, minimum item exact-match rate is {fmt(exact_min)} "
        f"and maximum mean absolute item difference is {fmt(mean_abs_max)}. "
        f"The maximum non-sparse severity-conditioned DAIC-WOZ minus E-DAIC project-contract item-mean delta is {fmt(daic_max_conditioned)}."
    )
    lines.extend(
        [
            "",
            "## Output Files",
            "",
        ]
    )
    for name in sorted(TRACKED_FILES):
        lines.append(f"- `{name}`")
    lines.append("")
    out_dir.joinpath("report.md").write_text("\n".join(lines), encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    files = sorted(path.name for path in out_dir.iterdir() if path.is_file())
    unexpected = sorted(set(files) - TRACKED_FILES)
    files_for_expected_check = set(files) | {"artifact_hygiene_audit.json"}
    missing = sorted(TRACKED_FILES - files_for_expected_check)
    banned_column_hits: list[dict[str, str]] = []
    banned_columns = {"subject_id", "subject_key", "text_path", "audio_path", "video_path", "gait_path"}
    for path in sorted(out_dir.glob("*.csv")):
        columns = set(pd.read_csv(path, nrows=0).columns)
        hits = sorted(columns & banned_columns)
        for column in hits:
            banned_column_hits.append({"file": path.name, "column": column})
    path_like_content_hits: list[str] = []
    for path in sorted(out_dir.glob("*")):
        if path.is_file() and path.suffix in {".csv", ".json", ".md"}:
            text = path.read_text(encoding="utf-8")
            if "/root/autodl-tmp/datasets/" in text:
                path_like_content_hits.append(path.name)
    passed = not unexpected and not missing and not banned_column_hits and not path_like_content_hits
    audit = {
        "artifact_hygiene_passed": bool(passed),
        "checked_at_utc": utc_now(),
        "tracked_files_expected": sorted(TRACKED_FILES),
        "files_present": sorted(files_for_expected_check),
        "unexpected_files": unexpected,
        "missing_files": missing,
        "banned_column_hits": banned_column_hits,
        "path_like_content_hits": path_like_content_hits,
        "privacy_boundary": "aggregate_only_no_subject_rows_no_raw_text_no_media_paths",
    }
    out_dir.joinpath("artifact_hygiene_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    return audit


def run(manifest_dir: Path, daicwoz_split_dir: Path, out_dir: Path) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    edaic_phq, edaic_audit = load_phq_manifest_dataset(
        manifest_dir,
        "edaic",
        EDAIC_ITEM_MAP,
        "phq8_total",
        "phq8_items",
        "PHQ-8",
        {"train", "dev"},
    )
    cmdc_phq, cmdc_audit = load_phq_manifest_dataset(
        manifest_dir,
        "cmdc",
        CMDC_PHQ_ITEM_MAP,
        "phq9_total",
        "phq9_items",
        "PHQ-9",
        None,
    )
    phq = pd.concat([edaic_phq, cmdc_phq], ignore_index=True)
    phq_audit = pd.DataFrame([edaic_audit, cmdc_audit])
    phq_distribution = item_distribution(phq, PHQ_CONSTRUCTS, ITEM_LABELS, "phq_shared_item", "shared_total")
    phq_category = category_proportions(phq, PHQ_CONSTRUCTS, ITEM_LABELS, "phq_shared_item")
    phq_conditioned = severity_conditioned_response(
        phq,
        PHQ_CONSTRUCTS,
        ITEM_LABELS,
        "phq_shared_item",
        "shared_total",
    )
    phq_delta = conditioned_deltas(phq_conditioned, "edaic", "cmdc")
    phq_total_bands = total_band_summary(phq, "shared_total", "severity_band", "phq_shared_item")

    cmdc_hamd, cmdc_hamd_audit = load_hamd_manifest_dataset(manifest_dir, "cmdc")
    pdch_hamd, pdch_hamd_audit = load_hamd_manifest_dataset(manifest_dir, "pdch")
    hamd = pd.concat([cmdc_hamd, pdch_hamd], ignore_index=True)
    hamd_audit = pd.DataFrame([cmdc_hamd_audit, pdch_hamd_audit])
    hamd_distribution = item_distribution(hamd, HAMD_ITEMS, None, "hamd_same_scale_exploratory", "hamd17_total")
    hamd_category = category_proportions(hamd, HAMD_ITEMS, None, "hamd_same_scale_exploratory")
    hamd_scoped = hamd.copy()
    hamd_scoped["scope"] = "all_subjects"
    hamd_overlap = hamd[hamd["severity_band"].isin({"mild", "moderate"})].copy()
    hamd_overlap["scope"] = "overlap_mild_moderate"
    hamd_for_condition = pd.concat([hamd_scoped, hamd_overlap], ignore_index=True)
    hamd_conditioned = severity_conditioned_response(
        hamd_for_condition,
        HAMD_ITEMS,
        None,
        "hamd_same_scale_exploratory",
        "hamd17_total",
        "scope",
    )
    hamd_delta = conditioned_deltas(hamd_conditioned, "cmdc", "pdch")
    hamd_scope = hamd_scope_audit(hamd)
    hamd_corr, hamd_corr_delta = hamd_correlation_summary(hamd)

    daicwoz_phq, daicwoz_input_audit = load_daicwoz_split_phq8(daicwoz_split_dir)
    daic_audit, daic_paired = daicwoz_edaic_scope_audit(daicwoz_phq, edaic_phq, daicwoz_input_audit)
    daic_contract = pd.concat(
        [
            daicwoz_phq.assign(dataset="daicwoz_official_train_dev"),
            edaic_phq.assign(dataset="edaic_project_train_dev"),
            edaic_phq[~edaic_phq["subject_id"].isin(set(daicwoz_phq["subject_id"]))].assign(
                dataset="edaic_additional_train_dev_not_in_daicwoz"
            ),
        ],
        ignore_index=True,
    )
    daic_distribution = item_distribution(
        daic_contract,
        PHQ_CONSTRUCTS,
        ITEM_LABELS,
        "daicwoz_edaic_same_phq8_lineage_control",
        "shared_total",
    )
    daic_conditioned = severity_conditioned_response(
        daic_contract,
        PHQ_CONSTRUCTS,
        ITEM_LABELS,
        "daicwoz_edaic_same_phq8_lineage_control",
        "shared_total",
    )
    daic_delta = conditioned_deltas(daic_conditioned, "daicwoz_official_train_dev", "edaic_project_train_dev")

    outputs = {
        "phq_shared_scope_audit.csv": phq_audit,
        "phq_shared_item_distribution.csv": phq_distribution,
        "phq_shared_item_category_proportions.csv": phq_category,
        "phq_shared_severity_conditioned_response.csv": phq_conditioned,
        "phq_shared_conditioned_deltas.csv": phq_delta,
        "phq_shared_total_band_summary.csv": phq_total_bands,
        "hamd_scope_audit.csv": hamd_scope,
        "hamd_item_distribution.csv": hamd_distribution,
        "hamd_item_category_proportions.csv": hamd_category,
        "hamd_severity_conditioned_response.csv": hamd_conditioned,
        "hamd_conditioned_deltas.csv": hamd_delta,
        "hamd_item_correlation_summary.csv": hamd_corr,
        "hamd_item_correlation_delta_summary.csv": hamd_corr_delta,
        "daicwoz_edaic_scope_audit.csv": daic_audit,
        "daicwoz_edaic_paired_item_differences.csv": daic_paired,
        "daicwoz_edaic_contract_distribution.csv": daic_distribution,
        "daicwoz_edaic_severity_conditioned_response.csv": daic_conditioned,
        "daicwoz_edaic_conditioned_deltas.csv": daic_delta,
    }
    for filename, frame in outputs.items():
        frame.to_csv(out_dir / filename, index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at_utc": utc_now(),
        "status": "complete_descriptive_measurement_gradient_reinforcement",
        "manifest_dir": rel(manifest_dir),
        "daicwoz_split_dir": rel(daicwoz_split_dir),
        "output_dir": rel(out_dir),
        "phq_edaic_subjects": int(len(edaic_phq)),
        "phq_cmdc_subjects": int(len(cmdc_phq)),
        "hamd_cmdc_subjects": int(len(cmdc_hamd)),
        "hamd_pdch_subjects": int(len(pdch_hamd)),
        "daicwoz_train_dev_item_subjects": int(len(daicwoz_phq)),
        "daicwoz_train_dev_rows": int(daicwoz_input_audit["raw_train_dev_rows"]),
        "daicwoz_incomplete_item_rows": int(daicwoz_input_audit["incomplete_item_rows"]),
        "edaic_train_dev_item_subjects": int(len(edaic_phq)),
        "daicwoz_edaic_paired_subjects": int(daic_audit.iloc[0]["overlapping_subject_ids"]),
        "formal_psychometric_model": "not_run",
        "hamd_mim_irt": "not_run",
        "privacy_boundary": "aggregate_only",
    }
    write_report(
        out_dir,
        run_summary,
        phq_audit,
        hamd_audit,
        daic_audit,
        phq_delta,
        hamd_delta,
        hamd_corr_delta,
        daic_paired,
        daic_delta,
    )
    out_dir.joinpath("run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True), encoding="utf-8")
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    out_dir.joinpath("run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True), encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError("artifact hygiene failed")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--daicwoz-split-dir", type=Path, default=DEFAULT_DAICWOZ_SPLIT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    summary = run(args.manifest_dir, args.daicwoz_split_dir, args.out_dir)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
