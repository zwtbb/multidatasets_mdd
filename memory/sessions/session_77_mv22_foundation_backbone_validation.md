# Session Memory: session_77_mv22_foundation_backbone_validation

Status: complete
Last updated: 2026-08-24 UTC
Thread/task: MV22 foundation-backbone experiment reinforcement

## Scope

This session executes the user-approved foundation-backbone stress-test slice
for the measurement-aware framework. It does not start full M0/M1/M2/M3
construction, full WavLM Large/video foundation sensitivity, or end-to-end
multimodal fine-tuning.

## Current State

- MV22 is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv22_foundation_backbone_validation/`.
- The runner is
  `/root/autodl-tmp/scripts/phase5_run_mv22_foundation_backbone_validation.py`.
- Qwen3-Embedding-0.6B text features were generated locally for
  E-DAIC/CMDC/PDCH under ignored Phase 2 feature roots.
- MV07/MV12/MV15 were rerun on Qwen features and all preserve the blocked
  diagnostic pattern.
- The adaptation baseline suite includes ERM itemwise Ridge, CORAL itemwise
  Ridge, MMD/DAN-style mean alignment, DANN itemwise MLP, IRM severity proxy,
  GroupDRO severity proxy, and MV12 measurement-aware aggregate references.
- Existing WavLM base-plus subject features are used as an audio foundation
  proxy; WavLM Large is recorded as future compute scope.

## Key Decisions

- Use Qwen3-Embedding-0.6B as the practical strong text foundation slice rather
  than attempting all suggested LLM encoders.
- Treat WavLM base-plus as an audio foundation proxy for this slice; do not
  claim WavLM Large or video-foundation completion.
- Report MV22 as a target-validity stress test, not as SOTA depression
  detection or a solved full method.
- Keep Qwen feature caches, row predictions, learned parameters, and
  participant-level outputs local-only/ignored.

## Files Owned Or Touched

- `/root/autodl-tmp/scripts/phase5_run_mv22_foundation_backbone_validation.py`
- `/root/autodl-tmp/scripts/phase5_run_mv17a_multilingual_feature_contract.py`
- `/root/autodl-tmp/scripts/build_diagnostic_paper_claim_tables.py`
- `/root/autodl-tmp/scripts/phase5_consolidate_experiment_inventory.py`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`
- `/root/autodl-tmp/README.md`
- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`

## Generated Artifacts

- MV22 aggregate output:
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv22_foundation_backbone_validation/`
- Regenerate with:
  `python scripts/phase5_run_mv22_foundation_backbone_validation.py --allow-download --include-audio-proxy-baseline`
- Important aggregate files:
  `report.md`, `run_summary.json`, `downstream_metric_extract.csv`,
  `adaptation_summary.csv`, `measurement_aware_reference_summary.csv`, and
  `model_comparison_summary.csv`.

## Blockers And Risks

- WavLM Large, VideoMAE, and end-to-end multimodal trainable measurement heads
  are not executed in this slice.
- IRM and GroupDRO are severity-environment proxies because each PHQ transfer
  direction has a single source corpus.
- MV22 supports the foundation-era validity argument but does not allow a full
  cross-corpus depression detection success claim.

## Next Handoff

Use MV22 in the manuscript as a bounded foundation-backbone negative/stress
test: Qwen features still retain corpus identity, feature identity and
observed-scale safety gates remain visible, and measurement-aware references
improve Qwen shared-item reconstruction in both PHQ transfer directions.
