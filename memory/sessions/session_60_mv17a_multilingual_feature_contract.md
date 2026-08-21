# Session Memory: MV17a Multilingual Feature Contract

Status: complete
Last updated: 2026-08-21 UTC
Thread/task: Continue implementing post-review modification document; run MV17a

## Scope

This session owns the MV17a feature-contract sensitivity requested after the
post-review route: regenerate E-DAIC/CMDC/PDCH subject-level text features with
two multilingual encoders and rerun only MV07, MV12, and MV15. It does not
rerun MV16, start full M0/M1/M2/M3 work, or broaden claims beyond the current
full-method gate.

## Current State

MV17a is complete at
`analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/`.

Feature generation:

- `bge_m3`: `BAAI/bge-m3`, CLS pooling, 512-token chunk contract, 1024 feature
  columns.
- `multilingual_e5_base`: `intfloat/multilingual-e5-base`, average pooling,
  `query: ` prefix, 512-token chunk contract, 768 feature columns.
- Both encoders cover E-DAIC 219 subjects, CMDC 77 subjects from 908 text
  segments, and PDCH 99 subjects from 165 text segments.
- Feature caches are local-only under
  `analysis/phase2_baselines/mv17_multilingual_text_features/`.

Downstream result summary:

- BGE-M3 MV07: `blocked_not_better_than_total_allocation_bge_contract`;
  feature identity BA `1.000`, prediction identity BA `0.932`.
- BGE-M3 MV12: `blocked_theta_gain_not_observed_scale_safe`.
- BGE-M3 MV15: `blocked_theta_conditioned_feature_identity_high`; theta,
  total, predicted-total, and B3-conditioned feature identity BA all `1.000`.
- multilingual-E5 MV07:
  `blocked_not_better_than_total_allocation_bge_contract`; feature identity BA
  `1.000`, prediction identity BA `0.993`.
- multilingual-E5 MV12: `blocked_theta_gain_not_observed_scale_safe`.
- multilingual-E5 MV15: `blocked_theta_conditioned_feature_identity_high`;
  theta, total, predicted-total, and B3-conditioned feature identity BA all
  `1.000`.

Top-level and downstream artifact hygiene audits passed. Row-level predictions
and feature caches remain ignored/local-only.

## Key Decisions

- The legacy Chinese-BGE caveat has been addressed by sensitivity analysis
  rather than by editing old baseline outputs.
- The feature-column prefix remains `bge_` only for compatibility with existing
  MV07/MV12/MV15 loaders; `encoder_contract.csv` records the true model,
  pooling, prefix, max length, and dimensionality.
- MV16 remains paused. MV17a already tests the paper-critical feature-level
  chain requested by the post-review document; rerunning MV16 should require a
  new explicit need.

## Files Owned Or Touched

Versionable files created or edited by this session:

- `scripts/phase5_run_mv17a_multilingual_feature_contract.py`
- `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/`
- `memory/sessions/session_60_mv17a_multilingual_feature_contract.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`
- `docs/experiment_issue_log.md`

No `.gitignore` change remains from this session; the attempted overbroad
`local_*` ignore was removed because it would have hidden
`local_artifact_manifest.csv`.

## Generated Artifacts

Primary regeneration command after model caches are present:

```bash
HF_HUB_DISABLE_XET=1 HF_HUB_ENABLE_HF_TRANSFER=1 HF_HUB_DOWNLOAD_TIMEOUT=600 HF_HUB_ETAG_TIMEOUT=60 python scripts/phase5_run_mv17a_multilingual_feature_contract.py
```

If model files are missing, first allow or pre-run downloads:

```bash
HF_HUB_DISABLE_XET=1 HF_HUB_ENABLE_HF_TRANSFER=1 HF_HUB_DOWNLOAD_TIMEOUT=600 HF_HUB_ETAG_TIMEOUT=60 python scripts/phase5_run_mv17a_multilingual_feature_contract.py --allow-download
```

Tracked aggregate outputs:

- `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/report.md`
- `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/run_summary.json`
- `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/encoder_contract.csv`
- `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/feature_generation_summary.csv`
- `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/downstream_run_summary.csv`
- Encoder-specific downstream MV07/MV12/MV15 aggregate folders under
  `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/downstream/`.

Local-only outputs:

- `analysis/phase2_baselines/mv17_multilingual_text_features/`
- `p5_mv07_local_predictions.csv` and `p5_mv12_local_predictions.csv` under the
  MV17a downstream folders.

## Blockers And Risks

- BGE-M3 and multilingual-E5 downloads required large Hugging Face files. The
  direct `AutoModel` path timed out once; using `hf download` with
  `HF_HUB_DOWNLOAD_TIMEOUT=600` completed both caches.
- E-DAIC transcript CSVs still lack speaker-role columns; MV17a does not fix
  participant/interviewer filtering.
- MV17a used a 512-token chunk contract for both encoders for parity with the
  existing MV07/MV12/MV15 interface and E5's model limit. BGE-M3 officially
  supports longer contexts, but this session did not run a long-context
  BGE-M3-only sensitivity.

## Next Handoff

Next research step: predeclare and run MV18 CMDC-HAMD vs PDCH-HAMD same-scale
exploratory control. After MV18, run MV19 finite-sample PHQ psychometric
simulation if the manuscript still needs a small-sample uncertainty support
layer. Keep full-method construction blocked unless a new gate audit changes
the decision.
