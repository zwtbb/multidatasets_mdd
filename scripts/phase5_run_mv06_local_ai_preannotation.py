#!/usr/bin/env python3
"""Create local-only AI triage annotations for P5_MV06.

This helper reads the ignored MV06 annotation workbench and its local text
locators, scans raw text locally with simple construct keyword rules, and
writes a filled local-only preannotation workbook. The output is meant to speed
human review. It is not a human annotation pass, not agreement evidence, and not
an RQ4 claim.

Tracked outputs contain aggregate counts and hygiene checks only. Raw excerpts,
source locators, subject-level rows, and reviewer notes stay in the ignored
local preannotation CSV.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE5_DIR = ROOT / "analysis" / "phase5_minimal_validation"
DEFAULT_WORKBOOK = (
    PHASE5_DIR
    / "p5_mv06_evidence_annotation_workbench"
    / "p5_mv06_local_annotation_workbook_predictions.csv"
)
DEFAULT_OUT_DIR = PHASE5_DIR / "p5_mv06_ai_preannotation_triage"

LOCAL_PREANNOTATION = "p5_mv06_local_ai_preannotation_workbook_predictions.csv"

TRACKED_FILES = [
    "report.md",
    "run_summary.json",
    "artifact_hygiene_audit.json",
    "preannotation_summary.csv",
    "aggregate_preannotation_presence_summary.csv",
    "aggregate_preannotation_source_summary.csv",
    "local_artifact_manifest.csv",
]

REQUIRED_COLUMNS = {
    "candidate_id",
    "prediction_source",
    "dataset",
    "subject_id",
    "target_family",
    "target_id",
    "construct_id",
    "candidate_bucket",
    "selection_model",
    "selection_protocol",
    "abs_error",
    "text_available_for_local_review",
    "explicit_evidence_only",
    "local_text_locators_json",
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
    "annotator_id",
    "local_notes",
    "local_excerpt",
}

ANNOTATION_FIELDS = [
    "evidence_presence",
    "evidence_source",
    "evidence_strength",
    "time_status",
    "prompt_artifact",
]

KEYWORDS = {
    "C01": [
        "depressed",
        "depression",
        "sad",
        "sadness",
        "down",
        "hopeless",
        "low mood",
        "情绪低落",
        "心情低落",
        "心情不好",
        "抑郁",
        "沮丧",
        "难过",
        "绝望",
    ],
    "C02": [
        "interest",
        "pleasure",
        "enjoy",
        "enjoyment",
        "no fun",
        "兴趣",
        "没兴趣",
        "没有兴趣",
        "乐趣",
        "愉快",
        "开心不起来",
    ],
    "C03": [
        "sleep",
        "asleep",
        "insomnia",
        "wake up",
        "waking",
        "nightmare",
        "睡",
        "睡眠",
        "失眠",
        "睡不着",
        "早醒",
        "醒",
        "做梦",
    ],
    "C04": [
        "tired",
        "fatigue",
        "energy",
        "exhausted",
        "drained",
        "累",
        "疲劳",
        "疲惫",
        "精力",
        "没劲",
        "乏力",
    ],
    "C05": [
        "appetite",
        "eat",
        "eating",
        "weight",
        "hungry",
        "食欲",
        "胃口",
        "吃饭",
        "吃",
        "体重",
        "饭量",
    ],
    "C06": [
        "failure",
        "guilt",
        "guilty",
        "worthless",
        "blame",
        "let down",
        "失败",
        "内疚",
        "自责",
        "没用",
        "无价值",
        "拖累",
    ],
    "C07": [
        "concentrate",
        "concentration",
        "focus",
        "attention",
        "memory",
        "decide",
        "decision",
        "注意力",
        "集中",
        "记忆",
        "记不住",
        "分心",
        "决定",
    ],
    "C08": [
        "slow",
        "slowed",
        "restless",
        "fidget",
        "moving",
        "speaking slowly",
        "迟缓",
        "动作慢",
        "说话慢",
        "坐立不安",
        "烦躁",
        "不安",
    ],
    "C09": [
        "suicide",
        "suicidal",
        "kill myself",
        "self harm",
        "self-harm",
        "death",
        "dead",
        "die",
        "自杀",
        "轻生",
        "伤害自己",
        "自残",
        "寻死",
        "想死",
        "死亡",
    ],
    "C10": [
        "anxiety",
        "anxious",
        "worry",
        "worried",
        "panic",
        "nervous",
        "tense",
        "焦虑",
        "担心",
        "紧张",
        "害怕",
        "恐慌",
        "心慌",
    ],
    "C11": [
        "pain",
        "ache",
        "headache",
        "stomach",
        "body",
        "physical",
        "ill",
        "疼",
        "头痛",
        "胃",
        "身体",
        "不舒服",
        "躯体",
        "症状",
    ],
    "C12": [
        "work",
        "school",
        "study",
        "social",
        "daily",
        "function",
        "生活",
        "工作",
        "学习",
        "上班",
        "社交",
        "日常",
        "功能",
    ],
    "C13": [
        "illness",
        "sick",
        "treatment",
        "medicine",
        "medication",
        "hospital",
        "病",
        "疾病",
        "治疗",
        "吃药",
        "药",
        "医院",
        "就诊",
    ],
}

TARGET_ALIASES = {
    "HAMD03": "C09",
    "HAMD10": "C10",
    "HAMD11": "C10",
    "HAMD12": "C11",
    "HAMD13": "C11",
    "HAMD14": "C11",
    "HAMD15": "C11",
    "HAMD16": "C11",
    "HAMD17": "C13",
}

NEGATION_CUES = [
    "no ",
    "not ",
    "never",
    "none",
    "without",
    "don't",
    "doesn't",
    "didn't",
    "没有",
    "没",
    "不",
    "无",
    "否认",
    "从不",
]

PAST_CUES = ["used to", "previously", "before", "past", "以前", "曾经", "过去", "之前"]
HYPOTHETICAL_CUES = ["if ", "would", "could", "might", "假如", "如果", "可能会", "也许"]
INTERVIEWER_CUES = [
    "interviewer",
    "ellie",
    "therapist",
    "question",
    "你是否",
    "是否",
    "吗",
    "?",
    "？",
]
PARTICIPANT_CUES = ["participant", "patient", "client", "受访", "患者", "病人"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"", "nan", "none", "null", "<na>"} else text


def parse_json_list(value: Any) -> list[str]:
    text = clean_value(value)
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [str(item) for item in data]
    return []


def require_columns(frame: pd.DataFrame, required: set[str]) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"MV06 workbook missing columns: {', '.join(sorted(missing))}")


def load_workbook(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist. Run phase5_prepare_mv06_annotation_workbench.py first.")
    frame = pd.read_csv(path)
    require_columns(frame, REQUIRED_COLUMNS)
    frame["candidate_id"] = frame["candidate_id"].map(clean_value)
    if not frame["candidate_id"].map(bool).all():
        raise ValueError("candidate_id cannot be empty")
    return frame


def read_text_file(path: Path, max_chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def read_candidate_text(locator_json: Any, max_chars_per_file: int, max_total_chars: int) -> tuple[str, int, int]:
    chunks: list[str] = []
    existing_files = 0
    total_chars = 0
    for locator in parse_json_list(locator_json):
        path = Path(locator)
        if not path.exists() or not path.is_file():
            continue
        existing_files += 1
        text = read_text_file(path, max_chars=max_chars_per_file)
        if not text:
            continue
        remaining = max_total_chars - total_chars
        if remaining <= 0:
            break
        text = text[:remaining]
        chunks.append(text)
        total_chars += len(text)
    return "\n".join(chunks), existing_files, total_chars


def target_construct(row: pd.Series) -> str:
    target_id = clean_value(row.get("target_id")).upper()
    if target_id in TARGET_ALIASES:
        return TARGET_ALIASES[target_id]
    construct_id = clean_value(row.get("construct_id")).upper()
    if construct_id in KEYWORDS:
        return construct_id
    if target_id in KEYWORDS:
        return target_id
    return construct_id


def keyword_pattern(keyword: str) -> re.Pattern[str]:
    escaped = re.escape(keyword)
    if re.fullmatch(r"[A-Za-z0-9 -]+", keyword):
        return re.compile(rf"(?<![A-Za-z]){escaped}(?![A-Za-z])", re.IGNORECASE)
    return re.compile(escaped, re.IGNORECASE)


def find_matches(text: str, construct_id: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for keyword in KEYWORDS.get(construct_id, []):
        for match in keyword_pattern(keyword).finditer(text):
            start = max(0, match.start() - 140)
            end = min(len(text), match.end() + 180)
            window = text[start:end].replace("\r", " ").replace("\n", " ")
            before = text[max(0, match.start() - 30) : match.start()].lower()
            matches.append(
                {
                    "keyword": keyword,
                    "start": int(match.start()),
                    "end": int(match.end()),
                    "window": re.sub(r"\s+", " ", window).strip(),
                    "negated": any(cue in before for cue in NEGATION_CUES),
                }
            )
    return sorted(matches, key=lambda item: item["start"])


def infer_source(dataset: str, window: str, prompt_artifact: str) -> str:
    lowered = window.lower()
    if any(cue in lowered for cue in PARTICIPANT_CUES):
        return "participant"
    if any(cue in lowered for cue in INTERVIEWER_CUES):
        return "interviewer"
    if prompt_artifact == "yes":
        return "interviewer"
    if dataset in {"cmdc", "pdch"}:
        return "participant"
    return "unknown"


def infer_prompt_artifact(window: str) -> str:
    lowered = window.lower()
    if any(cue in lowered for cue in INTERVIEWER_CUES):
        return "yes"
    return "no"


def infer_time_status(window: str, evidence_presence: str) -> str:
    if evidence_presence in {"insufficient", "protocol_artifact"}:
        return "unclear"
    lowered = window.lower()
    if any(cue in lowered for cue in HYPOTHETICAL_CUES):
        return "hypothetical"
    if any(cue in lowered for cue in PAST_CUES):
        return "past"
    return "current"


def classify_candidate(row: pd.Series, text: str, existing_files: int, text_chars: int) -> dict[str, Any]:
    construct_id = target_construct(row)
    matches = find_matches(text, construct_id)
    explicit_only = str(row.get("explicit_evidence_only")).strip().lower() in {"true", "1", "yes", "y"}
    positive = [match for match in matches if not match["negated"]]
    negated = [match for match in matches if match["negated"]]
    selected = positive[0] if positive else (negated[0] if negated else None)

    if selected is None:
        evidence_presence = "insufficient"
        evidence_strength = "0"
        prompt_artifact = "unclear"
        evidence_source = "unknown"
        time_status = "unclear"
        excerpt = ""
    else:
        prompt_artifact = infer_prompt_artifact(selected["window"])
        evidence_source = infer_source(clean_value(row.get("dataset")), selected["window"], prompt_artifact)
        if prompt_artifact == "yes" and evidence_source == "interviewer":
            evidence_presence = "protocol_artifact"
            evidence_strength = "1"
        elif selected["negated"]:
            evidence_presence = "explicit_negation"
            evidence_strength = "2"
        else:
            evidence_presence = "explicit_support"
            evidence_strength = "2"
        if explicit_only and construct_id == "C09" and evidence_presence not in {"explicit_support", "explicit_negation"}:
            evidence_presence = "insufficient"
            evidence_strength = "0"
            evidence_source = "unknown"
            prompt_artifact = "unclear"
        time_status = infer_time_status(selected["window"], evidence_presence)
        excerpt = selected["window"]

    keyword_counts = Counter(match["keyword"] for match in matches)
    notes = (
        "AI triage v1; requires human review. "
        f"target_construct={construct_id}; files_scanned={existing_files}; text_chars_scanned={text_chars}; "
        f"matched_keyword_count={len(matches)}"
    )
    if keyword_counts:
        notes += "; top_keywords=" + ",".join(keyword for keyword, _ in keyword_counts.most_common(5))
    return {
        "evidence_presence": evidence_presence,
        "evidence_source": evidence_source,
        "evidence_strength": evidence_strength,
        "time_status": time_status,
        "prompt_artifact": prompt_artifact,
        "annotator_id": "ai_triage_v1",
        "local_notes": notes,
        "local_excerpt": excerpt,
        "ai_target_construct": construct_id,
        "ai_matched_keyword_count": len(matches),
        "ai_files_scanned": existing_files,
        "ai_text_chars_scanned": text_chars,
        "ai_claim_policy": "local_triage_only_requires_human_review",
    }


def build_preannotation(
    workbook: pd.DataFrame,
    *,
    max_chars_per_file: int,
    max_total_chars: int,
) -> pd.DataFrame:
    candidates = workbook.drop_duplicates("candidate_id", keep="first").copy()
    rows: list[pd.Series] = []
    for _, row in candidates.iterrows():
        text, existing_files, text_chars = read_candidate_text(
            row["local_text_locators_json"],
            max_chars_per_file=max_chars_per_file,
            max_total_chars=max_total_chars,
        )
        annotation = classify_candidate(row, text, existing_files, text_chars)
        filled = row.copy()
        for key, value in annotation.items():
            filled[key] = value
        filled["annotation_round"] = "ai_triage_v1"
        filled["git_export_policy"] = "local_only_no_git"
        rows.append(filled)
    return pd.DataFrame(rows)


def aggregate_counts(frame: pd.DataFrame, field: str) -> pd.DataFrame:
    columns = ["dataset", "target_family", "candidate_bucket", field]
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(columns, sort=True, dropna=False):
        row = dict(zip(columns, key))
        row.update(
            {
                "preannotation_rows": int(len(group)),
                "candidate_count": int(group["candidate_id"].nunique()),
                "mean_abs_error": safe_float(pd.to_numeric(group["abs_error"], errors="coerce").mean()),
            }
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=columns + ["preannotation_rows", "candidate_count", "mean_abs_error"])
    return pd.DataFrame(rows)


def safe_float(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def preannotation_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for key, group in frame.groupby(["dataset", "target_family", "candidate_bucket"], sort=True, dropna=False):
        dataset, target_family, candidate_bucket = key
        rows.append(
            {
                "dataset": dataset,
                "target_family": target_family,
                "candidate_bucket": candidate_bucket,
                "candidate_count": int(group["candidate_id"].nunique()),
                "preannotation_rows": int(len(group)),
                "text_files_scanned": int(group["ai_files_scanned"].sum()),
                "text_chars_scanned": int(group["ai_text_chars_scanned"].sum()),
                "rows_with_keyword_match": int((group["ai_matched_keyword_count"] > 0).sum()),
                "explicit_evidence_only_candidates": int(
                    group.loc[group["explicit_evidence_only"].astype(str).str.lower().isin({"true", "1", "yes"}), "candidate_id"].nunique()
                ),
            }
        )
    return pd.DataFrame(rows)


def local_artifact_manifest(frame: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "file": LOCAL_PREANNOTATION,
                "row_count": int(len(frame)),
                "candidate_count": int(frame["candidate_id"].nunique()),
                "contains_subject_level_rows": True,
                "contains_local_file_locators": True,
                "contains_raw_text_excerpts": True,
                "contains_ai_triage_fields": True,
                "git_policy": "ignored_local_only",
            }
        ]
    )


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_text_locators_json",
        r"local_excerpt",
        r"source_path",
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
        "audit_id": "P5_MV06_ai_preannotation_triage_hygiene",
        "generated_at": utc_now(),
        "files_checked": checked,
        "artifact_hygiene_passed": not violations,
        "violation_count": len(violations),
        "violations": violations,
        "local_only_files_skipped": [LOCAL_PREANNOTATION],
    }


def write_report(out_dir: Path, run_summary: dict[str, Any], summary: pd.DataFrame) -> None:
    lines = [
        "# P5_MV06 Local AI Preannotation Triage",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Scope",
        "",
        "This helper creates local-only AI triage annotations for the MV06 evidence-localization workbench. It is a review accelerator, not human annotation, not agreement evidence, and not an RQ4 claim.",
        "",
        "## Decision",
        "",
        f"- Preannotation status: `{run_summary['decision']['preannotation_status']}`.",
        f"- Candidate count: `{run_summary['preannotation_summary']['candidate_count']}`.",
        f"- Rows with keyword match: `{run_summary['preannotation_summary']['rows_with_keyword_match']}`.",
        f"- Text files scanned locally: `{run_summary['preannotation_summary']['text_files_scanned']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Dataset Summary",
        "",
        "| dataset | target family | bucket | candidates | rows with keyword match |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['dataset']} | {row['target_family']} | {row['candidate_bucket']} | "
            f"{int(row['candidate_count'])} | {int(row['rows_with_keyword_match'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            "- The local preannotation CSV may contain raw excerpts and source locators; it is ignored by Git.",
            "- Human reviewers must confirm or correct every AI triage row before MV06 evidence can be used.",
            "- The default MV06 human-annotation summary gate remains the claim boundary.",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-chars-per-file", type=int, default=25000)
    parser.add_argument("--max-total-chars", type=int, default=120000)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.max_chars_per_file <= 0 or args.max_total_chars <= 0:
        raise ValueError("character limits must be positive")

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    local_path = out_dir / LOCAL_PREANNOTATION
    if local_path.exists() and not args.overwrite:
        raise FileExistsError(f"{local_path} exists. Use --overwrite only after preserving local review edits.")

    generated_at = utc_now()
    workbook = load_workbook(args.workbook)
    preannotation = build_preannotation(
        workbook,
        max_chars_per_file=args.max_chars_per_file,
        max_total_chars=args.max_total_chars,
    )
    preannotation.to_csv(local_path, index=False)
    shutil.copystat(args.workbook, local_path, follow_symlinks=True)

    summary = preannotation_summary(preannotation)
    presence = aggregate_counts(preannotation, "evidence_presence")
    source = aggregate_counts(preannotation, "evidence_source")
    manifest = local_artifact_manifest(preannotation)

    summary.to_csv(out_dir / "preannotation_summary.csv", index=False)
    presence.to_csv(out_dir / "aggregate_preannotation_presence_summary.csv", index=False)
    source.to_csv(out_dir / "aggregate_preannotation_source_summary.csv", index=False)
    manifest.to_csv(out_dir / "local_artifact_manifest.csv", index=False)

    run_summary = {
        "run_id": "P5_MV06_local_ai_preannotation_triage",
        "generated_at": generated_at,
        "status": "complete",
        "scope": "local_ai_triage_not_human_annotation",
        "input_contract": {
            "raw_text_read_locally": True,
            "source_locator_map_read_locally": True,
            "candidate_rows_read": int(len(workbook)),
            "unique_candidates_read": int(workbook["candidate_id"].nunique()),
        },
        "preannotation_summary": {
            "candidate_count": int(preannotation["candidate_id"].nunique()),
            "preannotation_rows": int(len(preannotation)),
            "rows_with_keyword_match": int((preannotation["ai_matched_keyword_count"] > 0).sum()),
            "text_files_scanned": int(preannotation["ai_files_scanned"].sum()),
            "text_chars_scanned": int(preannotation["ai_text_chars_scanned"].sum()),
        },
        "output_policy": {
            "tracked_outputs": TRACKED_FILES,
            "local_only_files": [LOCAL_PREANNOTATION],
            "subject_level_rows_in_tracked_outputs": False,
            "local_file_locators_in_tracked_outputs": False,
            "raw_text_or_excerpts_in_tracked_outputs": False,
            "raw_text_or_excerpts_in_local_only_file": True,
        },
        "decision": {
            "preannotation_status": "ready_for_human_review_not_claimable",
            "short_read": (
                "AI triage filled a local-only preannotation workbook. It can accelerate human review, but it does not satisfy MV06 human annotation or agreement gates."
            ),
        },
        "artifact_hygiene_passed": False,
    }
    stale_hygiene = out_dir / "artifact_hygiene_audit.json"
    if stale_hygiene.exists():
        stale_hygiene.unlink()
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, summary)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "run_summary.json").write_text(json.dumps(run_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(out_dir, run_summary, summary)
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
                "preannotation_status": run_summary["decision"]["preannotation_status"],
                "candidate_count": run_summary["preannotation_summary"]["candidate_count"],
                "rows_with_keyword_match": run_summary["preannotation_summary"]["rows_with_keyword_match"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
