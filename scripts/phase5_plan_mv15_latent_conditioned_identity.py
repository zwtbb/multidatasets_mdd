#!/usr/bin/env python3
"""Predeclare MV15 latent-conditioned dataset identity.

This is a design contract, not an identity-probe run. It converts the
post-MV14 gate action into a bounded experiment plan: compare dataset identity
from BGE features and predicted low-dimensional outputs after conditioning on
observed labels, total severity, dimension-matched severity controls,
label-derived theta, common-support bins, and legitimate covariates.

The script reads only aggregate Phase 5 artifacts. Future theta tables,
measurement parameters, residualized features, nuisance directions, row-level
predictions, split maps, and fitted probes remain local-only.
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
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv15_latent_conditioned_identity_design"

MV09_DIR = PHASE5_DIR / "p5_mv09_conditional_identity_audit"
MV10_DIR = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
MV12_DESIGN_DIR = PHASE5_DIR / "p5_mv12_two_stage_latent_target_design"
MV12_DIR = PHASE5_DIR / "p5_mv12_two_stage_latent_target"
MV12_ANALYSIS_DIR = PHASE5_DIR / "p5_mv12_latent_target_tradeoff_analysis"
MV13_DIR = PHASE5_DIR / "p5_mv13_external_psychometric_replication"
MV14_DIR = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap"
FULL_GATE_DIR = PHASE5_DIR / "full_method_gate_audit"

RUN_ID = "P5_MV15_latent_conditioned_dataset_identity_design"

TRACKED_FILES = [
    "analysis_variable_contract.csv",
    "artifact_hygiene_audit.json",
    "conditioning_ladder_contract.csv",
    "dataset_scope_contract.csv",
    "identity_probe_contract.csv",
    "implementation_queue.csv",
    "input_boundary_contract.csv",
    "local_only_boundary_contract.csv",
    "method_source_refs.csv",
    "pass_fail_gate_contract.csv",
    "report.md",
    "run_summary.json",
    "source_evidence_summary.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "samejima_graded_response_model",
        "url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        "source_type": "primary_method_monograph",
        "use_in_mv15": "Use the same label-only graded-response measurement target lineage as MV11-MV14.",
        "key_takeaway": "Ordinal item responses can be linked through a latent severity variable and ordered response thresholds.",
    },
    {
        "source_id": "mirt_jss_2012",
        "url": "https://www.jstatsoft.org/article/view/v048i06",
        "source_type": "primary_package_paper",
        "use_in_mv15": "The future runner may locally refit the MV11/MV14 PHQ measurement target with the version-captured mirt runtime.",
        "key_takeaway": "mirt supports maximum-likelihood IRT estimation for unidimensional and multidimensional item-response models.",
    },
    {
        "source_id": "phq9_measurement_invariance_helius",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        "source_type": "measurement_invariance_paper",
        "use_in_mv15": "Frame PHQ label conditioning as measurement-aware conditioning rather than assuming item interchangeability.",
        "key_takeaway": "PHQ comparisons across groups require explicit configural, metric, scalar, and partial-invariance checks.",
    },
    {
        "source_id": "phq_hamd_irt_2021",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "source_type": "cross_scale_measurement_reference",
        "use_in_mv15": "Keep PDCH/HAMD as a severity-only sensitivity scope until MV16 scale linking is predeclared.",
        "key_takeaway": "Different depression scales can reflect related severity while retaining item and scale-specific measurement differences.",
    },
    {
        "source_id": "questionnaire_grounding_acl_2022",
        "url": "https://aclanthology.org/2022.acl-long.578/",
        "source_type": "symptom_grounding_reference",
        "use_in_mv15": "Position feature identity probes as checks on whether symptom-grounded targets reduce dataset-specific shortcuts.",
        "key_takeaway": "Symptom-level grounding is related but does not remove the need to audit measurement and dataset identity directly.",
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
    return "NA" if numeric is None else f"{numeric:.{digits}f}"


def yesno(value: Any) -> str:
    return "true" if bool(value) else "false"


def source_evidence_summary() -> pd.DataFrame:
    mv09 = read_json(MV09_DIR / "run_summary.json")
    mv10 = read_json(MV10_DIR / "run_summary.json")
    mv11 = read_json(MV11_DIR / "run_summary.json")
    mv12_design = read_json(MV12_DESIGN_DIR / "run_summary.json")
    mv12 = read_json(MV12_DIR / "run_summary.json")
    mv12_analysis = read_json(MV12_ANALYSIS_DIR / "run_summary.json")
    mv13 = read_json(MV13_DIR / "run_summary.json")
    mv14 = read_json(MV14_DIR / "run_summary.json")
    full_gate_path = FULL_GATE_DIR / "run_summary.json"
    next_actions_path = FULL_GATE_DIR / "next_action_queue.csv"
    full_gate = read_json(full_gate_path) if full_gate_path.exists() else None
    next_actions = read_csv(next_actions_path) if next_actions_path.exists() else pd.DataFrame()
    mv09_identity = read_csv(MV09_DIR / "conditional_identity_summary.csv")
    mv12_identity = read_csv(MV12_DIR / "identity_probe_summary.csv")
    mv12_tradeoff = read_csv(MV12_ANALYSIS_DIR / "accuracy_identity_tradeoff_summary.csv")
    mv14_dif = read_csv(MV14_DIR / "item_dif_stability_summary.csv")

    mv09_v = mv09.get("verdict") or {}
    mv10_v = mv10.get("verdict") or {}
    mv11_v = mv11.get("verdict") or {}
    mv12_d = mv12_design.get("decision") or {}
    mv12_v = mv12.get("verdict") or {}
    mv12_a = mv12_analysis.get("decision") or {}
    mv12_a_outputs = mv12_analysis.get("outputs") or {}
    mv13_v = mv13.get("verdict") or {}
    mv14_v = mv14.get("verdict") or {}
    top_action = (
        next_actions.sort_values("rank").iloc[0].to_dict()
        if not next_actions.empty
        else {"action_id": "unavailable_previous_full_gate_context_missing"}
    )

    mv09_primary = mv09_identity[
        (mv09_identity["probe_id"] == "edaic_cmdc_phq_core")
        & (mv09_identity["strategy"] == "phq_core_items_residualized_bge")
    ].iloc[0].to_dict()
    mv12_cond = mv12_identity[
        (mv12_identity["probe_id"] == "ID1_conditional_predicted_theta_identity")
        & (mv12_identity["model"] == "M12a_BGE_Ridge_X_to_theta")
    ].iloc[0].to_dict()
    mv12_post = mv12_identity[
        (mv12_identity["probe_id"] == "ID2_conditional_post_mapping_identity")
        & (mv12_identity["model"] == "M12a_BGE_Ridge_X_to_theta")
    ].iloc[0].to_dict()
    mv12_b3_cond = mv12_identity[
        (mv12_identity["probe_id"] == "ID1_conditional_predicted_theta_identity")
        & (mv12_identity["model"] == "B3_direct_itemwise_ridge")
    ].iloc[0].to_dict()
    mv12_b3_uncond = mv12_identity[
        (mv12_identity["probe_id"] == "ID0_unconditional_predicted_theta_identity")
        & (mv12_identity["model"] == "B3_direct_itemwise_ridge")
    ].iloc[0].to_dict()
    mv12_tradeoff_pooled = mv12_tradeoff[
        (mv12_tradeoff["source_run"].astype(str) == "P5_MV12")
        & (mv12_tradeoff["evaluation_scope"].astype(str) == "pooled_shared_phq_edaic_cmdc_mean")
    ]
    mv12_b3_tradeoff = mv12_tradeoff_pooled[
        mv12_tradeoff_pooled["model"].astype(str) == "B3_direct_itemwise_ridge"
    ].iloc[0].to_dict()
    mv12_m12a_tradeoff = mv12_tradeoff_pooled[
        mv12_tradeoff_pooled["model"].astype(str) == "M12a_BGE_Ridge_X_to_theta"
    ].iloc[0].to_dict()
    stable_anchors = mv14_dif[
        (mv14_dif["mv10_role"] == "anchor_candidate")
        & (mv14_dif["anchor_support_frequency"] >= 0.90)
    ]["construct_id"].astype(str).tolist()
    top_threshold = (
        mv14_dif.sort_values("threshold_frequency_rank")
        .head(2)["construct_id"]
        .astype(str)
        .tolist()
    )

    rows = [
        {
            "source_id": "full_method_gate_after_mv14",
            "artifact": rel(FULL_GATE_DIR / "run_summary.json"),
            "status": (
                full_gate.get("gate_status")
                if full_gate is not None
                else "missing_previous_full_gate_context_clean_rebuild"
            ),
            "observation": (
                f"evidence_rows={(full_gate or {}).get('evidence_rows', 'NA')}; "
                f"full_method_allowed={(full_gate or {}).get('full_method_allowed', 'NA')}; "
                f"top_next_action={top_action.get('action_id')}"
            ),
            "implication_for_mv15": "MV15 is the next required predeclaration before any further latent-identity or scale-linking claim.",
        },
        {
            "source_id": "MV09_feature_identity_after_label_conditioning",
            "artifact": rel(MV09_DIR / "conditional_identity_summary.csv"),
            "status": mv09_v.get("status"),
            "observation": (
                f"E-DAIC/CMDC raw BGE BA={fmt(mv09_v.get('edaic_cmdc_raw_ba'))}; "
                f"PHQ-item residualized BGE BA={fmt(mv09_primary.get('mean'))}; "
                f"severity residualized BA={fmt(mv09_v.get('edaic_cmdc_severity_residualized_ba'))}"
            ),
            "implication_for_mv15": "Observed totals or item labels alone do not explain away BGE dataset identity; label-derived theta must be audited separately.",
        },
        {
            "source_id": "MV10_MV11_label_measurement_screen",
            "artifact": rel(MV11_DIR / "run_summary.json"),
            "status": mv11_v.get("status"),
            "observation": (
                f"MV10 loading congruence={fmt(mv10_v.get('loading_congruence'))}; "
                f"MV11 anchors={mv11_v.get('confirmed_mv10_anchor_items')}; "
                f"loading_DIF_flags={mv11_v.get('loading_dif_flagged_items')}; "
                f"threshold_DIF_flags={mv11_v.get('threshold_dif_flagged_items')}"
            ),
            "implication_for_mv15": "Conditioning on theta should use the partial-invariance PHQ measurement map, not a naive sum-only target.",
        },
        {
            "source_id": "MV12_predicted_theta_identity_tradeoff",
            "artifact": rel(MV12_DIR / "identity_probe_summary.csv"),
            "status": mv12_v.get("pass_rule_status"),
            "observation": (
                f"M12a conditional predicted-theta identity BA={fmt(mv12_cond.get('mean'))}; "
                f"B3 conditional predicted-theta identity BA={fmt(mv12_b3_cond.get('mean'))}; "
                f"post-mapping item residual identity BA={fmt(mv12_post.get('mean'))}; "
                f"observed-scale safety={mv12_v.get('same_dataset_observed_gate_passed')}; "
                f"external theta transfer={mv12_v.get('external_transfer_theta_gate_passed')}"
            ),
            "implication_for_mv15": "M12a reduces identity versus upstream BGE but not versus B3 direct itemwise theta; MV15 must include dimension-matched severity controls.",
        },
        {
            "source_id": "MV12_dimension_matched_baseline_caveat",
            "artifact": rel(MV12_ANALYSIS_DIR / "accuracy_identity_tradeoff_summary.csv"),
            "status": mv12_a.get("analysis_status"),
            "observation": (
                f"B3 observed macro MAE={fmt(mv12_b3_tradeoff.get('mean_observed_macro_mae'))}; "
                f"B3 conditional identity BA={fmt(mv12_b3_tradeoff.get('dataset_identity_ba_conditional_latent'))}; "
                f"M12a observed macro MAE={fmt(mv12_m12a_tradeoff.get('mean_observed_macro_mae'))}; "
                f"M12a conditional identity BA={fmt(mv12_m12a_tradeoff.get('dataset_identity_ba_conditional_latent'))}; "
                f"B3 unconditional identity BA={fmt(mv12_b3_uncond.get('mean'))}"
            ),
            "implication_for_mv15": "A low-dimensional output alone can lower dataset identity; psychometric theta must be compared with total and direct-item severity controls.",
        },
        {
            "source_id": "MV12_tradeoff_freeze",
            "artifact": rel(MV12_ANALYSIS_DIR / "run_summary.json"),
            "status": mv12_a.get("analysis_status"),
            "observation": (
                f"freeze_current_latent_target_line={mv12_a.get('freeze_current_latent_target_line')}; "
                f"tradeoff_rows={mv12_a_outputs.get('tradeoff_rows')}; "
                f"failure_mode_rows={mv12_a_outputs.get('failure_mode_rows')}"
            ),
            "implication_for_mv15": "MV15 may audit the identity gate but must not become another shallow-head retuning pass.",
        },
        {
            "source_id": "MV14_bootstrap_stability",
            "artifact": rel(MV14_DIR / "run_summary.json"),
            "status": mv14_v.get("status"),
            "observation": (
                f"stable_anchors={';'.join(stable_anchors)}; "
                f"top_threshold_DIF={';'.join(top_threshold)}; "
                f"core_convergence_safe_R={mv14_v.get('core_effective_draws')}/{mv14_v.get('core_selection_attempted_draws')}; "
                f"stable_ladder_R={mv14_v.get('stable_ladder_effective_draws')}; "
                f"DIF_effective_R={mv14_v.get('dif_min_anchor_effective_draws')}"
            ),
            "implication_for_mv15": "Use item-level wording: stable anchors and localized C02/C06 threshold non-equivalence, with global model-selection uncertainty visible.",
        },
        {
            "source_id": "MV13_external_replication_caveat",
            "artifact": rel(MV13_DIR / "run_summary.json"),
            "status": mv13_v.get("status"),
            "observation": (
                f"AIC/BIC={mv13_v.get('best_aic_model')}/{mv13_v.get('best_bic_model')}; "
                f"core_converged={mv13_v.get('core_converged')}; "
                f"aligned_decisions={mv13_v.get('mv11_mv13_aligned_rows')}/{mv13_v.get('mv11_mv13_alignment_rows')}"
            ),
            "implication_for_mv15": "Keep convergence/model-selection caveats visible when using locally generated theta as an identity-conditioning variable.",
        },
        {
            "source_id": "MV12_design_boundary",
            "artifact": rel(MV12_DESIGN_DIR / "run_summary.json"),
            "status": mv12_d.get("readiness_status"),
            "observation": (
                f"full_method_allowed={mv12_d.get('full_method_allowed')}; "
                "theta targets, fitted parameters, row predictions, and transformed features are local-only."
            ),
            "implication_for_mv15": "Reuse the same local-only latent-score and residualization boundary for MV15.",
        },
    ]
    return pd.DataFrame(rows)


def dataset_scope_contract() -> pd.DataFrame:
    rows = [
        {
            "scope_id": "S1_primary_edaic_cmdc_phq",
            "datasets": "edaic;cmdc",
            "feature_family": "text_bge",
            "label_scope": "shared PHQ C01-C08 item labels plus observed PHQ total",
            "latent_scope": "PHQ partial-invariance theta generated locally from MV11/MV14 anchor contract",
            "sample_contract": "Use the same 219 E-DAIC and 77 CMDC item-labeled BGE subjects as MV09/MV12 when available.",
            "status": "primary_ready_to_implement",
            "interpretation": "Primary MV15 identity evidence; still diagnostic, not a deployable method.",
        },
        {
            "scope_id": "S2_predicted_theta_output_identity",
            "datasets": "edaic;cmdc",
            "feature_family": "text_bge_to_theta",
            "label_scope": "same PHQ target used for MV12 X_to_theta",
            "latent_scope": "fold-generated true theta and predicted theta are local-only",
            "sample_contract": "Use the same folds as the future MV15 feature-identity run or regenerate them with recorded aggregate split audit.",
            "status": "secondary_ready_to_implement",
            "interpretation": "Tests whether a latent output is less dataset-identifiable than observed-scale outputs.",
        },
        {
            "scope_id": "S3_cmdc_pdch_total_sensitivity",
            "datasets": "cmdc;pdch",
            "feature_family": "text_bge",
            "label_scope": "normalized PHQ/HAMD total severity only",
            "latent_scope": "no shared PHQ-HAMD theta until MV16 scale-linking is predeclared",
            "sample_contract": "Use MV09-compatible 77 CMDC and 99 PDCH joined BGE subjects.",
            "status": "severity_sensitivity_only",
            "interpretation": "Report as severity-conditioned diagnostic only; do not mix with primary PHQ theta claims.",
        },
        {
            "scope_id": "S4_three_way_total_norm_sensitivity",
            "datasets": "edaic;cmdc;pdch",
            "feature_family": "text_bge",
            "label_scope": "normalized total severity",
            "latent_scope": "blocked for shared latent interpretation before MV16",
            "sample_contract": "Use MV09-compatible three-way BGE subject table and common severity support bins.",
            "status": "diagnostic_sensitivity_only",
            "interpretation": "Tracks broad dataset identity risk but cannot authorize cross-scale latent claims.",
        },
    ]
    return pd.DataFrame(rows)


def analysis_variable_contract() -> pd.DataFrame:
    rows = [
        {
            "variable_id": "D_dataset",
            "variable_role": "identity_target",
            "definition": "Dataset label for the identity classifier.",
            "allowed_use": "Diagnostic target only; never an input to deployable depression prediction.",
            "tracked_policy": "Aggregate class counts and balanced-accuracy summaries only.",
            "local_only_policy": "Fold assignments and participant-grain labels remain local-only.",
        },
        {
            "variable_id": "Z_bge",
            "variable_role": "feature_representation",
            "definition": "Frozen aligned BGE subject-level text features used in MV07-MV12.",
            "allowed_use": "Identity-probe input after train-fold residualization or common-support restriction.",
            "tracked_policy": "Aggregate feature-family and column-count summaries only.",
            "local_only_policy": "Feature matrices, residualized features, projections, and nuisance directions stay local-only.",
        },
        {
            "variable_id": "Y_items",
            "variable_role": "observed_label_condition",
            "definition": "PHQ C01-C08 observed item labels for E-DAIC/CMDC.",
            "allowed_use": "Diagnostic conditioning variable and theta-generation input.",
            "tracked_policy": "Aggregate item coverage and response-support summaries only.",
            "local_only_policy": "Participant-grain item table stays local-only.",
        },
        {
            "variable_id": "theta_label",
            "variable_role": "latent_condition",
            "definition": "Label-derived PHQ latent severity from the convergence-aware item-level measurement-shift contract.",
            "allowed_use": "Primary MV15 conditioning variable for D|Z,theta and theta-only controls.",
            "tracked_policy": "Aggregate theta coverage, distribution bins, reliability, and identity metrics only.",
            "local_only_policy": "Theta scores, posterior summaries, item parameters, and uncertainty rows stay local-only.",
        },
        {
            "variable_id": "T_total",
            "variable_role": "dimension_matched_observed_severity_condition",
            "definition": "Observed PHQ total or normalized total severity represented as a one-dimensional control.",
            "allowed_use": "Primary comparator to theta conditioning; answers whether identity reduction is more than low-dimensional severity compression.",
            "tracked_policy": "Aggregate distribution bins, common-support counts, and identity metrics only.",
            "local_only_policy": "Participant-grain totals used in folds stay local-only.",
        },
        {
            "variable_id": "S_pred_total",
            "variable_role": "dimension_matched_predicted_total_output",
            "definition": "Fold-generated one-dimensional predicted total score from a direct total-score head.",
            "allowed_use": "Output identity comparator for predicted theta.",
            "tracked_policy": "Aggregate utility and identity metrics only.",
            "local_only_policy": "Row predictions and fitted total-score heads stay local-only.",
        },
        {
            "variable_id": "S_b3_itemwise_theta",
            "variable_role": "dimension_matched_direct_itemwise_severity_output",
            "definition": "Direct itemwise Ridge predictions compressed to theta using the local measurement map, matching MV12 B3.",
            "allowed_use": "Critical comparator because MV12 B3 has lower identity and better observed fidelity than M12a in aggregate.",
            "tracked_policy": "Aggregate utility and identity metrics only.",
            "local_only_policy": "Itemwise row predictions, compressed theta rows, and fitted heads stay local-only.",
        },
        {
            "variable_id": "theta_pred",
            "variable_role": "predicted_latent_output",
            "definition": "Fold-generated predicted theta from the future MV15 or reproduced MV12 X_to_theta model.",
            "allowed_use": "Secondary identity target/output diagnostic.",
            "tracked_policy": "Aggregate identity and utility summaries only.",
            "local_only_policy": "Row-level predictions, fitted heads, and model artifacts stay local-only.",
        },
        {
            "variable_id": "C_covariates",
            "variable_role": "legitimate_covariate_condition",
            "definition": "Manifest-governed covariates available in both compared datasets, such as E-DAIC/CMDC gender when coverage permits.",
            "allowed_use": "Sensitivity conditioning only when coverage and missingness are reported.",
            "tracked_policy": "Aggregate coverage and missingness summaries only.",
            "local_only_policy": "Participant-grain covariate table and imputed values stay local-only.",
        },
    ]
    return pd.DataFrame(rows)


def conditioning_ladder_contract() -> pd.DataFrame:
    rows = [
        {
            "ladder_id": "L0_D_given_Z_raw",
            "estimand": "D|Z",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "none",
            "diagnostic_question": "How identifiable is dataset from the raw frozen BGE representation?",
            "future_run_rule": "Report balanced accuracy by seed and aggregate mean/std.",
            "interpretation": "Shortcut-risk reference, not a hard failure by itself.",
        },
        {
            "ladder_id": "L1_D_given_Z_and_total",
            "estimand": "D|residual(Z ~ normalized_total)",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "normalized PHQ total",
            "diagnostic_question": "Does total severity explain dataset identity?",
            "future_run_rule": "Residualizer fitted on train fold only; evaluation covariates can be used only for diagnostic residualization.",
            "interpretation": "If still high, total severity alone is not the explanation.",
        },
        {
            "ladder_id": "L2_D_given_Z_and_predicted_total",
            "estimand": "D|residual(Z ~ predicted_total)",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "fold-generated predicted total score",
            "diagnostic_question": "Does a one-dimensional predicted severity control explain identity about as well as theta?",
            "future_run_rule": "Generate predicted total inside the same subject-level folds; export aggregate identity only.",
            "interpretation": "Dimension-matched predicted-total control; favorable theta results must beat this comparator.",
        },
        {
            "ladder_id": "L3_D_given_Z_and_items",
            "estimand": "D|residual(Z ~ C01-C08)",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "observed PHQ C01-C08 items",
            "diagnostic_question": "Does item-level observed symptom profile explain dataset identity?",
            "future_run_rule": "Repeat MV09 item-conditioned residualization as the direct comparator.",
            "interpretation": "Expected reference is MV09 BA about 0.991; MV15 should not ignore this blocker.",
        },
        {
            "ladder_id": "L4_D_given_Z_and_b3_itemwise_theta",
            "estimand": "D|residual(Z ~ theta_from_direct_itemwise_predictions)",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "direct itemwise Ridge predictions compressed to theta",
            "diagnostic_question": "Does psychometric theta conditioning beat the MV12 B3 dimension-matched severity comparator?",
            "future_run_rule": "Regenerate B3-like direct itemwise predictions locally under the same folds; no row predictions exported.",
            "interpretation": "Critical reviewer-control layer; if B3 is equal or better, MV15 cannot claim theta-specific identity reduction.",
        },
        {
            "ladder_id": "L5_D_given_Z_and_theta",
            "estimand": "D|residual(Z ~ theta_label)",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "label-derived PHQ theta",
            "diagnostic_question": "Does the psychometric latent target explain more dataset identity than sums/items?",
            "future_run_rule": "Theta must be generated within the fold or from a predeclared local-only measurement fit; no theta scores exported.",
            "interpretation": "Primary MV15 latent-conditioned feature-identity gate.",
        },
        {
            "ladder_id": "L6_D_given_Z_theta_covariates",
            "estimand": "D|residual(Z ~ theta_label + legitimate_covariates)",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "theta_label;available shared covariates",
            "diagnostic_question": "Does legitimate covariate conditioning change the latent-conditioned identity conclusion?",
            "future_run_rule": "Run only for covariates with coverage in both datasets; otherwise export a skipped aggregate row.",
            "interpretation": "Sensitivity layer, not the primary gate.",
        },
        {
            "ladder_id": "L7_D_given_theta_only",
            "estimand": "D|theta_label",
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "conditioning_variables": "theta_label only",
            "diagnostic_question": "Does the latent severity distribution itself identify the dataset?",
            "future_run_rule": "Train classifier on theta or theta-bin only and report common-support bins.",
            "interpretation": "If high, population/severity distribution shift must be separated from representation shortcut.",
        },
        {
            "ladder_id": "L8_D_given_predicted_outputs",
            "estimand": "D|theta_pred and residual(theta_pred ~ theta_label,total)",
            "primary_scope": "S2_predicted_theta_output_identity",
            "conditioning_variables": "predicted total;B3 direct-item theta;psychometric predicted theta;true theta;observed total",
            "diagnostic_question": "Is psychometric predicted theta less dataset-identifiable than dimension-matched predicted severity outputs?",
            "future_run_rule": "Regenerate local predicted total, B3 itemwise-compressed theta, and M12a-like theta under the same split audit; export aggregate identity only.",
            "interpretation": "Secondary evidence for output-space identity; must be interpreted against B3 and predicted-total controls.",
        },
        {
            "ladder_id": "L9_severity_only_sensitivity",
            "estimand": "D|residual(Z ~ normalized_total)",
            "primary_scope": "S3/S4 sensitivity scopes",
            "conditioning_variables": "normalized total severity",
            "diagnostic_question": "How much identity remains for PDCH/HAMD or three-way severity-only comparisons?",
            "future_run_rule": "No shared theta wording; report as sensitivity while MV16 is pending.",
            "interpretation": "Cannot authorize PHQ-HAMD latent identity claims.",
        },
    ]
    return pd.DataFrame(rows)


def identity_probe_contract() -> pd.DataFrame:
    rows = [
        {
            "probe_id": "P1_primary_feature_identity_given_theta",
            "scope_id": "S1_primary_edaic_cmdc_phq",
            "classifier_target": "D_dataset",
            "representation": "residualized_Z_bge",
            "conditioning": "theta_label",
            "metric": "balanced_accuracy_mean_std_over_5_subject_level_seeds",
            "future_pass_rule": "Preferred pass only if theta-conditioned BA <= 0.70 and is at least 0.03 lower than total-, predicted-total-, and B3-itemwise-theta-conditioned BA; partial support if BA <= 0.75 and not worse than all dimension-matched controls; blocked if BA > 0.80 or B3/total dominates.",
            "claim_effect": "Can update identity-gate interpretation only; does not authorize full method alone.",
        },
        {
            "probe_id": "P2_theta_distribution_identity",
            "scope_id": "S1_primary_edaic_cmdc_phq",
            "classifier_target": "D_dataset",
            "representation": "theta_label_or_theta_bins",
            "conditioning": "none",
            "metric": "balanced_accuracy_and_common_support_bin_counts",
            "future_pass_rule": "Report-only diagnostic; high BA means dataset populations differ along latent severity.",
            "claim_effect": "Separates target/population shift from feature shortcut.",
        },
        {
            "probe_id": "P3_feature_identity_given_total_items_b3_vs_theta_delta",
            "scope_id": "S1_primary_edaic_cmdc_phq",
            "classifier_target": "D_dataset",
            "representation": "residualized_Z_bge",
            "conditioning": "normalized_total;predicted_total;Y_items;B3_itemwise_theta;theta_label",
            "metric": "delta_BA_theta_conditioned_minus_each_dimension_matched_control",
            "future_pass_rule": "Theta conditioning must be reported against MV09 item-conditioned BA plus total, predicted-total, and B3 itemwise-theta controls.",
            "claim_effect": "Shows whether psychometric conditioning changes the MV09 conclusion beyond low-dimensional severity compression.",
        },
        {
            "probe_id": "P4_predicted_theta_output_identity",
            "scope_id": "S2_predicted_theta_output_identity",
            "classifier_target": "D_dataset",
            "representation": "predicted_total;B3_itemwise_theta;theta_pred",
            "conditioning": "none and theta_label_plus_total residual",
            "metric": "balanced_accuracy_mean_std_over_5_subject_level_seeds",
            "future_pass_rule": "M12a-like theta output must be compared with MV12 B3 conditional BA around 0.579 and M12a around 0.602; it cannot be called theta-specific identity reduction if B3 or predicted total is lower.",
            "claim_effect": "Supports output-space identity interpretation, not feature invariance.",
        },
        {
            "probe_id": "P5_dimension_matched_severity_identity_controls",
            "scope_id": "S1_primary_edaic_cmdc_phq;S2_predicted_theta_output_identity",
            "classifier_target": "D_dataset",
            "representation": "one_dimensional_observed_or_predicted_severity",
            "conditioning": "none or common-support bins",
            "metric": "balanced_accuracy_and_fidelity_identity_pareto_status",
            "future_pass_rule": "Report whether theta is Pareto-dominated by total/predicted-total/B3 controls on identity BA and observed macro MAE.",
            "claim_effect": "Blocks overclaiming low identity from dimensionality reduction alone.",
        },
        {
            "probe_id": "P6_covariate_sensitivity",
            "scope_id": "S1_primary_edaic_cmdc_phq",
            "classifier_target": "D_dataset",
            "representation": "residualized_Z_bge",
            "conditioning": "theta_label plus shared manifest covariates",
            "metric": "coverage;missingness;balanced_accuracy",
            "future_pass_rule": "Run only for covariates with enough coverage in both datasets; otherwise skipped with reason.",
            "claim_effect": "Prevents unreported age/gender/population confounding from being folded into theta claims.",
        },
        {
            "probe_id": "P7_severity_only_external_sensitivity",
            "scope_id": "S3_cmdc_pdch_total_sensitivity;S4_three_way_total_norm_sensitivity",
            "classifier_target": "D_dataset",
            "representation": "residualized_Z_bge",
            "conditioning": "normalized_total",
            "metric": "balanced_accuracy_mean_std_over_5_subject_level_seeds",
            "future_pass_rule": "Report as sensitivity; no pass can authorize cross-scale latent claims before MV16.",
            "claim_effect": "Keeps PDCH/HAMD evidence bounded.",
        },
    ]
    return pd.DataFrame(rows)


def input_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "input_id": "aggregate_phase5_sources_for_design",
            "read_now": "true",
            "future_runner_use": "gate context and reference thresholds",
            "allowed_sources": "MV09;MV10;MV11;MV12;MV12_analysis;MV13;MV14;full_method_gate",
            "forbidden_sources": "raw media;raw transcripts;private review material;local workbooks",
            "tracked_derivative": "source_evidence_summary.csv",
        },
        {
            "input_id": "future_feature_inputs",
            "read_now": "false",
            "future_runner_use": "identity-probe inputs",
            "allowed_sources": "manifest-governed aligned BGE feature cache used by MV07-MV12",
            "forbidden_sources": "ad hoc raw-directory scans or new encoder fine-tuning",
            "tracked_derivative": "aggregate feature-family and coverage audit only",
        },
        {
            "input_id": "future_label_inputs",
            "read_now": "false",
            "future_runner_use": "conditioning and local theta generation",
            "allowed_sources": "manifest-governed PHQ item labels and totals for E-DAIC/CMDC; normalized totals for sensitivity scopes",
            "forbidden_sources": "E-DAIC official test labels or unmanifested labels",
            "tracked_derivative": "aggregate label coverage and category support only",
        },
        {
            "input_id": "future_theta_inputs",
            "read_now": "false",
            "future_runner_use": "primary latent-conditioning variable",
            "allowed_sources": "locally regenerated MV11/MV14-compatible measurement fit inside the future runner",
            "forbidden_sources": "tracked theta score files or public fitted parameter tables",
            "tracked_derivative": "aggregate theta coverage, reliability, bin, and identity summaries only",
        },
    ]
    return pd.DataFrame(rows)


def local_only_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "artifact_class": "theta_scores",
            "reason_local_only": "Latent scores are participant-grain measurement outputs.",
            "tracked_surrogate": "aggregate coverage, distribution bins, reliability, and identity metrics",
            "git_policy": "ignore local_*theta* files and do not export participant-grain theta tables",
        },
        {
            "artifact_class": "measurement_parameters",
            "reason_local_only": "Item parameters and uncertainty rows can reconstruct sensitive measurement details.",
            "tracked_surrogate": "aggregate anchor/DIF stability already available from MV14",
            "git_policy": "no fitted parameter CSV/JSON/RDS files in Git",
        },
        {
            "artifact_class": "residualized_features",
            "reason_local_only": "Residualized feature matrices remain participant-grain transformed representations.",
            "tracked_surrogate": "aggregate identity summaries by probe, seed, and conditioning ladder",
            "git_policy": "ignore residualized feature files and nuisance direction artifacts",
        },
        {
            "artifact_class": "row_predictions",
            "reason_local_only": "Per-participant model outputs are local diagnostics, not public evidence tables.",
            "tracked_surrogate": "aggregate BA, fold-count, sample-count, and split-overlap audits",
            "git_policy": "ignore prediction CSVs and fitted probe artifacts",
        },
        {
            "artifact_class": "split_maps",
            "reason_local_only": "Fold assignment tables are participant-grain experiment state.",
            "tracked_surrogate": "aggregate subject-overlap violation count and fold coverage",
            "git_policy": "track only split audit summaries",
        },
    ]
    return pd.DataFrame(rows)


def pass_fail_gate_contract() -> pd.DataFrame:
    rows = [
        {
            "gate_id": "G1_input_scope",
            "status": "predeclared",
            "future_run_pass_rule": "Future MV15 runner reads only manifest-governed BGE/label inputs plus aggregate MV09-MV14 references; no raw media or private review material.",
            "full_method_effect": "Violation invalidates MV15.",
        },
        {
            "gate_id": "G2_subject_level_splits",
            "status": "predeclared",
            "future_run_pass_rule": "All identity probes use subject-level folds with zero overlap violations.",
            "full_method_effect": "Any overlap keeps all MV15 identity claims blocked.",
        },
        {
            "gate_id": "G3_theta_local_only",
            "status": "predeclared",
            "future_run_pass_rule": "No theta scores, fitted item parameters, residualized feature matrices, row predictions, or nuisance directions are tracked.",
            "full_method_effect": "Any tracked local-only artifact invalidates the run until removed.",
        },
        {
            "gate_id": "G4_reference_reporting",
            "status": "predeclared",
            "future_run_pass_rule": "Report raw identity, total conditioning, predicted-total conditioning, item conditioning, B3 itemwise-theta conditioning, theta conditioning, and theta-only controls together.",
            "full_method_effect": "A single favorable conditional BA cannot be cited alone.",
        },
        {
            "gate_id": "G5_primary_identity_threshold",
            "status": "predeclared",
            "future_run_pass_rule": "Preferred pass if theta-conditioned feature identity BA <= 0.70 and at least 0.03 lower than every dimension-matched severity control; partial support if <=0.75 and tied with controls; blocked if BA >0.80 or any B3/total control dominates both identity and fidelity.",
            "full_method_effect": "Even a pass only permits MV16 predeclaration or bounded diagnostic wording, not full M0/M1/M2/M3.",
        },
        {
            "gate_id": "G6_output_identity_boundary",
            "status": "predeclared",
            "future_run_pass_rule": "Predicted-theta identity must be reported separately from predicted-total, B3 itemwise-theta, and post-mapping observed-scale identity.",
            "full_method_effect": "High observed-scale identity or B3/predicted-total dominance blocks theta-specific wording even if theta output identity is low.",
        },
        {
            "gate_id": "G7_external_sensitivity_boundary",
            "status": "predeclared",
            "future_run_pass_rule": "CMDC/PDCH and three-way probes are severity-only sensitivity rows until MV16 supplies scale-linking.",
            "full_method_effect": "No cross-scale PHQ-HAMD latent claim from MV15 alone.",
        },
        {
            "gate_id": "G8_artifact_hygiene",
            "status": "predeclared",
            "future_run_pass_rule": "Tracked outputs contain only aggregate contracts, coverage, metrics, gate results, reports, and memory.",
            "full_method_effect": "Hygiene failure blocks publishing and claim refresh.",
        },
    ]
    return pd.DataFrame(rows)


def implementation_queue() -> pd.DataFrame:
    rows = [
        {
            "rank": 1,
            "action_id": "IMPLEMENT_MV15_LATENT_CONDITIONED_IDENTITY_RUNNER",
            "action": "Implement the future MV15 runner with fold-safe theta generation, residualized BGE identity probes, total/predicted-total/B3 severity controls, theta-only controls, predicted-output identity, and severity-only sensitivity scopes.",
            "success_gate": "Aggregate outputs cover L0-L9, P1-P7, zero split overlap, and hygiene without tracked local-only artifacts.",
            "version_policy": "Track runner, aggregate summaries, report, refreshed gates, docs, and memory only.",
        },
        {
            "rank": 2,
            "action_id": "REFRESH_FULL_METHOD_GATE_AFTER_MV15",
            "action": "Rerun the full-method gate after the MV15 runner.",
            "success_gate": "Gate distinguishes feature identity, latent-conditioned feature identity, theta output identity, and observed-scale identity.",
            "version_policy": "Commit aggregate gate outputs only.",
        },
        {
            "rank": 3,
            "action_id": "PREDECLARE_MV16_THETA_CALIBRATION",
            "action": "If MV15 is interpretable, predeclare MV16 DIF-guided cross-dataset theta calibration and few-shot scale linking.",
            "success_gate": "MV16 compares zero-shot, global affine/monotonic, C02/C06 DIF-guided threshold calibration, all-threshold calibration, and direct adaptation with local-only calibration parameters and aggregate curves.",
            "version_policy": "Track design artifacts and aggregate summaries only.",
        },
        {
            "rank": 4,
            "action_id": "FREEZE_IF_IDENTITY_REMAINS_HIGH",
            "action": "If MV15 remains high-identity after theta conditioning, freeze the current latent-conditioned identity line as diagnostic evidence.",
            "success_gate": "Paper framing states that measurement-aware latent targets do not remove dataset identity under the current BGE contract.",
            "version_policy": "Track diagnostic summaries and manuscript claim tables only.",
        },
    ]
    return pd.DataFrame(rows)


def method_source_refs() -> pd.DataFrame:
    return pd.DataFrame(METHOD_SOURCE_REFS)


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
        r"source_locator",
        r"local_annotation_workbook",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"raw clinical",
        r"raw prompt",
        r"raw response",
        r"posterior_score",
        r"factor_score",
        r"parameter_value",
        r"nuisance_direction_value",
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
        "audit_id": "P5_MV15_latent_conditioned_identity_design_hygiene",
        "artifact_hygiene_passed": len(violations) == 0,
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    evidence: pd.DataFrame,
    scopes: pd.DataFrame,
    variables: pd.DataFrame,
    ladder: pd.DataFrame,
    probes: pd.DataFrame,
    gates: pd.DataFrame,
    queue: pd.DataFrame,
) -> None:
    decision = run_summary["decision"]
    lines = [
        "# P5_MV15 Latent-Conditioned Dataset Identity Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This is a predeclared design contract. It does not run identity probes, train a multimodal model, fit public theta scores, export residualized features, or authorize full-method construction.",
        "",
        "## Decision",
        "",
        f"- Design status: `{decision['design_status']}`.",
        f"- Recommended next action: `{decision['recommended_next_action']}`.",
        f"- Full method allowed: `{decision['full_method_allowed']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        decision["short_read"],
        "",
        "## Source Evidence",
        "",
        "| source | status | observation | implication |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in evidence.iterrows():
        lines.append(
            f"| {row['source_id']} | `{row['status']}` | "
            f"{md_escape(row['observation'])} | {md_escape(row['implication_for_mv15'])} |"
        )

    lines.extend(["", "## Dataset Scopes", "", "| scope | datasets | status | interpretation |", "| --- | --- | --- | --- |"])
    for _, row in scopes.iterrows():
        lines.append(f"| {row['scope_id']} | {row['datasets']} | `{row['status']}` | {md_escape(row['interpretation'])} |")

    lines.extend(["", "## Variables", "", "| variable | role | allowed use | tracked policy |", "| --- | --- | --- | --- |"])
    for _, row in variables.iterrows():
        lines.append(
            f"| {row['variable_id']} | {row['variable_role']} | "
            f"{md_escape(row['allowed_use'])} | {md_escape(row['tracked_policy'])} |"
        )

    lines.extend(["", "## Conditioning Ladder", "", "| ladder | estimand | variables | rule |", "| --- | --- | --- | --- |"])
    for _, row in ladder.iterrows():
        lines.append(
            f"| {row['ladder_id']} | {md_escape(row['estimand'])} | "
            f"{md_escape(row['conditioning_variables'])} | {md_escape(row['future_run_rule'])} |"
        )

    lines.extend(["", "## Identity Probes", "", "| probe | scope | representation | future rule |", "| --- | --- | --- | --- |"])
    for _, row in probes.iterrows():
        lines.append(
            f"| {row['probe_id']} | {row['scope_id']} | "
            f"{md_escape(row['representation'])} | {md_escape(row['future_pass_rule'])} |"
        )

    lines.extend(["", "## Gates", "", "| gate | status | future run rule | effect |", "| --- | --- | --- | --- |"])
    for _, row in gates.iterrows():
        lines.append(
            f"| {row['gate_id']} | `{row['status']}` | "
            f"{md_escape(row['future_run_pass_rule'])} | {md_escape(row['full_method_effect'])} |"
        )

    lines.extend(["", "## Implementation Queue", "", "| rank | action | success gate |", "| ---: | --- | --- |"])
    for _, row in queue.sort_values("rank").iterrows():
        lines.append(f"| {int(row['rank'])} | {md_escape(row['action'])} | {md_escape(row['success_gate'])} |")

    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- MV15 can update the identity-gate interpretation only after the future runner produces aggregate results.",
            "- MV15 does not authorize full M0/M1/M2/M3 method construction.",
            "- A favorable theta-conditioned identity result still needs MV16 scale calibration before cross-scale latent transfer claims.",
            "- If identity remains high after theta conditioning, freeze this line as diagnostic evidence for dataset-specific representation shift.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, generated_at: str, overwrite: bool) -> dict[str, Any]:
    evidence = source_evidence_summary()

    if out_dir.exists() and overwrite:
        shutil.rmtree(out_dir)
    if out_dir.exists():
        raise SystemExit(f"output directory exists; use --overwrite: {rel(out_dir)}")
    out_dir.mkdir(parents=True, exist_ok=True)

    scopes = dataset_scope_contract()
    variables = analysis_variable_contract()
    ladder = conditioning_ladder_contract()
    probes = identity_probe_contract()
    inputs = input_boundary_contract()
    local_only = local_only_boundary_contract()
    gates = pass_fail_gate_contract()
    queue = implementation_queue()
    refs = method_source_refs()

    evidence.to_csv(out_dir / "source_evidence_summary.csv", index=False)
    scopes.to_csv(out_dir / "dataset_scope_contract.csv", index=False)
    variables.to_csv(out_dir / "analysis_variable_contract.csv", index=False)
    ladder.to_csv(out_dir / "conditioning_ladder_contract.csv", index=False)
    probes.to_csv(out_dir / "identity_probe_contract.csv", index=False)
    inputs.to_csv(out_dir / "input_boundary_contract.csv", index=False)
    local_only.to_csv(out_dir / "local_only_boundary_contract.csv", index=False)
    gates.to_csv(out_dir / "pass_fail_gate_contract.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    run_summary = {
        "run_id": RUN_ID,
        "generated_at": generated_at,
        "scope": "latent_conditioned_identity_predeclaration_no_probe_run",
        "status": "complete",
        "input_contract": {
            "aggregate_phase5_artifacts_read": True,
            "raw_text_or_media_read": False,
            "multimodal_features_read_now": False,
            "row_level_predictions_read": False,
            "private_review_material_read": False,
            "future_primary_datasets": ["edaic", "cmdc"],
            "future_sensitivity_datasets": ["pdch"],
            "future_feature_family": "text_bge",
            "future_identity_unit": "subject_level",
            "full_method_allowed": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "source_evidence_rows": int(len(evidence)),
            "dataset_scope_rows": int(len(scopes)),
            "analysis_variable_rows": int(len(variables)),
            "conditioning_ladder_rows": int(len(ladder)),
            "identity_probe_rows": int(len(probes)),
            "input_boundary_rows": int(len(inputs)),
            "local_only_boundary_rows": int(len(local_only)),
            "pass_fail_gate_rows": int(len(gates)),
            "implementation_queue_rows": int(len(queue)),
            "method_source_ref_rows": int(len(refs)),
        },
        "decision": {
            "design_status": "ready_to_implement_mv15_latent_conditioned_identity",
            "recommended_next_action": "implement_scripts_phase5_run_mv15_latent_conditioned_identity",
            "full_method_allowed": False,
            "primary_scope": "S1_primary_edaic_cmdc_phq",
            "next_after_mv15": "predeclare_mv16_theta_calibration_if_mv15_interpretable",
            "short_read": (
                "MV15 is predeclared as a latent-conditioned identity audit: compare dataset identity "
                "from BGE features and low-dimensional outputs after conditioning on observed labels, "
                "total severity, predicted-total severity, direct-itemwise-theta severity, label-derived "
                "theta, common-support bins, and legitimate covariates. It is diagnostic only."
            ),
        },
        "verdict": {
            "status": "ready_to_implement_mv15_latent_conditioned_identity",
            "pass_rule_status": "design_ready_full_method_still_blocked",
            "pass_rule_met": None,
            "full_method_allowed": False,
            "short_read": "Design is ready; the actual MV15 identity run is still required before any identity-gate interpretation can change.",
        },
        "local_only_files": {
            "theta_scores": "all participant-grain label-derived and predicted theta tables",
            "measurement_parameters": "all fitted item parameters and posterior diagnostics",
            "residualized_features": "all feature residual matrices and nuisance directions",
            "row_predictions": "all per-participant identity probe outputs",
            "split_maps": "all fold assignment tables",
        },
        "artifact_hygiene_passed": False,
    }

    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, evidence, scopes, variables, ladder, probes, gates, queue)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, evidence, scopes, variables, ladder, probes, gates, queue)
    hygiene = artifact_hygiene(out_dir)
    write_json(out_dir / "artifact_hygiene_audit.json", hygiene)
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    summary = build_outputs(args.out_dir, utc_now(), args.overwrite)
    display_out = args.out_dir.resolve().relative_to(ROOT) if args.out_dir.is_absolute() else args.out_dir
    print(
        json.dumps(
            {
                "out_dir": str(display_out),
                "design_status": summary["decision"]["design_status"],
                "artifact_hygiene_passed": summary["artifact_hygiene_passed"],
                "full_method_allowed": summary["decision"]["full_method_allowed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
