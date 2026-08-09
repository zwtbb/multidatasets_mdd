#!/usr/bin/env python3
"""Generate the Phase 2 unified baseline matrix template and readiness audit."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path("/root/autodl-tmp")
DEFAULT_CONFIG = ROOT / "baselines" / "phase2_baseline_matrix.yaml"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines"
DEFAULT_RESULTS_GLOB = "*/phase2_metric_summary.csv"
REGISTRY_PATH = ROOT / "datasets" / "registry.yaml"
MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"

TABLE_COLUMNS = [
    "dataset",
    "modality",
    "task",
    "model",
    "metric",
    "mean",
    "std",
    "ci95_low",
    "ci95_high",
    "seed_count",
    "status",
    "run_id",
]

STATUS_COLUMNS = [
    "run_id",
    "dataset",
    "modality",
    "task",
    "task_type",
    "target",
    "model",
    "family",
    "metrics",
    "required_seed_count",
    "bootstrap_resamples",
    "label_subjects",
    "valid_rows",
    "split_status",
    "split_protocol_count",
    "modality_status",
    "result_metric_count",
    "completed_metric_count",
    "status",
    "blockers",
]

MODALITY_PATH_COLUMNS = {
    "text": "text_path",
    "audio": "audio_path",
    "video": "video_path",
    "gait": "gait_path",
    "personality": "personality",
}

REQUIRED_RUN_FIELDS = {
    "id",
    "dataset",
    "display_dataset",
    "modality",
    "input_modalities",
    "task",
    "task_type",
    "target",
    "model",
    "family",
    "split_policy",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping")
    return data


def load_registry() -> dict[str, Any]:
    return load_yaml(REGISTRY_PATH)


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metric_sets = config.get("metric_sets", {})
    runs = config.get("runs", [])
    if not isinstance(runs, list) or not runs:
        errors.append("runs must be a non-empty list")
        return errors

    seen_ids: set[str] = set()
    families: set[str] = set()
    public_by_dataset: dict[str, set[str]] = {}
    for index, run in enumerate(runs):
        if not isinstance(run, dict):
            errors.append(f"runs[{index}] is not a mapping")
            continue
        missing = sorted(REQUIRED_RUN_FIELDS - set(run))
        if missing:
            errors.append(f"{run.get('id', f'runs[{index}]')} missing fields: {', '.join(missing)}")
        run_id = str(run.get("id", ""))
        if run_id in seen_ids:
            errors.append(f"duplicate run id: {run_id}")
        seen_ids.add(run_id)
        task_type = run.get("task_type")
        if task_type not in metric_sets:
            errors.append(f"{run_id} has unknown task_type: {task_type}")
        family = str(run.get("family", ""))
        families.add(family)
        public_name = run.get("public_name")
        if public_name:
            public_by_dataset.setdefault(str(run.get("dataset")), set()).add(str(public_name))

    coverage = config.get("coverage_requirements", {})
    for section in ["single_modal_families", "multimodal_families"]:
        for required in coverage.get(section, []):
            if required not in families:
                errors.append(f"missing required family coverage: {required}")
    for dataset, required_names in coverage.get("public_reproduction", {}).items():
        observed = public_by_dataset.get(dataset, set())
        for required in required_names:
            if required not in observed:
                errors.append(f"missing required public baseline for {dataset}: {required}")
    return errors


def load_result_summaries(out_dir: Path, pattern: str) -> dict[tuple[str, str], dict[str, Any]]:
    results: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(out_dir.glob(pattern)):
        if not path.exists() or not path.is_file():
            continue
        frame = pd.read_csv(path)
        required = {"run_id", "metric", "mean", "std", "seed_count"}
        missing = required - set(frame.columns)
        if missing:
            continue
        for _, row in frame.iterrows():
            key = (str(row["run_id"]), str(row["metric"]))
            results[key] = row.to_dict()
    return results


def load_split_index(path: Path) -> dict[tuple[str, str], set[str]]:
    if not path.exists():
        return {}
    frame = pd.read_csv(path)
    required = {"dataset", "target", "protocol_type"}
    if required - set(frame.columns):
        return {}
    index: dict[tuple[str, str], set[str]] = defaultdict(set)
    for _, row in frame.drop_duplicates(["dataset", "target", "protocol_type"]).iterrows():
        index[(str(row["dataset"]), str(row["target"]))].add(str(row["protocol_type"]))
    return index


def load_compatibility_gate(out_dir: Path, run_id: str) -> dict[str, Any] | None:
    candidates = [
        out_dir / "compatibility_gates" / f"{run_id}.json",
        out_dir / f"{run_id}_compatibility.json",
        out_dir / run_id / "compatibility_gate.json",
        out_dir / f"{run_id}_compatibility" / "compatibility_gate.json",
        out_dir / f"{run_id}_compatibility" / f"{run_id}_compatibility.json",
    ]
    for path in candidates:
        if not path.exists() or not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return None


def read_manifest(dataset: str) -> pd.DataFrame:
    path = MANIFEST_DIR / f"{dataset}_subjects.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def manifest_unit_frame(df: pd.DataFrame) -> pd.DataFrame:
    usable = df[df["subject_id"].astype(str) != "none"].copy()
    key_columns = [
        column
        for column in [
            "dataset",
            "subject_id",
            "session_id",
            "segment_id",
            "task_type",
            "official_split",
            "text_path",
            "audio_path",
            "gait_path",
        ]
        if column in usable.columns
    ]
    if not key_columns:
        return usable
    return usable.drop_duplicates(key_columns)


def manifest_summary(dataset: str) -> dict[str, Any]:
    df = read_manifest(dataset)
    if df.empty:
        return {
            "manifest_exists": False,
            "subjects": 0,
            "valid_rows": 0,
            "split_values": [],
            "split_subjects": 0,
            "label_subjects": {},
            "modality_subjects": {},
        }

    usable = df[df["subject_id"].astype(str) != "none"].copy()
    unit_rows = manifest_unit_frame(df)
    subject_rows = usable.drop_duplicates(["dataset", "subject_id"])
    label_subjects: dict[str, int] = {}
    for column in [
        "binary_label",
        "phq8_total",
        "phq8_items",
        "phq9_total",
        "phq9_items",
        "hamd17_total",
        "hamd17_items",
        "sds_total",
        "severity_label",
    ]:
        if column in subject_rows.columns:
            label_subjects[column] = int(subject_rows[column].notna().sum())

    modality_subjects: dict[str, int] = {}
    for modality, column in MODALITY_PATH_COLUMNS.items():
        if column not in usable.columns:
            modality_subjects[modality] = 0
            continue
        modality_subjects[modality] = int(
            usable.loc[usable[column].notna(), "subject_id"].astype(str).nunique()
        )
    value_subjects: dict[str, dict[str, int]] = {}
    for column in ["video_feature_type"]:
        if column not in usable.columns:
            continue
        counts: dict[str, int] = {}
        values = usable.loc[usable[column].notna(), column].astype(str)
        for value in sorted(values.unique()):
            mask = usable[column].astype(str) == value
            counts[value] = int(usable.loc[mask, "subject_id"].astype(str).nunique())
        value_subjects[column] = counts

    split_series = subject_rows.get("official_split", pd.Series(dtype=object)).dropna().astype(str)
    split_values = sorted(value for value in split_series.unique() if value.strip())
    return {
        "manifest_exists": True,
        "subjects": int(subject_rows["subject_id"].nunique()),
        "valid_rows": int(unit_rows["file_valid"].fillna(False).sum())
        if "file_valid" in unit_rows
        else int(len(unit_rows)),
        "split_values": split_values,
        "split_subjects": int(split_series[split_series.str.strip() != ""].shape[0]),
        "label_subjects": label_subjects,
        "modality_subjects": modality_subjects,
        "value_subjects": value_subjects,
    }


def split_status(
    run: dict[str, Any],
    summary: dict[str, Any],
    split_index: dict[tuple[str, str], set[str]],
) -> tuple[str, int, list[str]]:
    policy = str(run.get("split_policy", ""))
    dataset = str(run.get("dataset"))
    target = str(run.get("target"))
    protocols = split_index.get((dataset, target), set())
    split_subjects = int(summary.get("split_subjects") or 0)
    split_values = summary.get("split_values") or []
    blockers: list[str] = []
    if "official_or_subject_cv_required" in policy:
        if "official_subject_cv" in protocols:
            return "official_cv_available", len(protocols), blockers
        if "subject_cv" in protocols:
            return "subject_cv_available", len(protocols), blockers
        if "subject_cv_fallback" in protocols:
            return "subject_cv_fallback_available", len(protocols), blockers
        blockers.append("official_or_subject_cv_policy_not_materialized_in_root_manifest")
        return "needs_cv_policy", len(protocols), blockers
    if "official_cv_required" in policy:
        if "official_subject_cv" in protocols:
            return "official_cv_available", len(protocols), blockers
        if "subject_cv" in protocols:
            return "subject_cv_available", len(protocols), blockers
        if "subject_cv_fallback" in protocols:
            return "subject_cv_fallback_available", len(protocols), blockers
        blockers.append("official_cv_policy_not_materialized_in_root_manifest")
        return "needs_official_cv", len(protocols), blockers
    if "cross_task" in policy or "task_specific" in policy:
        required = {"task_specific", "cross_task"} if "and_cross_task" in policy else set()
        if "task_specific" in policy and "and_cross_task" not in policy:
            required.add("task_specific")
        if "cross_task" in policy and "and_cross_task" not in policy:
            required.add("cross_task")
        if required and required.issubset(protocols):
            return "task_protocol_available", len(protocols), blockers
        blockers.append("task_specific_and_cross_task_split_protocol_not_materialized")
        return "needs_task_protocol", len(protocols), blockers
    if split_subjects <= 0:
        blockers.append("missing_subject_level_split_in_manifest")
        return "missing", len(protocols), blockers
    if split_values == ["test"]:
        blockers.append("only_test_split_observed")
        return "invalid", len(protocols), blockers
    return "available", len(protocols), blockers


def modality_status(run: dict[str, Any], summary: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if not summary.get("manifest_exists"):
        return "manifest_missing", ["manifest_missing"]
    subjects = int(summary.get("subjects") or 0)
    modality_subjects = summary.get("modality_subjects") or {}
    missing_modalities: list[str] = []
    for modality in run.get("input_modalities", []):
        if modality == "personality":
            if int(modality_subjects.get("personality", 0)) <= 0:
                missing_modalities.append(modality)
            continue
        if int(modality_subjects.get(str(modality), 0)) <= 0:
            missing_modalities.append(str(modality))
    if missing_modalities:
        blockers.append("missing_manifest_modality_paths:" + ",".join(sorted(missing_modalities)))
        return "missing_paths", blockers
    value_subjects = summary.get("value_subjects") or {}
    for column, expected in (run.get("required_manifest_values") or {}).items():
        expected_values = expected if isinstance(expected, list) else [expected]
        observed = value_subjects.get(str(column), {})
        if not any(int(observed.get(str(value), 0)) > 0 for value in expected_values):
            joined = "|".join(str(value) for value in expected_values)
            blockers.append(f"missing_manifest_value:{column}={joined}")
    if subjects and any(int(modality_subjects.get(str(m), 0)) < subjects for m in run.get("input_modalities", []) if m != "personality"):
        return "partial_paths", blockers
    if blockers:
        return "paths_available_missing_required_values", blockers
    return "paths_available", blockers


def readiness_row(
    run: dict[str, Any],
    config: dict[str, Any],
    summary: dict[str, Any],
    results: dict[tuple[str, str], dict[str, Any]],
    split_index: dict[tuple[str, str], set[str]],
    out_dir: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    target = str(run.get("target"))
    label_subjects = int((summary.get("label_subjects") or {}).get(target, 0))
    if label_subjects <= 0:
        blockers.append("missing_target_labels")
    split_state, split_protocol_count, split_blockers = split_status(run, summary, split_index)
    modality_state, modality_blockers = modality_status(run, summary)
    blockers.extend(split_blockers)
    blockers.extend(modality_blockers)
    metrics = config["metric_sets"][run["task_type"]]
    minimum_seeds = int(config["policy"]["minimum_random_seeds"])
    result_rows = [results[(run["id"], metric)] for metric in metrics if (run["id"], metric) in results]
    completed_metrics = [
        row for row in result_rows if int(row.get("seed_count") or 0) >= minimum_seeds and pd.notna(row.get("mean"))
    ]
    has_complete_result = len(completed_metrics) == len(metrics)
    compatibility_not_applicable = False
    compatibility_pending = False
    if run.get("compatibility_gate") and not has_complete_result:
        gate = load_compatibility_gate(out_dir, str(run["id"]))
        gate_status = str((gate or {}).get("status", "")).strip().lower()
        if gate_status == "passed":
            pass
        elif gate_status in {"not_applicable", "inapplicable"}:
            compatibility_not_applicable = True
            blockers.append("compatibility_gate_not_applicable")
        elif gate_status == "failed":
            blockers.append("compatibility_gate_failed")
        else:
            compatibility_pending = True
            blockers.append("compatibility_gate_not_yet_passed")
    if (
        run.get("family") == "public_reproduction"
        and not has_complete_result
        and not compatibility_not_applicable
        and "compatibility_gate_failed" not in blockers
    ):
        blockers.append("public_baseline_reproduction_not_yet_run")
    if compatibility_pending and "public_baseline_reproduction_not_yet_run" not in blockers:
        blockers.append("public_baseline_reproduction_not_yet_run")
    if has_complete_result:
        status = "completed"
    elif compatibility_not_applicable:
        status = "not_applicable"
    elif result_rows:
        status = "partial_results"
    elif blockers:
        status = "planned_blocked_by_prerequisites"
    else:
        status = "planned_ready_for_feature_extraction_or_training"
    policy = config["policy"]
    return {
        "run_id": run["id"],
        "dataset": run["display_dataset"],
        "modality": run["modality"],
        "task": run["task"],
        "task_type": run["task_type"],
        "target": target,
        "model": run["model"],
        "family": run["family"],
        "metrics": ";".join(metrics),
        "required_seed_count": policy["minimum_random_seeds"],
        "bootstrap_resamples": policy["bootstrap"]["resamples"],
        "label_subjects": label_subjects,
        "valid_rows": int(summary.get("valid_rows") or 0),
        "split_status": split_state,
        "split_protocol_count": split_protocol_count,
        "modality_status": modality_state,
        "result_metric_count": len(result_rows),
        "completed_metric_count": len(completed_metrics),
        "status": status,
        "blockers": ";".join(blockers),
    }


def matrix_rows(
    config: dict[str, Any],
    status_rows: list[dict[str, Any]],
    results: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    status_by_id = {row["run_id"]: row for row in status_rows}
    rows: list[dict[str, Any]] = []
    for run in config["runs"]:
        status = status_by_id[run["id"]]
        for metric in config["metric_sets"][run["task_type"]]:
            result = results.get((run["id"], metric), {})
            seed_count = int(result.get("seed_count") or 0) if result else 0
            row_status = "completed" if status["status"] == "completed" else status["status"]
            rows.append(
                {
                    "dataset": run["display_dataset"],
                    "modality": run["modality"],
                    "task": run["task"],
                    "model": run["model"],
                    "metric": metric,
                    "mean": result.get("mean", ""),
                    "std": result.get("std", ""),
                    "ci95_low": result.get("ci95_low", ""),
                    "ci95_high": result.get("ci95_high", ""),
                    "seed_count": seed_count,
                    "status": row_status,
                    "run_id": run["id"],
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_summary(
    path: Path,
    config: dict[str, Any],
    status_rows: list[dict[str, Any]],
    errors: list[str],
    results: dict[tuple[str, str], dict[str, Any]],
) -> None:
    status_counts = Counter(row["status"] for row in status_rows)
    dataset_counts = Counter(row["dataset"] for row in status_rows)
    family_counts = Counter(row["family"] for row in status_rows)
    blockers = Counter(
        blocker
        for row in status_rows
        for blocker in str(row.get("blockers") or "").split(";")
        if blocker
    )
    policy = config["policy"]
    completed_runs = [row for row in status_rows if row["status"] == "completed"]
    partial_runs = [row for row in status_rows if row["status"] == "partial_results"]
    lines = [
        "# Phase 2 Baseline Matrix Summary",
        "",
        f"Generated: `{utc_now()}`",
        "",
        "## Policy",
        "",
        f"- Minimum random seeds: `{policy['minimum_random_seeds']}`",
        f"- Seeds: `{policy['random_seeds']}`",
        f"- Bootstrap resamples: `{policy['bootstrap']['resamples']}`",
        f"- Bootstrap unit: `{policy['bootstrap']['resample_unit']}`",
        f"- Hyperparameter selection: `{policy['hyperparameter_selection']}`",
        f"- Test-set policy: `{policy['test_set_policy']}`",
        f"- Pretrained encoder policy: `{policy['pretrained_encoder_policy']}`",
        "",
        "## Matrix Coverage",
        "",
        f"- Planned runs: `{len(status_rows)}`",
        f"- Status counts: `{dict(sorted(status_counts.items()))}`",
        f"- Dataset counts: `{dict(sorted(dataset_counts.items()))}`",
        f"- Family counts: `{dict(sorted(family_counts.items()))}`",
        f"- Completed runs: `{len(completed_runs)}`",
        f"- Partial-result runs: `{len(partial_runs)}`",
        f"- Completed metric rows loaded: `{len(results)}`",
        "",
        "## Current Prerequisite Blockers",
        "",
    ]
    if blockers:
        for blocker, count in sorted(blockers.items()):
            lines.append(f"- `{blocker}`: `{count}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Config Validation", ""])
    if errors:
        for error in errors:
            lines.append(f"- ERROR: `{error}`")
    else:
        lines.append("- Passed.")
    lines.extend(
        [
            "",
            "The CSV matrix fills `mean`, `std`, and confidence interval fields only",
            "when a validated result summary is available. Rows without audited",
            "five-seed results remain blank.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--results-glob", default=DEFAULT_RESULTS_GLOB)
    parser.add_argument("--split-path", type=Path, default=DEFAULT_SPLIT_PATH)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on config validation errors.")
    args = parser.parse_args()

    config = load_yaml(args.config)
    errors = validate_config(config)
    if args.strict and errors:
        raise SystemExit("\n".join(errors))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results = load_result_summaries(args.out_dir, args.results_glob)
    split_index = load_split_index(args.split_path)
    registry = load_registry()
    summaries = {dataset: manifest_summary(dataset) for dataset in registry}
    status_rows = [
        readiness_row(run, config, summaries.get(run["dataset"], {"manifest_exists": False}), results, split_index, args.out_dir)
        for run in config["runs"]
    ]
    rows = matrix_rows(config, status_rows, results)

    write_csv(args.out_dir / "baseline_matrix_template.csv", rows, TABLE_COLUMNS)
    write_csv(args.out_dir / "baseline_matrix_status.csv", status_rows, STATUS_COLUMNS)
    (args.out_dir / "baseline_matrix_manifest_summary.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_summary(args.out_dir / "baseline_matrix_summary.md", config, status_rows, errors, results)

    print(f"Wrote {args.out_dir / 'baseline_matrix_template.csv'}")
    print(f"Wrote {args.out_dir / 'baseline_matrix_status.csv'}")
    print(f"Wrote {args.out_dir / 'baseline_matrix_summary.md'}")
    if errors:
        print("Config validation warnings:")
        for error in errors:
            print(f"- {error}")


if __name__ == "__main__":
    main()
