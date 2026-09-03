#!/usr/bin/env python3
"""Run MV29 PHQ measurement sensitivity synthesis.

MV29 is a reviewer-facing aggregate synthesis over existing MV10 and MV14
outputs. It tests whether the MV10 anchor/DIF interpretation depends strongly
on heuristic loading and threshold tolerances, then joins the result with MV14
bootstrap DIF frequencies and response-category support. It does not refit
psychometric models or export participant-level responses.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MV10_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv10_psychometric_invariance_baseline"
DEFAULT_MV14_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv14_measurement_uncertainty_bootstrap"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv29_phq_measurement_sensitivity"
PHQ_ITEMS = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"]
DEFAULT_ANCHORS = {"C01", "C04", "C05", "C07"}
DEFAULT_THRESHOLD_SHIFT = {"C02", "C06"}
TRACKED_FILES = {
    "anchor_grid_sensitivity.csv",
    "anchor_grid_sensitivity.md",
    "artifact_hygiene_audit.json",
    "item_level_measurement_robustness.csv",
    "item_level_measurement_robustness.md",
    "measurement_sensitivity_gate.csv",
    "report.md",
    "run_summary.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"missing required aggregate artifact: {path}")
    return pd.read_csv(path)


def item_label_map(partial: pd.DataFrame) -> dict[str, str]:
    return {
        str(row["construct_id"]): str(row["item_label_short"])
        for _, row in partial[["construct_id", "item_label_short"]].drop_duplicates().iterrows()
    }


def role_for(metric_invariant: bool, threshold_invariant: bool) -> str:
    if metric_invariant and threshold_invariant:
        return "anchor_candidate"
    if metric_invariant:
        return "metric_only_threshold_free"
    return "free_loading_or_threshold"


def build_anchor_grid(
    partial: pd.DataFrame,
    *,
    loading_tolerances: list[float],
    threshold_tolerances: list[float],
    min_anchor_counts: list[int],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for loading_tol in loading_tolerances:
        for threshold_tol in threshold_tolerances:
            roles: dict[str, str] = {}
            for _, row in partial.iterrows():
                item = str(row["construct_id"])
                metric_invariant = float(row["abs_loading_delta"]) <= float(loading_tol)
                threshold_invariant = float(row["max_abs_threshold_location_delta"]) <= float(threshold_tol)
                roles[item] = role_for(metric_invariant, threshold_invariant)
            anchors = sorted(item for item, role in roles.items() if role == "anchor_candidate")
            threshold_free = sorted(item for item, role in roles.items() if role == "metric_only_threshold_free")
            loading_or_threshold_free = sorted(item for item, role in roles.items() if role == "free_loading_or_threshold")
            for min_anchor_count in min_anchor_counts:
                anchor_set = set(anchors)
                rows.append(
                    {
                        "loading_delta_tolerance": float(loading_tol),
                        "threshold_location_tolerance": float(threshold_tol),
                        "minimum_anchor_count": int(min_anchor_count),
                        "anchor_count": int(len(anchors)),
                        "anchor_set": ";".join(anchors),
                        "threshold_free_set": ";".join(threshold_free),
                        "loading_or_threshold_free_set": ";".join(loading_or_threshold_free),
                        "partial_invariance_screen_pass": bool(len(anchors) >= int(min_anchor_count)),
                        "default_anchor_set_exact": bool(anchor_set == DEFAULT_ANCHORS),
                        "default_anchors_retained": bool(DEFAULT_ANCHORS.issubset(anchor_set)),
                        "c02_c06_threshold_shift_retained": bool(DEFAULT_THRESHOLD_SHIFT.issubset(set(threshold_free))),
                        "c08_loading_or_threshold_free": bool("C08" in loading_or_threshold_free),
                    }
                )
    return pd.DataFrame(rows).sort_values(
        ["loading_delta_tolerance", "threshold_location_tolerance", "minimum_anchor_count"]
    ).reset_index(drop=True)


def category_support(distribution: pd.DataFrame, response_support: pd.DataFrame) -> pd.DataFrame:
    distribution = distribution.copy()
    distribution["nonzero_category_count"] = distribution[[f"category_{i}" for i in range(4)]].gt(0).sum(axis=1)
    distribution["min_category_count"] = distribution[[f"category_{i}" for i in range(4)]].min(axis=1)
    by_item = (
        distribution.groupby(["construct_id", "item_label_short"], as_index=False)
        .agg(
            min_dataset_category_count=("min_category_count", "min"),
            min_dataset_nonzero_category_count=("nonzero_category_count", "min"),
            max_floor_rate=("floor_rate", "max"),
            max_ceiling_rate=("ceiling_rate", "max"),
        )
    )
    support = response_support.groupby(["construct_id"], as_index=False).agg(
        min_response_category_count=("count", "min"),
        min_response_category_proportion=("proportion", "min"),
    )
    return by_item.merge(support, on="construct_id", how="left")


def build_item_robustness(
    partial: pd.DataFrame,
    grid: pd.DataFrame,
    mv14_dif: pd.DataFrame,
    support: pd.DataFrame,
) -> pd.DataFrame:
    role_rows: list[dict[str, Any]] = []
    label_map = item_label_map(partial)
    role_by_item: dict[str, list[str]] = {item: [] for item in PHQ_ITEMS}
    for _, row in grid.iterrows():
        anchors = set(str(row["anchor_set"]).split(";")) if str(row["anchor_set"]).strip() else set()
        threshold_free = set(str(row["threshold_free_set"]).split(";")) if str(row["threshold_free_set"]).strip() else set()
        free = set(str(row["loading_or_threshold_free_set"]).split(";")) if str(row["loading_or_threshold_free_set"]).strip() else set()
        for item in PHQ_ITEMS:
            if item in anchors:
                role_by_item[item].append("anchor_candidate")
            elif item in threshold_free:
                role_by_item[item].append("metric_only_threshold_free")
            elif item in free:
                role_by_item[item].append("free_loading_or_threshold")
            else:
                role_by_item[item].append("unassigned")
    total_grid_rows = int(len(grid))
    partial_lookup = partial.set_index("construct_id")
    mv14_lookup = mv14_dif.set_index("construct_id")
    support_lookup = support.set_index("construct_id")
    for item in PHQ_ITEMS:
        roles = role_by_item[item]
        counts = pd.Series(roles).value_counts()
        partial_row = partial_lookup.loc[item]
        mv14_row = mv14_lookup.loc[item]
        support_row = support_lookup.loc[item]
        anchor_frequency = float(counts.get("anchor_candidate", 0) / total_grid_rows)
        threshold_free_frequency = float(counts.get("metric_only_threshold_free", 0) / total_grid_rows)
        free_frequency = float(counts.get("free_loading_or_threshold", 0) / total_grid_rows)
        if item in DEFAULT_ANCHORS and anchor_frequency >= 0.60 and float(mv14_row["anchor_support_frequency"]) >= 0.90:
            reading = "stable anchor with strict-threshold caveat"
        elif item in DEFAULT_THRESHOLD_SHIFT and threshold_free_frequency >= 0.70 and float(mv14_row["threshold_flag_frequency"]) >= 0.60:
            reading = "stable threshold-shift signal"
        elif free_frequency >= 0.50:
            reading = "unstable or free item"
        else:
            reading = "tolerance-sensitive item"
        role_rows.append(
            {
                "construct_id": item,
                "item_label_short": label_map[item],
                "mv10_role": str(partial_row["partial_invariance_role"]),
                "abs_loading_delta": float(partial_row["abs_loading_delta"]),
                "max_abs_threshold_location_delta": float(partial_row["max_abs_threshold_location_delta"]),
                "anchor_frequency_over_grid": anchor_frequency,
                "threshold_free_frequency_over_grid": threshold_free_frequency,
                "loading_or_threshold_free_frequency_over_grid": free_frequency,
                "mv14_loading_flag_frequency": float(mv14_row["loading_flag_frequency"]),
                "mv14_loading_ci_low": float(mv14_row["loading_ci_low"]),
                "mv14_loading_ci_high": float(mv14_row["loading_ci_high"]),
                "mv14_threshold_flag_frequency": float(mv14_row["threshold_flag_frequency"]),
                "mv14_threshold_ci_low": float(mv14_row["threshold_ci_low"]),
                "mv14_threshold_ci_high": float(mv14_row["threshold_ci_high"]),
                "mv14_anchor_support_frequency": float(mv14_row["anchor_support_frequency"]),
                "mv14_anchor_support_ci_low": float(mv14_row["anchor_support_ci_low"]),
                "mv14_anchor_support_ci_high": float(mv14_row["anchor_support_ci_high"]),
                "threshold_frequency_rank": int(mv14_row["threshold_frequency_rank"]),
                "min_response_category_count": int(support_row["min_response_category_count"]),
                "min_response_category_proportion": float(support_row["min_response_category_proportion"]),
                "max_floor_rate": float(support_row["max_floor_rate"]),
                "max_ceiling_rate": float(support_row["max_ceiling_rate"]),
                "sparsity_note": "sparse category" if int(support_row["min_response_category_count"]) < 5 else "adequate category coverage",
                "measurement_reading": reading,
            }
        )
    return pd.DataFrame(role_rows)


def build_gate(grid: pd.DataFrame, robustness: pd.DataFrame) -> pd.DataFrame:
    default_exact_rate = float(grid["default_anchor_set_exact"].mean())
    default_retained_rate = float(grid["default_anchors_retained"].mean())
    c02_c06_rate = float(grid["c02_c06_threshold_shift_retained"].mean())
    pass_rate_min4 = float(grid.loc[grid["minimum_anchor_count"].eq(4), "partial_invariance_screen_pass"].mean())
    stable_anchor_count = int(robustness["measurement_reading"].str.startswith("stable anchor").sum())
    stable_shift_count = int((robustness["measurement_reading"] == "stable threshold-shift signal").sum())
    status = (
        "supports_bounded_anchor_shift_interpretation"
        if stable_anchor_count >= 4 and stable_shift_count >= 2 and c02_c06_rate >= 0.90
        else "downgrade_anchor_shift_interpretation"
    )
    rows = [
        {
            "gate": "anchor_grid_sensitivity",
            "status": status,
            "metric": "default_anchor_set_exact_rate",
            "value": default_exact_rate,
            "criterion": "descriptive, exact anchor set need not be invariant across all heuristic tolerances",
        },
        {
            "gate": "anchor_grid_sensitivity",
            "status": status,
            "metric": "default_anchor_retained_rate",
            "value": default_retained_rate,
            "criterion": "default anchors should usually remain anchors across tolerance grid",
        },
        {
            "gate": "threshold_shift_sensitivity",
            "status": status,
            "metric": "c02_c06_threshold_shift_retained_rate",
            "value": c02_c06_rate,
            "criterion": "C02/C06 should remain threshold-free under the tolerance grid",
        },
        {
            "gate": "partial_invariance_screen",
            "status": status,
            "metric": "min4_anchor_pass_rate",
            "value": pass_rate_min4,
            "criterion": "at least four anchors should remain available in most grid settings",
        },
        {
            "gate": "item_level_reading",
            "status": status,
            "metric": "stable_anchor_item_count",
            "value": float(stable_anchor_count),
            "criterion": "stable anchors use grid frequency plus MV14 bootstrap support",
        },
        {
            "gate": "item_level_reading",
            "status": status,
            "metric": "stable_threshold_shift_item_count",
            "value": float(stable_shift_count),
            "criterion": "stable threshold-shift signals use grid frequency plus MV14 bootstrap DIF frequency",
        },
    ]
    return pd.DataFrame(rows)


def fmt(value: float) -> str:
    if pd.isna(value):
        return ""
    return f"{float(value):.3f}"


def fmt_interval(mean: float, low: float, high: float) -> str:
    return f"{float(mean):.3f} [{float(low):.3f}, {float(high):.3f}]"


def write_anchor_grid_markdown(grid: pd.DataFrame, path: Path) -> None:
    lines = [
        "| loading tol | threshold tol | min anchors | anchor count | anchor set | C02/C06 retained as threshold-shift | pass |",
        "| ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for _, row in grid.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    fmt(row["loading_delta_tolerance"]),
                    fmt(row["threshold_location_tolerance"]),
                    str(int(row["minimum_anchor_count"])),
                    str(int(row["anchor_count"])),
                    str(row["anchor_set"]),
                    "yes" if bool(row["c02_c06_threshold_shift_retained"]) else "no",
                    "yes" if bool(row["partial_invariance_screen_pass"]) else "no",
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_item_robustness_markdown(robustness: pd.DataFrame, path: Path) -> None:
    lines = [
        "| item | MV10 role | grid anchor freq | grid threshold-free freq | MV14 threshold DIF freq | MV14 anchor support | min category count | reading |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in robustness.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["construct_id"]),
                    str(row["mv10_role"]),
                    fmt(row["anchor_frequency_over_grid"]),
                    fmt(row["threshold_free_frequency_over_grid"]),
                    fmt_interval(
                        row["mv14_threshold_flag_frequency"],
                        row["mv14_threshold_ci_low"],
                        row["mv14_threshold_ci_high"],
                    ),
                    fmt_interval(
                        row["mv14_anchor_support_frequency"],
                        row["mv14_anchor_support_ci_low"],
                        row["mv14_anchor_support_ci_high"],
                    ),
                    str(int(row["min_response_category_count"])),
                    str(row["measurement_reading"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_report(out_dir: Path, run_summary: dict[str, Any], gate: pd.DataFrame) -> None:
    status = str(gate["status"].iloc[0])
    lines = [
        "# P5 MV29 PHQ Measurement Sensitivity",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "MV29 checks whether the E-DAIC/CMDC PHQ anchor and threshold-shift interpretation depends on one hand-picked heuristic threshold. It reads only MV10 and MV14 aggregate outputs.",
        "",
        "## Anchor Grid",
        "",
        (out_dir / "anchor_grid_sensitivity.md").read_text(encoding="utf-8").strip(),
        "",
        "## Item-Level Robustness",
        "",
        (out_dir / "item_level_measurement_robustness.md").read_text(encoding="utf-8").strip(),
        "",
        "## Interpretation Handle",
        "",
        f"Gate status: `{status}`.",
        "",
        run_summary["interpretation_handle"],
        "",
        "Use this as sensitivity support for a bounded measurement-validity claim. It does not remove the observed-N finite-sample caveat from MV19.",
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bparticipant_key\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in sorted(TRACKED_FILES - {"artifact_hygiene_audit.json"}):
        path = out_dir / name
        if not path.exists():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV29_phq_measurement_sensitivity_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mv10-dir", type=Path, default=DEFAULT_MV10_DIR)
    parser.add_argument("--mv14-dir", type=Path, default=DEFAULT_MV14_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--loading-tolerances", type=float, nargs="+", default=[0.15, 0.20, 0.25])
    parser.add_argument("--threshold-tolerances", type=float, nargs="+", default=[0.25, 0.35, 0.45])
    parser.add_argument("--min-anchor-counts", type=int, nargs="+", default=[3, 4, 5])
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.clean:
        clean_tracked_outputs(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    partial = read_csv(args.mv10_dir / "partial_invariance_summary.csv")
    distribution = read_csv(args.mv10_dir / "item_distribution_summary.csv")
    response_support = read_csv(args.mv14_dir / "input_response_category_support.csv")
    mv14_dif = read_csv(args.mv14_dir / "item_dif_stability_summary.csv")

    grid = build_anchor_grid(
        partial,
        loading_tolerances=[float(value) for value in args.loading_tolerances],
        threshold_tolerances=[float(value) for value in args.threshold_tolerances],
        min_anchor_counts=[int(value) for value in args.min_anchor_counts],
    )
    support = category_support(distribution, response_support)
    robustness = build_item_robustness(partial, grid, mv14_dif, support)
    gate = build_gate(grid, robustness)

    grid.to_csv(args.out_dir / "anchor_grid_sensitivity.csv", index=False)
    robustness.to_csv(args.out_dir / "item_level_measurement_robustness.csv", index=False)
    gate.to_csv(args.out_dir / "measurement_sensitivity_gate.csv", index=False)
    write_anchor_grid_markdown(grid, args.out_dir / "anchor_grid_sensitivity.md")
    write_item_robustness_markdown(robustness, args.out_dir / "item_level_measurement_robustness.md")

    stable_anchors = robustness.loc[
        robustness["measurement_reading"].str.startswith("stable anchor"),
        "construct_id",
    ].tolist()
    stable_shifts = robustness.loc[robustness["measurement_reading"].eq("stable threshold-shift signal"), "construct_id"].tolist()
    c02_c06_rate = float(gate.loc[gate["metric"].eq("c02_c06_threshold_shift_retained_rate"), "value"].iloc[0])
    exact_rate = float(gate.loc[gate["metric"].eq("default_anchor_set_exact_rate"), "value"].iloc[0])
    interpretation = (
        f"The default anchors are exact in {exact_rate:.2f} of tolerance-grid rows, while C02/C06 remain threshold-free "
        f"in {c02_c06_rate:.2f} of rows. MV14 bootstrap support identifies stable anchors "
        f"{';'.join(stable_anchors) or 'none'} and stable threshold-shift signals { ';'.join(stable_shifts) or 'none'}. "
        "This supports bounded item-level target-contract heterogeneity, with category-sparsity and MV19 finite-sample limits still foregrounded."
    )
    run_summary = {
        "run_id": "P5_MV29_phq_measurement_sensitivity",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "mv10_source": "p5_mv10_psychometric_invariance_baseline",
        "mv14_source": "p5_mv14_measurement_uncertainty_bootstrap",
        "loading_tolerances": [float(value) for value in args.loading_tolerances],
        "threshold_tolerances": [float(value) for value in args.threshold_tolerances],
        "min_anchor_counts": [int(value) for value in args.min_anchor_counts],
        "default_anchor_set": sorted(DEFAULT_ANCHORS),
        "default_threshold_shift_items": sorted(DEFAULT_THRESHOLD_SHIFT),
        "gate_status": str(gate["status"].iloc[0]),
        "stable_anchor_items": stable_anchors,
        "stable_threshold_shift_items": stable_shifts,
        "default_anchor_set_exact_rate": exact_rate,
        "c02_c06_threshold_shift_retained_rate": c02_c06_rate,
        "interpretation_handle": interpretation,
        "aggregate_outputs_only": True,
    }
    (args.out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(args.out_dir, run_summary, gate)
    hygiene = artifact_hygiene(args.out_dir)
    (args.out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
