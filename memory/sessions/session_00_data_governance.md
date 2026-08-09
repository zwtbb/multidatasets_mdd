# Session Memory: 第零阶段 Data Governance

Status: complete
Last updated: 2026-08-04 UTC
Thread/task: `第零阶段` (`019f9847-5251-7ab3-a830-a24c26181f28`)

## Scope

This session established the data-governance layer and Git hygiene for the
project. It did not run final modeling experiments.

## Current State

- Local Git repository was initialized at `/root/autodl-tmp` and the default
  branch was renamed to `main`.
- `gh` was installed and verified as version 2.96.0, but it is not
  authenticated.
- Raw datasets remain in their existing top-level directories under
  `/root/autodl-tmp/datasets/`; they were not moved into `datasets/raw/` to
  avoid breaking existing paths.
- `datasets/registry.yaml` is the logical source of truth for dataset paths,
  labels, modalities, roles, and status.
- Generated manifests under `datasets/manifests/` are the experiment input
  interface.
- `datasets/DATASET_AUDIT.md` was deleted because it duplicated generated audit
  outputs and contained stale conclusions.

## Key Decisions

- MPDD 2025 is out of scope for current auditing.
- All splits must be subject-level.
- Training and audit code should resolve through the registry and manifests,
  not raw directory scans.
- Stale governance Markdown should be updated or removed immediately.

## Generated Audit Summary

Source of truth: `/root/autodl-tmp/datasets/audit/`

Latest dataset audit summary:

| Dataset | Subjects | Segments | Valid rows | Status |
| --- | ---: | ---: | ---: | --- |
| edaic | 275 | 275 | 275 | uploaded_official |
| cmdc | 78 | 936 | 908 | uploaded_official |
| pdch | 100 | 167 | 165 | uploaded_extracted |
| modma | 52 | 1508 | 1503 | uploaded_official_with_invalid_files |
| eatd | 162 | 486 | 486 | uploaded_official |
| mpdd_avg_2026 | 224 | 772 | 602 | uploaded_official_with_label_gaps |

No subject-level split leakage was detected in
`/root/autodl-tmp/datasets/audit/leakage_check.md`.

## Data Quality Notes

- CMDC is an official-layout upload, not partial. Its metadata risk is that
  `SubjectInfo.xlsx` duplicates `MDD20` and omits folder `MDD21`.
- PDCH audio was extracted from split archive volumes and now lives under
  `/root/autodl-tmp/datasets/PDCH/audio/wav_data/`.
- PDCH subject `034A` has two audio/text segments but no HAMD annotation.
- MODMA has five invalid WAV files: `02010004/24.wav` through `02010004/28.wav`.
- MPDD subject IDs are prefixed with `young_` and `elder_` to prevent false
  duplicate-subject handling.

## Files Owned Or Touched

- `/root/autodl-tmp/AGENTS.md`
- `/root/autodl-tmp/.gitignore`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/datasets/registry.yaml`
- `/root/autodl-tmp/datasets/README.md`
- `/root/autodl-tmp/scripts/audit_datasets.py`
- `/root/autodl-tmp/docs/experiment_direction.md`
- Generated files under `/root/autodl-tmp/datasets/manifests/`
- Generated files under `/root/autodl-tmp/datasets/audit/`

## Regeneration Commands

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```

## Next Handoff

Use this session memory only for data-governance context. For Phase 2 baseline
details, read `session_01_phase1_phase2_baselines.md`.

