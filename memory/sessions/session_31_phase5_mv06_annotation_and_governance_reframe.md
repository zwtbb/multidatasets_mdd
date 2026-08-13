# Session Memory: Phase 5 MV06 Annotation And Governance Reframe

Status: complete
Last updated: 2026-08-13 UTC
Thread/task: main agent MV06 annotation import, agreement fix, and plan reframe

## Scope

This session imports the user-completed local MV06 human annotation workbook,
fixes the MV06 agreement export to report dataset-stratified kappa, refreshes
the Phase 5 full-method gate, and updates the project plan toward partial
measurement invariance.

It also starts a non-destructive latest-tree mitigation for public row-level
dataset-table exposure by keeping real manifests, integrity rows, and subject
split maps local-only while adding public schema and synthetic example files.
It does not force-push or rewrite remote history.

## Current State

- Superseded for current MV06 annotation counts by
  `memory/sessions/session_48_mv06_annotation_import_round2.md`. The historical
  first-import facts below are retained to explain the earlier agreement-gate
  and governance reframe.
- Imported the filled local workbook from the Codex attachment into the ignored
  default MV06 human workbook path:
  `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/p5_mv06_local_annotation_workbook_predictions.csv`.
- Backed up the previous local workbook as an ignored predictions-named backup
  in the same workbench directory.
- Updated `scripts/phase5_summarize_mv06_evidence_annotations.py` so
  `agreement_summary.csv` includes a `dataset` column and reports agreement for
  `ALL`, `cmdc`, `edaic`, and `pdch` separately.
- Reran the MV06 summary gate. Current status:
  `ready_for_aggregate_evidence_review`.
- MV06 aggregate gate counts:
  - 30 completed candidates;
  - 20 double-annotated candidates;
  - 0 invalid-value issue rows;
  - artifact hygiene passed.
- Dataset-stratified first-pass agreement:
  - ALL evidence-presence kappa `0.808`;
  - CMDC evidence-presence kappa `0.643`;
  - PDCH evidence-presence kappa `1.000`;
  - E-DAIC has 2 double pairs with degenerate marginals, so kappa is undefined
    in this pass.
- Reran the MV06 human review pack so tracked progress aggregates reflect the
  imported human annotations.
- Updated `scripts/phase5_full_method_gate_audit.py` to read the real MV06
  summary status instead of hard-coding it as blocked.
- Reran the full-method gate. Current gate status remains
  `blocked_but_publishable_diagnostic_direction`; RQ4 is now
  `allowed_limited`, but full method remains blocked.
- Added latest-tree public dataset-table mitigation:
  - real `datasets/manifests/*_subjects.csv` and `*_subjects.parquet` are
    ignored and staged for removal from Git index while remaining local;
  - real `datasets/audit/file_integrity.csv` and
    `datasets/splits/phase2_subject_splits.csv` are local-only and staged for
    removal from Git index while remaining local;
  - added `datasets/schemas/subject_manifest_schema.csv`;
  - added `datasets/schemas/file_integrity_schema.csv`;
  - added `datasets/schemas/subject_split_schema.csv`;
  - added `datasets/examples/synthetic_subject_manifest.csv`;
  - added `datasets/examples/synthetic_file_integrity.csv`;
  - added `datasets/examples/synthetic_subject_splits.csv`;
  - added `datasets/manifests/.gitkeep`.

## Key Decisions

- Cross-dataset MV06 evidence claims must use dataset-stratified agreement, not
  only pooled kappa.
- MV06 first-round evidence can support only bounded aggregate credibility
  claims. After the second import, stronger RQ4 claims should add
  uncertainty/alpha-style agreement and resolve the remaining incomplete local
  candidate if needed.
- Full method remains blocked despite MV06 passing because RQ1 direct shared
  symptom mapping remains unsupported and public data-governance risk must be
  reduced.
- RQ1 should pivot from fixed direct shared-symptom mapping to partial
  measurement invariance: shared latent constructs plus scale-specific
  DIF/loading-threshold deviations.
- Do not continue small shallow BGE/WavLM head variants unless the measurement
  contract changes.
- Latest-tree removal of real row-level dataset tables is allowed; remote
  history rewrite or force-push requires explicit user approval.

## Files Owned Or Touched

- `scripts/phase5_summarize_mv06_evidence_annotations.py`
- `scripts/phase5_full_method_gate_audit.py`
- `.gitignore`
- `README.md`
- `datasets/README.md`
- `datasets/schemas/subject_manifest_schema.csv`
- `datasets/schemas/file_integrity_schema.csv`
- `datasets/schemas/subject_split_schema.csv`
- `datasets/examples/synthetic_subject_manifest.csv`
- `datasets/examples/synthetic_file_integrity.csv`
- `datasets/examples/synthetic_subject_splits.csv`
- `datasets/manifests/.gitkeep`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `MEMORY.md`
- `docs/experiment_direction.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_17_phase5_mv06_evidence_annotation_summary_gate.md`
- `memory/sessions/session_22_phase5_full_method_gate_audit.md`
- `memory/sessions/session_30_phase5_mv06_human_review_pack.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_31_phase5_mv06_annotation_and_governance_reframe.md`

## Generated Artifacts

Regeneration commands:

```bash
python scripts/phase5_summarize_mv06_evidence_annotations.py
python scripts/phase5_prepare_mv06_human_review_pack.py --overwrite
python scripts/phase5_full_method_gate_audit.py
```

Versionable outputs:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/agreement_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_summary/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv06_human_review_pack/*` tracked aggregate/schema files only
- `analysis/phase5_minimal_validation/full_method_gate_audit/*` tracked gate outputs

Ignored local-only inputs/artifacts:

- filled MV06 human workbook and its backup under
  `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_workbench/`;
- MV06 local review pack/candidate index predictions CSVs;
- real row-level subject manifests under `datasets/manifests/`;
- real row-level file-integrity and subject split tables under
  `datasets/audit/` and `datasets/splits/`.

## Blockers And Risks

- Public remote history still contains older row-level dataset-table commits
  unless the user explicitly approves a history rewrite or repository
  recreation.
- Historical first-pass E-DAIC MV06 agreement was underpowered, but current
  counts are superseded by session 48.
- The partial-invariance method target still needs a concrete protocol row and
  implementation plan.

## Next Handoff

Finish latest-tree dataset-table governance and publish through the clean
GitHub workflow. Then design the next Phase 5 row around partial measurement
invariance over E-DAIC/CMDC/PDCH. Ask before any force-push or remote history
rewrite.
