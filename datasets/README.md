# Dataset Workspace

Last updated: 2026-08-24 UTC

Canonical dataset root:

```text
/root/autodl-tmp/datasets
```

This directory contains local raw datasets, locally generated subject-level
manifests, public dataset schemas/examples, and repeatable aggregate audit
reports for the cross-scale depression modeling project. Raw datasets, real
row-level subject manifests, real file-integrity rows, and real subject split
maps are intentionally excluded from Git; use the registry and generated local
manifests as the stable interface for experiments.

## Source Of Truth

- `registry.yaml`: canonical dataset registry and research-role mapping.
- `schemas/`: public schemas for local subject manifests, integrity tables,
  and subject split maps.
- `examples/`: synthetic public examples with the expected columns.
- `manifests/*_subjects.csv` and `manifests/*_subjects.parquet`: local-only
  subject/segment-level experiment interface, regenerated from licensed local
  data.
- `audit/`: latest generated data-quality reports. Aggregate reports are
  versionable; `audit/file_integrity.csv` is local-only.
- `raw/`, `processed/`, `splits/`: reserved project-managed staging areas.
  Real subject split maps under `splits/` are local-only.

Regenerate manifests and audit reports with:

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```

## Latest Audit Snapshot

| Dataset | Subjects | Segments | Valid rows | Status | Role |
| --- | ---: | ---: | ---: | --- | --- |
| edaic | 275 | 275 | 275 | uploaded_official | primary development |
| daicwoz | 189 | 189 | 189 | uploaded_same_lineage_benchmark_control | AVEC2017 DAIC-WOZ benchmark/control |
| cmdc | 78 | 936 | 908 | uploaded_official | Chinese cross-protocol validation |
| pdch | 100 | 167 | 165 | uploaded_extracted | hospital HAMD validation |
| modma | 52 | 1508 | 1503 | uploaded_official_with_invalid_files | controlled speech-task stress test |
| eatd | 162 | 486 | 486 | uploaded_official | Chinese valence stress test |
| mpdd_avg_2026 | 224 | 772 | 602 | uploaded_official_with_label_gaps | individual-difference and gait validation |

No subject-level split leakage was detected in the latest audit.

## Current Data Quality Notes

- PDCH audio has been extracted from the split archive into `PDCH/audio/wav_data`.
- DAIC-WOZ is configured as an AVEC2017 Wizard-of-Oz benchmark/control from the DAIC lineage, not a separate raw-data copy or an independent corpus from E-DAIC. It reuses overlapping `edaic` 300-492 extracted subject folders through `DAIC-WOZ/extracted` symlinks and uses DAIC-WOZ official split/label files under `DAIC-WOZ/splits`.
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
- Do not pool `daicwoz` and `edaic` as independent datasets; their 300-492 subject folders overlap exactly. Use `daicwoz` only when reproducing the DAIC-WOZ/AVEC2017 benchmark contract.
- Keep real row-level manifests, integrity rows, and subject split maps
  local-only. Public releases should include only schema, synthetic examples,
  generated aggregate audits, and regeneration scripts unless dataset licenses
  are separately reviewed.
- Keep all train/dev/test splits subject-level; never split different segments,
  tasks, or modalities from the same subject across train and test.
- Remove stale static audit files when they duplicate generated reports.
