#!/usr/bin/env python3
"""Assemble a v0.1 manuscript draft from aggregate paper artifacts.

This is a writing-prep script, not an experiment runner. It reads only
aggregate paper scaffolds, claim tables, source-context tables, and run
summaries that have already passed their own hygiene gates. It does not read
raw datasets, row-level predictions, local review workbooks, learned
parameters, embeddings, or private clinical text.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "analysis" / "diagnostic_measurement_audit_paper"
DEFAULT_OUT_DIR = PAPER_DIR

DATA_GOVERNANCE_MD = PAPER_DIR / "data_governance_label_contracts.md"
RESULTS_MD = PAPER_DIR / "baselines_failure_modes_measurement_results.md"
CLAIMS_CSV = PAPER_DIR / "paper_claim_boundary.csv"
FINDINGS_CSV = PAPER_DIR / "key_numeric_findings.csv"
LITERATURE_CSV = PAPER_DIR / "literature_positioning.csv"
DATASET_GOVERNANCE_CSV = PAPER_DIR / "dataset_governance_summary.csv"
LABEL_CONTRACT_CSV = PAPER_DIR / "label_contract_summary.csv"
RESULTS_CHECKLIST_CSV = PAPER_DIR / "results_section_claim_checklist.csv"
RESULTS_SOURCE_MAP_CSV = PAPER_DIR / "results_section_source_map.csv"
DATA_GOVERNANCE_SOURCE_CSV = PAPER_DIR / "source_context_data_governance.csv"
CLAIM_TABLES_SUMMARY = PAPER_DIR / "run_summary.json"
DATA_GOVERNANCE_SUMMARY = PAPER_DIR / "data_governance_run_summary.json"
RESULTS_SUMMARY = PAPER_DIR / "results_section_run_summary.json"
FULL_GATE_SUMMARY = ROOT / "analysis" / "phase5_minimal_validation" / "full_method_gate_audit" / "run_summary.json"
BIBLIOGRAPHY_SUMMARY = PAPER_DIR / "bibliography_run_summary.json"
CITATION_SOURCE_MAP_CSV = PAPER_DIR / "citation_source_map.csv"
REFERENCES_BIB = PAPER_DIR / "references.bib"

TRACKED_FILES = [
    "manuscript_artifact_hygiene_audit.json",
    "manuscript_draft.md",
    "manuscript_open_items.csv",
    "manuscript_report.md",
    "manuscript_run_summary.json",
    "manuscript_traceability_matrix.csv",
]
HYGIENE_CHECKED_FILES = [
    name for name in TRACKED_FILES if name != "manuscript_artifact_hygiene_audit.json"
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs() -> None:
    for path in [
        DATA_GOVERNANCE_MD,
        RESULTS_MD,
        CLAIMS_CSV,
        FINDINGS_CSV,
        LITERATURE_CSV,
        DATASET_GOVERNANCE_CSV,
        LABEL_CONTRACT_CSV,
        RESULTS_CHECKLIST_CSV,
        RESULTS_SOURCE_MAP_CSV,
        DATA_GOVERNANCE_SOURCE_CSV,
        CLAIM_TABLES_SUMMARY,
        DATA_GOVERNANCE_SUMMARY,
        RESULTS_SUMMARY,
        FULL_GATE_SUMMARY,
    ]:
        if not path.exists():
            raise FileNotFoundError(path)


def md_escape(value: Any) -> str:
    text = "" if value is None else str(value)
    if isinstance(value, float) and math.isnan(value):
        return ""
    return text.replace("|", "\\|").replace("\n", " ")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def read_section(path: Path, start_heading: str, end_heading: str | None) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.find(start_heading)
    if start < 0:
        raise ValueError(f"{rel(path)} missing heading {start_heading!r}")
    end = len(text)
    if end_heading is not None:
        found = text.find(end_heading, start + len(start_heading))
        if found < 0:
            raise ValueError(f"{rel(path)} missing heading {end_heading!r}")
        end = found
    return text[start:end].strip()


def markdown_table(df: pd.DataFrame, columns: list[str], headers: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(md_escape(row[column]) for column in columns) + " |")
    return lines


def row_by_id(df: pd.DataFrame, column: str, value: str) -> pd.Series:
    rows = df[df[column].astype(str) == value]
    if rows.empty:
        raise ValueError(f"missing {column}={value}")
    return rows.iloc[0]


def compact_sentence(text: str, max_chars: int = 520) -> str:
    cleaned = re.sub(r"\s+", " ", clean_text(text))
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def build_traceability(claims: pd.DataFrame, checklist: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in claims.iterrows():
        source_artifact_ids = clean_text(row["source_artifact_ids"])
        rows.append(
            {
                "trace_type": "claim_boundary",
                "manuscript_section": row["paper_section"],
                "claim_or_scope": row["claim_id"],
                "status": row["decision"],
                "evidence_summary": compact_sentence(row["evidence_to_report"], 700),
                "guardrail": row["manuscript_guardrail"],
                "source_artifact_ids": source_artifact_ids,
                "source_artifact_count": len([item for item in source_artifact_ids.split(";") if item]),
            }
        )
    for _, row in checklist.iterrows():
        rows.append(
            {
                "trace_type": "results_claim_checklist",
                "manuscript_section": "Results",
                "claim_or_scope": row["claim_scope"],
                "status": row["claim_status"],
                "evidence_summary": row["evidence"],
                "guardrail": row["guardrail"],
                "source_artifact_ids": "results_section_claim_checklist",
                "source_artifact_count": 1,
            }
        )
    return pd.DataFrame(rows)


def bibliography_status() -> dict[str, Any]:
    if not BIBLIOGRAPHY_SUMMARY.exists() or not REFERENCES_BIB.exists() or not CITATION_SOURCE_MAP_CSV.exists():
        return {
            "bibliography_available": False,
            "bibliography_status": "missing",
            "artifact_hygiene_passed": False,
        }
    summary = read_json(BIBLIOGRAPHY_SUMMARY)
    return {
        "bibliography_available": True,
        "bibliography_status": summary["decision"]["bibliography_status"],
        "artifact_hygiene_passed": bool(summary["artifact_hygiene_passed"]),
        "reference_rows": summary["outputs"]["reference_rows"],
        "source_context_rows": summary["outputs"]["source_context_rows"],
    }


def build_open_items(bib_status: dict[str, Any]) -> pd.DataFrame:
    if bib_status["bibliography_available"] and bib_status["artifact_hygiene_passed"]:
        citation_item = "Verify every bibliography row against DOI/publisher/ACL/arXiv metadata, then insert generated citation keys from references.bib into prose and adapt formatting to the target venue."
    else:
        citation_item = "Convert citation hints and source URLs into a formal bibliography, verify metadata against primary sources, and then perform venue-specific citation editing."
    rows = [
        {
            "item_id": "M002",
            "priority": "high",
            "area": "bibliography",
            "open_item": citation_item,
            "blocking_for_submission": True,
        },
        {
            "item_id": "M003",
            "priority": "high",
            "area": "claim_boundary",
            "open_item": "Keep full M0/M1/M2/M3 method claims blocked unless a genuinely new predeclared mechanism changes the full-method gate.",
            "blocking_for_submission": True,
        },
        {
            "item_id": "M006",
            "priority": "medium",
            "area": "criterion_contamination",
            "open_item": "Design a criterion-contamination stress test that separates mirror-like interview/question turns from non-mirror turns before adding any new protocol-bias method.",
            "blocking_for_submission": False,
        },
        {
            "item_id": "M007",
            "priority": "medium",
            "area": "RQ4",
            "open_item": "Resolve the one incomplete local CMDC MV06 candidate if annotator rows become available; otherwise keep RQ4 as first-round aggregate credibility evidence.",
            "blocking_for_submission": False,
        },
        {
            "item_id": "M008",
            "priority": "medium",
            "area": "limitations",
            "open_item": "Decide whether to run a larger corrected MV14 bootstrap only if interval precision becomes reviewer-critical.",
            "blocking_for_submission": False,
        },
        {
            "item_id": "M009",
            "priority": "medium",
            "area": "protocol",
            "open_item": "Speaker-resolved E-DAIC interviewer/participant controls remain optional unless the Results need a literal speaker-role claim.",
            "blocking_for_submission": False,
        },
        {
            "item_id": "M010",
            "priority": "medium",
            "area": "MPDD",
            "open_item": "Recover structured MPDD gender/health metadata only if population stress-test claims become central; do not revive personality-aware modeling as a main contribution.",
            "blocking_for_submission": False,
        },
    ]
    return pd.DataFrame(rows)


def source_reference_rows(literature: pd.DataFrame, governance_sources: pd.DataFrame) -> pd.DataFrame:
    if CITATION_SOURCE_MAP_CSV.exists():
        source_map = pd.read_csv(CITATION_SOURCE_MAP_CSV)
        rows = [
            {
                "citation_key": clean_text(row["citation_key"]),
                "source": clean_text(row["citation_hint"]),
                "url": clean_text(row["source_url"]),
                "use": clean_text(row["use_in_paper"]),
            }
            for _, row in source_map.iterrows()
        ]
        result = pd.DataFrame(rows).drop_duplicates(["citation_key", "source", "url"])
        return result.sort_values(["citation_key", "source", "url"]).reset_index(drop=True)

    rows: list[dict[str, str]] = []
    for _, row in literature.iterrows():
        rows.append(
            {
                "citation_key": "",
                "source": clean_text(row["citation_hint"]),
                "url": clean_text(row["url"]),
                "use": clean_text(row["paper_positioning"]),
            }
        )
    for _, row in governance_sources.iterrows():
        rows.append(
            {
                "citation_key": "",
                "source": clean_text(row["citation_hint"]),
                "url": clean_text(row["url"]),
                "use": clean_text(row["use_in_section"]),
            }
        )
    result = pd.DataFrame(rows).drop_duplicates(["source", "url"]).sort_values(["source", "url"])
    return result.reset_index(drop=True)


def humanize(value: Any) -> str:
    return clean_text(value).replace("_", " ")


def humanize_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        result[column] = result[column].map(humanize)
    return result


def build_manuscript(
    generated_at: str,
    claims: pd.DataFrame,
    findings: pd.DataFrame,
    literature: pd.DataFrame,
    dataset_governance: pd.DataFrame,
    label_contracts: pd.DataFrame,
    governance_sources: pd.DataFrame,
    traceability: pd.DataFrame,
    open_items: pd.DataFrame,
) -> str:
    full_gate = read_json(FULL_GATE_SUMMARY)
    claim_summary = read_json(CLAIM_TABLES_SUMMARY)
    data_summary = read_json(DATA_GOVERNANCE_SUMMARY)
    results_summary = read_json(RESULTS_SUMMARY)
    bib_status = bibliography_status()

    gate = row_by_id(findings, "finding_id", "gate_status")
    rq1 = row_by_id(findings, "finding_id", "rq1_measurement_negative")
    bge_caveat = row_by_id(findings, "finding_id", "legacy_bge_feature_contract_caveat")
    mv06 = row_by_id(findings, "finding_id", "mv06_first_round_evidence")
    mv14 = row_by_id(findings, "finding_id", "mv14_measurement_uncertainty_bootstrap")
    mv19 = row_by_id(findings, "finding_id", "mv19_finite_sample_phq_simulation")
    mv16 = row_by_id(findings, "finding_id", "mv16_dif_guided_calibration_run")

    governance_body = read_section(DATA_GOVERNANCE_MD, "## Draft Section", "## Dataset Governance Summary")
    results_body = read_section(RESULTS_MD, "## Draft Section: Baselines", "## Manuscript Guardrails")
    results_body = results_body.replace("## Draft Section: Baselines", "### Baselines")
    results_body = results_body.replace("## Draft Section: Failure-Mode Diagnostics", "### Failure-Mode Diagnostics")
    results_body = results_body.replace("## Draft Section: Measurement Results", "### Measurement Results")
    source_refs = source_reference_rows(literature, governance_sources)

    dataset_table = humanize_columns(
        dataset_governance[
            [
                "display_name",
                "paper_role",
                "protocol_axis",
                "modalities",
                "subjects",
                "valid_rows",
                "primary_scale",
                "item_supervision_status",
                "data_quality_note",
            ]
        ],
        [
            "paper_role",
            "protocol_axis",
            "modalities",
            "item_supervision_status",
        ],
    )
    label_table = humanize_columns(
        label_contracts[
            [
                "dataset",
                "scale",
                "total_subjects",
                "item_subjects",
                "item_supervision_status",
                "paper_claim_boundary",
            ]
        ],
        [
            "dataset",
            "item_supervision_status",
            "paper_claim_boundary",
        ],
    )

    lines = [
        "# Before Aligning Representations, Align the Target",
        "",
        "A Measurement-Validity Audit of Cross-Corpus Depression Detection",
        "",
        f"Generated: `{generated_at}`",
        "",
        "## Draft Status",
        "",
        "This is a generated manuscript draft for human editing. It consolidates aggregate paper artifacts only; it is not a new experiment run and it does not authorize claims beyond the full-method gate.",
        "",
        f"- Full-method gate: `{full_gate['gate_status']}`; full method allowed: `{full_gate['full_method_allowed']}`.",
        f"- Claim table status: `{claim_summary['decision']['paper_table_status']}`.",
        f"- Data-governance section status: `{data_summary['decision']['section_status']}`.",
        f"- Results scaffold status: `{results_summary['decision']['section_scaffold_status']}`.",
        f"- Bibliography status: `{bib_status['bibliography_status']}`; hygiene passed: `{bib_status['artifact_hygiene_passed']}`.",
        "",
        "## Abstract",
        "",
        "Cross-dataset depression detection is usually evaluated as a prediction problem, but pooled performance can hide a prior validity question: do different corpora measure the same target? We audit six depression corpora with registry-governed dataset roles, subject-level split contracts, dataset-group label contracts, and artifact-hygiene gates. The baseline matrix completes 66 applicable runs and serves as a reproducibility floor rather than the central novelty. Failure-mode diagnostics show that dataset and protocol identity are strongly recoverable from common frozen feature spaces, motivating conditional identity checks before shared-representation claims. Label-only E-DAIC/CMDC PHQ analyses then show substantial common structure but not uniform threshold or scalar equivalence: C01/C04/C05/C07 recur as anchors and C02/C06 recur as localized threshold-shift items, while finite-sample simulation downgrades those item-level claims from robust standalone DIF to observed-N-bounded dataset-group evidence. The old BGE-linked multimodal chain is treated as legacy/diagnostic because its E-DAIC feature contract used a Chinese encoder on English transcripts and available transcript rows are not speaker-resolved; MV17a repeats the paper-critical MV07/MV12/MV15 chain with BGE-M3 and multilingual-E5 and still reproduces the blocked pattern. Under that caveat, latent-target prediction improves within-dataset theta utility, but it is Pareto-dominated by a dimension-matched direct severity control and fails zero-shot source-calibrated external theta transfer. A later latent-conditioned identity audit keeps BGE feature identity high after theta and severity conditioning, and the DIF-guided few-shot calibration ladder fails the predeclared both-direction small-k mechanism gate. We therefore frame the contribution as a measurement-validity audit: feature alignment alone cannot solve cross-corpus learning if the target measurement function also shifts.",
        "",
        "## Contributions",
        "",
        "1. A measurement-validity framework for cross-corpus depression detection: feature shift, target measurement shift, and prediction shift are distinct failure modes.",
        "2. Empirical label-only psychometric evidence that E-DAIC and CMDC share substantial PHQ structure while exhibiting repeated but finite-sample-bounded C02/C06 threshold non-equivalence and convergence-aware uncertainty.",
        "3. A prediction-level consequence: current `X -> theta` models do not automatically improve observed-scale prediction, zero-shot transfer, or representation invariance over dimension-matched severity controls.",
        "",
        "## Introduction",
        "",
        "Depression-detection datasets differ in more than sample size or modality. They differ in interview protocol, language, clinical setting, scale family, item coverage, and population context. Official DAIC materials describe clinical interviews distributed under access constraints, while the PDCH repository describes real face-to-face consultation data paired with HAMD-17 assessments. Prior questionnaire-grounded depression-detection work shows that symptom instruments can improve out-of-domain generalization, but the present audit asks a preceding measurement question: whether datasets and scales define sufficiently comparable targets for a shared representation.",
        "",
        "Let `D` denote dataset/protocol/population, `theta` the latent depressive trait, `X` the observed language/audio/video/behavioral signal, and `Y` the observed scale response. The relevant factorization is `P(X,Y | theta,D) = P(X | theta,D) P(Y | theta,D)`. Most domain-alignment work targets the first factor, but cross-corpus validity also requires asking whether the second factor is stable. A symptom-aligned framework remains scientifically attractive, but it cannot be assumed from pooled model performance. Classical measurement-invariance and IRT sources, including PHQ invariance work and the graded-response model family used by `mirt`, motivate treating PHQ-8/PHQ-9/HAMD/SDS as related but non-identical measurement contracts. This paper therefore reports a governed sequence of baselines, shortcut diagnostics, label-only psychometric checks, legacy multimodal latent-target tests, identity conditioning, few-shot DIF-guided calibration, and aggregate evidence localization.",
        "",
        "## Methods",
        "",
        "### Data Governance And Label Contracts",
        "",
        governance_body.replace("## Draft Section", "").strip(),
        "",
        "Table 1 summarizes the governed dataset roles used by the manuscript draft.",
        "",
    ]
    lines.extend(
        markdown_table(
            dataset_table,
            [
                "display_name",
                "paper_role",
                "protocol_axis",
                "modalities",
                "subjects",
                "valid_rows",
                "primary_scale",
                "item_supervision_status",
                "data_quality_note",
            ],
            [
                "dataset",
                "role",
                "protocol",
                "modalities",
                "subjects",
                "valid rows",
                "primary scale",
                "item supervision",
                "quality note",
            ],
        )
    )
    lines.extend(
        [
            "",
            "Table 2 records the label contracts that determine which datasets can support item-level construct analyses.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            label_table,
            [
                "dataset",
                "scale",
                "total_subjects",
                "item_subjects",
                "item_supervision_status",
                "paper_claim_boundary",
            ],
            ["dataset", "scale", "total subjects", "item subjects", "supervision", "paper boundary"],
        )
    )
    lines.extend(
        [
            "",
            "### Analysis Sequence",
            "",
            "The analysis sequence is organized into three layers. First, representation/protocol shift asks how strongly `X` carries dataset, task, question, language, and population signatures. Second, target measurement shift asks whether item response functions vary by dataset/group after accounting for latent severity. Third, prediction shift asks whether an `X -> theta` model transfers once measurement has been harmonized. Phase 2 is a reproducibility floor, Phase 3 is motivating shortcut evidence, MV10-MV14/MV19 are the psychometric layer, and MV12/MV15/MV16 test prediction consequences under the old BGE caveat plus the completed MV17a multilingual sensitivity. All modeling rows use subject-level splits. Generated row predictions, learned parameters, feature caches, theta scores, source locators, evidence workbooks, and private clinical text remain local-only.",
            "",
            "### Claim Gate",
            "",
            compact_sentence(gate["finding"], 900),
            "",
            "The manuscript therefore reports allowed-limited and blocked claims explicitly. Broad M0/M1/M2/M3 construction remains blocked; the paper is allowed only as a measurement-validity diagnostic contribution.",
            "",
            "## Results",
            "",
            results_body,
            "",
            "## Discussion",
            "",
            "The central result is not a new state-of-the-art depression detector. It is a measurement audit showing that common cross-dataset shortcuts survive simple feature and head changes, and that label measurement itself is a major source of non-equivalence. The PHQ result should be read as E-DAIC/CMDC dataset-group threshold non-equivalence among shared items, not as a clean PHQ-8-versus-PHQ-9 scale-specific claim; MV19 further requires finite-sample caution for C02/C06 and the anchor map at the observed N. The negative MV08/MV08b sequence, the MV12 fidelity-identity trade-off, the MV15 latent-conditioned feature-identity result, and the MV16 calibration failure all point in the same direction: psychometric harmonization is not representation invariance, and representation alignment is not measurement validity.",
            "",
            compact_sentence(rq1["interpretation"], 900),
            "",
            compact_sentence(bge_caveat["interpretation"], 900),
            "",
            compact_sentence(mv14["interpretation"], 900),
            "",
            compact_sentence(mv19["interpretation"], 900),
            "",
            compact_sentence(mv16["interpretation"], 900),
            "",
            compact_sentence(mv06["interpretation"], 900),
            "",
            "### Limitations",
            "",
            "The draft remains bounded by the current manifest and artifact policy. E-DAIC speaker-resolved participant/interviewer controls are blocked by missing speaker labels in the available transcript CSVs. MV17a mitigates the old BGE language-contract caveat for the paper-critical MV07/MV12/MV15 chain, but it reproduces the blocked feature-level pattern rather than authorizing a shared-representation claim. The E-DAIC/CMDC PHQ evidence cannot separate language, country, protocol, clinical setting, sample severity, translation, and PHQ-8/PHQ-9 form effects; report it as dataset-group measurement shift. MV19 shows that the current observed-N PHQ decision screen is finite-sample sensitive, so C02/C06 should not be written as robust standalone DIF. MV18 adds exploratory same-HAMD CMDC/PDCH context-shift evidence, but CMDC HAMD supervision is too small for formal invariance or a complete bridge claim. EATD and MPDD are total-only for current item-level construct purposes. The MV06 evidence-localization set has one incomplete CMDC candidate and a wide E-DAIC agreement interval because the completed E-DAIC double-annotation set has 24 pairs. MV14 bootstrap uncertainty is convergence-aware but still uses the currently predeclared R=200/R=100 tiers.",
            "",
            "### Future Work",
            "",
            "Future positive method work should introduce a genuinely new predeclared mechanism rather than another shallow head variant. The immediate route is now narrow: consolidate the manuscript with MV19-downgraded PHQ wording, then design a criterion-contamination stress test over mirror-like versus non-mirror interview turns only if the manuscript still needs that support. MV17a, MV18, and MV19 are complete. Stop lines remain explicit: no extra BGE shallow heads, projection dimensions, DIF-guided calibration variants, personality-gating models, or EATD valence-adversarial modules unless a new design contract changes the gate.",
            "",
            "## Claim Traceability",
            "",
            "The full traceability matrix is stored in `manuscript_traceability_matrix.csv`. The table below shows the claim-boundary rows.",
            "",
        ]
    )
    trace_claims = traceability[traceability["trace_type"] == "claim_boundary"].copy()
    lines.extend(
        markdown_table(
            trace_claims[["manuscript_section", "claim_or_scope", "status", "guardrail", "source_artifact_count"]],
            ["manuscript_section", "claim_or_scope", "status", "guardrail", "source_artifact_count"],
            ["section", "claim", "status", "guardrail", "source artifacts"],
        )
    )
    lines.extend(
        [
            "",
            "## Open Editing Items",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            open_items,
            ["item_id", "priority", "area", "open_item", "blocking_for_submission"],
            ["id", "priority", "area", "item", "blocking"],
        )
    )
    lines.extend(
        [
            "",
            "## Source Context",
            "",
            "These source hints are mapped to citation keys for manuscript drafting; final submission should use the target venue's citation format.",
            "",
        ]
    )
    lines.extend(markdown_table(source_refs, ["citation_key", "source", "url", "use"], ["citation key", "source", "URL", "use"]))
    lines.extend(
        [
            "",
            "## Artifact Boundary",
            "",
            "- This draft is generated from aggregate artifacts only.",
            "- It does not read or export raw datasets, real row-level manifests, row predictions, embeddings, fitted parameters, private review workbooks, source locators, local notes, or clinical text.",
            "- Source experiment artifacts remain authoritative for numeric claims.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    lines = [
        "# Diagnostic Paper Manuscript Draft Report",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Manuscript draft status: `{run_summary['decision']['manuscript_draft_status']}`.",
        f"- Traceability rows: `{run_summary['outputs']['traceability_rows']}`.",
        f"- Open editing items: `{run_summary['outputs']['open_item_rows']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Outputs",
        "",
    ]
    for item in run_summary["outputs"]["tracked_outputs"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/build_diagnostic_paper_claim_tables.py",
            "python scripts/build_diagnostic_paper_data_governance_section.py",
            "python scripts/build_diagnostic_paper_results_sections.py",
            "python scripts/build_diagnostic_paper_bibliography.py",
            "python scripts/build_diagnostic_paper_manuscript_draft.py",
            "```",
        ]
    )
    (out_dir / "manuscript_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        r"local_annotation_workbook",
        r"local_text_locators_json",
        r"local_excerpt",
        r"local_notes",
        r"p5_mv[0-9a-z_]*_local_",
        r"raw snippet",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in HYGIENE_CHECKED_FILES:
        path = out_dir / name
        if not path.exists():
            violations.append({"file": name, "pattern": "missing_tracked_output"})
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": name, "pattern": pattern})
    return {
        "artifact_hygiene_passed": not violations,
        "audit_id": "diagnostic_paper_manuscript_draft_hygiene",
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    claims = pd.read_csv(CLAIMS_CSV)
    findings = pd.read_csv(FINDINGS_CSV)
    literature = pd.read_csv(LITERATURE_CSV)
    dataset_governance = pd.read_csv(DATASET_GOVERNANCE_CSV)
    label_contracts = pd.read_csv(LABEL_CONTRACT_CSV)
    checklist = pd.read_csv(RESULTS_CHECKLIST_CSV)
    governance_sources = pd.read_csv(DATA_GOVERNANCE_SOURCE_CSV)

    traceability = build_traceability(claims, checklist)
    open_items = build_open_items(bibliography_status())
    traceability.to_csv(out_dir / "manuscript_traceability_matrix.csv", index=False)
    open_items.to_csv(out_dir / "manuscript_open_items.csv", index=False)

    manuscript = build_manuscript(
        generated_at,
        claims,
        findings,
        literature,
        dataset_governance,
        label_contracts,
        governance_sources,
        traceability,
        open_items,
    )
    (out_dir / "manuscript_draft.md").write_text(manuscript, encoding="utf-8")

    run_summary = {
        "artifact_hygiene_passed": False,
        "decision": {
            "manuscript_draft_status": "ready_for_human_manuscript_editing_v0_1",
            "short_read": "A full manuscript draft has been assembled from aggregate, hygiene-passing paper artifacts; full-method claims remain blocked.",
        },
        "generated_at": generated_at,
        "input_contract": {
            "aggregate_claim_tables_read": True,
            "aggregate_data_governance_section_read": True,
            "aggregate_results_sections_read": True,
            "private_review_material_read": False,
            "raw_data_scanned": False,
            "row_level_outputs_read": False,
        },
        "outputs": {
            "draft_sections": [
                "Abstract",
                "Introduction",
                "Methods",
                "Results",
                "Discussion",
                "Claim Traceability",
                "Open Editing Items",
                "Source Context",
            ],
            "open_item_rows": int(len(open_items)),
            "tracked_outputs": TRACKED_FILES,
            "traceability_rows": int(len(traceability)),
        },
        "run_id": "diagnostic_paper_manuscript_draft",
        "source_artifacts": {
            "claim_tables": rel(CLAIM_TABLES_SUMMARY),
            "data_governance": rel(DATA_GOVERNANCE_SUMMARY),
            "full_method_gate": rel(FULL_GATE_SUMMARY),
            "results_sections": rel(RESULTS_SUMMARY),
            "bibliography": rel(BIBLIOGRAPHY_SUMMARY) if BIBLIOGRAPHY_SUMMARY.exists() else "",
        },
        "status": "complete",
    }
    (out_dir / "manuscript_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "manuscript_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary)
    (out_dir / "manuscript_artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see manuscript_artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "out_dir": rel(out_dir),
                "manuscript_draft_status": run_summary["decision"]["manuscript_draft_status"],
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
