#!/usr/bin/env python3
"""Build the minimal method-validation protocol contract.

This script turns the Phase 3 Stop/Go synthesis and Phase 4 symptom ontology
into an executable planning contract. It does not train models. It defines what
must be implemented and audited before any full method is attempted.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis" / "phase5_minimal_validation"
PHASE3_SYNTHESIS = ROOT / "analysis" / "phase3_diagnostics" / "phase3_stop_go_synthesis.md"
PHASE4_DIR = ROOT / "analysis" / "phase4_symptom_ontology"
PHASE4_MATRIX = PHASE4_DIR / "minimal_validation_matrix.csv"
PHASE4_CONTRACT = PHASE4_DIR / "dataset_label_contract.csv"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


EXPERIMENT_MATRIX = [
    {
        "protocol_id": "P5_MV01",
        "phase4_source_id": "MV01",
        "rq": "RQ1",
        "name": "phq_core_construct_bridge",
        "status": "complete_diagnostic_weak_asymmetric",
        "train_scope": "E-DAIC PHQ-8 item labels; CMDC PHQ-9 item labels",
        "eval_scope": "held-out subject folds within E-DAIC and CMDC; cross-scale PHQ-8/PHQ-9 bridge summaries",
        "target_contract": "C01-C08 direct PHQ-overlap constructs; C09 held out for PHQ-9-only/safety reporting",
        "feature_contract": "start with frozen text/audio/video features already audited; do not fine-tune encoders in minimal validation",
        "model_contract": "shared construct heads plus PHQ-8/PHQ-9 scale-specific measurement heads",
        "required_controls": "dataset-stratified metrics; dataset-identity probe on learned representation; Phase 2 total-score baselines as comparator",
        "primary_metrics": "construct MAE or ordinal MAE; Macro-F1 when binarized; ECE; cross-scale calibration",
        "pass_rule": "improves cross-scale construct transfer or calibration over total-score baseline without same-dataset degradation above 5 percent relative",
        "stop_rule": "only improves same-dataset totals, worsens cross-dataset calibration, or increases dataset identity recoverability",
        "version_policy": "track script/config/summary; keep fold predictions and learned embeddings local-only",
    },
    {
        "protocol_id": "P5_MV02",
        "phase4_source_id": "MV02",
        "rq": "RQ1",
        "name": "hamd17_auxiliary_bridge",
        "status": "complete_pdch_only_diagnostic",
        "train_scope": "PDCH HAMD-17 item labels; CMDC HAMD-17 limited subset held for sanity check",
        "eval_scope": "PDCH subject-level folds; optional CMDC 25-subject HAMD sanity subset only",
        "target_contract": "C01-C09 shared where direct; C10-C13 auxiliary/scale-specific HAMD heads",
        "feature_contract": "frozen text/audio features; no raw clinical text in outputs",
        "model_contract": "shared core construct heads with HAMD-specific auxiliary heads",
        "required_controls": "exclude PDCH 034A missing-label rows; use manifest HAMD total as severity target; apply official HAMD code-9 exclusion when deriving totals from items; keep CMDC HAMD as limited sanity subset",
        "primary_metrics": "HAMD item MAE; HAMD total MAE/RMSE/Spearman; construct calibration where ordinalized",
        "pass_rule": "retains HAMD severity performance while improving construct interpretability or external calibration",
        "stop_rule": "auxiliary HAMD items dominate and no shared core construct improvement appears",
        "version_policy": "track aggregate metric summaries only; keep item-level predictions local-only",
    },
    {
        "protocol_id": "P5_MV03",
        "phase4_source_id": "MV03",
        "rq": "RQ1/RQ2",
        "name": "sds_total_external_stress",
        "status": "complete_negative_sds_stress",
        "train_scope": "no SDS item-level training; use shared representation trained elsewhere",
        "eval_scope": "EATD SDS total/severity with valence-stratified evaluation",
        "target_contract": "SDS total/severity only; no claim of SDS item-level supervision",
        "feature_contract": "frozen audio/text features as available; valence slices must remain subject-level",
        "model_contract": "scale-specific SDS total/severity head attached only for external validation",
        "required_controls": "positive/neutral/negative stratification; compare against Phase 3 EATD valence diagnostic",
        "primary_metrics": "SDS MAE/RMSE/Spearman or ordinal metrics; valence gap; ECE",
        "pass_rule": "generalizes to SDS total without stronger negative-valence shortcut than Phase 3 baseline",
        "stop_rule": "performance is driven by valence slice or no stronger than total-only baseline",
        "version_policy": "track valence-stratified summaries; keep row-level predictions local-only",
    },
    {
        "protocol_id": "P5_MV04",
        "phase4_source_id": "MV04",
        "rq": "RQ2",
        "name": "dataset_protocol_control_ablation",
        "status": "complete_diagnostic_identity_control",
        "train_scope": "minimal shared model on audited item/total labels only",
        "eval_scope": "E-DAIC/CMDC protocol slices, MODMA task slices, EATD valence slices, dataset identity probes",
        "target_contract": "all available constructs/totals with dataset and protocol labels used only as controls",
        "feature_contract": "frozen encoders and lightweight heads; no protocol labels at inference except for stratified reporting",
        "model_contract": "baseline shared heads versus dataset-balanced, protocol-balanced, or adversarial identity-control variants",
        "required_controls": "same subject-level splits; identity-probe before/after; no test-label tuning; report every slice even if unfavorable",
        "primary_metrics": "slice Macro-F1/MAE/QWK; worst-slice metric; identity balanced accuracy; protocol gap",
        "pass_rule": "reduces identity/protocol/task gap while preserving main-task metric within 5 percent relative",
        "stop_rule": "pooled metric improves but worst-slice or identity-probe evidence worsens",
        "version_policy": "track slice summaries and probe summaries; keep learned features/predictions local-only",
    },
    {
        "protocol_id": "P5_MV05",
        "phase4_source_id": "MV05",
        "rq": "RQ3",
        "name": "mpdd_context_calibration",
        "status": "complete_negative_context_calibration",
        "train_scope": "MPDD labeled train subjects only; age/personality/gait context axes",
        "eval_scope": "MPDD subject-level OOF; age and personality-bin calibration; gait psychomotor context checks",
        "target_contract": "PHQ-9 severity/total plus context validation for C04/C08/C12",
        "feature_contract": "audio/video features plus context summaries; do not use generic AVP concatenation as the default claim",
        "model_contract": "calibration/context module versus AV baseline and shuffled-personality controls",
        "required_controls": "age ECE; personality-bin ECE; shuffled personality; age-swap counterfactual; gait as context only",
        "primary_metrics": "QWK; ordinal MAE; Macro-F1; ECE; Brier Score; subgroup gap",
        "pass_rule": "improves subgroup calibration or robustness without relying on the personality shortcut signal alone",
        "stop_rule": "no calibration gain, or shuffling personality leaves the proposed context mechanism unchanged",
        "version_policy": "track subgroup summaries; keep row-level predictions and counterfactual rows local-only",
    },
    {
        "protocol_id": "P5_MV06",
        "phase4_source_id": "MV06",
        "rq": "RQ4",
        "name": "construct_evidence_localization",
        "status": "readiness_complete_ready_local_annotation",
        "train_scope": "not a separate trainer; consumes minimal model outputs",
        "eval_scope": "E-DAIC, CMDC, and PDCH item/construct predictions",
        "target_contract": "C01-C09 where item labels exist; C09 explicit-evidence-only",
        "feature_contract": "localized snippets/statistics only; no raw text dumps or source paths in artifacts",
        "model_contract": "post-hoc evidence audit tied to construct predictions and protocol controls",
        "required_controls": "highlight prompt/protocol artifacts separately from participant symptom evidence",
        "primary_metrics": "evidence agreement rate; prompt-artifact rate; construct-specific localization coverage",
        "pass_rule": "localized evidence aligns with predicted constructs and avoids protocol-only explanations",
        "stop_rule": "evidence mainly highlights prompts, fixed questions, or dataset identity",
        "version_policy": "track aggregate evidence summaries; keep raw snippets and per-subject rationales local-only unless deidentified and approved",
    },
]


METRIC_CONTRACT = [
    {
        "metric_id": "construct_ordinal_mae",
        "task_family": "construct_item_or_ordinal",
        "required_for": "P5_MV01;P5_MV02",
        "definition": "mean absolute error on item-derived construct ordinal targets",
        "primary": "yes",
        "notes": "report per construct and macro average",
    },
    {
        "metric_id": "macro_f1",
        "task_family": "binary_or_ordinal_bins",
        "required_for": "P5_MV01;P5_MV03;P5_MV04;P5_MV05",
        "definition": "macro-averaged F1 for binary depression or ordinal severity bins",
        "primary": "yes",
        "notes": "pair with balanced accuracy for binary tasks",
    },
    {
        "metric_id": "qwk",
        "task_family": "ordinal",
        "required_for": "P5_MV05",
        "definition": "quadratic weighted kappa for ordinal severity labels",
        "primary": "yes",
        "notes": "MPDD severity primary ordinal metric",
    },
    {
        "metric_id": "mae_rmse_spearman",
        "task_family": "total_score_regression",
        "required_for": "P5_MV02;P5_MV03",
        "definition": "standard total-score regression metrics",
        "primary": "yes",
        "notes": "use scale-specific score ranges and subject-level bootstrap CIs",
    },
    {
        "metric_id": "ece_brier",
        "task_family": "calibration",
        "required_for": "all",
        "definition": "expected calibration error and Brier score for probabilistic outputs",
        "primary": "yes",
        "notes": "required for subgroup calibration and safety of pooled claims",
    },
    {
        "metric_id": "worst_slice_gap",
        "task_family": "robustness",
        "required_for": "P5_MV04;P5_MV05",
        "definition": "difference between overall and weakest dataset/protocol/task/subgroup slice",
        "primary": "yes",
        "notes": "must be reported even when pooled metric improves",
    },
    {
        "metric_id": "identity_probe_balanced_accuracy",
        "task_family": "shortcut_probe",
        "required_for": "P5_MV01;P5_MV04",
        "definition": "balanced accuracy of a lightweight dataset/protocol classifier on learned or frozen representations",
        "primary": "yes",
        "notes": "lower is better only when main-task evidence is preserved",
    },
]


OUTPUT_POLICY = [
    {
        "artifact_class": "tracked",
        "patterns": "scripts; configs; reports; run summaries; aggregate metric summaries; small figures",
        "notes": "safe for Git when no raw text, source paths, bulky predictions, embeddings, or model weights are included",
    },
    {
        "artifact_class": "local_only",
        "patterns": "row-level predictions; learned embeddings; checkpoints; raw snippets; raw prompts; raw model responses",
        "notes": "keep ignored unless explicitly reviewed and force-added",
    },
    {
        "artifact_class": "blocked",
        "patterns": "raw audio; raw video; raw transcripts; source data paths; personal contact/payment identifiers",
        "notes": "must not be uploaded through this project repo",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(audit: dict[str, Any]) -> None:
    lines = [
        "# Phase 5 Minimal Method-Validation Protocol",
        "",
        f"Generated: `{audit['generated_at']}`",
        "",
        "## Purpose",
        "",
        "This protocol freezes what must be validated before full method construction. It consumes the Phase 3 failure-mode synthesis and the Phase 4 symptom ontology. It does not train models.",
        "",
        "## Gate",
        "",
        "Minimal validation may begin only with subject-level splits, frozen or explicitly documented feature contracts, dataset/protocol/task/subgroup reporting, and artifact hygiene. Direct pooled-performance claims remain disallowed until identity and protocol controls pass.",
        "",
        "## Experiment Rows",
        "",
    ]
    for row in EXPERIMENT_MATRIX:
        lines.append(f"- `{row['protocol_id']}` `{row['name']}` ({row['status']}): {row['model_contract']}")
    lines.extend(
        [
            "",
            "## Mandatory Controls",
            "",
            "- Dataset-stratified and protocol/task-stratified metrics before any pooled claim.",
            "- Dataset/protocol identity probe for learned representations used in pooled or cross-dataset claims.",
            "- Phase 2 total-score baselines as the comparator floor.",
            "- MPDD age/personality subgroup calibration and shuffled/counterfactual controls for context claims.",
            "- Explicit blocking of gender/health claims until structured MPDD metadata is available.",
            "- Explicit-evidence-only handling for C09 death/self-harm.",
            "",
            "## Output Files",
            "",
            "- `experiment_matrix.csv`",
            "- `metric_contract.csv`",
            "- `output_policy.csv`",
            "- `readiness_audit.json`",
            "",
            "## Next Handoff",
            "",
            "`P5_MV01`, `P5_MV02`, `P5_MV03`, `P5_MV04`, and `P5_MV05` have now run. `P5_MV06` readiness is complete and can proceed only as a local raw-text annotation workflow with tracked aggregate evidence summaries. Full method work remains blocked until stronger cross-dataset/control evidence is accumulated.",
        ]
    )
    (OUT_DIR / "minimal_validation_protocol.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene() -> dict[str, Any]:
    forbidden = [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"/root/",
            r"/autodl-tmp/",
            r"\baudio_path\b",
            r"\bvideo_path\b",
            r"\btext_path\b",
            r"\bgait_path\b",
            r"\.wav\b",
            r"\.mp3\b",
            r"\.mp4\b",
            r"personality_text",
            r"personality_description",
        ]
    ]
    violations = []
    for path in sorted(OUT_DIR.glob("*")):
        if path.suffix not in {".csv", ".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern.search(text):
                violations.append({"file": path.name, "pattern": pattern.pattern})
    return {
        "generated_at": utc_now(),
        "checked_file_count": sum(1 for path in OUT_DIR.glob("*") if path.suffix in {".csv", ".json", ".md"}),
        "passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    phase4_rows = read_csv(PHASE4_MATRIX)
    label_contract = read_csv(PHASE4_CONTRACT)
    missing_sources = [
        str(path.relative_to(ROOT))
        for path in [PHASE3_SYNTHESIS, PHASE4_MATRIX, PHASE4_CONTRACT]
        if not path.exists()
    ]
    if missing_sources:
        raise FileNotFoundError(f"missing prerequisite artifacts: {missing_sources}")

    write_csv(
        OUT_DIR / "experiment_matrix.csv",
        EXPERIMENT_MATRIX,
        [
            "protocol_id",
            "phase4_source_id",
            "rq",
            "name",
            "status",
            "train_scope",
            "eval_scope",
            "target_contract",
            "feature_contract",
            "model_contract",
            "required_controls",
            "primary_metrics",
            "pass_rule",
            "stop_rule",
            "version_policy",
        ],
    )
    write_csv(
        OUT_DIR / "metric_contract.csv",
        METRIC_CONTRACT,
        ["metric_id", "task_family", "required_for", "definition", "primary", "notes"],
    )
    write_csv(
        OUT_DIR / "output_policy.csv",
        OUTPUT_POLICY,
        ["artifact_class", "patterns", "notes"],
    )
    audit = {
        "generated_at": utc_now(),
        "phase3_synthesis": "analysis/phase3_diagnostics/phase3_stop_go_synthesis.md",
        "phase4_matrix": "analysis/phase4_symptom_ontology/minimal_validation_matrix.csv",
        "phase4_label_contract": "analysis/phase4_symptom_ontology/dataset_label_contract.csv",
        "phase4_source_rows": len(phase4_rows),
        "label_contract_rows": len(label_contract),
        "protocol_rows": len(EXPERIMENT_MATRIX),
        "metric_rows": len(METRIC_CONTRACT),
        "output_policy_rows": len(OUTPUT_POLICY),
        "full_method_allowed": False,
        "recommended_first_row": "P5_MV01",
        "recommended_next_ready_row": "P5_MV06_local_evidence_annotation_or_identity_protocol_extension",
        "readiness_complete_rows": [
            row["protocol_id"] for row in EXPERIMENT_MATRIX if row["status"].startswith("readiness_complete")
        ],
        "completed_rows": [row["protocol_id"] for row in EXPERIMENT_MATRIX if row["status"].startswith("complete")],
        "blocked_rows": [row["protocol_id"] for row in EXPERIMENT_MATRIX if row["status"].startswith("blocked")],
    }
    write_report(audit)
    hygiene = artifact_hygiene()
    if not hygiene["passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")
    audit["artifact_hygiene_passed"] = True
    audit["artifact_hygiene"] = hygiene
    (OUT_DIR / "readiness_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Phase 5 protocol artifacts to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
