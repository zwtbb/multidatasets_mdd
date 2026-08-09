#!/usr/bin/env python3
"""Audit Phase 2 baseline result artifacts for reproducibility hygiene."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path("/root/autodl-tmp")
BASELINE_DIR = ROOT / "analysis" / "phase2_baselines"
STATUS_CSV = BASELINE_DIR / "baseline_matrix_status.csv"
TEMPLATE_CSV = BASELINE_DIR / "baseline_matrix_template.csv"
DEFAULT_OUT_DIR = BASELINE_DIR / "phase2_artifact_hygiene_audit"

SUMMARY_GLOB = "*/phase2_metric_summary.csv"
SEED_GLOB = "*/phase2_metrics_by_seed.csv"
PREDICTION_GLOB = "*predictions*.csv"
RUN_SUMMARY_GLOB = "*run_summary.json"

EXPECTED_SEEDS = {0, 1, 2, 3, 4}
TERMINAL_OK_STATUSES = {"completed", "not_applicable"}
NUMERIC_REQUIRED_SUMMARY_COLUMNS = ["mean", "std", "ci95_low", "ci95_high", "seed_count"]
NUMERIC_REQUIRED_SEED_COLUMNS = ["value", "ci95_low", "ci95_high", "sample_count"]

LEAKY_COLUMN_PATTERNS = [
    re.compile(r"(^|_)(raw_text|raw_audio|raw_video|raw_response|raw_prompt)(_|$)"),
    re.compile(r"(^|_)(transcript|prompt|response)(_|$)"),
    re.compile(r"(^|_)(text|audio|video|wav|source|data)?_?path(_|$)"),
    re.compile(r"(^|_)(file_name|filename|source_file)(_|$)"),
    re.compile(r"(^|_)personality_text(_|$)"),
]

LEAKY_VALUE_PATTERNS = [
    re.compile(r"/root/"),
    re.compile(r"/tmp/"),
    re.compile(r"autodl-tmp"),
    re.compile(r"datasets/"),
    re.compile(r"cache/"),
    re.compile(r"\.(wav|mp3|mp4|avi|mov|mkv|txt|csv|tsv|npy|npz|mat|pkl|xlsx)(\b|$)", re.I),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def finite_or_blank(value: Any) -> bool:
    if pd.isna(value):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def safe_read_csv(path: Path) -> tuple[pd.DataFrame, str | None]:
    try:
        return pd.read_csv(path), None
    except Exception as exc:  # noqa: BLE001 - audit should record bad files, not crash early.
        return pd.DataFrame(), f"{type(exc).__name__}: {exc}"


def load_metric_files(base_dir: Path, pattern: str) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    frames: list[pd.DataFrame] = []
    read_errors: list[dict[str, str]] = []
    for path in sorted(base_dir.glob(pattern)):
        frame, error = safe_read_csv(path)
        if error:
            read_errors.append({"path": str(path), "error": error})
            continue
        frame = frame.copy()
        frame["artifact_path"] = str(path)
        frame["artifact_dir"] = str(path.parent)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(), read_errors
    return pd.concat(frames, ignore_index=True), read_errors


def leaky_columns(columns: list[str]) -> list[str]:
    hits: list[str] = []
    for column in columns:
        normalized = str(column).strip().lower()
        if normalized.endswith("_count") or normalized.endswith("_seconds") or normalized.endswith("_minutes"):
            continue
        if normalized in {"context_minutes", "audio_clip_max_seconds"}:
            continue
        if any(pattern.search(normalized) for pattern in LEAKY_COLUMN_PATTERNS):
            hits.append(str(column))
    return hits


def leaky_value_count(frame: pd.DataFrame) -> int:
    total = 0
    for column in frame.columns:
        if not (pd.api.types.is_object_dtype(frame[column]) or pd.api.types.is_string_dtype(frame[column])):
            continue
        series = frame[column].dropna().astype(str)
        if series.empty:
            continue
        mask = series.apply(lambda value: any(pattern.search(value) for pattern in LEAKY_VALUE_PATTERNS))
        total += int(mask.sum())
    return total


def canonical_prediction_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(directory.glob(PREDICTION_GLOB)):
        name = path.name.lower()
        if "partial" in name or "progress" in name:
            continue
        files.append(path)
    return files


def prediction_audit_for_run(run_id: str, artifact_dirs: set[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    issues: list[str] = []
    for directory_text in sorted(artifact_dirs):
        directory = Path(directory_text)
        for path in canonical_prediction_files(directory):
            frame, error = safe_read_csv(path)
            if error:
                issues.append(f"prediction_read_error:{path}")
                rows.append({"run_id": run_id, "path": str(path), "read_error": error})
                continue
            if "run_id" not in frame.columns:
                continue
            selected = frame.loc[frame["run_id"].astype(str).eq(run_id)].copy()
            if selected.empty:
                continue
            seed_values: list[int] = []
            if "seed" in selected.columns:
                seed_values = sorted(
                    int(seed) for seed in pd.to_numeric(selected["seed"], errors="coerce").dropna().unique()
                )
            subject_count = (
                int(selected["subject_id"].astype(str).nunique()) if "subject_id" in selected.columns else None
            )
            column_hits = leaky_columns(list(selected.columns))
            value_hits = leaky_value_count(selected)
            if column_hits:
                issues.append(f"leaky_prediction_columns:{path.name}:{','.join(column_hits)}")
            if value_hits:
                issues.append(f"leaky_prediction_values:{path.name}:{value_hits}")
            rows.append(
                {
                    "run_id": run_id,
                    "path": str(path),
                    "rows": int(len(selected)),
                    "columns": int(len(selected.columns)),
                    "seed_values": ",".join(str(seed) for seed in seed_values),
                    "seed_count": len(seed_values) if seed_values else None,
                    "subject_count": subject_count,
                    "leaky_columns": ",".join(column_hits),
                    "leaky_value_count": int(value_hits),
                    "read_error": "",
                }
            )
    if not rows:
        issues.append("missing_canonical_prediction_file")
    return rows, issues


def list_run_summaries(artifact_dirs: set[str]) -> list[str]:
    paths: list[str] = []
    for directory_text in sorted(artifact_dirs):
        paths.extend(str(path) for path in sorted(Path(directory_text).glob(RUN_SUMMARY_GLOB)))
    return paths


def as_float_dict(row: pd.Series, columns: list[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for column in columns:
        if column not in row.index or pd.isna(row[column]):
            out[column] = None
            continue
        try:
            out[column] = float(row[column])
        except (TypeError, ValueError):
            out[column] = None
    return out


def metric_values_match(template_row: pd.Series, summary_row: pd.Series) -> bool:
    for column in ["mean", "std", "ci95_low", "ci95_high", "seed_count"]:
        left = as_float_dict(template_row, [column])[column]
        right = as_float_dict(summary_row, [column])[column]
        if left is None or right is None:
            return False
        if abs(left - right) > 1e-10:
            return False
    return True


def audit_run(
    run_id: str,
    expected_rows: pd.DataFrame,
    summary_rows: pd.DataFrame,
    seed_rows: pd.DataFrame,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    expected_metrics = sorted(expected_rows["metric"].astype(str).unique())

    if summary_rows.empty:
        artifact_dirs: set[str] = set()
        issues.append("missing_metric_summary_rows")
    else:
        artifact_dirs = set(summary_rows["artifact_dir"].astype(str).unique())

    observed_summary_metrics = sorted(summary_rows["metric"].astype(str).unique()) if not summary_rows.empty else []
    missing_summary_metrics = sorted(set(expected_metrics) - set(observed_summary_metrics))
    extra_summary_metrics = sorted(set(observed_summary_metrics) - set(expected_metrics))
    if missing_summary_metrics:
        issues.append(f"missing_summary_metrics:{','.join(missing_summary_metrics)}")
    if extra_summary_metrics:
        issues.append(f"extra_summary_metrics:{','.join(extra_summary_metrics)}")

    missing_numeric_count = 0
    mismatched_metric_count = 0
    for _, template_row in expected_rows.iterrows():
        metric = str(template_row["metric"])
        matching = summary_rows.loc[summary_rows["metric"].astype(str).eq(metric)]
        if matching.empty:
            continue
        summary_row = matching.iloc[0]
        missing_numeric_count += sum(
            1 for column in NUMERIC_REQUIRED_SUMMARY_COLUMNS if not finite_or_blank(summary_row.get(column))
        )
        if not metric_values_match(template_row, summary_row):
            mismatched_metric_count += 1
    if missing_numeric_count:
        issues.append(f"summary_missing_or_nonfinite_numeric:{missing_numeric_count}")
    if mismatched_metric_count:
        issues.append(f"summary_template_mismatch:{mismatched_metric_count}")

    summary_seed_values = []
    if not summary_rows.empty and "seed_count" in summary_rows.columns:
        summary_seed_values = sorted(
            int(seed) for seed in pd.to_numeric(summary_rows["seed_count"], errors="coerce").dropna().unique()
        )
        if summary_seed_values != [5]:
            issues.append(f"summary_seed_count_not_5:{summary_seed_values}")

    observed_seed_metrics = sorted(seed_rows["metric"].astype(str).unique()) if not seed_rows.empty else []
    missing_seed_metrics = sorted(set(expected_metrics) - set(observed_seed_metrics))
    if seed_rows.empty:
        issues.append("missing_seed_metric_rows")
    elif missing_seed_metrics:
        issues.append(f"missing_seed_metrics:{','.join(missing_seed_metrics)}")

    seed_metric_failures: dict[str, str] = {}
    nonfinite_seed_count = 0
    for metric in expected_metrics:
        metric_rows = seed_rows.loc[seed_rows["metric"].astype(str).eq(metric)].copy()
        if metric_rows.empty:
            continue
        seeds = set(int(seed) for seed in pd.to_numeric(metric_rows["seed"], errors="coerce").dropna().unique())
        if seeds != EXPECTED_SEEDS:
            seed_metric_failures[metric] = ",".join(str(seed) for seed in sorted(seeds))
        for _, row in metric_rows.iterrows():
            nonfinite_seed_count += sum(
                1 for column in NUMERIC_REQUIRED_SEED_COLUMNS if not finite_or_blank(row.get(column))
            )
    if seed_metric_failures:
        encoded = ";".join(f"{metric}={seeds}" for metric, seeds in sorted(seed_metric_failures.items()))
        issues.append(f"seed_set_not_0_4:{encoded}")
    if nonfinite_seed_count:
        issues.append(f"seed_missing_or_nonfinite_numeric:{nonfinite_seed_count}")

    prediction_rows, prediction_issues = prediction_audit_for_run(run_id, artifact_dirs)
    issues.extend(prediction_issues)

    run_summaries = list_run_summaries(artifact_dirs)
    if not run_summaries:
        issues.append("missing_run_summary_json")

    record = {
        "run_id": run_id,
        "expected_metric_count": int(len(expected_metrics)),
        "summary_metric_count": int(len(observed_summary_metrics)),
        "seed_metric_count": int(len(observed_seed_metrics)),
        "summary_paths": "|".join(sorted(summary_rows["artifact_path"].astype(str).unique()))
        if not summary_rows.empty
        else "",
        "seed_paths": "|".join(sorted(seed_rows["artifact_path"].astype(str).unique()))
        if not seed_rows.empty
        else "",
        "prediction_file_count": len(prediction_rows),
        "prediction_row_count": int(sum(int(row.get("rows") or 0) for row in prediction_rows)),
        "run_summary_count": len(run_summaries),
        "run_summary_paths": "|".join(run_summaries),
        "summary_seed_count_values": ",".join(str(seed) for seed in summary_seed_values),
        "missing_summary_metrics": ",".join(missing_summary_metrics),
        "extra_summary_metrics": ",".join(extra_summary_metrics),
        "missing_seed_metrics": ",".join(missing_seed_metrics),
        "issue_count": len(issues),
        "issues": "|".join(issues),
        "passed": len(issues) == 0,
    }
    return record, prediction_rows, issues


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase 2 Artifact Hygiene Audit",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Verdict",
        "",
        f"- Artifact hygiene passed: `{summary['artifact_hygiene_passed']}`",
        f"- Completed runs audited: `{summary['completed_runs_audited']}`",
        f"- Failed completed runs: `{summary['failed_completed_runs']}`",
        f"- Completed metric rows in matrix: `{summary['completed_metric_rows_in_matrix']}`",
        f"- Completed metric rows in summaries: `{summary['completed_metric_rows_in_summaries']}`",
        f"- Seed metric rows audited: `{summary['seed_metric_rows_audited']}`",
        f"- Canonical prediction files audited: `{summary['canonical_prediction_files_audited']}`",
        f"- Canonical prediction rows audited: `{summary['canonical_prediction_rows_audited']}`",
        f"- Prediction files with raw/path leakage indicators: `{summary['prediction_files_with_leak_indicators']}`",
        f"- Blocked runs with metric-summary rows: `{summary['blocked_runs_with_metric_summary_rows']}`",
        "",
        "## Scope",
        "",
        "- The audit treats `phase2_metric_summary.csv`, `phase2_metrics_by_seed.csv`, canonical `*predictions*.csv`, and `*run_summary.json` files as reproducibility evidence.",
        "- Files with `partial` or `progress` in the prediction filename are reported as non-canonical progress artifacts and are not used to prove completed matrix rows.",
        "- Leakage checks scan prediction column names and string values for raw transcript, prompt, response, local path, and source-file indicators.",
        "",
        "## Output Files",
        "",
        f"- Run audit CSV: `{summary['run_audit_csv']}`",
        f"- Prediction-file audit CSV: `{summary['prediction_file_audit_csv']}`",
        f"- JSON summary: `{summary['json_summary']}`",
    ]
    if summary["failed_run_ids"]:
        lines.extend(["", "## Failed Runs", ""])
        for run_id in summary["failed_run_ids"]:
            lines.append(f"- `{run_id}`")
    else:
        lines.extend(["", "## Failed Runs", "", "- None."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR)
    parser.add_argument("--status-csv", type=Path, default=STATUS_CSV)
    parser.add_argument("--template-csv", type=Path, default=TEMPLATE_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    status = pd.read_csv(args.status_csv)
    template = pd.read_csv(args.template_csv)
    summary_rows, summary_read_errors = load_metric_files(args.baseline_dir, SUMMARY_GLOB)
    seed_rows, seed_read_errors = load_metric_files(args.baseline_dir, SEED_GLOB)

    completed_run_ids = sorted(status.loc[status["status"].eq("completed"), "run_id"].astype(str).unique())
    blocked_run_ids = sorted(
        status.loc[~status["status"].isin(TERMINAL_OK_STATUSES), "run_id"].astype(str).unique()
    )
    completed_template = template.loc[template["status"].eq("completed")].copy()

    run_records: list[dict[str, Any]] = []
    prediction_records: list[dict[str, Any]] = []
    issue_by_run: dict[str, list[str]] = {}
    for run_id in completed_run_ids:
        expected_rows = completed_template.loc[completed_template["run_id"].astype(str).eq(run_id)].copy()
        current_summary = summary_rows.loc[summary_rows["run_id"].astype(str).eq(run_id)].copy()
        current_seed = seed_rows.loc[seed_rows["run_id"].astype(str).eq(run_id)].copy()
        run_record, prediction_rows, issues = audit_run(run_id, expected_rows, current_summary, current_seed)
        run_records.append(run_record)
        prediction_records.extend(prediction_rows)
        if issues:
            issue_by_run[run_id] = issues

    blocked_summary_rows = (
        summary_rows.loc[summary_rows["run_id"].astype(str).isin(blocked_run_ids)].copy()
        if not summary_rows.empty
        else pd.DataFrame()
    )
    extra_summary_run_ids = sorted(
        set(summary_rows["run_id"].astype(str).unique()) - set(status["run_id"].astype(str).unique())
    ) if not summary_rows.empty else []

    run_audit = pd.DataFrame(run_records).sort_values("run_id")
    prediction_audit = pd.DataFrame(prediction_records).sort_values(["run_id", "path"])

    failed_run_ids = sorted(issue_by_run)
    prediction_files_with_leak = int(
        prediction_audit[["leaky_columns", "leaky_value_count"]]
        .apply(
            lambda row: bool(str(row["leaky_columns"]).strip())
            or int(row["leaky_value_count"] or 0) > 0,
            axis=1,
        )
        .sum()
    ) if not prediction_audit.empty else 0

    completed_metric_rows_in_summaries = int(
        len(summary_rows.loc[summary_rows["run_id"].astype(str).isin(completed_run_ids)])
    ) if not summary_rows.empty else 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_csv = args.out_dir / "phase2_artifact_hygiene_run_audit.csv"
    prediction_csv = args.out_dir / "phase2_artifact_hygiene_prediction_files.csv"
    json_path = args.out_dir / "phase2_artifact_hygiene_audit.json"
    md_path = args.out_dir / "phase2_artifact_hygiene_audit.md"

    run_audit.to_csv(run_csv, index=False)
    prediction_audit.to_csv(prediction_csv, index=False)

    artifact_hygiene_passed = (
        not failed_run_ids
        and not summary_read_errors
        and not seed_read_errors
        and int(len(blocked_summary_rows)) == 0
        and not extra_summary_run_ids
        and completed_metric_rows_in_summaries == int(len(completed_template))
    )

    summary: dict[str, Any] = {
        "generated_at": utc_now(),
        "baseline_dir": str(args.baseline_dir),
        "status_csv": str(args.status_csv),
        "template_csv": str(args.template_csv),
        "json_summary": str(json_path),
        "run_audit_csv": str(run_csv),
        "prediction_file_audit_csv": str(prediction_csv),
        "artifact_hygiene_passed": bool(artifact_hygiene_passed),
        "completed_runs_audited": int(len(completed_run_ids)),
        "blocked_runs": int(len(blocked_run_ids)),
        "failed_completed_runs": int(len(failed_run_ids)),
        "failed_run_ids": failed_run_ids,
        "completed_metric_rows_in_matrix": int(len(completed_template)),
        "completed_metric_rows_in_summaries": int(completed_metric_rows_in_summaries),
        "summary_metric_rows_total": int(len(summary_rows)),
        "seed_metric_rows_audited": int(len(seed_rows.loc[seed_rows["run_id"].astype(str).isin(completed_run_ids)]))
        if not seed_rows.empty
        else 0,
        "canonical_prediction_files_audited": int(prediction_audit["path"].nunique())
        if not prediction_audit.empty
        else 0,
        "canonical_prediction_rows_audited": int(prediction_audit["rows"].fillna(0).astype(int).sum())
        if not prediction_audit.empty
        else 0,
        "prediction_files_with_leak_indicators": prediction_files_with_leak,
        "blocked_runs_with_metric_summary_rows": int(blocked_summary_rows["run_id"].nunique())
        if not blocked_summary_rows.empty
        else 0,
        "extra_summary_run_ids": extra_summary_run_ids,
        "summary_read_errors": summary_read_errors,
        "seed_read_errors": seed_read_errors,
        "issue_by_run": issue_by_run,
    }
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    write_markdown(md_path, summary)
    print(f"Wrote {json_path}")
    print(f"Wrote {run_csv}")
    print(f"Wrote {prediction_csv}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
