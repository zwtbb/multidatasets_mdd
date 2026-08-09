#!/usr/bin/env python3
"""Audit P5_MV06 construct evidence-localization inputs.

This readiness pass checks whether existing minimal-validation predictions and
manifest text availability can support a bounded evidence-localization workflow.
It does not read raw clinical text, export snippets, write source paths, or
score evidence. Subject-level candidate queues are written only to an ignored
local predictions file; tracked artifacts contain aggregate counts and policy.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv06_evidence_localization_readiness"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
MV01_PREDICTIONS = (
    ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv01_phq_core_bridge" / "p5_mv01_local_predictions.csv"
)
MV02_PREDICTIONS = (
    ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv02_hamd_auxiliary_bridge" / "p5_mv02_local_predictions.csv"
)

CONSTRUCT_IDS = [f"C{i:02d}" for i in range(1, 14)]
MV01_CONSTRUCTS = [f"C{i:02d}" for i in range(1, 9)]
MV02_CONSTRUCTS = [f"C{i:02d}" for i in range(1, 14)]
HAMD_KEYS = [f"HAMD{i:02d}" for i in range(1, 18)]
EVIDENCE_DATASETS = ["edaic", "cmdc", "pdch"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def nonempty(value: Any) -> bool:
    text = str(value).strip()
    return text not in {"", "nan", "NaN", "None", "null"}


def parse_item_values(value: Any) -> dict[str, float]:
    if not nonempty(value):
        return {}
    try:
        obj = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, raw_value in obj.items():
        try:
            numeric = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            parsed[str(key)] = numeric
    return parsed


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def read_manifest(manifest_dir: Path, dataset: str) -> pd.DataFrame:
    path = manifest_dir / f"{dataset}_subjects.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def path_exists(value: Any) -> bool:
    if not nonempty(value):
        return False
    path = Path(str(value))
    return path.exists()


def manifest_text_coverage(manifest_dir: Path) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    rows: list[dict[str, Any]] = []
    manifest_by_dataset: dict[str, pd.DataFrame] = {}
    for dataset in EVIDENCE_DATASETS:
        manifest = read_manifest(manifest_dir, dataset)
        manifest_by_dataset[dataset] = manifest
        valid = manifest[bool_series(manifest["file_valid"])].copy()
        valid["subject_id"] = valid["subject_id"].astype(str)
        has_text = valid["text_path"].map(nonempty) if "text_path" in valid else pd.Series(False, index=valid.index)
        existing_text = valid["text_path"].map(path_exists) if "text_path" in valid else pd.Series(False, index=valid.index)
        label_subjects = label_subject_set(dataset, valid)
        rows.append(
            {
                "dataset": dataset,
                "manifest_rows": int(len(manifest)),
                "manifest_subjects": int(manifest["subject_id"].astype(str).nunique()),
                "valid_rows": int(len(valid)),
                "valid_subjects": int(valid["subject_id"].nunique()),
                "text_rows_declared": int(has_text.sum()),
                "text_subjects_declared": int(valid.loc[has_text, "subject_id"].nunique()),
                "text_rows_existing": int(existing_text.sum()),
                "text_subjects_existing": int(valid.loc[existing_text, "subject_id"].nunique()),
                "item_or_total_label_subjects": int(len(label_subjects)),
            }
        )
    return pd.DataFrame(rows), manifest_by_dataset


def label_subject_set(dataset: str, manifest: pd.DataFrame) -> set[str]:
    subjects: set[str] = set()
    if dataset == "edaic":
        for subject_id, group in manifest.groupby("subject_id"):
            if any(parse_item_values(value) for value in group.get("phq8_items", [])):
                subjects.add(str(subject_id))
    elif dataset == "cmdc":
        for subject_id, group in manifest.groupby("subject_id"):
            if any(parse_item_values(value) for value in group.get("phq9_items", [])):
                subjects.add(str(subject_id))
            elif any(parse_item_values(value) for value in group.get("hamd17_items", [])):
                subjects.add(str(subject_id))
    elif dataset == "pdch":
        for subject_id, group in manifest.groupby("subject_id"):
            totals = pd.to_numeric(group.get("hamd17_total", pd.Series(dtype=float)), errors="coerce").dropna()
            if not totals.empty and any(parse_item_values(value) for value in group.get("hamd17_items", [])):
                subjects.add(str(subject_id))
    return subjects


def load_mv01_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    required = {"eval_dataset", "subject_key", "construct_id", "model", "protocol", "y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"MV01 predictions missing columns: {', '.join(sorted(missing))}")
    frame = frame[frame["eval_dataset"].isin(["edaic", "cmdc"]) & frame["construct_id"].isin(MV01_CONSTRUCTS)].copy()
    frame["dataset"] = frame["eval_dataset"].astype(str)
    frame["subject_id"] = frame["subject_key"].astype(str).str.split("::", n=1).str[-1]
    frame["prediction_source"] = "P5_MV01_phq_core_bridge"
    frame["target_id"] = frame["construct_id"].astype(str)
    frame["target_family"] = "construct"
    frame["selection_model"] = frame["model"].astype(str)
    frame["selection_protocol"] = frame["protocol"].astype(str)
    frame["abs_error"] = (pd.to_numeric(frame["y_pred"], errors="coerce") - pd.to_numeric(frame["y_true"], errors="coerce")).abs()
    return frame[
        [
            "prediction_source",
            "dataset",
            "subject_id",
            "target_family",
            "target_id",
            "construct_id",
            "selection_model",
            "selection_protocol",
            "y_true",
            "y_pred",
            "abs_error",
        ]
    ].copy()


def load_mv02_predictions(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    required = {"dataset", "subject_id", "eval_scope", "model", "target_family", "target_id", "y_true", "y_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"MV02 predictions missing columns: {', '.join(sorted(missing))}")
    selected = frame[
        (frame["dataset"].isin(["pdch", "cmdc"]))
        & (frame["model"].isin(["itemwise_ridge"]))
        & (frame["target_family"].isin(["hamd_construct_proxy", "hamd_item"]))
    ].copy()
    selected["prediction_source"] = "P5_MV02_hamd_auxiliary_bridge"
    selected["construct_id"] = np.where(
        selected["target_family"].astype(str) == "hamd_construct_proxy",
        selected["target_id"].astype(str),
        "",
    )
    selected["selection_model"] = selected["feature_space"].astype(str) + "::" + selected["model"].astype(str)
    selected["selection_protocol"] = selected["eval_scope"].astype(str)
    selected["abs_error"] = (
        pd.to_numeric(selected["y_pred"], errors="coerce") - pd.to_numeric(selected["y_true"], errors="coerce")
    ).abs()
    return selected[
        [
            "prediction_source",
            "dataset",
            "subject_id",
            "target_family",
            "target_id",
            "construct_id",
            "selection_model",
            "selection_protocol",
            "y_true",
            "y_pred",
            "abs_error",
        ]
    ].copy()


def prediction_source_summary(predictions: pd.DataFrame) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    group_cols = ["prediction_source", "dataset", "target_family", "selection_protocol", "selection_model"]
    for key, group in predictions.groupby(group_cols, sort=False, dropna=False):
        prediction_source, dataset, target_family, selection_protocol, selection_model = key
        rows.append(
            {
                "prediction_source": prediction_source,
                "dataset": dataset,
                "target_family": target_family,
                "selection_protocol": selection_protocol,
                "selection_model": selection_model,
                "row_count": int(len(group)),
                "subject_count": int(group["subject_id"].astype(str).nunique()),
                "target_count": int(group["target_id"].astype(str).nunique()),
                "construct_count": int(group.loc[group["construct_id"].astype(str) != "", "construct_id"].astype(str).nunique()),
                "mean_abs_error": safe_float(pd.to_numeric(group["abs_error"], errors="coerce").mean()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_coverage(
    text_coverage: pd.DataFrame,
    predictions: pd.DataFrame,
    manifest_by_dataset: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    coverage_by_dataset = text_coverage.set_index("dataset").to_dict(orient="index")
    for dataset in EVIDENCE_DATASETS:
        pred = predictions[predictions["dataset"] == dataset].copy()
        manifest = manifest_by_dataset[dataset]
        valid = manifest[bool_series(manifest["file_valid"])].copy()
        valid["subject_id"] = valid["subject_id"].astype(str)
        existing_subjects = set(
            valid.loc[valid["text_path"].map(path_exists) if "text_path" in valid else [], "subject_id"].astype(str)
        )
        pred_subjects = set(pred["subject_id"].astype(str)) if not pred.empty else set()
        constructs = sorted(set(pred.loc[pred["construct_id"].astype(str) != "", "construct_id"].astype(str)))
        rows.append(
            {
                "dataset": dataset,
                "text_subjects_existing": int(coverage_by_dataset[dataset]["text_subjects_existing"]),
                "prediction_subjects": int(len(pred_subjects)),
                "prediction_text_subject_overlap": int(len(pred_subjects & existing_subjects)),
                "target_families": ";".join(sorted(pred["target_family"].dropna().astype(str).unique())) if not pred.empty else "",
                "constructs_with_predictions": ";".join(constructs),
                "construct_count": int(len(constructs)),
                "mv06_readiness": readiness_label(dataset, len(pred_subjects & existing_subjects), constructs),
            }
        )
    return pd.DataFrame(rows)


def readiness_label(dataset: str, subject_overlap: int, constructs: list[str]) -> str:
    if subject_overlap <= 0:
        return "blocked_no_prediction_text_overlap"
    if dataset == "edaic" and set(MV01_CONSTRUCTS).issubset(set(constructs)):
        return "ready_text_localization_core_c01_c08"
    if dataset == "cmdc" and subject_overlap >= 25:
        return "ready_limited_text_localization"
    if dataset == "pdch" and subject_overlap >= 50:
        return "ready_hamd_text_localization"
    return "limited_sample_only"


def build_candidate_queue(predictions: pd.DataFrame, limit_per_bucket: int = 12) -> pd.DataFrame:
    if predictions.empty:
        return pd.DataFrame()
    usable = predictions.dropna(subset=["abs_error"]).copy()
    usable = usable[usable["target_family"].isin(["construct", "hamd_construct_proxy", "hamd_item"])].copy()
    rows: list[pd.DataFrame] = []
    group_cols = ["prediction_source", "dataset", "target_family", "target_id"]
    for _, group in usable.groupby(group_cols, sort=False, dropna=False):
        high_error = group.sort_values("abs_error", ascending=False).head(limit_per_bucket).copy()
        high_error["candidate_bucket"] = "high_prediction_error"
        low_error = group.sort_values("abs_error", ascending=True).head(limit_per_bucket).copy()
        low_error["candidate_bucket"] = "low_prediction_error"
        high_true = group.sort_values("y_true", ascending=False).head(limit_per_bucket).copy()
        high_true["candidate_bucket"] = "high_true_severity"
        rows.extend([high_error, low_error, high_true])
    if not rows:
        return pd.DataFrame()
    queue = pd.concat(rows, ignore_index=True)
    queue = queue.drop_duplicates(
        ["prediction_source", "dataset", "target_family", "target_id", "subject_id", "candidate_bucket"]
    )
    queue["raw_text_export_policy"] = "local_only_no_git"
    queue["source_path_export_policy"] = "local_only_no_git"
    return queue.sort_values(
        ["dataset", "target_family", "target_id", "candidate_bucket", "abs_error"],
        ascending=[True, True, True, True, False],
    ).reset_index(drop=True)


def candidate_summary(candidate_queue: pd.DataFrame) -> pd.DataFrame:
    if candidate_queue.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for key, group in candidate_queue.groupby(
        ["prediction_source", "dataset", "target_family", "candidate_bucket"], sort=False
    ):
        prediction_source, dataset, target_family, candidate_bucket = key
        rows.append(
            {
                "prediction_source": prediction_source,
                "dataset": dataset,
                "target_family": target_family,
                "candidate_bucket": candidate_bucket,
                "candidate_rows": int(len(group)),
                "candidate_subjects": int(group["subject_id"].astype(str).nunique()),
                "target_count": int(group["target_id"].astype(str).nunique()),
            }
        )
    return pd.DataFrame(rows)


def write_annotation_protocol(out_dir: Path, run_summary: dict[str, Any]) -> None:
    lines = [
        "# P5_MV06 Evidence Localization Readiness",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This readiness pass checks whether existing minimal-validation predictions can support a bounded evidence-localization workflow. It does not read raw clinical text, export snippets, or write source paths. Any future snippet review must stay local-only unless separately deidentified and approved.",
        "",
        "## Available Evidence Sources",
        "",
        "- E-DAIC: MV01 PHQ C01-C08 construct predictions with manifest text availability.",
        "- CMDC: MV01 PHQ C01-C08 predictions and limited MV02 HAMD sanity predictions with manifest text availability.",
        "- PDCH: MV02 HAMD item/construct predictions with manifest text availability.",
        "",
        "## Candidate Buckets",
        "",
        "- `high_prediction_error`: cases where evidence review should explain likely model failure.",
        "- `low_prediction_error`: cases where evidence review should test whether model success is supported by symptom evidence.",
        "- `high_true_severity`: cases likely to contain explicit clinical evidence for the target construct.",
        "",
        "## Annotation Fields",
        "",
        "| field | values | tracked? |",
        "| --- | --- | --- |",
        "| symptom_construct | C01-C13 or HAMD item | aggregate only |",
        "| evidence_presence | explicit_support; explicit_negation; insufficient; protocol_artifact | aggregate only |",
        "| evidence_source | participant; interviewer; scale_item; unknown | aggregate only |",
        "| evidence_strength | 0; 1; 2 | aggregate only |",
        "| time_status | current; past; hypothetical; unclear | aggregate only |",
        "| raw_snippet | free text | local-only, never tracked by default |",
        "| source_path | filesystem path | local-only, never tracked by default |",
        "",
        "## Stop Conditions",
        "",
        "- Stop evidence claims if candidate evidence mainly highlights prompts, fixed questions, or dataset identity cues.",
        "- Stop C09 claims unless the evidence is an explicit scale item or explicit clinical text.",
        "- Stop cross-dataset evidence claims unless evidence agreement is separately shown for each dataset.",
    ]
    (out_dir / "annotation_protocol.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"raw transcript",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file() or path.name.endswith("_local_predictions.csv"):
            continue
        if path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV06_evidence_localization_readiness_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(out_dir: Path, run_summary: dict[str, Any], coverage: pd.DataFrame, candidates: pd.DataFrame) -> None:
    lines = [
        "# P5_MV06 Evidence Localization Readiness",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This audit prepares RQ4 evidence localization without exporting raw snippets or source paths. It links only aggregate text availability, local prediction availability, and candidate sampling policy.",
        "",
        "## Dataset Coverage",
        "",
        "| dataset | text subjects existing | prediction subjects | overlap | constructs | readiness |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for _, row in coverage.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['text_subjects_existing']} | {row['prediction_subjects']} | "
            f"{row['prediction_text_subject_overlap']} | {row['construct_count']} | {row['mv06_readiness']} |"
        )
    lines.extend(
        [
            "",
            "## Candidate Queue Summary",
            "",
            "| dataset | target family | bucket | candidate rows | candidate subjects | targets |",
            "| --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in candidates.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['target_family']} | {row['candidate_bucket']} | "
            f"{row['candidate_rows']} | {row['candidate_subjects']} | {row['target_count']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- MV06 readiness status: `{run_summary['decision']['mv06_readiness_status']}`.",
            f"- Local candidate file written: `{run_summary['output_policy']['candidate_queue']}`.",
            f"- Raw snippets written: `{run_summary['output_policy']['raw_snippets']}`.",
            f"- Source paths written to tracked artifacts: `{run_summary['output_policy']['source_paths_tracked']}`.",
            "",
            run_summary["decision"]["short_read"],
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Tracked artifacts contain aggregate counts and policy only.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = utc_now()
    text_coverage, manifest_by_dataset = manifest_text_coverage(args.manifest_dir)
    mv01 = load_mv01_predictions(MV01_PREDICTIONS)
    mv02 = load_mv02_predictions(MV02_PREDICTIONS)
    predictions = pd.concat([frame for frame in [mv01, mv02] if not frame.empty], ignore_index=True)
    source_summary = prediction_source_summary(predictions)
    coverage = aggregate_coverage(text_coverage, predictions, manifest_by_dataset)
    candidate_queue = build_candidate_queue(predictions)
    candidates = candidate_summary(candidate_queue)

    ready_datasets = coverage[coverage["mv06_readiness"].astype(str).str.startswith("ready")]["dataset"].tolist()
    readiness_status = "ready_for_local_evidence_annotation" if ready_datasets else "blocked_no_ready_dataset"
    short_read = (
        "MV06 can proceed as a local-only evidence annotation workflow for datasets with prediction-text overlap. The next step should sample candidates from the local queue, inspect raw snippets locally, and commit only aggregate evidence agreement statistics."
        if ready_datasets
        else "MV06 cannot proceed until at least one dataset has both local predictions and existing text files."
    )

    text_coverage.to_csv(out_dir / "text_manifest_coverage.csv", index=False)
    source_summary.to_csv(out_dir / "prediction_source_summary.csv", index=False)
    coverage.to_csv(out_dir / "evidence_readiness_summary.csv", index=False)
    candidates.to_csv(out_dir / "candidate_queue_summary.csv", index=False)
    candidate_queue.to_csv(out_dir / "p5_mv06_local_candidate_predictions.csv", index=False)

    run_summary = {
        "run_id": "P5_MV06_evidence_localization_readiness",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "readiness_and_sampling_policy_no_raw_text_export",
        "decision": {
            "mv06_readiness_status": readiness_status,
            "ready_datasets": ready_datasets,
            "short_read": short_read,
        },
        "input_contract": {
            "prediction_sources": sorted(predictions["prediction_source"].unique().tolist()) if not predictions.empty else [],
            "datasets_checked": EVIDENCE_DATASETS,
            "raw_text_read": False,
            "source_paths_exported_to_tracked_artifacts": False,
        },
        "output_policy": {
            "candidate_queue": "local_only_ignored_predictions_csv",
            "raw_snippets": "not_written",
            "source_paths_tracked": "not_written",
            "aggregate_summaries": "tracked",
        },
        "artifact_hygiene_passed": False,
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "annotation_protocol.md",
            "text_manifest_coverage.csv",
            "prediction_source_summary.csv",
            "evidence_readiness_summary.csv",
            "candidate_queue_summary.csv",
        ],
        "local_only_files": ["p5_mv06_local_candidate_predictions.csv"],
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_annotation_protocol(out_dir, run_summary)
    write_report(out_dir, run_summary, coverage, candidates)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, coverage, candidates)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(f"Wrote MV06 evidence-localization readiness audit to {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
