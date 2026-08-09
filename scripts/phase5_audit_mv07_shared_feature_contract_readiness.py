#!/usr/bin/env python3
"""Audit readiness for a revised shared-symptom feature contract.

This is a planning/readiness gate for the next Phase 5 row, not a trainer. It
checks whether existing local feature caches can support a fair cross-dataset
shared-symptom validation after MV01/MV04b exposed WavLM identity risk. It
reads only manifest label fields and cached feature tables; it does not scan raw
text, audio, video, or gait files.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE2_ROOT = ROOT / "analysis" / "phase2_baselines"
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv07_shared_feature_contract_readiness"

TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "feature_cache_inventory.csv",
    "feature_contract_readiness.csv",
    "label_coverage_summary.csv",
    "recommended_feature_generation_queue.csv",
]

CORE_PHQ8_MAP = {
    "C01": "PHQ_8Depressed",
    "C02": "PHQ_8NoInterest",
    "C03": "PHQ_8Sleep",
    "C04": "PHQ_8Tired",
    "C05": "PHQ_8Appetite",
    "C06": "PHQ_8Failure",
    "C07": "PHQ_8Concentrating",
    "C08": "PHQ_8Moving",
}

CORE_PHQ9_MAP = {
    "C01": "PHQ-2",
    "C02": "PHQ-1",
    "C03": "PHQ-3",
    "C04": "PHQ-4",
    "C05": "PHQ-5",
    "C06": "PHQ-6",
    "C07": "PHQ-7",
    "C08": "PHQ-8",
}

HAMD_KEYS = [f"HAMD{i:02d}" for i in range(1, 18)]


@dataclass(frozen=True)
class FeatureCacheSpec:
    feature_family: str
    dataset: str
    cache_ref: str
    feature_prefix: str | None
    required_for_contracts: tuple[str, ...]


FEATURE_CACHE_SPECS = [
    FeatureCacheSpec(
        "audio_wavlm",
        "edaic",
        "edaic_audio_frozen_encoders/wavlm_subject_features.csv",
        "wavlm_",
        ("MV07_AUDIO_WAVLM_CONTROLLED",),
    ),
    FeatureCacheSpec(
        "audio_wavlm",
        "cmdc",
        "cmdc_audio_frozen_encoders/cmdc_wavlm_subject_features.csv",
        "wavlm_",
        ("MV07_AUDIO_WAVLM_CONTROLLED",),
    ),
    FeatureCacheSpec(
        "audio_wavlm",
        "pdch",
        "pdch_audio_wavlm/pdch_wavlm_subject_features.csv",
        "wavlm_",
        ("MV07_AUDIO_WAVLM_CONTROLLED",),
    ),
    FeatureCacheSpec(
        "text_bge",
        "edaic",
        "edaic_text_bge/edaic_bge_subject_features.csv",
        "bge_",
        ("MV07_TEXT_BGE_ALIGNED",),
    ),
    FeatureCacheSpec(
        "text_bge",
        "cmdc",
        "cmdc_pdch_text_encoder_mlp/cmdc_bge_subject_features.csv",
        "bge_",
        ("MV07_TEXT_BGE_ALIGNED",),
    ),
    FeatureCacheSpec(
        "text_bge",
        "pdch",
        "cmdc_pdch_text_encoder_mlp/pdch_bge_subject_features.csv",
        "bge_",
        ("MV07_TEXT_BGE_ALIGNED",),
    ),
    FeatureCacheSpec(
        "audio_egemaps",
        "edaic",
        "edaic_audio_egemaps/edaic_egemaps_subject_features.csv",
        None,
        ("MV07_AUDIO_EGEMAPS_ALIGNED",),
    ),
    FeatureCacheSpec(
        "audio_egemaps",
        "cmdc",
        "cmdc_pdch_audio_egemaps/cmdc_egemaps_subject_features.csv",
        None,
        ("MV07_AUDIO_EGEMAPS_ALIGNED",),
    ),
    FeatureCacheSpec(
        "audio_egemaps",
        "pdch",
        "cmdc_pdch_audio_egemaps/pdch_egemaps_subject_features.csv",
        None,
        ("MV07_AUDIO_EGEMAPS_ALIGNED",),
    ),
    FeatureCacheSpec(
        "audio_egemaps",
        "eatd",
        "eatd_audio_egemaps/eatd_egemaps_subject_features.csv",
        None,
        ("MV07_AUDIO_EGEMAPS_ALIGNED",),
    ),
]

CONTRACT_SPECS = {
    "MV07_TEXT_BGE_ALIGNED": {
        "name": "aligned_text_bge_shared_symptom_contract",
        "required_datasets": ("edaic", "cmdc", "pdch"),
        "required_feature_family": "text_bge",
        "target_scope": "E-DAIC/CMDC PHQ C01-C08 plus PDCH HAMD mapped constructs",
        "pass_gate": "same encoder family for all required datasets; at least E-DAIC and CMDC item labels; PDCH HAMD labels for auxiliary sanity; no raw text export",
    },
    "MV07_AUDIO_EGEMAPS_ALIGNED": {
        "name": "aligned_acoustic_egemaps_shared_contract",
        "required_datasets": ("edaic", "cmdc", "pdch", "eatd"),
        "required_feature_family": "audio_egemaps",
        "target_scope": "PHQ/HAMD shared constructs plus EATD SDS total stress as external audio floor",
        "pass_gate": "single eGeMAPS schema across required datasets before any pooled acoustic claim",
    },
    "MV07_AUDIO_WAVLM_CONTROLLED": {
        "name": "wavlm_identity_controlled_contract",
        "required_datasets": ("edaic", "cmdc", "pdch"),
        "required_feature_family": "audio_wavlm",
        "target_scope": "reuse common WavLM dimensionality only with stronger identity-control gates",
        "pass_gate": "feature-level identity must be reduced in an inference-compatible setting while preserving construct metrics",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def parse_json_object(value: Any) -> dict[str, Any]:
    text = clean_value(value)
    if not text:
        return {}
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return series.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def model_columns(frame: pd.DataFrame, spec: FeatureCacheSpec) -> list[str]:
    metadata = {
        "subject_id",
        "dataset_id",
        "split",
        "frame_count",
        "audio_segment_count",
        "text_segment_count",
        "token_count_sum",
        "chunk_count",
        "chunk_count_sum",
        "empty_text_segments",
        "duration_seconds",
        "duration_seconds_sum",
        "padded_short_chunk_count",
        "padded_short_chunk_count_sum",
        "transcript_turn_count",
        "non_empty_turn_count",
        "empty_turn_count",
        "token_count",
    }
    cols: list[str] = []
    for column in frame.columns:
        if column in metadata:
            continue
        if spec.feature_prefix is not None and not column.startswith(spec.feature_prefix):
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            cols.append(column)
    return sorted(cols)


def audit_feature_caches(phase2_root: Path) -> tuple[pd.DataFrame, dict[tuple[str, str], set[str]]]:
    rows: list[dict[str, Any]] = []
    columns_by_family_dataset: dict[tuple[str, str], set[str]] = {}
    for spec in FEATURE_CACHE_SPECS:
        cache_path = phase2_root / spec.cache_ref
        exists = cache_path.exists()
        row: dict[str, Any] = {
            "feature_family": spec.feature_family,
            "dataset": spec.dataset,
            "cache_ref": spec.cache_ref,
            "exists": exists,
            "feature_subjects": 0,
            "model_input_columns": 0,
            "path_like_columns": "",
            "required_for_contracts": ";".join(spec.required_for_contracts),
        }
        if exists:
            frame = pd.read_csv(cache_path)
            if "subject_id" not in frame.columns:
                row["path_like_columns"] = "missing_subject_id"
            else:
                frame["subject_id"] = frame["subject_id"].astype(str)
                path_like = [column for column in frame.columns if "path" in column.lower()]
                cols = model_columns(frame, spec)
                columns_by_family_dataset[(spec.feature_family, spec.dataset)] = set(cols)
                row.update(
                    {
                        "feature_subjects": int(frame["subject_id"].nunique()),
                        "model_input_columns": int(len(cols)),
                        "path_like_columns": ";".join(path_like),
                    }
                )
        rows.append(row)
    return pd.DataFrame(rows), columns_by_family_dataset


def has_all_numeric_items(payload: dict[str, Any], item_codes: dict[str, str]) -> bool:
    for item_code in item_codes.values():
        value = safe_float(payload.get(item_code))
        if value is None:
            return False
    return True


def full_hamd_payload(payload: dict[str, Any]) -> bool:
    return all(safe_float(payload.get(key)) is not None for key in HAMD_KEYS)


def label_coverage(manifest_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    edaic = pd.read_csv(
        manifest_dir / "edaic_subjects.csv",
        usecols=["subject_id", "file_valid", "official_split", "phq8_total", "phq8_items"],
    )
    edaic = edaic[bool_series(edaic["file_valid"]) & edaic["official_split"].isin(["train", "dev"])].copy()
    edaic["subject_id"] = edaic["subject_id"].astype(str)
    edaic_subjects = []
    for subject_id, group in edaic.groupby("subject_id", sort=True):
        row = group.iloc[0]
        if safe_float(row["phq8_total"]) is not None and has_all_numeric_items(parse_json_object(row["phq8_items"]), CORE_PHQ8_MAP):
            edaic_subjects.append(subject_id)
    rows.append(
        {
            "dataset": "edaic",
            "label_contract": "PHQ8_C01_C08_item_supervision",
            "usable_subjects": len(set(edaic_subjects)),
            "scope_note": "train_dev_only_no_official_test_item_labels",
        }
    )

    cmdc = pd.read_csv(
        manifest_dir / "cmdc_subjects.csv",
        usecols=["subject_id", "file_valid", "phq9_total", "phq9_items", "hamd17_total", "hamd17_items"],
    )
    cmdc = cmdc[bool_series(cmdc["file_valid"])].copy()
    cmdc["subject_id"] = cmdc["subject_id"].astype(str)
    cmdc_phq_subjects: set[str] = set()
    cmdc_hamd_subjects: set[str] = set()
    for subject_id, group in cmdc.groupby("subject_id", sort=True):
        row = group.iloc[0]
        if safe_float(row["phq9_total"]) is not None and has_all_numeric_items(parse_json_object(row["phq9_items"]), CORE_PHQ9_MAP):
            cmdc_phq_subjects.add(subject_id)
        totals = {safe_float(value) for value in group["hamd17_total"].tolist()}
        totals.discard(None)
        payloads = [parse_json_object(value) for value in group["hamd17_items"].tolist()]
        if len(totals) == 1 and any(full_hamd_payload(payload) for payload in payloads):
            cmdc_hamd_subjects.add(subject_id)
    rows.extend(
        [
            {
                "dataset": "cmdc",
                "label_contract": "PHQ9_C01_C08_item_supervision",
                "usable_subjects": len(cmdc_phq_subjects),
                "scope_note": "clinical_interview_subjects",
            },
            {
                "dataset": "cmdc",
                "label_contract": "HAMD17_limited_sanity_subset",
                "usable_subjects": len(cmdc_hamd_subjects),
                "scope_note": "coverage_limited_sanity_only",
            },
        ]
    )

    pdch = pd.read_csv(
        manifest_dir / "pdch_subjects.csv",
        usecols=["subject_id", "file_valid", "hamd17_total", "hamd17_items"],
    )
    pdch = pdch[bool_series(pdch["file_valid"])].copy()
    pdch["subject_id"] = pdch["subject_id"].astype(str)
    pdch_hamd_subjects: set[str] = set()
    for subject_id, group in pdch.groupby("subject_id", sort=True):
        totals = {safe_float(value) for value in group["hamd17_total"].tolist()}
        totals.discard(None)
        payloads = [parse_json_object(value) for value in group["hamd17_items"].tolist()]
        if len(totals) == 1 and any(full_hamd_payload(payload) for payload in payloads):
            pdch_hamd_subjects.add(subject_id)
    rows.append(
        {
            "dataset": "pdch",
            "label_contract": "HAMD17_item_total_supervision",
            "usable_subjects": len(pdch_hamd_subjects),
            "scope_note": "primary_hamd_internal_validation",
        }
    )

    eatd = pd.read_csv(
        manifest_dir / "eatd_subjects.csv",
        usecols=["subject_id", "file_valid", "sds_total", "official_split"],
    )
    eatd = eatd[bool_series(eatd["file_valid"])].copy()
    eatd["subject_id"] = eatd["subject_id"].astype(str)
    sds_subjects = eatd[pd.to_numeric(eatd["sds_total"], errors="coerce").notna()]["subject_id"].nunique()
    rows.append(
        {
            "dataset": "eatd",
            "label_contract": "SDS_total_only_external_stress",
            "usable_subjects": int(sds_subjects),
            "scope_note": "no_sds_item_supervision_current_manifest",
        }
    )

    return pd.DataFrame(rows)


def contract_readiness(features: pd.DataFrame, columns_by_family_dataset: dict[tuple[str, str], set[str]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for contract_id, spec in CONTRACT_SPECS.items():
        family = str(spec["required_feature_family"])
        datasets = tuple(spec["required_datasets"])
        selected = features[(features["feature_family"] == family) & (features["dataset"].isin(datasets))].copy()
        missing = sorted(set(datasets) - set(selected.loc[selected["exists"], "dataset"]))
        schema_sets = [columns_by_family_dataset.get((family, dataset), set()) for dataset in datasets]
        common_columns = set.intersection(*schema_sets) if schema_sets and all(schema_sets) else set()
        min_subjects = int(selected.loc[selected["exists"], "feature_subjects"].min()) if selected["exists"].any() else 0
        path_like = selected[selected["path_like_columns"].map(clean_value).map(bool)]
        if missing:
            status = "blocked_missing_required_feature_cache"
            next_step = f"Generate {family} subject features for: {', '.join(missing)}."
        elif len(common_columns) == 0:
            status = "blocked_schema_mismatch"
            next_step = f"Regenerate {family} with one shared schema/extractor across: {', '.join(datasets)}."
        elif contract_id == "MV07_AUDIO_WAVLM_CONTROLLED":
            status = "available_but_identity_blocked_current_contract"
            next_step = "Only rerun WavLM after a stronger inference-compatible identity control is specified; current WavLM evidence is not enough."
        elif not path_like.empty:
            status = "blocked_path_like_feature_columns"
            next_step = "Remove path-like columns from the feature contract before modeling."
        else:
            status = "ready_to_run_minimal_validation"
            next_step = "Run subject-level shallow-head MV07 with identity/protocol probes and local-only row predictions."
        rows.append(
            {
                "contract_id": contract_id,
                "name": spec["name"],
                "required_feature_family": family,
                "required_datasets": ";".join(datasets),
                "target_scope": spec["target_scope"],
                "current_status": status,
                "missing_datasets": ";".join(missing),
                "common_model_input_columns": int(len(common_columns)),
                "min_feature_subjects": min_subjects,
                "pass_gate": spec["pass_gate"],
                "next_step": next_step,
            }
        )
    return pd.DataFrame(rows)


def generation_queue(contracts: pd.DataFrame) -> pd.DataFrame:
    text_status = str(
        contracts.loc[contracts["contract_id"] == "MV07_TEXT_BGE_ALIGNED", "current_status"].iloc[0]
    )
    if text_status == "ready_to_run_minimal_validation":
        first_action = {
            "rank": 1,
            "action_id": "RUN_MV07_TEXT_BGE_SHARED_SYMPTOM",
            "action": "Run the MV07 shallow shared-symptom validation row on aligned E-DAIC/CMDC/PDCH BGE features.",
            "why": "E-DAIC, CMDC, and PDCH now share a 512-column BGE subject-level feature family, so the next blocker is model evidence rather than feature availability.",
            "success_gate": "subject-level PHQ/HAMD construct heads beat simple floors where applicable and include dataset/protocol identity probes with local-only predictions.",
            "version_policy": "Track scripts and aggregate summaries; keep row predictions, transformed features, and model artifacts local-only.",
        }
    else:
        first_action = {
            "rank": 1,
            "action_id": "GEN_EDAIC_BGE_SUBJECT_FEATURES",
            "action": "Generate E-DAIC subject-level BGE text features from manifest-governed transcripts.",
            "why": "BGE is already available for CMDC and PDCH; adding E-DAIC creates the cleanest aligned text feature contract for PHQ/HAMD shared-symptom testing.",
            "success_gate": "edaic text_bge cache exists with bge_* columns, subject-level rows, no path-like columns, no raw text export.",
            "version_policy": "Keep generated BGE feature CSV local-only; commit only scripts and aggregate readiness summaries.",
        }
    rows = [
        first_action,
        {
            "rank": 2,
            "action_id": "REGEN_ALIGNED_EGEMAPS_V2",
            "action": "Regenerate aligned eGeMAPS subject features with one extractor/schema for E-DAIC, CMDC, PDCH, and EATD.",
            "why": "Current E-DAIC/EATD eGeMAPS schema does not align with CMDC/PDCH eGeMAPS schema, blocking fair pooled acoustic claims.",
            "success_gate": "all required datasets share nonzero common model-input columns and pass artifact hygiene.",
            "version_policy": "Keep feature CSVs local-only; commit schema/readiness summaries only.",
        },
        {
            "rank": 3,
            "action_id": "SPECIFY_WAVLM_IDENTITY_CONTROL",
            "action": "Specify a stronger WavLM identity-control variant before rerunning shared-symptom validation on WavLM.",
            "why": "WavLM is dimensionally aligned but current MV01/MV04b evidence leaves feature-level dataset identity too high.",
            "success_gate": "feature identity is reduced in an inference-compatible setting while construct metrics stay within tolerance.",
            "version_policy": "Track scripts/summaries; keep projections, transformed features, and row predictions local-only.",
        },
    ]
    return pd.DataFrame(rows)


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
        r"raw_snippet",
        r"local_text_locators_json",
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
        "audit_id": "P5_MV07_shared_feature_contract_readiness_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(out_dir: Path, run_summary: dict[str, Any], contracts: pd.DataFrame, labels: pd.DataFrame, queue: pd.DataFrame) -> None:
    lines = [
        "# P5_MV07 Shared Feature Contract Readiness",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This audit checks whether existing cached subject-level features are aligned enough to run a revised shared-symptom minimal-validation row. It does not train a model and does not scan raw text, audio, video, or gait files.",
        "",
        "## Decision",
        "",
        f"- Readiness status: `{run_summary['decision']['readiness_status']}`.",
        f"- Recommended next contract: `{run_summary['decision']['recommended_next_contract']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Contract Readiness",
        "",
        "| contract | status | required datasets | common columns | next step |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for _, row in contracts.iterrows():
        lines.append(
            f"| {row['contract_id']} | `{row['current_status']}` | {row['required_datasets']} | "
            f"{row['common_model_input_columns']} | {row['next_step']} |"
        )
    lines.extend(
        [
            "",
            "## Label Coverage",
            "",
            "| dataset | label contract | usable subjects | note |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for _, row in labels.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['label_contract']} | {row['usable_subjects']} | {row['scope_note']} |"
        )
    lines.extend(
        [
            "",
        "## Recommended Next Actions",
            "",
            "| rank | action | success gate |",
            "| ---: | --- | --- |",
        ]
    )
    for _, row in queue.iterrows():
        lines.append(f"| {row['rank']} | {row['action']} | {row['success_gate']} |")
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
        "- Readiness means the feature contract is available; it is not model evidence.",
        "- WavLM remains usable only as a controlled diagnostic because identity remains high.",
        "- The cleanest next implementation is the aligned BGE MV07 shallow shared-symptom validation row with identity/protocol probes.",
    ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase2-root", type=Path, default=PHASE2_ROOT)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    features, columns_by_family_dataset = audit_feature_caches(args.phase2_root)
    labels = label_coverage(args.manifest_dir)
    contracts = contract_readiness(features, columns_by_family_dataset)
    queue = generation_queue(contracts)

    features.to_csv(out_dir / "feature_cache_inventory.csv", index=False)
    contracts.to_csv(out_dir / "feature_contract_readiness.csv", index=False)
    labels.to_csv(out_dir / "label_coverage_summary.csv", index=False)
    queue.to_csv(out_dir / "recommended_feature_generation_queue.csv", index=False)

    ready_contracts = contracts[contracts["current_status"] == "ready_to_run_minimal_validation"]
    text_status = contracts.loc[contracts["contract_id"] == "MV07_TEXT_BGE_ALIGNED", "current_status"].iloc[0]
    readiness_status = (
        "ready_to_run_minimal_validation"
        if not ready_contracts.empty
        else "blocked_current_cached_features_insufficient_for_mv07"
    )
    if readiness_status == "ready_to_run_minimal_validation":
        recommended = "MV07_TEXT_BGE_ALIGNED_run_shallow_shared_symptom_validation"
        short_read = (
            "The aligned BGE text contract is ready: E-DAIC, CMDC, and PDCH now share 512 BGE model-input columns. This authorizes the next MV07 shallow validation row, not a shared-symptom claim yet."
        )
    else:
        recommended = "MV07_TEXT_BGE_ALIGNED_after_generating_EDAIC_BGE"
        short_read = (
            "Current caches are not sufficient for a fair new shared-symptom row: WavLM is aligned but identity-blocked, BGE text lacks E-DAIC, and eGeMAPS schemas are mismatched. Generate aligned E-DAIC BGE text features first."
        )
    run_summary = {
        "run_id": "P5_MV07_shared_feature_contract_readiness",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "feature_contract_readiness_no_training",
        "input_contract": {
            "raw_data_scanned": False,
            "raw_text_read": False,
            "feature_cache_rows_read": True,
            "manifest_label_fields_read": True,
        },
        "decision": {
            "readiness_status": readiness_status,
            "recommended_next_contract": recommended,
            "text_bge_contract_status": str(text_status),
            "short_read": short_read,
        },
        "feature_cache_rows": int(len(features)),
        "contract_rows": int(len(contracts)),
        "label_coverage_rows": int(len(labels)),
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "row_level_predictions_written": False,
            "learned_features_written": False,
            "raw_paths_written": False,
            "raw_text_written": False,
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, contracts, labels, queue)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, contracts, labels, queue)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "readiness_status": readiness_status,
                "recommended_next_contract": recommended,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
