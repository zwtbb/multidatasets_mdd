#!/usr/bin/env python3
"""Prepare a local-only MV06 human review pack.

This script joins the ignored MV06 human annotation workbench with the ignored
AI triage preannotation workbook. It writes a reviewer-friendly local pack with
AI suggestions, review priority ranks, and the original blank human annotation
fields side by side.

The pack is a convenience layer only. It does not modify the human workbench,
does not count AI suggestions as human labels, and does not unblock RQ4 evidence
claims. Tracked outputs contain only aggregate counts, schema, a run summary,
and hygiene checks.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_WORKBOOK = (
    PHASE5_DIR
    / "p5_mv06_evidence_annotation_workbench"
    / "p5_mv06_local_annotation_workbook_predictions.csv"
)
DEFAULT_AI_PREANNOTATION = (
    PHASE5_DIR
    / "p5_mv06_ai_preannotation_triage"
    / "p5_mv06_local_ai_preannotation_workbook_predictions.csv"
)
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv06_human_review_pack"

LOCAL_REVIEW_PACK = "p5_mv06_local_human_review_pack_predictions.csv"
LOCAL_CANDIDATE_INDEX = "p5_mv06_local_human_review_candidate_index_predictions.csv"

TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "review_pack_schema.csv",
    "aggregate_review_pack_summary.csv",
    "aggregate_priority_summary.csv",
    "aggregate_human_review_progress_summary.csv",
    "local_artifact_manifest.csv",
]

ANNOTATION_FIELDS = [
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
]

ALLOWED_VALUES = {
    "evidence_presence": {"explicit_support", "explicit_negation", "insufficient", "protocol_artifact"},
    "evidence_source": {"participant", "interviewer", "scale_item", "unknown"},
    "evidence_strength": {"0", "1", "2"},
    "time_status": {"current", "past", "hypothetical", "unclear"},
    "prompt_artifact": {"yes", "no", "unclear"},
}

WORKBOOK_REQUIRED_COLUMNS = {
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
    "annotator_id",
    "local_notes",
    "review_instruction",
    "annotation_round",
    "local_excerpt",
    *ANNOTATION_FIELDS,
}

AI_REQUIRED_COLUMNS = {
    "candidate_id",
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
    "local_notes",
    "local_excerpt",
    "ai_target_construct",
    "ai_matched_keyword_count",
    "ai_files_scanned",
    "ai_text_chars_scanned",
    "ai_claim_policy",
}

REVIEW_BASE_SCORES = {
    "safety_sensitive_explicit_evidence_only": 100.0,
    "failure_case_review": 78.0,
    "positive_evidence_review": 68.0,
    "model_success_support_review": 52.0,
}

BUCKET_SCORES = {
    "high_prediction_error": 20.0,
    "high_true_severity": 15.0,
    "low_prediction_error": 8.0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
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


def normalize_bool(value: Any) -> bool:
    return clean_value(value).lower() in {"true", "1", "yes", "y"}


def normalize_field_value(field: str, value: Any) -> str:
    text = clean_value(value).strip().lower()
    if field == "evidence_strength" and text:
        try:
            numeric = float(text)
        except ValueError:
            return text
        if math.isfinite(numeric) and numeric.is_integer():
            return str(int(numeric))
    return text


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if math.isfinite(out) else default


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(sorted(missing))}")


def load_workbook(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run phase5_prepare_mv06_annotation_workbench.py first.")
    frame = pd.read_csv(path)
    require_columns(frame, WORKBOOK_REQUIRED_COLUMNS, "MV06 human annotation workbook")
    frame["candidate_id"] = frame["candidate_id"].map(clean_value)
    if not frame["candidate_id"].map(bool).all():
        raise ValueError("candidate_id cannot be empty in the human workbook")
    for field in ANNOTATION_FIELDS:
        frame[field] = frame[field].map(lambda value, field=field: normalize_field_value(field, value))
    frame["annotator_id"] = frame["annotator_id"].map(clean_value)
    frame["abs_error"] = pd.to_numeric(frame["abs_error"], errors="coerce")
    frame["text_available_for_local_review"] = frame["text_available_for_local_review"].map(normalize_bool)
    frame["explicit_evidence_only"] = frame["explicit_evidence_only"].map(normalize_bool)
    return frame


def load_ai_preannotation(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run phase5_run_mv06_local_ai_preannotation.py first.")
    frame = pd.read_csv(path)
    require_columns(frame, AI_REQUIRED_COLUMNS, "MV06 AI preannotation workbook")
    frame["candidate_id"] = frame["candidate_id"].map(clean_value)
    if frame["candidate_id"].duplicated().any():
        raise ValueError("AI preannotation should contain one row per candidate_id")
    for field in ANNOTATION_FIELDS:
        frame[field] = frame[field].map(lambda value, field=field: normalize_field_value(field, value))
    return frame


def annotation_row_complete(row: pd.Series) -> bool:
    if not clean_value(row.get("annotator_id")):
        return False
    for field in ANNOTATION_FIELDS:
        value = normalize_field_value(field, row.get(field))
        if not value or value not in ALLOWED_VALUES[field]:
            return False
    return True


def priority_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    if normalize_bool(row.get("explicit_evidence_only")):
        reasons.append("explicit_evidence_only")
    bucket = clean_value(row.get("candidate_bucket"))
    if bucket:
        reasons.append(bucket)
    existing_priority = clean_value(row.get("local_review_priority"))
    if existing_priority:
        reasons.append(existing_priority)
    ai_presence = clean_value(row.get("ai_suggested_evidence_presence"))
    if ai_presence == "protocol_artifact":
        reasons.append("ai_protocol_artifact")
    elif ai_presence == "insufficient":
        reasons.append("ai_insufficient")
    elif ai_presence in {"explicit_support", "explicit_negation"}:
        reasons.append("ai_explicit_evidence")
    if safe_float(row.get("ai_matched_keyword_count")) > 0:
        reasons.append("ai_keyword_match")
    if not normalize_bool(row.get("text_available_for_local_review")):
        reasons.append("missing_local_text")
    target = clean_value(row.get("target_id")).upper()
    if target in {"C09", "HAMD03"}:
        reasons.append("safety_sensitive_target")
    return ";".join(dict.fromkeys(reasons))


def priority_score(row: pd.Series) -> float:
    score = REVIEW_BASE_SCORES.get(clean_value(row.get("local_review_priority")), 40.0)
    score += BUCKET_SCORES.get(clean_value(row.get("candidate_bucket")), 0.0)
    score += min(max(safe_float(row.get("abs_error")), 0.0), 4.0) * 4.0
    if normalize_bool(row.get("explicit_evidence_only")):
        score += 25.0
    if normalize_bool(row.get("text_available_for_local_review")):
        score += 8.0
    else:
        score -= 35.0
    ai_presence = clean_value(row.get("ai_suggested_evidence_presence"))
    if ai_presence == "protocol_artifact":
        score += 20.0
    elif ai_presence == "insufficient" and clean_value(row.get("candidate_bucket")) == "high_prediction_error":
        score += 14.0
    elif ai_presence in {"explicit_support", "explicit_negation"}:
        score += 10.0
    if safe_float(row.get("ai_matched_keyword_count")) > 0:
        score += 12.0
    target = clean_value(row.get("target_id")).upper()
    if target in {"C09", "HAMD03"}:
        score += 15.0
    return round(score, 3)


def priority_band(score: float) -> str:
    if score >= 135:
        return "priority_1_immediate"
    if score >= 110:
        return "priority_2_high"
    if score >= 82:
        return "priority_3_balanced"
    return "priority_4_holdout"


def build_review_pack(workbook: pd.DataFrame, ai: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ai_cols = [
        "candidate_id",
        "evidence_presence",
        "evidence_source",
        "evidence_strength",
        "time_status",
        "prompt_artifact",
        "local_notes",
        "local_excerpt",
        "ai_target_construct",
        "ai_matched_keyword_count",
        "ai_files_scanned",
        "ai_text_chars_scanned",
        "ai_claim_policy",
    ]
    renamed_ai = ai[ai_cols].rename(
        columns={
            "evidence_presence": "ai_suggested_evidence_presence",
            "evidence_source": "ai_suggested_evidence_source",
            "evidence_strength": "ai_suggested_evidence_strength",
            "time_status": "ai_suggested_time_status",
            "prompt_artifact": "ai_suggested_prompt_artifact",
            "local_notes": "ai_local_notes",
            "local_excerpt": "ai_local_excerpt",
        }
    )
    pack = workbook.merge(renamed_ai, on="candidate_id", how="left", validate="many_to_one")
    for column in [
        "ai_suggested_evidence_presence",
        "ai_suggested_evidence_source",
        "ai_suggested_evidence_strength",
        "ai_suggested_time_status",
        "ai_suggested_prompt_artifact",
        "ai_local_notes",
        "ai_local_excerpt",
        "ai_target_construct",
        "ai_claim_policy",
    ]:
        pack[column] = pack[column].map(clean_value)
    for column in ["ai_matched_keyword_count", "ai_files_scanned", "ai_text_chars_scanned"]:
        pack[column] = pd.to_numeric(pack[column], errors="coerce").fillna(0).astype(int)

    candidate_priority = pack.drop_duplicates("candidate_id", keep="first").copy()
    candidate_priority["review_priority_score"] = candidate_priority.apply(priority_score, axis=1)
    candidate_priority["review_priority_band"] = candidate_priority["review_priority_score"].map(priority_band)
    candidate_priority["review_priority_reason"] = candidate_priority.apply(priority_reason, axis=1)
    candidate_priority = candidate_priority.sort_values(
        ["review_priority_score", "dataset", "target_family", "candidate_id"],
        ascending=[False, True, True, True],
    ).reset_index(drop=True)
    candidate_priority["review_rank"] = candidate_priority.index + 1
    priority_cols = [
        "candidate_id",
        "review_rank",
        "review_priority_score",
        "review_priority_band",
        "review_priority_reason",
    ]
    pack = pack.merge(candidate_priority[priority_cols], on="candidate_id", how="left", validate="many_to_one")
    pack["human_annotation_complete"] = pack.apply(annotation_row_complete, axis=1)
    complete_counts = pack.loc[pack["human_annotation_complete"]].groupby("candidate_id")["annotator_id"].nunique()
    pack["candidate_complete_once"] = pack["candidate_id"].map(lambda candidate_id: complete_counts.get(candidate_id, 0) >= 1)
    pack["candidate_double_complete"] = pack["candidate_id"].map(lambda candidate_id: complete_counts.get(candidate_id, 0) >= 2)
    pack["review_pack_policy"] = "local_only_human_review_aid_not_claimable"
    pack["copy_back_instruction"] = (
        "Use AI fields only as suggestions; enter verified human decisions in the original evidence_* fields "
        "for the matching candidate_id and annotator_id before running the summary gate."
    )

    candidate_cols = [
        "candidate_id",
        "review_rank",
        "review_priority_score",
        "review_priority_band",
        "review_priority_reason",
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
        "text_rows_existing",
        "text_available_for_local_review",
        "explicit_evidence_only",
        "local_review_priority",
        "review_instruction",
        "ai_suggested_evidence_presence",
        "ai_suggested_evidence_source",
        "ai_suggested_evidence_strength",
        "ai_suggested_time_status",
        "ai_suggested_prompt_artifact",
        "ai_target_construct",
        "ai_matched_keyword_count",
        "ai_files_scanned",
        "ai_text_chars_scanned",
        "ai_claim_policy",
        "ai_local_notes",
        "ai_local_excerpt",
        "text_segments_existing_json",
        "local_text_locators_json",
        "candidate_complete_once",
        "candidate_double_complete",
        "review_pack_policy",
    ]
    index_cols = [column for column in candidate_cols if column in pack.columns]
    candidate_index = pack.sort_values("review_rank").drop_duplicates("candidate_id", keep="first")[index_cols].copy()
    pack = pack.sort_values(["review_rank", "annotator_id"]).reset_index(drop=True)
    return pack, candidate_index


def aggregate_review_pack_summary(pack: pd.DataFrame) -> pd.DataFrame:
    candidates = pack.drop_duplicates("candidate_id", keep="first").copy()
    rows: list[dict[str, Any]] = []
    for key, group in candidates.groupby(["dataset", "target_family", "candidate_bucket"], sort=True, dropna=False):
        dataset, target_family, candidate_bucket = key
        rows.append(
            {
                "dataset": dataset,
                "target_family": target_family,
                "candidate_bucket": candidate_bucket,
                "candidate_count": int(len(group)),
                "annotation_row_count": int(pack.loc[pack["candidate_id"].isin(group["candidate_id"])].shape[0]),
                "explicit_evidence_only_candidates": int(group["explicit_evidence_only"].sum()),
                "text_available_candidates": int(group["text_available_for_local_review"].sum()),
                "ai_keyword_match_candidates": int((group["ai_matched_keyword_count"] > 0).sum()),
                "ai_protocol_artifact_candidates": int(
                    (group["ai_suggested_evidence_presence"] == "protocol_artifact").sum()
                ),
                "priority_1_or_2_candidates": int(
                    group["review_priority_band"].isin({"priority_1_immediate", "priority_2_high"}).sum()
                ),
                "candidates_complete_once": int(group["candidate_complete_once"].sum()),
                "candidates_double_complete": int(group["candidate_double_complete"].sum()),
            }
        )
    return pd.DataFrame(rows)


def aggregate_priority_summary(pack: pd.DataFrame) -> pd.DataFrame:
    candidates = pack.drop_duplicates("candidate_id", keep="first").copy()
    rows: list[dict[str, Any]] = []
    for key, group in candidates.groupby(["review_priority_band", "dataset"], sort=True, dropna=False):
        band, dataset = key
        rows.append(
            {
                "review_priority_band": band,
                "dataset": dataset,
                "candidate_count": int(len(group)),
                "mean_abs_error": round(float(group["abs_error"].mean()), 4),
                "explicit_evidence_only_candidates": int(group["explicit_evidence_only"].sum()),
                "ai_keyword_match_candidates": int((group["ai_matched_keyword_count"] > 0).sum()),
                "ai_protocol_artifact_candidates": int(
                    (group["ai_suggested_evidence_presence"] == "protocol_artifact").sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def aggregate_human_review_progress(pack: pd.DataFrame) -> pd.DataFrame:
    candidates = pack.drop_duplicates("candidate_id", keep="first").copy()
    completed_rows = int(pack["human_annotation_complete"].sum())
    completed_candidates = int(candidates["candidate_complete_once"].sum())
    double_candidates = int(candidates["candidate_double_complete"].sum())
    return pd.DataFrame(
        [
            {
                "candidate_count": int(pack["candidate_id"].nunique()),
                "annotation_row_count": int(len(pack)),
                "complete_annotation_rows": completed_rows,
                "candidates_with_any_complete_annotation": completed_candidates,
                "candidates_with_two_or_more_complete_annotators": double_candidates,
                "remaining_candidates_before_default_completed_gate": max(0, 30 - completed_candidates),
                "remaining_candidates_before_default_double_gate": max(0, 20 - double_candidates),
                "review_pack_claim_status": "not_claimable_until_human_workbench_summary_gate_passes",
            }
        ]
    )


def review_pack_schema(pack: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    sensitive_prefixes = ("local_", "ai_local_", "text_segments_", "local_text_")
    for column in pack.columns:
        if column in ANNOTATION_FIELDS or column in {"annotator_id", "local_notes", "local_excerpt"}:
            purpose = "human_annotation_field"
        elif column.startswith("ai_suggested_") or column.startswith("ai_"):
            purpose = "ai_suggestion_for_human_review"
        elif column.startswith("review_priority_") or column == "review_rank":
            purpose = "review_prioritization"
        elif column.startswith(sensitive_prefixes) or column in {"subject_id"}:
            purpose = "local_subject_level_review_context"
        else:
            purpose = "candidate_metadata_or_model_context"
        rows.append(
            {
                "column": column,
                "purpose": purpose,
                "tracked_release_policy": "schema_only_no_row_values",
                "local_pack_policy": "ignored_local_only",
            }
        )
    return pd.DataFrame(rows)


def local_artifact_manifest(pack: pd.DataFrame, candidate_index: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "artifact": LOCAL_REVIEW_PACK,
                "row_count": int(len(pack)),
                "candidate_count": int(pack["candidate_id"].nunique()),
                "contains_subject_level_rows": True,
                "may_contain_local_text_locators_or_excerpts": True,
                "git_policy": "ignored_local_only",
            },
            {
                "artifact": LOCAL_CANDIDATE_INDEX,
                "row_count": int(len(candidate_index)),
                "candidate_count": int(candidate_index["candidate_id"].nunique()),
                "contains_subject_level_rows": True,
                "may_contain_local_text_locators_or_excerpts": True,
                "git_policy": "ignored_local_only",
            },
        ]
    )


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    banned_patterns = [
        re.compile(r"/root/"),
        re.compile(r"/autodl-tmp/datasets/"),
        re.compile(r"datasets/(CMDC|EATD-Corpus|MODMA|MPDD|PDCH|edaic)/"),
        re.compile(r"\b(raw_text|raw_response|api_key|password|passwd|secret|token)\b", re.IGNORECASE),
    ]
    violations: list[dict[str, Any]] = []
    for filename in TRACKED_FILES:
        path = out_dir / filename
        if not path.exists():
            if filename == "artifact_hygiene_audit.json":
                continue
            violations.append({"file": filename, "pattern": "missing_tracked_file"})
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in banned_patterns:
            if pattern.search(text):
                violations.append({"file": filename, "pattern": pattern.pattern})
    audit = {
        "audit_id": "P5_MV06_human_review_pack_hygiene",
        "generated_at": utc_now(),
        "tracked_files_checked": TRACKED_FILES,
        "local_only_files_skipped": [LOCAL_REVIEW_PACK, LOCAL_CANDIDATE_INDEX],
        "artifact_hygiene_passed": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
    }
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    review_summary: pd.DataFrame,
    priority_summary: pd.DataFrame,
    progress_summary: pd.DataFrame,
) -> None:
    progress = progress_summary.iloc[0].to_dict()
    lines = [
        "# P5_MV06 Human Review Pack",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "This helper joins the local human annotation workbench with the local AI triage workbook. It is a review accelerator only; AI suggestions are not human annotation or agreement evidence.",
        "",
        "## Summary",
        "",
        f"- Review pack status: `{run_summary['decision']['review_pack_status']}`.",
        f"- Candidate count: `{run_summary['review_pack_summary']['candidate_count']}`.",
        f"- Annotation rows: `{run_summary['review_pack_summary']['annotation_row_count']}`.",
        f"- AI keyword-match candidates: `{run_summary['review_pack_summary']['ai_keyword_match_candidates']}`.",
        f"- Completed human candidates currently visible in source workbook: `{progress['candidates_with_any_complete_annotation']}`.",
        f"- Double-completed human candidates currently visible in source workbook: `{progress['candidates_with_two_or_more_complete_annotators']}`.",
        f"- Artifact hygiene passed: `{run_summary.get('artifact_hygiene_passed', 'pending')}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Aggregate Review Summary",
        "",
        "| dataset | target family | bucket | candidates | priority 1/2 | AI keyword | AI protocol artifact | complete once | double complete |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in review_summary.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['target_family']} | {row['candidate_bucket']} | "
            f"{int(row['candidate_count'])} | {int(row['priority_1_or_2_candidates'])} | "
            f"{int(row['ai_keyword_match_candidates'])} | {int(row['ai_protocol_artifact_candidates'])} | "
            f"{int(row['candidates_complete_once'])} | {int(row['candidates_double_complete'])} |"
        )
    lines.extend(
        [
            "",
            "## Priority Bands",
            "",
            "| priority band | dataset | candidates | mean abs error | AI keyword |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in priority_summary.iterrows():
        lines.append(
            f"| {row['review_priority_band']} | {row['dataset']} | {int(row['candidate_count'])} | "
            f"{row['mean_abs_error']:.4f} | {int(row['ai_keyword_match_candidates'])} |"
        )
    lines.extend(
        [
            "",
            "## Use Policy",
            "",
            "- Fill or correct human decisions in the original ignored workbench before running the summary gate.",
            "- Do not copy AI suggestion fields into evidence fields without human verification.",
            "- Commit only aggregate summaries; keep the local pack, candidate index, snippets, and source locators out of Git.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(
    out_dir: Path,
    workbook_path: Path,
    ai_path: Path,
    pack: pd.DataFrame,
    candidate_index: pd.DataFrame,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    review_summary = aggregate_review_pack_summary(pack)
    priority_summary = aggregate_priority_summary(pack)
    progress_summary = aggregate_human_review_progress(pack)
    schema = review_pack_schema(pack)
    manifest = local_artifact_manifest(pack, candidate_index)

    pack.to_csv(out_dir / LOCAL_REVIEW_PACK, index=False)
    candidate_index.to_csv(out_dir / LOCAL_CANDIDATE_INDEX, index=False)
    review_summary.to_csv(out_dir / "aggregate_review_pack_summary.csv", index=False)
    priority_summary.to_csv(out_dir / "aggregate_priority_summary.csv", index=False)
    progress_summary.to_csv(out_dir / "aggregate_human_review_progress_summary.csv", index=False)
    schema.to_csv(out_dir / "review_pack_schema.csv", index=False)
    manifest.to_csv(out_dir / "local_artifact_manifest.csv", index=False)

    candidates = pack.drop_duplicates("candidate_id", keep="first")
    run_summary = {
        "run_id": "P5_MV06_human_review_pack",
        "generated_at": utc_now(),
        "status": "complete",
        "scope": "local_human_review_pack_not_annotation_result",
        "inputs": {
            "human_workbook": rel(workbook_path),
            "ai_preannotation": rel(ai_path),
        },
        "outputs": {
            "out_dir": rel(out_dir),
            "tracked_files": TRACKED_FILES,
            "local_only_files": [LOCAL_REVIEW_PACK, LOCAL_CANDIDATE_INDEX],
        },
        "review_pack_summary": {
            "candidate_count": int(pack["candidate_id"].nunique()),
            "annotation_row_count": int(len(pack)),
            "candidate_index_rows": int(len(candidate_index)),
            "ai_keyword_match_candidates": int((candidates["ai_matched_keyword_count"] > 0).sum()),
            "ai_protocol_artifact_candidates": int(
                (candidates["ai_suggested_evidence_presence"] == "protocol_artifact").sum()
            ),
            "priority_1_or_2_candidates": int(
                candidates["review_priority_band"].isin({"priority_1_immediate", "priority_2_high"}).sum()
            ),
            "completed_human_candidates_in_source_workbook": int(candidates["candidate_complete_once"].sum()),
            "double_completed_human_candidates_in_source_workbook": int(candidates["candidate_double_complete"].sum()),
        },
        "decision": {
            "review_pack_status": "ready_for_human_review_pack_not_claimable",
            "short_read": (
                "A local review pack now combines AI suggestions, human annotation fields, and priority ranks. "
                "It can speed manual review but does not satisfy MV06 annotation, agreement, or RQ4 evidence gates."
            ),
        },
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, review_summary, priority_summary, progress_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    run_summary["artifact_hygiene_violation_count"] = int(hygiene["violation_count"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, review_summary, priority_summary, progress_summary)
    return run_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--ai-preannotation", type=Path, default=DEFAULT_AI_PREANNOTATION)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing local review pack.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    local_paths = [args.out_dir / LOCAL_REVIEW_PACK, args.out_dir / LOCAL_CANDIDATE_INDEX]
    if not args.overwrite:
        for path in local_paths:
            if path.exists():
                raise FileExistsError(f"{path} exists. Use --overwrite only after preserving any local review edits.")
    workbook = load_workbook(args.workbook)
    ai = load_ai_preannotation(args.ai_preannotation)
    pack, candidate_index = build_review_pack(workbook, ai)
    run_summary = write_outputs(args.out_dir, args.workbook, args.ai_preannotation, pack, candidate_index)
    print(
        "Wrote MV06 human review pack to "
        f"{rel(args.out_dir)}: {run_summary['decision']['review_pack_status']}"
    )


if __name__ == "__main__":
    main()
