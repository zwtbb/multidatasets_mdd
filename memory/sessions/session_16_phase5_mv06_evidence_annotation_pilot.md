# Session Memory: Phase 5 MV06 Evidence Annotation Pilot

Status: complete
Last updated: 2026-08-09 UTC
Thread/task: main agent MV06 annotation pilot

## Scope

This session prepares a bounded local-only manual annotation packet for RQ4
evidence localization. It samples from the MV06 readiness candidate queue and
writes only aggregate sampling and hygiene summaries to versionable artifacts.
It does not train a model, read raw clinical text, write raw snippets, or
commit subject-level review rows.

## Current State

- Implemented `scripts/phase5_run_mv06_evidence_annotation_pilot.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/`.
- The script sampled 144 candidate rows from 1157 local MV06 candidates.
- The pilot covers 60 dataset-qualified subjects across E-DAIC, CMDC, and
  PDCH.
- All 144 selected rows have existing local text available through the local
  manifest-derived locator map.
- Twelve C09/HAMD03 rows are marked explicit-evidence-only.
- Artifact hygiene passed. Tracked artifacts contain no raw snippets, no local
  source locators, and no subject-level candidate rows.

## Key Decisions

- Treat this as `ready_for_manual_local_annotation`, not as evidence results.
- The local packet can support manual review and double-annotation planning,
  but RQ4 claims remain blocked until annotations are completed locally and
  summarized only as aggregate evidence agreement, prompt-artifact rates,
  evidence-source distributions, and construct coverage.
- C09/HAMD03 rows must rely only on explicit scale or explicit clinical-text
  evidence and should be reported separately or excluded from weak evidence
  claims.
- Local subject-level annotation files are ignored by Git because their names
  include `predictions`.

## Files Owned Or Touched

- `scripts/phase5_run_mv06_evidence_annotation_pilot.py`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/`
- `MEMORY.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_16_phase5_mv06_evidence_annotation_pilot.md`
- `memory/sessions/session_master_orchestration.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv06_evidence_annotation_pilot.py
```

Versionable artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/report.md`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/annotation_field_template.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/sampling_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/construct_sampling_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/dataset_bucket_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/text_access_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/local_artifact_manifest.csv`

Local-only ignored artifacts:

- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/p5_mv06_local_annotation_packet_predictions.csv`
- `analysis/phase5_minimal_validation/p5_mv06_evidence_annotation_pilot/p5_mv06_local_annotation_source_map_predictions.csv`

## Blockers And Risks

- No human annotation or double-annotation agreement audit has been completed.
- The local packet contains subject-level prediction candidates and must remain
  local-only.
- The local source locator map contains local file locators and must remain
  local-only.
- Evidence-localization validity claims remain blocked until annotation outputs
  are aggregated and re-checked for artifact hygiene.

## Next Handoff

Annotate the local packet manually or with a separately audited local workflow,
then create a new aggregate-only MV06 evidence annotation summary. That future
summary should report evidence presence, evidence source, prompt-artifact rate,
construct coverage, annotator agreement or audit agreement, and
safety-sensitive C09/HAMD03 handling without exporting raw text, local locators,
or subject-level rationales.
