#!/usr/bin/env python3
"""Run the PDCH official audio-text multimodal LLM reproduction.

This wrapper preserves the public PDCH Qwen2-Audio evaluation contract while
routing data through the Phase 2 manifest and split layer. It writes parsed
HAMD-17 factor predictions and unified regression metrics only; raw transcript
text, raw prompts, raw responses, source paths, and audio paths are not written
to result CSVs.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from phase2_metrics import metric_records
from phase2_run_pdch_public_llm import (
    HAMD_ITEMS,
    MANIFEST_PATH,
    OFFICIAL_PDCH_DIR,
    PDCH_ROOT,
    PROTOCOL_GROUPS,
    ROOT,
    SEEDS,
    load_labels,
    load_protocol_plan,
    natural_key,
    official_hamd_description,
    parse_hamd_response,
    predicted_total,
    read_text_file,
)


DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "pdch_public_audio_text"
DEFAULT_CACHE_DIR = ROOT / "cache" / "modelscope"
DEFAULT_MODEL_NAME = "Qwen/Qwen2-Audio-7B-Instruct"
DEFAULT_MODEL_LOAD_PATH = ROOT / "cache" / "modelscope" / "Qwen-Qwen2-Audio-7B-Instruct"
DEFAULT_MODEL_SOURCE = "ModelScope/Qwen/Qwen2-Audio-7B-Instruct"
DEFAULT_CLIP_CACHE_DIR = ROOT / "cache" / "pdch_public_audio_text_clips"


@dataclass(frozen=True)
class AudioTextSpec:
    run_id: str = "pdch_public_audio_text"
    dataset_id: str = "pdch"
    display_dataset: str = "PDCH"
    modality: str = "Audio/Text"
    task: str = "HAMD-17 regression"
    task_type: str = "severity_regression"
    target: str = "hamd17_total"
    model: str = "PDCH official audio-text"


SPEC = AudioTextSpec()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_time_emotion(value: str, path: Path, line_index: int) -> tuple[int, int, list[str]]:
    pattern = r"(\d+):(\d+)-(\d+):(\d+)(?:\s*(.*))?"
    match = re.search(pattern, value)
    if not match:
        raise ValueError(f"could not parse PDCH timestamp at {path}:{line_index}")
    start_minute, start_second, end_minute, end_second, optional_label = match.groups()
    start = int(start_minute) * 60 + int(start_second)
    end = int(end_minute) * 60 + int(end_second)
    if end < start:
        raise ValueError(f"end time precedes start time at {path}:{line_index}")
    emotions = [
        item.strip()
        for item in str(optional_label or "").replace("，", ",").replace(".", ",").split(",")
        if item.strip()
    ]
    return start, end, emotions


def subject_blocks(subject_id: str) -> list[dict[str, Any]]:
    subject_dir = PDCH_ROOT / subject_id
    if not subject_dir.exists():
        raise FileNotFoundError(f"PDCH subject directory missing: {subject_dir}")
    blocks: list[dict[str, Any]] = []
    timestamp_paths = sorted(subject_dir.glob("*_correction_timestamp_emotion.txt"), key=lambda path: natural_key(path.name))
    for timestamp_path in timestamp_paths:
        wav_path = Path(str(timestamp_path).replace("_correction_timestamp_emotion.txt", ".wav"))
        if not wav_path.exists():
            raise FileNotFoundError(f"PDCH audio file missing for {subject_id}: {wav_path}")
        lines = [line.strip() for line in read_text_file(timestamp_path).splitlines() if line.strip()]
        for idx in range(0, len(lines) - 1, 2):
            start, end, emotions = parse_time_emotion(lines[idx], timestamp_path, idx + 1)
            saying = lines[idx + 1]
            blocks.append(
                {
                    "saying": saying,
                    "audio_path": wav_path,
                    "start_time": start,
                    "end_time": end,
                    "emotions": emotions,
                }
            )
    if not blocks:
        raise ValueError(f"no timestamped PDCH blocks for {subject_id}")
    return blocks


def blocks_duration_seconds(blocks: list[dict[str, Any]]) -> float:
    duration = 0.0
    start_audio_time = None
    for idx, block in enumerate(blocks):
        if idx == 0:
            start_audio_time = float(block["start_time"])
        current_audio = block["audio_path"]
        is_last = idx == len(blocks) - 1
        next_audio = None if is_last else blocks[idx + 1]["audio_path"]
        if is_last or current_audio != next_audio:
            duration += float(block["end_time"]) + 1.0 - float(start_audio_time)
            if not is_last:
                start_audio_time = float(blocks[idx + 1]["start_time"])
    return duration


def subject_chunks(blocks: list[dict[str, Any]], *, context_minutes: int) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    limit = float(context_minutes * 60 - 5)
    for idx, block in enumerate(blocks):
        current.append(block)
        next_blocks = current + ([blocks[idx + 1]] if idx < len(blocks) - 1 else [])
        if idx == len(blocks) - 1 or blocks_duration_seconds(next_blocks) > limit:
            chunks.append(current)
            current = []
    return chunks


def chunk_text(blocks: list[dict[str, Any]], *, include_audio_emotion: bool) -> str:
    lines: list[str] = []
    for block in blocks:
        suffix = ""
        if include_audio_emotion and block["emotions"]:
            suffix = f"({', '.join(block['emotions'])})"
        lines.append(f"{block['saying']}{suffix}")
    return "\n".join(lines)


def prepare_audio_clips(
    subject_id: str,
    chunk_index: int,
    blocks: list[dict[str, Any]],
    *,
    clip_cache_dir: Path,
    audio_clip_max_seconds: int,
) -> tuple[list[Path], float]:
    import librosa
    import soundfile as sf

    clip_cache_dir.mkdir(parents=True, exist_ok=True)
    cache_pattern = f"{subject_id}_chunk{chunk_index:03d}_clip*.wav"
    cached = sorted(clip_cache_dir.glob(cache_pattern), key=lambda path: natural_key(path.name))
    if cached:
        return cached, blocks_duration_seconds(blocks)

    audio_paths = sorted({Path(block["audio_path"]) for block in blocks}, key=lambda path: natural_key(path.name))
    audio_data = {path: librosa.load(str(path)) for path in audio_paths}
    clips: list[np.ndarray] = []
    start_audio_time = float(blocks[0]["start_time"])
    sr = None
    for idx, block in enumerate(blocks):
        current_audio = Path(block["audio_path"])
        y_wave, sr = audio_data[current_audio]
        is_last = idx == len(blocks) - 1
        next_audio = None if is_last else Path(blocks[idx + 1]["audio_path"])
        if is_last or current_audio != next_audio:
            start = max(0, int(start_audio_time * sr))
            end = min(y_wave.shape[-1], int((float(block["end_time"]) + 1.0) * sr))
            if end > start:
                clips.append(y_wave[start:end])
            if not is_last:
                start_audio_time = float(blocks[idx + 1]["start_time"])
    if sr is None:
        raise ValueError(f"no audio sample rate available for {subject_id} chunk {chunk_index}")
    if clips:
        concatenated = np.concatenate(clips)
    else:
        concatenated = np.zeros(int(sr), dtype=np.float32)

    stride = int(sr * audio_clip_max_seconds)
    output_paths: list[Path] = []
    for clip_index, start in enumerate(range(0, concatenated.shape[-1], stride)):
        sub_audio = concatenated[start : start + stride]
        if sub_audio.size == 0:
            continue
        output_path = clip_cache_dir / f"{subject_id}_chunk{chunk_index:03d}_clip{clip_index:03d}.wav"
        sf.write(output_path, sub_audio, sr)
        output_paths.append(output_path)
    return output_paths, float(concatenated.shape[-1] / sr)


def task_description(*, need_all_factors_result: bool, hamd_description: str) -> str:
    if need_all_factors_result:
        requirement = """请基于访谈对话片段，给出所有关注因子结果的分数,访谈中未提到的因子也要结合患者情况填写出来。
