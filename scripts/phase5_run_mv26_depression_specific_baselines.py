#!/usr/bin/env python3
"""Build the combined MV26 depression-specific baseline package.

This is the canonical MV26 entrypoint. It runs the two component runners in
temporary directories, then writes one combined aggregate package to
`analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`.

The combined package contains three close baseline families:

- GNN-SDA-style semi-supervised graph domain adaptation.
- QuestMF-style question-wise ordinal fusion.
- SCD-MLLM-style heterogeneous multimodal adapter/fusion.

Each family is evaluated with a direct ordinal item head and with the paper's
measurement-aware target pathway under the same target calibration label
budget. Outputs are aggregate-only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv24_measurement_aware_ordinal_model as mv24


DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv26_depression_specific_baselines"
CORE_SCRIPT = ROOT / "scripts" / "phase5_run_mv26_core_depression_specific_baselines.py"
SCD_SCRIPT = ROOT / "scripts" / "phase5_run_mv26_scd_mllm_baseline.py"
METHOD_ORDER = [
    "gnn_sda_style_direct_head",
    "gnn_sda_style_measurement_aware",
    "questmf_style_direct_head",
    "questmf_style_measurement_aware",
    "scd_mllm_style_direct_head",
    "scd_mllm_style_measurement_aware",
]
METHOD_RANK = {method: rank for rank, method in enumerate(METHOD_ORDER)}
MEASUREMENT_PAIR = {
    "gnn_sda_style": ("gnn_sda_style_direct_head", "gnn_sda_style_measurement_aware"),
    "questmf_style": ("questmf_style_direct_head", "questmf_style_measurement_aware"),
    "scd_mllm_style": ("scd_mllm_style_direct_head", "scd_mllm_style_measurement_aware"),
}
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "baseline_contract.csv",
    "baseline_contract.md",
    "feature_asset_coverage.csv",
    "main_result_table.csv",
    "main_result_table.md",
    "metrics_by_seed.csv",
    "paired_measurement_layer_significance.csv",
    "report.md",
    "run_summary.json",
    "secondary_clinical_metrics_table.csv",
    "secondary_clinical_metrics_table.md",
    "summary_by_method.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def run_component(script: Path, out_dir: Path, passthrough: list[str]) -> None:
    cmd = [sys.executable, str(script), "--clean", "--out-dir", str(out_dir), *passthrough]
    subprocess.run(cmd, cwd=ROOT, check=True)


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def read_csv(folder: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(folder / name)


def summarize_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = metrics.groupby(["transfer_id", "baseline_family", "method", "method_rank"], dropna=False)
    for (transfer_id, family, method, method_rank), group in grouped:
        row: dict[str, Any] = {
            "transfer_id": transfer_id,
            "baseline_family": family,
            "method": method,
            "method_rank": int(method_rank),
            "seed_count": int(group["seed"].nunique()),
            "source_participant_count": int(round(group["source_participant_count"].mean())),
            "target_calibration_count": int(round(group["target_calibration_count"].mean())),
            "target_evaluation_count": int(round(group["target_evaluation_count"].mean())),
            "input_columns": int(group["input_columns"].max()),
            "representation_columns": int(group["representation_columns"].max()),
            "text_components": int(group["text_components"].max()),
            "audio_components": int(group["audio_components"].max()),
            "video_components": int(group["video_components"].max()),
            "target_calibration_labels_used": True,
        }
        for metric in mv24.METRIC_COLUMNS:
            values = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy(dtype=np.float64)
            if len(values) == 0:
                row[f"{metric}_mean"] = math.nan
                row[f"{metric}_std"] = math.nan
                row[f"{metric}_ci95_low"] = math.nan
                row[f"{metric}_ci95_high"] = math.nan
                continue
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            half_width = float(stats.t.ppf(0.975, len(values) - 1) * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
            row[f"{metric}_mean"] = mean
            row[f"{metric}_std"] = std
            row[f"{metric}_ci95_low"] = mean - half_width
            row[f"{metric}_ci95_high"] = mean + half_width
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).reset_index(drop=True)


def paired_measurement_layer_significance(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for transfer_id, transfer_group in metrics.groupby("transfer_id", dropna=False):
        for family, (direct_method, aware_method) in MEASUREMENT_PAIR.items():
            direct = transfer_group[transfer_group["method"] == direct_method].set_index("seed")
            aware = transfer_group[transfer_group["method"] == aware_method].set_index("seed")
            common = direct.index.intersection(aware.index)
            if len(common) < 2:
                mean_delta = math.nan
                p_two_sided = math.nan
                p_aware_better = math.nan
            else:
                direct_score = direct.loc[common, "reconstruction_calibration_score"].to_numpy(dtype=np.float64)
                aware_score = aware.loc[common, "reconstruction_calibration_score"].to_numpy(dtype=np.float64)
                delta = direct_score - aware_score
                mean_delta = float(delta.mean())
                p_two_sided = float(stats.ttest_rel(direct_score, aware_score, nan_policy="omit").pvalue)
                try:
                    p_aware_better = float(
                        stats.ttest_rel(direct_score, aware_score, alternative="greater", nan_policy="omit").pvalue
                    )
                except TypeError:
                    statistic = stats.ttest_rel(direct_score, aware_score, nan_policy="omit").statistic
                    p_aware_better = float(stats.t.sf(statistic, df=len(common) - 1))
            rows.append(
                {
                    "transfer_id": transfer_id,
                    "baseline_family": family,
                    "comparison": f"{aware_method}_vs_{direct_method}",
                    "comparison_scope": "same_source_target_split_same_target_calibration_label_budget",
                    "paired_seed_count": int(len(common)),
                    "metric": "reconstruction_calibration_score",
                    "mean_delta_direct_minus_measurement_aware": mean_delta,
                    "p_value_two_sided": p_two_sided,
                    "p_value_measurement_aware_better_one_sided": p_aware_better,
                    "measurement_aware_better_significance": mv24.significance_label(p_aware_better),
                }
            )
    return pd.DataFrame(rows).sort_values(["transfer_id", "baseline_family"]).reset_index(drop=True)


def build_main_result_table(summary: pd.DataFrame, significance: pd.DataFrame) -> pd.DataFrame:
    sig_lookup = {
        (str(row["transfer_id"]), str(row["baseline_family"])): str(row["measurement_aware_better_significance"])
        for _, row in significance.iterrows()
    }
    delta_lookup = {
        (str(row["transfer_id"]), str(row["baseline_family"])): float(row["mean_delta_direct_minus_measurement_aware"])
        for _, row in significance.iterrows()
    }
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        family = str(row["baseline_family"])
        is_measurement = str(row["method"]).endswith("_measurement_aware")
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "baseline_family": family,
                "method": row["method"],
                "seeds": int(row["seed_count"]),
                "target_calibration_labels": "yes",
                "labeled_target_calib_n": int(row["target_calibration_count"]),
                "target_eval_n": int(row["target_evaluation_count"]),
                "macro_item_mae_ci95": mv24.format_mean_ci(row, "target_macro_item_mae"),
                "calibration_mae_ci95": mv24.format_mean_ci(row, "target_calibration_mae"),
                "reconstruction_calibration_score_ci95": mv24.format_mean_ci(row, "reconstruction_calibration_score"),
                "total_mae_ci95": mv24.format_mean_ci(row, "target_total_mae"),
                "total_ccc_ci95": mv24.format_mean_ci(row, "target_total_ccc"),
                "post_head_domain_ba_ci95": mv24.format_mean_ci(row, "post_head_domain_identity_ba"),
                "measurement_layer_delta_score": (
                    f"{delta_lookup[(str(row['transfer_id']), family)]:.3f}" if is_measurement else ""
                ),
                "direct_vs_measurement_significance": (
                    sig_lookup.get((str(row["transfer_id"]), family), "") if is_measurement else ""
                ),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).drop(columns=["method_rank"]).reset_index(drop=True)


def build_secondary_clinical_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in summary.iterrows():
        rows.append(
            {
                "transfer_id": row["transfer_id"],
                "baseline_family": row["baseline_family"],
                "method": row["method"],
                "target_calibration_labels": "yes",
                "labeled_target_calib_n": int(row["target_calibration_count"]),
                "macro_f1_ci95": mv24.format_mean_ci(row, "target_binary_macro_f1"),
                "balanced_accuracy_ci95": mv24.format_mean_ci(row, "target_binary_balanced_accuracy"),
                "auroc_ci95": mv24.format_mean_ci(row, "target_binary_auroc"),
                "auprc_ci95": mv24.format_mean_ci(row, "target_binary_auprc"),
                "sensitivity_ci95": mv24.format_mean_ci(row, "target_binary_sensitivity"),
                "specificity_ci95": mv24.format_mean_ci(row, "target_binary_specificity"),
                "method_rank": int(row["method_rank"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["transfer_id", "method_rank"]).drop(columns=["method_rank"]).reset_index(drop=True)


def write_main_markdown(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "| transfer | family | method | seeds | target labels | calib n | eval n | macro item MAE | calibration MAE | recon+calib score | total MAE | CCC | post-head BA | aware delta | sig |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in table.columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_secondary_markdown(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "| transfer | family | method | macro-F1 | BA | AUROC | AUPRC | sensitivity | specificity |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in table.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["transfer_id"]),
                    str(row["baseline_family"]),
                    str(row["method"]),
                    str(row["macro_f1_ci95"]),
                    str(row["balanced_accuracy_ci95"]),
                    str(row["auroc_ci95"]),
                    str(row["auprc_ci95"]),
                    str(row["sensitivity_ci95"]),
                    str(row["specificity_ci95"]),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_contract(core_dir: Path, scd_dir: Path, out_dir: Path) -> None:
    core = read_csv(core_dir, "baseline_contract.csv")
    scd = read_csv(scd_dir, "baseline_contract.csv")
    contract = pd.concat([core, scd], ignore_index=True, sort=False)
    contract["method_rank"] = contract["method"].map(METHOD_RANK).astype(int)
    contract = contract.sort_values("method_rank").drop(columns=["method_rank"]).reset_index(drop=True)
    contract["baseline_package"] = "mv26_depression_specific_baselines"
    contract.to_csv(out_dir / "baseline_contract.csv", index=False)
    lines = [
        "# MV26 Depression-Specific Baseline Contract",
        "",
        "MV26 is a targeted close-baseline stress test, not a broad leaderboard expansion. It asks whether the measurement-aware target layer still adds value after three depression-specific modeling ideas: GNN-SDA-style semi-supervised graph domain adaptation, QuestMF-style question-wise ordinal fusion, and SCD-MLLM-style heterogeneous multimodal adapter/fusion.",
        "",
        "All rows use the same E-DAIC <-> CMDC split, the same eight shared PHQ items, the same official MV24 Qwen3 + WavLM + OpenFace subject representation, the same five seeds, and the same labeled target calibration budget. The intended contrast within each family is the final target pathway: direct ordinal item head versus shared symptom layer plus corpus-specific cumulative ordinal heads.",
        "",
        "| method | reference | MV26 adaptation | target calibration labels |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in contract.iterrows():
        lines.append(
            f"| {row['method']} | {row['reference']} | {row['mv26_adaptation']} | {row['target_calibration_labels']} |"
        )
    lines.extend(
        [
            "",
            "Rows are style/adapted implementations under our subject-level frozen-feature and PHQ shared-item target contract. They should be cited as controlled target-pathway stress tests rather than exact reproductions of external leaderboard settings.",
            "",
        ]
    )
    (out_dir / "baseline_contract.md").write_text("\n".join(lines), encoding="utf-8")


def significance_to_markdown(table: pd.DataFrame) -> str:
    lines = [
        "| transfer | family | comparison | seeds | direct-minus-aware score delta | aware-better p | sig |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for _, row in table.iterrows():
        lines.append(
            f"| {row['transfer_id']} | {row['baseline_family']} | {row['comparison']} | {int(row['paired_seed_count'])} | {float(row['mean_delta_direct_minus_measurement_aware']):.4f} | {float(row['p_value_measurement_aware_better_one_sided']):.4g} | {row['measurement_aware_better_significance']} |"
        )
    return "\n".join(lines)


def write_report(out_dir: Path, summary: pd.DataFrame, significance: pd.DataFrame, generated_at: str) -> None:
    best = (
        summary.sort_values(["transfer_id", "baseline_family", "reconstruction_calibration_score_mean"])
        .groupby(["transfer_id", "baseline_family"], as_index=False)
        .head(1)
    )
    lines = [
        "# P5 MV26 Depression-Specific Baseline Stress Test",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Scope",
        "",
        "MV26 evaluates three close depression-specific baseline families under the same MV24 PHQ shared-item transfer contract. The package combines GNN-SDA-style graph adaptation, QuestMF-style question-wise ordinal fusion, and SCD-MLLM-style heterogeneous multimodal fusion. It is a controlled test of whether stronger representation/adaptation ideas remove the need for an explicit corpus-specific measurement pathway.",
        "",
        "## Best Rows By Family",
        "",
        "| transfer | family | best method | recon+calib score | macro item MAE | calibration MAE | total MAE | seeds |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best.iterrows():
        lines.append(
            f"| {row['transfer_id']} | {row['baseline_family']} | {row['method']} | {float(row['reconstruction_calibration_score_mean']):.4f} | {float(row['target_macro_item_mae_mean']):.4f} | {float(row['target_calibration_mae_mean']):.4f} | {float(row['target_total_mae_mean']):.4f} | {int(row['seed_count'])} |"
        )
    lines.extend(
        [
            "",
            "## Paired Measurement-Layer Test",
            "",
            significance_to_markdown(significance),
            "",
            "## Main Result Table",
            "",
            (out_dir / "main_result_table.md").read_text(encoding="utf-8").strip(),
            "",
            "## Secondary Clinical Endpoint",
            "",
            (out_dir / "secondary_clinical_metrics_table.md").read_text(encoding="utf-8").strip(),
            "",
            "## Interpretation Handle",
            "",
            "Use MV26 as a close-baseline stress-test package. The manuscript should foreground MV24 as the formal main method result, then use MV26 to show that measurement-aware target modeling remains complementary for question-wise item fusion and heterogeneous multimodal/foundation fusion. GNN-SDA-style remains direction-sensitive, which is useful stress evidence that representation adaptation alone does not make corpus-specific response mechanisms disappear.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path, generated_at: str) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"row prediction",
        r"embedding matrix",
        r"model weight",
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
        "audit_id": "P5_MV26_depression_specific_baseline_hygiene",
        "generated_at": generated_at,
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def merge_component_outputs(core_dir: Path, scd_dir: Path, out_dir: Path, *, generated_at: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    coverage = read_csv(core_dir, "feature_asset_coverage.csv")
    coverage.to_csv(out_dir / "feature_asset_coverage.csv", index=False)

    write_contract(core_dir, scd_dir, out_dir)
    metrics = pd.concat(
        [read_csv(core_dir, "metrics_by_seed.csv"), read_csv(scd_dir, "metrics_by_seed.csv")],
        ignore_index=True,
        sort=False,
    )
    metrics["method_rank"] = metrics["method"].map(METHOD_RANK).astype(int)
    metrics["baseline_package"] = "mv26_depression_specific_baselines"
    metrics = metrics.sort_values(["transfer_id", "method_rank", "seed"]).reset_index(drop=True)
    metrics.to_csv(out_dir / "metrics_by_seed.csv", index=False)

    summary = summarize_metrics(metrics)
    summary.to_csv(out_dir / "summary_by_method.csv", index=False)
    significance = paired_measurement_layer_significance(metrics)
    significance.to_csv(out_dir / "paired_measurement_layer_significance.csv", index=False)
    main_table = build_main_result_table(summary, significance)
    main_table.to_csv(out_dir / "main_result_table.csv", index=False)
    write_main_markdown(main_table, out_dir / "main_result_table.md")
    secondary_table = build_secondary_clinical_table(summary)
    secondary_table.to_csv(out_dir / "secondary_clinical_metrics_table.csv", index=False)
    write_secondary_markdown(secondary_table, out_dir / "secondary_clinical_metrics_table.md")

    run_summary = {
        "run_id": "P5_MV26_depression_specific_baselines",
        "generated_at": generated_at,
        "git_commit": git_commit(),
        "status": "complete_combined",
        "directions": ["edaic_to_cmdc_phq_shared", "cmdc_to_edaic_phq_shared"],
        "methods": METHOD_ORDER,
        "baseline_families": ["gnn_sda_style", "questmf_style", "scd_mllm_style"],
        "seed_count": int(metrics["seed"].nunique()),
        "official_view_id": mv24.official_view().view_id,
        "target_calibration_fraction": 0.30,
        "target_calibration_min": 24,
        "target_calibration_labels_used_by_all_rows": True,
        "primary_metric": "reconstruction_calibration_score",
        "primary_metric_components": ["target_macro_item_mae", "target_calibration_mae"],
        "secondary_severity_metrics": ["target_total_mae", "target_total_ccc"],
        "secondary_clinical_classification_endpoint": f"shared PHQ total >= {mv24.PHQ_SHARED_BINARY_THRESHOLD:.0f}",
        "secondary_clinical_classification_metrics": [
            "target_binary_macro_f1",
            "target_binary_balanced_accuracy",
            "target_binary_auroc",
            "target_binary_auprc",
            "target_binary_sensitivity",
            "target_binary_specificity",
        ],
        "comparison_scope": "within-family direct target head versus measurement-aware target layer under the same target calibration labels",
        "aggregate_outputs_only": True,
        "combined_package_note": "This folder contains the public MV26 close-baseline families used for manuscript comparison.",
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, summary, significance, generated_at)
    hygiene = artifact_hygiene(out_dir, generated_at)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--clean", action="store_true", help="remove previous aggregate outputs before writing")
    args, passthrough = parser.parse_known_args()
    blocked = {"--methods"}
    if any(item == "--methods" or item.startswith("--methods=") for item in passthrough):
        raise ValueError("The combined MV26 runner does not support partial --methods runs; run component scripts for debugging.")
    return args, passthrough


def main() -> None:
    args, passthrough = parse_args()
    if args.clean:
        clean_tracked_outputs(args.out_dir)
    generated_at = utc_now()
    with tempfile.TemporaryDirectory(prefix="mv26_baseline_components_") as tmp:
        tmp_root = Path(tmp)
        core_dir = tmp_root / "core"
        scd_dir = tmp_root / "scd"
        run_component(CORE_SCRIPT, core_dir, passthrough)
        run_component(SCD_SCRIPT, scd_dir, passthrough)
        merge_component_outputs(core_dir, scd_dir, args.out_dir, generated_at=generated_at)


if __name__ == "__main__":
    main()
