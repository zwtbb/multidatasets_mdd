# Session Memory: 第1&2阶段 Research Frame And Unified Baselines

Status: complete for Phase 1 and applicable Phase 2 rows
Last updated: 2026-08-04 UTC
Thread/task: `第1&2阶段` (`019f9dcf-18ba-7c90-b04a-012e26dd7148`)

## Scope

This session froze the Phase 1 paper frame and implemented the Phase 2 unified
baseline matrix. It should not be used as permission to start full method
design before Phase 3 diagnostics.

## Phase 1 Decisions

- RQ1: shared symptom constructs across PHQ-8, PHQ-9, HAMD-17, and SDS.
- RQ2: protocol/task shortcut dependence versus participant symptom evidence.
- RQ3: individual-difference moderation by age, personality, health, and gait.
- RQ4: evidence localization as a credibility layer.
- The paper should not be framed as "one new fusion model over many datasets."
  The stronger frame is symptom evidence, protocol robustness, and moderated
  behavioral expression.

## Phase 2 Completion State

Source of truth:

- `/root/autodl-tmp/analysis/phase2_baselines/baseline_matrix_status.csv`
- `/root/autodl-tmp/analysis/phase2_baselines/final_table/phase2_final_baseline_table.csv`
- `/root/autodl-tmp/analysis/phase2_baselines/final_table/phase2_final_baseline_table_audit.csv`
- `/root/autodl-tmp/analysis/phase2_baselines/phase2_completion_audit/phase2_completion_audit.md`

Current gate:

- Planned runs: 67.
- Completed runs: 66.
- Not applicable: 1 (`mpdd_public_p3hf`).
- Blocked runs: 0.
- Completed metric rows: 313/318.
- Not-applicable metric rows: 5/318.
- Phase 2 completion audit verdict: `phase2_goal_complete=true`.
- Method-design gate recommendation: `ready`.
- Artifact hygiene audit verdict: `artifact_hygiene_passed=true`.
- Hygiene audit scope: 66 completed runs, 313 completed metric rows, 1565
  seed-metric rows, 39 canonical prediction files, and 33913 canonical
  prediction rows; failed completed runs = 0 and prediction files with raw/path
  leakage indicators = 0.

Completed families:

- E-DAIC: text TF-IDF, frozen/simple text encoders, sentence attention,
  audio eGeMAPS, frozen audio encoders, video features, A/V/T fusion, existing
  local baselines, AVEC official, QuestMF.
- CMDC: text TF-IDF, frozen text encoder, audio eGeMAPS, frozen audio
  encoders, video features, binary audio/text fusion, HAMD-17 audio/text fusion.
- PDCH: text TF-IDF, frozen text encoder, audio eGeMAPS, frozen WavLM,
  audio/text late fusion, official text-only, official audio-text.
- EATD-Corpus: text TF-IDF, audio eGeMAPS, frozen WavLM, audio/text fusion,
  public GRU/BiLSTM-style reproduction with audited-feature adaptation.
- MODMA: eGeMAPS, WavLM, wav2vec2, task-specific and cross-task WavLM rows.
- MPDD-AVG-2026: gait statistics, IMU temporal encoder, WavLM audio, ResNet
  video, OpenFace video, AVP early/late/gated fusion, official MPDD baseline.

## Important Baseline Caveats

- P3HF is conditionally excluded from the canonical Phase 2 matrix. Its
  packaged 110-Young split/features/dev+test evaluation contract does not
  match the current 175-subject MPDD Phase 2 protocol. ID coverage is not the
  problem; protocol compatibility is.
- MPDD OpenFace was synchronized from the local audited MPDD project and is now
  complete on the server: 756 `.npy` files, 4,332,161,768 bytes, 0 zero-byte
  files. The Phase 2 baseline used 175 labeled train subjects and 602 video
  events.
- MPDD Young OpenFace uses nested `subject/event_*/*.npy` layout; the runner was
  fixed to recursively read all events before the final OpenFace results were
  accepted.
- AVEC/E-DAIC subject `657` is missing a VGG feature file in the official
  release. The AVEC wrapper treats this as a known official omission and does
  not fabricate it.
- PDCH official audio-text Qwen2-Audio is weak: parsing all 17 HAMD factors
  succeeded for only 46/99 subjects; missing-factor scoring pushes predictions
  high.
- PDCH public LLM runners now separate public `model_name` from local
  `--model-load-path`. The canonical factor-prediction artifacts store public
  model IDs (`Qwen/Qwen2.5-7B-Instruct` and
  `Qwen/Qwen2-Audio-7B-Instruct`) rather than local ModelScope cache paths.
- CMDC WavLM/audio and official visual scores are very high and should be
  treated as shortcut-risk signals until RQ2 controls are run.

## Verification Commands

```bash
python /root/autodl-tmp/scripts/phase2_build_subject_splits.py
python /root/autodl-tmp/scripts/phase2_baseline_matrix.py --strict
python /root/autodl-tmp/scripts/phase2_export_final_table.py
python /root/autodl-tmp/scripts/phase2_completion_audit.py
python /root/autodl-tmp/scripts/phase2_artifact_hygiene_audit.py
python /root/autodl-tmp/scripts/phase2_metrics.py --self-test
```

## Files Owned Or Touched

Baseline config:

- `/root/autodl-tmp/baselines/phase2_baseline_matrix.yaml`

Core scripts:

- `/root/autodl-tmp/scripts/phase2_build_subject_splits.py`
- `/root/autodl-tmp/scripts/phase2_baseline_matrix.py`
- `/root/autodl-tmp/scripts/phase2_metrics.py`
- `/root/autodl-tmp/scripts/phase2_export_final_table.py`
- `/root/autodl-tmp/scripts/phase2_completion_audit.py`
- `/root/autodl-tmp/scripts/phase2_artifact_hygiene_audit.py`
- `/root/autodl-tmp/scripts/phase2_run_*.py`

Docs and reports:

- `/root/autodl-tmp/docs/phase2_unified_baseline_protocol.md`
- `/root/autodl-tmp/docs/reproduction_zh.md`
- `/root/autodl-tmp/analysis/phase2_baselines/`

## Next Handoff

Proceed to Phase 3 diagnostics. Do not design the final symptom-aligned model
until diagnostic evidence shows which failure modes are empirically real.
