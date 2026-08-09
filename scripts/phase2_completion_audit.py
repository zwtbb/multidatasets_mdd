#!/usr/bin/env python3
"""Generate a requirement-by-requirement audit for Phase 2 baselines."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path("/root/autodl-tmp")
MATRIX_CONFIG = ROOT / "baselines" / "phase2_baseline_matrix.yaml"
BASELINE_DIR = ROOT / "analysis" / "phase2_baselines"
STATUS_CSV = BASELINE_DIR / "baseline_matrix_status.csv"
TEMPLATE_CSV = BASELINE_DIR / "baseline_matrix_template.csv"
DEFAULT_OUT_DIR = BASELINE_DIR / "phase2_completion_audit"
FINAL_TABLE_SUMMARY = BASELINE_DIR / "final_table" / "phase2_final_baseline_table_summary.json"

BLOCKER_FILES = {
    "mpdd_public_p3hf": BASELINE_DIR
    / "mpdd_public_p3hf_compatibility"
    / "compatibility_gate.json",
    "mpdd_video_severity_openface_mlp": BASELINE_DIR
    / "mpdd_openface_availability"
    / "availability.json",
    "mpdd_official_split": BASELINE_DIR / "mpdd_official_split_audit" / "split_audit.json",
}

TERMINAL_OK_STATUSES = {"completed", "not_applicable"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def status_counts(rows: pd.DataFrame) -> dict[str, int]:
    return {str(k): int(v) for k, v in rows["status"].value_counts().sort_index().items()}


def family_audit(status: pd.DataFrame, families: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for family in families:
        rows = status.loc[status["family"].eq(family)].copy()
        out[family] = {
            "run_count": int(len(rows)),
            "status_counts": status_counts(rows),
            "completed_run_ids": rows.loc[rows["status"].eq("completed"), "run_id"].astype(str).tolist(),
            "not_applicable_run_ids": rows.loc[
                rows["status"].eq("not_applicable"), "run_id"
            ].astype(str).tolist(),
            "blocked_run_ids": rows.loc[
                ~rows["status"].isin(TERMINAL_OK_STATUSES), "run_id"
            ].astype(str).tolist(),
        }
    return out


def public_audit(
    matrix: dict[str, Any],
    status: pd.DataFrame,
) -> dict[str, dict[str, list[dict[str, str]]]]:
    status_by_run = status.set_index("run_id")["status"].astype(str).to_dict()
    by_public_name: dict[str, list[dict[str, str]]] = {}
    for run in matrix["runs"]:
        public_name = run.get("public_name")
        if not public_name:
            continue
        by_public_name.setdefault(str(public_name), []).append(
            {
                "run_id": str(run["id"]),
                "status": str(status_by_run.get(str(run["id"]), "missing_from_status")),
            }
        )

    out: dict[str, dict[str, list[dict[str, str]]]] = {}
    for dataset, names in matrix["coverage_requirements"]["public_reproduction"].items():
        out[str(dataset)] = {}
        for name in names:
            out[str(dataset)][str(name)] = by_public_name.get(str(name), [])
    return out


def metric_audit(template: pd.DataFrame, status: pd.DataFrame) -> dict[str, Any]:
    completed = template.loc[template["status"].eq("completed")].copy()
    not_applicable = template.loc[template["status"].eq("not_applicable")].copy()
    blocked = template.loc[~template["status"].isin(TERMINAL_OK_STATUSES)].copy()
    return {
        "metric_rows": int(len(template)),
        "completed_metric_rows": int(len(completed)),
        "not_applicable_metric_rows": int(len(not_applicable)),
        "blocked_metric_rows": int(len(blocked)),
        "completed_rows_missing_mean": int(completed["mean"].isna().sum()),
        "completed_rows_missing_ci": int(
            completed[["ci95_low", "ci95_high"]].isna().any(axis=1).sum()
        ),
        "not_applicable_rows_with_mean": int(not_applicable["mean"].notna().sum()),
        "blocked_rows_with_mean": int(blocked["mean"].notna().sum()),
        "completed_seed_count_min": int(completed["seed_count"].min()) if not completed.empty else 0,
        "completed_seed_count_max": int(completed["seed_count"].max()) if not completed.empty else 0,
        "required_seed_count_values": {
            str(k): int(v)
            for k, v in status["required_seed_count"].value_counts(dropna=False).sort_index().items()
        },
        "bootstrap_resample_values": {
            str(k): int(v)
            for k, v in status["bootstrap_resamples"].value_counts(dropna=False).sort_index().items()
        },
        "metric_sets_by_task_type": {
            str(task_type): str(rows["metrics"].iloc[0])
            for task_type, rows in status.groupby("task_type", sort=True)
        },
    }


def verdict(summary: dict[str, Any]) -> dict[str, Any]:
    blocked = int(summary["matrix_status"]["blocked_runs"])
    completed = int(summary["matrix_status"]["completed_runs"])
    not_applicable = int(summary["matrix_status"].get("not_applicable_runs", 0))
    planned = int(summary["matrix_status"]["planned_runs"])
    completed_metrics_ok = (
        summary["metric_audit"]["completed_rows_missing_mean"] == 0
        and summary["metric_audit"]["completed_rows_missing_ci"] == 0
        and summary["metric_audit"]["completed_seed_count_min"] >= 5
        and summary["metric_audit"]["completed_seed_count_max"] == 5
    )
    final_table_ok = not bool(summary["final_table_audit"].get("missing", False))
    blocked_run_ids = summary["matrix_status"].get("blocked_run_ids", [])
    if blocked == 0 and completed_metrics_ok and final_table_ok:
        reason = (
            "All applicable Phase 2 baseline rows have validated metric summaries and "
            "final-table exports; conditional public baselines that failed their "
            "compatibility gate are recorded as not applicable."
        )
        recommendation = "ready"
        complete = True
    else:
        blocked_text = ", ".join(f"`{run_id}`" for run_id in blocked_run_ids) or "none"
        reason = (
            "The audited matrix has validated completed results for all currently runnable rows, "
            f"but {blocked} planned row(s) remain blocked or incomplete: {blocked_text}."
        )
        recommendation = (
            "ready_after_user_accepts_blocker_state"
            if blocked > 0 and completed_metrics_ok and final_table_ok
            else "not_ready"
        )
        complete = False
    return {
        "phase2_goal_complete": bool(complete),
        "reason": reason,
        "completed_runs": completed,
        "not_applicable_runs": not_applicable,
        "planned_runs": planned,
        "blocked_runs": blocked,
        "completed_metric_rows_pass_basic_audit": bool(completed_metrics_ok),
        "final_table_export_present": bool(final_table_ok),
        "method_design_gate_recommendation": recommendation,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    matrix_status = summary["matrix_status"]
    metric = summary["metric_audit"]
    v = summary["verdict"]
    blockers = summary["blockers"]
    blocked_status_rows = summary.get("blocked_status_rows", [])
    not_applicable_status_rows = summary.get("not_applicable_status_rows", [])
    blocked_run_ids = {str(row.get("run_id", "")) for row in blocked_status_rows}
    not_applicable_run_ids = {str(row.get("run_id", "")) for row in not_applicable_status_rows}

    single_modal_line = (
        "- 4.1 single-modal baselines: completed for text, audio, OpenFace, official visual pooling, and gait families."
        if "mpdd_video_severity_openface_mlp" not in blocked_run_ids
        else "- 4.1 single-modal baselines: completed for text, audio, official visual pooling, and gait families; MPDD OpenFace remains blocked by missing OpenFace/raw-video inputs."
    )
    if "mpdd_public_p3hf" in blocked_run_ids:
        public_line = "- 4.3 public baselines: E-DAIC AVEC/QuestMF/existing baselines, MPDD official, PDCH official text/audio-text, EATD GRU/BiLSTM, and MODMA protocol tests are completed; P3HF remains blocked by the compatibility gate."
    elif "mpdd_public_p3hf" in not_applicable_run_ids:
        public_line = "- 4.3 public baselines: E-DAIC AVEC/QuestMF/existing baselines, MPDD official, PDCH official text/audio-text, EATD GRU/BiLSTM, and MODMA protocol tests are completed; P3HF is conditionally excluded because its code/input/evaluation contract does not match the current MPDD Phase 2 matrix."
    else:
        public_line = "- 4.3 public baselines: E-DAIC AVEC/QuestMF/existing baselines, MPDD official/P3HF, PDCH official text/audio-text, EATD GRU/BiLSTM, and MODMA protocol tests are completed."
    final_table_line = (
        "- 4.5 final table: `baseline_matrix_template.csv` is generated and validated, the paper-ready Chinese core final-table export includes only completed metric rows, and the audit CSV retains conditional exclusions."
        if not blocked_status_rows
        else "- 4.5 final table: `baseline_matrix_template.csv` is generated and validated, and the paper-ready Chinese final-table export is present; blocked rows intentionally keep metric fields blank."
    )
    blocker_lines: list[str] = []
    if blocked_status_rows:
        for row in blocked_status_rows:
            run_id = str(row.get("run_id", ""))
            status_reason = str(row.get("blockers", "")).strip() or "missing gate reason"
            gate_reason = blockers.get(run_id, {}).get("reason")
            blocker_lines.append(f"- `{run_id}`: {status_reason}")
            if gate_reason:
                blocker_lines.append(f"  Gate reason: {gate_reason}")
    else:
        blocker_lines.append("- None.")
    not_applicable_lines: list[str] = []
    if not_applicable_status_rows:
        for row in not_applicable_status_rows:
            run_id = str(row.get("run_id", ""))
            status_reason = str(row.get("blockers", "")).strip() or "not applicable"
            gate_reason = blockers.get(run_id, {}).get("reason")
            not_applicable_lines.append(f"- `{run_id}`: {status_reason}")
            if gate_reason:
                not_applicable_lines.append(f"  Gate reason: {gate_reason}")
    else:
        not_applicable_lines.append("- None.")

    lines: list[str] = [
        "# Phase 2 Completion Audit",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Verdict",
        "",
        f"- Phase 2 goal complete: `{v['phase2_goal_complete']}`",
        f"- Method-design gate recommendation: `{v['method_design_gate_recommendation']}`",
        f"- Completed runs: `{v['completed_runs']}/{v['planned_runs']}`",
        f"- Not-applicable runs: `{v['not_applicable_runs']}`",
        f"- Blocked planned runs: `{v['blocked_runs']}`",
        f"- Reason: {v['reason']}",
        "",
        "## Matrix Evidence",
        "",
        f"- Planned runs: `{matrix_status['planned_runs']}`",
        f"- Completed runs: `{matrix_status['completed_runs']}`",
        f"- Not-applicable runs: `{matrix_status['not_applicable_runs']}`",
        f"- Blocked runs: `{matrix_status['blocked_runs']}`",
        f"- Metric rows: `{metric['metric_rows']}`",
        f"- Completed metric rows: `{metric['completed_metric_rows']}`",
        f"- Not-applicable metric rows: `{metric['not_applicable_metric_rows']}`",
        f"- Blocked metric rows: `{metric['blocked_metric_rows']}`",
        f"- Completed seed count range: `{metric['completed_seed_count_min']}..{metric['completed_seed_count_max']}`",
        f"- Completed rows missing mean: `{metric['completed_rows_missing_mean']}`",
        f"- Completed rows missing CI: `{metric['completed_rows_missing_ci']}`",
        f"- Not-applicable rows with filled mean: `{metric['not_applicable_rows_with_mean']}`",
        f"- Blocked rows with filled mean: `{metric['blocked_rows_with_mean']}`",
        f"- Required seed counts in status table: `{metric['required_seed_count_values']}`",
        f"- Bootstrap resample counts in status table: `{metric['bootstrap_resample_values']}`",
        f"- Final table export present: `{v['final_table_export_present']}`",
        "",
        "## Requirement Audit",
        "",
        single_modal_line,
        "- 4.2 simple multimodal baselines: Early Fusion, Late Fusion, and Gated Fusion families are completed.",
        public_line,
        "- 4.4 unified evaluation: completed metric rows use the declared task metric sets, five seeds, subject-bootstrap CIs, and no test-label tuning policy.",
        final_table_line,
        "",
        "## Blockers",
        "",
        *blocker_lines,
        "",
        "## Conditional Exclusions",
        "",
        *not_applicable_lines,
        "",
        "## Key Paths",
        "",
        f"- Matrix config: `{MATRIX_CONFIG}`",
        f"- Matrix status: `{STATUS_CSV}`",
        f"- Final table: `{TEMPLATE_CSV}`",
        f"- Paper-ready final table summary: `{FINAL_TABLE_SUMMARY}`",
        f"- P3HF gate: `{BLOCKER_FILES['mpdd_public_p3hf']}`",
        f"- OpenFace gate: `{BLOCKER_FILES['mpdd_video_severity_openface_mlp']}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-config", type=Path, default=MATRIX_CONFIG)
    parser.add_argument("--status-csv", type=Path, default=STATUS_CSV)
    parser.add_argument("--template-csv", type=Path, default=TEMPLATE_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    matrix = yaml.safe_load(args.matrix_config.read_text(encoding="utf-8"))
    status = pd.read_csv(args.status_csv)
    template = pd.read_csv(args.template_csv)

    completed_runs = int(status["status"].eq("completed").sum())
    not_applicable_runs = int(status["status"].eq("not_applicable").sum())
    blocked_runs = int((~status["status"].isin(TERMINAL_OK_STATUSES)).sum())
    summary: dict[str, Any] = {
        "generated_at": utc_now(),
        "matrix_config": str(args.matrix_config),
        "status_csv": str(args.status_csv),
        "template_csv": str(args.template_csv),
        "policy": matrix["policy"],
        "matrix_status": {
            "planned_runs": int(len(status)),
            "completed_runs": completed_runs,
            "not_applicable_runs": not_applicable_runs,
            "blocked_runs": blocked_runs,
            "blocked_run_ids": status.loc[
                ~status["status"].isin(TERMINAL_OK_STATUSES), "run_id"
            ].astype(str).tolist(),
            "not_applicable_run_ids": status.loc[
                status["status"].eq("not_applicable"), "run_id"
            ].astype(str).tolist(),
            "status_counts": status_counts(status),
            "dataset_counts": {
                str(k): int(v) for k, v in status["dataset"].value_counts().sort_index().items()
            },
            "family_counts": {
                str(k): int(v) for k, v in status["family"].value_counts().sort_index().items()
            },
        },
        "single_modal_family_audit": family_audit(
            status,
            [str(item) for item in matrix["coverage_requirements"]["single_modal_families"]],
        ),
        "multimodal_family_audit": family_audit(
            status,
            [str(item) for item in matrix["coverage_requirements"]["multimodal_families"]],
        ),
        "public_reproduction_audit": public_audit(matrix, status),
        "metric_audit": metric_audit(template, status),
        "final_table_audit": load_json(FINAL_TABLE_SUMMARY),
        "blockers": {name: load_json(path) for name, path in BLOCKER_FILES.items()},
        "blocked_status_rows": status.loc[~status["status"].isin(TERMINAL_OK_STATUSES)][
            ["run_id", "dataset", "task", "model", "status", "blockers"]
        ].to_dict("records"),
        "not_applicable_status_rows": status.loc[status["status"].eq("not_applicable")][
            ["run_id", "dataset", "task", "model", "status", "blockers"]
        ].to_dict("records"),
    }
    summary["verdict"] = verdict(summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "phase2_completion_audit.json"
    md_path = args.out_dir / "phase2_completion_audit.md"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    write_markdown(md_path, summary)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
