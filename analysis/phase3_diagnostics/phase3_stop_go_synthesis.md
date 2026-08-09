# Phase 3 Failure-Mode Stop/Go Synthesis

Last updated: 2026-08-05 UTC

## Scope

This synthesis closes the planned Phase 3 failure-mode diagnostics before any
minimal method validation or full method construction. It summarizes only
diagnostic evidence and implementation gates. Numeric source of truth remains
the generated files under `analysis/phase3_diagnostics/`.

## Evidence Sources

- Dataset/protocol identity:
  `analysis/phase3_diagnostics/dataset_identity_probe/dataset_identity_probe_report.md`
- E-DAIC/CMDC protocol controls:
  `analysis/phase3_diagnostics/protocol_controls/protocol_controls_report.md`
- MODMA/EATD task-valence diagnostics:
  `analysis/phase3_diagnostics/task_valence/phase3_task_valence_report.md`
- MPDD individual-difference diagnostics:
  `analysis/phase3_diagnostics/mpdd_individual_differences/mpdd_individual_differences_report.md`

## Gate Decision

Phase 3 provides enough evidence to proceed to Phase 4 symptom ontology and a
minimal method-validation design. It does not justify jumping directly to a
full model. The next method plan must include explicit controls for dataset,
protocol/task, and subgroup/calibration effects.

## Go Signals

- Dataset/protocol robustness is required. Dataset identity is nearly perfectly
  recoverable from frozen representations: WavLM six-way balanced accuracy
  `0.990`, CMDC/PDCH BGE text `1.000`, and E-DAIC/CMDC OpenFace `1.000`.
- Protocol/task-content controls are required. E-DAIC fixed-position proxies
  and CMDC question-position probes show meaningful shortcut risk; CMDC Q10
  binary Macro-F1 drops by `0.374` versus all questions.
- Task-stratified validation is required. MODMA overall cross-task Balanced
  Accuracy drops by `0.099`, with the clearest signal for affective-task
  evaluation: Balanced Accuracy drop `0.142`, CI `0.003` to `0.280`.
- Personality/moderation diagnostics should continue. MPDD personality-only
  TF-IDF beats shuffled personality by Macro-F1 `+0.116` and QWK `+0.272`, and
  age-swap counterfactuals change many predictions.
- Subgroup calibration auditing should continue. MPDD age ECE gap reaches
  `0.132`, personality-bin ECE gap reaches `0.289`, and true-severity subgroup
  gaps remain large.
- Gait can be used as psychomotor context validation. MPDD gait statistics have
  modest association with PHQ-9; the top absolute Spearman correlation is
  `0.269`.

## Stop Or Weak Signals

- Stop using direct pooled training as standalone evidence for shared symptom
  representation; dataset identity is too easy to recover.
- Stop treating generic MPDD audio-video-personality concatenation as a
  supported method component. AVP early fusion improves over AV by only
  Macro-F1 `+0.001` and QWK `+0.001`, and shuffling personality inside AVP does
  not hurt performance.
- Do not add a valence-adversarial component solely from EATD audio eGeMAPS.
  Healthy negative material does not inflate depressed-probability estimates in
  this diagnostic; healthy negative predicted-depressed rate is `0.118` versus
  `0.206` for healthy nonnegative material.
- Treat age as a subgroup/calibration axis, not a standalone predictive
  shortcut. MPDD age-only versus shuffled-age QWK delta is `-0.013`.

## Blocked Signals

- E-DAIC literal participant-only and interviewer-only controls remain blocked
  because transcript/manifest fields do not expose speaker identity.
- CMDC interviewer/prompt-only controls remain blocked by missing populated
  speaker/prompt fields; question-position controls are the available proxy.
- MPDD gender-only, health-only, and gender/health subgroup calibration are
  blocked because structured `gender` and `health_condition` manifest fields
  are empty.

## Requirements For Minimal Method Validation

- Preserve subject-level splits across all datasets and tasks.
- Report dataset-stratified, protocol/task-stratified, and subgroup/calibration
  metrics before any pooled performance claim.
- Include a dataset/protocol control or penalty only as a minimal validation
  component, with ablations showing whether it reduces shortcut reliance.
- Keep personality/context conditioning separate from naive feature
  concatenation; test whether it improves calibration or robustness rather than
  only point accuracy.
- Use gait as psychomotor context evidence, not as an automatically fused fourth
  modality.
- Keep EATD valence as a monitoring/stress-test axis unless a text/semantic
  diagnostic later reveals stronger valence confounding.

## Next Actions

1. Cross-scale symptom ontology and label mapping for PHQ-8, PHQ-9, HAMD-17,
   and SDS are drafted at
   `analysis/phase4_symptom_ontology/phase4_symptom_ontology_report.md`.
2. Specify the minimal method-validation experiment protocol with the above
   controls and ablations.
3. Rerun selected Phase 3 intervals with higher bootstrap counts only for
   figures/tables that will enter the manuscript.
4. Decide whether to seek structured MPDD gender/health metadata; otherwise
   keep those analyses explicitly blocked.
