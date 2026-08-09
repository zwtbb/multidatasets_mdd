#!/usr/bin/env python3
"""Prepare a local-only P5_MV06 evidence annotation pilot packet.

This script samples a bounded, balanced subset from the local MV06 candidate
queue, creates ignored subject-level annotation files for local review, and
writes only aggregate sampling and hygiene summaries to versionable artifacts.
It never reads or exports raw clinical text. Local source locators are written
only to files whose names match the repository's ignored predictions pattern.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = (
    ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv06_evidence_localization_readiness"
    / "p5_mv06_local_candidate_predictions.csv"
)
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv06_evidence_annotation_pilot"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"

EVIDENCE_DATASETS = ["edaic", "cmdc", "pdch"]
TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "annotation_field_template.csv",
    "sampling_summary.csv",
    "construct_sampling_summary.csv",
    "dataset_bucket_summary.csv",
    "text_access_summary.csv",
    "local_artifact_manifest.csv",
]
LOCAL_PACKET = "p5_mv06_local_annotation_packet_predictions.csv"
LOCAL_SOURCE_MAP = "p5_mv06_local_annotation_source_map_predictions.csv"

BUCKET_PRIORITY = {
    "high_prediction_error": 0,
    "high_true_severity": 1,
    "low_prediction_error": 2,
}
SAFETY_TARGETS = {"C09", "HAMD03"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def nonempty(value: Any) -> bool:
    text = str(value).strip()
    return text not in {"", "nan", "NaN", "None", "null", "<NA>"}


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def path_exists(value: Any) -> bool:
    if not nonempty(value):
        return False
    return Path(str(value)).exists()


def stable_candidate_id(row: pd.Series) -> str:
    parts = [
        row.get("prediction_source", ""),
        row.get("dataset", ""),
        row.get("subject_id", ""),
        row.get("target_family", ""),
        row.get("target_id", ""),
        row.get("candidate_bucket", ""),
        row.get("selection_model", ""),
        row.get("selection_protocol", ""),
    ]
    digest = hashlib.sha1("||".join(map(str, parts)).encode("utf-8")).hexdigest()
    return f"mv06_{digest[:12]}"


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(sorted(missing))}")


def load_candidate_queue(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run scripts/phase5_audit_mv06_evidence_localization_inputs.py first."
        )
    frame = pd.read_csv(path)
    require_columns(
        frame,
        {
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
            "candidate_bucket",
        },
        "MV06 candidate queue",
    )
    frame = frame[frame["dataset"].isin(EVIDENCE_DATASETS)].copy()
    for column in [
        "prediction_source",
        "dataset",
        "subject_id",
        "target_family",
        "target_id",
        "construct_id",
        "selection_model",
        "selection_protocol",
        "candidate_bucket",
    ]:
        frame[column] = frame[column].fillna("").astype(str)
    for column in ["y_true", "y_pred", "abs_error"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["abs_error"]).reset_index(drop=True)


def sort_for_bucket(group: pd.DataFrame) -> pd.DataFrame:
    bucket = str(group["candidate_bucket"].iloc[0])
    if bucket == "low_prediction_error":
        return group.sort_values(["abs_error", "subject_id"], ascending=[True, True])
    if bucket == "high_true_severity":
        return group.sort_values(["y_true", "abs_error", "subject_id"], ascending=[False, False, True])
    return group.sort_values(["abs_error", "y_true", "subject_id"], ascending=[False, False, True])


def sample_candidates(
    queue: pd.DataFrame,
    max_per_target_bucket: int,
    max_per_dataset_bucket: int,
) -> pd.DataFrame:
    selected_groups: list[pd.DataFrame] = []
    group_cols = ["prediction_source", "dataset", "target_family", "target_id", "candidate_bucket"]
    for _, group in queue.groupby(group_cols, sort=True, dropna=False):
        selected_groups.append(sort_for_bucket(group).head(max_per_target_bucket).copy())
    if not selected_groups:
        return pd.DataFrame()

    selected = pd.concat(selected_groups, ignore_index=True)
    selected = selected.drop_duplicates(
        [
            "prediction_source",
            "dataset",
            "target_family",
            "target_id",
            "subject_id",
            "candidate_bucket",
            "selection_model",
            "selection_protocol",
        ]
    ).copy()
    selected["bucket_priority"] = selected["candidate_bucket"].map(BUCKET_PRIORITY).fillna(99).astype(int)
    selected["safety_sensitive"] = selected.apply(
        lambda row: bool({str(row["target_id"]), str(row["construct_id"])} & SAFETY_TARGETS),
        axis=1,
    )

    capped_groups: list[pd.DataFrame] = []
    for _, group in selected.groupby(["dataset", "candidate_bucket"], sort=True):
        capped_groups.append(
            group.sort_values(["safety_sensitive", "bucket_priority", "abs_error", "target_id", "subject_id"], ascending=[False, True, False, True, True])
            .head(max_per_dataset_bucket)
            .copy()
        )
    selected = pd.concat(capped_groups, ignore_index=True)
    selected = selected.sort_values(
        ["dataset", "bucket_priority", "target_family", "target_id", "abs_error", "subject_id"],
        ascending=[True, True, True, True, False, True],
    ).reset_index(drop=True)
    selected["candidate_id"] = selected.apply(stable_candidate_id, axis=1)
    return selected


def load_subject_text_inventory(manifest_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for dataset in EVIDENCE_DATASETS:
        manifest_path = manifest_dir / f"{dataset}_subjects.csv"
        if not manifest_path.exists():
            raise FileNotFoundError(manifest_path)
        manifest = pd.read_csv(manifest_path)
        require_columns(manifest, {"subject_id", "segment_id", "text_path", "file_valid"}, str(manifest_path))
        manifest = manifest[bool_series(manifest["file_valid"])].copy()
        manifest["subject_id"] = manifest["subject_id"].astype(str)
        manifest["segment_id"] = manifest["segment_id"].astype(str)
        manifest["text_declared"] = manifest["text_path"].map(nonempty)
        manifest["text_existing"] = manifest["text_path"].map(path_exists)
        for subject_id, group in manifest.groupby("subject_id", sort=True):
            declared = group[group["text_declared"]].copy()
            existing = group[group["text_existing"]].copy()
            rows.append(
                {
                    "dataset": dataset,
                    "subject_id": str(subject_id),
                    "text_rows_declared": int(len(declared)),
                    "text_rows_existing": int(len(existing)),
                    "text_segments_declared_json": json.dumps(
                        sorted(declared["segment_id"].dropna().astype(str).unique().tolist()), ensure_ascii=True
                    ),
                    "text_segments_existing_json": json.dumps(
                        sorted(existing["segment_id"].dropna().astype(str).unique().tolist()), ensure_ascii=True
                    ),
                    "local_text_locators_json": json.dumps(
                        sorted(existing["text_path"].dropna().astype(str).unique().tolist()), ensure_ascii=True
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_local_annotation_files(selected: pd.DataFrame, inventory: pd.DataFrame, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = selected.merge(inventory, on=["dataset", "subject_id"], how="left")
    for column in ["text_rows_declared", "text_rows_existing"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0).astype(int)
    merged["text_available_for_local_review"] = merged["text_rows_existing"] > 0
    merged["explicit_evidence_only"] = merged["safety_sensitive"].map(lambda value: bool(value))
    merged["local_review_priority"] = merged.apply(local_review_priority, axis=1)
    merged["git_export_policy"] = "local_only_no_git"

    annotation_columns = {
        "evidence_presence": "",
        "evidence_source": "",
        "evidence_strength": "",
        "time_status": "",
        "prompt_artifact": "",
        "annotator_id": "",
        "local_notes": "",
    }
    packet_cols = [
        "candidate_id",
        "prediction_source",
        "dataset",
        "subject_id",
        "target_family",
        "target_id",
        "construct_id",
        "candidate_bucket",
        "selection_model",
        "selection_protocol",
        "y_true",
        "y_pred",
        "abs_error",
        "text_rows_declared",
        "text_rows_existing",
        "text_available_for_local_review",
        "explicit_evidence_only",
        "local_review_priority",
        "git_export_policy",
    ]
    packet = merged[packet_cols].copy()
    for column, default in annotation_columns.items():
        packet[column] = default
    packet.to_csv(out_dir / LOCAL_PACKET, index=False)

    source_map = merged[
        [
            "candidate_id",
            "dataset",
            "subject_id",
            "text_rows_declared",
            "text_rows_existing",
            "text_segments_declared_json",
            "text_segments_existing_json",
            "local_text_locators_json",
        ]
    ].copy()
    source_map["git_export_policy"] = "local_only_no_git"
    source_map.to_csv(out_dir / LOCAL_SOURCE_MAP, index=False)
    return packet, source_map


def local_review_priority(row: pd.Series) -> str:
    if bool(row.get("safety_sensitive")):
        return "safety_sensitive_explicit_evidence_only"
    bucket = str(row.get("candidate_bucket"))
    if bucket == "high_prediction_error":
        return "failure_case_review"
    if bucket == "high_true_severity":
        return "positive_evidence_review"
    return "model_success_support_review"


def annotation_field_template() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "field": "evidence_presence",
                "allowed_values": "explicit_support;explicit_negation;insufficient;protocol_artifact",
                "required_for_local_annotation": True,
                "tracked_release_policy": "aggregate_counts_only",
            },
            {
                "field": "evidence_source",
                "allowed_values": "participant;interviewer;scale_item;unknown",
                "required_for_local_annotation": True,
                "tracked_release_policy": "aggregate_counts_only",
            },
            {
                "field": "evidence_strength",
                "allowed_values": "0;1;2",
                "required_for_local_annotation": True,
                "tracked_release_policy": "aggregate_counts_only",
            },
            {
                "field": "time_status",
                "allowed_values": "current;past;hypothetical;unclear",
                "required_for_local_annotation": True,
                "tracked_release_policy": "aggregate_counts_only",
            },
            {
                "field": "prompt_artifact",
                "allowed_values": "yes;no;unclear",
                "required_for_local_annotation": True,
                "tracked_release_policy": "aggregate_counts_only",
            },
            {
                "field": "local_excerpt",
                "allowed_values": "free_text",
                "required_for_local_annotation": False,
                "tracked_release_policy": "local_only_never_git_by_default",
            },
            {
                "field": "local_notes",
                "allowed_values": "free_text",
                "required_for_local_annotation": False,
                "tracked_release_policy": "local_only_never_git_by_default",
            },
        ]
    )


def write_summaries(packet: pd.DataFrame, source_map: pd.DataFrame, out_dir: Path) -> dict[str, Any]:
    packet["has_text"] = packet["text_rows_existing"] > 0

    sampling_summary = summarize(
        packet,
        ["dataset", "target_family", "candidate_bucket"],
    )
    construct_summary = summarize(
        packet,
        ["dataset", "target_family", "target_id", "candidate_bucket"],
    )
    dataset_bucket_summary = summarize(packet, ["dataset", "candidate_bucket"])
    text_access_summary = (
        packet.groupby("dataset", sort=True)
        .agg(
            selected_rows=("candidate_id", "count"),
            selected_subjects=("subject_id", "nunique"),
            rows_with_existing_text=("has_text", "sum"),
            subjects_with_existing_text=("subject_id", lambda s: packet.loc[s.index[packet.loc[s.index, "has_text"]], "subject_id"].nunique()),
            total_existing_text_rows=("text_rows_existing", "sum"),
            safety_sensitive_rows=("explicit_evidence_only", "sum"),
        )
        .reset_index()
    )

    sampling_summary.to_csv(out_dir / "sampling_summary.csv", index=False)
    construct_summary.to_csv(out_dir / "construct_sampling_summary.csv", index=False)
    dataset_bucket_summary.to_csv(out_dir / "dataset_bucket_summary.csv", index=False)
    text_access_summary.to_csv(out_dir / "text_access_summary.csv", index=False)
    annotation_field_template().to_csv(out_dir / "annotation_field_template.csv", index=False)

    local_artifact_manifest = pd.DataFrame(
        [
            {
                "file": LOCAL_PACKET,
                "contains_subject_level_rows": True,
                "contains_raw_text": False,
                "contains_local_file_locators": False,
                "git_policy": "ignored_local_only",
            },
            {
                "file": LOCAL_SOURCE_MAP,
                "contains_subject_level_rows": True,
                "contains_raw_text": False,
                "contains_local_file_locators": True,
                "git_policy": "ignored_local_only",
            },
        ]
    )
    local_artifact_manifest.to_csv(out_dir / "local_artifact_manifest.csv", index=False)

    return {
        "selected_rows": int(len(packet)),
        "selected_subjects": int(
            packet[["dataset", "subject_id"]].drop_duplicates().shape[0]
        ),
        "datasets": sorted(packet["dataset"].unique().tolist()),
        "rows_with_existing_text": int(packet["has_text"].sum()),
        "subjects_with_existing_text": int(
            packet.loc[packet["has_text"], ["dataset", "subject_id"]].drop_duplicates().shape[0]
        ),
        "safety_sensitive_rows": int(packet["explicit_evidence_only"].sum()),
        "local_packet_rows": int(len(packet)),
        "local_source_map_rows": int(len(source_map)),
    }


def summarize(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(group_cols, sort=True, dropna=False):
        key_tuple = key if isinstance(key, tuple) else (key,)
        row = dict(zip(group_cols, key_tuple))
        row.update(
            {
                "selected_rows": int(len(group)),
                "selected_subjects": int(group["subject_id"].nunique()),
                "target_count": int(group["target_id"].nunique()),
                "rows_with_existing_text": int(group["has_text"].sum()),
                "safety_sensitive_rows": int(group["explicit_evidence_only"].sum()),
                "mean_abs_error": safe_float(group["abs_error"].mean()),
                "mean_y_true": safe_float(group["y_true"].mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    sampling = pd.read_csv(out_dir / "sampling_summary.csv")
    text_access = pd.read_csv(out_dir / "text_access_summary.csv")
    lines = [
        "# P5_MV06 Evidence Annotation Pilot",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This pilot prepares a bounded local annotation packet for RQ4 evidence localization. It samples from the local MV06 candidate queue and writes subject-level review files only to ignored local artifacts. Tracked outputs contain aggregate sampling, annotation-field policy, and hygiene checks only.",
        "",
        "## Local Packet",
        "",
        f"- Local annotation packet: `{LOCAL_PACKET}`.",
        f"- Local locator map: `{LOCAL_SOURCE_MAP}`.",
        "- Raw clinical text read: `false`.",
        "- Raw clinical text written: `false`.",
        "- Local file locators in tracked artifacts: `false`.",
        "",
        "## Dataset Text Access",
        "",
        "| dataset | selected rows | selected subjects | rows with existing text | subjects with existing text | safety-sensitive rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in text_access.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['selected_rows']} | {row['selected_subjects']} | "
            f"{row['rows_with_existing_text']} | {row['subjects_with_existing_text']} | {row['safety_sensitive_rows']} |"
        )
    lines.extend(
        [
            "",
            "## Sampling Summary",
            "",
            "| dataset | target family | bucket | rows | subjects | targets | with text |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in sampling.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['target_family']} | {row['candidate_bucket']} | "
            f"{row['selected_rows']} | {row['selected_subjects']} | {row['target_count']} | {row['rows_with_existing_text']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Pilot status: `{run_summary['decision']['pilot_status']}`.",
            "- Use this as a manual evidence-review packet, not as model-training supervision.",
            "- C09/HAMD03 rows are marked explicit-evidence-only.",
            "- Do not make evidence-localization claims until local annotations are completed and aggregated agreement/error summaries pass hygiene review.",
            "",
            "## Hygiene",
            "",
            f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
            "- Versionable files contain no raw snippets, no local source locators, and no subject-level candidate rows.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        r"\.avi\b",
        r"local_text_locators_json",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file():
            continue
        if path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV06_evidence_annotation_pilot_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
        "local_only_files_skipped": [LOCAL_PACKET, LOCAL_SOURCE_MAP],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-per-target-bucket", type=int, default=1)
    parser.add_argument("--max-per-dataset-bucket", type=int, default=20)
    args = parser.parse_args()

    if args.max_per_target_bucket < 1 or args.max_per_dataset_bucket < 1:
        raise ValueError("sampling limits must be positive")

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    queue = load_candidate_queue(args.candidate_queue)
    selected = sample_candidates(queue, args.max_per_target_bucket, args.max_per_dataset_bucket)
    if selected.empty:
        raise SystemExit("No MV06 candidates selected")
    inventory = load_subject_text_inventory(args.manifest_dir)
    packet, source_map = build_local_annotation_files(selected, inventory, out_dir)
    summary = write_summaries(packet, source_map, out_dir)

    run_summary = {
        "run_id": "P5_MV06_evidence_annotation_pilot",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "local_annotation_packet_and_tracked_aggregate_sampling_only",
        "sampling_contract": {
            "candidate_queue": "local_only_mv06_readiness_candidate_predictions",
            "max_per_target_bucket": args.max_per_target_bucket,
            "max_per_dataset_bucket": args.max_per_dataset_bucket,
            "bucket_priority": BUCKET_PRIORITY,
        },
        "input_contract": {
            "raw_text_read": False,
            "candidate_queue_rows": int(len(queue)),
            "candidate_queue_subjects": int(queue["subject_id"].nunique()),
        },
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "local_only_files": [LOCAL_PACKET, LOCAL_SOURCE_MAP],
            "raw_text_written": False,
            "local_file_locators_in_tracked_artifacts": False,
            "subject_level_rows_in_tracked_artifacts": False,
        },
        "selection_summary": summary,
        "decision": {
            "pilot_status": "ready_for_manual_local_annotation",
            "short_read": (
                "A bounded MV06 local annotation packet is ready. It should be annotated locally and later summarized only as aggregate evidence agreement, prompt-artifact rate, evidence-source distribution, and construct coverage."
            ),
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(f"Wrote MV06 evidence annotation pilot to {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
