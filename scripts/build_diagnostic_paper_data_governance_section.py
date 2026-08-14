#!/usr/bin/env python3
"""Build the data-governance and label-contract section for the paper.

This writing-prep script reads only registry fields and aggregate audit/Phase 4
tables. It intentionally excludes raw roots, local paths, row-level manifests,
private review workbooks, and subject-level identifiers from all outputs.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "datasets" / "registry.yaml"
FILE_INTEGRITY_SUMMARY = ROOT / "datasets" / "audit" / "file_integrity_summary.csv"
LABEL_DISTRIBUTION = ROOT / "datasets" / "audit" / "label_distribution.csv"
LABEL_CONTRACT = ROOT / "analysis" / "phase4_symptom_ontology" / "dataset_label_contract.csv"
CONSTRUCT_MAP = ROOT / "analysis" / "phase4_symptom_ontology" / "construct_scale_map.csv"
PHASE4_AUDIT = ROOT / "analysis" / "phase4_symptom_ontology" / "phase4_symptom_ontology_audit.json"
DEFAULT_OUT_DIR = ROOT / "analysis" / "diagnostic_measurement_audit_paper"

TRACKED_FILES = [
    "construct_coverage_summary.csv",
    "data_governance_artifact_hygiene_audit.json",
    "data_governance_label_contracts.md",
    "data_governance_report.md",
    "data_governance_run_summary.json",
    "dataset_governance_summary.csv",
    "label_contract_summary.csv",
    "release_boundary_summary.csv",
    "source_context_data_governance.csv",
]

DATASET_NAMES = {
    "edaic": "E-DAIC",
    "cmdc": "CMDC",
    "pdch": "PDCH",
    "modma": "MODMA",
    "eatd": "EATD-Corpus",
    "mpdd_avg_2026": "MPDD-AVG-2026",
}

SOURCE_ROWS = [
    {
        "dataset_or_topic": "E-DAIC/DAIC",
        "source_role": "official access and consent boundary",
        "citation_hint": "USC ICT DAIC-WOZ and Extended DAIC download page",
        "url": "https://dcapswoz.ict.usc.edu/",
        "use_in_section": "Supports restricted-data governance and local-only real manifest policy.",
    },
    {
        "dataset_or_topic": "DAIC",
        "source_role": "clinical-interview corpus origin",
        "citation_hint": "Gratch et al. 2014, LREC",
        "url": "https://aclanthology.org/L14-1421/",
        "use_in_section": "Supports the clinical-interview framing and multimodal questionnaire/transcript context.",
    },
    {
        "dataset_or_topic": "CMDC",
        "source_role": "Chinese semi-structured interview corpus",
        "citation_hint": "Zou et al. 2023, IEEE Transactions on Affective Computing",
        "url": "https://doi.org/10.1109/TAFFC.2022.3181210",
        "use_in_section": "Supports CMDC as Chinese clinical-interview validation with PHQ-9 and HAMD labels.",
    },
    {
        "dataset_or_topic": "PDCH",
        "source_role": "real consultation and HAMD-17 source",
        "citation_hint": "PDCH repository and dataset paper",
        "url": "https://github.com/Miraclemarvel55/PDCH",
        "use_in_section": "Supports PDCH as a bounded HAMD-17 consultation validation dataset.",
    },
    {
        "dataset_or_topic": "MODMA",
        "source_role": "controlled task stress-test source",
        "citation_hint": "MODMA dataset description",
        "url": "https://reshare.ukdataservice.ac.uk/854301/",
        "use_in_section": "Supports MODMA as an interview/reading/picture-description task robustness dataset.",
    },
    {
        "dataset_or_topic": "EATD-Corpus",
        "source_role": "Chinese valence stress-test source",
        "citation_hint": "EATD-Corpus repository",
        "url": "https://github.com/Fancy-Block/EATD-Corpus",
        "use_in_section": "Supports EATD as Chinese audio/text depression data with emotion-related tasks.",
    },
    {
        "dataset_or_topic": "MPDD",
        "source_role": "individual-difference benchmark source",
        "citation_hint": "MPDD Challenge official page",
        "url": "https://hacilab.github.io/MPDDChallenge.github.io/",
        "use_in_section": "Supports MPDD as the age/personality/health/gait context dataset.",
    },
    {
        "dataset_or_topic": "PHQ/HAMD measurement",
        "source_role": "scale-specific psychometric motivation",
        "citation_hint": "Ma et al. 2021, Frontiers in Psychiatry",
        "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        "use_in_section": "Supports not treating PHQ and HAMD as interchangeable raw item spaces.",
    },
    {
        "dataset_or_topic": "PHQ measurement invariance",
        "source_role": "measurement invariance and DIF context",
        "citation_hint": "Delamain et al. 2024, Journal of Affective Disorders",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37989437/",
        "use_in_section": "Supports the label-contract framing around measurement invariance and DIF.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_int(value: Any) -> int | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def list_text(values: Any) -> str:
    if isinstance(values, list):
        return ";".join(str(value) for value in values)
    return safe_str(values)


def require_inputs() -> None:
    for path in [REGISTRY, FILE_INTEGRITY_SUMMARY, LABEL_DISTRIBUTION, LABEL_CONTRACT, CONSTRUCT_MAP, PHASE4_AUDIT]:
        if not path.exists():
            raise FileNotFoundError(path)


def load_registry() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("registry must be a mapping")
    return data


def build_dataset_governance_summary() -> pd.DataFrame:
    registry = load_registry()
    integrity = pd.read_csv(FILE_INTEGRITY_SUMMARY)
    label_contract = pd.read_csv(LABEL_CONTRACT)

    primary_scale = (
        label_contract.sort_values(["dataset", "item_subjects", "total_subjects"], ascending=[True, False, False])
        .drop_duplicates("dataset")
        .set_index("dataset")
    )
    rows: list[dict[str, Any]] = []
    for _, audit_row in integrity.iterrows():
        dataset = str(audit_row["dataset"])
        info = registry.get(dataset, {})
        contract_row = primary_scale.loc[dataset] if dataset in primary_scale.index else {}
        rows.append(
            {
                "dataset": dataset,
                "display_name": DATASET_NAMES.get(dataset, dataset),
                "paper_role": safe_str(info.get("role")),
                "protocol_axis": safe_str(info.get("protocol")),
                "modalities": list_text(info.get("modalities")),
                "main_label_type": safe_str(info.get("label_type")),
                "subjects": safe_int(audit_row["subjects"]),
                "segments_or_rows": safe_int(audit_row["manifest_rows"]),
                "valid_rows": safe_int(audit_row["valid_rows"]),
                "status": safe_str(info.get("status")),
                "primary_scale": safe_str(contract_row.get("scale") if isinstance(contract_row, pd.Series) else ""),
                "item_supervision_status": safe_str(
                    contract_row.get("item_supervision_status") if isinstance(contract_row, pd.Series) else ""
                ),
                "paper_use": safe_str(info.get("notes")).split(".")[0],
                "data_quality_note": summarize_quality_note(dataset, audit_row, info),
            }
        )
    return pd.DataFrame(rows)


def summarize_quality_note(dataset: str, audit_row: pd.Series, info: dict[str, Any]) -> str:
    invalid = safe_int(audit_row.get("invalid_rows")) or 0
    status = safe_str(info.get("status"))
    notes = safe_str(info.get("notes"))
    if dataset == "cmdc":
        return "Metadata has duplicate/omitted subject-info entries; modality availability varies by row."
    if dataset == "pdch":
        return "One consultation subject lacks HAMD annotation; supervised HAMD rows use labeled subset only."
    if dataset == "modma":
        return f"{invalid} invalid audio rows are excluded; task type is a stress-test axis."
    if dataset == "mpdd_avg_2026":
        return "Local labels cover train subjects only; gender/health structured fields remain incomplete."
    if invalid:
        return f"{invalid} invalid rows are excluded."
    return notes.split(".")[0] if notes else status


def build_label_contract_summary() -> pd.DataFrame:
    contract = pd.read_csv(LABEL_CONTRACT)
    rows: list[dict[str, Any]] = []
    for _, row in contract.iterrows():
        rows.append(
            {
                "dataset": row["dataset"],
                "scale": row["scale"],
                "manifest_subjects": safe_int(row["manifest_subjects"]),
                "total_subjects": safe_int(row["total_subjects"]),
                "item_subjects": safe_int(row["item_subjects"]),
                "item_supervision_status": row["item_supervision_status"],
                "primary_use": row["primary_use"],
                "limitations": safe_str(row["limitations"]),
                "paper_claim_boundary": label_claim_boundary(row),
            }
        )
    return pd.DataFrame(rows)


def label_claim_boundary(row: pd.Series) -> str:
    status = str(row["item_supervision_status"])
    dataset = str(row["dataset"])
    scale = str(row["scale"])
    if status == "item_level_available" and dataset in {"edaic", "cmdc", "pdch"}:
        if dataset == "cmdc" and scale == "HAMD-17":
            return "sanity subset only; do not claim complete CMDC HAMD supervision"
        return "eligible for item-level minimal validation under subject-level splits"
    if status == "total_only":
        return "use as total/severity stress or context target only; no item-level construct claim"
    return "review before claim"


def build_construct_coverage_summary() -> pd.DataFrame:
    constructs = pd.read_csv(CONSTRUCT_MAP)
    rows: list[dict[str, Any]] = []
    for scale in ["PHQ-8", "PHQ-9", "HAMD-17", "SDS"]:
        column = f"{scale}_mapping"
        counts = Counter(str(value) for value in constructs[column].fillna("absent"))
        rows.append(
            {
                "scale": scale,
                "direct_constructs": counts.get("direct", 0),
                "partial_constructs": counts.get("partial", 0),
                "secondary_constructs": counts.get("secondary", 0),
                "absent_constructs": counts.get("absent", 0),
                "paper_interpretation": construct_interpretation(scale, counts),
            }
        )
    return pd.DataFrame(rows)


def construct_interpretation(scale: str, counts: Counter[str]) -> str:
    if scale in {"PHQ-8", "PHQ-9"}:
        return "cleanest core PHQ bridge, especially C01-C08; PHQ-9 alone includes C09"
    if scale == "HAMD-17":
        return "clinician-rated HAMD includes core items plus anxiety/somatic/insight content"
    return "SDS is broad self-report and currently total-only in EATD; use cautiously for stress testing"


def build_release_boundary_summary() -> pd.DataFrame:
    rows = [
        {
            "artifact_family": "raw data and media",
            "examples": "audio; video; raw transcripts; archives",
            "release_policy": "local_only",
            "rationale": "dataset licenses, consent boundaries, and file size",
        },
        {
            "artifact_family": "real row-level tables",
            "examples": "real subject manifests; real file-integrity rows; real split maps",
            "release_policy": "local_only",
            "rationale": "contains identifiers, labels, or local file references",
        },
        {
            "artifact_family": "model internals and private review",
            "examples": "row predictions; learned parameters; embeddings; verbatim excerpts; annotation workbooks",
            "release_policy": "local_only_by_default",
            "rationale": "privacy and artifact-hygiene boundary",
        },
        {
            "artifact_family": "public reproducibility skeleton",
            "examples": "scripts; registry roles; schemas; synthetic examples; aggregate audits",
            "release_policy": "track_in_git",
            "rationale": "supports reproducibility without redistributing sensitive data",
        },
        {
            "artifact_family": "paper-critical summaries",
            "examples": "claim gates; aggregate metric tables; hygiene audits; writing scaffolds",
            "release_policy": "track_in_git_after_hygiene",
            "rationale": "needed for manuscript traceability and does not expose row-level material",
        },
    ]
    return pd.DataFrame(rows)


def build_source_context() -> pd.DataFrame:
    return pd.DataFrame(SOURCE_ROWS)


def md_escape(value: Any) -> str:
    return safe_str(value).replace("|", "\\|").replace("\n", " ")


def write_section(
    out_dir: Path,
    dataset_summary: pd.DataFrame,
    label_summary: pd.DataFrame,
    construct_summary: pd.DataFrame,
    release_summary: pd.DataFrame,
    source_context: pd.DataFrame,
    generated_at: str,
) -> None:
    phase4 = read_json(PHASE4_AUDIT)
    item_available = label_summary[label_summary["item_supervision_status"] == "item_level_available"]
    total_only = label_summary[label_summary["item_supervision_status"] == "total_only"]
    lines = [
        "# Data Governance and Label Contracts",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Draft Section",
        "",
        "This study treats cross-dataset depression detection as a measurement problem before it treats it as a model-capacity problem. The data layer is governed by a registry-first workflow: each corpus is assigned a scientific role, protocol axis, modality set, and label contract before any pooled modeling claim is considered. Raw datasets and real row-level tables remain local-only; the public repository contains scripts, schemas, synthetic examples, aggregate audits, claim gates, and paper-critical summaries.",
        "",
        f"The governed corpus currently spans `{len(dataset_summary)}` datasets and `{int(dataset_summary['subjects'].sum())}` audited subjects. Phase 4 defines `{phase4['construct_count']}` symptom constructs and `{phase4['scale_item_count']}` mapped scale items. Item-level supervision is available for `{len(item_available)}` dataset-scale contracts and absent or total-only for `{len(total_only)}` contracts. This difference is central to the paper: PHQ-8/PHQ-9 provide the cleanest C01-C08 shared bridge, PDCH provides the strongest HAMD-17 item-level clinical validation, CMDC HAMD remains a small sanity subset, and EATD/MODMA/MPDD primarily serve stress-test or context roles rather than item-level construct supervision.",
        "",
        "The release boundary is deliberately conservative. Real identifiers, labels at row granularity, local file references, media, raw transcripts, learned parameters, embeddings, row predictions, private evidence workbooks, and verbatim evidence excerpts remain local-only. Public artifacts are limited to code, schemas, synthetic examples, aggregate audit summaries, and paper-facing tables that pass artifact hygiene. This policy preserves reproducibility of the experimental logic without redistributing licensed or privacy-sensitive material.",
        "",
        "## Dataset Governance Summary",
        "",
        "| dataset | role | protocol | modalities | subjects | valid rows | main label | claim role | quality note |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for _, row in dataset_summary.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["display_name"]),
                    md_escape(row["paper_role"]),
                    md_escape(row["protocol_axis"]),
                    md_escape(row["modalities"]),
                    md_escape(row["subjects"]),
                    md_escape(row["valid_rows"]),
                    md_escape(row["main_label_type"]),
                    md_escape(row["paper_use"]),
                    md_escape(row["data_quality_note"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Label Contract Summary",
            "",
            "| dataset | scale | total subjects | item subjects | supervision | paper boundary |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for _, row in label_summary.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(DATASET_NAMES.get(row["dataset"], row["dataset"])),
                    md_escape(row["scale"]),
                    md_escape(row["total_subjects"]),
                    md_escape(row["item_subjects"]),
                    md_escape(row["item_supervision_status"]),
                    md_escape(row["paper_claim_boundary"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Construct Coverage",
            "",
            "| scale | direct | partial | secondary | absent | interpretation |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for _, row in construct_summary.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["scale"]),
                    md_escape(row["direct_constructs"]),
                    md_escape(row["partial_constructs"]),
                    md_escape(row["secondary_constructs"]),
                    md_escape(row["absent_constructs"]),
                    md_escape(row["paper_interpretation"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Release Boundary",
            "",
            "| artifact family | examples | policy | rationale |",
            "| --- | --- | --- | --- |",
        ]
    )
    for _, row in release_summary.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["artifact_family"]),
                    md_escape(row["examples"]),
                    md_escape(row["release_policy"]),
                    md_escape(row["rationale"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Source Context",
            "",
            "| dataset or topic | source role | citation hint | URL | use in section |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in source_context.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(row["dataset_or_topic"]),
                    md_escape(row["source_role"]),
                    md_escape(row["citation_hint"]),
                    md_escape(row["url"]),
                    md_escape(row["use_in_section"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Manuscript Guardrails",
            "",
            "- Do not describe EATD, MODMA, or MPDD as item-level construct-supervision datasets under the current manifest.",
            "- Do not claim CMDC HAMD as a complete bridge; it is a small sanity subset.",
            "- Do not use public tables as substitutes for the local manifest layer when running experiments.",
            "- Re-check official dataset and scale citations before final manuscript submission.",
        ]
    )
    (out_dir / "data_governance_label_contracts.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    lines = [
        "# Data Governance Section Build Report",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This artifact prepares the diagnostic paper's Data Governance and Label Contracts section from registry and aggregate audit tables only.",
        "",
        "## Outputs",
        "",
        f"- Dataset governance rows: `{run_summary['outputs']['dataset_governance_rows']}`.",
        f"- Label contract rows: `{run_summary['outputs']['label_contract_rows']}`.",
        f"- Construct coverage rows: `{run_summary['outputs']['construct_coverage_rows']}`.",
        f"- Release-boundary rows: `{run_summary['outputs']['release_boundary_rows']}`.",
        f"- Source-context rows: `{run_summary['outputs']['source_context_rows']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
    ]
    (out_dir / "data_governance_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\braw_root\b",
        r"\bsubject_id\b",
        r"\bsession_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"source_locator",
        r"raw snippet",
        r"raw evidence snippet",
        r"row-level prediction",
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
        "audit_id": "diagnostic_paper_data_governance_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
    }


def build_outputs(out_dir: Path, generated_at: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset_summary = build_dataset_governance_summary()
    label_summary = build_label_contract_summary()
    construct_summary = build_construct_coverage_summary()
    release_summary = build_release_boundary_summary()
    source_context = build_source_context()

    dataset_summary.to_csv(out_dir / "dataset_governance_summary.csv", index=False)
    label_summary.to_csv(out_dir / "label_contract_summary.csv", index=False)
    construct_summary.to_csv(out_dir / "construct_coverage_summary.csv", index=False)
    release_summary.to_csv(out_dir / "release_boundary_summary.csv", index=False)
    source_context.to_csv(out_dir / "source_context_data_governance.csv", index=False)
    write_section(out_dir, dataset_summary, label_summary, construct_summary, release_summary, source_context, generated_at)

    stale_hygiene = out_dir / "data_governance_artifact_hygiene_audit.json"
    if stale_hygiene.exists():
        stale_hygiene.unlink()

    run_summary = {
        "run_id": "diagnostic_paper_data_governance_section",
        "generated_at": generated_at,
        "status": "complete",
        "input_contract": {
            "registry_read": True,
            "aggregate_dataset_audit_read": True,
            "phase4_label_contract_read": True,
            "raw_data_scanned": False,
            "row_level_manifests_read": False,
            "private_review_material_read": False,
            "raw_paths_written": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "dataset_governance_rows": int(len(dataset_summary)),
            "label_contract_rows": int(len(label_summary)),
            "construct_coverage_rows": int(len(construct_summary)),
            "release_boundary_rows": int(len(release_summary)),
            "source_context_rows": int(len(source_context)),
        },
        "decision": {
            "section_status": "ready_for_manuscript_drafting",
            "short_read": "Data governance and label-contract draft section is ready from registry and aggregate audit sources.",
        },
        "artifact_hygiene_passed": False,
    }
    (out_dir / "data_governance_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "data_governance_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "data_governance_artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see data_governance_artifact_hygiene_audit.json")
    return run_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    generated_at = utc_now()
    run_summary = build_outputs(args.out_dir, generated_at)
    print(
        "Wrote data governance paper section to "
        f"{args.out_dir.relative_to(ROOT)} with status "
        f"{run_summary['decision']['section_status']}"
    )


if __name__ == "__main__":
    main()
