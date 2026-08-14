#!/usr/bin/env python3
"""Summarize local-only P5_MV06 evidence annotations into safe aggregates.

The input annotation packet is intentionally ignored by Git because it contains
subject-level candidate rows. This script reads that local packet, validates the
annotation fields, and writes only aggregate completion, evidence, prompt
artifact, and agreement summaries. It does not read raw clinical text, source
locator maps, or local snippets.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET = (
    ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv06_evidence_annotation_workbench"
    / "p5_mv06_local_annotation_workbook_predictions.csv"
)
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv06_evidence_annotation_summary"
DEFAULT_BOOTSTRAP_RESAMPLES = 2000
DEFAULT_BOOTSTRAP_SEED = 20260814

REQUIRED_PACKET_COLUMNS = {
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
    "abs_error",
    "text_available_for_local_review",
    "explicit_evidence_only",
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
    "annotator_id",
}

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

TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "annotation_completion_summary.csv",
    "annotation_value_issues.csv",
    "aggregate_evidence_presence_summary.csv",
    "aggregate_evidence_source_summary.csv",
    "aggregate_prompt_artifact_summary.csv",
    "agreement_summary.csv",
    "agreement_uncertainty_summary.csv",
    "field_contract.csv",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "null", "<na>"}:
        return ""
    return text


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


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {', '.join(sorted(missing))}")


def load_packet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist. Run scripts/phase5_prepare_mv06_annotation_workbench.py first."
        )
    frame = pd.read_csv(path)
    require_columns(frame, REQUIRED_PACKET_COLUMNS, "MV06 annotation packet")
    for column in [
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
        "annotator_id",
    ]:
        frame[column] = frame[column].map(clean_value)
    for field in ANNOTATION_FIELDS:
        frame[field] = frame[field].map(lambda value, field=field: normalize_field_value(field, value))
    frame["abs_error"] = pd.to_numeric(frame["abs_error"], errors="coerce")
    frame["text_available_for_local_review"] = frame["text_available_for_local_review"].astype(str).str.lower().isin(
        {"true", "1", "yes", "y"}
    )
    frame["explicit_evidence_only"] = frame["explicit_evidence_only"].astype(str).str.lower().isin(
        {"true", "1", "yes", "y"}
    )
    return frame


def validate_annotations(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    annotated = frame.copy()
    required = ANNOTATION_FIELDS + ["annotator_id"]
    for column in required:
        annotated[f"{column}_valid"] = annotated[column].map(bool)

    for field in ANNOTATION_FIELDS:
        allowed = ALLOWED_VALUES[field]
        present = annotated[field].map(bool)
        valid = annotated[field].isin(allowed)
        annotated[f"{field}_valid"] = present & valid
        bad_values = sorted(set(annotated.loc[present & ~valid, field].tolist()))
        if bad_values:
            rows.append(
                {
                    "issue_type": "invalid_value",
                    "field": field,
                    "row_count": int((present & ~valid).sum()),
                    "values": ";".join(bad_values),
                    "release_policy": "fix_local_packet_before_claiming_evidence",
                }
            )
        missing_count = int((~present).sum())
        if missing_count:
            rows.append(
                {
                    "issue_type": "missing_value",
                    "field": field,
                    "row_count": missing_count,
                    "values": "",
                    "release_policy": "not_claimable_until_completed",
                }
            )

    missing_annotator = int((~annotated["annotator_id"].map(bool)).sum())
    if missing_annotator:
        rows.append(
            {
                "issue_type": "missing_value",
                "field": "annotator_id",
                "row_count": missing_annotator,
                "values": "",
                "release_policy": "required_for_agreement_audit",
            }
        )
    annotated["annotation_complete"] = annotated[[f"{field}_valid" for field in ANNOTATION_FIELDS]].all(axis=1) & annotated[
        "annotator_id"
    ].map(bool)
    annotated["candidate_complete_once"] = annotated.groupby("candidate_id")["annotation_complete"].transform("any")
    annotated["complete_annotator_count"] = annotated.groupby("candidate_id")["annotator_id"].transform(
        lambda values: len(set(value for value in values if value))
    )
    issues = pd.DataFrame(rows)
    if issues.empty:
        issues = pd.DataFrame(columns=["issue_type", "field", "row_count", "values", "release_policy"])
    return annotated, issues


def completion_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(["dataset", "target_family", "candidate_bucket"], sort=True, dropna=False):
        dataset, target_family, candidate_bucket = key
        candidate_groups = group.groupby("candidate_id")
        completed_candidates = int(candidate_groups["annotation_complete"].any().sum())
        double_completed = int(
            candidate_groups.apply(
                lambda rows: rows.loc[rows["annotation_complete"], "annotator_id"].nunique() >= 2,
                include_groups=False,
            ).sum()
        )
        rows.append(
            {
                "dataset": dataset,
                "target_family": target_family,
                "candidate_bucket": candidate_bucket,
                "candidate_count": int(group["candidate_id"].nunique()),
                "annotation_row_count": int(len(group)),
                "complete_annotation_rows": int(group["annotation_complete"].sum()),
                "candidates_with_any_complete_annotation": completed_candidates,
                "candidates_with_two_or_more_complete_annotators": double_completed,
                "explicit_evidence_only_candidates": int(
                    group.loc[group["explicit_evidence_only"], "candidate_id"].nunique()
                ),
            }
        )
    return pd.DataFrame(rows)


def aggregate_counts(frame: pd.DataFrame, field: str) -> pd.DataFrame:
    complete = frame[frame["annotation_complete"]].copy()
    columns = ["dataset", "target_family", "target_id", "candidate_bucket", field]
    if complete.empty:
        return pd.DataFrame(
            columns=columns
            + [
                "complete_annotation_rows",
                "candidate_count",
                "annotator_count",
                "mean_abs_error",
            ]
        )
    rows: list[dict[str, Any]] = []
    for key, group in complete.groupby(columns, sort=True, dropna=False):
        row = dict(zip(columns, key if isinstance(key, tuple) else (key,)))
        row.update(
            {
                "complete_annotation_rows": int(len(group)),
                "candidate_count": int(group["candidate_id"].nunique()),
                "annotator_count": int(group["annotator_id"].nunique()),
                "mean_abs_error": safe_float(group["abs_error"].mean()),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def kappa_from_pairs(pairs: list[tuple[str, str]]) -> tuple[float | None, float | None, float | None, str]:
    if not pairs:
        return None, None, None, "insufficient_pair_annotations"
    observed = sum(1 for left, right in pairs if left == right) / len(pairs)
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    values = sorted(set(left_counts) | set(right_counts))
    expected = sum((left_counts[value] / len(pairs)) * (right_counts[value] / len(pairs)) for value in values)
    if expected >= 1:
        return safe_float(observed), safe_float(expected), None, "undefined_degenerate_marginals"
    kappa = (observed - expected) / (1 - expected)
    return safe_float(observed), safe_float(expected), safe_float(kappa), "computed_pairwise_kappa"


def pair_values_for_field(complete: pd.DataFrame, field: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for _, group in complete.groupby("candidate_id", sort=True):
        per_annotator = group.drop_duplicates(["annotator_id"], keep="first")
        values = per_annotator[["annotator_id", field]].dropna().values.tolist()
        for left, right in itertools.combinations(values, 2):
            pairs.append((str(left[1]), str(right[1])))
    return pairs


def pairwise_agreement_for_scope(dataset: str, complete: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in ANNOTATION_FIELDS:
        pairs = pair_values_for_field(complete, field)
        observed, expected, kappa, status = kappa_from_pairs(pairs)
        rows.append(
            {
                "dataset": dataset,
                "field": field,
                "pair_count": int(len(pairs)),
                "observed_agreement": observed,
                "expected_agreement": expected,
                "pairwise_kappa": kappa,
                "agreement_status": status,
            }
        )
    return rows


def pairwise_agreement(frame: pd.DataFrame) -> pd.DataFrame:
    complete = frame[frame["annotation_complete"]].copy()
    rows: list[dict[str, Any]] = []
    rows.extend(pairwise_agreement_for_scope("ALL", complete))
    for dataset in sorted(frame["dataset"].dropna().unique()):
        rows.extend(pairwise_agreement_for_scope(str(dataset), complete[complete["dataset"] == dataset]))
    return pd.DataFrame(rows)


def percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    if not 0 <= probability <= 1:
        raise ValueError("percentile probability must be between 0 and 1")
    ordered = sorted(values)
    if len(ordered) == 1:
        return safe_float(ordered[0])
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return safe_float(ordered[lower])
    weight = position - lower
    return safe_float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def percentile_ci(values: list[float]) -> tuple[float | None, float | None]:
    return percentile(values, 0.025), percentile(values, 0.975)


def agreement_uncertainty_for_scope(
    dataset: str,
    complete: pd.DataFrame,
    bootstrap_resamples: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in ANNOTATION_FIELDS:
        pairs = pair_values_for_field(complete, field)
        observed, _, kappa, kappa_status = kappa_from_pairs(pairs)
        agreement_samples: list[float] = []
        kappa_samples: list[float] = []
        undefined_kappa_resamples = 0
        if pairs:
            for _ in range(bootstrap_resamples):
                sample = [pairs[rng.randrange(len(pairs))] for _ in range(len(pairs))]
                sample_observed, _, sample_kappa, _ = kappa_from_pairs(sample)
                if sample_observed is None:
                    raise ValueError("bootstrap sample unexpectedly has no pairs")
                agreement_samples.append(sample_observed)
                if sample_kappa is None:
                    undefined_kappa_resamples += 1
                else:
                    kappa_samples.append(sample_kappa)
        agreement_low, agreement_high = percentile_ci(agreement_samples)
        kappa_low, kappa_high = percentile_ci(kappa_samples)
        if not pairs:
            uncertainty_status = "insufficient_pair_annotations"
        elif not kappa_samples:
            uncertainty_status = "undefined_bootstrap_kappa_degenerate_marginals"
        elif undefined_kappa_resamples:
            uncertainty_status = "computed_bootstrap_ci_with_degenerate_resamples"
        else:
            uncertainty_status = "computed_bootstrap_ci"
        rows.append(
            {
                "dataset": dataset,
                "field": field,
                "pair_count": int(len(pairs)),
                "observed_agreement": observed,
                "agreement_ci95_low": agreement_low,
                "agreement_ci95_high": agreement_high,
                "observed_kappa": kappa,
                "observed_kappa_status": kappa_status,
                "kappa_ci95_low": kappa_low,
                "kappa_ci95_high": kappa_high,
                "bootstrap_resamples_requested": bootstrap_resamples,
                "bootstrap_resamples_effective_for_kappa": int(len(kappa_samples)),
                "undefined_kappa_resamples": int(undefined_kappa_resamples),
                "bootstrap_unit": "double_annotated_candidate_pair",
                "ci_method": "nonparametric_percentile_bootstrap",
                "uncertainty_status": uncertainty_status,
            }
        )
    return rows


def agreement_uncertainty(
    frame: pd.DataFrame,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> pd.DataFrame:
    complete = frame[frame["annotation_complete"]].copy()
    rows: list[dict[str, Any]] = []
    rng = random.Random(bootstrap_seed)
    rows.extend(agreement_uncertainty_for_scope("ALL", complete, bootstrap_resamples, rng))
    for dataset in sorted(frame["dataset"].dropna().unique()):
        rows.extend(
            agreement_uncertainty_for_scope(
                str(dataset),
                complete[complete["dataset"] == dataset],
                bootstrap_resamples,
                rng,
            )
        )
    return pd.DataFrame(rows)


def field_contract() -> pd.DataFrame:
    rows = []
    for field in ANNOTATION_FIELDS:
        rows.append(
            {
                "field": field,
                "allowed_values": ";".join(sorted(ALLOWED_VALUES[field])),
                "required_for_claim": True,
                "tracked_release_policy": "aggregate_counts_only",
            }
        )
    rows.append(
        {
            "field": "annotator_id",
            "allowed_values": "local_stable_annotator_code",
            "required_for_claim": True,
            "tracked_release_policy": "counts_only_no_personal_identity",
        }
    )
    rows.append(
        {
            "field": "private_free_text_fields",
            "allowed_values": "free_text",
            "required_for_claim": False,
            "tracked_release_policy": "local_only_never_git_by_default",
        }
    )
    return pd.DataFrame(rows)


def determine_status(
    frame: pd.DataFrame,
    issues: pd.DataFrame,
    min_completed_candidates: int,
    min_double_annotated_candidates: int,
) -> tuple[str, str]:
    completed_candidates = int(frame.groupby("candidate_id")["annotation_complete"].any().sum())
    double_candidates = int(
        frame.groupby("candidate_id").apply(
            lambda rows: rows.loc[rows["annotation_complete"], "annotator_id"].nunique() >= 2,
            include_groups=False,
        ).sum()
    )
    invalid_rows = int(issues.loc[issues["issue_type"] == "invalid_value", "row_count"].sum()) if not issues.empty else 0
    if invalid_rows:
        return "blocked_invalid_annotation_values", "Fix invalid local annotation values before exporting any aggregate evidence result."
    if completed_candidates == 0:
        return "blocked_no_completed_annotations", "The local annotation workbook has not been filled yet; only completion and field-contract gates are meaningful."
    if completed_candidates < min_completed_candidates:
        return (
            "blocked_too_few_completed_annotations",
            f"Only {completed_candidates} candidates are complete; require at least {min_completed_candidates} before RQ4 evidence reporting.",
        )
    if double_candidates < min_double_annotated_candidates:
        return (
            "blocked_too_few_double_annotations",
            f"Only {double_candidates} candidates have two complete annotators; require at least {min_double_annotated_candidates} for agreement reporting.",
        )
    return (
        "ready_for_aggregate_evidence_review",
        "Aggregate annotation counts and pairwise agreement are ready for human review; raw snippets and subject-level rows remain local-only.",
    )


def write_outputs(
    frame: pd.DataFrame,
    issues: pd.DataFrame,
    out_dir: Path,
    min_completed_candidates: int,
    min_double_annotated_candidates: int,
    bootstrap_resamples: int,
    bootstrap_seed: int,
    generated_at: str,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    completion = completion_summary(frame)
    evidence_presence = aggregate_counts(frame, "evidence_presence")
    evidence_source = aggregate_counts(frame, "evidence_source")
    prompt_artifact = aggregate_counts(frame, "prompt_artifact")
    agreement = pairwise_agreement(frame)
    uncertainty = agreement_uncertainty(
        frame,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
    )
    contract = field_contract()

    completion.to_csv(out_dir / "annotation_completion_summary.csv", index=False)
    issues.to_csv(out_dir / "annotation_value_issues.csv", index=False)
    evidence_presence.to_csv(out_dir / "aggregate_evidence_presence_summary.csv", index=False)
    evidence_source.to_csv(out_dir / "aggregate_evidence_source_summary.csv", index=False)
    prompt_artifact.to_csv(out_dir / "aggregate_prompt_artifact_summary.csv", index=False)
    agreement.to_csv(out_dir / "agreement_summary.csv", index=False)
    uncertainty.to_csv(out_dir / "agreement_uncertainty_summary.csv", index=False)
    contract.to_csv(out_dir / "field_contract.csv", index=False)
    stale_hygiene = out_dir / "artifact_hygiene_audit.json"
    if stale_hygiene.exists():
        stale_hygiene.unlink()

    status, short_read = determine_status(
        frame,
        issues,
        min_completed_candidates=min_completed_candidates,
        min_double_annotated_candidates=min_double_annotated_candidates,
    )
    completed_candidates = int(frame.groupby("candidate_id")["annotation_complete"].any().sum())
    double_candidates = int(
        frame.groupby("candidate_id").apply(
            lambda rows: rows.loc[rows["annotation_complete"], "annotator_id"].nunique() >= 2,
            include_groups=False,
        ).sum()
    )
    evidence_presence_uncertainty = uncertainty[uncertainty["field"] == "evidence_presence"].copy()
    run_summary = {
        "run_id": "P5_MV06_evidence_annotation_summary",
        "generated_at": generated_at,
        "status": "complete",
        "decision": {
            "annotation_summary_status": status,
            "short_read": short_read,
        },
        "input_contract": {
            "raw_text_read": False,
            "source_locator_map_read": False,
            "local_annotation_packet_rows": int(len(frame)),
            "candidate_count": int(frame["candidate_id"].nunique()),
        },
        "annotation_gate": {
            "completed_candidates": completed_candidates,
            "double_annotated_candidates": double_candidates,
            "min_completed_candidates": min_completed_candidates,
            "min_double_annotated_candidates": min_double_annotated_candidates,
            "invalid_value_issue_rows": int(issues.loc[issues["issue_type"] == "invalid_value", "row_count"].sum())
            if not issues.empty
            else 0,
        },
        "agreement_uncertainty": {
            "bootstrap_resamples_requested": bootstrap_resamples,
            "bootstrap_seed": bootstrap_seed,
            "ci_method": "nonparametric_percentile_bootstrap",
            "bootstrap_unit": "double_annotated_candidate_pair",
            "evidence_presence": evidence_presence_uncertainty.to_dict(orient="records"),
        },
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "raw_text_written": False,
            "source_paths_written": False,
            "subject_level_rows_written": False,
            "aggregate_only": True,
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, completion, issues, agreement, uncertainty)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, completion, issues, agreement, uncertainty)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    completion: pd.DataFrame,
    issues: pd.DataFrame,
    agreement: pd.DataFrame,
    uncertainty: pd.DataFrame,
) -> None:
    lines = [
        "# P5_MV06 Evidence Annotation Summary Gate",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This gate validates the local MV06 annotation packet and exports only aggregate annotation completion, evidence-field, prompt-artifact, agreement, and agreement-uncertainty summaries. It does not read raw clinical text, local source locators, or raw snippets.",
        "",
        "## Decision",
        "",
        f"- Annotation summary status: `{run_summary['decision']['annotation_summary_status']}`.",
        f"- Completed candidates: `{run_summary['annotation_gate']['completed_candidates']}`.",
        f"- Double-annotated candidates: `{run_summary['annotation_gate']['double_annotated_candidates']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Completion By Dataset",
        "",
        "| dataset | target family | bucket | candidates | complete rows | candidates complete | candidates double-complete |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in completion.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['target_family']} | {row['candidate_bucket']} | "
            f"{row['candidate_count']} | {row['complete_annotation_rows']} | "
            f"{row['candidates_with_any_complete_annotation']} | "
            f"{row['candidates_with_two_or_more_complete_annotators']} |"
        )
    lines.extend(
        [
            "",
            "## Field Issues",
            "",
            "| issue type | field | rows | release policy |",
            "| --- | --- | ---: | --- |",
        ]
    )
    if issues.empty:
        lines.append("| none | none | 0 | none |")
    else:
        for _, row in issues.iterrows():
            lines.append(f"| {row['issue_type']} | {row['field']} | {row['row_count']} | {row['release_policy']} |")
    lines.extend(
        [
            "",
            "## Agreement",
            "",
            "| dataset | field | pair count | observed agreement | pairwise kappa | status |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in agreement.iterrows():
        observed = "" if pd.isna(row["observed_agreement"]) else f"{row['observed_agreement']:.3f}"
        kappa = "" if pd.isna(row["pairwise_kappa"]) else f"{row['pairwise_kappa']:.3f}"
        lines.append(
            f"| {row['dataset']} | {row['field']} | {row['pair_count']} | "
            f"{observed} | {kappa} | {row['agreement_status']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence-Presence Agreement Uncertainty",
            "",
            "| dataset | pairs | observed agreement 95 percent CI | kappa 95 percent CI | effective kappa resamples | status |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    evidence_presence_uncertainty = uncertainty[uncertainty["field"] == "evidence_presence"].copy()
    for _, row in evidence_presence_uncertainty.iterrows():
        agreement_low = "" if pd.isna(row["agreement_ci95_low"]) else f"{row['agreement_ci95_low']:.3f}"
        agreement_high = "" if pd.isna(row["agreement_ci95_high"]) else f"{row['agreement_ci95_high']:.3f}"
        kappa_low = "" if pd.isna(row["kappa_ci95_low"]) else f"{row['kappa_ci95_low']:.3f}"
        kappa_high = "" if pd.isna(row["kappa_ci95_high"]) else f"{row['kappa_ci95_high']:.3f}"
        lines.append(
            f"| {row['dataset']} | {row['pair_count']} | {agreement_low}-{agreement_high} | "
            f"{kappa_low}-{kappa_high} | {row['bootstrap_resamples_effective_for_kappa']} | "
            f"{row['uncertainty_status']} |"
        )
    lines.extend(
        [
            "",
            "## Release Rule",
            "",
            "- Do not claim RQ4 evidence-localization validity while status is blocked.",
            "- Commit only aggregate outputs from this directory.",
            "- Keep local snippets, local notes, local source locators, and subject-level candidate rows out of Git.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_text_locators_json",
        r"local_excerpt",
        r"local_notes",
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
        "audit_id": "P5_MV06_evidence_annotation_summary_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotation-packet", type=Path, default=DEFAULT_PACKET)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--min-completed-candidates", type=int, default=30)
    parser.add_argument("--min-double-annotated-candidates", type=int, default=20)
    parser.add_argument("--bootstrap-resamples", type=int, default=DEFAULT_BOOTSTRAP_RESAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    args = parser.parse_args()

    if args.min_completed_candidates < 1 or args.min_double_annotated_candidates < 1:
        raise ValueError("minimum annotation thresholds must be positive")
    if args.bootstrap_resamples < 1:
        raise ValueError("bootstrap resamples must be positive")
    generated_at = utc_now()
    packet = load_packet(args.annotation_packet)
    annotated, issues = validate_annotations(packet)
    run_summary = write_outputs(
        annotated,
        issues,
        args.out_dir,
        min_completed_candidates=args.min_completed_candidates,
        min_double_annotated_candidates=args.min_double_annotated_candidates,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
        generated_at=generated_at,
    )
    print(
        "Wrote MV06 evidence annotation summary gate to "
        f"{display_path(args.out_dir)} with status "
        f"{run_summary['decision']['annotation_summary_status']}"
    )


if __name__ == "__main__":
    main()
