#!/usr/bin/env python3
"""Build subject-level manifests and repeatable dataset audit reports."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import soundfile as sf
import yaml


ROOT = Path("/root/autodl-tmp")
DATASETS = ROOT / "datasets"
REGISTRY_PATH = DATASETS / "registry.yaml"
MANIFEST_DIR = DATASETS / "manifests"
AUDIT_DIR = DATASETS / "audit"

COMMON_COLUMNS = [
    "dataset",
    "subject_id",
    "session_id",
    "segment_id",
    "speaker",
    "task_type",
    "valence",
    "start_time",
    "end_time",
    "text_path",
    "audio_path",
    "video_path",
    "video_feature_type",
    "gait_path",
    "phq8_total",
    "phq8_items",
    "phq9_total",
    "phq9_items",
    "hamd17_total",
    "hamd17_items",
    "sds_total",
    "binary_label",
    "severity_label",
    "age",
    "gender",
    "personality",
    "health_condition",
    "official_split",
    "file_valid",
    "exclusion_reason",
]

EATD_TASKS = [
    ("positive", "positive"),
    ("neutral", "neutral"),
    ("negative", "negative"),
]

MODMA_TASK_MAP = {
    "01": "interview",
    "02": "interview",
    "03": "interview",
    "04": "interview",
    "05": "interview",
    "06": "interview",
    "07": "interview",
    "08": "interview",
    "09": "interview",
    "10": "interview",
    "11": "interview",
    "12": "reading",
    "13": "reading",
    "14": "reading",
    "15": "reading",
    "16": "reading",
    "17": "reading",
    "18": "reading",
    "19": "reading",
    "20": "picture_description",
    "21": "picture_description",
    "22": "picture_description",
    "23": "picture_description",
    "24": "affective_task",
    "25": "affective_task",
    "26": "affective_task",
    "27": "affective_task",
    "28": "affective_task",
    "29": "affective_task",
}


def blank_row(dataset: str, subject_id: str) -> dict[str, Any]:
    row = {column: None for column in COMMON_COLUMNS}
    row["dataset"] = dataset
    row["subject_id"] = str(subject_id)
    row["session_id"] = "default"
    row["file_valid"] = True
    return row


def norm_path(path: Path | None) -> str | None:
    if path is None:
        return None
    return str(path)


def read_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def first_notna(*values: Any) -> Any:
    for value in values:
        if not pd.isna(value):
            return value
    return None


def audio_status(path: Path | None, check_audio: bool) -> tuple[bool, str | None]:
    if path is None:
        return False, "missing_audio_path"
    if not path.exists():
        return False, "missing_audio_file"
    if not check_audio:
        return True, None
    try:
        info = sf.info(str(path))
        if info.frames <= 0 or info.samplerate <= 0:
            return False, "invalid_audio_empty_or_bad_rate"
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, f"invalid_audio:{type(exc).__name__}"


def write_manifest(dataset: str, rows: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for column in COMMON_COLUMNS:
        if column not in df.columns:
            df[column] = None
    df = df[COMMON_COLUMNS]
    parquet_path = MANIFEST_DIR / f"{dataset}_subjects.parquet"
    csv_path = MANIFEST_DIR / f"{dataset}_subjects.csv"
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False)
    return df


def load_edaic(root: Path, check_audio: bool) -> pd.DataFrame:
    splits = []
    for split in ["train", "dev", "test"]:
        p = root / f"{split}_split.csv"
        if p.exists():
            df = pd.read_csv(p)
            df["official_split"] = split
            splits.append(df)
    split_df = pd.concat(splits, ignore_index=True) if splits else pd.DataFrame()
    detailed = root / "labels" / "Detailed_PHQ8_Labels.csv"
    item_df = pd.read_csv(detailed) if detailed.exists() else pd.DataFrame()
    if not split_df.empty and not item_df.empty:
        df = split_df.merge(item_df, on="Participant_ID", how="left")
    else:
        df = split_df if not split_df.empty else item_df

    rows = []
    item_cols = [c for c in df.columns if c.startswith("PHQ_8") and c != "PHQ_8Total"]
    for _, rec in df.iterrows():
        sid = str(int(rec["Participant_ID"]))
        row = blank_row("edaic", sid)
        row["phq8_total"] = first_notna(rec.get("PHQ_8Total"), rec.get("PHQ_Score"))
        row["phq8_items"] = json.dumps({c: rec.get(c) for c in item_cols}, ensure_ascii=True)
        row["binary_label"] = rec.get("PHQ_Binary")
        row["severity_label"] = rec.get("PHQ_Score")
        row["gender"] = rec.get("Gender")
        row["health_condition"] = json.dumps(
            {"ptsd_binary": rec.get("PCL-C (PTSD)"), "ptsd_severity": rec.get("PTSD Severity")},
            ensure_ascii=True,
        )
        row["official_split"] = rec.get("official_split")
        subject_dir = next(iter((root / "data").glob(f"{sid}_P")), None)
        if subject_dir is None:
            subject_dir = next(iter((root / "extracted").glob(f"{sid}_P")), None)
        if subject_dir is None:
            row["exclusion_reason"] = "missing_subject_folder"
            row["file_valid"] = False
        else:
            transcript = subject_dir / f"{sid}_Transcript.csv"
            audio = subject_dir / f"{sid}_AUDIO.wav"
            features = subject_dir / "features"
            openface = features / f"{sid}_OpenFace2.1.0_Pose_gaze_AUs.csv"
            if not openface.exists():
                openface = features / f"{sid}_BoVW_openFace_2.1.0_Pose_Gaze_AUs.csv"
            audio_valid, audio_reason = audio_status(audio, check_audio)
            missing: list[str] = []
            if not transcript.exists():
                missing.append("missing_transcript")
            if not audio_valid and audio_reason:
                missing.append(audio_reason)
            if not openface.exists():
                missing.append("missing_video_features")
            row["segment_id"] = "interview"
            row["task_type"] = "virtual_interview"
            row["text_path"] = norm_path(transcript if transcript.exists() else None)
            row["audio_path"] = norm_path(audio if audio.exists() else None)
            row["video_path"] = norm_path(openface if openface.exists() else None)
            row["exclusion_reason"] = ",".join(missing) if missing else None
            row["file_valid"] = not missing
        rows.append(row)
    return write_manifest("edaic", rows)


def load_daicwoz(root: Path, check_audio: bool) -> pd.DataFrame:
    split_files = [
        ("train", root / "splits" / "train_split_Depression_AVEC2017.csv"),
        ("dev", root / "splits" / "dev_split_Depression_AVEC2017.csv"),
        ("test", root / "splits" / "full_test_split.csv"),
    ]
    frames = []
    for split, path in split_files:
        df = pd.read_csv(path)
        df["official_split"] = split
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)

    rows = []
    item_columns = [
        "PHQ8_NoInterest",
        "PHQ8_Depressed",
        "PHQ8_Sleep",
        "PHQ8_Tired",
        "PHQ8_Appetite",
        "PHQ8_Failure",
        "PHQ8_Concentrating",
        "PHQ8_Moving",
    ]
    for _, rec in df.iterrows():
        sid = str(int(rec["Participant_ID"]))
        row = blank_row("daicwoz", sid)
        row["phq8_total"] = first_notna(rec.get("PHQ8_Score"), rec.get("PHQ_Score"))
        row["phq8_items"] = json.dumps({c: rec.get(c) for c in item_columns}, ensure_ascii=True)
        row["binary_label"] = first_notna(rec.get("PHQ8_Binary"), rec.get("PHQ_Binary"))
        row["gender"] = rec.get("Gender")
        row["official_split"] = rec.get("official_split")
        subject_dir = root / "extracted" / f"{sid}_P"
        if not subject_dir.exists():
            row["exclusion_reason"] = "missing_subject_folder"
            row["file_valid"] = False
        else:
            transcript = subject_dir / f"{sid}_Transcript.csv"
            audio = subject_dir / f"{sid}_AUDIO.wav"
            features = subject_dir / "features"
            openface = features / f"{sid}_OpenFace2.1.0_Pose_gaze_AUs.csv"
            if not openface.exists():
                openface = features / f"{sid}_BoVW_openFace_2.1.0_Pose_Gaze_AUs.csv"
            audio_valid, audio_reason = audio_status(audio, check_audio)
            missing: list[str] = []
            if not transcript.exists():
                missing.append("missing_transcript")
            if not audio_valid and audio_reason:
                missing.append(audio_reason)
            if not openface.exists():
                missing.append("missing_video_features")
            row["segment_id"] = "interview"
            row["task_type"] = "virtual_interview"
            row["text_path"] = norm_path(transcript if transcript.exists() else None)
            row["audio_path"] = norm_path(audio if audio.exists() else None)
            row["video_path"] = norm_path(openface if openface.exists() else None)
            row["exclusion_reason"] = ",".join(missing) if missing else None
            row["file_valid"] = not missing
        rows.append(row)
    return write_manifest("daicwoz", rows)


def load_eatd(root: Path, check_audio: bool) -> pd.DataFrame:
    rows = []
    for subj in sorted(p for p in root.iterdir() if p.is_dir() and re.match(r"^[tv]_\d+$", p.name)):
        split = "train" if subj.name.startswith("t_") else "validation"
        raw_label = read_number(subj / "label.txt")
        sds_total = read_number(subj / "new_label.txt")
        binary = None if sds_total is None else int(sds_total >= 53)
        for task, valence in EATD_TASKS:
            audio = subj / f"{task}.wav"
            text = subj / f"{task}.txt"
            valid, reason = audio_status(audio, check_audio)
            row = blank_row("eatd", subj.name)
            row["segment_id"] = task
            row["task_type"] = "emotion_elicitation"
            row["valence"] = valence
            row["text_path"] = norm_path(text if text.exists() else None)
            row["audio_path"] = norm_path(audio)
            row["sds_total"] = sds_total
            row["binary_label"] = binary
            row["severity_label"] = raw_label
            row["official_split"] = split
            row["file_valid"] = valid and text.exists()
            row["exclusion_reason"] = reason if not valid else (None if text.exists() else "missing_text")
            rows.append(row)
    return write_manifest("eatd", rows)


def read_number(path: Path) -> float | None:
    if not path.exists():
        return None
    text = path.read_text(errors="ignore").strip()
    try:
        return float(text.split()[0])
    except Exception:
        return None


def load_cmdc(root: Path, check_audio: bool) -> pd.DataFrame:
    extracted = root / "extracted"
    info_path = extracted / "SubjectInfo.xlsx"
    info = pd.read_excel(info_path) if info_path.exists() else pd.DataFrame()
    meta = {}
    for _, rec in info.iterrows():
        sid = str(rec.get("ID"))
        meta[sid] = rec

    rows = []
    subjects = sorted(p for p in extracted.iterdir() if p.is_dir() and re.match(r"^(HC|MDD)\d+$", p.name))
    for subj in subjects:
        rec = meta.get(subj.name)
        for q in range(1, 13):
            audio = subj / f"Q{q}.wav"
            text = subj / f"Q{q}.txt"
            video_npy = subj / f"Q{q}.npy"
            video_csv = subj / f"Q{q}.csv"
            valid, reason = audio_status(audio, check_audio)
            row = blank_row("cmdc", subj.name)
            row["segment_id"] = f"Q{q}"
            row["task_type"] = "clinical_interview_question"
            row["text_path"] = norm_path(text if text.exists() else None)
            row["audio_path"] = norm_path(audio if audio.exists() else None)
            row["video_path"] = norm_path(video_npy if video_npy.exists() else (video_csv if video_csv.exists() else None))
            row["binary_label"] = int(subj.name.startswith("MDD"))
            if rec is not None:
                row["age"] = rec.get("age")
                row["gender"] = rec.get("gender")
                row["phq9_total"] = rec.get("PHQtotal")
                phq_items = {f"PHQ-{i}": rec.get(f"PHQ-{i}") for i in range(1, 10)}
                hamd_items = {f"HAMD{i:02d}": rec.get(f"HAMD{i:02d}") for i in range(1, 18)}
                if "V2HAMD05" in rec:
                    hamd_items["HAMD05"] = rec.get("V2HAMD05")
                row["phq9_items"] = json.dumps(phq_items, ensure_ascii=True)
                row["hamd17_total"] = rec.get("HAMDtotal")
                row["hamd17_items"] = json.dumps(hamd_items, ensure_ascii=True)
            missing = []
            if not audio.exists():
                missing.append("audio")
            if not text.exists():
                missing.append("text")
            if rec is None:
                missing.append("missing_subject_metadata")
            row["file_valid"] = valid and text.exists() and rec is not None
            if reason:
                missing.append(reason)
            row["exclusion_reason"] = ",".join(missing) if missing else None
            rows.append(row)
    return write_manifest("cmdc", rows)


def load_pdch(root: Path, check_audio: bool) -> pd.DataFrame:
    anno_path = root / "metadata" / "HAMD_annotation.xlsx"
    anno = pd.read_excel(anno_path) if anno_path.exists() else pd.DataFrame()
    audio_root = root / "audio" / "wav_data"
    rows = []
    labeled_subjects = set()
    for _, rec in anno.iterrows():
        sid = str(rec.get("序号")).strip()
        labeled_subjects.add(sid)
        items = {f"HAMD{i:02d}": rec.get(i) for i in range(1, 18)}
        item_values = pd.to_numeric(pd.Series(list(items.values())), errors="coerce")
        total = rec.get("总分")
        imputed_total = False
        if pd.isna(total) and item_values.notna().all():
            total = float(item_values.sum())
            imputed_total = True
        subject_dir = audio_root / sid
        audio_files = sorted(list(subject_dir.glob("*.wav")) + list(subject_dir.glob("*.WAV")))
        if not audio_files:
            row = blank_row("pdch", sid)
            row["task_type"] = "face_to_face_consultation"
            row["hamd17_total"] = total
            row["hamd17_items"] = json.dumps(items, ensure_ascii=True)
            row["severity_label"] = total
            row["health_condition"] = json.dumps(
                {"hamd_total_imputed_from_items": imputed_total}, ensure_ascii=True
            )
            row["file_valid"] = False
            row["exclusion_reason"] = "missing_audio_folder"
            rows.append(row)
            continue
        for audio in audio_files:
            segment = audio.stem
            text = subject_dir / f"{segment}.txt"
            valid, reason = audio_status(audio, check_audio)
            row = blank_row("pdch", sid)
            row["segment_id"] = segment
            row["task_type"] = "face_to_face_consultation"
            row["text_path"] = norm_path(text if text.exists() else None)
            row["audio_path"] = norm_path(audio)
            row["hamd17_total"] = total
            row["hamd17_items"] = json.dumps(items, ensure_ascii=True)
            row["severity_label"] = total
            row["health_condition"] = json.dumps(
                {"hamd_total_imputed_from_items": imputed_total}, ensure_ascii=True
            )
            row["file_valid"] = valid and text.exists()
            missing = []
            if reason:
                missing.append(reason)
            if not text.exists():
                missing.append("missing_text")
            row["exclusion_reason"] = ",".join(missing) if missing else None
            rows.append(row)
    if audio_root.exists():
        for subject_dir in sorted(p for p in audio_root.iterdir() if p.is_dir() and p.name not in labeled_subjects):
            for audio in sorted(list(subject_dir.glob("*.wav")) + list(subject_dir.glob("*.WAV"))):
                segment = audio.stem
                text = subject_dir / f"{segment}.txt"
                valid, reason = audio_status(audio, check_audio)
                row = blank_row("pdch", subject_dir.name)
                row["segment_id"] = segment
                row["task_type"] = "face_to_face_consultation"
                row["text_path"] = norm_path(text if text.exists() else None)
                row["audio_path"] = norm_path(audio)
                row["file_valid"] = False
                missing = ["missing_label"]
                if reason:
                    missing.append(reason)
                if not text.exists():
                    missing.append("missing_text")
                row["exclusion_reason"] = ",".join(missing)
                rows.append(row)
    return write_manifest("pdch", rows)


def load_modma(root: Path, check_audio: bool) -> pd.DataFrame:
    audio_root = root / "audio_lanzhou_2015"
    meta_path = audio_root / "subjects_information_audio_lanzhou_2015.xlsx"
    meta_df = pd.read_excel(meta_path) if meta_path.exists() else pd.DataFrame()
    meta = {}
    for _, rec in meta_df.iterrows():
        raw = str(rec.get("subject id"))
        sid = re.sub(r"\D", "", raw).zfill(8)
        meta[sid] = rec
    rows = []
    for subj in sorted(p for p in audio_root.iterdir() if p.is_dir()):
        rec = meta.get(subj.name)
        for audio in sorted(subj.glob("*.wav")) + sorted(subj.glob("*.WAV")):
            segment = audio.stem
            valid, reason = audio_status(audio, check_audio)
            row = blank_row("modma", subj.name)
            row["segment_id"] = segment
            row["task_type"] = MODMA_TASK_MAP.get(segment, "unknown_audio_task")
            row["audio_path"] = norm_path(audio)
            if rec is not None:
                row["age"] = rec.get("age")
                row["gender"] = rec.get("gender")
                row["phq9_total"] = rec.get("PHQ-9")
                row["binary_label"] = 1 if str(rec.get("type")).upper() == "MDD" else 0
                row["health_condition"] = str(rec.get("type"))
            row["file_valid"] = valid
            row["exclusion_reason"] = reason
            rows.append(row)
    return write_manifest("modma", rows)


def load_mpdd_avg_2026(root: Path, check_audio: bool) -> pd.DataFrame:
    label_frames = []
    for group_dir, age_group in [("Train-MPDD-Elder", "elder"), ("Train-MPDD-Young", "young")]:
        label_path = root / group_dir / "split_labels_train.csv"
        if label_path.exists():
            labels = pd.read_csv(label_path)
            labels["age_group"] = age_group
            labels["official_split"] = "train"
            labels["ID"] = labels["ID"].astype(str)
            label_frames.append(labels)
    labels = pd.concat(label_frames, ignore_index=True) if label_frames else pd.DataFrame()

    descriptions = {}
    elder_desc = root / "Train-MPDD-Elder" / "personalized_descriptions.csv"
    if elder_desc.exists():
        for _, rec in pd.read_csv(elder_desc).iterrows():
            descriptions[("elder", str(rec.get("id")))] = rec.get("description")
    young_desc = root / "Train-MPDD-Young" / "descriptions.csv"
    if young_desc.exists():
        for _, rec in pd.read_csv(young_desc).iterrows():
            descriptions[("young", str(rec.get("ID")))] = rec.get("Descriptions")

    raw_dirs = [
        ("elder", "train", root / "privacy-constrained-raw-Elder-train" / "audio"),
        ("elder", "test", root / "privacy-constrained-raw-Elder-test" / "audio"),
        (
            "young",
            "train",
            root
            / "privacy-constrained-raw-Young"
            / "privacy-constrained-raw-Young-train"
            / "audio",
        ),
        (
            "young",
            "test",
            root
            / "privacy-constrained-raw-Young"
            / "privacy-constrained-raw-Young-test"
            / "audio",
        ),
    ]
    rows = []
    seen_segments = set()
    for age_group, split_hint, audio_root in raw_dirs:
        if not audio_root.exists():
            continue
        for audio in sorted(list(audio_root.rglob("*.wav")) + list(audio_root.rglob("*.WAV"))):
            sid = audio.parent.name
            segment = audio.stem
            key = (age_group, sid, segment, str(audio))
            if key in seen_segments:
                continue
            seen_segments.add(key)
            recs = labels[(labels["age_group"] == age_group) & (labels["ID"] == sid)] if not labels.empty else pd.DataFrame()
            rec = recs.iloc[0] if not recs.empty else None
            valid, reason = audio_status(audio, check_audio)
            row = blank_row("mpdd_avg_2026", f"{age_group}_{sid}")
            row["segment_id"] = segment
            row["task_type"] = "mpdd_avg_audio_task"
            row["audio_path"] = norm_path(audio)
            row["gait_path"] = find_modality_path(root, age_group, split_hint, sid, "IMU")
            video_features = find_mpdd_video_feature_paths(root, age_group, split_hint, sid)
            if rec is not None:
                row["phq9_total"] = first_notna(rec.get("PHQ-9"), rec.get("phq9_score"))
                row["binary_label"] = rec.get("label2")
                row["severity_label"] = rec.get("label3")
                row["official_split"] = rec.get("split", split_hint)
            else:
                row["official_split"] = split_hint
                row["exclusion_reason"] = "missing_label"
            row["age"] = age_group
            row["personality"] = descriptions.get((age_group, sid))
            row["file_valid"] = valid and rec is not None
            if reason:
                row["exclusion_reason"] = reason
            for video_path, video_feature_type in video_features:
                feature_row = row.copy()
                feature_row["video_path"] = video_path
                feature_row["video_feature_type"] = video_feature_type
                rows.append(feature_row)
    return write_manifest("mpdd_avg_2026", rows)


def find_modality_path(root: Path, age_group: str, split_hint: str, sid: str, modality: str) -> str | None:
    group = "Elder" if age_group == "elder" else "Young"
    candidates = []
    if split_hint == "train":
        candidates.append(root / f"Train-MPDD-{group}" / modality / "train" / sid)
        candidates.append(root / f"Train-MPDD-{group}" / modality / sid)
    else:
        candidates.append(root / f"Test-MPDD-{group}" / modality / sid)
        candidates.append(root / f"Test-MPDD-{group}" / modality / "test" / sid)
    for base in candidates:
        if base.exists():
            files = sorted([p for p in base.rglob("*") if p.is_file()])
            if files:
                return str(files[0])
    return None


def find_mpdd_video_feature_paths(
    root: Path,
    age_group: str,
    split_hint: str,
    sid: str,
) -> list[tuple[str | None, str | None]]:
    group = "Elder" if age_group == "elder" else "Young"
    candidates: list[tuple[Path, str | None]] = []
    if split_hint == "train":
        candidates.extend(
            [
                (root / f"Train-MPDD-{group}" / "Video" / "train" / "resnet" / sid, "resnet_npy"),
                (root / f"Train-MPDD-{group}" / "Video" / "resnet" / sid, "resnet_npy"),
                (root / f"Train-MPDD-{group}" / "Video" / "train" / "openface" / sid, "openface"),
                (root / f"Train-MPDD-{group}" / "Video" / "openface" / sid, "openface"),
                (root / f"Train-MPDD-{group}" / "Video" / "train" / sid, None),
                (root / f"Train-MPDD-{group}" / "Video" / sid, None),
            ]
        )
    else:
        candidates.extend(
            [
                (root / f"Test-MPDD-{group}" / "Video" / "resnet" / sid, "resnet_npy"),
                (root / f"Test-MPDD-{group}" / "Video" / "test" / "resnet" / sid, "resnet_npy"),
                (root / f"Test-MPDD-{group}" / "Video" / "openface" / sid, "openface"),
                (root / f"Test-MPDD-{group}" / "Video" / "test" / "openface" / sid, "openface"),
                (root / f"Test-MPDD-{group}" / "Video" / sid, None),
                (root / f"Test-MPDD-{group}" / "Video" / "test" / sid, None),
            ]
        )
    found: list[tuple[str | None, str | None]] = []
    observed: set[tuple[str, str | None]] = set()
    for base, feature_type in candidates:
        if base.exists():
            files = sorted([p for p in base.rglob("*") if p.is_file()])
            if files:
                inferred_type = feature_type or ("resnet_npy" if files[0].suffix == ".npy" else None)
                key = (str(files[0]), inferred_type)
                if key not in observed:
                    observed.add(key)
                    found.append((str(files[0]), inferred_type))
    return found or [(None, None)]


def load_absent(dataset: str) -> pd.DataFrame:
    row = blank_row(dataset, "none")
    row["file_valid"] = False
    row["exclusion_reason"] = "dataset_absent"
    return write_manifest(dataset, [row])


def build_all(check_audio: bool) -> dict[str, pd.DataFrame]:
    registry = read_registry()
    loaders = {
        "edaic": load_edaic,
        "daicwoz": load_daicwoz,
        "cmdc": load_cmdc,
        "pdch": load_pdch,
        "modma": load_modma,
        "eatd": load_eatd,
        "mpdd_avg_2026": load_mpdd_avg_2026,
    }
    frames = {}
    for dataset, cfg in registry.items():
        root = Path(cfg["raw_root"])
        if cfg.get("status") == "absent" or not root.exists():
            frames[dataset] = load_absent(dataset)
            continue
        if dataset in loaders:
            frames[dataset] = loaders[dataset](root, check_audio)
        else:
            frames[dataset] = load_absent(dataset)
    return frames


def audit_unit_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse manifest feature variants to one sample row for dataset audits."""

    usable = df[df["subject_id"] != "none"].copy()
    key_columns = [
        column
        for column in [
            "dataset",
            "subject_id",
            "session_id",
            "segment_id",
            "task_type",
            "official_split",
            "text_path",
            "audio_path",
            "gait_path",
        ]
        if column in usable.columns
    ]
    if not key_columns:
        return usable
    return usable.drop_duplicates(key_columns)