输出格式：id 因子名:分数为(score)，以`;`分隔。
样例：
1 抑郁情绪因子:分数为(x);2 有罪感因子:分数为(y);......;16 体重减轻因子:分数为(a);17 自知力因子:分数为(z)"""
    else:
        requirement = """请基于访谈对话片段，给出关注因子结果的分数，若对话中没有提到这个因子，则输出分数为`None`。
输出格式：id 因子名:分数为(score)，以`;`分隔。
样例：
1 抑郁情绪因子:分数为(x);2 有罪感因子:分数为(y);......;16 体重减轻因子:分数为(None);17 自知力因子:分数为(z)"""
    return f"""你是一个尽职的助手，请依据医患访谈对话来分析出任务要求的目标因子分数。
{hamd_description}
任务要求：
{requirement}"""


def audio_text_conversation(
    blocks: list[dict[str, Any]],
    clip_paths: list[Path],
    *,
    include_audio_emotion: bool,
    need_all_factors_result: bool,
    hamd_description: str,
) -> list[dict[str, Any]]:
    content: list[dict[str, str]] = [
        {"type": "text", "text": f"转录后的文字：\n{chunk_text(blocks, include_audio_emotion=include_audio_emotion)}\n"},
        {"type": "text", "text": "原始音频：\n"},
    ]
    content.extend({"type": "audio", "audio_url": str(path)} for path in clip_paths)
    return [
        {"role": "user", "content": "<访谈对话片段>"},
        {"role": "user", "content": content},
        {"role": "user", "content": "</访谈对话片段>"},
        {"role": "user", "content": task_description(need_all_factors_result=need_all_factors_result, hamd_description=hamd_description)},
        {"role": "user", "content": "请基于访谈对话按照格式给出具体的因子分数，直接给出结果不需要解释。"},
    ]


def load_qwen2_audio_generator(
    model_load_path: str,
    *,
    cache_dir: Path,
    local_files_only: bool,
    device_map: str,
) -> Callable[[list[dict[str, Any]], int, bool, int], str]:
    import librosa
    import torch
    from transformers import Qwen2AudioForConditionalGeneration, set_seed
    from transformers.models.qwen2_audio.processing_qwen2_audio import Qwen2AudioProcessor

    cache_dir.mkdir(parents=True, exist_ok=True)
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    processor = Qwen2AudioProcessor.from_pretrained(
        model_load_path,
        cache_dir=str(cache_dir),
        local_files_only=local_files_only,
        trust_remote_code=True,
    )
    model = Qwen2AudioForConditionalGeneration.from_pretrained(
        model_load_path,
        cache_dir=str(cache_dir),
        local_files_only=local_files_only,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True,
    )
    model.eval()

    def generate(conversation: list[dict[str, Any]], seed: int, do_sample: bool, max_new_tokens: int) -> str:
        set_seed(seed)
        audios: list[np.ndarray] = []
        for message in conversation:
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                item_type = str(item.get("type", ""))
                if item_type not in {"audio", "input_audio"}:
                    continue
                audio_path = item.get("audio_url") or item.get("local_file")
                if not audio_path and isinstance(item.get("input_audio"), dict):
                    audio_path = item["input_audio"].get("data")
                if not audio_path:
                    continue
                audios.append(
                    librosa.load(str(audio_path), sr=processor.feature_extractor.sampling_rate)[0]
                )
        prompt = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
        inputs = processor(
            text=prompt,
            audio=audios if audios else None,
            sampling_rate=processor.feature_extractor.sampling_rate,
            return_tensors="pt",
            padding=True,
        )
        device = next(model.parameters()).device
        inputs = inputs.to(device)
        with torch.no_grad():
            generated_ids = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
            )
        generated_ids = generated_ids[:, inputs.input_ids.shape[1] :]
        return processor.batch_decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

    return generate


def row_key(row: dict[str, Any]) -> tuple[str, str, str, int, bool]:
    return (
        str(row.get("model_name")),
        str(row.get("protocol_group")),
        str(row.get("subject_id")),
        int(row.get("generation_seed")),
        bool(row.get("do_sample")),
    )


def load_existing_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict("records")


def write_factor_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "run_id",
        "model_name",
        "model_source",
        "protocol_group",
        "subject_id",
        "generation_seed",
        "do_sample",
        "parsed_factor_count",
        "predicted_hamd17_total",
        "chunk_count",
        "audio_clip_count",
        "utterance_count",
        "transcript_char_count",
        "total_audio_seconds",
        "context_minutes",
        "audio_clip_max_seconds",
        *HAMD_ITEMS,
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (str(item["subject_id"]), int(item["generation_seed"]))):
            writer.writerow({column: row.get(column, "") for column in columns})


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
    clip_cache_dir: Path,
    context_minutes: int,
    audio_clip_max_seconds: int,
    max_chunks_per_subject: int | None,
    canonical_outputs: bool,
    force_generations: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    factor_name = (
        "pdch_public_audio_text_factor_predictions.csv"
        if canonical_outputs
        else "pdch_public_audio_text_partial_factor_predictions.csv"
    )
    factor_path = out_dir / factor_name
    existing_rows = [] if force_generations else load_existing_rows(factor_path)
    generation_seeds = [SEEDS[0]] if deterministic_seed_reuse and not do_sample else SEEDS
    required_keys = {
        (model_name, protocol_group, subject_id, seed, do_sample)
        for subject_id in plan["subject_id"].astype(str)
        for seed in generation_seeds
    }
    usable_rows = [
        row for row in existing_rows if row_key(row) in required_keys and str(row.get("run_id")) == SPEC.run_id
    ]
    observed = {row_key(row) for row in usable_rows}
    missing = sorted(required_keys - observed, key=lambda key: (natural_key(key[2]), key[3]))
    summary = {
        "factor_cache_path": str(factor_path),
        "cached_generation_rows": int(len(usable_rows)),
        "missing_generation_rows": int(len(missing)),
        "generation_seeds": generation_seeds,
        "deterministic_seed_reuse": bool(deterministic_seed_reuse and not do_sample),
        "context_minutes": int(context_minutes),
        "audio_clip_max_seconds": int(audio_clip_max_seconds),
        "max_chunks_per_subject": max_chunks_per_subject,
        "clip_cache_dir": str(clip_cache_dir),
        "model_name": model_name,
        "model_source": model_source,
        "local_model_path_used": bool(Path(model_load_path).is_absolute()),
    }
    if missing:
        generator = load_qwen2_audio_generator(
            model_load_path,
            cache_dir=cache_dir,
            local_files_only=local_files_only,
            device_map=device_map,
        )
        hamd_description = official_hamd_description(OFFICIAL_PDCH_DIR / "HAMD17_original.json")
        for idx, (_, _, subject_id, seed, _) in enumerate(missing, start=1):
            blocks = subject_blocks(subject_id)
            chunks = subject_chunks(blocks, context_minutes=context_minutes)
            if max_chunks_per_subject is not None:
                chunks = chunks[: int(max_chunks_per_subject)]
            total_minutes = blocks_duration_seconds(blocks) / 60.0
            need_all = context_minutes >= 120 or total_minutes < context_minutes
            item_scores: dict[str, int] = {}
            clip_count = 0
            audio_seconds = 0.0
            print(
                f"[pdch-public-audio-text] {idx}/{len(missing)} subject={subject_id} "
                f"seed={seed} chunks={len(chunks)} minutes={total_minutes:.2f}",
                flush=True,
            )
            for chunk_index, chunk in enumerate(chunks):
                clip_paths, chunk_audio_seconds = prepare_audio_clips(
                    subject_id,
                    chunk_index,
                    chunk,
                    clip_cache_dir=clip_cache_dir,
                    audio_clip_max_seconds=audio_clip_max_seconds,
                )
                clip_count += len(clip_paths)
                audio_seconds += chunk_audio_seconds
                messages = audio_text_conversation(
                    chunk,
                    clip_paths,
                    include_audio_emotion=include_audio_emotion,
                    need_all_factors_result=need_all,
                    hamd_description=hamd_description,
                )
                response = generator(messages, seed, do_sample, max_new_tokens)
                for item, score in parse_hamd_response(response).items():
                    item_scores[item] = score
            transcript = chunk_text(blocks, include_audio_emotion=include_audio_emotion)
            row = {
                "run_id": SPEC.run_id,
                "model_name": model_name,
                "model_source": model_source,
                "protocol_group": protocol_group,
                "subject_id": subject_id,
                "generation_seed": int(seed),
                "do_sample": bool(do_sample),
                "parsed_factor_count": int(len(item_scores)),
                "predicted_hamd17_total": predicted_total(item_scores),
                "chunk_count": int(len(chunks)),
                "audio_clip_count": int(clip_count),
                "utterance_count": int(len(blocks)),
                "transcript_char_count": int(len(transcript)),
                "total_audio_seconds": float(audio_seconds),
                "context_minutes": int(context_minutes),
                "audio_clip_max_seconds": int(audio_clip_max_seconds),
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
    factor_by_key = {row_key(row): row for row in factor_rows}
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
                    "run_id": SPEC.run_id,
                    "dataset": SPEC.display_dataset,
                    "modality": SPEC.modality,
                    "task": SPEC.task,
                    "model": SPEC.model,
                    "seed": int(seed),
                    "fold": str(plan_row["fold"]),
                    "protocol_id": str(plan_row["protocol_id"]),
                    "protocol_group": protocol_group,
                    "task_type": SPEC.task_type,
                    "subject_id": subject_id,
                    "split": "validation",
                    "y_true": float(label_row[SPEC.target]),
                    "y_pred": float(factor_row["predicted_hamd17_total"]),
                    "y_score": "",
                    "generation_seed": int(generation_seed),
                    "deterministic_seed_reuse": bool(deterministic_seed_reuse and not do_sample),
                    "parsed_factor_count": int(factor_row.get("parsed_factor_count") or 0),
                    "chunk_count": int(factor_row.get("chunk_count") or 0),
                    "audio_clip_count": int(factor_row.get("audio_clip_count") or 0),
                    "utterance_count": int(factor_row.get("utterance_count") or 0),
                    "transcript_char_count": int(factor_row.get("transcript_char_count") or 0),
                    "total_audio_seconds": float(factor_row.get("total_audio_seconds") or 0.0),
                }
            )
    return pd.DataFrame(predictions)


def full_contract_completed(args: argparse.Namespace, plan: pd.DataFrame) -> bool:
    return (
        args.max_subjects is None
        and args.max_chunks_per_subject is None
        and args.protocol_group == "imbalance"
        and int(args.context_minutes) == 3
        and int(args.audio_clip_max_seconds) == 25
        and not bool(args.include_audio_emotion)
        and not bool(args.do_sample)
        and not bool(args.no_deterministic_seed_reuse)
        and len(SEEDS) >= 5
        and int(args.bootstrap_resamples) >= 1000
        and int(plan["subject_id"].nunique()) == 99
    )


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    if summary["full_contract_completed"]:
        prediction_file = "pdch_public_audio_text_predictions.csv"
        factor_file = "pdch_public_audio_text_factor_predictions.csv"
        metric_files = "`phase2_metrics_by_seed.csv` and `phase2_metric_summary.csv`"
    else:
        prediction_file = "pdch_public_audio_text_partial_predictions.csv"
        factor_file = "pdch_public_audio_text_partial_factor_predictions.csv"
        metric_files = (
            "`pdch_public_audio_text_partial_metrics_by_seed.csv` and "
            "`pdch_public_audio_text_partial_metric_summary.csv`"
        )
    lines = [
        "# PDCH Public Audio-Text LLM Reproduction",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Public source: `Miraclemarvel55/PDCH` Qwen2-Audio evaluation contract.",
        "- Input interface: project PDCH manifest plus official PDCH split protocols from `datasets/splits/phase2_subject_splits.csv`.",
        "- Audio-text contract: Qwen2-Audio, local WAV clips, 3-minute context windows, 25-second audio clips, and official HAMD-17 factor prompts.",
        "- Long interviews are evaluated in official-style chunks; chunk-level parsed factors update the subject-level factor dictionary.",
        "- Predicted HAMD-17 total is the sum of parsed item scores, with missing item scores treated as 0 for total calculation, matching the official evaluator's missing-score convention.",
        "- No train split, test split, validation-label tuning, raw transcript text, raw prompt text, raw responses, or source audio paths are written to outputs.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Model name: `{summary['model_name']}`",
        f"- Model source: `{summary['model_source']}`",
        f"- Local model path used: `{summary['local_model_path_used']}`",
        f"- Protocol group: `{summary['protocol_group']}`",
        f"- Subjects: `{summary['subject_count']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
        f"- Prediction rows: `{summary['prediction_rows']}`",
        f"- Full matrix contract completed: `{summary['full_contract_completed']}`",
        "",
        "## Output Files",
        "",
        f"- `{prediction_file}`",
        f"- `{factor_file}`",
        f"- {metric_files}",
        "- `pdch_public_audio_text_run_summary.json`",
    ]
    (out_dir / "pdch_public_audio_text_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=SPEC.run_id, choices=[SPEC.run_id])
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--model-source", default=DEFAULT_MODEL_SOURCE)
    parser.add_argument("--model-load-path", default=str(DEFAULT_MODEL_LOAD_PATH))
    parser.add_argument("--protocol-group", choices=sorted(PROTOCOL_GROUPS), default="imbalance")
    parser.add_argument("--split-path", type=Path, default=ROOT / "datasets" / "splits" / "phase2_subject_splits.csv")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--clip-cache-dir", type=Path, default=DEFAULT_CLIP_CACHE_DIR)
    parser.add_argument("--device-map", default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--include-audio-emotion", action="store_true")
    parser.add_argument("--do-sample", action="store_true")
    parser.add_argument("--no-deterministic-seed-reuse", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--context-minutes", type=int, default=3)
    parser.add_argument("--audio-clip-max-seconds", type=int, default=25)
    parser.add_argument("--max-subjects", type=int, default=None)
    parser.add_argument("--max-chunks-per-subject", type=int, default=None)
    parser.add_argument("--force-generations", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    plan = load_protocol_plan(args.split_path, args.protocol_group)
    if args.max_subjects is not None:
        plan = plan.head(int(args.max_subjects)).copy()
    is_full = full_contract_completed(args, plan)
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
        cache_dir=args.cache_dir,
        local_files_only=args.local_files_only,
        device_map=args.device_map,
        out_dir=args.out_dir,
        clip_cache_dir=args.clip_cache_dir,
        context_minutes=args.context_minutes,
        audio_clip_max_seconds=args.audio_clip_max_seconds,
        max_chunks_per_subject=args.max_chunks_per_subject,
        canonical_outputs=is_full,
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
    predictions_name = (
        "pdch_public_audio_text_predictions.csv"
        if is_full
        else "pdch_public_audio_text_partial_predictions.csv"
    )
    predictions_path = args.out_dir / predictions_name
    predictions_frame.to_csv(predictions_path, index=False)

    metrics_by_seed, metric_summary = metric_records(
        predictions_frame,
        bootstrap_resamples=args.bootstrap_resamples,
        seed=20260727,
    )
    if is_full:
        metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)
    else:
        metrics_by_seed.to_csv(args.out_dir / "pdch_public_audio_text_partial_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "pdch_public_audio_text_partial_metric_summary.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "run_id": SPEC.run_id,
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
        "context_minutes": int(args.context_minutes),
        "audio_clip_max_seconds": int(args.audio_clip_max_seconds),
        "max_chunks_per_subject": args.max_chunks_per_subject,
        "factor_summary": factor_summary,
        "full_contract_completed": bool(is_full),
        "no_training_used": True,
        "no_test_split_used": True,
        "validation_label_tuning_used": False,
        "raw_transcripts_written": False,
        "raw_prompts_written": False,
        "raw_model_responses_written": False,
        "raw_audio_paths_written": False,
    }
    (args.out_dir / "pdch_public_audio_text_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {predictions_path}")
    if is_full:
        print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")
    else:
        print(f"Wrote {args.out_dir / 'pdch_public_audio_text_partial_metric_summary.csv'}")


if __name__ == "__main__":
    main()
