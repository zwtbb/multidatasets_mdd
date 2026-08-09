#!/usr/bin/env python3
"""Build Phase 4 symptom ontology and label-contract artifacts.

This is a planning artifact, not a modeling script. It creates a compact,
machine-readable bridge between depression scale items, shared symptom
constructs, and the labels actually available in the project manifests.

The script intentionally avoids long copyrighted item wording. It stores short
paraphrased item labels, item codes, construct IDs, project manifest aliases,
and source references.
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis" / "phase4_symptom_ontology"
MANIFEST_DIR = ROOT / "datasets" / "manifests"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SOURCES = [
    {
        "scale": "PHQ-9",
        "source_type": "primary_validation",
        "citation": "Kroenke, Spitzer, and Williams, 2001, Journal of General Internal Medicine",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC1495268/",
        "note": "Nine DSM-IV depression symptom items plus severity scoring; PHQ-8 removes the self-harm item.",
    },
    {
        "scale": "PHQ-8",
        "source_type": "primary_validation",
        "citation": "Kroenke et al., 2009, Journal of Affective Disorders",
        "url": "https://www.sciencedirect.com/science/article/abs/pii/S0165032708002826",
        "note": "PHQ-8 is the eight-item depression severity measure used when the self-harm item is omitted.",
    },
    {
        "scale": "HAMD-17",
        "source_type": "primary_scale",
        "citation": "Hamilton, 1960, Journal of Neurology, Neurosurgery and Psychiatry",
        "url": "https://dcf.psychiatry.ufl.edu/files/2011/05/HAMILTON-DEPRESSION.pdf",
        "note": "Clinician-rated depression scale with mood, guilt, suicide, sleep, psychomotor, anxiety, somatic, and insight items.",
    },
    {
        "scale": "SDS",
        "source_type": "primary_scale",
        "citation": "Zung, 1965, Archives of General Psychiatry",
        "url": "https://integrationacademy.ahrq.gov/sites/default/files/2020-07/Zung_Self_Rating_Depression_Scale.pdf",
        "note": "Twenty-item self-rating depression scale spanning affective, psychological, and somatic symptoms.",
    },
]


CONSTRUCTS = [
    {
        "construct_id": "C01",
        "construct_label": "depressed_mood_negative_affect",
        "tier": "core_shared",
        "definition": "sad, depressed, empty, tearful, or persistently negative affect",
        "preferred_evidence": "language affect, prosody, facial affect, self-report or clinician item",
    },
    {
        "construct_id": "C02",
        "construct_label": "anhedonia_low_positive_affect",
        "tier": "core_shared",
        "definition": "loss of interest, pleasure, enjoyment, satisfaction, or positive engagement",
        "preferred_evidence": "activity language, reward/interest expressions, affective flattening",
    },
    {
        "construct_id": "C03",
        "construct_label": "sleep_disturbance",
        "tier": "core_shared",
        "definition": "insomnia, hypersomnia, sleep continuity problems, or sleep timing disturbance",
        "preferred_evidence": "self-report or interview content; weak acoustic evidence only if explicit",
    },
    {
        "construct_id": "C04",
        "construct_label": "fatigue_low_energy",
        "tier": "core_shared",
        "definition": "low energy, tiredness, reduced vitality, or effortful activity",
        "preferred_evidence": "self-report, speech energy/prosody, psychomotor tempo",
    },
    {
        "construct_id": "C05",
        "construct_label": "appetite_weight_change",
        "tier": "core_shared",
        "definition": "appetite change, eating change, or weight change",
        "preferred_evidence": "self-report or clinician item; behavioral modalities are weak evidence",
    },
    {
        "construct_id": "C06",
        "construct_label": "self_worth_guilt_failure",
        "tier": "core_shared",
        "definition": "worthlessness, guilt, failure, blame, or perceived uselessness",
        "preferred_evidence": "language content and self/clinician item",
    },
    {
        "construct_id": "C07",
        "construct_label": "cognition_concentration_decision",
        "tier": "core_shared",
        "definition": "difficulty thinking, concentrating, deciding, or mental clarity problems",
        "preferred_evidence": "self-report, interviewer-rated cognition, response latency and coherence",
    },
    {
        "construct_id": "C08",
        "construct_label": "psychomotor_change",
        "tier": "core_shared",
        "definition": "observable or self-rated slowing, agitation, restlessness, or reduced movement",
        "preferred_evidence": "speech timing, facial movement, gait/IMU context, clinician item",
    },
    {
        "construct_id": "C09",
        "construct_label": "death_suicidality",
        "tier": "safety_sensitive_shared_except_phq8",
        "definition": "thoughts of death, self-harm, suicide, or feeling like a burden",
        "preferred_evidence": "scale item or explicit clinical text only; do not infer from weak modality cues",
    },
    {
        "construct_id": "C10",
        "construct_label": "anxiety_irritability_arousal",
        "tier": "hamd_sds_auxiliary",
        "definition": "psychic anxiety, somatic anxiety, irritability, tension, or autonomic arousal",
        "preferred_evidence": "clinician/self item, physiological or prosodic arousal as auxiliary evidence",
    },
    {
        "construct_id": "C11",
        "construct_label": "somatic_vegetative_body",
        "tier": "hamd_sds_auxiliary",
        "definition": "gastrointestinal, sexual, hypochondriacal, autonomic, or general somatic complaints",
        "preferred_evidence": "scale item or explicit content; avoid modality-only overinterpretation",
    },
    {
        "construct_id": "C12",
        "construct_label": "functioning_work_activity",
        "tier": "clinician_self_functioning",
        "definition": "work, daily activity, usefulness, ease of action, or functional impairment",
        "preferred_evidence": "language content, clinician-rated work/activity item, activity/gait context",
    },
    {
        "construct_id": "C13",
        "construct_label": "insight_illness_attribution",
        "tier": "hamd_specific",
        "definition": "clinician-rated insight or attribution of illness",
        "preferred_evidence": "clinician rating; keep as scale-specific HAMD head",
    },
    {
        "construct_id": "C14",
        "construct_label": "diurnal_circadian_variation",
        "tier": "sds_specific_auxiliary",
        "definition": "diurnal variation or morning-evening mood/energy pattern",
        "preferred_evidence": "self-report item or temporal diary; current datasets offer limited direct evidence",
    },
    {
        "construct_id": "C15",
        "construct_label": "hope_future_outlook",
        "tier": "sds_auxiliary",
        "definition": "hopefulness, future outlook, life fullness, or positive future cognition",
        "preferred_evidence": "self-report/language content; map cautiously to PHQ/HAMD mood/guilt constructs",
    },
]


ITEMS = [
    # PHQ-8 and PHQ-9. Aliases include actual E-DAIC/CMDC manifest keys where present.
    ("PHQ-8", "PHQ8_1", "no_interest", "C02", "", "exact", "direct", "PHQ_8NoInterest"),
    ("PHQ-8", "PHQ8_2", "depressed_mood", "C01", "", "exact", "direct", "PHQ_8Depressed"),
    ("PHQ-8", "PHQ8_3", "sleep", "C03", "", "exact", "direct", "PHQ_8Sleep"),
    ("PHQ-8", "PHQ8_4", "fatigue_energy", "C04", "", "exact", "direct", "PHQ_8Tired"),
    ("PHQ-8", "PHQ8_5", "appetite", "C05", "", "exact", "direct", "PHQ_8Appetite"),
    ("PHQ-8", "PHQ8_6", "failure_self_worth", "C06", "", "exact", "direct", "PHQ_8Failure"),
    ("PHQ-8", "PHQ8_7", "concentration", "C07", "", "exact", "direct", "PHQ_8Concentrating"),
    ("PHQ-8", "PHQ8_8", "psychomotor", "C08", "", "exact", "direct", "PHQ_8Moving"),
    ("PHQ-9", "PHQ9_1", "no_interest", "C02", "", "exact", "direct", "PHQ-1"),
    ("PHQ-9", "PHQ9_2", "depressed_mood", "C01", "", "exact", "direct", "PHQ-2"),
    ("PHQ-9", "PHQ9_3", "sleep", "C03", "", "exact", "direct", "PHQ-3"),
    ("PHQ-9", "PHQ9_4", "fatigue_energy", "C04", "", "exact", "direct", "PHQ-4"),
    ("PHQ-9", "PHQ9_5", "appetite", "C05", "", "exact", "direct", "PHQ-5"),
    ("PHQ-9", "PHQ9_6", "failure_self_worth", "C06", "", "exact", "direct", "PHQ-6"),
    ("PHQ-9", "PHQ9_7", "concentration", "C07", "", "exact", "direct", "PHQ-7"),
    ("PHQ-9", "PHQ9_8", "psychomotor", "C08", "", "exact", "direct", "PHQ-8"),
    ("PHQ-9", "PHQ9_9", "death_self_harm", "C09", "", "exact", "direct", "PHQ-9"),
    # HAMD-17.
    ("HAMD-17", "HAMD01", "depressed_mood", "C01", "", "exact", "direct", "HAMD01"),
    ("HAMD-17", "HAMD02", "guilt", "C06", "", "exact", "direct", "HAMD02"),
    ("HAMD-17", "HAMD03", "suicide", "C09", "", "exact", "direct", "HAMD03"),
    ("HAMD-17", "HAMD04", "insomnia_initial", "C03", "", "partial", "direct", "HAMD04"),
    ("HAMD-17", "HAMD05", "insomnia_middle", "C03", "", "partial", "direct", "HAMD05"),
    ("HAMD-17", "HAMD06", "insomnia_late", "C03", "", "partial", "direct", "HAMD06"),
    ("HAMD-17", "HAMD07", "work_activities", "C12", "C02;C04", "partial", "direct", "HAMD07"),
    ("HAMD-17", "HAMD08", "retardation", "C08", "C07", "exact", "direct", "HAMD08"),
    ("HAMD-17", "HAMD09", "agitation", "C08", "", "exact", "direct", "HAMD09"),
    ("HAMD-17", "HAMD10", "psychic_anxiety", "C10", "", "exact", "direct", "HAMD10"),
    ("HAMD-17", "HAMD11", "somatic_anxiety", "C10", "C11", "partial", "direct", "HAMD11"),
    ("HAMD-17", "HAMD12", "somatic_gastrointestinal", "C11", "C05", "partial", "direct", "HAMD12"),
    ("HAMD-17", "HAMD13", "somatic_general", "C11", "C04", "partial", "direct", "HAMD13"),
    ("HAMD-17", "HAMD14", "genital_symptoms", "C11", "", "exact", "direct", "HAMD14"),
    ("HAMD-17", "HAMD15", "hypochondriasis", "C11", "", "exact", "direct", "HAMD15"),
    ("HAMD-17", "HAMD16", "weight_loss", "C05", "", "exact", "direct", "HAMD16"),
    ("HAMD-17", "HAMD17", "insight", "C13", "", "exact", "direct", "HAMD17"),
    # SDS. Item labels are short paraphrases, not full questionnaire wording.
    ("SDS", "SDS01", "depressed_affect", "C01", "", "exact", "direct", ""),
    ("SDS", "SDS02", "morning_variation", "C14", "C01;C04", "partial", "reverse", ""),
    ("SDS", "SDS03", "crying", "C01", "", "partial", "direct", ""),
    ("SDS", "SDS04", "sleep", "C03", "", "exact", "direct", ""),
    ("SDS", "SDS05", "appetite", "C05", "", "exact", "reverse", ""),
    ("SDS", "SDS06", "sexual_interest", "C11", "", "exact", "reverse", ""),
    ("SDS", "SDS07", "weight_loss", "C05", "", "exact", "direct", ""),
    ("SDS", "SDS08", "constipation", "C11", "", "exact", "direct", ""),
    ("SDS", "SDS09", "autonomic_arousal", "C10", "C11", "partial", "direct", ""),
    ("SDS", "SDS10", "fatigue", "C04", "", "exact", "direct", ""),
    ("SDS", "SDS11", "mental_clarity", "C07", "", "exact", "reverse", ""),
    ("SDS", "SDS12", "activity_ease", "C12", "C04", "partial", "reverse", ""),
    ("SDS", "SDS13", "restlessness", "C08", "", "exact", "direct", ""),
    ("SDS", "SDS14", "hope_future", "C15", "", "exact", "reverse", ""),
    ("SDS", "SDS15", "irritability", "C10", "", "partial", "direct", ""),
    ("SDS", "SDS16", "decision_making", "C07", "", "exact", "reverse", ""),
    ("SDS", "SDS17", "usefulness_needed", "C06", "C12", "partial", "reverse", ""),
    ("SDS", "SDS18", "life_fullness", "C15", "C02", "partial", "reverse", ""),
    ("SDS", "SDS19", "death_burden", "C09", "", "exact", "direct", ""),
    ("SDS", "SDS20", "enjoyment", "C02", "", "exact", "reverse", ""),
]


DATASET_SCALES = {
    "edaic": [("PHQ-8", "phq8_total", "phq8_items")],
    "cmdc": [("PHQ-9", "phq9_total", "phq9_items"), ("HAMD-17", "hamd17_total", "hamd17_items")],
    "pdch": [("HAMD-17", "hamd17_total", "hamd17_items")],
    "modma": [("PHQ-9", "phq9_total", "phq9_items")],
    "eatd": [("SDS", "sds_total", "")],
    "mpdd_avg_2026": [("PHQ-9", "phq9_total", "phq9_items")],
}


DATASET_PRIMARY_USE = {
    "edaic": "PHQ-8 item-level development and E-DAIC protocol controls",
    "cmdc": "Chinese PHQ-9 item bridge and partial HAMD-17 validation",
    "pdch": "Real hospital HAMD-17 symptom/severity validation",
    "modma": "PHQ-9 total and diagnosis labels for task robustness stress tests",
    "eatd": "SDS total/severity and valence stress tests; no item-level SDS supervision",
    "mpdd_avg_2026": "PHQ-9 total/severity plus age/personality/gait context",
}


MINIMAL_VALIDATION_MATRIX = [
    {
        "experiment_id": "MV01",
        "rq": "RQ1",
        "name": "phq8_phq9_core_construct_bridge",
        "scope": "E-DAIC PHQ-8 items and CMDC PHQ-9 items",
        "target_constructs": "C01-C08",
        "design": "shared construct supervision for the eight PHQ-overlap constructs with scale-specific output heads",
        "required_controls": "dataset-stratified metrics; no E-DAIC/CMDC pooled claim without identity control",
        "go_criterion": "improves cross-scale construct transfer or calibration versus total-score baseline",
        "stop_criterion": "only improves same-dataset totals or worsens cross-dataset calibration",
    },
    {
        "experiment_id": "MV02",
        "rq": "RQ1",
        "name": "hamd17_bridge_to_core_constructs",
        "scope": "PDCH HAMD-17 items plus CMDC available HAMD-17 fields",
        "target_constructs": "C01-C13 with C10-C13 scale-specific or auxiliary",
        "design": "map HAMD items into shared constructs where defensible and keep anxiety/somatic/insight as auxiliary scale-specific heads",
        "required_controls": "report HAMD item-coverage and PDCH subject-level split; exclude PDCH 034A missing label rows",
        "go_criterion": "shared constructs retain or improve HAMD severity prediction while improving interpretability",
        "stop_criterion": "auxiliary HAMD items dominate without improving shared core constructs",
    },
    {
        "experiment_id": "MV03",
        "rq": "RQ1",
        "name": "sds_total_weak_bridge",
        "scope": "EATD SDS total/severity only",
        "target_constructs": "scale-level SDS total; no item-level SDS construct supervision",
        "design": "use EATD as external total/severity and valence stress test, not as an item-level construct trainer",
        "required_controls": "valence-stratified metrics and no claim that SDS item constructs were supervised",
        "go_criterion": "shared representation generalizes to SDS total without valence shortcut inflation",
        "stop_criterion": "performance is valence-dependent or no stronger than total-score baseline",
    },
    {
        "experiment_id": "MV04",
        "rq": "RQ2",
        "name": "protocol_task_robust_validation",
        "scope": "E-DAIC, CMDC, MODMA, EATD",
        "target_constructs": "all available constructs and totals",
        "design": "evaluate minimal method under protocol, question-position, task, and valence slices before pooled reporting",
        "required_controls": "dataset identity probe; E-DAIC/CMDC protocol controls; MODMA task transfer; EATD valence monitoring",
        "go_criterion": "reduces protocol/task gaps without sacrificing same-dataset performance materially",
        "stop_criterion": "pooled gains vanish under protocol or task-stratified evaluation",
    },
    {
        "experiment_id": "MV05",
        "rq": "RQ3",
        "name": "mpdd_context_calibration_validation",
        "scope": "MPDD age, personality bins, and gait context",
        "target_constructs": "PHQ-9 severity and psychomotor/context constructs C04, C08, C12",
        "design": "test calibration/context conditioning separately from naive AVP concatenation",
        "required_controls": "age subgroup ECE; personality-bin ECE; shuffled personality; gait as context validation only",
        "go_criterion": "improves subgroup calibration or robustness over AV without relying on personality shortcut",
        "stop_criterion": "no calibration gain or personality shuffling has no effect on the proposed context mechanism",
    },
    {
        "experiment_id": "MV06",
        "rq": "RQ4",
        "name": "construct_evidence_localization",
        "scope": "E-DAIC, CMDC, PDCH",
        "target_constructs": "C01-C09 where item labels exist",
        "design": "localize predicted constructs to observable text/audio/video evidence with scale-specific caveats",
        "required_controls": "do not infer C09 from weak modality cues; cite missing speaker labels for E-DAIC controls",
        "go_criterion": "localized evidence aligns with the predicted construct and not only protocol artifacts",
        "stop_criterion": "evidence highlights prompts, fixed questions, or dataset identity rather than symptom expression",
    },
]


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def nonempty(value: Any) -> bool:
    return str(value).strip() not in {"", "nan", "NaN", "None", "null"}


def parse_item_keys(value: str) -> set[str]:
    return set(parse_item_values(value))


def parse_item_values(value: str) -> dict[str, float]:
    """Return only item values that are real numeric labels, not placeholder NaNs."""
    if not nonempty(value):
        return {}
    try:
        obj = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(obj, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, raw_value in obj.items():
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if math.isnan(numeric_value):
            continue
        parsed[str(key)] = numeric_value
    return parsed


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def item_rows() -> list[dict[str, Any]]:
    fieldnames = [
        "scale",
        "item_code",
        "item_label_short",
        "primary_construct_id",
        "secondary_construct_ids",
        "mapping_strength",
        "score_direction",
        "project_aliases",
    ]
    return [dict(zip(fieldnames, item)) for item in ITEMS]


def construct_scale_map(item_catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    strength: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in item_catalog:
        key = (item["primary_construct_id"], item["scale"])
        grouped[key].append(item["item_code"])
        strength[key].add(item["mapping_strength"])
        for secondary in str(item.get("secondary_construct_ids", "")).split(";"):
            secondary = secondary.strip()
            if secondary:
                sec_key = (secondary, item["scale"])
                grouped[sec_key].append(f"{item['item_code']}*")
                strength[sec_key].add("secondary")

    rows = []
    scales = ["PHQ-8", "PHQ-9", "HAMD-17", "SDS"]
    construct_by_id = {row["construct_id"]: row for row in CONSTRUCTS}
    for construct in CONSTRUCTS:
        row = {
            "construct_id": construct["construct_id"],
            "construct_label": construct["construct_label"],
            "tier": construct["tier"],
            "definition": construct["definition"],
            "preferred_evidence": construct["preferred_evidence"],
        }
        for scale in scales:
            key = (construct["construct_id"], scale)
            items = sorted(grouped.get(key, []), key=natural_key)
            row[f"{scale}_items"] = ";".join(items)
            if not items:
                row[f"{scale}_mapping"] = "absent"
            elif "exact" in strength[key] and len(strength[key]) == 1:
                row[f"{scale}_mapping"] = "direct"
            elif "secondary" in strength[key] and len(strength[key]) == 1:
                row[f"{scale}_mapping"] = "secondary"
            else:
                row[f"{scale}_mapping"] = "partial"
        rows.append(row)
    assert set(construct_by_id) == {row["construct_id"] for row in rows}
    return rows


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def dataset_label_contract() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    audit = {
        "generated_at": utc_now(),
        "manifest_dir": "datasets/manifests",
        "datasets": {},
        "warnings": [],
    }
    for dataset, specs in DATASET_SCALES.items():
        manifest_path = MANIFEST_DIR / f"{dataset}_subjects.csv"
        if not manifest_path.exists():
            audit["warnings"].append(f"missing manifest for {dataset}")
            continue
        manifest_rows = read_manifest(manifest_path)
        subjects_all = {row.get("subject_id", "") for row in manifest_rows if nonempty(row.get("subject_id", ""))}
        audit["datasets"][dataset] = {"rows": len(manifest_rows), "subjects": len(subjects_all)}
        for scale, total_col, item_col in specs:
            total_subjects = {
                row.get("subject_id", "")
                for row in manifest_rows
                if nonempty(row.get("subject_id", "")) and nonempty(row.get(total_col, ""))
            }
            item_subjects = {
                row.get("subject_id", "")
                for row in manifest_rows
                if item_col
                and nonempty(row.get("subject_id", ""))
                and parse_item_values(row.get(item_col, ""))
            }
            item_keys: set[str] = set()
            item_rows_count = 0
            total_rows_count = 0
            for row in manifest_rows:
                if nonempty(row.get(total_col, "")):
                    total_rows_count += 1
                item_values = parse_item_values(row.get(item_col, "")) if item_col else {}
                if item_values:
                    item_rows_count += 1
                    item_keys.update(item_values)

            if item_col and item_rows_count:
                item_status = "item_level_available"
            elif total_rows_count:
                item_status = "total_only"
            else:
                item_status = "unavailable"

            limitations = []
            if item_status == "total_only":
                limitations.append("no item-level construct supervision")
            if item_col and len(item_subjects) < len(total_subjects):
                limitations.append(
                    f"{scale} item labels cover {len(item_subjects)} of {len(total_subjects)} total-labeled subjects"
                )
            if dataset == "cmdc" and scale == "HAMD-17":
                if total_rows_count != item_rows_count:
                    limitations.append("HAMD item rows and HAMD total rows have different coverage")
                if len(total_subjects) < len(subjects_all):
                    limitations.append(
                        f"HAMD-17 labels cover {len(total_subjects)} of {len(subjects_all)} CMDC subjects"
                    )
            if dataset == "modma":
                limitations.append("controlled task stress-test dataset; no PHQ-9 item fields")
            if dataset == "mpdd_avg_2026":
                limitations.append("PHQ-9 total/severity repeated over modality/task rows; no item fields")
            if dataset == "eatd":
                limitations.append("SDS total/severity only; valence tasks are stress tests")

            rows.append(
                {
                    "dataset": dataset,
                    "scale": scale,
                    "manifest_rows": len(manifest_rows),
                    "manifest_subjects": len(subjects_all),
                    "total_rows": total_rows_count,
                    "total_subjects": len(total_subjects),
                    "item_rows": item_rows_count,
                    "item_subjects": len(item_subjects),
                    "item_keys_present": ";".join(sorted(item_keys, key=natural_key)),
                    "item_supervision_status": item_status,
                    "primary_use": DATASET_PRIMARY_USE[dataset],
                    "limitations": "; ".join(limitations),
                }
            )
    return rows, audit


def source_rows() -> list[dict[str, Any]]:
    return SOURCES


def write_report(
    *,
    construct_rows: list[dict[str, Any]],
    dataset_rows: list[dict[str, Any]],
    matrix_rows: list[dict[str, Any]],
    audit: dict[str, Any],
) -> None:
    direct_core = [
        row["construct_id"]
        for row in construct_rows
        if row["tier"].startswith("core") and row["PHQ-8_mapping"] != "absent" and row["HAMD-17_mapping"] != "absent"
    ]
    item_ready = [
        f"{row['dataset']}:{row['scale']}"
        for row in dataset_rows
        if row["item_supervision_status"] == "item_level_available"
    ]
    total_only = [
        f"{row['dataset']}:{row['scale']}"
        for row in dataset_rows
        if row["item_supervision_status"] == "total_only"
    ]
    lines = [
        "# Phase 4 Symptom Ontology And Label Contract",
        "",
        f"Generated: `{audit['generated_at']}`",
        "",
        "## Purpose",
        "",
        "This artifact defines the cross-scale symptom constructs that are safe to use before minimal method validation. It maps PHQ-8, PHQ-9, HAMD-17, and SDS items to shared or scale-specific constructs, then audits which datasets actually expose item-level labels.",
        "",
        "The mapping avoids long questionnaire wording. It uses item codes and short paraphrased labels only.",
        "",
        "## Source Anchors",
        "",
    ]
    for source in SOURCES:
        lines.append(f"- {source['scale']}: {source['citation']} ({source['url']})")
    lines.extend(
        [
            "",
            "## Construct Summary",
            "",
            f"- Constructs defined: `{len(construct_rows)}`.",
            f"- Core PHQ/HAMD-overlap construct IDs: `{';'.join(direct_core)}`.",
            f"- Project item-level supervision currently available for: `{';'.join(item_ready)}`.",
            f"- Project total-only supervision currently available for: `{';'.join(total_only)}`.",
            "",
            "## Key Mapping Decisions",
            "",
            "- PHQ-8 and PHQ-9 share eight direct symptom constructs. PHQ-9 adds death/self-harm (C09), while PHQ-8 intentionally omits it.",
            "- HAMD-17 can bridge many core constructs, but anxiety, somatic, and insight items should remain auxiliary or scale-specific heads rather than forced into PHQ-like supervision.",
            "- SDS has a useful theoretical item map, but the current EATD manifest exposes SDS total/severity only, so EATD cannot train item-level constructs in the current project state.",
            "- Death/self-harm (C09) is safety-sensitive. Treat it as explicit scale/text evidence only; do not infer it from weak acoustic, video, or gait cues.",
            "- Gait should be used as psychomotor/context validation for C04/C08/C12, not as direct item supervision.",
            "",
            "## Dataset Label Contract Caveats",
            "",
        ]
    )
    caveat_rows = [row for row in dataset_rows if row.get("limitations")]
    if caveat_rows:
        for row in caveat_rows:
            lines.append(f"- `{row['dataset']}:{row['scale']}`: {row['limitations']}.")
    else:
        lines.append("- No dataset label-contract caveats recorded.")
    lines.extend(
        [
            "",
            "## Minimal Validation Gate",
            "",
            "Proceed to minimal method-validation planning with the six experiments in `minimal_validation_matrix.csv`. Do not build the full model until those experiments are specified with dataset/protocol/task/subgroup controls from the Phase 3 synthesis.",
            "",
            "## Output Files",
            "",
            "- `scale_item_catalog.csv`",
            "- `construct_scale_map.csv`",
            "- `dataset_label_contract.csv`",
            "- `minimal_validation_matrix.csv`",
            "- `scale_source_refs.csv`",
            "- `phase4_symptom_ontology_audit.json`",
            "",
            "## Planned Minimal Validation Rows",
            "",
        ]
    )
    for row in matrix_rows:
        lines.append(f"- `{row['experiment_id']}` `{row['name']}`: {row['design']}")
    (OUT_DIR / "phase4_symptom_ontology_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    item_catalog = item_rows()
    construct_rows = construct_scale_map(item_catalog)
    dataset_rows, audit = dataset_label_contract()

    write_csv(
        OUT_DIR / "scale_item_catalog.csv",
        item_catalog,
        [
            "scale",
            "item_code",
            "item_label_short",
            "primary_construct_id",
            "secondary_construct_ids",
            "mapping_strength",
            "score_direction",
            "project_aliases",
        ],
    )
    write_csv(
        OUT_DIR / "construct_scale_map.csv",
        construct_rows,
        [
            "construct_id",
            "construct_label",
            "tier",
            "definition",
            "preferred_evidence",
            "PHQ-8_items",
            "PHQ-8_mapping",
            "PHQ-9_items",
            "PHQ-9_mapping",
            "HAMD-17_items",
            "HAMD-17_mapping",
            "SDS_items",
            "SDS_mapping",
        ],
    )
    write_csv(
        OUT_DIR / "dataset_label_contract.csv",
        dataset_rows,
        [
            "dataset",
            "scale",
            "manifest_rows",
            "manifest_subjects",
            "total_rows",
            "total_subjects",
            "item_rows",
            "item_subjects",
            "item_keys_present",
            "item_supervision_status",
            "primary_use",
            "limitations",
        ],
    )
    write_csv(
        OUT_DIR / "minimal_validation_matrix.csv",
        MINIMAL_VALIDATION_MATRIX,
        [
            "experiment_id",
            "rq",
            "name",
            "scope",
            "target_constructs",
            "design",
            "required_controls",
            "go_criterion",
            "stop_criterion",
        ],
    )
    write_csv(
        OUT_DIR / "scale_source_refs.csv",
        source_rows(),
        ["scale", "source_type", "citation", "url", "note"],
    )
    write_report(
        construct_rows=construct_rows,
        dataset_rows=dataset_rows,
        matrix_rows=MINIMAL_VALIDATION_MATRIX,
        audit=audit,
    )

    audit.update(
        {
            "construct_count": len(CONSTRUCTS),
            "scale_item_count": len(ITEMS),
            "minimal_validation_rows": len(MINIMAL_VALIDATION_MATRIX),
            "output_dir": "analysis/phase4_symptom_ontology",
        }
    )
    (OUT_DIR / "phase4_symptom_ontology_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    hygiene = artifact_hygiene()
    if not hygiene["passed"]:
        raise RuntimeError(f"artifact hygiene failed: {hygiene['violations']}")
    audit["artifact_hygiene_passed"] = True
    audit["artifact_hygiene"] = hygiene
    (OUT_DIR / "phase4_symptom_ontology_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Phase 4 ontology artifacts to {OUT_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
