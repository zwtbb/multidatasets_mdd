# Session Memory: DAIC-WOZ Benchmark View

Status: complete
Last updated: 2026-08-24 UTC
Thread/task: Configure DAIC-WOZ as an E-DAIC-overlap benchmark view

## Scope

This session configures DAIC-WOZ for benchmark reproduction without
re-downloading or duplicating the overlapping E-DAIC subject folders.

## Current State

- DAIC-WOZ official AVEC2017 split files are present under
  `/root/autodl-tmp/datasets/DAIC-WOZ/splits/`.
- DAIC-WOZ local `extracted/` contains symlinks to
  `/root/autodl-tmp/datasets/edaic/extracted/` for 189 official subject IDs in
  the 300-492 range.
- Local verification found exact subject-ID overlap between the official
  DAIC-WOZ split subjects and E-DAIC extracted folders in the 300-492 range:
  189 matched, 0 missing locally, 0 extra local 300-492 folders outside the
  official DAIC-WOZ splits.
- The official DAIC-WOZ file index lists one `300_P.zip`; no duplicate
  physical `300_P` data copy is needed.

## Key Decisions

- Do not download DAIC-WOZ raw archives from Baidu Netdisk because the
  overlapping DAIC-WOZ subject folders are already extracted locally as part
  of E-DAIC.
- Register `daicwoz` as `uploaded_official_view_of_edaic`, not as an
  independent dataset upload.
- Use DAIC-WOZ official AVEC2017 split/label files for `daicwoz`; use E-DAIC
  split/label files for `edaic`.
- Do not pool `daicwoz` and `edaic` as independent datasets because subject
  overlap is exact for DAIC-WOZ IDs.

## Files Owned Or Touched

- `/root/autodl-tmp/.gitignore`
- `/root/autodl-tmp/datasets/registry.yaml`
- `/root/autodl-tmp/datasets/README.md`
- `/root/autodl-tmp/datasets/DAIC-WOZ/README.md`
- `/root/autodl-tmp/scripts/audit_datasets.py`
- `/root/autodl-tmp/memory/sessions/session_68_daicwoz_benchmark_view.md`

## Generated Artifacts

Regenerate manifests and aggregate audit with:

```bash
python /root/autodl-tmp/scripts/audit_datasets.py
```

Expected DAIC-WOZ generated artifacts:

- `/root/autodl-tmp/datasets/manifests/daicwoz_subjects.csv`
- `/root/autodl-tmp/datasets/manifests/daicwoz_subjects.parquet`
- `/root/autodl-tmp/datasets/audit/dataset_inventory.md`
- `/root/autodl-tmp/datasets/audit/file_integrity_summary.csv`
- `/root/autodl-tmp/datasets/audit/label_distribution.csv`
- `/root/autodl-tmp/datasets/audit/leakage_check.md`

Audit completed successfully on 2026-08-24 UTC. `daicwoz` has 189 subjects,
189 segments, 189 valid rows, official split counts train/dev/test =
107/35/47, and no subject-level split leakage.

## Blockers And Risks

- DAIC-WOZ is an overlapping benchmark view. Any pooled experiment must exclude
  duplicate subject use across `daicwoz` and `edaic`.
- DAIC-WOZ official test labels are limited compared with train/dev item-level
  files: `full_test_split.csv` supplies PHQ total/binary/gender, while
  item-level PHQ8 columns are present for train/dev.

## Next Handoff

Use `daicwoz` only when reproducing DAIC-WOZ/AVEC2017 benchmark results. Use
`edaic` for the current 275-subject E-DAIC project contract.
