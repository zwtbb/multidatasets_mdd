# Session Memory: Phase 3 Dataset/Protocol Identity Probe

Status: complete
Last updated: 2026-08-04 UTC
Thread/task: Phase 3 diagnostic sub-session for dataset/protocol identity probes

## Scope

This session owns Phase 3 diagnostics that estimate how much dataset, protocol,
task, and valence identity is retained in existing frozen or lightweight
subject-level representations. It writes code, reports, and generated artifacts
only under the current worktree.

Out of scope:

- No changes to the Phase 2 baseline matrix.
- No raw text, audio, video, or raw path extraction.
- No final method design before the diagnostic evidence is recorded.

Canonical experiment order is a hard constraint for this task:
data audit -> task/hypothesis freeze -> unified baselines -> failure-mode
diagnostics -> minimal method validation -> full method -> cross-dataset
experiments -> statistics/writing. This session is only the Phase 3
failure-mode diagnostic step.

## Current State

- Master memory, Phase 1/2 session memory, and the session-memory template were
  read at session start.
- The task was corrected to use the current worktree for code, reports, and
  session memory. Existing Phase 2 feature caches under the main checkout may
  be used only as read-only inputs when the current worktree has no local cache
  copy.
- Mainline synchronization confirmed the canonical order above. This session
  must not implement a full model or method module.
- Implemented `scripts/phase3_dataset_identity_probe.py` and generated a small,
  reproducible report bundle under
  `analysis/phase3_diagnostics/dataset_identity_probe/`.
- Seven grouped CV probes completed with zero skipped probes and zero train/test
  group-overlap violations.
- No raw modality files were opened; outputs were checked for raw modality path,
  prompt, response, and transcript markers.

## Key Decisions

- Use read-only Phase 2 feature caches as probe inputs instead of regenerating
  embeddings or reading raw modalities.
- Use fixed balanced logistic regression with imputation/scaling inside each
  fold, reporting accuracy, macro-F1, balanced accuracy, grouped bootstrap 95%
  CIs, and confusion matrices.
- Treat only same-feature-space comparisons as interpretable:
  six-dataset WavLM audio, three-dataset wav2vec2 audio, CMDC/PDCH/MODMA
  eGeMAPS audio, CMDC/PDCH BGE text, and E-DAIC/CMDC semantic OpenFace video.
- Stop/Go: direct pooled training is not sufficient evidence of a shared
  depression representation. Minimal method validation may proceed only if it
  explicitly controls, penalizes, stratifies, or reports dataset/protocol
  identity effects.

## Files Owned Or Touched

- `memory/sessions/session_05_phase3_dataset_identity_probe.md`
- `scripts/phase3_dataset_identity_probe.py`
- `analysis/phase3_diagnostics/dataset_identity_probe/`

## Generated Artifacts

- Regeneration command:

```bash
python scripts/phase3_dataset_identity_probe.py
```

- Main report:
  `analysis/phase3_diagnostics/dataset_identity_probe/dataset_identity_probe_report.md`
- Metric table:
  `analysis/phase3_diagnostics/dataset_identity_probe/probe_metric_summary.csv`
- Local-only out-of-fold predictions:
  `analysis/phase3_diagnostics/dataset_identity_probe/probe_predictions.csv`
- Long-form confusion matrices:
  `analysis/phase3_diagnostics/dataset_identity_probe/confusion_matrices_long.csv`
- Inventory/run metadata:
  `analysis/phase3_diagnostics/dataset_identity_probe/feature_probe_inventory.csv`
  and `analysis/phase3_diagnostics/dataset_identity_probe/run_summary.json`
- Figures:
  `analysis/phase3_diagnostics/dataset_identity_probe/figures/`

Headline results:

- Dataset identity is almost perfectly recoverable from frozen/audio-lightweight
  features: WavLM six-way balanced accuracy 0.990, wav2vec2 three-way 0.994,
  CMDC/PDCH/MODMA eGeMAPS 0.989, CMDC/PDCH BGE text 1.000, and E-DAIC/CMDC
  OpenFace 1.000.
- Within-dataset protocol identity is also visible: MODMA WavLM task-type
  balanced accuracy 0.841; EATD WavLM valence balanced accuracy 0.553.

## Blockers And Risks

- Some modality/dataset combinations are not comparable because Phase 2 cached
  different encoders or feature spaces by dataset.
- E-DAIC text uses English DeBERTa/ModernBERT caches and cannot be pooled with
  CMDC/PDCH BGE text; EATD/MODMA/MPDD have no cached subject-level frozen text
  embeddings from Phase 2.
- E-DAIC eGeMAPS, EATD valence-expanded eGeMAPS, CMDC/PDCH/MODMA eGeMAPS, and
  MPDD no-eGeMAPS availability are not one common six-dataset eGeMAPS feature
  space.
- MPDD OpenFace is numeric-indexed and not safely joinable to E-DAIC/CMDC
  semantic OpenFace columns.

## Next Handoff

- Use these diagnostics as a Phase 3 Stop/Go gate before minimal method
  validation. Later method validation should include protocol/dataset identity
  controls or penalties and should report this diagnostic risk explicitly.
