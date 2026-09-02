#!/usr/bin/env python3
"""Run MV24 companion simulation for corpus-specific ordinal heads.

This simulation keeps the latent representation observed by the measurement
head fixed and compares two target-calibrated ordinal measurement contracts:

1. a shared ordinal head pooled across corpora;
2. a corpus-specific ordinal head with target-domain threshold offsets.

It is a mechanism sanity check for the MV24 fair-ablation result, not a new
multimodal training run. Participant-grain observed and simulated responses are
kept in memory; tracked outputs are aggregate only.
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
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

import phase5_run_mv19_phq_finite_sample_simulation as mv19
import phase5_run_mv24_measurement_aware_ordinal_model as mv24


ROOT = mv24.ROOT
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv24_measurement_head_dif_simulation"
RUN_ID = "P5_MV24_measurement_head_dif_simulation"
RANDOM_SEED = 20260902
DEFAULT_SIMULATIONS = 500

PHQ_ITEM_IDS = mv24.PHQ_ITEM_IDS
THRESHOLD_SHIFT_ITEMS = ["C02", "C06"]
ANCHOR_ITEMS = ["C01", "C04", "C05", "C07"]
SIMULATION_WORLDS = ["H0_scalar_invariant", "H1_C02_C06_threshold_DIF"]
HEAD_METHODS = ["shared_ordinal_head", "corpus_specific_ordinal_head"]
SUMMARY_ROWS = [
    ("item_set", "all_shared_items"),
    ("item_set", "anchor_items"),
    ("item_set", "threshold_shift_items"),
    ("item", "C02"),
    ("item", "C06"),
]
TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "comparison_by_draw.csv",
    "gate_recommendations.csv",
    "head_comparison_summary.csv",
    "head_comparison_table.md",
    "input_boundary_contract.csv",
    "observed_input_audit.csv",
    "report.md",
    "run_summary.json",
    "simulation_design_contract.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return "unknown"


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def dataset_scale(dataset: str) -> str:
    return {"edaic": "PHQ-8", "cmdc": "PHQ-9"}[dataset]


def build_observed_mv24_table(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
    tables, _, coverage = mv24.load_official_view_tables(args)
    frames: list[pd.DataFrame] = []
    for dataset, table in tables.items():
        frame = table[PHQ_ITEM_IDS].copy()
        frame["dataset"] = dataset
        frame["scale"] = dataset_scale(dataset)
        frame["core_total"] = frame[PHQ_ITEM_IDS].sum(axis=1).astype(float)
        frame["full_total"] = frame["core_total"]
        frames.append(frame)
    observed = pd.concat(frames, ignore_index=True)
    observed = mv19.build_observed_theta(observed)
    return observed, coverage


def observed_input_audit(observed: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset, group in observed.groupby("dataset", sort=False):
        labels = group[PHQ_ITEM_IDS].to_numpy(dtype=np.int64)
        calib, eval_idx = mv24.calibration_split_indices(
            labels,
            int(args.seed),
            fraction=args.target_calibration_fraction,
            minimum=args.target_calibration_min,
        )
        rows.append(
            {
                "dataset": dataset,
                "scale": dataset_scale(dataset),
                "mv24_label_feature_intersection_n": int(len(group)),
                "default_target_calibration_n_if_target": int(len(calib)),
                "default_target_evaluation_n_if_target": int(len(eval_idx)),
                "mean_shared_phq_total": float(group["core_total"].mean()),
                "sd_shared_phq_total": float(group["core_total"].std(ddof=1)),
            }
        )
    return pd.DataFrame(rows)


def fit_binary_threshold_model(features: np.ndarray, labels: np.ndarray, seed: int) -> dict[str, Any]:
    y = labels.astype(int)
    if len(np.unique(y)) < 2:
        return {
            "kind": "constant",
            "positive_rate": float(np.mean(y)),
            "scaler": None,
            "model": None,
        }
    scaler = StandardScaler().fit(features)
    model = LogisticRegression(C=100.0, max_iter=1000, solver="lbfgs", random_state=int(seed))
    model.fit(scaler.transform(features), y)
    return {"kind": "logistic", "positive_rate": float(np.mean(y)), "scaler": scaler, "model": model}


def predict_binary_threshold_model(model: dict[str, Any], features: np.ndarray) -> np.ndarray:
    if model["kind"] == "constant":
        return np.full(features.shape[0], float(model["positive_rate"]), dtype=np.float64)
    return model["model"].predict_proba(model["scaler"].transform(features))[:, 1].astype(np.float64)


def simulate_latent_table(
    observed: pd.DataFrame,
    generation_models: dict[tuple[str, int], dict[str, Any]],
    h1_offsets: pd.DataFrame,
    world_id: str,
    rng: np.random.Generator,
) -> pd.DataFrame:
    offset_map = {
        (str(row["construct_id"]), int(row["threshold"])): float(row["h1_cmdc_logit_offset"])
        for _, row in h1_offsets.iterrows()
    }
    frames: list[pd.DataFrame] = []
    for dataset, group in observed.groupby("dataset", sort=False):
        theta_pool = group["theta_proxy_z"].to_numpy(dtype=np.float64)
        theta = rng.choice(theta_pool, size=len(group), replace=True)
        theta = theta + rng.normal(0.0, mv19.THETA_JITTER_SD, size=len(group))
        frame = pd.DataFrame({"dataset": dataset, "scale": dataset_scale(dataset), "theta_proxy_z": theta})
        for item_id in PHQ_ITEM_IDS:
            cumulative: list[np.ndarray] = []
            for threshold in mv19.THRESHOLDS:
                offset = 0.0
                if world_id == "H1_C02_C06_threshold_DIF" and dataset == "cmdc":
                    offset = offset_map[(item_id, int(threshold))]
                cumulative.append(mv19.predict_threshold_probability(generation_models[(item_id, int(threshold))], theta, offset))
            p1, p2, p3 = mv19.monotone_cumulative(cumulative)
            frame[item_id] = mv19.sample_ordinal_from_cumulative(p1, p2, p3, rng)
        frame["core_total"] = frame[PHQ_ITEM_IDS].sum(axis=1).astype(float)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def head_features(theta: np.ndarray, domain_indicator: np.ndarray | None) -> np.ndarray:
    theta_col = theta.astype(np.float64).reshape(-1, 1)
    if domain_indicator is None:
        return theta_col
    return np.column_stack([theta_col, domain_indicator.astype(np.float64)])


def fit_head_predictions(
    source_theta: np.ndarray,
    source_y: np.ndarray,
    target_calib_theta: np.ndarray,
    target_calib_y: np.ndarray,
    target_eval_theta: np.ndarray,
    method: str,
    seed: int,
) -> np.ndarray:
    source_domain = np.zeros(len(source_theta), dtype=np.float64)
    target_calib_domain = np.ones(len(target_calib_theta), dtype=np.float64)
    target_eval_domain = np.ones(len(target_eval_theta), dtype=np.float64)
    if method == "shared_ordinal_head":
        train_x = head_features(np.concatenate([source_theta, target_calib_theta]), None)
        eval_x = head_features(target_eval_theta, None)
    elif method == "corpus_specific_ordinal_head":
        train_x = head_features(
            np.concatenate([source_theta, target_calib_theta]),
            np.concatenate([source_domain, target_calib_domain]),
        )
        eval_x = head_features(target_eval_theta, target_eval_domain)
    else:
        raise ValueError(f"unknown head method: {method}")
    train_y = np.vstack([source_y, target_calib_y])
    pred = np.zeros((len(target_eval_theta), len(PHQ_ITEM_IDS)), dtype=np.float64)
    for item_idx, item_id in enumerate(PHQ_ITEM_IDS):
        cumulative: list[np.ndarray] = []
        for threshold in mv19.THRESHOLDS:
            labels = (train_y[:, item_idx] >= int(threshold)).astype(int)
            model = fit_binary_threshold_model(train_x, labels, seed + item_idx * 11 + int(threshold))
            cumulative.append(predict_binary_threshold_model(model, eval_x))
        p1, p2, p3 = mv19.monotone_cumulative(cumulative)
        pred[:, item_idx] = p1 + p2 + p3
    return np.clip(pred, 0.0, 3.0)


def item_set_specs() -> list[tuple[str, str, str, list[str], str]]:
    specs: list[tuple[str, str, str, list[str], str]] = []
    for item_id in PHQ_ITEM_IDS:
        specs.append(("item", item_id, item_id, [item_id], mv24.TARGETED_ITEM_ROLES[item_id]))
    for set_id, display, item_ids, audit_role in mv24.TARGETED_ITEM_SETS:
        specs.append(("item_set", set_id, display, item_ids, audit_role))
    return specs


def append_metric_rows(
    rows: list[dict[str, Any]],
    *,
    world_id: str,
    draw_id: int,
    transfer_id: str,
    method: str,
    target_calibration_count: int,
    target_evaluation_count: int,
    pred: np.ndarray,
    truth: np.ndarray,
) -> None:
    errors = np.abs(np.clip(pred, 0.0, 3.0) - truth.astype(np.float64))
    for analysis_level, item_set_id, display, item_ids, audit_role in item_set_specs():
        item_indices = [PHQ_ITEM_IDS.index(item_id) for item_id in item_ids]
        rows.append(
            {
                "world_id": world_id,
                "draw_id": int(draw_id),
                "transfer_id": transfer_id,
                "method": method,
                "target_calibration_count": int(target_calibration_count),
                "target_evaluation_count": int(target_evaluation_count),
                "analysis_level": analysis_level,
                "item_set_id": item_set_id,
                "item_display": display,
                "item_ids": "/".join(item_ids),
                "item_count": int(len(item_ids)),
                "audit_role": audit_role,
                "item_mae": float(errors[:, item_indices].mean()),
            }
        )


def run_simulation(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    observed, coverage = build_observed_mv24_table(args)
    generation_models = mv19.fit_generation_models(observed)
    h1_offsets = mv19.load_h1_offsets()
    rng = np.random.default_rng(int(args.seed))
    rows: list[dict[str, Any]] = []
    for world_id in SIMULATION_WORLDS:
        for draw_id in range(int(args.simulations)):
            simulated = simulate_latent_table(observed, generation_models, h1_offsets, world_id, rng)
            for source_dataset, target_dataset in mv24.TRANSFER_DIRECTIONS:
                source = simulated[simulated["dataset"].eq(source_dataset)].copy()
                target = simulated[simulated["dataset"].eq(target_dataset)].copy()
                source_theta = source["theta_proxy_z"].to_numpy(dtype=np.float64)
                target_theta = target["theta_proxy_z"].to_numpy(dtype=np.float64)
                source_y = source[PHQ_ITEM_IDS].to_numpy(dtype=np.int64)
                target_y = target[PHQ_ITEM_IDS].to_numpy(dtype=np.int64)
                split_seed = int(args.seed) + draw_id * 37 + (0 if source_dataset == "edaic" else 100000)
                target_calib_idx, target_eval_idx = mv24.calibration_split_indices(
                    target_y,
                    split_seed,
                    fraction=args.target_calibration_fraction,
                    minimum=args.target_calibration_min,
                )
                target_calib_theta = target_theta[target_calib_idx]
                target_eval_theta = target_theta[target_eval_idx]
                target_calib_y = target_y[target_calib_idx]
                target_eval_y = target_y[target_eval_idx]
                transfer_id = f"{source_dataset}_to_{target_dataset}_phq_shared"
                for method in HEAD_METHODS:
                    pred = fit_head_predictions(
                        source_theta,
                        source_y,
                        target_calib_theta,
                        target_calib_y,
                        target_eval_theta,
                        method,
                        split_seed,
                    )
                    append_metric_rows(
                        rows,
                        world_id=world_id,
                        draw_id=draw_id,
                        transfer_id=transfer_id,
                        method=method,
                        target_calibration_count=len(target_calib_idx),
                        target_evaluation_count=len(target_eval_idx),
                        pred=pred,
                        truth=target_eval_y,
                    )
    return pd.DataFrame(rows), observed, coverage


def summarize_values(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=np.float64)
    values = values[~np.isnan(values)]
    mean = float(values.mean())
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    half_width = float(stats.t.ppf(0.975, len(values) - 1) * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
    return {"mean": mean, "std": std, "ci95_low": mean - half_width, "ci95_high": mean + half_width}


def format_ci(row: dict[str, float]) -> str:
    return f"{row['mean']:.3f} [{row['ci95_low']:.3f}, {row['ci95_high']:.3f}]"


def summarize_head_comparisons(by_draw: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    row_order = {spec: idx for idx, spec in enumerate(SUMMARY_ROWS)}
    for (world_id, transfer_id, analysis_level, item_set_id), group in by_draw.groupby(
        ["world_id", "transfer_id", "analysis_level", "item_set_id"],
        dropna=False,
    ):
        if (analysis_level, item_set_id) not in row_order:
            continue
        shared = group[group["method"].eq("shared_ordinal_head")].set_index("draw_id")["item_mae"]
        corpus = group[group["method"].eq("corpus_specific_ordinal_head")].set_index("draw_id")["item_mae"]
        common = shared.index.intersection(corpus.index)
        shared_values = shared.loc[common].to_numpy(dtype=np.float64)
        corpus_values = corpus.loc[common].to_numpy(dtype=np.float64)
        delta_values = shared_values - corpus_values
        shared_stats = summarize_values(shared_values)
        corpus_stats = summarize_values(corpus_values)
        delta_stats = summarize_values(delta_values)
        lower_count = int((delta_values > 0.0).sum())
        lower_low, lower_high = mv19.wilson_interval(lower_count, int(len(common)))
        descriptor = group.iloc[0]
        rows.append(
            {
                "world_id": world_id,
                "transfer_id": transfer_id,
                "analysis_level": analysis_level,
                "item_set_id": item_set_id,
                "item_display": descriptor["item_display"],
                "item_ids": descriptor["item_ids"],
                "item_count": int(descriptor["item_count"]),
                "audit_role": descriptor["audit_role"],
                "target_calibration_count": int(round(group["target_calibration_count"].mean())),
                "target_evaluation_count": int(round(group["target_evaluation_count"].mean())),
                "draw_count": int(len(common)),
                "shared_ordinal_head_mae_mean": shared_stats["mean"],
                "shared_ordinal_head_mae_ci95": format_ci(shared_stats),
                "corpus_specific_ordinal_head_mae_mean": corpus_stats["mean"],
                "corpus_specific_ordinal_head_mae_ci95": format_ci(corpus_stats),
                "delta_shared_minus_corpus_specific_mean": delta_stats["mean"],
                "delta_shared_minus_corpus_specific_ci95": format_ci(delta_stats),
                "corpus_specific_lower_error_draws": lower_count,
                "corpus_specific_lower_error_rate": float(lower_count / len(common)),
                "corpus_specific_lower_error_ci95_low": lower_low,
                "corpus_specific_lower_error_ci95_high": lower_high,
                "row_order": int(row_order[(analysis_level, item_set_id)]),
            }
        )
    return pd.DataFrame(rows).sort_values(["world_id", "transfer_id", "row_order"]).reset_index(drop=True)


def world_summary(summary: pd.DataFrame) -> pd.DataFrame:
    focus = summary[summary["item_set_id"].isin(["all_shared_items", "anchor_items", "threshold_shift_items"])].copy()
    return focus[
        [
            "world_id",
            "transfer_id",
            "item_set_id",
            "item_ids",
            "target_calibration_count",
            "target_evaluation_count",
            "draw_count",
            "delta_shared_minus_corpus_specific_mean",
            "corpus_specific_lower_error_rate",
        ]
    ].reset_index(drop=True)


def simulation_design_contract(args: argparse.Namespace) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "contract_id": "S001_latent_input",
                "scope": "both",
                "description": "The measurement head observes the simulated latent severity coordinate directly; feature encoders and representation adaptation are not part of this simulation.",
                "readout": "Isolates the measurement-head parameterization from target-supervised representation adaptation.",
            },
            {
                "contract_id": "S002_world_H0",
                "scope": "H0_scalar_invariant",
                "description": "Both corpora share the same ordinal response process conditional on latent severity.",
                "readout": "Shared and corpus-specific ordinal heads should be close; extra corpus-specific offsets should not create a broad gain.",
            },
            {
                "contract_id": "S003_world_H1",
                "scope": "H1_C02_C06_threshold_DIF",
                "description": "CMDC receives the MV19/MV10 C02 and C06 threshold-logit offsets; other items remain invariant.",
                "readout": "Corpus-specific ordinal heads should mainly improve C02/C06 when the target corpus is affected by the planted threshold shift.",
            },
            {
                "contract_id": "S004_sample_budget",
                "scope": "both",
                "description": f"Each draw uses the MV24 official label-feature intersection and target calibration split rule: fraction={args.target_calibration_fraction}, minimum={args.target_calibration_min}.",
                "readout": "Matches the calibration exposure that bounds Table 3.",
            },
            {
                "contract_id": "S005_heads",
                "scope": "both",
                "description": "Shared head fits cumulative threshold logits from latent severity only; corpus-specific head fits the same logits plus a target-domain threshold-offset indicator.",
                "readout": "Tests whether corpus-specific ordinal threshold parameterization has value when latent evidence is held fixed.",
            },
            {
                "contract_id": "S006_repetitions",
                "scope": "both",
                "description": f"{args.simulations} simulated draws with seed {args.seed}.",
                "readout": "Draw-level mean differences and descriptive confidence intervals.",
            },
        ]
    )


def input_boundary_contract() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact_class": "observed_mv24_complete_case_rows",
                "git_policy": "not_exported",
                "reason": "Real participant-grain PHQ item responses are analysis input.",
                "allowed_tracked_derivative": "dataset counts, split counts, and aggregate severity summaries",
            },
            {
                "artifact_class": "simulated_participant_response_rows",
                "git_policy": "not_exported",
                "reason": "Participant-grain simulated responses are unnecessary for the claim and can be regenerated.",
                "allowed_tracked_derivative": "draw-level aggregate item and item-set MAE only",
            },
            {
                "artifact_class": "fitted_head_parameters",
                "git_policy": "not_exported",
                "reason": "Head parameters are simulation internals rather than paper evidence.",
                "allowed_tracked_derivative": "aggregate shared-vs-corpus-specific error summaries",
            },
        ]
    )


def gate_recommendations(summary: pd.DataFrame) -> pd.DataFrame:
    h0 = summary[
        summary["world_id"].eq("H0_scalar_invariant") & summary["item_set_id"].eq("threshold_shift_items")
    ]
    h1 = summary[
        summary["world_id"].eq("H1_C02_C06_threshold_DIF") & summary["item_set_id"].eq("threshold_shift_items")
    ]
    h0_max_abs_delta = float(h0["delta_shared_minus_corpus_specific_mean"].abs().max())
    h1_min_delta = float(h1["delta_shared_minus_corpus_specific_mean"].min())
    h1_min_lower_rate = float(h1["corpus_specific_lower_error_rate"].min())
    h0_close = h0_max_abs_delta <= 0.02
    h1_item_local_consistent = h1_min_delta > 0.0 and h1_min_lower_rate >= 0.60
    h1_practical_shift_gain = h1_min_delta > 0.03 and h1_min_lower_rate >= 0.60
    if h0_close and h1_practical_shift_gain:
        status = "mechanism_supported_under_planted_threshold_dif"
    elif h0_close and h1_item_local_consistent:
        status = "weak_item_local_mechanism_consistent_but_small"
    else:
        status = "mechanism_not_cleanly_supported_under_current_simulation"
    return pd.DataFrame(
        [
            {
                "recommendation_id": "mechanism_sanity_check",
                "status": status,
                "recommendation": "Use the simulation only as bounded item-local mechanism evidence under known threshold DIF.",
                "evidence": f"H0 max abs C02/C06-set delta={h0_max_abs_delta:.3f}; H1 min C02/C06-set delta={h1_min_delta:.3f}; H1 min lower-error rate={h1_min_lower_rate:.3f}.",
            },
            {
                "recommendation_id": "real_data_claim_boundary",
                "status": "keep_bounded",
                "recommendation": "Do not override the real MV24 fair-ablation and targeted-item near-tie results.",
                "evidence": "This simulation fixes the latent input and plants a known response-process shift; real MV24 still estimates latent representations from frozen multimodal features.",
            },
            {
                "recommendation_id": "paper_positioning",
                "status": "framework_instantiation_not_sota_claim",
                "recommendation": "Present corpus-specific ordinal heads as a constructive instantiation whose value depends on observed target measurement shift and calibration budget.",
                "evidence": "The intended claim is audit-to-model coherence, not universal architecture superiority.",
            },
        ]
    )


def write_comparison_markdown(summary: pd.DataFrame, path: Path) -> None:
    lines = [
        "Positive delta means the corpus-specific ordinal head has lower item MAE than the shared ordinal head.",
        "",
    ]
    for world_id in SIMULATION_WORLDS:
        lines.extend([f"**{world_id}.**", ""])
        for transfer_id in ["cmdc_to_edaic_phq_shared", "edaic_to_cmdc_phq_shared"]:
            sub = summary[summary["world_id"].eq(world_id) & summary["transfer_id"].eq(transfer_id)].copy()
            if sub.empty:
                continue
            sub = sub.sort_values("row_order")
            first = sub.iloc[0]
            lines.extend(
                [
                    f"{mv24.display_transfer_id(transfer_id)}; n_cal={int(first['target_calibration_count'])}, n_eval={int(first['target_evaluation_count'])}.",
                    "",
                    "| item set | role | shared ordinal MAE | corpus-specific ordinal MAE | delta shared - corpus-specific | corpus-specific lower-error draws |",
                    "| --- | --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for _, row in sub.iterrows():
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            str(row["item_display"]),
                            str(row["audit_role"]),
                            str(row["shared_ordinal_head_mae_ci95"]),
                            str(row["corpus_specific_ordinal_head_mae_ci95"]),
                            str(row["delta_shared_minus_corpus_specific_ci95"]),
                            f"{int(row['corpus_specific_lower_error_draws'])}/{int(row['draw_count'])}",
                        ]
                    )
                    + " |"
                )
            lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    recommendations = pd.read_csv(out_dir / "gate_recommendations.csv")
    audit = pd.read_csv(out_dir / "observed_input_audit.csv")
    lines = [
        "# P5 MV24 Measurement-Head DIF Simulation",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This companion simulation fixes the latent input seen by the measurement head and compares a shared ordinal head against a corpus-specific ordinal threshold-offset head. It is designed to isolate measurement parameterization from representation adaptation.",
        "",
        "## Observed MV24 Input Boundary",
        "",
        "| dataset | scale | n | default n_cal | default n_eval | mean total | sd total |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in audit.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['scale']} | {int(row['mv24_label_feature_intersection_n'])} | "
            f"{int(row['default_target_calibration_n_if_target'])} | {int(row['default_target_evaluation_n_if_target'])} | "
            f"{float(row['mean_shared_phq_total']):.3f} | {float(row['sd_shared_phq_total']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Head Comparison",
            "",
            (out_dir / "head_comparison_table.md").read_text(encoding="utf-8").strip(),
            "",
            "## Recommendations",
            "",
            "| recommendation | status | evidence |",
            "| --- | --- | --- |",
        ]
    )
    for _, row in recommendations.iterrows():
        lines.append(f"| {row['recommendation_id']} | `{row['status']}` | {md_escape(row['evidence'])} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- This simulation may support the conceptual link between threshold-DIF audits and corpus-specific measurement heads when the response-process shift is known.",
            "- It does not overturn MV24's real-data result: the shared ordinal head and corpus-specific measurement-aware head are nearly tied on overall and C02/C06 item-set MAE.",
            "- It does not test feature invariance, target-supervised representation adaptation, or clinical endpoint superiority.",
        ]
    )
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
        r"raw clinical",
        r"model weight",
        r"embedding matrix",
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
        "audit_id": "P5_MV24_measurement_head_dif_simulation_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def build_outputs(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_dir
    if args.clean:
        clean_tracked_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_draw, observed, coverage = run_simulation(args)
    by_draw.to_csv(out_dir / "comparison_by_draw.csv", index=False)
    observed_input_audit(observed, args).to_csv(out_dir / "observed_input_audit.csv", index=False)
    simulation_design_contract(args).to_csv(out_dir / "simulation_design_contract.csv", index=False)
    input_boundary_contract().to_csv(out_dir / "input_boundary_contract.csv", index=False)
    summary = summarize_head_comparisons(by_draw)
    summary.to_csv(out_dir / "head_comparison_summary.csv", index=False)
    write_comparison_markdown(summary, out_dir / "head_comparison_table.md")
    world = world_summary(summary)
    recommendations = gate_recommendations(summary)
    recommendations.to_csv(out_dir / "gate_recommendations.csv", index=False)
    run_summary = {
        "run_id": RUN_ID,
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "scope": "fixed_latent_measurement_head_simulation",
        "worlds": SIMULATION_WORLDS,
        "head_methods": HEAD_METHODS,
        "simulations_per_world": int(args.simulations),
        "seed": int(args.seed),
        "target_calibration_fraction": float(args.target_calibration_fraction),
        "target_calibration_min": int(args.target_calibration_min),
        "mv24_official_view_rows": json.loads(
            observed_input_audit(observed, args).to_json(orient="records")
        ),
        "feature_coverage_rows": int(len(coverage)),
        "world_summary_rows": json.loads(world.to_json(orient="records")),
        "gate_recommendations": json.loads(recommendations.to_json(orient="records")),
        "aggregate_outputs_only": True,
        "tracked_outputs": sorted(TRACKED_FILES),
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=mv24.DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=mv24.DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--target-calibration-fraction", type=float, default=0.30)
    parser.add_argument("--target-calibration-min", type=int, default=24)
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_summary = build_outputs(args)
    print(f"Wrote {RUN_ID} to {args.out_dir} with hygiene={run_summary['artifact_hygiene_passed']}")


if __name__ == "__main__":
    main()
