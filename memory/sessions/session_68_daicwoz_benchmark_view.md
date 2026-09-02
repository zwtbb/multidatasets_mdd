# Session Memory: DAIC-WOZ Benchmark View

Status: complete
Last updated: 2026-08-24 UTC
Thread/task: Configure DAIC-WOZ as a DAIC-lineage benchmark/control view

## Scope

This session configures DAIC-WOZ for benchmark reproduction and same-lineage
PHQ-8 control analyses without re-downloading or duplicating locally
overlapping subject folders.

## Current State

- DAIC-WOZ official AVEC2017 split files are present under
  `/root/autodl-tmp/datasets/DAIC-WOZ/splits/`.
- DAIC-WOZ local `extracted/` contains symlinks to the locally available
  `/root/autodl-tmp/datasets/edaic/extracted/` folders for 189 official subject
  IDs in the 300-492 range.
- Local verification found exact subject-ID overlap between the official
  DAIC-WOZ split subjects and the locally available E-DAIC extracted folders in
  the 300-492 range:
  189 matched, 0 missing locally, 0 extra local 300-492 folders outside the
  official DAIC-WOZ splits.
- The official DAIC-WOZ file index lists one `300_P.zip`; no duplicate
  physical `300_P` data copy is needed.

## Key Decisions

- Do not download DAIC-WOZ raw archives from Baidu Netdisk because the
  overlapping DAIC-WOZ subject folders are already available locally.
- Register `daicwoz` as an AVEC2017 Wizard-of-Oz benchmark/control from the
  DAIC lineage, not as an independent dataset upload.
- Use DAIC-WOZ official AVEC2017 split/label files for `daicwoz`; use E-DAIC
  split/label files for `edaic`.
- E-DAIC is the extended DAIC dataset. Do not pool `daicwoz` and `edaic` as
  independent datasets because their 300-492 subjects overlap heavily.

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

- DAIC-WOZ is a same-lineage benchmark/control view. Any pooled experiment must
  exclude duplicate subject use across `daicwoz` and `edaic`.
- DAIC-WOZ official test labels are limited compared with train/dev item-level
  files: `full_test_split.csv` supplies PHQ total/binary/gender, while
  item-level PHQ8 columns are present for train/dev.

## Next Handoff

Use `daicwoz` when reproducing DAIC-WOZ/AVEC2017 benchmark results or when a
same-scale PHQ-8 lineage control is explicitly needed. Use `edaic` for the
current 275-subject E-DAIC project contract.
