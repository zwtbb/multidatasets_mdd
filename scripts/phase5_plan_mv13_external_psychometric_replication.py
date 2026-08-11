#!/usr/bin/env python3
"""Predeclare MV13 external psychometric replication.

This script is a design contract, not an external model run. It prepares the
claim boundary, local-only data/export policy, model ladder, pass/fail gates,
and runtime preflight for replicating MV10/MV11 PHQ measurement-invariance
conclusions with a mature psychometric workflow such as R mirt or lavaan.

It reads only aggregate MV10/MV11 and full-method gate artifacts. It does not
export item response rows, subject-grain labels, theta scores, fitted
parameters, or model objects.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv13_external_psychometric_replication_design"

MV10_DIR = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline"
MV11_DIR = PHASE5_DIR / "p5_mv11_formal_psychometric_confirmation"
FULL_GATE_DIR = PHASE5_DIR / "full_method_gate_audit"

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "external_model_ladder_contract.csv",
    "implementation_queue.csv",
    "input_boundary_contract.csv",
    "method_source_refs.csv",
    "pass_fail_gate_contract.csv",
    "report.md",
    "run_summary.json",
    "runtime_preflight.csv",
    "source_evidence_summary.csv",
]

METHOD_SOURCE_REFS = [
    {
        "source_id": "mirt_jss_2012",
        "url": "https://www.jstatsoft.org/article/view/v048i06",
        "source_type": "primary_package_paper",
        "use_in_mv13": "Use mirt as the preferred external package family for graded-response IRT replication.",
        "key_takeaway": "mirt estimates exploratory and confirmatory multidimensional IRT models by maximum-likelihood methods.",
    },
    {
        "source_id": "mirt_multipleGroup_docs",
        "url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
        "source_type": "official_package_documentation",
        "use_in_mv13": "Use multipleGroup for two-group PHQ-8/PHQ-9 graded-response model comparisons and DIF checks.",
        "key_takeaway": "multipleGroup supports dichotomous and polytomous multi-group IRT, equality constraints, invariance keywords, and DIF workflows.",
    },
    {
        "source_id": "lavaan_categorical_docs",
        "url": "https://lavaan.ugent.be/tutorial/cat.html",
        "source_type": "official_package_documentation",
        "use_in_mv13": "Use lavaan as an ordinal CFA sensitivity path when mirt is unavailable or nonconvergent.",
        "key_takeaway": "lavaan treats declared ordered endogenous variables as categorical and switches to WLSMV/DWLS-style estimation.",
    },
    {
        "source_id": "lavaan_multiple_groups_docs",
        "url": "https://lavaan.ugent.be/tutorial/groups.html",
        "source_type": "official_package_documentation",
        "use_in_mv13": "Use lavaan group syntax to define configural, constrained, and partial-invariance ordinal CFA sensitivity models.",
        "key_takeaway": "lavaan supports multiple-group fitting with group arguments and cross-group equality constraints.",
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
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def fmt(value: Any, digits: int = 3) -> str:
    numeric = safe_float(value)
    if numeric is None:
        return "NA"
    return f"{numeric:.{digits}f}"


def first_row(frame: pd.DataFrame, column: str, value: str) -> dict[str, Any]:
    rows = frame[frame[column].astype(str) == value]
    if rows.empty:
        raise ValueError(f"missing {column}={value}")
    return rows.iloc[0].to_dict()


def bool_count(series: pd.Series) -> int:
    return int(series.astype(str).str.lower().isin({"true", "1", "yes"}).sum())


def runtime_preflight() -> pd.DataFrame:
    rscript_available = shutil.which("Rscript") is not None
    package_status = {"mirt": "not_checked_no_rscript", "lavaan": "not_checked_no_rscript"}
    if rscript_available:
        probe = (
            "pkgs <- c('mirt','lavaan'); "
            "cat(paste(pkgs, sapply(pkgs, function(p) "
            "if (requireNamespace(p, quietly=TRUE)) as.character(packageVersion(p)) else 'missing'), "
            "sep='=', collapse=';'))"
        )
        result = subprocess.run(
            ["Rscript", "-e", probe],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            for item in result.stdout.strip().split(";"):
                if "=" in item:
                    name, status = item.split("=", 1)
                    package_status[name.strip()] = status.strip()
        else:
            package_status = {"mirt": "package_probe_failed", "lavaan": "package_probe_failed"}

    rows = [
        {
            "check_id": "Rscript_on_path",
            "status": "pass" if rscript_available else "blocked_runtime_missing",
            "observed": "available" if rscript_available else "missing",
            "decision": "MV13 execution can use R only after Rscript is available on PATH.",
        },
        {
            "check_id": "mirt_package",
            "status": "pass" if package_status["mirt"] not in {"missing", "not_checked_no_rscript", "package_probe_failed"} else "not_ready",
            "observed": package_status["mirt"],
            "decision": "mirt is the preferred external replication engine for multi-group graded-response IRT.",
        },
        {
            "check_id": "lavaan_package",
            "status": "pass" if package_status["lavaan"] not in {"missing", "not_checked_no_rscript", "package_probe_failed"} else "not_ready",
            "observed": package_status["lavaan"],
            "decision": "lavaan is the ordinal CFA sensitivity fallback if mirt is unavailable or does not converge.",
        },
        {
            "check_id": "external_runtime_ready",
            "status": "pass"
            if rscript_available
            and package_status["mirt"] not in {"missing", "not_checked_no_rscript", "package_probe_failed"}
            else "blocked_runtime_setup_required",
            "observed": "ready" if rscript_available and package_status["mirt"] not in {"missing", "not_checked_no_rscript", "package_probe_failed"} else "setup_required",
            "decision": "Do not run MV13 claims until the external runtime is installed and version-captured.",
        },
    ]
    return pd.DataFrame(rows)


def source_evidence_summary(preflight: pd.DataFrame) -> pd.DataFrame:
    mv10 = read_json(MV10_DIR / "run_summary.json")
    mv11 = read_json(MV11_DIR / "run_summary.json")
    full_gate = read_json(FULL_GATE_DIR / "run_summary.json")
    comparisons = read_csv(MV11_DIR / "invariance_comparison_summary.csv")
    anchors = read_csv(MV11_DIR / "anchor_confirmation_summary.csv")
    next_actions = read_csv(FULL_GATE_DIR / "next_action_queue.csv")

    mv10_v = mv10["verdict"]
    mv11_v = mv11["verdict"]
    metric = first_row(comparisons, "comparison_id", "metric_vs_configural")
    scalar = first_row(comparisons, "comparison_id", "scalar_vs_metric")
    partial = first_row(comparisons, "comparison_id", "partial_mv10_vs_configural")
    confirmed_anchors = anchors.loc[
        anchors["mv10_anchor_confirmed"].astype(str).str.lower() == "true",
        "construct_id",
    ].tolist()
    threshold_dif = anchors.loc[
        anchors["threshold_dif_flag"].astype(str).str.lower() == "true",
        "construct_id",
    ].tolist()
    loading_dif_count = bool_count(anchors["loading_dif_flag"])
    top_action = next_actions.sort_values("rank").iloc[0].to_dict()
    runtime_status = first_row(preflight, "check_id", "external_runtime_ready")

    rows = [
        {
            "source_id": "MV10_approximate_phq_screen",
            "artifact": rel(MV10_DIR / "run_summary.json"),
            "status": mv10_v["status"],
            "observation": (
                f"subjects_edaic={mv10['data_contract']['subjects']['edaic']}; "
                f"subjects_cmdc={mv10['data_contract']['subjects']['cmdc']}; "
                f"loading_congruence={fmt(mv10_v['loading_congruence'])}; "
                f"metric_items={mv10_v['metric_invariant_items']}/8; "
                f"threshold_items={mv10_v['threshold_invariant_items']}/8"
            ),
            "implication_for_mv13": "External replication must use the same PHQ C01-C08 label bridge and keep threshold/scalar claims conservative.",
        },
        {
            "source_id": "MV11_formal_irt_confirmation",
            "artifact": rel(MV11_DIR / "run_summary.json"),
            "status": mv11_v["status"],
            "observation": (
                f"confirmed_anchors={mv11_v['confirmed_mv10_anchor_items']}; "
                f"loading_DIF_flags={mv11_v['loading_dif_flagged_items']}; "
                f"threshold_DIF_flags={mv11_v['threshold_dif_flagged_items']}; "
                f"best_AIC={mv11_v['best_aic_model']}; best_BIC={mv11_v['best_bic_model']}"
            ),
            "implication_for_mv13": "MV13 should attempt to reproduce the qualitative partial-invariance conclusion outside the in-repo implementation.",
        },
        {
            "source_id": "MV11_nested_comparisons",
            "artifact": rel(MV11_DIR / "invariance_comparison_summary.csv"),
            "status": "bounded_formal_reference",
            "observation": (
                f"metric_vs_configural_p={fmt(metric['p_value'], 4)}; "
                f"scalar_vs_metric_p={fmt(scalar['p_value'], 4)}; "
                f"partial_vs_configural_p={fmt(partial['p_value'], 4)}"
            ),
            "implication_for_mv13": "Replication should compare configural, metric, scalar/threshold, and MV10 partial models rather than report only one fitted model.",
        },
        {
            "source_id": "MV11_anchor_and_DIF_map",
            "artifact": rel(MV11_DIR / "anchor_confirmation_summary.csv"),
            "status": "partial_anchor_map_reference",
            "observation": (
                f"anchors={';'.join(confirmed_anchors)}; "
                f"threshold_DIF={';'.join(threshold_dif)}; "
                f"loading_DIF_count={loading_dif_count}"
            ),
            "implication_for_mv13": "Primary qualitative agreement is anchor preservation plus threshold, not loading, DIF concentration.",
        },
        {
            "source_id": "full_method_gate",
            "artifact": rel(FULL_GATE_DIR / "run_summary.json"),
            "status": full_gate["gate_status"],
            "observation": (
                f"full_method_allowed={full_gate['full_method_allowed']}; "
                f"evidence_rows={full_gate['evidence_rows']}; "
                f"top_next_action={top_action['action_id']}"
            ),
            "implication_for_mv13": "MV13 can strengthen the measurement evidence pillar, but cannot by itself authorize full M0/M1/M2/M3.",
        },
        {
            "source_id": "runtime_preflight",
            "artifact": "runtime_preflight.csv",
            "status": runtime_status["status"],
            "observation": f"external_runtime={runtime_status['observed']}",
            "implication_for_mv13": "Predeclaration is complete, but execution waits for a version-captured external runtime.",
        },
    ]
    return pd.DataFrame(rows)


def input_boundary_contract() -> pd.DataFrame:
    rows = [
        {
            "input_id": "local_phq_item_response_matrix",
            "scope": "E-DAIC PHQ-8 and CMDC PHQ-9 shared C01-C08 ordinal item labels",
            "local_source_policy": "Build from manifest-governed item labels only inside the execution workspace.",
            "r_export_policy": "Allowed only as ignored local R input with no public release.",
            "tracked_surrogate": "aggregate dataset counts, item coverage counts, response-category support, and hygiene booleans",
            "forbidden_public_outputs": "participant-grain rows; local item-response matrix; fitted model objects; full item parameter table",
        },
        {
            "input_id": "group_variable",
            "scope": "Two-group E-DAIC versus CMDC scale/dataset membership",
            "local_source_policy": "Use only dataset labels already required for multi-group psychometric fitting.",
            "r_export_policy": "Local R input may contain group labels, but tracked output must aggregate by model and item.",
            "tracked_surrogate": "group sizes and fit/convergence summaries",
            "forbidden_public_outputs": "row-grain group assignments tied to item responses",
        },
        {
            "input_id": "mv10_mv11_anchor_reference",
            "scope": "C01/C04/C05/C07 anchors; C02/C06 threshold-DIF; C03/C08 sensitivity",
            "local_source_policy": "Read tracked aggregate MV10/MV11 anchor summaries before external fitting.",
            "r_export_policy": "May be encoded as local model syntax, not tracked as fitted output.",
            "tracked_surrogate": "anchor confirmation status and qualitative agreement summary",
            "forbidden_public_outputs": "post-hoc anchor changes chosen from held-out performance",
        },
        {
            "input_id": "runtime_versions",
            "scope": "R, mirt, lavaan, and system package versions",
            "local_source_policy": "Probe at execution time without installing packages inside the replication script.",
            "r_export_policy": "Version strings are safe to track.",
            "tracked_surrogate": "runtime_preflight and execution run summary",
            "forbidden_public_outputs": "credentials, local cache paths, package library paths",
        },
    ]
    return pd.DataFrame(rows)


def external_model_ladder_contract() -> pd.DataFrame:
    rows = [
        {
            "model_id": "M13_A_mirt_configural_GRM",
            "engine": "mirt",
            "model_family": "multi_group_graded_response_irt",
            "constraint_policy": "same one-factor structure; slopes and thresholds free by group",
            "required_outputs": "convergence, logLik, AIC, BIC, parameter count, group sizes",
            "interpretation_role": "tests whether the common PHQ item structure can be fit externally",
        },
        {
            "model_id": "M13_B_mirt_metric_slopes",
            "engine": "mirt",
            "model_family": "multi_group_graded_response_irt",
            "constraint_policy": "equal item slopes/discriminations across E-DAIC and CMDC; thresholds free",
            "required_outputs": "nested comparison versus configural; AIC/BIC deltas; convergence",
            "interpretation_role": "replicates the MV10/MV11 metric/loading conclusion",
        },
        {
            "model_id": "M13_C_mirt_scalar_thresholds",
            "engine": "mirt",
            "model_family": "multi_group_graded_response_irt",
            "constraint_policy": "equal slopes and thresholds across groups where engine semantics permit",
            "required_outputs": "comparison versus metric; AIC/BIC deltas; convergence and category-support warnings",
            "interpretation_role": "tests whether full threshold/scalar equivalence is externally supported",
        },
        {
            "model_id": "M13_D_mirt_partial_mv10",
            "engine": "mirt",
            "model_family": "multi_group_graded_response_irt",
            "constraint_policy": "constrain MV10 anchors C01/C04/C05/C07; free threshold-DIF items C02/C06; keep C03/C08 sensitivity",
            "required_outputs": "comparison against configural, metric, and scalar; anchor preservation summary",
            "interpretation_role": "primary replication of the partial-invariance measurement target",
        },
        {
            "model_id": "M13_E_mirt_DIF_checks",
            "engine": "mirt",
            "model_family": "DIF_diagnostic",
            "constraint_policy": "test item-level loading and threshold freeing against the selected anchor model",
            "required_outputs": "aggregate loading-DIF and threshold-DIF flags; no full fitted parameter export",
            "interpretation_role": "checks whether C02/C06 remain the strongest threshold-DIF candidates",
        },
        {
            "model_id": "M13_F_lavaan_ordinal_CFA_sensitivity",
            "engine": "lavaan",
            "model_family": "ordinal_multi_group_cfa",
            "constraint_policy": "ordered items; WLSMV/DWLS-style estimation; configural, metric, scalar/threshold, and partial syntax",
            "required_outputs": "convergence, fit indices, qualitative agreement/disagreement with mirt/MV11",
            "interpretation_role": "sensitivity path, not primary IRT replacement unless mirt fails",
        },
    ]
    return pd.DataFrame(rows)


def pass_fail_gate_contract(preflight: pd.DataFrame) -> pd.DataFrame:
    runtime_ready = first_row(preflight, "check_id", "external_runtime_ready")["status"] == "pass"
    rows = [
        {
            "gate_id": "G0_predeclaration_complete",
            "status": "pass",
            "current_evidence": "MV13 defines runtime checks, local-only input boundaries, external model ladder, fit/DIF outputs, and claim downgrades before execution.",
            "future_execution_rule": "Execution script must follow this contract or explicitly supersede it with a new predeclaration.",
            "claim_effect": "Design pass only; no new psychometric result yet.",
        },
        {
            "gate_id": "G1_external_runtime_ready",
            "status": "pass" if runtime_ready else "blocked_runtime_setup_required",
            "current_evidence": "Rscript and package preflight are recorded in runtime_preflight.csv.",
            "future_execution_rule": "Do not claim external replication until R/mirt or an equivalent mature workflow is available and version-captured.",
            "claim_effect": "Runtime missing blocks MV13 execution but not this predeclaration.",
        },
        {
            "gate_id": "G2_input_privacy_boundary",
            "status": "pass_for_design",
            "current_evidence": "Item response rows and R input files are declared local-only; tracked outputs are aggregate only.",
            "future_execution_rule": "No participant-grain item table, local R input, fitted model object, theta score, or full parameter table may enter Git.",
            "claim_effect": "Any boundary failure blocks publication until cleaned.",
        },
        {
            "gate_id": "G3_qualitative_replication",
            "status": "pending_external_run",
            "current_evidence": "MV10/MV11 reference conclusions are available from aggregate artifacts.",
            "future_execution_rule": "Primary pass means external results agree that one-factor/metric structure broadly holds and threshold/scalar equivalence is partial, with anchors broadly preserved.",
            "claim_effect": "If passed, MV11 becomes a stronger manuscript pillar; if failed, downgrade MV11 to in-repo exploratory evidence.",
        },
        {
            "gate_id": "G4_DIF_stability_and_disagreement",
            "status": "pending_external_run",
            "current_evidence": "MV11 flags C02/C06 threshold DIF and no strong loading DIF.",
            "future_execution_rule": "Report disagreements explicitly; do not convert single-engine DIF flags into strong clinical claims without MV14 bootstrap support.",
            "claim_effect": "Disagreement motivates MV14 or revised measurement wording, not full-method authorization.",
        },
        {
            "gate_id": "G5_no_full_method_authorization",
            "status": "pass_for_design",
            "current_evidence": "The Phase 5 full-method gate remains blocked.",
            "future_execution_rule": "Even a successful MV13 only strengthens label-measurement evidence; multimodal full method remains blocked until MV14-MV16 or a later gate changes.",
            "claim_effect": "No M0/M1/M2/M3 start from MV13 alone.",
        },
    ]
    return pd.DataFrame(rows)


def implementation_queue(preflight: pd.DataFrame) -> pd.DataFrame:
    runtime_ready = first_row(preflight, "check_id", "external_runtime_ready")["status"] == "pass"
    rows = [
        {
            "rank": 1,
            "action_id": "PREPARE_EXTERNAL_R_RUNTIME" if not runtime_ready else "CAPTURE_EXTERNAL_R_RUNTIME",
            "action": "Install or expose Rscript with mirt as the primary package and lavaan as a sensitivity fallback, then capture versions.",
            "success_gate": "runtime_preflight shows Rscript and mirt available; lavaan is available or its absence is explicitly documented.",
            "version_policy": "Track version summaries only; do not track package library paths or caches.",
        },
        {
            "rank": 2,
            "action_id": "CREATE_LOCAL_R_INPUT_EXPORT",
            "action": "Build an ignored local PHQ C01-C08 ordinal item-response file from manifest-governed labels.",
            "success_gate": "Local input has E-DAIC and CMDC group counts matching MV10/MV11 and complete category audits.",
            "version_policy": "Do not track local R input or participant-grain rows.",
        },
        {
            "rank": 3,
            "action_id": "RUN_MIRT_MODEL_LADDER",
            "action": "Run configural, metric, scalar/threshold, partial MV10 anchor, and DIF-check models in mirt.",
            "success_gate": "Aggregate fit, convergence, comparison, and DIF summaries are produced.",
            "version_policy": "Track aggregate summaries only; keep fitted objects and full parameter tables local-only.",
        },
        {
            "rank": 4,
            "action_id": "RUN_LAVAAN_SENSITIVITY_IF_NEEDED",
            "action": "Run ordinal multi-group CFA sensitivity in lavaan if mirt is missing, nonconvergent, or materially disagrees.",
            "success_gate": "Sensitivity results are compared qualitatively to MV11/mirt without overstating exact equivalence.",
            "version_policy": "Track aggregate fit and agreement summaries only.",
        },
        {
            "rank": 5,
            "action_id": "UPDATE_MEASUREMENT_CLAIM_BOUNDARY",
            "action": "Refresh issue log, master memory, paper claim tables, and full-method gate after MV13 execution.",
            "success_gate": "Claims distinguish external replication, unresolved runtime/setup issues, and any model disagreement.",
            "version_policy": "Commit code, docs, aggregate reports, and memory only after hygiene passes.",
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
        r"raw prompt",
        r"raw response",
        r"parameter_value",
        r"factor_score",
        r"posterior_score",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in TRACKED_FILES:
        path = out_dir / name
        if not path.exists() or not path.is_file():
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": name, "pattern": pattern})
    return {
        "audit_id": "p5_mv13_external_psychometric_replication_design_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(out_dir: Path, run_summary: dict[str, Any], preflight: pd.DataFrame) -> None:
    runtime_ready = run_summary["decision"]["external_runtime_ready"]
    lines = [
        "# P5 MV13 External Psychometric Replication Design",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Design status: `{run_summary['decision']['design_status']}`.",
        f"- External runtime ready: `{runtime_ready}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "- MV13 is an external replication contract, not a new psychometric result.",
        "",
        "## Runtime Preflight",
        "",
        "| check | status | observed |",
        "| --- | --- | --- |",
    ]
    for _, row in preflight.iterrows():
        lines.append(f"| {row['check_id']} | `{row['status']}` | {row['observed']} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "MV13 should strengthen or downgrade the MV10/MV11 measurement evidence, not authorize the full multimodal method by itself. A successful external replication means the qualitative conclusion holds in a mature external workflow: broad one-factor/metric PHQ structure, partial threshold/scalar equivalence, and broadly preserved anchors with model-selection caveats.",
            "",
            "## Next Step",
            "",
            "Prepare the external R/mirt runtime, then implement the execution runner against this contract. Keep local R inputs, fitted objects, full parameter tables, theta scores, and participant-grain rows local-only.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, generated_at: str, overwrite: bool) -> dict[str, Any]:
    if out_dir.exists() and overwrite:
        for name in TRACKED_FILES:
            path = out_dir / name
            if path.exists() and path.is_file():
                path.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    preflight = runtime_preflight()
    evidence = source_evidence_summary(preflight)
    inputs = input_boundary_contract()
    models = external_model_ladder_contract()
    gates = pass_fail_gate_contract(preflight)
    queue = implementation_queue(preflight)
    refs = method_source_refs()

    preflight.to_csv(out_dir / "runtime_preflight.csv", index=False)
    evidence.to_csv(out_dir / "source_evidence_summary.csv", index=False)
    inputs.to_csv(out_dir / "input_boundary_contract.csv", index=False)
    models.to_csv(out_dir / "external_model_ladder_contract.csv", index=False)
    gates.to_csv(out_dir / "pass_fail_gate_contract.csv", index=False)
    queue.to_csv(out_dir / "implementation_queue.csv", index=False)
    refs.to_csv(out_dir / "method_source_refs.csv", index=False)

    external_runtime_ready = first_row(preflight, "check_id", "external_runtime_ready")["status"] == "pass"
    design_status = (
        "ready_for_external_replication_run"
        if external_runtime_ready
        else "complete_predeclared_runtime_setup_required"
    )
    run_summary = {
        "run_id": "P5_MV13_external_psychometric_replication_design",
        "generated_at": generated_at,
        "scope": "external_psychometric_replication_predeclaration",
        "status": "complete",
        "input_contract": {
            "label_only": True,
            "datasets": ["edaic", "cmdc"],
            "scales": ["PHQ-8", "PHQ-9"],
            "shared_items": ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"],
            "multimodal_features_read": False,
            "raw_text_or_media_read": False,
            "row_level_predictions_read": False,
            "participant_grain_outputs_written": False,
            "local_r_input_written": False,
            "external_model_run_performed": False,
        },
        "runtime_preflight": {
            "rscript_available": bool(first_row(preflight, "check_id", "Rscript_on_path")["status"] == "pass"),
            "mirt_status": first_row(preflight, "check_id", "mirt_package")["observed"],
            "lavaan_status": first_row(preflight, "check_id", "lavaan_package")["observed"],
            "external_runtime_ready": bool(external_runtime_ready),
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "source_evidence_rows": int(len(evidence)),
            "input_contract_rows": int(len(inputs)),
            "model_contract_rows": int(len(models)),
            "gate_rows": int(len(gates)),
            "implementation_rows": int(len(queue)),
            "method_source_rows": int(len(refs)),
        },
        "decision": {
            "design_status": design_status,
            "external_runtime_ready": bool(external_runtime_ready),
            "short_read": (
                "MV13 is predeclared as an external mirt/lavaan psychometric replication. "
                "Execution waits for a version-captured external runtime."
            ),
            "next_action": "PREPARE_EXTERNAL_R_RUNTIME" if not external_runtime_ready else "RUN_MIRT_MODEL_LADDER",
            "full_method_allowed": False,
        },
        "artifact_hygiene_passed": False,
    }

    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, preflight)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    write_json(out_dir / "run_summary.json", run_summary)
    write_report(out_dir, run_summary, preflight)
    hygiene = artifact_hygiene(out_dir)
    write_json(out_dir / "artifact_hygiene_audit.json", hygiene)
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
                "external_runtime_ready": summary["decision"]["external_runtime_ready"],
                "artifact_hygiene_passed": summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
