#!/usr/bin/env python3
"""Run PDCH public text-only LLM reproduction with the official HAMD prompt.

The wrapper keeps the official PDCH prompt and parsing contract, but routes
inputs through the project manifest/split layer. It writes parsed factor scores
and unified Phase 2 regression metrics only; raw transcripts and raw prompts are
not persisted.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")


normalize_thread_env()

import numpy as np
import pandas as pd

from phase2_metrics import metric_records


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "pdch_subjects.csv"
SPLIT_PATH = ROOT / "datasets" / "splits" / "phase2_subject_splits.csv"
PDCH_ROOT = ROOT / "datasets" / "PDCH" / "audio" / "wav_data"
OFFICIAL_PDCH_DIR = ROOT / "cache" / "official_baselines" / "PDCH"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "pdch_public_llm"
DEFAULT_HF_CACHE = ROOT / "cache" / "huggingface"
DEFAULT_TEXT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_TEXT_MODEL_SOURCE = "ModelScope/Qwen/Qwen2.5-7B-Instruct"
DEFAULT_TEXT_MODEL_LOAD_PATH = ROOT / "cache" / "modelscope" / "Qwen-Qwen2.5-7B-Instruct"
SEEDS = [0, 1, 2, 3, 4]
HAMD_ITEMS = [f"HAMD{idx:02d}" for idx in range(1, 18)]
HAMD_FACTORS = [
    "抑郁情绪因子",
    "有罪感因子",
    "自杀因子",
    "入睡困难因子",
    "睡眠不深因子",
    "早醒因子",
    "工作和兴趣因子",
    "迟滞因子",
    "激越因子",
    "精神性焦虑因子",
    "躯体性焦虑因子",
    "胃肠道症状因子",
    "全身症状因子",
    "性症状因子",
    "疑病因子",
    "体重减轻因子",
    "自知力因子",
]
FACTOR_TO_ITEM = {factor: HAMD_ITEMS[idx] for idx, factor in enumerate(HAMD_FACTORS)}
PROTOCOL_GROUPS = {
    "imbalance": [
        "pdch_hamd17_official_imbalance_small_cv",
        "pdch_hamd17_official_imbalance_big_cv",
    ],
    "word_count": [
        "pdch_hamd17_official_word_count_small_cv",
        "pdch_hamd17_official_word_count_big_cv",
    ],
}


@dataclass(frozen=True)
class PublicSpec:
    run_id: str
    dataset_id: str
    display_dataset: str
    modality: str
    task: str
    task_type: str
    target: str
    model: str


TEXT_SPEC = PublicSpec(
    run_id="pdch_public_text_only",
    dataset_id="pdch",
    display_dataset="PDCH",
    modality="Text",
    task="HAMD-17 regression",
    task_type="severity_regression",
    target="hamd17_total",
    model="PDCH official text-only",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def natural_key(value: Any) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", str(value))]


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ["utf-8-sig", "utf-8", "gb18030"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def official_hamd_description(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"official HAMD-17 description missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    description = f'{data["问卷信息"]}\n当前关注的因子：\n'
    factor_to_item = {item["name"]: item for item in data["问题集"]}
    for idx, factor in enumerate(HAMD_FACTORS, start=1):
        item = factor_to_item[factor]
        description += f"因子名称: {idx} {factor}\n"
        description += "打分标准：\n"
        for score in sorted(item["打分或选项例子"].keys(), key=lambda value: int(value)):
            description += f'{score}: {item["打分或选项例子"][score][0]}\n'
    return description


def official_text_conversation(transcript_text: str, hamd_description: str) -> list[dict[str, str]]:
    task_description = f"""你是一个尽职的助手，请依据医患访谈对话来分析出任务要求的目标因子分数。
{hamd_description}
任务要求：
请基于访谈对话片段，给出所有关注因子结果的分数,访谈中未提到的因子也要结合患者情况填写出来。
输出格式：id 因子名:分数为(score)，以`;`分隔。
样例：
1 抑郁情绪因子:分数为(x);2 有罪感因子:分数为(y);......;16 体重减轻因子:分数为(a);17 自知力因子:分数为(z)"""
    return [
        {"role": "user", "content": "<访谈对话片段>"},
        {"role": "user", "content": f"转录后的文字：\n{transcript_text}\n"},
        {"role": "user", "content": "</访谈对话片段>"},
        {"role": "user", "content": task_description},
        {"role": "user", "content": "请基于访谈对话按照格式给出具体的因子分数，直接给出结果不需要解释。"},
    ]


def parse_timestamp_emotion_file(path: Path, *, include_audio_emotion: bool) -> list[str]:
    text = read_text_file(path).strip()
    if not text:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    utterances: list[str] = []
    for idx in range(0, len(lines) - 1, 2):
        time_emotion = lines[idx]
        saying = lines[idx + 1]
        if not re.search(r"\d+:\d+-\d+:\d+", time_emotion):
            continue
        if include_audio_emotion:
            suffix = re.sub(r"^\d+:\d+-\d+:\d+", "", time_emotion).strip()
            if suffix:
                saying = f"{saying}({suffix})"
        utterances.append(saying)
    return utterances


def subject_transcript(subject_id: str, *, include_audio_emotion: bool) -> tuple[str, int, int]:
    subject_dir = PDCH_ROOT / subject_id
    if not subject_dir.exists():
        raise FileNotFoundError(f"PDCH subject directory missing: {subject_dir}")
    timestamp_paths = sorted(subject_dir.glob("*_correction_timestamp_emotion.txt"), key=lambda path: natural_key(path.name))
    utterances: list[str] = []
    for path in timestamp_paths:
        utterances.extend(parse_timestamp_emotion_file(path, include_audio_emotion=include_audio_emotion))
    if not utterances:
        txt_paths = sorted(subject_dir.glob("*.txt"), key=lambda path: natural_key(path.name))
        txt_paths = [path for path in txt_paths if path.name.endswith(".txt") and "_correction" not in path.name]
        for path in txt_paths:
            utterances.extend(line.strip() for line in read_text_file(path).splitlines() if line.strip())
    if not utterances:
        raise ValueError(f"no usable PDCH transcript utterances for {subject_id}")
    transcript = "\n".join(utterances)
    return transcript, len(utterances), int(len(transcript))


def load_protocol_plan(split_path: Path, protocol_group: str) -> pd.DataFrame:
    protocols = PROTOCOL_GROUPS[protocol_group]
    split_frame = pd.read_csv(split_path)
    required = {"dataset", "protocol_id", "target", "fold", "role", "subject_id"}
    missing = required - set(split_frame.columns)
    if missing:
        raise ValueError(f"split layer missing columns: {', '.join(sorted(missing))}")
    selected = split_frame[
        (split_frame["dataset"].astype(str) == TEXT_SPEC.dataset_id)
        & (split_frame["target"].astype(str) == TEXT_SPEC.target)
        & (split_frame["protocol_id"].astype(str).isin(protocols))
        & (split_frame["role"].astype(str) == "validation")
    ].copy()
    if selected.empty:
        raise ValueError(f"no PDCH official validation rows for protocol group {protocol_group}")
    selected["subject_id"] = selected["subject_id"].astype(str)
    duplicated = selected[selected["subject_id"].duplicated(keep=False)]["subject_id"].unique().tolist()
    if duplicated:
        raise ValueError(f"subjects appear in multiple validation folds for {protocol_group}: {duplicated[:10]}")
    return selected[["protocol_id", "fold", "subject_id"]].sort_values(
        ["protocol_id", "fold", "subject_id"],
        key=lambda series: series.map(lambda item: tuple(natural_key(item))),
    ).reset_index(drop=True)


def load_labels(subject_ids: set[str]) -> pd.DataFrame:
    manifest = pd.read_csv(MANIFEST_PATH)
    rows = manifest[
        manifest["subject_id"].astype(str).isin(subject_ids)
        & manifest[TEXT_SPEC.target].notna()
    ].copy()
    if rows.empty:
        raise ValueError("no PDCH labels found for selected subjects")
    labels: list[dict[str, Any]] = []
    for subject_id, group in rows.groupby("subject_id", sort=False):
        totals = group[TEXT_SPEC.target].dropna().unique()
        if len(totals) != 1:
            raise ValueError(f"{subject_id} has inconsistent HAMD totals: {totals[:5]}")
        item_payloads = group["hamd17_items"].dropna().unique() if "hamd17_items" in group else []
        item_values: dict[str, int] = {}
        if len(item_payloads):
            parsed = json.loads(str(item_payloads[0]))
            item_values = {item: int(parsed[item]) for item in HAMD_ITEMS if item in parsed}
        labels.append(
            {
                "subject_id": str(subject_id),
                TEXT_SPEC.target: float(totals[0]),
                **{f"y_true_{item}": item_values.get(item, math.nan) for item in HAMD_ITEMS},
            }
        )
    frame = pd.DataFrame(labels)
    missing_subjects = sorted(subject_ids - set(frame["subject_id"].astype(str)), key=natural_key)
    if missing_subjects:
        raise ValueError(f"subjects missing PDCH labels: {missing_subjects[:10]}")
    return frame


def normalize_factor_name(value: str) -> str:
    factor = value.replace("阻滞", "迟滞").replace(".", "").strip()
    if "激越因子" in factor:
        return "激越因子"
    for official_factor in HAMD_FACTORS:
        if official_factor in factor:
            return official_factor
    return factor


def parse_hamd_response(response: str) -> dict[str, int]:
    patterns = [
        r"(\d+)\s*([^:：]+)[:：]\s*分数为\((\d|None)\)",
        r"(\d+)\s*([^:：]+)[:：]\s*分数为\s*(\d|None)",
        r"(\d+)\s*([^:：]+)[:：]\s+(\d|None)",
    ]
    result: dict[str, int] = {}
    for pattern in patterns:
        matches = re.findall(pattern, response)
        for _, factor_name, score_text in matches:
            if score_text == "None":
                continue
            factor = normalize_factor_name(factor_name)
            if factor in FACTOR_TO_ITEM and FACTOR_TO_ITEM[factor] not in result:
                result[FACTOR_TO_ITEM[factor]] = int(score_text)
        if result:
            break
    return result


def predicted_total(item_scores: dict[str, int]) -> float:
    values = []
    for item in HAMD_ITEMS:
        score = item_scores.get(item, 9)
        values.append(0 if score == 9 else int(score))
    return float(np.sum(values))


def load_existing_factor_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    return frame.to_dict("records")


def write_factor_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "run_id",
        "model_name",
        "protocol_group",
        "subject_id",
        "generation_seed",
        "do_sample",
        "parsed_factor_count",
        "predicted_hamd17_total",
        "utterance_count",
        "transcript_char_count",
        *HAMD_ITEMS,
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (str(item["subject_id"]), int(item["generation_seed"]))):
            writer.writerow({column: row.get(column, "") for column in columns})


def load_text_generator(
    model_load_path: str,
    *,
    cache_dir: Path,
    local_files_only: bool,
    device_map: str,
) -> Callable[[list[dict[str, str]], int, bool, int], str]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

    cache_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(
        model_load_path,
        cache_dir=str(cache_dir),
        local_files_only=local_files_only,
        trust_remote_code=True,
    )
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_load_path,
        cache_dir=str(cache_dir),
        local_files_only=local_files_only,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True,
    )
    model.eval()

    def generate(messages: list[dict[str, str]], seed: int, do_sample: bool, max_new_tokens: int) -> str:
        set_seed(seed)
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([prompt], return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            output = model.generate(
                **inputs,
                do_sample=do_sample,
                max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = output[:, inputs["input_ids"].shape[1] :]
        return tokenizer.batch_decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

    return generate


def factor_row_key(row: dict[str, Any]) -> tuple[str, str, str, int, bool]:
    return (
        str(row.get("model_name")),
        str(row.get("protocol_group")),
        str(row.get("subject_id")),
        int(row.get("generation_seed")),
        bool(row.get("do_sample")),
    )


def build_factor_rows(
    plan: pd.DataFrame,
    *,
    model_name: str,
    model_source: str,
    model_load_path: str,
    protocol_group: str,
    include_audio_emotion: bool,
    do_sample: bool,
    deterministic_seed_reuse: bool,
    max_new_tokens: int,
    cache_dir: Path,
    local_files_only: bool,
    device_map: str,
    out_dir: Path,
    force_generations: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    factor_path = out_dir / "pdch_public_llm_factor_predictions.csv"
    existing_rows = [] if force_generations else load_existing_factor_rows(factor_path)
    generation_seeds = [SEEDS[0]] if deterministic_seed_reuse and not do_sample else SEEDS
    required_keys = {
        (model_name, protocol_group, subject_id, seed, do_sample)
        for subject_id in plan["subject_id"].astype(str)
        for seed in generation_seeds
    }
    usable_rows = [
        row for row in existing_rows if factor_row_key(row) in required_keys and str(row.get("run_id")) == TEXT_SPEC.run_id
    ]
    observed = {factor_row_key(row) for row in usable_rows}
    missing = sorted(required_keys - observed, key=lambda key: (natural_key(key[2]), key[3]))
    summary = {
        "factor_cache_path": str(factor_path),
        "cached_generation_rows": int(len(usable_rows)),
        "missing_generation_rows": int(len(missing)),
        "generation_seeds": generation_seeds,
        "deterministic_seed_reuse": bool(deterministic_seed_reuse and not do_sample),
        "model_name": model_name,
        "model_source": model_source,
        "local_model_path_used": bool(Path(model_load_path).is_absolute()),
    }
    if missing:
        generator = load_text_generator(
            model_load_path,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
            device_map=device_map,
        )
        hamd_description = official_hamd_description(OFFICIAL_PDCH_DIR / "HAMD17_original.json")
        for idx, (_, _, subject_id, seed, _) in enumerate(missing, start=1):
            transcript, utterance_count, char_count = subject_transcript(
                subject_id,
                include_audio_emotion=include_audio_emotion,
            )
            messages = official_text_conversation(transcript, hamd_description)
            print(
                f"[pdch-public-text] {idx}/{len(missing)} subject={subject_id} seed={seed} "
                f"chars={char_count}",
                flush=True,
            )
            response = generator(messages, seed, do_sample, max_new_tokens)
            item_scores = parse_hamd_response(response)
            row = {
                "run_id": TEXT_SPEC.run_id,
                "model_name": model_name,
                "protocol_group": protocol_group,
                "subject_id": subject_id,
                "generation_seed": int(seed),
                "do_sample": bool(do_sample),
                "parsed_factor_count": int(len(item_scores)),
                "predicted_hamd17_total": predicted_total(item_scores),
                "utterance_count": int(utterance_count),
                "transcript_char_count": int(char_count),
                **{item: item_scores.get(item, 9) for item in HAMD_ITEMS},
            }
            usable_rows.append(row)
            write_factor_rows(factor_path, usable_rows)
    return usable_rows, summary


def build_prediction_frame(
    plan: pd.DataFrame,
    labels: pd.DataFrame,
    factor_rows: list[dict[str, Any]],
    *,
    model_name: str,
    protocol_group: str,
    do_sample: bool,
    deterministic_seed_reuse: bool,
) -> pd.DataFrame:
    label_by_subject = labels.set_index("subject_id", drop=False)
    factor_by_key = {factor_row_key(row): row for row in factor_rows}
    predictions: list[dict[str, Any]] = []
    for seed in SEEDS:
        generation_seed = SEEDS[0] if deterministic_seed_reuse and not do_sample else seed
        for _, plan_row in plan.iterrows():
            subject_id = str(plan_row["subject_id"])
            factor_key = (model_name, protocol_group, subject_id, generation_seed, do_sample)
            factor_row = factor_by_key.get(factor_key)
            if factor_row is None:
                raise ValueError(f"missing factor prediction for {factor_key}")
            label_row = label_by_subject.loc[subject_id]
            predictions.append(
                {
                    "run_id": TEXT_SPEC.run_id,
                    "dataset": TEXT_SPEC.display_dataset,
                    "modality": TEXT_SPEC.modality,
                    "task": TEXT_SPEC.task,
                    "model": TEXT_SPEC.model,
                    "seed": int(seed),
                    "fold": str(plan_row["fold"]),
                    "protocol_id": str(plan_row["protocol_id"]),
                    "protocol_group": protocol_group,
                    "task_type": TEXT_SPEC.task_type,
                    "subject_id": subject_id,
                    "split": "validation",
                    "y_true": float(label_row[TEXT_SPEC.target]),
                    "y_pred": float(factor_row["predicted_hamd17_total"]),
                    "y_score": "",
                    "generation_seed": int(generation_seed),
                    "deterministic_seed_reuse": bool(deterministic_seed_reuse and not do_sample),
                    "parsed_factor_count": int(factor_row.get("parsed_factor_count") or 0),
                    "utterance_count": int(factor_row.get("utterance_count") or 0),
                    "transcript_char_count": int(factor_row.get("transcript_char_count") or 0),
                }
            )
    return pd.DataFrame(predictions)


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# PDCH Public Text-Only LLM Reproduction",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Public source: `Miraclemarvel55/PDCH` official prompt and HAMD-17 parsing contract.",
        "- Input interface: project PDCH manifest plus official PDCH split protocols from `datasets/splits/phase2_subject_splits.csv`.",
        "- Text source: local `*_correction_timestamp_emotion.txt` transcripts, using text only by default.",
        "- Model family: official text-only LLM evaluation.",
        f"- Model source: `{summary['model_source']}`.",
        "- Generation is deterministic by default (`do_sample=False`), matching the official wrapper.",
        "- Deterministic seed reuse is recorded when one generation is reused across the five Phase 2 seed slots.",
        "- Predicted HAMD-17 total is the sum of parsed item scores, with missing item scores treated as 0 for total calculation, matching the official evaluator's missing-score convention.",
        "- No train split, test split, validation-label tuning, raw transcript text, or raw prompt text is written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Model name: `{summary['model_name']}`",
        f"- Local model path used: `{summary['local_model_path_used']}`",
        f"- Protocol group: `{summary['protocol_group']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Raw transcripts written: `{summary['raw_transcripts_written']}`",
        f"- Raw model responses written: `{summary['raw_model_responses_written']}`",
        "",
        "## Output Files",
        "",
        "- `pdch_public_llm_predictions.csv`",
        "- `pdch_public_llm_factor_predictions.csv`",
        "- `phase2_metrics_by_seed.csv`",
        "- `phase2_metric_summary.csv`",
        "- `pdch_public_llm_run_summary.json`",
    ]
    (out_dir / "pdch_public_llm_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=TEXT_SPEC.run_id, choices=[TEXT_SPEC.run_id])
    parser.add_argument("--model-name", default=DEFAULT_TEXT_MODEL)
    parser.add_argument("--model-source", default=DEFAULT_TEXT_MODEL_SOURCE)
    parser.add_argument("--model-load-path", default=str(DEFAULT_TEXT_MODEL_LOAD_PATH))
    parser.add_argument("--protocol-group", choices=sorted(PROTOCOL_GROUPS), default="imbalance")
    parser.add_argument("--split-path", type=Path, default=SPLIT_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--hf-cache-dir", type=Path, default=DEFAULT_HF_CACHE)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--include-audio-emotion", action="store_true")
    parser.add_argument("--do-sample", action="store_true")
    parser.add_argument("--no-deterministic-seed-reuse", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-generations", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plan = load_protocol_plan(args.split_path, args.protocol_group)
    labels = load_labels(set(plan["subject_id"].astype(str)))
    factor_rows, factor_summary = build_factor_rows(
        plan,
        model_name=args.model_name,
        model_source=args.model_source,
        model_load_path=args.model_load_path,
        protocol_group=args.protocol_group,
        include_audio_emotion=args.include_audio_emotion,
        do_sample=args.do_sample,
        deterministic_seed_reuse=not args.no_deterministic_seed_reuse,
        max_new_tokens=args.max_new_tokens,
        cache_dir=args.hf_cache_dir,
        local_files_only=args.local_files_only,
        device_map=args.device_map,
        out_dir=args.out_dir,
        force_generations=args.force_generations,
    )
    predictions_frame = build_prediction_frame(
        plan,
        labels,
        factor_rows,
        model_name=args.model_name,
        protocol_group=args.protocol_group,
        do_sample=args.do_sample,
        deterministic_seed_reuse=not args.no_deterministic_seed_reuse,
    )
    predictions_path = args.out_dir / "pdch_public_llm_predictions.csv"
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
    metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "run_id": TEXT_SPEC.run_id,
        "model_name": args.model_name,
        "model_source": args.model_source,
        "local_model_path_used": bool(Path(args.model_load_path).is_absolute()),
        "official_source_dir": str(OFFICIAL_PDCH_DIR),
        "manifest_path": str(MANIFEST_PATH),
        "split_path": str(args.split_path),
        "protocol_group": args.protocol_group,
        "protocol_ids": PROTOCOL_GROUPS[args.protocol_group],
        "subject_count": int(plan["subject_id"].nunique()),
        "seeds": SEEDS,
        "seed_count": len(SEEDS),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "prediction_rows": int(len(predictions_frame)),
        "do_sample": bool(args.do_sample),
        "deterministic_seed_reuse": bool((not args.no_deterministic_seed_reuse) and not args.do_sample),
        "include_audio_emotion": bool(args.include_audio_emotion),
        "max_new_tokens": int(args.max_new_tokens),
        "factor_summary": factor_summary,
        "no_training_used": True,
        "no_test_split_used": True,
        "validation_label_tuning_used": False,
        "raw_transcripts_written": False,
        "raw_prompts_written": False,
        "raw_model_responses_written": False,
    }
    (args.out_dir / "pdch_public_llm_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")


if __name__ == "__main__":
    main()
