#!/usr/bin/env python3
"""Run MV30 representation-control sensitivity probes.

MV30 answers a reviewer-sensitive question raised after MV25: why does the
raw E-DAIC/CMDC corpus-identity probe fall from near-perfect to near-chance
after length and severity controls?

The run reuses the MV25 feature/label joins and fold-internal residualization
implementation, then adds:

1. a decomposed control ladder: raw, length-only, severity-only,
   length+severity, and shuffled length+severity;
2. a nonlinear identity probe alongside the original linear probe;
3. an aggregate-only report explaining the residualization protocol.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def normalize_thread_env() -> None:
    for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"]:
        value = str(os.environ.get(key, "")).strip()
        if not value.isdigit() or int(value) <= 0:
            os.environ[key] = "1"


normalize_thread_env()

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import phase5_run_mv25_provenance_controlled_identity as mv25


DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv30_representation_control_sensitivity"

CONTROL_STRATEGIES = {
    "raw": {"base": "raw", "shuffle": False},
    "length_only": {"base": "length_residualized", "shuffle": False},
    "severity_only": {"base": "severity_residualized", "shuffle": False},
    "length_severity": {"base": "length_severity_residualized", "shuffle": False},
    "length_severity_shuffled": {"base": "length_severity_residualized", "shuffle": True},
}

PROBE_MODELS = ("linear_logistic", "nonlinear_random_forest")

TRACKED_FILES = {
    "artifact_hygiene_audit.json",
    "control_decomposition_by_seed.csv",
    "control_decomposition_summary.csv",
    "control_decomposition_table.csv",
    "control_decomposition_table.md",
    "residualization_protocol.md",
    "report.md",
    "run_summary.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        return "unknown"


def clean_tracked_outputs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in TRACKED_FILES:
        path = out_dir / name
        if path.exists():
            path.unlink()


def format_mean_ci(row: pd.Series) -> str:
    return (
        f"{float(row['balanced_accuracy_mean']):.3f} "
        f"[{float(row['balanced_accuracy_ci95_low']):.3f}, {float(row['balanced_accuracy_ci95_high']):.3f}]"
    )


def format_float(value: float) -> str:
    if not math.isfinite(float(value)):
        return ""
    return f"{float(value):.3f}"


def control_columns_for_strategy(probe: mv25.ProbeData, control_strategy: str) -> list[str]:
    base = str(CONTROL_STRATEGIES[control_strategy]["base"])
    return mv25.control_columns_for(probe, base)


def make_classifier(probe_model: str, seed: int) -> LogisticRegression | RandomForestClassifier:
    if probe_model == "linear_logistic":
        return LogisticRegression(max_iter=3000, class_weight="balanced", solver="lbfgs", random_state=int(seed))
    if probe_model == "nonlinear_random_forest":
        return RandomForestClassifier(
            n_estimators=160,
            max_depth=6,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=int(seed),
            n_jobs=4,
        )
    raise ValueError(f"unknown probe model: {probe_model}")


def residualize_with_strategy(
    x_train: np.ndarray,
    x_eval: np.ndarray,
    c_train: np.ndarray,
    c_eval: np.ndarray,
    *,
    control_strategy: str,
    seed: int,
    fold_index: int,
) -> tuple[np.ndarray, np.ndarray]:
    if c_train.size == 0:
        return x_train, x_eval
    if bool(CONTROL_STRATEGIES[control_strategy]["shuffle"]):
        rng = np.random.default_rng(int(seed) * 1000 + int(fold_index))
        c_train = c_train[rng.permutation(c_train.shape[0])]
        c_eval = c_eval[rng.permutation(c_eval.shape[0])]
    return mv25.residualize_train_eval(x_train, x_eval, c_train, c_eval)


def cv_identity_ba_sensitivity(
    probe: mv25.ProbeData,
    control_strategy: str,
    probe_model: str,
    *,
    seed: int,
    pca_components: int,
) -> tuple[float, float, int, int]:
    combined = pd.concat(
        [
            probe.source_table.assign(_identity_label=0),
            probe.target_table.assign(_identity_label=1),
        ],
        ignore_index=True,
    )
    y = combined["_identity_label"].to_numpy(dtype=int)
    x = mv25.finite_matrix(combined, probe.feature_cols)
    control_cols = control_columns_for_strategy(probe, control_strategy)
    c = mv25.finite_matrix(combined, control_cols) if control_cols else np.empty((len(combined), 0), dtype=np.float64)

    min_class = int(np.bincount(y).min())
    n_splits = min(5, min_class)
    if n_splits < 2:
        return math.nan, math.nan, n_splits, 0

    scores: list[float] = []
    components: list[int] = []
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=int(seed))
    for fold_index, (train_idx, eval_idx) in enumerate(splitter.split(x, y)):
        x_train, x_eval = mv25.impute_from_train(x[train_idx], x[eval_idx])
        feature_scaler = StandardScaler().fit(x_train)
        x_train = feature_scaler.transform(x_train)
        x_eval = feature_scaler.transform(x_eval)
        x_train, x_eval = residualize_with_strategy(
            x_train,
            x_eval,
            c[train_idx],
            c[eval_idx],
            control_strategy=control_strategy,
            seed=int(seed),
            fold_index=int(fold_index),
        )

        max_components = min(int(pca_components), x_train.shape[0] - 1, x_train.shape[1])
        if max_components >= 1 and max_components < x_train.shape[1]:
            pca = PCA(n_components=max_components, random_state=int(seed))
            x_train = pca.fit_transform(x_train)
            x_eval = pca.transform(x_eval)
            components.append(int(max_components))
        else:
            components.append(int(x_train.shape[1]))

        clf = make_classifier(probe_model, seed)
        clf.fit(x_train, y[train_idx])
        pred = clf.predict(x_eval)
        scores.append(float(balanced_accuracy_score(y[eval_idx], pred)))

    return float(np.mean(scores)), float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0, n_splits, int(max(components))


def run_sensitivity(
    probes: list[mv25.ProbeData],
    seeds: list[int],
    pca_components: int,
    probe_models: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for probe in probes:
        for probe_model in probe_models:
            for control_strategy in CONTROL_STRATEGIES:
                control_cols = control_columns_for_strategy(probe, control_strategy)
                for seed in seeds:
                    ba, fold_std, cv_splits, actual_components = cv_identity_ba_sensitivity(
                        probe,
                        control_strategy,
                        probe_model,
                        seed=int(seed),
                        pca_components=int(pca_components),
                    )
                    rows.append(
                        {
                            "probe_id": probe.probe_id,
                            "comparison_family": probe.comparison_family,
                            "view_id": probe.view_id,
                            "modality_set": probe.modality_set,
                            "probe_model": probe_model,
                            "control_strategy": control_strategy,
                            "control_column_count": int(len(control_cols)),
                            "control_alignment": "shuffled" if bool(CONTROL_STRATEGIES[control_strategy]["shuffle"]) else "subject_aligned",
                            "seed": int(seed),
                            "source_n": int(len(probe.source_table)),
                            "target_n": int(len(probe.target_table)),
                            "feature_columns": int(len(probe.feature_cols)),
                            "pca_components": int(actual_components),
                            "cv_splits": int(cv_splits),
                            "balanced_accuracy": ba,
                            "fold_balanced_accuracy_std": fold_std,
                            "severity_basis": probe.severity_basis,
                        }
                    )
    return pd.DataFrame(rows)


def summarize(metrics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    group_cols = [
        "probe_id",
        "comparison_family",
        "view_id",
        "modality_set",
        "probe_model",
        "control_strategy",
        "control_alignment",
    ]
    for key, group in metrics.groupby(group_cols, dropna=False):
        values = pd.to_numeric(group["balanced_accuracy"], errors="coerce").dropna().to_numpy(dtype=np.float64)
        if len(values):
            mean = float(values.mean())
            std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
            half = float(stats.t.ppf(0.975, len(values) - 1) * std / math.sqrt(len(values))) if len(values) > 1 else 0.0
            ci_low = mean - half
            ci_high = mean + half
        else:
            mean = std = ci_low = ci_high = math.nan
        first = group.iloc[0]
        rows.append(
            {
                "probe_id": key[0],
                "comparison_family": key[1],
                "view_id": key[2],
                "modality_set": key[3],
                "probe_model": key[4],
                "control_strategy": key[5],
                "control_alignment": key[6],
                "seed_count": int(group["seed"].nunique()),
                "source_n": int(first["source_n"]),
                "target_n": int(first["target_n"]),
                "feature_columns": int(first["feature_columns"]),
                "control_column_count": int(first["control_column_count"]),
                "pca_components_max": int(group["pca_components"].max()),
                "balanced_accuracy_mean": mean,
                "balanced_accuracy_std": std,
                "balanced_accuracy_ci95_low": ci_low,
                "balanced_accuracy_ci95_high": ci_high,
                "min_seed_balanced_accuracy": float(values.min()) if len(values) else math.nan,
                "max_seed_balanced_accuracy": float(values.max()) if len(values) else math.nan,
                "severity_basis": str(first["severity_basis"]),
            }
        )
    return pd.DataFrame(rows).sort_values(["probe_id", "probe_model", "control_strategy"]).reset_index(drop=True)


def interpret_probe(values: dict[str, float]) -> str:
    raw = values.get("raw", math.nan)
    length = values.get("length_only", math.nan)
    severity = values.get("severity_only", math.nan)
    both = values.get("length_severity", math.nan)
    shuffled = values.get("length_severity_shuffled", math.nan)
    if raw >= 0.95 and length < 0.58 and severity >= 0.90 and both < 0.58 and shuffled >= 0.85:
        return "aligned length/acquisition controls account for the raw identity signal"
    if raw >= 0.95 and both >= 0.70:
        return "identity persists after aligned controls"
    if raw >= 0.95 and both < 0.58 and shuffled < 0.70:
        return "control sensitivity should be interpreted cautiously"
    if both >= 0.58:
        return "modest residual identity remains"
    return "near-chance after aligned controls"


def build_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    order = ["raw", "length_only", "severity_only", "length_severity", "length_severity_shuffled"]
    for key, group in summary.groupby(["probe_id", "comparison_family", "view_id", "probe_model"], dropna=False):
        values = {str(row["control_strategy"]): float(row["balanced_accuracy_mean"]) for _, row in group.iterrows()}
        display = {str(row["control_strategy"]): format_mean_ci(row) for _, row in group.iterrows()}
        first = group.iloc[0]
        row = {
            "probe_id": key[0],
            "comparison_family": key[1],
            "view_id": key[2],
            "probe_model": key[3],
            "source_n": int(first["source_n"]),
            "target_n": int(first["target_n"]),
            "raw": display.get("raw", ""),
            "length_only": display.get("length_only", ""),
            "severity_only": display.get("severity_only", ""),
            "length_severity": display.get("length_severity", ""),
            "length_severity_shuffled": display.get("length_severity_shuffled", ""),
            "raw_minus_length_severity": format_float(values.get("raw", math.nan) - values.get("length_severity", math.nan)),
            "shuffled_minus_aligned": format_float(
                values.get("length_severity_shuffled", math.nan) - values.get("length_severity", math.nan)
            ),
            "interpretation": interpret_probe(values),
        }
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["comparison_family", "view_id", "probe_model"]).reset_index(drop=True)


def write_markdown_table(table: pd.DataFrame, out_path: Path) -> None:
    columns = [
        "probe_id",
        "view_id",
        "probe_model",
        "raw",
        "length_only",
        "severity_only",
        "length_severity",
        "length_severity_shuffled",
        "interpretation",
    ]
    lines = [
        "| probe | view | probe | raw BA | length-only BA | severity-only BA | length+severity BA | shuffled-control BA | interpretation |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in table[columns].iterrows():
        lines.append(
            f"| {row['probe_id']} | {row['view_id']} | {row['probe_model']} | {row['raw']} | "
            f"{row['length_only']} | {row['severity_only']} | {row['length_severity']} | "
            f"{row['length_severity_shuffled']} | {row['interpretation']} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_protocol(out_dir: Path, summary: pd.DataFrame) -> None:
    control_counts = (
        summary[summary["control_strategy"].isin(["length_only", "severity_only", "length_severity"])]
        .drop_duplicates(["probe_id", "control_strategy"])
        .pivot(index="probe_id", columns="control_strategy", values="control_column_count")
        .reset_index()
    )
    lines = [
        "# MV30 Residualization Protocol",
        "",
        "The identity probe is fold-internal. Within each training fold, feature values are imputed from training medians, standardized on the training fold, residualized by ordinary least squares against the selected controls with an intercept, then projected by PCA fitted only on the training fold before held-out classification.",
        "",
        "The severity control is one clinical total-score covariate. The length control is not a single scalar: each modality contributes the available log-transformed acquisition or availability counters, such as transcript segment/token/chunk counts for text, duration/chunk counts for audio, and frame/segment counts for video.",
        "",
        "The shuffled-control row keeps the same covariate marginals but permutes rows within each train/evaluation fold before residualization. If shuffled controls do not remove identity while aligned controls do, the drop is attributed to corpus-linked length/acquisition structure rather than to residualization being mechanically too strong.",
        "",
        "| probe | length controls | severity controls | length+severity controls |",
        "| --- | ---: | ---: | ---: |",
    ]
    for _, row in control_counts.iterrows():
        lines.append(
            f"| {row['probe_id']} | {int(row.get('length_only', 0))} | "
            f"{int(row.get('severity_only', 0))} | {int(row.get('length_severity', 0))} |"
        )
    out_dir.joinpath("residualization_protocol.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(out_dir: Path, table: pd.DataFrame, run_summary: dict[str, Any]) -> None:
    primary = table[
        (table["comparison_family"] == "E-DAIC_vs_CMDC")
        & table["probe_model"].isin(["linear_logistic", "nonlinear_random_forest"])
    ]
    lines = [
        "# MV30 Representation-Control Sensitivity",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Reviewer-Facing Question",
        "",
        "MV25 showed that raw E-DAIC/CMDC corpus identity is near-perfect but becomes near-chance after fold-internal length and severity residualization. MV30 decomposes that result and adds a nonlinear probe plus shuffled-control rows.",
        "",
        "## Primary E-DAIC/CMDC Check",
        "",
        "| view | probe | raw BA | length-only BA | severity-only BA | length+severity BA | shuffled-control BA | interpretation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in primary.iterrows():
        lines.append(
            f"| {row['view_id']} | {row['probe_model']} | {row['raw']} | {row['length_only']} | "
            f"{row['severity_only']} | {row['length_severity']} | {row['length_severity_shuffled']} | "
            f"{row['interpretation']} |"
        )
    lines.extend(
        [
            "",
            "## Writing Implication",
            "",
            "The manuscript should not say that language or protocol was directly residualized. A defensible wording is that the raw identity signal is strongly coupled to corpus-linked length/acquisition structure and clinical severity; in the primary E-DAIC/CMDC rows, length/acquisition controls account for most of the raw separability, while severity alone does not.",
            "",
            "Same-language lineage probes remain useful because they show whether identity persists after aligned controls when language is held constant.",
            "",
            "## Files",
            "",
            "- `control_decomposition_summary.csv`",
            "- `control_decomposition_table.csv`",
            "- `control_decomposition_table.md`",
            "- `residualization_protocol.md`",
        ]
    )
    out_dir.joinpath("report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        r"clinical transcript",
        r"row prediction",
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
        "audit_id": "P5_MV30_representation_control_sensitivity_hygiene",
        "generated_at": utc_now(),
        "files_checked": int(checked),
        "artifact_hygiene_passed": not violations,
        "violation_count": int(len(violations)),
        "violations": violations,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, default=mv25.DEFAULT_INPUT_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=mv25.DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--pca-components", type=int, default=128)
    parser.add_argument("--probe-models", nargs="+", choices=PROBE_MODELS, default=list(PROBE_MODELS))
    parser.add_argument("--clean", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = args.out_dir
    if args.clean:
        clean_tracked_outputs(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    probes = mv25.build_probe_data(args.input_root, args.manifest_dir)
    metrics = run_sensitivity(
        probes,
        [int(seed) for seed in args.seeds],
        int(args.pca_components),
        [str(model) for model in args.probe_models],
    )
    metrics.to_csv(out_dir / "control_decomposition_by_seed.csv", index=False)

    summary = summarize(metrics)
    summary.to_csv(out_dir / "control_decomposition_summary.csv", index=False)

    table = build_table(summary)
    table.to_csv(out_dir / "control_decomposition_table.csv", index=False)
    write_markdown_table(table, out_dir / "control_decomposition_table.md")
    write_protocol(out_dir, summary)

    primary = table[table["comparison_family"] == "E-DAIC_vs_CMDC"].copy()
    run_summary = {
        "run_id": "P5_MV30_representation_control_sensitivity",
        "generated_at": utc_now(),
        "git_commit": git_commit(),
        "status": "complete",
        "probe_count": int(len(probes)),
        "probe_models": [str(model) for model in args.probe_models],
        "control_strategies": list(CONTROL_STRATEGIES),
        "seed_count": int(len(set(args.seeds))),
        "primary_edaic_cmdc_rows": int(len(primary)),
        "primary_min_aligned_length_severity_ba": float(
            pd.to_numeric(primary["length_severity"].str.extract(r"^([0-9.]+)")[0], errors="coerce").min()
        ),
        "primary_min_shuffled_minus_aligned_ba": float(
            pd.to_numeric(primary["shuffled_minus_aligned"], errors="coerce").min()
        ),
        "aggregate_outputs_only": True,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out_dir, table, run_summary)

    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")


if __name__ == "__main__":
    main()