def dataset_inventory(frames: dict[str, pd.DataFrame], registry: dict[str, Any]) -> str:
    lines = [
        "# Dataset Inventory",
        "",
        "Generated by `scripts/audit_datasets.py`.",
        "",
        "| Dataset | Role | Status | Subjects | Sessions | Segments | Valid rows | Main label | Protocol |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for name, df in frames.items():
        cfg = registry.get(name, {})
        usable = audit_unit_frame(df)
        subjects = usable["subject_id"].nunique()
        sessions = usable[["subject_id", "session_id"]].drop_duplicates().shape[0]
        segments = len(usable)
        valid = int(usable["file_valid"].fillna(False).sum())
        lines.append(
            f"| {name} | {cfg.get('role')} | {cfg.get('status')} | {subjects} | {sessions} | {segments} | {valid} | {cfg.get('label_type')} | {cfg.get('protocol')} |"
        )
    lines.extend(
        [
            "",
            "## Modeling gate",
            "",
            "- Use `edaic` as the primary development dataset.",
            "- Use `daicwoz` only as the AVEC2017 benchmark view over the overlapping E-DAIC 300-492 subjects; do not pool it with `edaic` as an independent dataset.",
            "- Use `cmdc`, `pdch`, `modma`, `eatd`, and `mpdd_avg_2026` as role-specific validation or stress-test datasets.",
            "- Do not pool segments across datasets until subject-level split and leakage checks pass.",
            "- CMDC is treated as `uploaded_official`; row-level invalidity reflects metadata/modality availability, not an incomplete upload.",
            "- PDCH audio has been extracted; subject `034A` has audio/text but no HAMD annotation and is excluded by `missing_label`.",
        ]
    )
    return "\n".join(lines) + "\n"


def label_distribution(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in frames.items():
        subj = df.drop_duplicates(["dataset", "subject_id"])
        for label in ["binary_label", "phq8_total", "phq9_total", "hamd17_total", "sds_total", "severity_label"]:
            series = pd.to_numeric(subj[label], errors="coerce") if label in subj else pd.Series(dtype=float)
            nonnull = int(series.notna().sum())
            rows.append(
                {
                    "dataset": name,
                    "label": label,
                    "nonnull_subjects": nonnull,
                    "missing_subjects": int(len(subj) - nonnull),
                    "min": series.min() if nonnull else None,
                    "max": series.max() if nonnull else None,
                    "mean": series.mean() if nonnull else None,
                    "positive_subjects": int((series == 1).sum()) if label == "binary_label" else None,
                }
            )
    return pd.DataFrame(rows)


def file_integrity_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in frames.items():
        unit_df = audit_unit_frame(df)
        reasons = Counter(
            reason
            for reason in unit_df["exclusion_reason"].fillna("")
            for reason in str(reason).split(",")
            if reason
        )
        rows.append(
            {
                "dataset": name,
                "rows": len(unit_df),
                "manifest_rows": len(df),
                "subjects": unit_df["subject_id"].nunique(),
                "valid_rows": int(unit_df["file_valid"].fillna(False).sum()),
                "invalid_rows": int((~unit_df["file_valid"].fillna(False)).sum()),
                "missing_text_rows": int(unit_df["text_path"].isna().sum()),
                "missing_audio_rows": int(unit_df["audio_path"].isna().sum()),
                "missing_video_rows": int(unit_df["video_path"].isna().sum()),
                "missing_gait_rows": int(unit_df["gait_path"].isna().sum()),
                "exclusion_reasons": json.dumps(reasons, ensure_ascii=True, sort_keys=True),
            }
        )
    return pd.DataFrame(rows)


def file_integrity_rows(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in frames.items():
        for _, rec in df.iterrows():
            rows.append(
                {
                    "dataset": name,
                    "subject_id": rec.get("subject_id"),
                    "session_id": rec.get("session_id"),
                    "segment_id": rec.get("segment_id"),
                    "task_type": rec.get("task_type"),
                    "official_split": rec.get("official_split"),
                    "text_present": pd.notna(rec.get("text_path")),
                    "audio_present": pd.notna(rec.get("audio_path")),
                    "video_present": pd.notna(rec.get("video_path")),
                    "gait_present": pd.notna(rec.get("gait_path")),
                    "label_present": any(
                        pd.notna(rec.get(label))
                        for label in [
                            "phq8_total",
                            "phq9_total",
                            "hamd17_total",
                            "sds_total",
                            "binary_label",
                            "severity_label",
                        ]
                    ),
                    "file_valid": bool(rec.get("file_valid")),
                    "exclusion_reason": rec.get("exclusion_reason"),
                    "video_feature_type": rec.get("video_feature_type"),
                    "text_path": rec.get("text_path"),
                    "audio_path": rec.get("audio_path"),
                    "video_path": rec.get("video_path"),
                    "gait_path": rec.get("gait_path"),
                }
            )
    return pd.DataFrame(rows)


def leakage_report(frames: dict[str, pd.DataFrame]) -> str:
    lines = ["# Leakage Check", "", "Generated by `scripts/audit_datasets.py`.", ""]
    for name, df in frames.items():
        raw_usable = df[df["subject_id"] != "none"]
        usable = audit_unit_frame(df)
        split_counts = usable.groupby("subject_id")["official_split"].nunique(dropna=True)
        leaked = split_counts[split_counts > 1]
        dup_subject_rows = int(usable.duplicated(["subject_id", "session_id", "segment_id"], keep=False).sum())
        feature_variant_rows = int(len(raw_usable) - len(usable))
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- Unique subjects: {usable['subject_id'].nunique()}")
        lines.append(f"- Duplicate subject/session/segment rows: {dup_subject_rows}")
        if feature_variant_rows:
            lines.append(f"- Manifest feature-variant rows collapsed for audit: {feature_variant_rows}")
        lines.append(f"- Subjects appearing in more than one official split: {len(leaked)}")
        if len(leaked):
            sample = ", ".join(list(leaked.index[:20]))
            lines.append(f"- Leakage sample: {sample}")
        else:
            lines.append("- Split leakage: none detected at subject level.")
        lines.append("")
    lines.append("## MPDD directory duplication check")
    lines.append("")
    mpdd = frames.get("mpdd_avg_2026", pd.DataFrame())
    if not mpdd.empty:
        raw = audit_unit_frame(mpdd)
        raw["base_subject"] = raw["subject_id"].str.replace(r"^(elder|young)_", "", regex=True)
        by_group_split_df = (
            raw.drop_duplicates(["subject_id", "official_split"])
            .assign(age_group=raw["subject_id"].str.extract(r"^(elder|young)_", expand=False))
            .groupby(["age_group", "official_split"])["subject_id"]
            .nunique()
            .reset_index(name="subjects")
        )
        overlap = set(raw[raw["subject_id"].str.startswith("elder_")]["base_subject"]) & set(
            raw[raw["subject_id"].str.startswith("young_")]["base_subject"]
        )
        elder_train = set(
            raw[(raw["subject_id"].str.startswith("elder_")) & (raw["official_split"] == "train")]["base_subject"]
        )
        elder_test = set(
            raw[(raw["subject_id"].str.startswith("elder_")) & (raw["official_split"] == "test")]["base_subject"]
        )
        young_train = set(
            raw[(raw["subject_id"].str.startswith("young_")) & (raw["official_split"] == "train")]["base_subject"]
        )
        young_test = set(
            raw[(raw["subject_id"].str.startswith("young_")) & (raw["official_split"] == "test")]["base_subject"]
        )
        lines.append(
            f"- Subject counts by group/split: {json.dumps(by_group_split_df.to_dict('records'), ensure_ascii=True, sort_keys=True)}"
        )
        lines.append(f"- Elder train/test numeric ID overlap: {len(elder_train & elder_test)}")
        lines.append(f"- Young train/test numeric ID overlap: {len(young_train & young_test)}")
        lines.append(f"- Same numeric IDs present in both young and elder groups: {len(overlap)}")
        lines.append("- These are treated as distinct subjects by prefixing `young_` or `elder_`.")
        if overlap:
            lines.append(f"- Numeric overlap sample: {', '.join(sorted(overlap)[:30])}")
    return "\n".join(lines) + "\n"


def write_reports(frames: dict[str, pd.DataFrame]) -> None:
    registry = read_registry()
    (AUDIT_DIR / "dataset_inventory.md").write_text(dataset_inventory(frames, registry), encoding="utf-8")
    label_distribution(frames).to_csv(AUDIT_DIR / "label_distribution.csv", index=False)
    file_integrity_rows(frames).to_csv(AUDIT_DIR / "file_integrity.csv", index=False)
    file_integrity_summary(frames).to_csv(AUDIT_DIR / "file_integrity_summary.csv", index=False)
    (AUDIT_DIR / "leakage_check.md").write_text(leakage_report(frames), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-audio-decode", action="store_true", help="Only check file existence, not audio readability.")
    args = parser.parse_args()
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    frames = build_all(check_audio=not args.skip_audio_decode)
    write_reports(frames)
    print(f"Wrote manifests to {MANIFEST_DIR}")
    print(f"Wrote audit reports to {AUDIT_DIR}")


if __name__ == "__main__":
    main()
