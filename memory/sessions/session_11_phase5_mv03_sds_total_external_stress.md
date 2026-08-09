# Session Memory: Phase 5 P5_MV03 SDS Total External Stress

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: main agent Phase 5 P5_MV03

## Scope

This session owns `P5_MV03 sds_total_external_stress`, the SDS total/severity
external stress row on EATD-Corpus. It tests whether shallow SDS total heads on
existing frozen audio features generalize to validation subjects and whether
positive/neutral/negative material drives predictions. It does not use SDS
item-level labels, train a full method, fine-tune encoders, scan raw audio, or
write cached feature matrices into the output directory.

## Current State

- Implemented and ran `scripts/phase5_run_mv03_sds_total_external_stress.py`.
- Generated
  `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/`.
- The run completed with `status=complete`, `artifact_hygiene_passed=true`,
  and zero subject-overlap violations.
- EATD official train/validation split was used:
  - train subjects: `83`;
  - validation subjects: `79`;
  - valences: positive, neutral, negative.
- Feature inputs were existing cached Phase 2 audio features:
  - frozen WavLM valence segment features, 768 columns;
  - eGeMAPS valence segment features, 88 columns.
- Models compared:
  - `train_mean_sds_total`;
  - `egemaps_valence_segment_svr`;
  - `wavlm_valence_segment_ridge`;
  - `wavlm_subject_mean_ridge`.
- Best all-valence validation MAE was `7.341` from
  `egemaps_valence_segment_svr`, which is worse than the train-mean floor
  (`7.201`; delta `+0.140`).
- No stronger healthy-negative shortcut than Phase 3 was observed for the best
  model:
  - best-model healthy negative minus nonnegative SDS prediction: `-0.186`;
  - Phase 3 healthy negative minus nonnegative reference: `-0.061`;
  - `stronger_negative_shortcut_than_phase3=false`.
- P5_MV03 pass-rule status is `blocked_no_sds_generalization`.

## Key Decisions

- Treat EATD SDS total external stress as a runnable negative result: current
  frozen audio features do not beat a train-mean SDS total floor.
- Do not claim SDS item-level construct supervision from EATD.
- Do not add a valence-adversarial method component solely from this result;
  the negative-valence shortcut check remains weak/negative.
- Keep full method construction blocked. This row broadens evidence beyond
  E-DAIC/CMDC identity controls but does not supply positive external SDS
  generalization.

## Files Owned Or Touched

- `scripts/phase5_run_mv03_sds_total_external_stress.py`
- `memory/sessions/session_11_phase5_mv03_sds_total_external_stress.md`
- `MEMORY.md`
- `docs/master_experiment_plan.md`
- `docs/experiment_issue_log.md`
- `memory/sessions/session_master_orchestration.md`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/report.md`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/artifact_hygiene_audit.json`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/metric_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/metrics_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/comparison_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/valence_gap_by_seed.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/valence_gap_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/healthy_negative_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/phase3_valence_reference.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/model_split_audit.csv`
- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/feature_availability.csv`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv03_sds_total_external_stress.py
```

Versionable/import-suitable files:

- `scripts/phase5_run_mv03_sds_total_external_stress.py`
- `memory/sessions/session_11_phase5_mv03_sds_total_external_stress.md`
- all non-local-only files under
  `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/`.

Local-only/ignored files:

- `analysis/phase5_minimal_validation/p5_mv03_sds_total_external_stress/p5_mv03_local_predictions.csv`

## Blockers And Risks

- SDS external generalization is blocked for current frozen audio features:
  no tested shallow SDS total head beats train mean.
- EATD still has only SDS total/severity in the manifest, not SDS item labels,
  so it cannot validate item-level SDS construct heads.
- This row does not test text features or richer cross-scale representations.
  If SDS external validation is needed later, a text/semantic feature contract
  should be explicitly specified and audited.

## Next Handoff

Continue Phase 5 with MPDD context calibration (`P5_MV05`), stronger
inference-compatible identity/protocol controls, or a documented text-feature
variant for EATD SDS total. Full method work should remain blocked until at
least one broader minimal-validation row gives positive, controlled evidence.
