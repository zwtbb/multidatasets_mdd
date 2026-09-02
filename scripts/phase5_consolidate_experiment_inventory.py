#!/usr/bin/env python3
"""Consolidate Phase 5 experiment evidence and cleanup decisions.

This is an orchestration script. It does not train models, inspect raw data, or
delete files. It reads the current full-method evidence inventory and writes a
small, versionable consolidation layer that says which experiments remain paper
core evidence, which are supporting diagnostics, which are retained only as
predeclared contracts, and which local ignored artifacts should stay local.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
GATE_INVENTORY = PHASE5_DIR / "full_method_gate_audit" / "evidence_inventory.csv"
OUT_DIR = PHASE5_DIR / "experiment_consolidation"


PAPER_CORE = {
    "P5_MV10",
    "P5_MV11",
    "P5_MV13",
    "P5_MV14",
    "P5_MV19",
    "P5_MV21",
}

PAPER_SUPPORT = {
    "P5_MV02",
    "P5_MV04c",
    "P5_MV06_summary",
    "P5_MV09",
    "P5_MV12",
    "P5_MV12_analysis",
    "P5_MV15",
    "P5_MV16",
    "P5_MV17a",
    "P5_MV18",
    "P5_MV20",
}

PAPER_GUARDRAIL = {
    "P5_mirt_parameterization_audit",
}

HISTORICAL_DIAGNOSTIC = {
    "P5_MV01",
    "P5_MV02b",
    "P5_MV03",
    "P5_MV03b",
    "P5_MV04",
    "P5_MV04b",
    "P5_MV05",
    "P5_MV07",
    "P5_MV07b",
    "P5_MV07c",
    "P5_MV08",
    "P5_MV08_error_analysis",
    "P5_MV08b",
}

PREDECLARATION_CONTRACT = {
    "P5_MV02_readiness",
    "P5_MV07_readiness",
    "P5_MV08_design",
    "P5_MV08b_design",
    "P5_MV12_design",
    "P5_MV13_design",
    "P5_MV14_design",
    "P5_MV15_design",
    "P5_MV16_design",
}

LOCAL_WORKFLOW = {
    "P5_MV06_readiness",
    "P5_MV06_pilot",
    "P5_MV06_workbench",
    "P5_MV06_ai_preannotation",
    "P5_MV06_review_pack",
    "P5_MV07_edaic_bge_generation",
}

MERGE_BUCKET = {
    "P5_MV10": "phq_label_only_psychometrics",
    "P5_MV11": "phq_label_only_psychometrics",
    "P5_MV13": "phq_label_only_psychometrics",
    "P5_MV14": "phq_label_only_psychometrics",
    "P5_MV19": "phq_label_only_psychometrics",
    "P5_MV21": "measurement_discrepancy_gradient_controls",
    "P5_MV12": "latent_target_negative_chain",
    "P5_MV12_analysis": "latent_target_negative_chain",
    "P5_MV15": "latent_target_negative_chain",
    "P5_MV16": "latent_target_negative_chain",
    "P5_MV17a": "feature_contract_sensitivity",
    "P5_MV18": "same_scale_hamd_context_control",
    "P5_MV20": "criterion_overlap_contamination_stress",
    "P5_MV22": "foundation_backbone_stress_test",
    "P5_MV23": "foundation_multimodal_completion_stress_test",
    "P5_MV06_summary": "evidence_localization_credibility",
    "P5_MV02": "bounded_hamd_internal_diagnostic",
    "P5_MV04c": "protocol_task_control_support",
    "P5_MV09": "conditional_identity_gate",
    "P5_mirt_parameterization_audit": "psychometric_parameterization_guardrail",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def run_git_status_ignored() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--ignored"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return [line[3:] for line in result.stdout.splitlines() if line.startswith("!! ")]


def read_gate_inventory() -> pd.DataFrame:
    if not GATE_INVENTORY.exists():
        raise FileNotFoundError(f"run phase5_full_method_gate_audit.py first: {GATE_INVENTORY}")
    df = pd.read_csv(GATE_INVENTORY)
    missing = (
        set(df["evidence_id"])
        - PAPER_CORE
        - PAPER_SUPPORT
        - PAPER_GUARDRAIL
        - HISTORICAL_DIAGNOSTIC
        - PREDECLARATION_CONTRACT
        - LOCAL_WORKFLOW
    )
    if missing:
        raise ValueError(f"consolidation rules missing evidence ids: {sorted(missing)}")
    return df


def decision_for(evidence_id: str) -> dict[str, Any]:
    if evidence_id in PAPER_CORE:
        manuscript_role = "main psychometric measurement-validity evidence"
        if evidence_id in {"P5_MV13", "P5_MV14"}:
            manuscript_role = "corrected anchor-linked mirt corroboration with convergence and finite-sample caveats"
        if evidence_id == "P5_MV21":
            manuscript_role = "descriptive measurement-discrepancy gradient and same-scale controls; not formal HAMD MIM/IRT"
        return {
            "evidence_bundle": "paper_core",
            "retention_decision": "keep_primary_aggregate",
            "merge_bucket": MERGE_BUCKET[evidence_id],
            "manuscript_role": manuscript_role,
            "new_runs_allowed": False,
            "tracked_deletion_allowed": False,
            "physical_cleanup": "keep tracked aggregate outputs; keep local-only detailed artifacts ignored",
        }
    if evidence_id in PAPER_SUPPORT:
        return {
            "evidence_bundle": "paper_support",
            "retention_decision": "keep_supporting_aggregate",
            "merge_bucket": MERGE_BUCKET[evidence_id],
            "manuscript_role": "bounded diagnostic support or negative control",
            "new_runs_allowed": False,
            "tracked_deletion_allowed": False,
            "physical_cleanup": "keep tracked aggregate outputs; keep local-only detailed artifacts ignored",
        }
    if evidence_id in PAPER_GUARDRAIL:
        return {
            "evidence_bundle": "paper_guardrail",
            "retention_decision": "keep_claim_boundary_audit",
            "merge_bucket": MERGE_BUCKET[evidence_id],
            "manuscript_role": "statistical correctness boundary for mirt-backed psychometric wording",
            "new_runs_allowed": False,
            "tracked_deletion_allowed": False,
            "physical_cleanup": "keep tracked aggregate audit outputs; keep any detailed mirt artifacts local-only",
        }
    if evidence_id in HISTORICAL_DIAGNOSTIC:
        return {
            "evidence_bundle": "retired_historical",
            "retention_decision": "freeze_no_new_iterations",
            "merge_bucket": "historical_minimal_validation_background",
            "manuscript_role": "brief negative background only when needed",
            "new_runs_allowed": False,
            "tracked_deletion_allowed": False,
            "physical_cleanup": "retain lightweight aggregate traceability; do not feature in main narrative",
        }
    if evidence_id in PREDECLARATION_CONTRACT:
        return {
            "evidence_bundle": "predeclaration_contract",
            "retention_decision": "keep_as_protocol_contract_consumed_by_run",
            "merge_bucket": "predeclared_design_contracts",
            "manuscript_role": "methods traceability, not standalone result",
            "new_runs_allowed": False,
            "tracked_deletion_allowed": False,
            "physical_cleanup": "retain tracked contracts because they prove predeclaration before results",
        }
    if evidence_id in LOCAL_WORKFLOW:
        return {
            "evidence_bundle": "local_workflow",
            "retention_decision": "keep_workflow_boundary",
            "merge_bucket": "local_review_or_feature_generation_workflow",
            "manuscript_role": "local-only workflow boundary; cite only aggregate summary rows",
            "new_runs_allowed": False,
            "tracked_deletion_allowed": False,
            "physical_cleanup": "retain tracked schema/hygiene summaries; keep workbooks/features local-only",
        }
    raise AssertionError(evidence_id)


def build_inventory(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        decision = decision_for(str(row["evidence_id"]))
        rows.append(
            {
                **row,
                **decision,
                "paper_active": decision["evidence_bundle"] in {"paper_core", "paper_support", "paper_guardrail"},
                "cleanup_rationale": cleanup_rationale(str(row["evidence_id"]), decision["evidence_bundle"]),
            }
        )
    extra = {
        "evidence_id": "P5_MV17_route",
        "artifact": "analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/run_summary.json",
        "status": "complete",
        "pass_rule_status": "mv17a_mv18_mv19_mv20_mv21_complete_next_manuscript_finalization",
        "pass_rule_met": "",
        "artifact_hygiene_passed": True,
        "artifact_hygiene_violation_count": 0,
        "local_only_files": "",
        "short_read": "Post-review triage route is complete through MV17a/MV18/MV19/MV20 plus user-directed MV21; experiments are frozen and next work is manuscript finalization.",
        "evidence_bundle": "planning_route",
        "retention_decision": "keep_current_route",
        "merge_bucket": "postreview_orchestration",
        "manuscript_role": "orchestration handoff, not a paper result",
        "new_runs_allowed": False,
        "tracked_deletion_allowed": False,
        "physical_cleanup": "retain because it records the completed MV21 reinforcement line and final manuscript boundary",
        "paper_active": False,
        "cleanup_rationale": "Current route prevents accidental return to redundant model iteration.",
    }
    rows.append(extra)
    mv22 = {
        "evidence_id": "P5_MV22",
        "artifact": "analysis/phase5_minimal_validation/p5_mv22_foundation_backbone_validation/run_summary.json",
        "status": "complete",
        "pass_rule_status": "complete_foundation_backbone_stress_test_gates_remain_visible",
        "pass_rule_met": "",
        "artifact_hygiene_passed": True,
        "artifact_hygiene_violation_count": 0,
        "local_only_files": "qwen_subject_feature_caches;downstream_prediction_outputs",
        "short_read": "Qwen3-Embedding-0.6B reruns MV07/MV12/MV15 and remains blocked on feature identity/observed-scale gates; lightweight ERM/CORAL/MMD/DANN/IRM/GroupDRO-style baselines and WavLM audio proxy coverage are aggregate-only.",
        "evidence_bundle": "paper_support",
        "retention_decision": "keep_supporting_aggregate",
        "merge_bucket": MERGE_BUCKET["P5_MV22"],
        "manuscript_role": "foundation-backbone stress test for the measurement-aware framework; not a SOTA or full-method success claim",
        "new_runs_allowed": False,
        "tracked_deletion_allowed": False,
        "physical_cleanup": "keep tracked aggregate outputs; keep Qwen feature caches and downstream predictions local-only/ignored",
        "paper_active": True,
        "cleanup_rationale": "Closes the immediate foundation-model validation gap while preserving the blocked full-method gate.",
    }
    rows.append(mv22)
    mv23 = {
        "evidence_id": "P5_MV23",
        "artifact": "analysis/phase5_minimal_validation/p5_mv23_foundation_multimodal_completion/run_summary.json",
        "status": "complete",
        "pass_rule_status": "complete_lightweight_foundation_multimodal_stress_test",
        "pass_rule_met": "",
        "artifact_hygiene_passed": True,
        "artifact_hygiene_violation_count": 0,
        "local_only_files": "reused_phase2_feature_caches;no_row_predictions_written",
        "short_read": "Eight audio, video-proxy, text-audio, and text-audio-video feature views are evaluated on E-DAIC/CMDC PHQ shared-item transfer with ERM/CORAL/MMD/DANN/IRM/GroupDRO-style baselines plus a lightweight measurement-aware latent-total proxy head.",
        "evidence_bundle": "paper_support",
        "retention_decision": "keep_supporting_aggregate",
        "merge_bucket": MERGE_BUCKET["P5_MV23"],
        "manuscript_role": "lightweight multimodal foundation completion stress test; not WavLM Large, VideoMAE, or end-to-end multimodal success",
        "new_runs_allowed": False,
        "tracked_deletion_allowed": False,
        "physical_cleanup": "keep tracked aggregate outputs; input feature caches remain local-only/ignored",
        "paper_active": True,
        "cleanup_rationale": "Closes the practical multimodal baseline gap while preserving the bounded framework claim.",
    }
    rows.append(mv23)
    return pd.DataFrame(rows)


def cleanup_rationale(evidence_id: str, bundle: str) -> str:
    if bundle == "paper_core":
        return "Core evidence for the measurement-validity claim; do not delete aggregate outputs."
    if bundle == "paper_support":
        return "Supports bounded controls, negative consequences, or exploratory context checks; keep but avoid new iterations."
    if bundle == "retired_historical":
        return "The result is superseded or negative; retain aggregate traceability but remove from the active experiment queue."
    if bundle == "predeclaration_contract":
        return "Design/readiness output is consumed by later runs; keep for preregistration-style traceability."
    return "Workflow artifact defines local-only or feature-generation boundaries; tracked summary stays, private data stays local."


def category_for_ignored(path: str) -> tuple[str, str, bool, bool]:
    if "__pycache__" in path or path.endswith(".pyc"):
        return ("python_bytecode_cache", "delete_if_present", True, False)
    if ".ipynb_checkpoints" in path:
        return ("notebook_checkpoint_cache", "delete_if_present", True, False)
    if path.startswith("analysis/phase2_baselines/"):
        return ("phase2_local_results", "keep_local_for_baseline_rebuild_or_manual_purge_after_archive", False, True)
    if path.startswith("datasets/"):
        return ("local_dataset_or_manifest", "keep_local_governed_data", False, False)
    if "local_annotation_workbook" in path or "human_review" in path:
        return ("mv06_local_human_review_files", "keep_local_until_mv06_candidate_resolved", False, False)
    if "predictions" in path:
        return ("local_row_predictions", "keep_local_for_recompute_or_delete_only_after confirming summaries are enough", False, True)
    if "features" in path or "embeddings" in path:
        return ("local_features_or_embeddings", "keep_local_for_recompute_or_delete_only_if storage constrained", False, True)
    if path.startswith("cache/"):
        return ("external_code_or_model_cache", "keep_local_environment_cache_unless storage cleanup requested", False, True)
    if path in {".autodl/", ".Trash-0/"} or path.startswith(".autodl/") or path.startswith(".Trash-0/"):
        return ("environment_local_files", "ask_before_delete_environment_files", False, True)
    if path == "untitled.md":
        return ("local_original_plan_note", "keep_or_manually_archive_after confirming master plan fully absorbs it", False, True)
    return ("other_ignored_local", "review_before_delete", False, True)


def build_local_cleanup_inventory() -> pd.DataFrame:
    grouped: dict[str, dict[str, Any]] = {}
    for path in run_git_status_ignored():
        category, action, safe_delete, needs_approval = category_for_ignored(path)
        entry = grouped.setdefault(
            category,
            {
                "local_category": category,
                "ignored_path_count": 0,
                "recommended_action": action,
                "safe_to_delete_without_user_input": safe_delete,
                "needs_user_approval": needs_approval,
                "example_ignored_paths": [],
            },
        )
        entry["ignored_path_count"] += 1
        examples = entry["example_ignored_paths"]
        if len(examples) < 5 and category not in {"local_dataset_or_manifest", "environment_local_files"}:
            examples.append(redact_ignored_path(path, category))
    rows = []
    for entry in grouped.values():
        entry["example_ignored_paths"] = ";".join(entry["example_ignored_paths"])
        rows.append(entry)
    return pd.DataFrame(rows).sort_values(["safe_to_delete_without_user_input", "local_category"], ascending=[False, True])


def redact_ignored_path(path: str, category: str) -> str:
    if category == "mv06_local_human_review_files":
        return "analysis/phase5_minimal_validation/p5_mv06_<local-review-file>"
    if category == "local_row_predictions":
        return "analysis/<local-row-prediction-artifact>"
    if category == "local_features_or_embeddings":
        return "analysis/<local-feature-or-embedding-artifact>"
    if category == "other_ignored_local":
        return "analysis/phase5_minimal_validation/<local-detail-artifact>"
    if path.startswith("datasets/"):
        return "datasets/<local-governed-data>"
    return path


def build_artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    banned = [
        re.compile(r"subject_id", re.IGNORECASE),
        re.compile(r"subject_key", re.IGNORECASE),
        re.compile(r"/root/autodl-tmp/datasets", re.IGNORECASE),
        re.compile(r"audio_path|video_path|text_path|gait_path", re.IGNORECASE),
        re.compile(r"raw prompt|raw response", re.IGNORECASE),
        re.compile(r"source_locator", re.IGNORECASE),
        re.compile(r"\b[0-9]{6,}@qq\.com\b|\b[a-z]{2,}[0-9]{6,}\.[0-9]+\b|github_pat_|ghp_", re.IGNORECASE),
    ]
    violations: list[dict[str, str]] = []
    for path in sorted(out_dir.glob("*")):
        if path.suffix.lower() not in {".csv", ".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in banned:
            if pattern.search(text):
                violations.append({"file": rel(path), "pattern": pattern.pattern})
    return {
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(inventory: pd.DataFrame, local_cleanup: pd.DataFrame, hygiene: dict[str, Any]) -> None:
    bundle_counts = inventory["evidence_bundle"].value_counts().sort_index()
    active = inventory[inventory["paper_active"]].copy()
    retired = inventory[inventory["evidence_bundle"].isin(["retired_historical", "predeclaration_contract", "local_workflow"])]
    delete_now = local_cleanup[local_cleanup["safe_to_delete_without_user_input"] == True]
    report = [
        "# Phase 5 Experiment Consolidation",
        "",
        f"Generated: {utc_now()}",
        "",
        "## Decision",
        "",
        "Do not physically delete tracked aggregate experiment outputs. They are small, versionable traceability records used by the full-method gate and manuscript claim boundary. Consolidate them by role instead:",
        "",
        "- Paper core: label-only PHQ psychometric evidence (`MV10/MV11/MV19` primary; `MV13/MV14` corrected anchor-linked mirt corroboration with convergence and finite-sample caveats) plus `MV21` descriptive measurement-gradient controls.",
        "- Paper support: bounded controls and negative consequences (`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20`).",
        "- Paper guardrail: mirt parameterization correctness audit, kept as a statistical wording boundary rather than a new experiment.",
        "- Retired historical: early weak or superseded minimal validations kept only as aggregate background.",
        "- Predeclaration contracts: design/readiness artifacts retained to prove that later runs were predeclared.",
        "- Local workflow: MV06 workbooks and feature-generation boundaries stay local-only; tracked outputs remain schemas/hygiene summaries.",
        "",
        "## Counts",
        "",
    ]
    for bundle, count in bundle_counts.items():
        report.append(f"- `{bundle}`: {count}")
    report.extend(
        [
            "",
            "## Active Evidence Bundle",
            "",
            "| Evidence ID | Merge bucket | Manuscript role |",
            "| --- | --- | --- |",
        ]
    )
    for row in active.sort_values(["evidence_bundle", "evidence_id"]).to_dict(orient="records"):
        report.append(f"| `{row['evidence_id']}` | `{row['merge_bucket']}` | {row['manuscript_role']} |")
    report.extend(
        [
            "",
            "## Retired Or Frozen Rows",
            "",
            f"{len(retired)} rows are retained for traceability but removed from the active experiment queue. They should not trigger new model iterations unless a new mechanism-changing contract is written first.",
            "",
            "## Local Cleanup Boundary",
            "",
        ]
    )
    if len(delete_now) == 0:
        report.append("No bytecode/notebook cache categories remain in the ignored working tree.")
    else:
        for row in delete_now.to_dict(orient="records"):
            report.append(f"- `{row['local_category']}`: {row['ignored_path_count']} ignored paths can be deleted without affecting evidence.")
    report.extend(
        [
            "",
            "Local predictions, features, raw datasets, Phase 2 local outputs, MV06 workbooks, and original plan notes are not deleted by this policy. They require user approval or a storage-specific cleanup request.",
            "",
            "## Hygiene",
            "",
            f"- `artifact_hygiene_passed`: `{hygiene['artifact_hygiene_passed']}`",
            f"- `violation_count`: `{hygiene['violation_count']}`",
        ]
    )
    (OUT_DIR / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gate = read_gate_inventory()
    inventory = build_inventory(gate)
    active = inventory[inventory["paper_active"]].copy()
    retired = inventory[inventory["evidence_bundle"].isin(["retired_historical", "predeclaration_contract", "local_workflow"])]
    local_cleanup = build_local_cleanup_inventory()

    inventory.to_csv(OUT_DIR / "experiment_consolidation_inventory.csv", index=False)
    active.to_csv(OUT_DIR / "active_evidence_bundle.csv", index=False)
    retired.to_csv(OUT_DIR / "retired_or_frozen_experiments.csv", index=False)
    local_cleanup.to_csv(OUT_DIR / "local_cleanup_inventory.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "source_inventory": rel(GATE_INVENTORY),
        "consolidation_status": "complete_active_bundle_defined",
        "experiment_rows": int(len(inventory)),
        "paper_active_rows": int(len(active)),
        "paper_core_rows": int((inventory["evidence_bundle"] == "paper_core").sum()),
        "paper_support_rows": int((inventory["evidence_bundle"] == "paper_support").sum()),
        "retired_or_frozen_rows": int(len(retired)),
        "tracked_experiment_deletion_allowed": False,
        "safe_delete_without_user_input_categories": sorted(
            local_cleanup.loc[local_cleanup["safe_to_delete_without_user_input"] == True, "local_category"].tolist()
        ),
        "requires_user_approval_categories": sorted(
            local_cleanup.loc[local_cleanup["needs_user_approval"] == True, "local_category"].tolist()
        ),
    }
    (OUT_DIR / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    hygiene = build_artifact_hygiene(OUT_DIR)
    (OUT_DIR / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2) + "\n", encoding="utf-8")
    write_report(inventory, local_cleanup, hygiene)
    hygiene = build_artifact_hygiene(OUT_DIR)
    (OUT_DIR / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"out_dir": rel(OUT_DIR), **summary, "artifact_hygiene_passed": hygiene["artifact_hygiene_passed"]}, indent=2))


if __name__ == "__main__":
    main()
