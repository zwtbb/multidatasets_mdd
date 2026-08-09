#!/usr/bin/env python3
"""Prepare a local-only MV06 annotation workbench.

The MV06 pilot packet is intentionally subject-level and ignored by Git. This
script makes that packet easier to annotate by creating a local workbook with
one row per candidate per annotator code, local text locators, fixed annotation
fields, and reviewer instructions. Tracked outputs contain only schema,
decision rules, a run summary, and hygiene results.

No raw clinical text is read, copied, or exported.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_PACKET = (
    PHASE5_DIR
    / "p5_mv06_evidence_annotation_pilot"
    / "p5_mv06_local_annotation_packet_predictions.csv"
)
DEFAULT_SOURCE_MAP = (
    PHASE5_DIR
    / "p5_mv06_evidence_annotation_pilot"
    / "p5_mv06_local_annotation_source_map_predictions.csv"
)
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv06_evidence_annotation_workbench"

LOCAL_WORKBOOK = "p5_mv06_local_annotation_workbook_predictions.csv"
LOCAL_REVIEW_INDEX = "p5_mv06_local_review_index_predictions.csv"

TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "annotation_decision_rules.csv",
    "local_workbook_schema.csv",
    "local_artifact_manifest.csv",
]

PACKET_REQUIRED_COLUMNS = {
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
    "text_available_for_local_review",
    "explicit_evidence_only",
    "local_review_priority",
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
    "annotator_id",
}

SOURCE_MAP_REQUIRED_COLUMNS = {
    "candidate_id",
    "text_rows_declared",
    "text_rows_existing",
    "text_segments_existing_json",
    "local_text_locators_json",
}

ANNOTATION_FIELDS = [
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(sorted(missing))}")


def load_inputs(packet_path: Path, source_map_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not packet_path.exists():
        raise FileNotFoundError(
            f"{packet_path} does not exist. Run scripts/phase5_run_mv06_evidence_annotation_pilot.py first."
        )
    if not source_map_path.exists():
        raise FileNotFoundError(
            f"{source_map_path} does not exist. Run scripts/phase5_run_mv06_evidence_annotation_pilot.py first."
        )
    packet = pd.read_csv(packet_path)
    source_map = pd.read_csv(source_map_path)
    require_columns(packet, PACKET_REQUIRED_COLUMNS, "MV06 local annotation packet")
    require_columns(source_map, SOURCE_MAP_REQUIRED_COLUMNS, "MV06 local source map")
    packet["candidate_id"] = packet["candidate_id"].map(clean_value)
    source_map["candidate_id"] = source_map["candidate_id"].map(clean_value)
    if packet["candidate_id"].duplicated().any():
        raise ValueError("input packet should have one row per candidate before workbench expansion")
    return packet, source_map


def normalize_annotators(values: list[str]) -> list[str]:
    annotators = [clean_value(value) for value in values]
    annotators = [value for value in annotators if value]
    if not annotators:
        raise ValueError("at least one annotator code is required")
    if len(set(annotators)) != len(annotators):
        raise ValueError("annotator codes must be unique")
    for value in annotators:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{2,32}", value):
            raise ValueError(f"invalid annotator code {value!r}; use 2-32 ASCII letters, numbers, dash, dot, or underscore")
    return annotators


def review_instruction(row: pd.Series) -> str:
    if bool(row.get("explicit_evidence_only")):
        return "Use explicit scale item or direct clinical text only; mark weak/inferred evidence insufficient."
    bucket = str(row.get("candidate_bucket"))
    if bucket == "high_prediction_error":
        return "Check whether the target evidence is absent, contradicted, or mostly protocol artifact."
    if bucket == "low_prediction_error":
        return "Check whether model success is supported by direct target evidence."
    if bucket == "high_true_severity":
        return "Look for direct support or negation of the high-severity target."
    return "Review target evidence with the field contract."


def build_workbook(packet: pd.DataFrame, source_map: pd.DataFrame, annotators: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    source_cols = [
        "candidate_id",
        "text_segments_existing_json",
        "local_text_locators_json",
    ]
    merged = packet.merge(source_map[source_cols], on="candidate_id", how="left", validate="one_to_one")
    merged["review_instruction"] = merged.apply(review_instruction, axis=1)
    merged["annotation_round"] = "round_1"
    merged["git_export_policy"] = "local_only_no_git"
    if "local_notes" not in merged:
        merged["local_notes"] = ""
    merged["local_excerpt"] = ""

    expanded: list[pd.DataFrame] = []
    for annotator in annotators:
        copy = merged.copy()
        copy["annotator_id"] = annotator
        for field in ANNOTATION_FIELDS:
            copy[field] = ""
        expanded.append(copy)
    workbook = pd.concat(expanded, ignore_index=True)
    workbook = workbook.sort_values(
        ["dataset", "candidate_bucket", "target_family", "target_id", "candidate_id", "annotator_id"],
        kind="stable",
    ).reset_index(drop=True)

    review_index = merged[
        [
            "candidate_id",
            "dataset",
            "subject_id",
            "target_family",
            "target_id",
            "construct_id",
            "candidate_bucket",
            "local_review_priority",
            "text_rows_existing",
            "text_segments_existing_json",
            "local_text_locators_json",
            "review_instruction",
            "git_export_policy",
        ]
    ].copy()
    return workbook, review_index


def annotation_decision_rules() -> pd.DataFrame:
    rows = [
        {
            "field": "evidence_presence",
            "allowed_values": "explicit_support;explicit_negation;insufficient;protocol_artifact",
            "decision_rule": "Choose explicit_support or explicit_negation only for direct target evidence; use protocol_artifact when fixed prompts or task material explain the signal.",
        },
        {
            "field": "evidence_source",
            "allowed_values": "participant;interviewer;scale_item;unknown",
            "decision_rule": "Prefer participant for subject speech/text, interviewer for prompt-led evidence, scale_item for explicit questionnaire/clinical rating evidence.",
        },
        {
            "field": "evidence_strength",
            "allowed_values": "0;1;2",
            "decision_rule": "0 means none/contradictory/insufficient, 1 means weak or indirect, 2 means clear direct evidence.",
        },
        {
            "field": "time_status",
            "allowed_values": "current;past;hypothetical;unclear",
            "decision_rule": "Use current only for present symptom evidence; avoid upgrading past or hypothetical mentions to current symptoms.",
        },
        {
            "field": "prompt_artifact",
            "allowed_values": "yes;no;unclear",
            "decision_rule": "Use yes when the evidence is mainly induced by a prompt, fixed question, task text, or protocol cue rather than participant symptom expression.",
        },
        {
            "field": "C09_or_HAMD03_policy",
            "allowed_values": "explicit_only",
            "decision_rule": "For death/self-harm targets, do not infer from mood, distress, or general severity; require explicit scale item or direct clinical text evidence.",
        },
    ]
    return pd.DataFrame(rows)


def local_workbook_schema() -> pd.DataFrame:
    rows = [
        {
            "column_group": "candidate_metadata",
            "local_file_only": True,
            "editable": False,
            "description": "Candidate identifiers, dataset label, target label, selection model/protocol, prediction values, bucket, and review priority.",
        },
        {
            "column_group": "local_text_locator",
            "local_file_only": True,
            "editable": False,
            "description": "Local text segment names and local file locators for reviewer navigation. These columns must never be committed.",
        },
        {
            "column_group": "required_annotation_fields",
            "local_file_only": True,
            "editable": True,
            "description": "Evidence presence, source, strength, time status, prompt artifact, and stable annotator code.",
        },
        {
            "column_group": "private_free_text_fields",
            "local_file_only": True,
            "editable": True,
            "description": "Optional local excerpt and notes. These are for reviewer memory only and are ignored by aggregate export.",
        },
    ]
    return pd.DataFrame(rows)


def local_artifact_manifest(annotators: list[str], workbook: pd.DataFrame, review_index: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "file": LOCAL_WORKBOOK,
                "row_count": int(len(workbook)),
                "candidate_count": int(workbook["candidate_id"].nunique()),
                "annotator_count": len(annotators),
                "contains_subject_level_rows": True,
                "contains_raw_text": False,
                "contains_local_file_locators": True,
                "contains_private_free_text_fields": True,
                "git_policy": "ignored_local_only",
            },
            {
                "file": LOCAL_REVIEW_INDEX,
                "row_count": int(len(review_index)),
                "candidate_count": int(review_index["candidate_id"].nunique()),
                "annotator_count": 0,
                "contains_subject_level_rows": True,
                "contains_raw_text": False,
                "contains_local_file_locators": True,
                "contains_private_free_text_fields": False,
                "git_policy": "ignored_local_only",
            },
        ]
    )


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    lines = [
        "# P5_MV06 Evidence Annotation Workbench",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This workbench prepares local-only files for human MV06 evidence annotation. It does not read raw clinical text, copy snippets, train a model, or export subject-level rows to tracked artifacts.",
        "",
        "## Local Files",
        "",
        f"- Annotation workbook: `{LOCAL_WORKBOOK}`.",
        f"- Review index: `{LOCAL_REVIEW_INDEX}`.",
        "- Both local files are ignored by Git through the Phase 5 predictions rule.",
        "- The workbook can be passed to the aggregate gate with `--annotation-packet` after local review is filled.",
        "",
        "## Workbook Summary",
        "",
        f"- Candidate count: `{run_summary['selection_summary']['candidate_count']}`.",
        f"- Workbook rows: `{run_summary['selection_summary']['workbook_rows']}`.",
        f"- Annotator codes: `{run_summary['selection_summary']['annotator_count']}`.",
        f"- Candidates with local text locators: `{run_summary['selection_summary']['candidates_with_local_text_locators']}`.",
        "",
        "## Annotation Rules",
        "",
        "- Use only the allowed categorical values recorded in `annotation_decision_rules.csv`.",
        "- Keep optional excerpts and reviewer notes inside the ignored local workbook only.",
        "- Treat death/self-harm targets as explicit-evidence-only.",
        "- Mark prompt-driven or fixed-task evidence as protocol artifact instead of symptom evidence.",
        "",
        "## Next Command",
        "",
        "After local annotation is filled, run:",
        "",
        "```bash",
        f"python scripts/phase5_summarize_mv06_evidence_annotations.py --annotation-packet {display_path(out_dir / LOCAL_WORKBOOK)}",
        "```",
        "",
        "## Decision",
        "",
        f"- Workbench status: `{run_summary['decision']['workbench_status']}`.",
        "- This is annotation infrastructure only. RQ4 evidence-localization claims remain blocked until the aggregate summary gate passes.",
        "",
        "## Hygiene",
        "",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "- Tracked files contain no raw text, no local source locators, and no subject-level annotation rows.",
    ]
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
        r"raw_snippet",
        r"source_path",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(out_dir.glob("*")):
        if not path.is_file() or path.name not in TRACKED_FILES:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": path.name, "pattern": pattern})
    return {
        "audit_id": "P5_MV06_annotation_workbench_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
        "local_only_files_skipped": [LOCAL_WORKBOOK, LOCAL_REVIEW_INDEX],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation-packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--source-map", type=Path, default=DEFAULT_SOURCE_MAP)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--annotator", action="append", default=None, help="Stable local annotator code. Repeat for double annotation.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing local workbook and review index.")
    args = parser.parse_args()

    annotators = normalize_annotators(args.annotator or ["ann_a", "ann_b"])
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    local_workbook_path = out_dir / LOCAL_WORKBOOK
    local_review_index_path = out_dir / LOCAL_REVIEW_INDEX
    for path in [local_workbook_path, local_review_index_path]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"{path} exists. Use --overwrite only if local annotation edits are backed up.")

    generated_at = utc_now()
    packet, source_map = load_inputs(args.annotation_packet, args.source_map)
    workbook, review_index = build_workbook(packet, source_map, annotators)
    workbook.to_csv(local_workbook_path, index=False)
    review_index.to_csv(local_review_index_path, index=False)
    shutil.copystat(args.annotation_packet, local_workbook_path, follow_symlinks=True)

    rules = annotation_decision_rules()
    schema = local_workbook_schema()
    manifest = local_artifact_manifest(annotators, workbook, review_index)
    rules.to_csv(out_dir / "annotation_decision_rules.csv", index=False)
    schema.to_csv(out_dir / "local_workbook_schema.csv", index=False)
    manifest.to_csv(out_dir / "local_artifact_manifest.csv", index=False)

    locator_present = review_index["local_text_locators_json"].map(clean_value).map(bool)
    run_summary = {
        "run_id": "P5_MV06_evidence_annotation_workbench",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "local_only_human_annotation_workbench",
        "input_contract": {
            "raw_text_read": False,
            "source_locator_map_read": True,
            "source_locator_map_exported_to_tracked_outputs": False,
            "input_candidate_count": int(packet["candidate_id"].nunique()),
            "input_packet_rows": int(len(packet)),
        },
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "local_only_files": [LOCAL_WORKBOOK, LOCAL_REVIEW_INDEX],
            "raw_text_written": False,
            "subject_level_rows_in_tracked_outputs": False,
            "local_file_locators_in_tracked_outputs": False,
            "local_file_locators_in_local_workbook": True,
        },
        "selection_summary": {
            "candidate_count": int(workbook["candidate_id"].nunique()),
            "workbook_rows": int(len(workbook)),
            "review_index_rows": int(len(review_index)),
            "annotator_count": len(annotators),
            "candidates_with_local_text_locators": int(locator_present.sum()),
        },
        "decision": {
            "workbench_status": "ready_for_local_human_annotation",
            "short_read": (
                "A two-annotator local MV06 workbook is ready. It contains local text locators and private free-text fields only in ignored local files; tracked outputs are schema and hygiene summaries only."
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
    print(f"Wrote MV06 annotation workbench to {display_path(out_dir)}")


if __name__ == "__main__":
    main()
