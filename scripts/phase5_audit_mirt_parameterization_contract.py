#!/usr/bin/env python3
"""Audit the actual mirt multiple-group parameterization used by MV13/MV14.

This is a statistical correctness audit, not a new experiment. It checks the
implementation contract for reference/focal latent mean and variance,
anchor-linking constraints, and graded-response threshold parameters. Outputs
are aggregate code/protocol summaries only; no fitted parameter values, factor
scores, subject rows, row predictions, local workbooks, or clinical text are
exported.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
OUT_DIR = PHASE5_DIR / "p5_mirt_parameterization_correctness_audit"
MV13_R = ROOT / "scripts" / "phase5_run_mv13_external_psychometric_replication.R"
MV14_R = ROOT / "scripts" / "phase5_run_mv14_measurement_uncertainty_bootstrap.R"
MV10_ROLES = PHASE5_DIR / "p5_mv10_psychometric_invariance_baseline" / "partial_invariance_summary.csv"
MV13_SYNTAX = PHASE5_DIR / "p5_mv13_external_psychometric_replication" / "external_model_syntax_summary.csv"
MV13_RUN = PHASE5_DIR / "p5_mv13_external_psychometric_replication" / "run_summary.json"
MV14_RUN = PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap" / "run_summary.json"
MV14_DESIGN_REFS = (
    PHASE5_DIR / "p5_mv14_measurement_uncertainty_bootstrap_design" / "method_source_refs.csv"
)

TRACKED_FILES = [
    "anchor_linking_audit.csv",
    "artifact_hygiene_audit.json",
    "claim_impact_assessment.csv",
    "generated_syntax_audit.csv",
    "latent_hyperparameter_design_check.csv",
    "method_source_refs.csv",
    "mirt_call_audit.csv",
    "parameterization_contract_check.csv",
    "report.md",
    "run_summary.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs() -> None:
    for path in [MV13_R, MV14_R, MV10_ROLES, MV13_SYNTAX, MV13_RUN, MV14_RUN, MV14_DESIGN_REFS]:
        if not path.exists():
            raise FileNotFoundError(path)


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def audit_r_script(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    group_match = re.search(
        r"factor\s*\([^)]*levels\s*=\s*c\s*\(\s*[\"']([^\"']+)[\"']\s*,\s*[\"']([^\"']+)[\"']\s*\)",
        text,
        flags=re.DOTALL,
    )
    reference_group = group_match.group(1) if group_match else ""
    focal_group = group_match.group(2) if group_match else ""
    threshold_parameters = sorted(set(re.findall(r"\(\s*%d\s*,\s*(d[0-9]+)\s*\)", text)))
    return {
        "script": rel(path),
        "multiple_group_call_count": len(re.findall(r"\bmultipleGroup\s*\(", text)),
        "reference_group_from_factor_order": reference_group,
        "focal_group_from_factor_order": focal_group,
        "itemtype_graded_present": 'itemtype = rep("graded"' in text or 'itemtype <- rep("graded"' in text,
        "invariance_argument_present": bool(re.search(r"\binvariance\s*=", text)),
        "free_means_literal_present": "free_means" in text or "free_mean" in text,
        "free_var_literal_present": "free_var" in text or "free_vars" in text,
        "manual_constrainb_present": "CONSTRAINB" in text,
        "manual_slope_parameter_present": "a1" in text,
        "manual_threshold_parameters": ";".join(threshold_parameters),
        "manual_threshold_parameter_count": len(threshold_parameters),
    }


def mirt_latent_design_check() -> tuple[pd.DataFrame, str]:
    if shutil.which("Rscript") is None:
        return (
            pd.DataFrame(
                [
                    {
                        "parameterization_id": "rscript_unavailable",
                        "group": "",
                        "parameter": "",
                        "starting_value": "",
                        "estimated": "",
                    }
                ]
            ),
            "skipped_rscript_unavailable",
        )

    r_code = r'''
suppressPackageStartupMessages(library(mirt))
items <- sprintf("C%02d", 1:8)
dat <- as.data.frame(replicate(8, rep(0:3, times = 4), simplify = FALSE))
names(dat) <- items
group <- factor(rep(c("edaic", "cmdc"), each = 8), levels = c("edaic", "cmdc"))
model <- mirt.model("F = 1-8
CONSTRAINB = (1, a1), (1, d1), (1, d2), (1, d3)")
inspect <- function(parameterization_id, invariance_terms) {
  args <- list(
    data = dat,
    model = model,
    group = group,
    itemtype = rep("graded", 8),
    pars = "values"
  )
  if (length(invariance_terms) > 0) {
    args$invariance <- invariance_terms
  }
  values <- do.call(multipleGroup, args)
  rows <- values[values$item == "GROUP" & values$name %in% c("MEAN_1", "COV_11"), ]
  data.frame(
    parameterization_id = parameterization_id,
    group = as.character(rows$group),
    parameter = as.character(rows$name),
    starting_value = as.character(rows$value),
    estimated = as.character(rows$est),
    stringsAsFactors = FALSE
  )
}
out <- rbind(
  inspect("actual_no_invariance_argument", character()),
  inspect("anchor_items_plus_free_focal_hyperparameters", c("C01", "C04", "C05", "C07", "free_means", "free_var"))
)
write.csv(out, row.names = FALSE)
'''
    env = os.environ.copy()
    env.update(
        {
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    result = subprocess.run(
        ["Rscript", "-e", r_code],
        check=False,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return (
            pd.DataFrame(
                [
                    {
                        "parameterization_id": "rscript_check_failed",
                        "group": "",
                        "parameter": "",
                        "starting_value": "",
                        "estimated": "",
                    }
                ]
            ),
            "failed_rscript_parameter_design_check",
        )
    stdout = result.stdout.strip()
    csv_start = stdout.find('"parameterization_id"')
    if csv_start < 0:
        csv_start = stdout.find("parameterization_id")
    if csv_start < 0:
        raise ValueError("Rscript did not return a CSV parameter table")
    return pd.read_csv(StringIO(stdout[csv_start:])), "complete"


def parse_syntax_constraints(syntax: str) -> dict[str, set[str]]:
    item_map = {str(idx): f"C{idx:02d}" for idx in range(1, 9)}
    constraints: dict[str, set[str]] = {item: set() for item in item_map.values()}
    for idx, param in re.findall(r"\(\s*([0-9]+)\s*,\s*([ad][0-9]+)\s*\)", syntax):
        item = item_map.get(idx)
        if item is not None:
            constraints[item].add(param)
    return constraints


def build_syntax_audit() -> pd.DataFrame:
    syntax = pd.read_csv(MV13_SYNTAX)
    rows: list[dict[str, Any]] = []
    for _, row in syntax.iterrows():
        model_id = str(row["model_id"])
        model_syntax = str(row["mirt_model_syntax"])
        constraints = parse_syntax_constraints(model_syntax)
        constrained_items = [item for item, params in constraints.items() if params]
        threshold_items = [item for item, params in constraints.items() if {"d1", "d2", "d3"}.issubset(params)]
        loading_items = [item for item, params in constraints.items() if "a1" in params]
        rows.append(
            {
                "model_id": model_id,
                "uses_constrainb": "CONSTRAINB" in model_syntax,
                "loading_constrained_items": ";".join(loading_items),
                "threshold_constrained_items": ";".join(threshold_items),
                "constrained_item_count": len(constrained_items),
                "loading_constrained_item_count": len(loading_items),
                "threshold_constrained_item_count": len(threshold_items),
                "uses_d1_d2_d3_for_threshold_constraints": all(
                    {"d1", "d2", "d3"}.issubset(params) for item, params in constraints.items() if item in threshold_items
                )
                if threshold_items
                else False,
            }
        )
    return pd.DataFrame(rows)


def build_anchor_linking_audit() -> pd.DataFrame:
    roles = pd.read_csv(MV10_ROLES)
    partial = build_syntax_audit()
    partial_row = partial[partial["model_id"] == "partial_mv10"].iloc[0]
    loading_items = set(str(partial_row["loading_constrained_items"]).split(";")) - {""}
    threshold_items = set(str(partial_row["threshold_constrained_items"]).split(";")) - {""}
    rows: list[dict[str, Any]] = []
    for _, row in roles.iterrows():
        item = str(row["construct_id"])
        role = str(row["partial_invariance_role"])
        expected_loading = role in {"anchor_candidate", "metric_only_threshold_free"}
        expected_threshold = role == "anchor_candidate"
        rows.append(
            {
                "construct_id": item,
                "item_label_short": row["item_label_short"],
                "mv10_role": role,
                "expected_partial_mv10_loading_constraint": expected_loading,
                "observed_partial_mv10_loading_constraint": item in loading_items,
                "expected_partial_mv10_threshold_constraint": expected_threshold,
                "observed_partial_mv10_threshold_constraint": item in threshold_items,
                "anchor_linking_status": "pass"
                if expected_loading == (item in loading_items) and expected_threshold == (item in threshold_items)
                else "mismatch",
            }
        )
    return pd.DataFrame(rows)


def build_method_source_refs() -> pd.DataFrame:
    existing = pd.read_csv(MV14_DESIGN_REFS)
    has_mirt_dif = "mirt_DIF_docs" in set(existing.get("source_id", pd.Series(dtype=str)).astype(str))
    rows = [
        {
            "source_id": "mirt_multipleGroup_docs_reference_group",
            "source_url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
            "source_type": "official_package_documentation",
            "audit_use": "reference_and_focal_group_identification",
            "key_point": "The first factor level is the reference group; focal-group latent means and variances require explicit free_means/free_var invariance terms.",
        },
        {
            "source_id": "mirt_DIF_docs_anchor_equating",
            "source_url": "https://rdrr.io/cran/mirt/man/DIF.html",
            "source_type": "official_package_documentation",
            "audit_use": "DIF_anchor_linking_contract",
            "key_point": "DIF examples equate groups through anchor items while freeing focal-group latent hyperparameters; otherwise DIF tests can mix item effects with latent-distribution differences.",
        },
        {
            "source_id": "mv14_design_predeclared_source_refs",
            "source_url": rel(MV14_DESIGN_REFS),
            "source_type": "local_aggregate_design_artifact",
            "audit_use": "project_contract_consistency",
            "key_point": f"MV14 design source references include mirt DIF anchor-equating guidance: {bool_text(has_mirt_dif)}.",
        },
    ]
    return pd.DataFrame(rows)


def build_contract_checks(
    script_audit: pd.DataFrame,
    latent_check: pd.DataFrame,
    anchor_audit: pd.DataFrame,
    syntax_audit: pd.DataFrame,
) -> pd.DataFrame:
    observed_no_invariance = latent_check[
        latent_check["parameterization_id"].astype(str) == "actual_no_invariance_argument"
    ]
    focal_rows = observed_no_invariance[observed_no_invariance["group"].astype(str) == "cmdc"]
    focal_mean_free = bool(
        not focal_rows.empty
        and (
            focal_rows[focal_rows["parameter"].astype(str) == "MEAN_1"]["estimated"].astype(str).str.upper()
            == "TRUE"
        ).any()
    )
    focal_var_free = bool(
        not focal_rows.empty
        and (
            focal_rows[focal_rows["parameter"].astype(str) == "COV_11"]["estimated"].astype(str).str.upper()
            == "TRUE"
        ).any()
    )
    all_scripts_have_reference = bool(
        (script_audit["reference_group_from_factor_order"] == "edaic").all()
        and (script_audit["focal_group_from_factor_order"] == "cmdc").all()
    )
    all_scripts_lack_invariance_arg = bool((script_audit["invariance_argument_present"] == False).all())
    partial = syntax_audit[syntax_audit["model_id"] == "partial_mv10"].iloc[0]
    return pd.DataFrame(
        [
            {
                "check_id": "reference_focal_group_order",
                "expected_contract": "E-DAIC is the reference group and CMDC is the focal group.",
                "observed_contract": "All audited R scripts set factor levels to edaic,cmdc.",
                "status": "pass" if all_scripts_have_reference else "fail",
                "claim_effect": "Reference/focal naming in reports is code-consistent.",
            },
            {
                "check_id": "focal_latent_mean_variance",
                "expected_contract": "Anchor-linked DIF/invariance interpretation should free focal-group latent mean and variance while keeping the reference group fixed.",
                "observed_contract": "MV13/MV14 multipleGroup calls omit the invariance argument; mirt design check shows CMDC MEAN_1 and COV_11 fixed under the actual call.",
                "status": "fail" if all_scripts_lack_invariance_arg and not focal_mean_free and not focal_var_free else "pass",
                "claim_effect": "Current mirt outputs are fixed-group-hyperparameter qualitative screens, not final anchor-linked DIF evidence separated from latent distribution shifts.",
            },
            {
                "check_id": "anchor_linking_partial_mv10",
                "expected_contract": "C01/C04/C05/C07 constrain loadings and thresholds; C02/C03/C06 constrain loadings only; C08 is free.",
                "observed_contract": "partial_mv10 generated syntax matches MV10 roles by CONSTRAINB.",
                "status": "pass" if bool((anchor_audit["anchor_linking_status"] == "pass").all()) else "fail",
                "claim_effect": "Manual anchor item linking is internally consistent, apart from the missing focal hyperparameter release.",
            },
            {
                "check_id": "graded_threshold_parameterization",
                "expected_contract": "Four-category PHQ item responses use graded item parameters with three ordered threshold/intercept terms per item.",
                "observed_contract": f"R scripts use itemtype graded and constrain d1,d2,d3; partial_mv10 threshold-constrained item count is {partial['threshold_constrained_item_count']}.",
                "status": "pass"
                if bool((script_audit["itemtype_graded_present"] == True).all())
                and bool((script_audit["manual_threshold_parameter_count"] == 3).all())
                else "fail",
                "claim_effect": "Manuscript should call these mirt graded d-parameter threshold/intercept constraints, not exported raw cutpoint values.",
            },
        ]
    )


def build_claim_impact(contract: pd.DataFrame) -> pd.DataFrame:
    latent_failed = bool(
        not contract[
            (contract["check_id"] == "focal_latent_mean_variance") & (contract["status"] == "fail")
        ].empty
    )
    return pd.DataFrame(
        [
            {
                "claim_scope": "MV13_external_mirt_replication",
                "audit_result": "parameterization_mismatch" if latent_failed else "parameterization_consistent",
                "manuscript_boundary": "Use as a qualitative external mirt replication under fixed group hyperparameters; do not present as final anchor-linked DIF proof until rerun with anchor items plus free focal mean/variance.",
                "action_required": "Correct and rerun MV13, or explicitly state the fixed-hyperparameter limitation.",
                "blocking_for_submission": True,
            },
            {
                "claim_scope": "MV14_bootstrap_uncertainty",
                "audit_result": "parameterization_mismatch" if latent_failed else "parameterization_consistent",
                "manuscript_boundary": "Bootstrap frequencies describe the same fixed-hyperparameter mirt screen; they should not be used as identification-robust DIF stability until corrected.",
                "action_required": "Correct and rerun the bootstrap if manuscript needs formal mirt-backed DIF stability intervals.",
                "blocking_for_submission": True,
            },
            {
                "claim_scope": "MV10_MV11_MV19_label_only_core",
                "audit_result": "not_directly_invalidated_by_mirt_audit",
                "manuscript_boundary": "Keep the broader observed-N and in-repo label-only PHQ measurement caveats, but downgrade MV13/MV14 corroboration until corrected.",
                "action_required": "Do not strengthen PHQ DIF wording using MV13/MV14 before resolving the mirt parameterization issue.",
                "blocking_for_submission": True,
            },
            {
                "claim_scope": "full_method_gate",
                "audit_result": "gate_remains_blocked",
                "manuscript_boundary": "This audit reinforces the blocked full-method gate rather than opening a new experiment line.",
                "action_required": "Treat corrected mirt rerun as statistical correctness work, not as exploratory model iteration.",
                "blocking_for_submission": False,
            },
        ]
    )


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\bsubject_key\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"local_mirt_phq_response_matrix",
        r"local_mv14_phq_response_matrix",
        r"row-level",
        r"fitted parameter values",
        r"factor scores",
        r"clinical text",
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
        "artifact_hygiene_passed": not violations,
        "audit_id": "p5_mirt_parameterization_correctness_audit_hygiene",
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def write_report(out_dir: Path, run_summary: dict[str, Any], contract: pd.DataFrame) -> None:
    latent = contract[contract["check_id"] == "focal_latent_mean_variance"].iloc[0]
    lines = [
        "# mirt Parameterization Correctness Audit",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Audit status: `{run_summary['decision']['audit_status']}`.",
        f"- Statistical correctness blocker: `{run_summary['decision']['statistical_correctness_blocker']}`.",
        f"- Short read: {run_summary['decision']['short_read']}",
        "",
        "## Key Finding",
        "",
        latent["observed_contract"],
        "",
        latent["claim_effect"],
        "",
        "## Checks",
        "",
        "| check | status | effect |",
        "| --- | --- | --- |",
    ]
    for _, row in contract.iterrows():
        lines.append(f"| {row['check_id']} | {row['status']} | {row['claim_effect']} |")
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/phase5_audit_mirt_parameterization_contract.py",
            "python scripts/build_diagnostic_paper_claim_tables.py",
            "python scripts/build_diagnostic_paper_results_sections.py",
            "python scripts/build_diagnostic_paper_manuscript_draft.py",
            "```",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_outputs(out_dir: Path, generated_at: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    script_audit = pd.DataFrame([audit_r_script(MV13_R), audit_r_script(MV14_R)])
    latent_check, r_check_status = mirt_latent_design_check()
    syntax_audit = build_syntax_audit()
    anchor_audit = build_anchor_linking_audit()
    source_refs = build_method_source_refs()
    contract = build_contract_checks(script_audit, latent_check, anchor_audit, syntax_audit)
    impact = build_claim_impact(contract)

    script_audit.to_csv(out_dir / "mirt_call_audit.csv", index=False)
    latent_check.to_csv(out_dir / "latent_hyperparameter_design_check.csv", index=False)
    syntax_audit.to_csv(out_dir / "generated_syntax_audit.csv", index=False)
    anchor_audit.to_csv(out_dir / "anchor_linking_audit.csv", index=False)
    source_refs.to_csv(out_dir / "method_source_refs.csv", index=False)
    contract.to_csv(out_dir / "parameterization_contract_check.csv", index=False)
    impact.to_csv(out_dir / "claim_impact_assessment.csv", index=False)

    blocker = bool(
        not contract[
            (contract["check_id"] == "focal_latent_mean_variance") & (contract["status"] == "fail")
        ].empty
    )
    run_summary = {
        "artifact_hygiene_passed": False,
        "decision": {
            "audit_status": "complete_mirt_parameterization_mismatch" if blocker else "complete_mirt_parameterization_consistent",
            "statistical_correctness_blocker": blocker,
            "short_read": (
                "MV13/MV14 correctly set E-DAIC as reference, manually link anchors through CONSTRAINB, and use graded d1-d3 threshold/intercept constraints; however, the actual multipleGroup calls do not free CMDC latent mean/variance, so current mirt results must be treated as fixed-hyperparameter qualitative screens until corrected or explicitly limited."
                if blocker
                else "MV13/MV14 mirt parameterization matches the audited anchor-linked measurement-invariance contract."
            ),
        },
        "generated_at": generated_at,
        "input_contract": {
            "raw_data_scanned": False,
            "clinical_text_read": False,
            "row_level_outputs_read": False,
            "synthetic_mirt_design_check_used": True,
            "scripts_read": [rel(MV13_R), rel(MV14_R)],
            "aggregate_artifacts_read": [
                rel(MV10_ROLES),
                rel(MV13_SYNTAX),
                rel(MV13_RUN),
                rel(MV14_RUN),
                rel(MV14_DESIGN_REFS),
            ],
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "contract_check_rows": int(len(contract)),
            "anchor_audit_rows": int(len(anchor_audit)),
            "syntax_audit_rows": int(len(syntax_audit)),
            "claim_impact_rows": int(len(impact)),
            "r_design_check_status": r_check_status,
        },
        "run_id": "P5_mirt_parameterization_correctness_audit",
        "source_artifacts": {
            "mv13_r_script": rel(MV13_R),
            "mv14_r_script": rel(MV14_R),
            "mv13_syntax_summary": rel(MV13_SYNTAX),
            "mv10_roles": rel(MV10_ROLES),
        },
        "status": "complete",
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, contract)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, contract)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    run_summary = build_outputs(args.out_dir, utc_now())
    print(
        json.dumps(
            {
                "out_dir": rel(args.out_dir),
                "audit_status": run_summary["decision"]["audit_status"],
                "statistical_correctness_blocker": run_summary["decision"]["statistical_correctness_blocker"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
