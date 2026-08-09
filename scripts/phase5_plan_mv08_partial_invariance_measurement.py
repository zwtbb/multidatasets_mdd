#!/usr/bin/env python3
"""Plan the next RQ1 row around partial measurement invariance.

This is a design/readiness audit, not a trainer. It translates the current
negative/partial Phase 5 evidence into a concrete P5_MV08 protocol:
shared latent symptom constructs with scale-specific loading and threshold DIF
deviations. It reads only generated manifests and Phase 4 ontology tables, and
exports aggregate planning artifacts.
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
PHASE4_DIR = ROOT / "analysis" / "phase4_symptom_ontology"
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_MANIFEST_DIR = ROOT / "datasets" / "manifests"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv08_partial_invariance_measurement_design"

TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "label_contract_coverage.csv",
    "construct_anchor_matrix.csv",
    "measurement_model_contract.csv",
    "dif_parameter_contract.csv",
    "readiness_gate.csv",
    "implementation_queue.csv",
    "method_source_refs.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "ordinal_measurement_invariance_guide",
        "url": "https://gsdi.unc.edu/wp-content/uploads/sites/1264/2017/03/Bowen_Masa_2015.pdf",
        "source_type": "methodological_guide",
        "use_in_mv08": "Use configural, metric/loading, scalar/threshold, and partial-invariance logic for ordinal indicators.",
        "key_takeaway": "For ordinal data, threshold constraints matter; partial invariance is acceptable only when noninvariant parameters are explicit and limited.",
    },
    {
        "source_id": "dif_methods_columbia",
        "url": "https://www.publichealth.columbia.edu/research/population-health-methods/differential-item-functioning",
        "source_type": "method_overview",
        "use_in_mv08": "Frame scale and dataset deviations as DIF in loadings/discrimination and thresholds/severity.",
        "key_takeaway": "DIF compares no-DIF models with models that allow item parameters to differ across groups; MIMIC models are a covariate-based extension.",
    },
    {
        "source_id": "graded_response_model_stata_manual",
        "url": "https://www.stata.com/manuals/irtirtgrm.pdf",
        "source_type": "official_software_manual",
        "use_in_mv08": "Use a graded-response/cumulative-logit item likelihood for ordered PHQ and HAMD item scores.",
        "key_takeaway": "GRM models ordinal item responses with item discrimination and ordered cutpoints.",
    },
    {
        "source_id": "lord_irt_item_bias",
        "url": "https://www.ets.org/research/policy_research_reports/publications/book/1980/jexj.html",
        "source_type": "classic_irt_reference",
        "use_in_mv08": "Use IRT terminology for item parameters, equating, and item bias when writing the paper method section.",
        "key_takeaway": "IRT expresses test measurement through item parameters; item bias/equating are central when comparing scales.",
    },
]


@dataclass(frozen=True)
class ScaleContract:
    dataset: str
    scale: str
    manifest_name: str
    total_col: str
    item_col: str | None
    active_role: str
    subject_filter: str


SCALE_CONTRACTS = [
    ScaleContract(
        "edaic",
        "PHQ-8",
        "edaic_subjects.csv",
        "phq8_total",
        "phq8_items",
        "primary_phq_anchor",
        "train_dev_only",
    ),
    ScaleContract(
        "cmdc",
        "PHQ-9",
        "cmdc_subjects.csv",
        "phq9_total",
        "phq9_items",
        "cross_language_phq_anchor",
        "all_valid_rows",
    ),
    ScaleContract(
        "cmdc",
        "HAMD-17",
        "cmdc_subjects.csv",
        "hamd17_total",
        "hamd17_items",
        "limited_hamd_sanity",
        "all_valid_rows",
    ),
    ScaleContract(
        "pdch",
        "HAMD-17",
        "pdch_subjects.csv",
        "hamd17_total",
        "hamd17_items",
        "primary_hamd_validation",
        "all_valid_rows",
    ),
    ScaleContract(
        "eatd",
        "SDS",
        "eatd_subjects.csv",
        "sds_total",
        None,
        "total_only_external_stress",
        "all_valid_rows",
    ),
    ScaleContract(
        "mpdd_avg_2026",
        "PHQ-9",
        "mpdd_avg_2026_subjects.csv",
        "phq9_total",
        None,
        "total_only_context_stress",
        "labeled_train_only",
    ),
]


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


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def manifest_item_key(row: pd.Series) -> str:
    aliases = clean_value(row.get("project_aliases"))
    if aliases:
        return aliases.split(";")[0]
    return clean_value(row.get("item_code"))


def item_catalog(path: Path) -> pd.DataFrame:
    catalog = pd.read_csv(path)
    catalog["manifest_key"] = catalog.apply(manifest_item_key, axis=1)
    return catalog


def item_keys_by_scale(catalog: pd.DataFrame) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for scale, group in catalog.groupby("scale", sort=True):
        out[str(scale)] = sorted(clean_value(value) for value in group["manifest_key"] if clean_value(value))
    return out


def construct_items(catalog: pd.DataFrame, scale: str, construct_id: str) -> list[str]:
    selected = catalog[
        (catalog["scale"] == scale)
        & (
            (catalog["primary_construct_id"] == construct_id)
            | catalog["secondary_construct_ids"].fillna("").astype(str).str.split(";").map(
                lambda values: construct_id in {clean_value(value) for value in values}
            )
        )
    ]
    return sorted(clean_value(code) for code in selected["item_code"] if clean_value(code))


def apply_subject_filter(frame: pd.DataFrame, spec: ScaleContract) -> pd.DataFrame:
    if "file_valid" in frame.columns:
        frame = frame[bool_series(frame["file_valid"])].copy()
    if spec.subject_filter == "train_dev_only" and "official_split" in frame.columns:
        frame = frame[frame["official_split"].astype(str).isin(["train", "dev"])].copy()
    if spec.subject_filter == "labeled_train_only" and "official_split" in frame.columns:
        frame = frame[frame["official_split"].astype(str).isin(["train", "training", "train_labeled"])].copy()
    return frame


def has_item_payload(payload: dict[str, Any], keys: list[str]) -> bool:
    return bool(keys) and all(safe_float(payload.get(key)) is not None for key in keys)


def score_range(values: list[float]) -> str:
    if not values:
        return ""
    return f"{min(values):.3f}:{max(values):.3f}"


def label_contract_coverage(manifest_dir: Path, catalog: pd.DataFrame) -> pd.DataFrame:
    keys_by_scale = item_keys_by_scale(catalog)
    rows: list[dict[str, Any]] = []
    for spec in SCALE_CONTRACTS:
        path = manifest_dir / spec.manifest_name
        usecols = ["subject_id", "file_valid", spec.total_col]
        if spec.item_col is not None:
            usecols.append(spec.item_col)
        if spec.subject_filter in {"train_dev_only", "labeled_train_only"}:
            usecols.append("official_split")
        frame = pd.read_csv(path, usecols=[column for column in usecols if column])
        frame = apply_subject_filter(frame, spec)
        frame["subject_id"] = frame["subject_id"].astype(str)

        total_subjects: set[str] = set()
        item_subjects: set[str] = set()
        score_values: list[float] = []
        required_keys = keys_by_scale.get(spec.scale, [])
        for group_id, group in frame.groupby("subject_id", sort=True):
            totals = [safe_float(value) for value in group[spec.total_col].tolist()]
            numeric_totals = [value for value in totals if value is not None]
            if numeric_totals:
                total_subjects.add(str(group_id))
                score_values.append(float(numeric_totals[0]))
            if spec.item_col is None:
                continue
            payloads = [parse_json_object(value) for value in group[spec.item_col].tolist()]
            if any(has_item_payload(payload, required_keys) for payload in payloads):
                item_subjects.add(str(group_id))

        item_status = "item_level_available" if item_subjects else "total_only"
        if spec.scale == "HAMD-17" and spec.dataset == "cmdc":
            item_status = "limited_hamd_sanity_subset"
        active_in_mv08 = spec.dataset in {"edaic", "cmdc", "pdch"} and bool(item_subjects)
        rows.append(
            {
                "dataset": spec.dataset,
                "scale": spec.scale,
                "active_role": spec.active_role,
                "total_subjects": int(len(total_subjects)),
                "item_subjects": int(len(item_subjects)),
                "required_item_count": int(len(required_keys)),
                "total_score_range": score_range(score_values),
                "item_supervision_status": item_status,
                "active_in_mv08": active_in_mv08,
                "scope_note": spec.subject_filter,
            }
        )
    return pd.DataFrame(rows)


def build_construct_anchor_matrix(construct_map: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in construct_map.iterrows():
        construct_id = clean_value(row["construct_id"])
        phq8_items = construct_items(catalog, "PHQ-8", construct_id)
        phq9_items = construct_items(catalog, "PHQ-9", construct_id)
        hamd_items = construct_items(catalog, "HAMD-17", construct_id)
        sds_items = construct_items(catalog, "SDS", construct_id)
        if construct_id in {f"C{i:02d}" for i in range(1, 9)}:
            if phq8_items and phq9_items and hamd_items:
                role = "core_anchor_partial_hamd"
            elif phq8_items and phq9_items:
                role = "core_phq_anchor"
            else:
                role = "construct_specific"
        elif construct_id == "C09":
            role = "safety_anchor_phq9_hamd_explicit_only"
        elif hamd_items:
            role = "hamd_auxiliary_or_scale_specific"
        elif sds_items:
            role = "sds_total_blocked_until_item_supervision"
        else:
            role = "not_active_in_mv08"
        rows.append(
            {
                "construct_id": construct_id,
                "construct_label": clean_value(row["construct_label"]),
                "tier": clean_value(row["tier"]),
                "phq8_items": ";".join(phq8_items),
                "phq9_items": ";".join(phq9_items),
                "hamd17_items": ";".join(hamd_items),
                "sds_items": ";".join(sds_items),
                "mv08_anchor_role": role,
            }
        )
    return pd.DataFrame(rows)


def measurement_model_contract() -> pd.DataFrame:
    rows = [
        {
            "model_id": "M0_total_score_floor",
            "model_family": "baseline",
            "latent_constructs": "none",
            "item_likelihood": "none_or_total_regression",
            "scale_parameters": "dataset_specific_total_or_total_allocation_heads",
            "dif_policy": "not_modeled",
            "comparison_role": "must_beat_or_explain_failure",
            "pass_gate": "Partial-invariance model must improve over this floor on at least one active external/sanity axis without worse dataset identity evidence.",
        },
        {
            "model_id": "M1_fixed_construct_map",
            "model_family": "fixed_mapping",
            "latent_constructs": "C01_C09_from_phase4_map",
            "item_likelihood": "ordinal_or_squared_item_loss",
            "scale_parameters": "fixed_A0_mapping_with_scale_specific_item_heads",
            "dif_policy": "no_free_dataset_dif",
            "comparison_role": "tests_the_old_hypothesis",
            "pass_gate": "If this fails again, report it as negative evidence for direct fixed shared mapping.",
        },
        {
            "model_id": "M2_partial_invariance_ordinal_latent",
            "model_family": "target_mv08",
            "latent_constructs": "shared_C01_C09_plus_hamd_auxiliary_C10_C13",
            "item_likelihood": "graded_response_or_cumulative_logit",
            "scale_parameters": "shared_anchor_loadings_with_scale_specific_thresholds_and_sparse_delta_loadings",
            "dif_policy": "allow_shrunk_dataset_or_scale_DIF_for_predeclared_items",
            "comparison_role": "next_rq1_candidate",
            "pass_gate": "Beat total-score/fixed-map floors where feasible and produce interpretable DIF concentrated in known partial/auxiliary HAMD/SDS constructs.",
        },
        {
            "model_id": "M3_measurement_heterogeneity_moderators",
            "model_family": "later_extension",
            "latent_constructs": "same_as_M2",
            "item_likelihood": "graded_response_or_cumulative_logit",
            "scale_parameters": "M2_plus_age_personality_or_protocol_DIF_terms",
            "dif_policy": "moderator_DIF_only_after_M2_passes",
            "comparison_role": "later_RQ3_RQ2_bridge",
            "pass_gate": "Only run after M2 has nontrivial measurement value; must improve subgroup/protocol behavior over M2 and shuffled controls.",
        },
    ]
    return pd.DataFrame(rows)


def dif_parameter_contract() -> pd.DataFrame:
    rows = [
        {
            "layer": "configural",
            "parameter": "construct_item_graph",
            "first_pass_constraint": "same_C01_C08_graph_for_PHQ8_PHQ9; HAMD_uses_phase4_partial_auxiliary_graph",
            "free_deviation": "no_unmapped_item_may_load_on_all_constructs",
            "why": "Do not let the latent model erase the clinical ontology.",
        },
        {
            "layer": "metric_loading",
            "parameter": "item_to_construct_loading",
            "first_pass_constraint": "tie_direct_PHQ8_PHQ9_C01_C08_loadings_where_item_meaning_matches",
            "free_deviation": "allow_sparse_scale_delta_for_HAMD_partial_or_secondary_items",
            "why": "Direct PHQ anchors test shared symptom meaning; HAMD items often split or broaden constructs.",
        },
        {
            "layer": "scalar_threshold",
            "parameter": "ordinal_cutpoints",
            "first_pass_constraint": "keep_ordered_cutpoints; do_not_force_PHQ_and_HAMD_thresholds_equal",
            "free_deviation": "estimate_scale_specific_thresholds; optionally shrink_dataset_threshold_offsets",
            "why": "Different scales can measure the same construct with different category boundaries.",
        },
        {
            "layer": "dataset_DIF",
            "parameter": "dataset_or_language_loading_threshold_offsets",
            "first_pass_constraint": "zero_mean_shrunk_offsets_with_dataset_stratified_report",
            "free_deviation": "allow_cmdc_language_protocol_DIF_and_pdch_clinician_scale_DIF_when_supported",
            "why": "DIF is the target diagnostic, not a nuisance to hide.",
        },
        {
            "layer": "moderator_DIF",
            "parameter": "age_personality_health_protocol_offsets",
            "first_pass_constraint": "blocked_in_mv08_training",
            "free_deviation": "design_only_for_later_M3",
            "why": "Keep the first row focused on scale/dataset measurement before adding RQ2/RQ3 complexity.",
        },
    ]
    return pd.DataFrame(rows)


def readiness_gate(coverage: pd.DataFrame) -> pd.DataFrame:
    def item_count(dataset: str, scale: str) -> int:
        selected = coverage[(coverage["dataset"] == dataset) & (coverage["scale"] == scale)]
        if selected.empty:
            return 0
        return int(selected["item_subjects"].iloc[0])

    edaic_phq8 = item_count("edaic", "PHQ-8")
    cmdc_phq9 = item_count("cmdc", "PHQ-9")
    pdch_hamd = item_count("pdch", "HAMD-17")
    cmdc_hamd = item_count("cmdc", "HAMD-17")
    prior_mv07 = PHASE5_DIR / "p5_mv07c_bge_total_anchor" / "run_summary.json"
    mv06_summary = PHASE5_DIR / "p5_mv06_evidence_annotation_summary" / "run_summary.json"
    rows = [
        {
            "gate_id": "G_LABEL_ACTIVE_DATASETS",
            "status": "pass" if edaic_phq8 >= 200 and cmdc_phq9 >= 50 and pdch_hamd >= 80 else "blocked",
            "evidence": f"edaic_phq8_items={edaic_phq8};cmdc_phq9_items={cmdc_phq9};pdch_hamd_items={pdch_hamd}",
            "required_next": "Use E-DAIC/CMDC/PDCH as active MV08 datasets; keep CMDC HAMD as sanity only.",
        },
        {
            "gate_id": "G_CMDC_HAMD_SANITY_ONLY",
            "status": "pass_limited" if 0 < cmdc_hamd < 50 else "review",
            "evidence": f"cmdc_hamd_items={cmdc_hamd}",
            "required_next": "Do not treat CMDC HAMD as a full HAMD external validation set.",
        },
        {
            "gate_id": "G_PRIOR_FIXED_MAP_NEGATIVE",
            "status": "pass" if prior_mv07.exists() else "missing",
            "evidence": rel(prior_mv07) if prior_mv07.exists() else "",
            "required_next": "Use MV07/MV07b/MV07c as the negative/partial baseline sequence that justifies changing the measurement contract.",
        },
        {
            "gate_id": "G_RQ4_SUPPORT_LIMITED",
            "status": "pass_limited" if mv06_summary.exists() else "missing",
            "evidence": rel(mv06_summary) if mv06_summary.exists() else "",
            "required_next": "Use MV06 only as first-round aggregate credibility evidence; strengthen E-DAIC agreement later.",
        },
        {
            "gate_id": "G_NO_FULL_METHOD_AUTHORIZATION",
            "status": "blocked_full_method",
            "evidence": "MV08 is a minimal-validation row design, not a full M0/M1/M2/M3 start.",
            "required_next": "Implement and audit MV08 before changing the full-method gate.",
        },
    ]
    return pd.DataFrame(rows)


def implementation_queue() -> pd.DataFrame:
    rows = [
        {
            "rank": 1,
            "action_id": "IMPLEMENT_MV08_TRAINER",
            "action": "Create scripts/phase5_run_mv08_partial_invariance_measurement.py using aligned BGE features and subject-level folds.",
            "success_gate": "Outputs compare M0 total, M1 fixed map, and M2 partial-invariance ordinal heads with dataset-stratified metrics.",
            "version_policy": "Track script and aggregate summaries; keep row predictions, latent scores, learned parameters, and model files local-only.",
        },
        {
            "rank": 2,
            "action_id": "FREEZE_MV08_PARAMETER_TABLE",
            "action": "Turn dif_parameter_contract.csv into a checked config that names exactly which loadings or thresholds may deviate.",
            "success_gate": "No post-hoc item freeing without an issue-log entry and rerun of the design audit.",
            "version_policy": "Track config because it is part of the reproducibility contract.",
        },
        {
            "rank": 3,
            "action_id": "RUN_MV08_PILOT",
            "action": "Run the first MV08 pilot on E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17 labels only.",
            "success_gate": "Subject-level split checks pass, no raw text/media read, and artifact hygiene passes.",
            "version_policy": "Commit aggregate gate outputs only.",
        },
        {
            "rank": 4,
            "action_id": "UPDATE_FULL_METHOD_GATE_WITH_MV08_RESULTS",
            "action": "After MV08 results exist, rerun the full-method gate and decide whether RQ1 remains blocked or becomes a bounded method claim.",
            "success_gate": "The gate changes only from measured evidence, not from design intent.",
            "version_policy": "Track claim-gate outputs; keep local-only artifacts ignored.",
        },
    ]
    return pd.DataFrame(rows)


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
        "audit_id": "P5_MV08_partial_invariance_measurement_design_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    coverage: pd.DataFrame,
    anchors: pd.DataFrame,
    models: pd.DataFrame,
    gate: pd.DataFrame,
    queue: pd.DataFrame,
) -> None:
    active = coverage[coverage["active_in_mv08"]]
    core_anchors = anchors[anchors["mv08_anchor_role"].astype(str).str.contains("anchor")]
    lines = [
        "# P5_MV08 Partial-Invariance Measurement Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This design audit turns the RQ1 pivot into a concrete minimal-validation row. It does not train a model, read raw text, or export row-level examples.",
        "",
        "## Decision",
        "",
        f"- Readiness status: `{run_summary['decision']['readiness_status']}`.",
        f"- Recommended next action: `{run_summary['decision']['recommended_next_action']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Active Label Coverage",
        "",
        "| dataset | scale | role | total subjects | item subjects | status |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for _, row in active.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['scale']} | {row['active_role']} | "
            f"{row['total_subjects']} | {row['item_subjects']} | {row['item_supervision_status']} |"
        )
    lines.extend(
        [
            "",
            "## Anchor Constructs",
            "",
            "| construct | label | role | PHQ-8 | PHQ-9 | HAMD-17 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in core_anchors.iterrows():
        lines.append(
            f"| {row['construct_id']} | {row['construct_label']} | {row['mv08_anchor_role']} | "
            f"{row['phq8_items']} | {row['phq9_items']} | {row['hamd17_items']} |"
        )
    lines.extend(
        [
            "",
            "## Model Ladder",
            "",
            "| model | family | comparison role | DIF policy |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in models.iterrows():
        lines.append(f"| {row['model_id']} | {row['model_family']} | {row['comparison_role']} | {row['dif_policy']} |")
    lines.extend(
        [
            "",
            "## Readiness Gate",
            "",
            "| gate | status | evidence | required next |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in gate.iterrows():
        lines.append(f"| {row['gate_id']} | `{row['status']}` | {row['evidence']} | {row['required_next']} |")
    lines.extend(
        [
            "",
            "## Implementation Queue",
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
            "- MV08 design readiness does not authorize full M0/M1/M2/M3 construction.",
            "- A future MV08 result must beat or explain failure against both total-score and fixed-map baselines.",
            "- Any DIF finding must be reported as measurement heterogeneity, not hidden as a generic domain-adaptation residual.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-dir", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    catalog = item_catalog(PHASE4_DIR / "scale_item_catalog.csv")
    construct_map = pd.read_csv(PHASE4_DIR / "construct_scale_map.csv")
    coverage = label_contract_coverage(args.manifest_dir, catalog)
    anchors = build_construct_anchor_matrix(construct_map, catalog)
    models = measurement_model_contract()
    dif = dif_parameter_contract()
    gate = readiness_gate(coverage)
    queue = implementation_queue()
    refs = pd.DataFrame(METHOD_SOURCE_REFS)

    coverage.to_csv(out_dir / "label_contract_coverage.csv", index=False)
    anchors.to_csv(out_dir / "construct_anchor_matrix.csv", index=False)
    models.to_csv(out_dir / "measurement_model_contract.csv", index=False)
    dif.to_csv(out_dir / "dif_parameter_contract.csv", index=False)
    gate.to_csv(out_dir / "readiness_gate.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    active = coverage[coverage["active_in_mv08"]]
    label_gate_passed = bool((gate["gate_id"] == "G_LABEL_ACTIVE_DATASETS").any()) and (
        str(gate.loc[gate["gate_id"] == "G_LABEL_ACTIVE_DATASETS", "status"].iloc[0]) == "pass"
    )
    readiness_status = (
        "ready_to_implement_partial_invariance_validation"
        if label_gate_passed
        else "blocked_insufficient_item_supervision"
    )
    run_summary = {
        "run_id": "P5_MV08_partial_invariance_measurement_design",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "design_readiness_no_training",
        "input_contract": {
            "raw_data_scanned": False,
            "raw_text_read": False,
            "manifest_label_fields_read": True,
            "phase4_ontology_read": True,
        },
        "decision": {
            "readiness_status": readiness_status,
            "recommended_next_action": "IMPLEMENT_MV08_TRAINER",
            "short_read": (
                "MV08 is ready to implement as a minimal-validation row: active item supervision exists for E-DAIC PHQ-8, CMDC PHQ-9, and PDCH HAMD-17. The row should compare total-score, fixed-map, and partial-invariance ordinal latent measurement heads before any full-method claim."
                if label_gate_passed
                else "MV08 is not ready: active E-DAIC/CMDC/PDCH item supervision does not meet the minimum design gate."
            ),
        },
        "coverage_rows": int(len(coverage)),
        "active_coverage_rows": int(len(active)),
        "anchor_rows": int(len(anchors)),
        "model_contract_rows": int(len(models)),
        "dif_contract_rows": int(len(dif)),
        "source_ref_rows": int(len(refs)),
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "row_level_predictions_written": False,
            "learned_parameters_written": False,
            "latent_scores_written": False,
            "raw_paths_written": False,
            "raw_text_written": False,
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, coverage, anchors, models, gate, queue)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, coverage, anchors, models, gate, queue)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "readiness_status": readiness_status,
                "recommended_next_action": "IMPLEMENT_MV08_TRAINER",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
