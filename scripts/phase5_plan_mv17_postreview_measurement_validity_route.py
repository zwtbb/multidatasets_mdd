#!/usr/bin/env python3
"""Predeclare the post-review measurement-validity route after MV16.

This is a planning artifact, not an experiment runner. It records the
post-review feature-contract caveat, prioritized experiments, and stop lines
from aggregate/local-code evidence only. It does not read raw datasets,
row-level predictions, feature matrices, annotation workbooks, or clinical
text.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    ROOT
    / "analysis"
    / "phase5_minimal_validation"
    / "p5_mv17_postreview_measurement_validity_route"
)

TRACKED_FILES = [
    "artifact_hygiene_audit.json",
    "legacy_bge_contract_risk.csv",
    "postreview_experiment_queue.csv",
    "report.md",
    "run_summary.json",
    "source_verification_summary.csv",
    "stop_line_summary.csv",
]
HYGIENE_CHECKED_FILES = [name for name in TRACKED_FILES if name != "artifact_hygiene_audit.json"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], headers: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(row[column]) for column in columns) + " |")
    return lines


def legacy_bge_contract_risk() -> list[dict[str, str]]:
    return [
        {
            "risk_id": "BGE_R001",
            "status": "mitigated_for_mv17a",
            "affected_chain": "MV07->MV12->MV15->MV16",
            "evidence": "E-DAIC MV07 generator defaults to BAAI/bge-small-zh-v1.5, which is documented as Chinese; E-DAIC transcripts are English.",
            "claim_boundary": "Old Chinese-BGE outputs remain legacy/diagnostic; MV17a now provides multilingual BGE-M3 and multilingual-E5 reruns for MV07/MV12/MV15.",
            "unaffected_evidence": "Label-only MV10/MV11/MV19 primary psychometric findings; MV13/MV14 have a separate mirt focal-mean/variance parameterization caveat.",
        },
        {
            "risk_id": "BGE_R002",
            "status": "open",
            "affected_chain": "E-DAIC text features",
            "evidence": "Current E-DAIC transcript contract exposes Text rows but no speaker role in the available CSV header, so participant/interviewer filtering is unavailable.",
            "claim_boundary": "Do not interpret high BGE identity or poor transfer as pure participant symptom-representation failure.",
            "unaffected_evidence": "Dataset governance, label-only psychometrics, and aggregate MV06 agreement.",
        },
    ]


def experiment_queue() -> list[dict[str, str]]:
    return [
        {
            "priority": "1",
            "experiment_id": "MV17a_multilingual_feature_contract",
            "status": "complete",
            "why_now": "Fixes the paper-critical BGE language contract before renewing feature-level MV07/MV12/MV15 claims.",
            "minimum_scope": "Regenerated E-DAIC, CMDC, and PDCH subject features with BGE-M3 and multilingual-E5; reran MV07, MV12, and MV15 only.",
            "success_readout": "Both encoders reproduce the blocked MV07/MV12/MV15 pattern; see p5_mv17a_multilingual_feature_contract outputs.",
            "stop_rule": "Do not rerun MV16 unless a new explicit need is identified after MV17a review.",
        },
        {
            "priority": "2",
            "experiment_id": "MV18_cmdc_pdch_hamd_same_scale_control",
            "status": "complete",
            "why_now": "Separates dataset/context measurement shift from pure language or PHQ-8/PHQ-9 form differences.",
            "minimum_scope": "Completed exploratory CMDC-HAMD versus PDCH-HAMD same-language/same-scale item distribution, total-excluding-item residual shifts, bootstrap threshold differences, and bidirectional frozen-feature transfer.",
            "success_readout": "The mild/moderate HAMD overlap shows 4 severity-conditioned residual item-shift flags, 7 threshold-shift flags, and weak primary bidirectional transfer.",
            "stop_rule": "Do not overclaim formal HAMD invariance because CMDC HAMD item supervision is only a small sanity subset.",
        },
        {
            "priority": "3",
            "experiment_id": "MV19_phq_finite_sample_psychometric_simulation",
            "status": "complete",
            "why_now": "Addresses the small E-DAIC/CMDC PHQ item-labeled N and category sparsity before strong DIF language.",
            "minimum_scope": "Completed observed-N label-only simulation under scalar-invariant H0 and C02/C06 threshold-DIF H1 using the MV10 decision screen.",
            "success_readout": "The simulation reports H0 C02/C06 both-flag false rate 0.208, H1 C02/C06 both-flag recovery 0.662, H1 top-two recovery 0.222, and H1 anchor subset recovery 0.178.",
            "stop_rule": "Downgrade C02/C06 from robust standalone DIF evidence to repeated but finite-sample-bounded dataset-group threshold-shift evidence.",
        },
        {
            "priority": "4",
            "experiment_id": "MV20_criterion_contamination_stress",
            "status": "complete_bounded_negative",
            "why_now": "Connects protocol/question shortcuts to measurement validity through mirror-like criterion contamination.",
            "minimum_scope": "Completed CMDC-only question-position criterion-overlap ranking with BGE-M3 primary and multilingual-E5 sensitivity, using deletion/high-only comparisons against matched random deletion.",
            "success_readout": "No primary or sensitivity evidence that high-overlap question-position content is clearly worse to remove than matched random content; paired intervals cross zero.",
            "stop_rule": "Freeze overlap-threshold tuning and do not build a contamination-aware architecture from this negative bounded stress test.",
        },
    ]


def source_verification() -> list[dict[str, str]]:
    return [
        {
            "source_id": "bge_small_zh_model_card",
            "url": "https://huggingface.co/BAAI/bge-small-zh-v1.5",
            "verified_fact": "Model card and FlagEmbedding table list bge-small-zh-v1.5 as Chinese.",
            "use": "Supports legacy BGE feature-contract caveat.",
        },
        {
            "source_id": "bge_m3_model_card",
            "url": "https://huggingface.co/BAAI/bge-m3",
            "verified_fact": "Model card describes BGE-M3 as multilingual, supporting more than 100 working languages.",
            "use": "Primary MV17a replacement encoder.",
        },
        {
            "source_id": "multilingual_e5_model_card",
            "url": "https://huggingface.co/intfloat/multilingual-e5-base",
            "verified_fact": "Model card lists multilingual-E5-base as multilingual and documents 768-dimensional embeddings.",
            "use": "Second MV17a encoder sensitivity.",
        },
        {
            "source_id": "multi_probe_audit_2026",
            "url": "https://arxiv.org/abs/2605.23977",
            "verified_fact": "Title and authors are A Multi-Probe Audit of Clinical-Interview Depression Detection Benchmarks by Takehiro Ishikawa and Jon Duke.",
            "use": "Motivates demoting Phase 3 to supporting benchmark-validity evidence.",
        },
        {
            "source_id": "interviewer_bias_emnlp_2025",
            "url": "https://aclanthology.org/2025.findings-emnlp.650/",
            "verified_fact": "Title, authors, pages, and DOI verified from ACL Anthology.",
            "use": "Supports protocol/question-type nuisance framing.",
        },
        {
            "source_id": "p3hf_aaai_2026",
            "url": "https://ojs.aaai.org/index.php/AAAI/article/view/37159",
            "verified_fact": "P3HF AAAI title, authors, DOI, and MPDD-Young improvement claim verified from the AAAI page.",
            "use": "Motivates demoting personality-aware modeling from a core contribution.",
        },
        {
            "source_id": "mirror_criterion_contamination_2025",
            "url": "https://arxiv.org/abs/2508.05830",
            "verified_fact": "Mirror/non-mirror criterion-contamination framing checked from the arXiv source page.",
            "use": "Motivates MV20 as a bounded protocol-label-overlap stress test rather than a new architecture.",
        },
    ]


def stop_lines() -> list[dict[str, str]]:
    return [
        {
            "stop_id": "S001",
            "area": "BGE variants",
            "decision": "Stop extra shallow BGE heads, projection dimensions, or total-anchor variants unless the feature contract changes first.",
        },
        {
            "stop_id": "S002",
            "area": "MV16 calibration",
            "decision": "MV17a is complete; keep MV16 paused unless a new explicit need is identified.",
        },
        {
            "stop_id": "S003",
            "area": "RQ3 personality",
            "decision": "Do not design personality gating/calibrators as a main method contribution; keep MPDD as a population stress test.",
        },
        {
            "stop_id": "S004",
            "area": "EATD valence",
            "decision": "Do not add an EATD valence-adversarial method from current negative SDS evidence.",
        },
        {
            "stop_id": "S005",
            "area": "Evidence localization",
            "decision": "Do not build an evidence network; use MV06 agreement as credibility support unless deletion/sufficiency tests are explicitly predeclared.",
        },
        {
            "stop_id": "S006",
            "area": "Criterion overlap",
            "decision": "MV20 is complete; stop threshold tuning, insertion variants, and contamination-aware model design from this negative bounded stress test.",
        },
    ]


def write_report(out_dir: Path, run_summary: dict[str, Any]) -> None:
    risks = legacy_bge_contract_risk()
    queue = experiment_queue()
    sources = source_verification()
    stops = stop_lines()

    lines = [
        "# MV17 Post-Review Measurement-Validity Route",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        "- Current paper direction: target measurement validity, not a generic multimodal method.",
        "- MV17a multilingual sensitivity is complete and reproduces the blocked MV07/MV12/MV15 feature-level pattern.",
        "- MV18 same-HAMD exploratory control is complete and supports cautious dataset/context-shift wording, not formal HAMD invariance.",
        "- MV19 finite-sample PHQ simulation is complete and downgrades strong C02/C06 wording under the observed-N screen.",
        "- MV20 criterion-overlap stress is complete and freezes further protocol-overlap tuning or contamination-aware model work.",
        "- Label-only MV10/MV11/MV19 PHQ psychometric results remain the primary positive evidence and are unaffected by the BGE feature-contract caveat; MV13/MV14 carry a separate mirt parameterization caveat.",
        "",
        "## Legacy BGE Contract Risks",
        "",
    ]
    lines.extend(markdown_table(risks, ["risk_id", "status", "affected_chain", "evidence", "claim_boundary"], ["risk", "status", "chain", "evidence", "boundary"]))
    lines.extend(["", "## Prioritized Experiment Queue", ""])
    lines.extend(markdown_table(queue, ["priority", "experiment_id", "status", "minimum_scope", "success_readout", "stop_rule"], ["priority", "experiment", "status", "minimum scope", "success readout", "stop rule"]))
    lines.extend(["", "## Stop Lines", ""])
    lines.extend(markdown_table(stops, ["stop_id", "area", "decision"], ["id", "area", "decision"]))
    lines.extend(["", "## Source Verification Summary", ""])
    lines.extend(markdown_table(sources, ["source_id", "url", "verified_fact", "use"], ["source", "URL", "verified fact", "use"]))
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite",
            "```",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        r"\b[0-9]{6,}@qq\.com\b",
        r"\b[a-z]{2,}[0-9]{6,}\.[0-9]+\b",
        r"github_pat_",
        r"ghp_",
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
        "audit_id": "mv17_postreview_measurement_validity_route_hygiene",
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    if out_dir.exists() and any(out_dir.iterdir()) and not args.overwrite:
        raise SystemExit(f"{rel(out_dir)} already exists; pass --overwrite to refresh")
    out_dir.mkdir(parents=True, exist_ok=True)

    generated_at = utc_now()
    write_csv(out_dir / "legacy_bge_contract_risk.csv", legacy_bge_contract_risk())
    write_csv(out_dir / "postreview_experiment_queue.csv", experiment_queue())
    write_csv(out_dir / "source_verification_summary.csv", source_verification())
    write_csv(out_dir / "stop_line_summary.csv", stop_lines())

    run_summary = {
        "artifact_hygiene_passed": False,
        "decision": {
            "route_status": "mv17a_mv18_mv19_mv20_complete_next_manuscript_finalization",
            "short_read": "MV17a, MV18, MV19, and MV20 are complete; experiments are frozen and next step is manuscript finalization with primary-source citation verification.",
        },
        "generated_at": generated_at,
        "input_contract": {
            "raw_data_scanned": False,
            "row_level_outputs_read": False,
            "feature_matrices_read": False,
            "private_review_material_read": False,
        },
        "outputs": {
            "tracked_outputs": TRACKED_FILES,
            "risk_rows": len(legacy_bge_contract_risk()),
            "experiment_rows": len(experiment_queue()),
            "source_rows": len(source_verification()),
            "stop_line_rows": len(stop_lines()),
        },
        "run_id": "p5_mv17_postreview_measurement_validity_route",
        "status": "complete",
    }
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary)
    hygiene = artifact_hygiene(out_dir)
    (out_dir / "artifact_hygiene_audit.json").write_text(json.dumps(hygiene, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see artifact_hygiene_audit.json")
    print(
        "Wrote MV17 post-review route to "
        f"{rel(out_dir)} with status {run_summary['decision']['route_status']}"
    )


if __name__ == "__main__":
    main()
