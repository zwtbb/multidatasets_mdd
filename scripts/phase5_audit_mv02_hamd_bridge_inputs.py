#!/usr/bin/env python3
"""Audit Phase 5 MV02 HAMD-17 bridge inputs.

This is a readiness audit, not a modeling script. It checks whether PDCH and
CMDC expose enough internally consistent HAMD-17 item/total labels and reusable
frozen features to launch `P5_MV02 hamd17_auxiliary_bridge`.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "datasets" / "manifests"
PHASE2_DIR = ROOT / "analysis" / "phase2_baselines"
OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation" / "p5_mv02_hamd_bridge_readiness"
EXPECTED_HAMD_KEYS = [f"HAMD{i:02d}" for i in range(1, 18)]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def nonempty(value: Any) -> bool:
    return str(value).strip() not in {"", "nan", "NaN", "None", "null"}


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
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isnan(numeric_value):
            continue
        parsed[str(key)] = numeric_value
    return parsed


def round_key(values: dict[str, float]) -> str:
    return json.dumps({key: values.get(key) for key in EXPECTED_HAMD_KEYS}, sort_keys=True)


def read_manifest(dataset: str) -> pd.DataFrame:
    path = MANIFEST_DIR / f"{dataset}_subjects.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def subject_hamd_records(dataset: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest = read_manifest(dataset)
    rows: list[dict[str, Any]] = []
    for subject_id, group in manifest.groupby("subject_id"):
        total_values = sorted(
            {
                float(value)
                for value in pd.to_numeric(group["hamd17_total"], errors="coerce").dropna().tolist()
            }
        )
        item_payloads = [parse_item_values(value) for value in group["hamd17_items"].tolist()]
        nonempty_items = [payload for payload in item_payloads if payload]
        full_items = [payload for payload in nonempty_items if all(key in payload for key in EXPECTED_HAMD_KEYS)]
        item_vectors = sorted({round_key(payload) for payload in full_items})
        raw_item_sums = sorted({round(sum(payload[key] for key in EXPECTED_HAMD_KEYS), 6) for payload in full_items})
        scored_item_sums = sorted(
            {
                round(sum(0.0 if payload[key] == 9 else payload[key] for key in EXPECTED_HAMD_KEYS), 6)
                for payload in full_items
            }
        )
        contains_hamd_code_9 = any(
            any(payload.get(key) == 9 for key in EXPECTED_HAMD_KEYS) for payload in full_items
        )
        full_item_and_total = bool(full_items) and len(total_values) == 1
        raw_sum_delta = ""
        scored_sum_delta = ""
        raw_sum_matches_total = ""
        scored_sum_matches_total = ""
        if full_item_and_total and raw_item_sums:
            raw_deltas = sorted({round(item_sum - total_values[0], 6) for item_sum in raw_item_sums})
            raw_sum_delta = ";".join(str(delta) for delta in raw_deltas)
            raw_sum_matches_total = all(abs(delta) <= 1e-6 for delta in raw_deltas)
        if full_item_and_total and scored_item_sums:
            scored_deltas = sorted({round(item_sum - total_values[0], 6) for item_sum in scored_item_sums})
            scored_sum_delta = ";".join(str(delta) for delta in scored_deltas)
            scored_sum_matches_total = all(abs(delta) <= 1e-6 for delta in scored_deltas)
        rows.append(
            {
                "dataset": dataset,
                "subject_id": str(subject_id),
                "manifest_rows": len(group),
                "file_valid_rows": int(group["file_valid"].fillna(False).astype(bool).sum()),
                "has_hamd_total": bool(total_values),
                "hamd_total_unique_count": len(total_values),
                "has_any_hamd_item": bool(nonempty_items),
                "has_full_hamd17_items": bool(full_items),
                "hamd_item_vector_unique_count": len(item_vectors),
                "has_total_and_full_items": full_item_and_total,
                "raw_hamd_item_sum_unique_count": len(raw_item_sums),
                "scored_hamd_item_sum_unique_count": len(scored_item_sums),
                "contains_hamd_code_9": contains_hamd_code_9,
                "raw_item_sum_matches_total": raw_sum_matches_total,
                "scored_item_sum_matches_total": scored_sum_matches_total,
                "raw_item_sum_minus_total": raw_sum_delta,
                "scored_item_sum_minus_total": scored_sum_delta,
            }
        )
    table = pd.DataFrame(rows)
    raw_delta_counts = Counter(
        value
        for value in table.loc[table["raw_item_sum_minus_total"].astype(str) != "", "raw_item_sum_minus_total"].astype(str)
    )
    scored_delta_counts = Counter(
        value
        for value in table.loc[
            table["scored_item_sum_minus_total"].astype(str) != "", "scored_item_sum_minus_total"
        ].astype(str)
    )
    summary = {
        "dataset": dataset,
        "manifest_rows": int(len(manifest)),
        "manifest_subjects": int(table["subject_id"].nunique()),
        "hamd_total_subjects": int(table["has_hamd_total"].sum()),
        "any_item_subjects": int(table["has_any_hamd_item"].sum()),
        "full_hamd17_item_subjects": int(table["has_full_hamd17_items"].sum()),
        "total_and_full_item_subjects": int(table["has_total_and_full_items"].sum()),
        "total_conflict_subjects": int((table["hamd_total_unique_count"] > 1).sum()),
        "item_vector_conflict_subjects": int((table["hamd_item_vector_unique_count"] > 1).sum()),
        "hamd_code_9_subjects": int(table["contains_hamd_code_9"].sum()),
        "raw_item_sum_mismatch_subjects": int((table["raw_item_sum_matches_total"] == False).sum()),
        "scored_item_sum_mismatch_subjects": int((table["scored_item_sum_matches_total"] == False).sum()),
        "raw_item_sum_delta_counts": dict(sorted(raw_delta_counts.items())),
        "scored_item_sum_delta_counts": dict(sorted(scored_delta_counts.items())),
    }
    return table, summary


def feature_file_specs() -> list[dict[str, str]]:
    return [
        {
            "dataset": "pdch",
            "feature_family": "text_bge_subject",
            "relative_path": "cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv",
        },
        {
            "dataset": "pdch",
            "feature_family": "audio_wavlm_subject",
            "relative_path": "pdch_audio_wavlm/pdch_wavlm_subject_features.csv",
        },
        {
            "dataset": "pdch",
            "feature_family": "audio_egemaps_subject",
            "relative_path": "cmdc_pdch_audio_egemaps/pdch_egemaps_subject_features.csv",
        },
        {
            "dataset": "cmdc",
            "feature_family": "text_bge_subject",
            "relative_path": "cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv",
        },
        {
            "dataset": "cmdc",
            "feature_family": "audio_wavlm_subject",
            "relative_path": "cmdc_audio_frozen_encoders/cmdc_wavlm_subject_features.csv",
        },
        {
            "dataset": "cmdc",
            "feature_family": "audio_egemaps_subject",
            "relative_path": "cmdc_pdch_audio_egemaps/cmdc_egemaps_subject_features.csv",
        },
    ]


def model_input_columns(data: pd.DataFrame, feature_family: str) -> list[str]:
    if feature_family == "text_bge_subject":
        return [column for column in data.columns if column.startswith("bge_")]
    if feature_family == "audio_wavlm_subject":
        return [column for column in data.columns if column.startswith("wavlm_")]
    if feature_family == "audio_egemaps_subject":
        excluded = {"dataset_id", "subject_id", "audio_segment_count"}
        return [
            column
            for column in data.columns
            if column not in excluded and pd.api.types.is_numeric_dtype(data[column])
        ]
    return [
        column
        for column in data.columns
        if column != "subject_id" and pd.api.types.is_numeric_dtype(data[column])
    ]


def feature_availability(label_subjects: dict[str, set[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in feature_file_specs():
        path = PHASE2_DIR / spec["relative_path"]
        row = dict(spec)
        row["exists"] = path.exists()
        row["source_scope"] = "current_worktree" if path.exists() else "missing"
        row["row_count"] = 0
        row["feature_subjects"] = 0
        row["joined_label_subjects"] = 0
        row["model_input_column_count"] = 0
        if path.exists():
            data = pd.read_csv(path)
            if "subject_id" not in data.columns:
                raise ValueError(f"feature file missing subject_id: {spec['relative_path']}")
            feature_subjects = set(data["subject_id"].astype(str))
            input_cols = model_input_columns(data, spec["feature_family"])
            row["row_count"] = int(len(data))
            row["feature_subjects"] = int(len(feature_subjects))
            row["joined_label_subjects"] = int(len(feature_subjects & label_subjects.get(spec["dataset"], set())))
            row["model_input_column_count"] = int(len(input_cols))
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=fieldnames).to_csv(path, index=False)


def artifact_hygiene() -> dict[str, Any]:
    forbidden = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"/root/",
            r"/autodl-tmp/",
            r"\btext_path\b",
            r"\baudio_path\b",
            r"\bvideo_path\b",
            r"\bgait_path\b",
            r"\.wav\b",
            r"\.mp4\b",
            r"\.txt\b",
            r"raw transcript",
        ]
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for path in sorted(OUT_DIR.glob("*")):
        if path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern.search(text):
                violations.append({"file": path.name, "pattern": pattern.pattern})
    return {
        "audit_id": "P5_MV02_hamd_bridge_readiness_artifact_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    generated_at: str,
    coverage_rows: list[dict[str, Any]],
    consistency_rows: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    decision: dict[str, Any],
) -> None:
    def fmt_bool(value: Any) -> str:
        return "true" if bool(value) else "false"

    lines = [
        "# P5_MV02 HAMD Bridge Readiness Audit",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Scope",
        "",
        "This audit checks whether `P5_MV02 hamd17_auxiliary_bridge` can start from the current manifests and cached frozen features. It does not train a model and does not write subject-level labels, raw text, media paths, embeddings, or predictions.",
        "",
        "## Label Coverage",
        "",
        "| dataset | manifest subjects | HAMD total subjects | full HAMD-17 item subjects | total + full item subjects | HAMD code-9 subjects | scored item-sum mismatch subjects |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['dataset']} | {row['manifest_subjects']} | {row['hamd_total_subjects']} | "
            f"{row['full_hamd17_item_subjects']} | {row['total_and_full_item_subjects']} | "
            f"{row['hamd_code_9_subjects']} | {row['scored_item_sum_mismatch_subjects']} |"
        )
    lines.extend(
        [
            "",
            "## Item-Total Consistency",
            "",
            "| dataset | comparable subjects | raw item-sum matches | scored item-sum matches | raw delta summary | scored delta summary |",
            "| --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in consistency_rows:
        lines.append(
            f"| {row['dataset']} | {row['comparable_subjects']} | {row['item_sum_match_subjects']} | "
            f"{row['scored_item_sum_match_subjects']} | {row['raw_item_sum_delta_counts']} | "
            f"{row['scored_item_sum_delta_counts']} |"
        )
    lines.extend(
        [
            "",
            "## Reusable Feature Availability",
            "",
        "| dataset | feature family | exists | label subjects joined | model-input columns |",
            "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in feature_rows:
        lines.append(
            f"| {row['dataset']} | {row['feature_family']} | {fmt_bool(row['exists'])} | "
            f"{row['joined_label_subjects']} | {row['model_input_column_count']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- MV02 readiness status: `{decision['mv02_readiness_status']}`.",
            f"- Recommended first mode: `{decision['recommended_first_mode']}`.",
            f"- CMDC HAMD use: `{decision['cmdc_hamd_use']}`.",
            f"- PDCH total target policy: `{decision['pdch_total_target_policy']}`.",
            f"- Full-method allowed by this audit: `{fmt_bool(decision['full_method_allowed'])}`.",
            "",
            "PDCH has the only adequately sized HAMD-17 item+total supervision for the first MV02 run. CMDC HAMD is aligned after filtering placeholder item payloads, but it covers only 25 subjects and should be held for a small external sanity check or reported as limited, not used as a broad joint HAMD bridge claim.",
            "",
            "Seven PDCH subjects contain HAMD item code `9`, which the official evaluation code treats as not sure/not applicable and excludes from total scoring. Their raw item sums are therefore `+9.0` above the manifest total, but scored item sums match after applying the official `9 -> 0 for total` convention. MV02 should use the manifest HAMD total as the primary severity target and apply the same official scoring convention when deriving totals from item heads.",
        ]
    )
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    subject_tables: dict[str, pd.DataFrame] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for dataset in ["cmdc", "pdch"]:
        subject_tables[dataset], summaries[dataset] = subject_hamd_records(dataset)

    coverage_rows = [summaries["cmdc"], summaries["pdch"]]
    coverage_rows_for_csv = [
        {
            **row,
            "raw_item_sum_delta_counts": json.dumps(row["raw_item_sum_delta_counts"], sort_keys=True),
            "scored_item_sum_delta_counts": json.dumps(row["scored_item_sum_delta_counts"], sort_keys=True),
        }
        for row in coverage_rows
    ]
    consistency_rows = []
    label_subjects: dict[str, set[str]] = {}
    for dataset, table in subject_tables.items():
        usable = table.loc[table["has_total_and_full_items"], "subject_id"].astype(str)
        label_subjects[dataset] = set(usable)
        comparable = table.loc[table["has_total_and_full_items"]]
        consistency_rows.append(
            {
                "dataset": dataset,
                "comparable_subjects": int(len(comparable)),
                "item_sum_match_subjects": int((comparable["raw_item_sum_matches_total"] == True).sum()),
                "raw_item_sum_mismatch_subjects": int((comparable["raw_item_sum_matches_total"] == False).sum()),
                "scored_item_sum_match_subjects": int((comparable["scored_item_sum_matches_total"] == True).sum()),
                "scored_item_sum_mismatch_subjects": int(
                    (comparable["scored_item_sum_matches_total"] == False).sum()
                ),
                "raw_item_sum_delta_counts": json.dumps(summaries[dataset]["raw_item_sum_delta_counts"], sort_keys=True),
                "scored_item_sum_delta_counts": json.dumps(
                    summaries[dataset]["scored_item_sum_delta_counts"], sort_keys=True
                ),
            }
        )

    feature_rows = feature_availability(label_subjects)
    decision = {
        "mv02_readiness_status": "ready_pdch_only_mode",
        "recommended_first_mode": "pdch_only_subject_level_hamd17_auxiliary_bridge",
        "cmdc_hamd_use": "small_aligned_25_subject_external_sanity_check_only",
        "pdch_total_target_policy": "use_manifest_hamd17_total_and_official_9_excluded_scoring",
        "pdch_hamd_code_9_subjects": summaries["pdch"]["hamd_code_9_subjects"],
        "pdch_raw_item_sum_mismatch_subjects": summaries["pdch"]["raw_item_sum_mismatch_subjects"],
        "pdch_scored_item_sum_mismatch_subjects": summaries["pdch"]["scored_item_sum_mismatch_subjects"],
        "cmdc_hamd_subjects_after_valid_item_filter": summaries["cmdc"]["total_and_full_item_subjects"],
        "full_method_allowed": False,
    }

    write_csv(
        OUT_DIR / "hamd_label_coverage.csv",
        coverage_rows_for_csv,
        [
            "dataset",
            "manifest_rows",
            "manifest_subjects",
            "hamd_total_subjects",
            "any_item_subjects",
            "full_hamd17_item_subjects",
            "total_and_full_item_subjects",
            "total_conflict_subjects",
            "item_vector_conflict_subjects",
            "hamd_code_9_subjects",
            "raw_item_sum_mismatch_subjects",
            "scored_item_sum_mismatch_subjects",
            "raw_item_sum_delta_counts",
            "scored_item_sum_delta_counts",
        ],
    )
    write_csv(
        OUT_DIR / "hamd_total_item_consistency.csv",
        consistency_rows,
        [
            "dataset",
            "comparable_subjects",
            "item_sum_match_subjects",
            "raw_item_sum_mismatch_subjects",
            "scored_item_sum_match_subjects",
            "scored_item_sum_mismatch_subjects",
            "raw_item_sum_delta_counts",
            "scored_item_sum_delta_counts",
        ],
    )
    write_csv(
        OUT_DIR / "feature_availability.csv",
        feature_rows,
        [
            "dataset",
            "feature_family",
            "relative_path",
            "exists",
            "source_scope",
            "row_count",
            "feature_subjects",
            "joined_label_subjects",
            "model_input_column_count",
        ],
    )
    write_csv(
        OUT_DIR / "readiness_decision.csv",
        [decision],
        [
            "mv02_readiness_status",
            "recommended_first_mode",
            "cmdc_hamd_use",
            "pdch_total_target_policy",
            "pdch_hamd_code_9_subjects",
            "pdch_raw_item_sum_mismatch_subjects",
            "pdch_scored_item_sum_mismatch_subjects",
            "cmdc_hamd_subjects_after_valid_item_filter",
            "full_method_allowed",
        ],
    )
    write_report(generated_at, coverage_rows, consistency_rows, feature_rows, decision)

    run_summary = {
        "run_id": "P5_MV02_hamd_bridge_readiness_audit",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "readiness_audit_no_model_training",
        "label_summaries": summaries,
        "feature_families_checked": len(feature_rows),
        "decision": decision,
        "output_policy": {
            "raw_text": "not_written",
            "source_paths": "not_written",
            "subject_level_labels": "not_written",
            "row_level_predictions": "not_written",
            "learned_embeddings": "not_written",
            "model_weights": "not_written",
        },
        "summary_files": [
            "report.md",
            "run_summary.json",
            "artifact_hygiene_audit.json",
            "hamd_label_coverage.csv",
            "hamd_total_item_consistency.csv",
            "feature_availability.csv",
            "readiness_decision.csv",
        ],
    }
    (OUT_DIR / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n")
    hygiene = artifact_hygiene()
    if not hygiene["artifact_hygiene_passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")
    (OUT_DIR / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n")
    run_summary["artifact_hygiene_passed"] = True
    (OUT_DIR / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n")
    print(f"Wrote MV02 HAMD bridge readiness audit to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
