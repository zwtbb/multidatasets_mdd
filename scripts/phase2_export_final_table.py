#!/usr/bin/env python3
"""Export the Phase 2 baseline matrix as paper-ready final tables."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path("/root/autodl-tmp")
BASELINE_DIR = ROOT / "analysis" / "phase2_baselines"
MATRIX_TABLE = BASELINE_DIR / "baseline_matrix_template.csv"
MATRIX_STATUS = BASELINE_DIR / "baseline_matrix_status.csv"
DEFAULT_OUT_DIR = BASELINE_DIR / "final_table"

CORE_COLUMNS = {
    "dataset": "数据集",
    "modality": "模态",
    "task": "任务",
    "model": "模型",
    "metric": "指标",
    "mean": "均值",
    "std": "标准差",
}

AUDIT_COLUMNS = {
    **CORE_COLUMNS,
    "ci95_low": "95%CI下限",
    "ci95_high": "95%CI上限",
    "seed_count": "随机种子数",
    "status": "状态",
    "run_id": "run_id",
    "blockers": "阻塞原因",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def format_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def markdown_table(rows: pd.DataFrame, columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for _, row in rows.iterrows():
        values = [format_value(row[col]) for col in columns]
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([header, divider, *body])


def export_tables(matrix_path: Path, status_path: Path, out_dir: Path) -> dict[str, Any]:
    matrix = pd.read_csv(matrix_path)
    status = pd.read_csv(status_path)
    required = set(CORE_COLUMNS) | {"ci95_low", "ci95_high", "seed_count", "status", "run_id"}
    missing = required - set(matrix.columns)
    if missing:
        raise ValueError(f"matrix table missing columns: {', '.join(sorted(missing))}")
    if "blockers" not in status.columns or "run_id" not in status.columns:
        raise ValueError("status table must include run_id and blockers columns")

    blockers = status[["run_id", "blockers"]].copy()
    rows = matrix.merge(blockers, on="run_id", how="left")
    rows["blockers"] = rows["blockers"].fillna("")

    completed = rows.loc[rows["status"].eq("completed")].copy()
    not_applicable = rows.loc[rows["status"].eq("not_applicable")].copy()
    blocked = rows.loc[~rows["status"].isin(["completed", "not_applicable"])].copy()

    core = completed[list(CORE_COLUMNS)].rename(columns=CORE_COLUMNS)
    audit = rows[list(AUDIT_COLUMNS)].rename(columns=AUDIT_COLUMNS)

    out_dir.mkdir(parents=True, exist_ok=True)
    core_path = out_dir / "phase2_final_baseline_table.csv"
    audit_path = out_dir / "phase2_final_baseline_table_audit.csv"
    md_path = out_dir / "phase2_final_baseline_table.md"
    summary_path = out_dir / "phase2_final_baseline_table_summary.json"

    core.to_csv(core_path, index=False)
    audit.to_csv(audit_path, index=False)

    summary = {
        "generated_at": utc_now(),
        "source_matrix_table": str(matrix_path),
        "source_status_table": str(status_path),
        "core_table": str(core_path),
        "audit_table": str(audit_path),
        "markdown_table": str(md_path),
        "row_count": int(len(rows)),
        "core_row_count": int(len(core)),
        "completed_metric_rows": int(len(completed)),
        "not_applicable_metric_rows": int(len(not_applicable)),
        "blocked_metric_rows": int(len(blocked)),
        "completed_rows_missing_mean": int(completed["mean"].isna().sum()),
        "completed_rows_missing_std": int(completed["std"].isna().sum()),
        "blocked_rows_with_mean": int(blocked["mean"].notna().sum()),
        "not_applicable_rows_with_mean": int(not_applicable["mean"].notna().sum()),
        "status_counts": {
            str(k): int(v) for k, v in rows["status"].value_counts(dropna=False).sort_index().items()
        },
        "blocked_run_ids": sorted(blocked["run_id"].dropna().astype(str).unique().tolist()),
        "not_applicable_run_ids": sorted(not_applicable["run_id"].dropna().astype(str).unique().tolist()),
        "core_columns": list(CORE_COLUMNS.values()),
        "audit_columns": list(AUDIT_COLUMNS.values()),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")

    lines = [
        "# Phase 2 Final Baseline Table",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "This core table is exported from completed rows in `baseline_matrix_template.csv`; conditional or blocked rows are retained in the audit CSV.",
        "",
        f"- Core completed rows: `{summary['core_row_count']}`",
        f"- Audit rows: `{summary['row_count']}`",
        f"- Completed metric rows: `{summary['completed_metric_rows']}`",
        f"- Not-applicable metric rows: `{summary['not_applicable_metric_rows']}`",
        f"- Blocked metric rows: `{summary['blocked_metric_rows']}`",
        f"- Completed rows missing mean/std: `{summary['completed_rows_missing_mean']}` / `{summary['completed_rows_missing_std']}`",
        f"- Blocked rows with filled mean: `{summary['blocked_rows_with_mean']}`",
        f"- Not-applicable rows with filled mean: `{summary['not_applicable_rows_with_mean']}`",
        "",
        markdown_table(core, list(core.columns)),
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-table", type=Path, default=MATRIX_TABLE)
    parser.add_argument("--status-table", type=Path, default=MATRIX_STATUS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()
    summary = export_tables(args.matrix_table, args.status_table, args.out_dir)
    print(f"Wrote {summary['core_table']}")
    print(f"Wrote {summary['audit_table']}")
    print(f"Wrote {summary['markdown_table']}")
    print(f"Wrote {args.out_dir / 'phase2_final_baseline_table_summary.json'}")


if __name__ == "__main__":
    main()
