#!/usr/bin/env python3
"""Run a manifest-routed QuestMF public baseline reproduction for E-DAIC.

This wrapper preserves the public QuestMF contract: PHQ-8 item-wise ordinal
classification, ImbOLL loss, text/audio/video recurrent encoders, and
question-wise TAV fusion. It adapts the data interface to the project manifest,
precomputes turn-level features for repeatability, and writes audited
prediction/metric files only. Raw transcripts, prompts, source paths, audio, and
video frames are not written to outputs.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def normalize_thread_env() -> None:
    value = str(os.environ.get("OMP_NUM_THREADS", "")).strip()
    if not value.isdigit() or int(value) <= 0:
        os.environ["OMP_NUM_THREADS"] = "1"
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


normalize_thread_env()

import librosa
import numpy as np
import pandas as pd
import scipy.io as sio
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModel, AutoTokenizer

from phase2_metrics import metric_records, regression_metrics


ROOT = Path("/root/autodl-tmp")
MANIFEST_PATH = ROOT / "datasets" / "manifests" / "edaic_subjects.csv"
LABEL_DIR = ROOT / "datasets" / "edaic" / "labels"
OFFICIAL_QUESTMF_DIR = ROOT / "cache" / "official_baselines" / "clpsych2025-questmf"
DEFAULT_OUT_DIR = ROOT / "analysis" / "phase2_baselines" / "edaic_public_questmf"
DEFAULT_HF_CACHE = ROOT / "cache" / "huggingface"
DEFAULT_TEXT_MODEL = "sentence-transformers/all-distilroberta-v1"
RUN_ID = "edaic_public_questmf"
SEEDS = [0, 1, 2, 3, 4]
QUESTIONS = list(range(1, 9))
QUESTION_COLUMNS = [
    "PHQ_8NoInterest",
    "PHQ_8Depressed",
    "PHQ_8Sleep",
    "PHQ_8Tired",
    "PHQ_8Appetite",
    "PHQ_8Failure",
    "PHQ_8Concentrating",
    "PHQ_8Moving",
]
MAX_TURNS = 120
TEXT_DIM = 768
AUDIO_DIM = 23
VIDEO_DIM = 2048
OFFICIAL_UNIMODAL_EPOCHS = 10
OFFICIAL_FUSION_EPOCHS = 20
EPS = 1.0e-12


@dataclass(frozen=True)
class PublicSpec:
    run_id: str
    dataset: str
    modality: str
    task: str
    model: str
    task_type: str


SPEC = PublicSpec(
    run_id=RUN_ID,
    dataset="E-DAIC",
    modality="Audio/Video/Text",
    task="PHQ-8 item-wise ordinal prediction",
    model="QuestMF",
    task_type="ordinal_prediction",
)


@dataclass
class SubjectFeatures:
    subject_id: str
    split: str
    phq8_total: float
    item_scores: list[int]
    text: np.ndarray
    text_mask: np.ndarray
    audio: np.ndarray
    audio_mask: np.ndarray
    video: np.ndarray
    video_mask: np.ndarray


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def as_device(name: str) -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def mean_pool_hidden(hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.to(dtype=hidden.dtype).unsqueeze(-1)
    summed = torch.sum(hidden * mask, dim=1)
    denom = torch.clamp(torch.sum(mask, dim=1), min=1.0)
    return summed / denom


def read_subject_table() -> pd.DataFrame:
    manifest = pd.read_csv(MANIFEST_PATH)
    labels = pd.read_csv(LABEL_DIR / "Detailed_PHQ8_Labels.csv")
    required = {
        "subject_id",
        "official_split",
        "text_path",
        "audio_path",
        "video_path",
        "phq8_total",
        "file_valid",
    }
    missing = required - set(manifest.columns)
    if missing:
        raise ValueError(f"E-DAIC manifest missing columns: {', '.join(sorted(missing))}")
    usable = manifest[
        manifest["file_valid"].fillna(False).astype(bool)
        & manifest["official_split"].isin(["train", "dev"])
        & manifest["text_path"].notna()
        & manifest["audio_path"].notna()
        & manifest["video_path"].notna()
        & manifest["phq8_total"].notna()
    ].copy()
    usable["subject_id"] = usable["subject_id"].astype(str)
    label_cols = ["Participant_ID", *QUESTION_COLUMNS, "PHQ_8Total"]
    labels = labels[label_cols].copy()
    labels["subject_id"] = labels["Participant_ID"].astype(str)
    table = usable.merge(labels.drop(columns=["Participant_ID"]), on="subject_id", how="left", validate="one_to_one")
    if table[QUESTION_COLUMNS].isna().any().any():
        missing_subjects = table.loc[table[QUESTION_COLUMNS].isna().any(axis=1), "subject_id"].tolist()
        raise ValueError(f"E-DAIC train/dev subjects missing detailed PHQ-8 labels: {missing_subjects[:10]}")
    if len(table) != 219:
        raise ValueError(f"QuestMF expected 219 E-DAIC train/dev rows, observed {len(table)}")
    split_counts = table["official_split"].value_counts().to_dict()
    if split_counts.get("train") != 163 or split_counts.get("dev") != 56:
        raise ValueError(f"unexpected E-DAIC split counts for QuestMF: {split_counts}")
    for column in ["text_path", "audio_path", "video_path"]:
        missing_paths = [path for path in table[column].astype(str).tolist() if not Path(path).exists()]
        if missing_paths:
            raise FileNotFoundError(f"{column} has missing files, examples: {missing_paths[:5]}")
    return table.sort_values(["official_split", "subject_id"], kind="mergesort").reset_index(drop=True)


def clean_intervals(starts: Iterable[float], ends: Iterable[float], max_length: float) -> tuple[list[int], list[int], int]:
    start_list = list(starts)
    end_list = list(ends)
    x = 1
    y = len(start_list)
    removed = 0
    while x < y:
        if start_list[x - 1] > start_list[x] or start_list[x] > max_length:
            del start_list[x]
            del end_list[x]
            x -= 1
            y -= 1
            removed += 1
        if x < y and (end_list[x - 1] > end_list[x] or end_list[x] > max_length):
            del start_list[x]
            del end_list[x]
            x -= 1
            y -= 1
            removed += 1
        x += 1
    return [round(v) for v in start_list], [round(v) for v in end_list], removed


def interval_mean_features(
    values: np.ndarray,
    starts: list[int],
    ends: list[int],
    *,
    max_turns: int,
    normalize: bool,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if values.ndim != 2:
        raise ValueError(f"expected 2D feature matrix, got shape {values.shape}")
    feature_dim = values.shape[1]
    rows: list[np.ndarray] = []
    adjusted = 0
    empty = 0
    length = values.shape[0]
    for start, end in zip(starts, ends, strict=False):
        if len(rows) >= max_turns:
            break
        start_i = max(0, min(int(start), max(0, length - 1)))
        end_i = max(0, min(int(end), length))
        if end_i <= start_i:
            end_i = min(length, start_i + 1)
            adjusted += 1
        segment = values[start_i:end_i]
        if segment.size == 0:
            rows.append(np.zeros(feature_dim, dtype=np.float32))
            empty += 1
        else:
            rows.append(np.mean(segment, axis=0, dtype=np.float64).astype(np.float32))
    valid = len(rows)
    mask = np.asarray([False] * valid + [True] * max(0, max_turns - valid), dtype=np.bool_)
    if valid < max_turns:
        rows.extend([np.zeros(feature_dim, dtype=np.float32) for _ in range(max_turns - valid)])
    arr = np.vstack(rows[:max_turns]).astype(np.float32)
    if normalize:
        norm = np.linalg.norm(arr, axis=1, keepdims=True)
        arr = np.divide(arr, np.maximum(norm, 1.0e-12), out=np.zeros_like(arr), where=norm > 0)
    return arr, mask, {"valid_turns": int(valid), "adjusted_empty_intervals": int(adjusted), "empty_segments": int(empty)}


def preprocess_audio(transcript: pd.DataFrame, audio_path: Path, egemaps_path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    duration = float(librosa.get_duration(path=audio_path))
    egemaps = pd.read_csv(egemaps_path, sep=";").iloc[:, 2:].to_numpy(dtype=np.float32)
    starts, ends, removed = clean_intervals(
        transcript["Start_Time"].to_numpy(dtype=float) * 100.0,
        transcript["End_Time"].to_numpy(dtype=float) * 100.0,
        duration * 100.0,
    )
    arr, mask, stats = interval_mean_features(egemaps, starts, ends, max_turns=MAX_TURNS, normalize=False)
    if arr.shape[1] != AUDIO_DIM:
        raise ValueError(f"QuestMF expected {AUDIO_DIM} eGeMAPS columns, got {arr.shape[1]} at {egemaps_path}")
    return arr, mask, {"audio_duration_seconds": duration, "audio_removed_intervals": removed, **stats}


def preprocess_video(transcript: pd.DataFrame, audio_path: Path, video_path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    duration = float(librosa.get_duration(path=audio_path))
    video = sio.loadmat(video_path)["feature"].astype(np.float32)
    if duration <= 0.0:
        raise ValueError(f"non-positive E-DAIC audio duration for video alignment: {audio_path}")
    factor = float(len(video)) / duration
    starts, ends, removed = clean_intervals(
        transcript["Start_Time"].to_numpy(dtype=float) * factor,
        transcript["End_Time"].to_numpy(dtype=float) * factor,
        float(len(video)),
    )
    arr, mask, stats = interval_mean_features(video, starts, ends, max_turns=MAX_TURNS, normalize=True)
    if arr.shape[1] != VIDEO_DIM:
        raise ValueError(f"QuestMF expected {VIDEO_DIM} ResNet columns, got {arr.shape[1]} at {video_path}")
    return arr, mask, {"video_frames": int(len(video)), "video_removed_intervals": removed, **stats}


def load_text_encoder(model_name: str, cache_dir: Path, local_files_only: bool, device: torch.device) -> tuple[Any, nn.Module]:
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=str(cache_dir), local_files_only=local_files_only)
    model = AutoModel.from_pretrained(model_name, cache_dir=str(cache_dir), local_files_only=local_files_only)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    model.to(device)
    return tokenizer, model


def preprocess_text(
    texts: list[str],
    tokenizer: Any,
    model: nn.Module,
    device: torch.device,
    *,
    max_length: int,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    clean_texts = [str(text) if str(text).strip() else "" for text in texts]
    embeddings: list[np.ndarray] = []
    token_counts: list[int] = []
    truncated = 0
    for start in range(0, len(clean_texts), batch_size):
        batch_texts = clean_texts[start : start + batch_size]
        raw = tokenizer(batch_texts, add_special_tokens=False, padding=False, truncation=False)
        counts = [len(ids) for ids in raw["input_ids"]]
        token_counts.extend(counts)
        truncated += int(sum(count > max(1, max_length - 2) for count in counts))
        encoded = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.inference_mode():
            output = model(**encoded)
            pooled = mean_pool_hidden(output.last_hidden_state, encoded["attention_mask"])
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
        embeddings.extend(pooled.detach().cpu().numpy().astype(np.float32))
    valid = min(len(embeddings), MAX_TURNS)
    mask = np.asarray([False] * valid + [True] * max(0, MAX_TURNS - valid), dtype=np.bool_)
    if valid:
        arr = np.vstack(embeddings[:valid]).astype(np.float32)
    else:
        arr = np.zeros((0, TEXT_DIM), dtype=np.float32)
    if arr.shape[1] != TEXT_DIM:
        raise ValueError(f"QuestMF expected {TEXT_DIM} text embedding columns, got {arr.shape[1]}")
    if valid < MAX_TURNS:
        arr = np.vstack([arr, np.zeros((MAX_TURNS - valid, TEXT_DIM), dtype=np.float32)])
    return arr, mask, {
        "text_turn_count": int(len(clean_texts)),
        "text_valid_turns": int(valid),
        "text_token_count_sum": int(sum(token_counts)),
        "text_truncated_turns": int(truncated),
    }


def feature_cache_path(cache_dir: Path, subject_id: str) -> Path:
    return cache_dir / f"{subject_id}.npz"


def build_feature_cache(
    table: pd.DataFrame,
    out_dir: Path,
    *,
    text_model_name: str,
    cache_dir: Path,
    local_files_only: bool,
    device: torch.device,
    text_max_length: int,
    encode_batch_size: int,
    force: bool,
) -> tuple[list[SubjectFeatures], dict[str, Any]]:
    feature_dir = out_dir / "questmf_feature_cache"
    feature_dir.mkdir(parents=True, exist_ok=True)
    need_text_encoder = force or any(not feature_cache_path(feature_dir, str(row["subject_id"])).exists() for _, row in table.iterrows())
    tokenizer = None
    text_model = None
    if need_text_encoder:
        tokenizer, text_model = load_text_encoder(text_model_name, cache_dir, local_files_only, device)
    rows: list[dict[str, Any]] = []
    subjects: list[SubjectFeatures] = []
    for idx, row in table.iterrows():
        subject_id = str(row["subject_id"])
        path = feature_cache_path(feature_dir, subject_id)
        item_scores = [int(row[column]) for column in QUESTION_COLUMNS]
        if path.exists() and not force:
            loaded = np.load(path)
            text = loaded["text"].astype(np.float32)
            text_mask = loaded["text_mask"].astype(np.bool_)
            audio = loaded["audio"].astype(np.float32)
            audio_mask = loaded["audio_mask"].astype(np.bool_)
            video = loaded["video"].astype(np.float32)
            video_mask = loaded["video_mask"].astype(np.bool_)
            rows.append(json.loads(str(loaded["metadata"].item())))
        else:
            if tokenizer is None or text_model is None:
                tokenizer, text_model = load_text_encoder(text_model_name, cache_dir, local_files_only, device)
            text_path = Path(str(row["text_path"]))
            audio_path = Path(str(row["audio_path"]))
            feature_dir_path = Path(str(row["video_path"])).parent
            transcript = pd.read_csv(text_path).sort_values(["Start_Time", "End_Time"], kind="mergesort")
            transcript["Text"] = transcript["Text"].fillna("").astype(str)
            egemaps_path = feature_dir_path / f"{subject_id}_OpenSMILE2.3.0_egemaps.csv"
            resnet_path = feature_dir_path / f"{subject_id}_CNN_ResNet.mat"
            text, text_mask, text_stats = preprocess_text(
                transcript["Text"].tolist(),
                tokenizer,
                text_model,
                device,
                max_length=text_max_length,
                batch_size=encode_batch_size,
            )
            audio, audio_mask, audio_stats = preprocess_audio(transcript, audio_path, egemaps_path)
            video, video_mask, video_stats = preprocess_video(transcript, audio_path, resnet_path)
            metadata = {
                "subject_id": subject_id,
                "split": str(row["official_split"]),
                "phq8_total": float(row["phq8_total"]),
                "feature_model_name": text_model_name,
                **text_stats,
                **{f"audio_{key}": value for key, value in audio_stats.items()},
                **{f"video_{key}": value for key, value in video_stats.items()},
            }
            np.savez_compressed(
                path,
                text=text,
                text_mask=text_mask,
                audio=audio,
                audio_mask=audio_mask,
                video=video,
                video_mask=video_mask,
                metadata=np.asarray(json.dumps(metadata, sort_keys=True), dtype=object),
            )
            rows.append(metadata)
            print(f"[questmf-features] {idx + 1}/{len(table)} subject={subject_id}", flush=True)
        subjects.append(
            SubjectFeatures(
                subject_id=subject_id,
                split=str(row["official_split"]),
                phq8_total=float(row["phq8_total"]),
                item_scores=item_scores,
                text=text,
                text_mask=text_mask,
                audio=audio,
                audio_mask=audio_mask,
                video=video,
                video_mask=video_mask,
            )
        )
    metadata_frame = pd.DataFrame(rows).sort_values("subject_id").reset_index(drop=True)
    metadata_frame.to_csv(out_dir / "edaic_public_questmf_feature_metadata.csv", index=False)
    if text_model is not None:
        del text_model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return subjects, {
        "feature_cache_dir": str(feature_dir),
        "feature_rows": int(len(subjects)),
        "text_feature_dim": TEXT_DIM,
        "audio_feature_dim": AUDIO_DIM,
        "video_feature_dim": VIDEO_DIM,
        "max_turns": MAX_TURNS,
        "feature_model_name": text_model_name,
    }


class QuestDataset(Dataset):
    def __init__(self, subjects: list[SubjectFeatures], question: int):
        self.subjects = subjects
        self.question = int(question)

    def __len__(self) -> int:
        return len(self.subjects)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, ...]:
        subject = self.subjects[index]
        label = subject.item_scores[self.question - 1]
        return (
            torch.from_numpy(subject.text),
            torch.from_numpy(subject.text_mask),
            torch.from_numpy(subject.audio),
            torch.from_numpy(subject.audio_mask),
            torch.from_numpy(subject.video),
            torch.from_numpy(subject.video_mask),
            torch.tensor(label, dtype=torch.long),
        )


class TextEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.lstm_1 = nn.LSTM(TEXT_DIM, 50, batch_first=True, bidirectional=True)
        self.attention = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.5)
        self.mlp = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(MAX_TURNS * 100, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 4),
        )

    def forward(self, values: torch.Tensor, mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden, _ = self.lstm_1(values)
        attended, _ = self.attention(hidden, hidden, hidden, key_padding_mask=mask)
        return self.mlp(attended), attended


class AudioEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.lstm_1 = nn.LSTM(AUDIO_DIM, 50, batch_first=True, bidirectional=True)
        self.attention1 = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.2)
        self.attention2 = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.2)
        self.mlp = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.2),
            nn.Linear(MAX_TURNS * 100, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 4),
        )

    def forward(self, values: torch.Tensor, mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden, _ = self.lstm_1(values)
        attended, _ = self.attention1(hidden, hidden, hidden, key_padding_mask=mask)
        attended2, _ = self.attention2(attended, attended, attended, key_padding_mask=mask)
        return self.mlp(attended2), attended2


class VideoEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.lstm_1 = nn.LSTM(VIDEO_DIM, 50, batch_first=True, bidirectional=True)
        self.attention1 = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.2)
        self.attention2 = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.2)
        self.mlp = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.2),
            nn.Linear(MAX_TURNS * 100, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, 4),
        )

    def forward(self, values: torch.Tensor, mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden, _ = self.lstm_1(values)
        attended, _ = self.attention1(hidden, hidden, hidden, key_padding_mask=mask)
        attended2, _ = self.attention2(attended, attended, attended, key_padding_mask=mask)
        return self.mlp(attended2), attended2


class TAVFusion(nn.Module):
    def __init__(self, text_model: TextEncoder, audio_model: AudioEncoder, video_model: VideoEncoder) -> None:
        super().__init__()
        self.txt_model = text_model
        self.aud_model = audio_model
        self.vid_model = video_model
        self.cross_aud_txt = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.8)
        self.cross_txt_aud = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.8)
        self.cross_vid_aud = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.8)
        self.cross_aud_vid = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.8)
        self.cross_txt_vid = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.8)
        self.cross_vid_txt = nn.MultiheadAttention(100, 4, batch_first=True, dropout=0.8)
        self.self_aud_txt_vid = nn.MultiheadAttention(200, 4, batch_first=True, dropout=0.8)
        self.self_vid_txt_aud = nn.MultiheadAttention(200, 4, batch_first=True, dropout=0.8)
        self.self_txt_aud_vid = nn.MultiheadAttention(200, 4, batch_first=True, dropout=0.8)
        self.mlp = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.8),
            nn.Linear(MAX_TURNS * 600, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 4),
        )
        for parameter in self.txt_model.parameters():
            parameter.requires_grad = False

    def forward(
        self,
        text: torch.Tensor,
        text_mask: torch.Tensor,
        audio: torch.Tensor,
        audio_mask: torch.Tensor,
        video: torch.Tensor,
        video_mask: torch.Tensor,
    ) -> torch.Tensor:
        _, text_att = self.txt_model(text, text_mask)
        _, audio_att = self.aud_model(audio, audio_mask)
        _, video_att = self.vid_model(video, video_mask)
        aud_txt, _ = self.cross_aud_txt(audio_att, text_att, text_att, key_padding_mask=text_mask)
        txt_aud, _ = self.cross_txt_aud(text_att, audio_att, audio_att, key_padding_mask=audio_mask)
        vid_aud, _ = self.cross_vid_aud(video_att, audio_att, audio_att, key_padding_mask=audio_mask)
        aud_vid, _ = self.cross_aud_vid(audio_att, video_att, video_att, key_padding_mask=video_mask)
        txt_vid, _ = self.cross_txt_vid(text_att, video_att, video_att, key_padding_mask=video_mask)
        vid_txt, _ = self.cross_vid_txt(video_att, text_att, text_att, key_padding_mask=text_mask)
        aud_txt_vid = torch.cat((aud_txt, aud_vid), dim=2)
        vid_txt_aud = torch.cat((vid_txt, vid_aud), dim=2)
        txt_aud_vid = torch.cat((txt_aud, txt_vid), dim=2)
        att_aud_txt_vid, _ = self.self_aud_txt_vid(aud_txt_vid, aud_txt_vid, aud_txt_vid, key_padding_mask=audio_mask)
        att_vid_txt_aud, _ = self.self_vid_txt_aud(vid_txt_aud, vid_txt_aud, vid_txt_aud, key_padding_mask=video_mask)
        att_txt_aud_vid, _ = self.self_txt_aud_vid(txt_aud_vid, txt_aud_vid, txt_aud_vid, key_padding_mask=text_mask)
        combined = torch.cat((att_aud_txt_vid, att_vid_txt_aud, att_txt_aud_vid), dim=2)
        return self.mlp(combined)


def clone_state_dict(model: nn.Module) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def class_weights(train_subjects: list[SubjectFeatures], question: int, beta: float) -> torch.Tensor:
    labels = [subject.item_scores[question - 1] for subject in train_subjects]
    counts = np.bincount(np.asarray(labels, dtype=np.int64), minlength=4)
    if np.any(counts == 0):
        raise ValueError(f"question {question} has missing train classes for ImbOLL: {counts.tolist()}")
    total = float(np.sum(counts))
    return torch.tensor((total / counts) ** beta, dtype=torch.float32)


def imboll_loss(logits: torch.Tensor, weights: torch.Tensor, labels: torch.Tensor, alpha: float) -> torch.Tensor:
    num_classes = logits.shape[1]
    class_ids = torch.arange(num_classes, device=logits.device, dtype=torch.float32).unsqueeze(0)
    labels_float = labels.to(dtype=torch.float32).unsqueeze(1)
    label_weights = weights.to(logits.device)[labels].unsqueeze(1)
    distances = torch.abs(labels_float - class_ids) * label_weights
    probabilities = torch.softmax(logits, dim=1)
    err = -torch.log(torch.clamp(1.0 - probabilities + EPS, min=EPS)) * torch.pow(distances, alpha)
    return torch.sum(err, dim=1).mean()


def qwk_numpy(true: np.ndarray, pred: np.ndarray) -> float | None:
    true = true.astype(np.int64)
    pred = pred.astype(np.int64)
    labels = sorted(set(true.tolist()) | set(pred.tolist()))
    if len(labels) <= 1:
        return None
    index = {label: idx for idx, label in enumerate(labels)}
    observed = np.zeros((len(labels), len(labels)), dtype=np.float64)
    for truth, guess in zip(true, pred, strict=False):
        observed[index[int(truth)], index[int(guess)]] += 1.0
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / float(np.sum(observed))
    weights = np.zeros_like(observed)
    for i in range(len(labels)):
        for j in range(len(labels)):
            weights[i, j] = ((i - j) ** 2) / float((len(labels) - 1) ** 2)
    expected_weighted = float(np.sum(weights * expected))
    if expected_weighted <= 0.0:
        return None
    return float(1.0 - float(np.sum(weights * observed)) / expected_weighted)


def evaluate_unimodal(
    model: TextEncoder | AudioEncoder | VideoEncoder,
    loader: DataLoader,
    modality: str,
    weights: torch.Tensor,
    alpha: float,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    losses: list[float] = []
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs: list[np.ndarray] = []
    with torch.inference_mode():
        for batch in loader:
            text, text_mask, audio, audio_mask, video, video_mask, y = [value.to(device) for value in batch]
            if modality == "text":
                logits, _ = model(text, text_mask)
            elif modality == "audio":
                logits, _ = model(audio, audio_mask)
            elif modality == "video":
                logits, _ = model(video, video_mask)
            else:
                raise ValueError(f"unknown modality: {modality}")
            loss = imboll_loss(logits, weights, y, alpha)
            losses.append(float(loss.item()) * int(y.numel()))
            prob = torch.softmax(logits, dim=1)
            preds.append(torch.argmax(prob, dim=1).detach().cpu().numpy())
            labels.append(y.detach().cpu().numpy())
            probs.append(prob.detach().cpu().numpy())
    pred_arr = np.concatenate(preds)
    label_arr = np.concatenate(labels)
    return {
        "loss": float(np.sum(losses) / max(1, len(label_arr))),
        "qwk": qwk_numpy(label_arr, pred_arr),
        "pred": pred_arr,
        "label": label_arr,
        "prob": np.vstack(probs),
    }


def evaluate_fusion(
    model: TAVFusion,
    loader: DataLoader,
    weights: torch.Tensor,
    alpha: float,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    losses: list[float] = []
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs: list[np.ndarray] = []
    with torch.inference_mode():
        for batch in loader:
            text, text_mask, audio, audio_mask, video, video_mask, y = [value.to(device) for value in batch]
            logits = model(text, text_mask, audio, audio_mask, video, video_mask)
            loss = imboll_loss(logits, weights, y, alpha)
            losses.append(float(loss.item()) * int(y.numel()))
            prob = torch.softmax(logits, dim=1)
            preds.append(torch.argmax(prob, dim=1).detach().cpu().numpy())
            labels.append(y.detach().cpu().numpy())
            probs.append(prob.detach().cpu().numpy())
    pred_arr = np.concatenate(preds)
    label_arr = np.concatenate(labels)
    return {
        "loss": float(np.sum(losses) / max(1, len(label_arr))),
        "qwk": qwk_numpy(label_arr, pred_arr),
        "pred": pred_arr,
        "label": label_arr,
        "prob": np.vstack(probs),
    }


def train_unimodal(
    model: TextEncoder | AudioEncoder | VideoEncoder,
    modality: str,
    train_loader: DataLoader,
    val_loader: DataLoader,
    weights: torch.Tensor,
    alpha: float,
    epochs: int,
    device: torch.device,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5.0e-4, eps=1.0e-8, weight_decay=1.0e-3)
    best_loss = math.inf
    best_state: dict[str, torch.Tensor] | None = None
    trace: list[dict[str, Any]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_count = 0
        for batch in train_loader:
            text, text_mask, audio, audio_mask, video, video_mask, y = [value.to(device) for value in batch]
            optimizer.zero_grad(set_to_none=True)
            if modality == "text":
                logits, _ = model(text, text_mask)
            elif modality == "audio":
                logits, _ = model(audio, audio_mask)
            elif modality == "video":
                logits, _ = model(video, video_mask)
            else:
                raise ValueError(f"unknown modality: {modality}")
            loss = imboll_loss(logits, weights, y, alpha)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item()) * int(y.numel())
            total_count += int(y.numel())
        eval_row = evaluate_unimodal(model, val_loader, modality, weights, alpha, device)
        train_loss = total_loss / max(1, total_count)
        val_loss = float(eval_row["loss"])
        if math.isfinite(val_loss) and val_loss < best_loss:
            best_loss = val_loss
            best_state = clone_state_dict(model)
        trace.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_qwk": eval_row["qwk"],
            }
        )
    if best_state is None:
        best_state = clone_state_dict(model)
    return best_state, {"best_val_loss": best_loss, "trace": trace}


def train_fusion(
    model: TAVFusion,
    train_loader: DataLoader,
    val_loader: DataLoader,
    weights: torch.Tensor,
    alpha: float,
    epochs: int,
    device: torch.device,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    model.to(device)
    optimizer = torch.optim.AdamW(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=5.0e-4,
        eps=1.0e-8,
        weight_decay=1.0e-3,
    )
    best_qwk = -math.inf
    best_loss = math.inf
    best_state: dict[str, torch.Tensor] | None = None
    trace: list[dict[str, Any]] = []
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_count = 0
        for batch in train_loader:
            text, text_mask, audio, audio_mask, video, video_mask, y = [value.to(device) for value in batch]
            optimizer.zero_grad(set_to_none=True)
            logits = model(text, text_mask, audio, audio_mask, video, video_mask)
            loss = imboll_loss(logits, weights, y, alpha)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item()) * int(y.numel())
            total_count += int(y.numel())
        eval_row = evaluate_fusion(model, val_loader, weights, alpha, device)
        train_loss = total_loss / max(1, total_count)
        val_loss = float(eval_row["loss"])
        val_qwk = eval_row["qwk"]
        comparable_qwk = float(val_qwk) if val_qwk is not None and math.isfinite(float(val_qwk)) else -math.inf
        if comparable_qwk > best_qwk or (comparable_qwk == best_qwk and val_loss < best_loss):
            best_qwk = comparable_qwk
            best_loss = val_loss
            best_state = clone_state_dict(model)
        trace.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_loss": val_loss,
                "val_qwk": val_qwk,
            }
        )
    if best_state is None:
        best_state = clone_state_dict(model)
    return best_state, {"best_val_loss": best_loss, "best_val_qwk": best_qwk, "trace": trace}


def make_loader(
    subjects: list[SubjectFeatures],
    question: int,
    *,
    batch_size: int,
    shuffle: bool,
    seed: int,
) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        QuestDataset(subjects, question),
        batch_size=batch_size,
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
    )


def existing_completed_keys(path: Path, required_subjects: int) -> set[tuple[int, int]]:
    if not path.exists():
        return set()
    frame = pd.read_csv(path)
    required = {"seed", "question_number", "subject_id"}
    if required - set(frame.columns):
        return set()
    completed: set[tuple[int, int]] = set()
    for (seed, question), group in frame.groupby(["seed", "question_number"], dropna=False):
        if int(group["subject_id"].nunique()) == required_subjects:
            completed.add((int(seed), int(question)))
    return completed


def load_progress_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict("records")


def write_progress_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["seed", "question_number", "subject_id"], kind="mergesort").reset_index(drop=True)
    frame.to_csv(path, index=False)


def prediction_rows_from_eval(
    eval_row: dict[str, Any],
    dev_subjects: list[SubjectFeatures],
    *,
    seed: int,
    question: int,
    alpha: float,
    beta: float,
    epochs_unimodal: int,
    epochs_fusion: int,
    text_model_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    preds = eval_row["pred"].astype(int)
    probs = eval_row["prob"]
    for idx, subject in enumerate(dev_subjects):
        rows.append(
            {
                "run_id": SPEC.run_id,
                "dataset": SPEC.dataset,
                "modality": SPEC.modality,
                "task": SPEC.task,
                "model": SPEC.model,
                "seed": int(seed),
                "fold": "official_dev",
                "task_type": SPEC.task_type,
                "subject_id": subject.subject_id,
                "split": "dev",
                "question_number": int(question),
                "question_name": QUESTION_COLUMNS[question - 1],
                "y_true": int(subject.item_scores[question - 1]),
                "y_pred": int(preds[idx]),
                "y_prob": json.dumps([float(value) for value in probs[idx]], ensure_ascii=True),
                "alpha": float(alpha),
                "beta": float(beta),
                "epochs_unimodal": int(epochs_unimodal),
                "epochs_fusion": int(epochs_fusion),
                "feature_model_name": text_model_name,
            }
        )
    return rows


def build_total_prediction_frame(item_predictions: pd.DataFrame, dev_subjects: list[SubjectFeatures]) -> pd.DataFrame:
    true_total_by_subject = {subject.subject_id: subject.phq8_total for subject in dev_subjects}
    rows: list[dict[str, Any]] = []
    for (seed, subject_id), group in item_predictions.groupby(["seed", "subject_id"], dropna=False):
        if int(group["question_number"].nunique()) != 8:
            continue
        rows.append(
            {
                "run_id": f"{RUN_ID}_total_audit",
                "dataset": SPEC.dataset,
                "modality": SPEC.modality,
                "task": "PHQ-8 regression",
                "model": SPEC.model,
                "seed": int(seed),
                "fold": "official_dev",
                "task_type": "severity_regression",
                "subject_id": str(subject_id),
                "split": "dev",
                "y_true": float(true_total_by_subject[str(subject_id)]),
                "y_pred": float(group["y_pred"].astype(float).sum()),
                "y_score": "",
            }
        )
    return pd.DataFrame(rows)


def write_report(out_dir: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E-DAIC QuestMF Public Reproduction",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        "## Protocol",
        "",
        "- Public source: `clpsych2025-questmf` QuestMF code.",
        "- Input interface: project E-DAIC manifest, official train/dev split, and detailed PHQ-8 item labels.",
        "- Model: PHQ-8 question-wise ordinal text/audio/video fusion with ImbOLL loss.",
        "- Text features: frozen `sentence-transformers/all-distilroberta-v1` turn embeddings.",
        "- Audio features: official openSMILE eGeMAPS turn pooling.",
        "- Video features: official ResNet turn pooling.",
        "- No test split, raw transcript text, source paths, audio, video frames, or checkpoints are written to prediction artifacts.",
        "",
        "## Audit",
        "",
        f"- Run: `{summary['run_id']}`",
        f"- Completed full matrix contract: `{summary['full_contract_completed']}`",
        f"- Seeds: `{summary['seeds']}`",
        f"- Questions: `{summary['questions']}`",
        f"- Item prediction rows: `{summary['item_prediction_rows']}`",
        f"- Bootstrap resamples: `{summary['bootstrap_resamples']}`",
    ]
    (out_dir / "edaic_public_questmf_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_ints(values: list[str] | None, default: list[int]) -> list[int]:
    if not values:
        return list(default)
    out: list[int] = []
    for value in values:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                out.append(int(part))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--text-model-name", default=DEFAULT_TEXT_MODEL)
    parser.add_argument("--hf-cache-dir", type=Path, default=DEFAULT_HF_CACHE)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--seeds", nargs="*", default=None)
    parser.add_argument("--questions", nargs="*", default=None)
    parser.add_argument("--alpha", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=0.5)
    parser.add_argument("--epochs-unimodal", type=int, default=OFFICIAL_UNIMODAL_EPOCHS)
    parser.add_argument("--epochs-fusion", type=int, default=OFFICIAL_FUSION_EPOCHS)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--encode-batch-size", type=int, default=32)
    parser.add_argument("--text-max-length", type=int, default=512)
    parser.add_argument("--bootstrap-resamples", type=int, default=1000)
    parser.add_argument("--force-features", action="store_true")
    parser.add_argument("--force-training", action="store_true")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    seeds = parse_ints(args.seeds, SEEDS)
    questions = parse_ints(args.questions, QUESTIONS)
    invalid_questions = sorted(set(questions) - set(QUESTIONS))
    if invalid_questions:
        raise ValueError(f"QuestMF question ids must be 1-8, got {invalid_questions}")
    device = as_device(args.device)
    if torch.cuda.is_available():
        torch.set_float32_matmul_precision("high")

    table = read_subject_table()
    subjects, feature_summary = build_feature_cache(
        table,
        args.out_dir,
        text_model_name=args.text_model_name,
        cache_dir=args.hf_cache_dir,
        local_files_only=args.local_files_only,
        device=device,
        text_max_length=args.text_max_length,
        encode_batch_size=args.encode_batch_size,
        force=args.force_features,
    )
    train_subjects = [subject for subject in subjects if subject.split == "train"]
    dev_subjects = [subject for subject in subjects if subject.split == "dev"]
    if len(train_subjects) != 163 or len(dev_subjects) != 56:
        raise ValueError(f"unexpected train/dev subject counts: {len(train_subjects)} / {len(dev_subjects)}")

    progress_path = args.out_dir / "edaic_public_questmf_item_predictions_progress.csv"
    trace_path = args.out_dir / "edaic_public_questmf_training_trace.csv"
    progress_rows = [] if args.force_training else load_progress_rows(progress_path)
    completed = set() if args.force_training else existing_completed_keys(progress_path, len(dev_subjects))
    trace_rows: list[dict[str, Any]] = [] if args.force_training or not trace_path.exists() else pd.read_csv(trace_path).to_dict("records")

    for seed in seeds:
        for question in questions:
            key = (int(seed), int(question))
            if key in completed:
                print(f"[questmf] skip completed seed={seed} question={question}", flush=True)
                continue
            set_seed(seed)
            weights = class_weights(train_subjects, question, args.beta)
            train_loader = make_loader(
                train_subjects,
                question,
                batch_size=args.batch_size,
                shuffle=True,
                seed=seed * 1000 + question,
            )
            val_loader = make_loader(
                dev_subjects,
                question,
                batch_size=args.batch_size,
                shuffle=False,
                seed=seed * 1000 + question,
            )
            print(f"[questmf] seed={seed} question={question} train text", flush=True)
            text_state, text_trace = train_unimodal(
                TextEncoder(),
                "text",
                train_loader,
                val_loader,
                weights,
                args.alpha,
                args.epochs_unimodal,
                device,
            )
            print(f"[questmf] seed={seed} question={question} train audio", flush=True)
            audio_state, audio_trace = train_unimodal(
                AudioEncoder(),
                "audio",
                train_loader,
                val_loader,
                weights,
                args.alpha,
                args.epochs_unimodal,
                device,
            )
            print(f"[questmf] seed={seed} question={question} train video", flush=True)
            video_state, video_trace = train_unimodal(
                VideoEncoder(),
                "video",
                train_loader,
                val_loader,
                weights,
                args.alpha,
                args.epochs_unimodal,
                device,
            )

            text_model = TextEncoder()
            text_model.load_state_dict(text_state)
            audio_model = AudioEncoder()
            audio_model.load_state_dict(audio_state)
            video_model = VideoEncoder()
            video_model.load_state_dict(video_state)
            fusion_model = TAVFusion(text_model, audio_model, video_model)
            print(f"[questmf] seed={seed} question={question} train tav", flush=True)
            fusion_state, fusion_trace = train_fusion(
                fusion_model,
                train_loader,
                val_loader,
                weights,
                args.alpha,
                args.epochs_fusion,
                device,
            )
            best_model = TAVFusion(TextEncoder(), AudioEncoder(), VideoEncoder())
            best_model.load_state_dict(fusion_state)
            best_model.to(device)
            eval_row = evaluate_fusion(best_model, val_loader, weights, args.alpha, device)
            new_rows = prediction_rows_from_eval(
                eval_row,
                dev_subjects,
                seed=seed,
                question=question,
                alpha=args.alpha,
                beta=args.beta,
                epochs_unimodal=args.epochs_unimodal,
                epochs_fusion=args.epochs_fusion,
                text_model_name=args.text_model_name,
            )
            progress_rows = [
                row
                for row in progress_rows
                if not (int(row.get("seed", -1)) == int(seed) and int(row.get("question_number", -1)) == int(question))
            ]
            progress_rows.extend(new_rows)
            write_progress_rows(progress_path, progress_rows)
            for stage, trace in [
                ("text", text_trace),
                ("audio", audio_trace),
                ("video", video_trace),
                ("tav", fusion_trace),
            ]:
                for epoch_row in trace["trace"]:
                    trace_rows.append(
                        {
                            "seed": int(seed),
                            "question_number": int(question),
                            "stage": stage,
                            **epoch_row,
                        }
                    )
            pd.DataFrame(trace_rows).to_csv(trace_path, index=False)
            completed.add(key)
            del text_model, audio_model, video_model, fusion_model, best_model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    prediction_frame = pd.DataFrame(progress_rows)
    required_full = {
        (seed, question)
        for seed in SEEDS
        for question in QUESTIONS
    }
    observed_full = existing_completed_keys(progress_path, len(dev_subjects))
    full_contract = (
        required_full.issubset(observed_full)
        and args.epochs_unimodal == OFFICIAL_UNIMODAL_EPOCHS
        and args.epochs_fusion == OFFICIAL_FUSION_EPOCHS
        and args.bootstrap_resamples >= 1000
    )
    item_predictions_path = args.out_dir / "edaic_public_questmf_item_predictions.csv"
    if full_contract:
        full_frame = prediction_frame[
            prediction_frame["seed"].astype(int).isin(SEEDS)
            & prediction_frame["question_number"].astype(int).isin(QUESTIONS)
        ].copy()
        full_frame = full_frame.sort_values(["seed", "question_number", "subject_id"], kind="mergesort").reset_index(drop=True)
        full_frame.to_csv(item_predictions_path, index=False)
        metrics_by_seed, metric_summary = metric_records(
            full_frame,
            bootstrap_resamples=args.bootstrap_resamples,
            seed=20260727,
        )
        metrics_by_seed.to_csv(args.out_dir / "phase2_metrics_by_seed.csv", index=False)
        metric_summary.to_csv(args.out_dir / "phase2_metric_summary.csv", index=False)
        total_frame = build_total_prediction_frame(full_frame, dev_subjects)
        total_frame.to_csv(args.out_dir / "edaic_public_questmf_total_predictions.csv", index=False)
        total_metrics = []
        for seed, group in total_frame.groupby("seed"):
            values = regression_metrics(group["y_true"], group["y_pred"])
            for metric, value in values.items():
                total_metrics.append({"seed": int(seed), "metric": metric, "value": value, "sample_count": int(len(group))})
        pd.DataFrame(total_metrics).to_csv(args.out_dir / "edaic_public_questmf_total_metrics_by_seed.csv", index=False)
    else:
        partial_frame = prediction_frame.copy()
        if not partial_frame.empty:
            partial_metrics_by_seed, partial_metric_summary = metric_records(
                partial_frame,
                bootstrap_resamples=min(args.bootstrap_resamples, 100),
                seed=20260727,
            )
            partial_metrics_by_seed.to_csv(args.out_dir / "edaic_public_questmf_partial_metrics_by_seed.csv", index=False)
            partial_metric_summary.to_csv(args.out_dir / "edaic_public_questmf_partial_metric_summary.csv", index=False)

    summary = {
        "generated_at": utc_now(),
        "run_id": RUN_ID,
        "official_source_dir": str(OFFICIAL_QUESTMF_DIR),
        "official_source_commit": "3776a2bb84927b2613abf5686322b63957158c68",
        "manifest_path": str(MANIFEST_PATH),
        "label_dir": str(LABEL_DIR),
        "text_model_name": args.text_model_name,
        "seeds": seeds,
        "questions": questions,
        "official_required_seeds": SEEDS,
        "official_required_questions": QUESTIONS,
        "alpha": float(args.alpha),
        "beta": float(args.beta),
        "epochs_unimodal": int(args.epochs_unimodal),
        "epochs_fusion": int(args.epochs_fusion),
        "bootstrap_resamples": int(args.bootstrap_resamples),
        "train_subjects": int(len(train_subjects)),
        "dev_subjects": int(len(dev_subjects)),
        "item_prediction_rows": int(len(prediction_frame)),
        "full_contract_completed": bool(full_contract),
        "completed_seed_question_blocks": int(len(observed_full)),
        "required_seed_question_blocks": int(len(required_full)),
        "feature_summary": feature_summary,
        "no_test_split_used": True,
        "raw_transcripts_written": False,
        "raw_paths_written": False,
        "raw_audio_written": False,
        "raw_video_written": False,
        "checkpoints_written": False,
    }
    (args.out_dir / "edaic_public_questmf_run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    write_report(args.out_dir, summary)
    print(f"Wrote {progress_path}")
    if full_contract:
        print(f"Wrote {args.out_dir / 'phase2_metric_summary.csv'}")
    else:
        print("QuestMF full matrix contract not complete; wrote partial metrics only.")


if __name__ == "__main__":
    main()
