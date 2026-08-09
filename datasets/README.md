# Dataset Workspace

Last updated: 2026-07-26 UTC

Canonical dataset root:

```text
/root/autodl-tmp/datasets
```

This directory contains local raw datasets, generated subject-level manifests,
and repeatable audit reports for the cross-scale depression modeling project.
Raw datasets are intentionally excluded from Git; use the registry and generated
manifests as the stable interface for experiments.

## Source Of Truth

- `registry.yaml`: canonical dataset registry and research-role mapping.
- `manifests/*_subjects.parquet`: subject/segment-level experiment interface.
- `audit/`: latest generated data-quality reports.
- `raw/`, `processed/`, `splits/`: reserved project-managed staging areas.

Regenerate manifests and audit reports with:

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```

## Latest Audit Snapshot

| Dataset | Subjects | Segments | Valid rows | Status | Role |
| --- | ---: | ---: | ---: | --- | --- |
| edaic | 275 | 275 | 275 | uploaded_official | primary development |
| cmdc | 78 | 936 | 908 | uploaded_official | Chinese cross-protocol validation |
| pdch | 100 | 167 | 165 | uploaded_extracted | hospital HAMD validation |
| modma | 52 | 1508 | 1503 | uploaded_official_with_invalid_files | controlled speech-task stress test |
| eatd | 162 | 486 | 486 | uploaded_official | Chinese valence stress test |
| mpdd_avg_2026 | 224 | 772 | 602 | uploaded_official_with_label_gaps | individual-difference and gait validation |

No subject-level split leakage was detected in the latest audit.

## Current Data Quality Notes

- PDCH audio has been extracted from the split archive into `PDCH/audio/wav_data`.
- PDCH subject `034A` has audio/text but no HAMD annotation and is excluded as `missing_label`.
- CMDC is treated as an official-layout upload. Its invalid rows reflect
  row-level metadata/modality availability, not an incomplete upload.
- MODMA is treated as an official-layout upload with 5 invalid WAV files:
  `02010004/24.wav` through `02010004/28.wav`.
- MPDD-AVG-2026 uses prefixed subject IDs, `elder_*` and `young_*`, because many numeric IDs overlap across age groups.
- MPDD-AVG-2026 has 170 raw/test rows without locally available labels and marks them as `missing_label`.

## Policy

- Do not train directly from ad hoc raw-directory scans.
- Load experiment inputs from generated manifests.
- Keep all train/dev/test splits subject-level; never split different segments,
  tasks, or modalities from the same subject across train and test.
- Remove stale static audit files when they duplicate generated reports.
