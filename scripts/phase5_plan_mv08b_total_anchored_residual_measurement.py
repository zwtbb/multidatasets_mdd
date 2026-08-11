#!/usr/bin/env python3
"""Predeclare the MV08b total-anchored residual measurement revision.

This is a design contract, not a trainer. It responds to the negative MV08
error analysis by changing the measurement mechanism: predict scale severity
first, then model item residual structure only after severity is controlled.
It reads existing aggregate Phase 5 artifacts and Phase 4 ontology tables, and
exports only versionable planning artifacts.
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
PHASE4_DIR = ROOT / "analysis" / "phase4_symptom_ontology"
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
MV08_DIR = PHASE5_DIR / "p5_mv08_partial_invariance_measurement"
MV08_ERROR_DIR = PHASE5_DIR / "p5_mv08_error_analysis"
MV08_DESIGN_DIR = PHASE5_DIR / "p5_mv08_partial_invariance_measurement_design"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv08b_total_anchored_residual_measurement_design"

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "design_decision_gate.csv",
    "implementation_queue.csv",
    "method_source_refs.csv",
    "model_ladder_contract.csv",
    "report.md",
    "residual_target_contract.csv",
    "run_summary.json",
    "source_evidence_summary.csv",
    "threshold_policy_contract.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "graded_response_model",
        "url": "https://www.stata.com/manuals/irtirtgrm.pdf",
        "source_type": "official_software_manual",
        "use_in_mv08b": "Use ordered response logic for item scores while avoiding independently fitted sparse thresholds.",
        "key_takeaway": "A graded response model represents ordinal items with discrimination and ordered cutpoints.",
    },
    {
        "source_id": "differential_item_functioning",
        "url": "https://www.publichealth.columbia.edu/research/population-health-methods/differential-item-functioning",
        "source_type": "method_overview",
        "use_in_mv08b": "Frame scale and dataset item residual differences as predeclared DIF rather than hidden nuisance effects.",
        "key_takeaway": "DIF asks whether item behavior differs across groups after matching on the measured construct.",
    },
    {
        "source_id": "ordinal_measurement_invariance",
        "url": "https://doi.org/10.1007/s11336-016-9506-0",
        "source_type": "method_paper",
        "use_in_mv08b": "Keep ordinal threshold constraints explicit and avoid treating item-category sparsity as free evidence.",
        "key_takeaway": "Ordered-categorical invariance requires careful treatment of thresholds, loadings, and intercept-like constraints.",
    },
    {
        "source_id": "phq_hamd_irt_linking",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "source_type": "scale_linking_paper",
        "use_in_mv08b": "Use PHQ and HAMD cross-scale IRT evidence as motivation for bounded scale-linking, not as proof that the local datasets share one representation.",
        "key_takeaway": "PHQ and HAMD items can be studied through latent severity, but scale-specific measurement behavior remains important.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def safe_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if clean_value(value):
            return value
    return None


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def first_row(frame: pd.DataFrame, **filters: str) -> dict[str, Any]:
    selected = frame.copy()
    for column, value in filters.items():
        if column not in selected.columns:
            return {}
        selected = selected[selected[column].astype(str) == str(value)]
    if selected.empty:
        return {}
    return selected.iloc[0].to_dict()


def source_evidence_summary() -> pd.DataFrame:
    mv08 = read_json(MV08_DIR / "run_summary.json")
    mv08_error = read_json(MV08_ERROR_DIR / "run_summary.json")
    slice_errors = read_csv(MV08_ERROR_DIR / "slice_error_diagnostics.csv")
    item_errors = read_csv(MV08_ERROR_DIR / "item_error_diagnostics.csv")
    threshold_errors = read_csv(MV08_ERROR_DIR / "threshold_sparsity_diagnostics.csv")
    revision_queue = read_csv(MV08_ERROR_DIR / "revision_queue.csv")

    verdict = mv08.get("verdict") or {}
    decision = mv08_error.get("decision") or {}
    top_item = item_errors.sort_values("m2_delta_mae_vs_total_floor", ascending=False).iloc[0].to_dict()
    top_threshold = threshold_errors.sort_values("constant_threshold_fraction", ascending=False).iloc[0].to_dict()
    top_revision = revision_queue.sort_values("priority").iloc[0].to_dict()

    rows = [
        {
            "source_id": "MV08_result",
            "artifact": rel(MV08_DIR / "run_summary.json"),
            "current_observation": (
                f"status={verdict.get('pass_rule_status')}; "
                f"m2_improved_vs_total_slices={verdict.get('pooled_m2_improved_vs_total_score_floor_slices')}; "
                f"prediction_identity_ba_m2={fmt(verdict.get('prediction_identity_ba_m2'))}"
            ),
            "implication_for_mv08b": "Do not continue the original M2 as positive RQ1 evidence; any revision must change the mechanism and keep identity from increasing.",
        },
        {
            "source_id": "MV08_error_gate",
            "artifact": rel(MV08_ERROR_DIR / "run_summary.json"),
            "current_observation": (
                f"failed_total_floor_slices={decision.get('pooled_slices_failed_total_floor')}; "
                f"failed_fixed_map_slices={decision.get('pooled_slices_failed_fixed_map')}; "
                f"worst_delta_vs_total={fmt(decision.get('worst_pooled_delta_vs_total_floor'))}"
            ),
            "implication_for_mv08b": "Total-score and fixed-map floors stay mandatory comparators; MV08b cannot pass through pooled-only averaging.",
        },
        {
            "source_id": "largest_item_error",
            "artifact": rel(MV08_ERROR_DIR / "item_error_diagnostics.csv"),
            "current_observation": (
                f"dataset={top_item.get('eval_dataset')};scale={top_item.get('scale')};"
                f"item={top_item.get('item_code')};construct={top_item.get('construct_id')};"
                f"delta_vs_total={fmt(top_item.get('m2_delta_mae_vs_total_floor'))};"
                f"bias={fmt(top_item.get('m2_bias_mean'))}"
            ),
            "implication_for_mv08b": "Model residuals after severity anchoring so item-specific overprediction cannot masquerade as shared latent symptom signal.",
        },
        {
            "source_id": "threshold_sparsity",
            "artifact": rel(MV08_ERROR_DIR / "threshold_sparsity_diagnostics.csv"),
            "current_observation": (
                f"protocol={top_threshold.get('protocol')};dif_policy={top_threshold.get('dif_policy')};"
                f"constant_threshold_fraction={fmt(top_threshold.get('constant_threshold_fraction'))}"
            ),
            "implication_for_mv08b": "Pool thresholds or collapse rare ordinal levels before allowing scale/item-specific threshold deviations.",
        },
        {
            "source_id": "revision_queue_top_action",
            "artifact": rel(MV08_ERROR_DIR / "revision_queue.csv"),
            "current_observation": f"priority={top_revision.get('priority')};action={top_revision.get('action_id')}",
            "implication_for_mv08b": "Freeze current MV08 as negative unless the predeclared MV08b mechanism is implemented and independently beats its gates.",
        },
    ]
    for dataset in ["edaic", "cmdc", "pdch"]:
        row = first_row(slice_errors, protocol="pooled_partial_invariance", eval_dataset=dataset)
        if not row:
            row = first_row(slice_errors, eval_dataset=dataset)
        if row:
            rows.append(
                {
                    "source_id": f"pooled_slice_{dataset}",
                    "artifact": rel(MV08_ERROR_DIR / "slice_error_diagnostics.csv"),
                    "current_observation": (
                        f"scale={row.get('scale')};m2_mae={fmt(first_present(row, ['m2_row_weighted_mae', 'm2_partial_invariance_mae']))};"
                        f"delta_vs_total={fmt(row.get('m2_delta_mae_vs_total_floor'))};"
                        f"delta_vs_fixed={fmt(row.get('m2_delta_mae_vs_fixed_map'))};"
                        f"bias={fmt(row.get('m2_bias_mean'))}"
                    ),
                    "implication_for_mv08b": "Require dataset-stratified success, not only a pooled average.",
                }
            )
    return pd.DataFrame(rows)


def model_ladder_contract() -> pd.DataFrame:
    rows = [
        {
            "model_id": "B0_train_mean_items",
            "model_family": "baseline",
            "severity_anchor": "none",
            "item_residual_component": "none",
            "threshold_policy": "none",
            "comparison_role": "sanity_floor",
            "pass_gate": "MV08b must beat this floor on active item and item-derived-total summaries.",
        },
        {
            "model_id": "B1_total_score_floor",
            "model_family": "baseline",
            "severity_anchor": "train_fold_total_score_model_or_total_allocation",
            "item_residual_component": "none",
            "threshold_policy": "scale_specific_total_allocation_only",
            "comparison_role": "primary_floor",
            "pass_gate": "MV08b must beat this floor on at least two pooled active dataset slices.",
        },
        {
            "model_id": "B2_fixed_construct_map",
            "model_family": "baseline",
            "severity_anchor": "same_as_B1_where_available",
            "item_residual_component": "phase4_fixed_item_map_without_learned_DIF",
            "threshold_policy": "fixed_map_item_rounding_or_fold_thresholds",
            "comparison_role": "old_shared_mapping_floor",
            "pass_gate": "MV08b must beat or narrowly match this floor while reducing interpretable item errors.",
        },
        {
            "model_id": "M2b_total_anchored_residual_measurement",
            "model_family": "target_mv08b",
            "severity_anchor": "predeclared_train_fold_anchor_predicts_total_or_latent_severity_first",
            "item_residual_component": "sparse_construct_residual_heads_fit_only_on_item_deviation_after_anchor",
            "threshold_policy": "pooled_or_collapsed_thresholds_before_any_scale_item_specific_offsets",
            "comparison_role": "next_executable_RQ1_candidate",
            "pass_gate": "Beat B1 and B2 on at least two pooled active slices and keep prediction identity BA <= current MV08 M2 identity.",
        },
        {
            "model_id": "M2b_HAMD_external_stress",
            "model_family": "target_mv08b_stress",
            "severity_anchor": "PDCH_HAMD_total_anchor_only",
            "item_residual_component": "HAMD residual heads separate from PHQ shared-core pass decision",
            "threshold_policy": "HAMD-specific collapsed thresholds when sparse",
            "comparison_role": "clinical_measurement_stress_test",
            "pass_gate": "HAMD must improve PDCH item and item-derived total metrics beyond floors before any HAMD-compatible claim.",
        },
    ]
    return pd.DataFrame(rows)


def residual_target_contract(anchors: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    active = coverage[coverage["active_in_mv08"].astype(str).str.lower().isin({"true", "1", "yes"})]
    active_pairs = [f"{row['dataset']}:{row['scale']}" for _, row in active.iterrows()]
    for _, row in anchors.iterrows():
        construct_id = clean_value(row.get("construct_id"))
        if not construct_id:
            continue
        role = clean_value(row.get("mv08_anchor_role"))
        if construct_id in {f"C{i:02d}" for i in range(1, 9)}:
            residual_role = "shared_phq_core_residual"
            allowed_residual = "allow_small_sparse_item_residual_after_total_anchor"
            exclusion_rule = "do_not_let_residual_head_reconstruct_total_severity"
        elif construct_id == "C09":
            residual_role = "explicit_safety_residual"
            allowed_residual = "PHQ9_HAMD_explicit_evidence_only_no_imputation_from_total"
            exclusion_rule = "no_PHQ8_pseudo_item_and_no_local_snippet_export"
        elif "hamd" in role:
            residual_role = "hamd_auxiliary_residual"
            allowed_residual = "HAMD_scale_specific_residual_only_after_PDCH_total_anchor"
            exclusion_rule = "excluded_from_shared_PHQ_core_pass_count"
        else:
            residual_role = "inactive_or_total_only"
            allowed_residual = "not_active_in_mv08b"
            exclusion_rule = "do_not_train_item_residual_without_item_supervision"
        rows.append(
            {
                "construct_id": construct_id,
                "construct_label": clean_value(row.get("construct_label")),
                "mv08_anchor_role": role,
                "mv08b_residual_role": residual_role,
                "active_dataset_scales": ";".join(active_pairs),
                "allowed_residual": allowed_residual,
                "exclusion_rule": exclusion_rule,
            }
        )
    return pd.DataFrame(rows)


def threshold_policy_contract() -> pd.DataFrame:
    rows = [
        {
            "policy_id": "T0_observed_score_support",
            "trigger": "before_training",
            "rule": "measure per-item observed category counts inside train folds",
            "pass_condition": "no item-specific threshold is estimated for a category with insufficient train-fold support",
            "tracked_output": "aggregate category-support and collapse counts only",
        },
        {
            "policy_id": "T1_collapse_sparse_categories",
            "trigger": "rare_or_empty_ordinal_levels",
            "rule": "collapse adjacent high or low categories by predeclared scale-specific rules before threshold fitting",
            "pass_condition": "constant-threshold fraction is lower than current MV08 and rounded-within-one does not degrade materially",
            "tracked_output": "threshold_sparsity_summary.csv aggregate only",
        },
        {
            "policy_id": "T2_pool_thresholds_first",
            "trigger": "default_MV08b",
            "rule": "fit pooled thresholds by scale and construct before freeing item-specific offsets",
            "pass_condition": "item residual heads improve beyond B1/B2 without diffuse threshold freeing",
            "tracked_output": "aggregate freed-threshold counts by scale/construct",
        },
        {
            "policy_id": "T3_free_offsets_only_after_error_trigger",
            "trigger": "large_train_fold_residual_error_with_stable_support",
            "rule": "allow a scale/item-specific threshold offset only for predeclared high-error items",
            "pass_condition": "offsets remain sparse and interpretable; no post-hoc broad freeing",
            "tracked_output": "aggregate DIF sparsity by dataset/scale/construct",
        },
    ]
    return pd.DataFrame(rows)


def design_decision_gate(evidence: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {
            "gate_id": "G_MECHANISM_CHANGED",
            "status": "pass",
            "evidence": "MV08b predicts total severity first and models item residuals only after anchoring.",
            "required_next": "Implement B0/B1/B2/M2b in one script with subject-level folds.",
        },
        {
            "gate_id": "G_TOTAL_FLOOR_PRIMARY",
            "status": "pass",
            "evidence": "MV08 error analysis shows total-score floors are best or near-best across active slices.",
            "required_next": "B1_total_score_floor remains the primary pass/fail comparator.",
        },
        {
            "gate_id": "G_THRESHOLD_SPARSITY_ADDRESSED",
            "status": "pass",
            "evidence": "MV08b predeclares category-support checks, category collapse, and pooled thresholds.",
            "required_next": "Do not export learned thresholds; export only aggregate sparsity diagnostics.",
        },
        {
            "gate_id": "G_HAMD_SEPARATE_STRESS",
            "status": "pass_limited",
            "evidence": "PDCH HAMD remains the only adequately sized HAMD item source; CMDC HAMD is sanity-only.",
            "required_next": "Do not count HAMD success as a PHQ shared-core pass unless PHQ slices also pass.",
        },
        {
            "gate_id": "G_NO_FULL_METHOD_AUTHORIZATION",
            "status": "blocked_full_method",
            "evidence": "MV08b design is a minimal-validation contract, not a full M0/M1/M2/M3 start.",
            "required_next": "Run and gate MV08b before changing full-method authorization.",
        },
    ]
    if evidence.empty:
        rows[0]["status"] = "blocked"
        rows[0]["evidence"] = "Missing MV08 aggregate evidence."
    return pd.DataFrame(rows)


def implementation_queue() -> pd.DataFrame:
    rows = [
        {
            "rank": 1,
            "action_id": "IMPLEMENT_MV08B_RUNNER",
            "action": "Create scripts/phase5_run_mv08b_total_anchored_residual_measurement.py.",
            "success_gate": "One run compares B0 train mean, B1 total floor, B2 fixed map, and M2b total-anchored residual heads on the same subject-level slices.",
            "version_policy": "Track script and aggregate summaries only; keep residual predictions, latent scores, fitted thresholds, and model files local-only.",
        },
        {
            "rank": 2,
            "action_id": "ADD_FOLD_LOCAL_PREDICTION_EXPORT",
            "action": "Write row-level residual predictions only to an ignored local file for later aggregate error analysis.",
            "success_gate": "Tracked artifacts contain no subject-level rows, raw text, local locators, or learned parameters.",
            "version_policy": "Ignored local-only CSV; never force-add without a separate deidentification review.",
        },
        {
            "rank": 3,
            "action_id": "RUN_MV08B_AND_REFRESH_GATE",
            "action": "Run MV08b and rerun scripts/phase5_full_method_gate_audit.py.",
            "success_gate": "Full-method gate changes only if MV08b beats B1/B2 on at least two pooled active slices and identity does not increase.",
            "version_policy": "Commit aggregate run summaries, reports, and gate outputs only.",
        },
        {
            "rank": 4,
            "action_id": "FREEZE_IF_MV08B_FAILS",
            "action": "If MV08b fails, freeze MV08/MV08b as negative RQ1 diagnostic evidence and pivot writing.",
            "success_gate": "Issue log and master plan explicitly state the bounded diagnostic claim.",
            "version_policy": "Track the decision and aggregate evidence; no extra shallow retuning loop.",
        },
    ]
    return pd.DataFrame(rows)


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
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
        "audit_id": "P5_MV08b_total_anchored_residual_measurement_design_hygiene",
        "artifact_hygiene_passed": len(violations) == 0,
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    evidence: pd.DataFrame,
    models: pd.DataFrame,
    residuals: pd.DataFrame,
    thresholds: pd.DataFrame,
    gate: pd.DataFrame,
    queue: pd.DataFrame,
) -> None:
    lines = [
        "# P5_MV08b Total-Anchored Residual Measurement Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This design predeclares one mechanism-changing revision after the negative MV08 pilot. It does not train a model, read raw text, export row-level predictions, or authorize full-method construction.",
        "",
        "## Decision",
        "",
        f"- Readiness status: `{run_summary['decision']['readiness_status']}`.",
        f"- Recommended next action: `{run_summary['decision']['recommended_next_action']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Why MV08b Is Not A Retune",
        "",
        "MV08 let lightweight item heads reconstruct ordinal item scores directly. MV08b first anchors scale severity, then asks whether item residuals add transferable construct information after that severity is controlled. If the residual layer cannot beat the total-score floor, the RQ1 result stays negative.",
        "",
        "## Source Evidence",
        "",
        "| source | observation | implication |",
        "| --- | --- | --- |",
    ]
    for _, row in evidence.iterrows():
        lines.append(f"| {row['source_id']} | {row['current_observation']} | {row['implication_for_mv08b']} |")

    lines.extend(
        [
            "",
            "## Model Ladder",
            "",
            "| model | role | severity anchor | residual component | pass gate |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in models.iterrows():
        lines.append(
            f"| {row['model_id']} | {row['comparison_role']} | {row['severity_anchor']} | "
            f"{row['item_residual_component']} | {row['pass_gate']} |"
        )

    shared = residuals[residuals["mv08b_residual_role"].astype(str).isin(["shared_phq_core_residual", "explicit_safety_residual"])]
    lines.extend(
        [
            "",
            "## Residual Targets",
            "",
            "| construct | role | allowed residual | exclusion rule |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in shared.iterrows():
        lines.append(
            f"| {row['construct_id']} | {row['mv08b_residual_role']} | {row['allowed_residual']} | {row['exclusion_rule']} |"
        )

    lines.extend(
        [
            "",
            "## Threshold Policy",
            "",
            "| policy | trigger | rule | pass condition |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in thresholds.iterrows():
        lines.append(f"| {row['policy_id']} | {row['trigger']} | {row['rule']} | {row['pass_condition']} |")

    lines.extend(
        [
            "",
            "## Design Gate",
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
            "- MV08b is allowed only as a minimal-validation revision; full M0/M1/M2/M3 construction remains blocked.",
            "- The current MV08 result remains negative unless MV08b independently passes its predeclared gates.",
            "- Any residual or DIF finding must be reported as measurement heterogeneity, not as proof of one dataset-invariant depression representation.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists():
        if not args.overwrite:
            raise SystemExit(f"output directory exists; use --overwrite: {rel(out_dir)}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = utc_now()
    coverage = read_csv(MV08_DESIGN_DIR / "label_contract_coverage.csv")
    anchors = read_csv(MV08_DESIGN_DIR / "construct_anchor_matrix.csv")
    evidence = source_evidence_summary()
    models = model_ladder_contract()
    residuals = residual_target_contract(anchors, coverage)
    thresholds = threshold_policy_contract()
    gate = design_decision_gate(evidence)
    queue = implementation_queue()
    refs = pd.DataFrame(METHOD_SOURCE_REFS)

    evidence.to_csv(out_dir / "source_evidence_summary.csv", index=False)
    models.to_csv(out_dir / "model_ladder_contract.csv", index=False)
    residuals.to_csv(out_dir / "residual_target_contract.csv", index=False)
    thresholds.to_csv(out_dir / "threshold_policy_contract.csv", index=False)
    gate.to_csv(out_dir / "design_decision_gate.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    readiness_status = (
        "ready_to_implement_mv08b_total_anchored_residual_measurement"
        if set(gate["status"]).issuperset({"pass", "pass_limited", "blocked_full_method"})
        else "blocked_missing_mv08_evidence"
    )
    run_summary = {
        "run_id": "P5_MV08b_total_anchored_residual_measurement_design",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "design_readiness_no_training_after_negative_mv08",
        "input_contract": {
            "phase4_design_artifacts_read": True,
            "mv08_aggregate_artifacts_read": True,
            "raw_data_scanned": False,
            "raw_text_read": False,
            "row_level_predictions_read": False,
        },
        "decision": {
            "readiness_status": readiness_status,
            "recommended_next_action": "IMPLEMENT_MV08B_RUNNER",
            "short_read": (
                "MV08b is predeclared as a total-anchored residual measurement revision: predict severity first, model item residuals only after anchoring, pool or collapse sparse thresholds, and keep HAMD as a separate clinical stress test. Full-method work remains blocked until MV08b is run and passes."
            ),
            "current_mv08_frozen_as_negative_unless_mv08b_passes": True,
            "full_method_authorized": False,
        },
        "source_evidence_rows": int(len(evidence)),
        "model_contract_rows": int(len(models)),
        "residual_target_rows": int(len(residuals)),
        "threshold_policy_rows": int(len(thresholds)),
        "design_gate_rows": int(len(gate)),
        "source_ref_rows": int(len(refs)),
        "pass_rule": {
            "primary_floor": "B1_total_score_floor",
            "secondary_floor": "B2_fixed_construct_map",
            "minimum_pooled_active_slices_beating_both_floors": 2,
            "prediction_identity_ba_must_not_exceed_current_mv08_m2": True,
            "hamd_success_separate_from_phq_shared_core": True,
        },
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
    write_report(out_dir, run_summary, evidence, models, residuals, thresholds, gate, queue)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, evidence, models, residuals, thresholds, gate, queue)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")

    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "readiness_status": readiness_status,
                "recommended_next_action": "IMPLEMENT_MV08B_RUNNER",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
