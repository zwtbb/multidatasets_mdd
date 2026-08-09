# Session Memory: Phase 3 Protocol Diagnostics

Status: complete
Last updated: 2026-08-05 UTC
Thread/task: Phase 3 E-DAIC/CMDC protocol-control diagnostics

## Scope

This session owns Phase 3 protocol and interviewer/prompt shortcut diagnostics
for E-DAIC and CMDC. It stays inside the failure-mode diagnostic stage and does
not implement method modules or full shared-symptom models.

## Current State

- Implemented `scripts/phase3_protocol_controls.py`.
- Generated protocol diagnostic outputs under
  `analysis/phase3_diagnostics/protocol_controls/`.
- Default bootstrap resamples were reduced from 1000 to 200 after the first run
  showed the bottleneck was bootstrap CI computation. Coverage stayed the same;
  the script exposes `--bootstrap-resamples 1000` for tighter CIs if needed.
- Completed 60 model/control runs over 5 seeds, producing 284 metric-summary
  rows and 1420 metric-by-seed rows.
- Subject overlap violations: 0.
- `artifact_hygiene_summary.json` reports no raw text, raw prompt text, or
  source paths written.

## Completed Controls

- E-DAIC:
  full available transcript, front 25%, middle 50%, back 25%, train
  repeated-turn removal, and train repeated-turn-only fixed-protocol proxy.
- CMDC:
  all questions, Q1-Q12 individual question-position probes, and Q1-Q4, Q5-Q8,
  Q9-Q12 question-block probes for binary, PHQ-9, and HAMD-17 targets where
  the split/labels support them.

## Key Findings

- E-DAIC participant-only and interviewer-only controls are blocked by missing
  speaker identity: manifest speaker values are empty and transcript headers
  expose only `Start_Time`, `End_Time`, `Text`, and `Confidence`.
- E-DAIC binary full-dialogue Macro-F1 is 0.440. Front-25% control reaches
  0.549, and train repeated-turn-only proxy reaches 0.621, suggesting strong
  position/fixed-protocol shortcut risk even without speaker labels.
- E-DAIC PHQ-8 total MAE changes little under position controls: full dialogue
  4.745, middle 50% 4.714, back 25% 4.774.
- CMDC binary all-question Macro-F1 is 0.850. Single question probes vary
  sharply: Q1 0.742, Q6 0.527, Q10 0.476, Q12 0.618. This supports a
  question-position/task-content dependence risk.
- CMDC PHQ-9 and HAMD-17 text position controls also vary, but HAMD-17 has only
  25 labeled subjects and should be interpreted cautiously.

## Files Owned Or Touched

- `scripts/phase3_protocol_controls.py`
- `analysis/phase3_diagnostics/protocol_controls/`
- `memory/sessions/session_02_phase3_protocol_diagnostics.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase3_protocol_controls.py
```

Tracked lightweight artifacts:

- `analysis/phase3_diagnostics/protocol_controls/protocol_controls_report.md`
- `analysis/phase3_diagnostics/protocol_controls/protocol_controls_run_summary.json`
- `analysis/phase3_diagnostics/protocol_controls/artifact_hygiene_summary.json`
- `analysis/phase3_diagnostics/protocol_controls/protocol_control_metric_deltas.csv`
- `analysis/phase3_diagnostics/protocol_controls/protocol_feasibility_audit.csv`
- `analysis/phase3_diagnostics/protocol_controls/dataset_slice_summary.csv`
- `analysis/phase3_diagnostics/protocol_controls/protocol_model_status.csv`
- `analysis/phase3_diagnostics/protocol_controls/phase3_metric_summary.csv`
- `analysis/phase3_diagnostics/protocol_controls/phase3_metrics_by_seed.csv`

Local-only artifact:

- `analysis/phase3_diagnostics/protocol_controls/protocol_control_predictions.csv`
  has 17680 rows and is ignored by default as row-level prediction output.

## Blockers And Risks

- Speaker-resolved E-DAIC interviewer-only/participant-only controls need a
  transcript source with speaker labels or a new transcript-alignment route.
- CMDC interviewer/prompt-only controls need populated speaker/prompt fields or
  a separate protocol prompt source.
- E-DAIC repeated-turn-only is a proxy, not a literal interviewer-only control.

## Next Handoff

Use this diagnostic together with the dataset-identity probe when making the
Phase 3 Stop/Go decision. Current evidence supports protocol robustness as a
required consideration, but exact mechanism design should wait for MODMA/EATD
and MPDD diagnostics.
