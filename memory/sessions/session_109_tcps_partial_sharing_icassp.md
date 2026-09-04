# Session Memory: tcps_partial_sharing_icassp

Status: complete
Last updated: 2026-09-04 UTC
Thread/task: ICASSP 2027 TCPS partial-sharing algorithm execution

## Scope

This session owns the user-approved ICASSP-oriented upgrade from a pure
target-comparability audit toward a learnable measurement-sharing method:
Target-Contract Partial Sharing (TCPS). It does not add a generic Mamba, LLM,
or multimodal fusion block as the main novelty.

## Current State

- MV32 is implemented in
  `/root/autodl-tmp/scripts/phase5_run_mv32_tcps_partial_sharing.py`.
- The clean completed output directory is
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv32_tcps_partial_sharing/`.
- A first interrupted/transductive-PCA run was deleted as stale local residue
  because it used the old lambda/default feature-access contract and should
  not be used as evidence.
- The final clean run reuses the MV24 frozen Qwen3+WavLM+OpenFace
  subject-level feature contract and MV28 repeated target-calibration split
  contract.
- The final default PCA feature contract fits PCA on source subjects plus the
  target calibration subset only: `pca_fit_scope=source_target_calibration`.
  Evaluation target features are not used to fit the default PCA projection.

## Method Contract

- Main mechanism: sparse partially shared cumulative-logit ordinal measurement
  head with shared base item parameters plus target-corpus item-level threshold
  residuals.
- Primary row: `tcps_threshold` with proximal group-lasso and fixed
  `lambda_group=1.0`.
- Sensitivity grid: `0.0, 0.3, 1.0, 3.0, 10.0`; this is a reported
  regularization path, not a held-out-evaluation lambda search.
- Ablations: threshold+slope residuals and audit-weighted threshold residuals.
- Fair comparison rows include target-only direct MLP, target-only ordinal,
  direct source+target multitask, shared ordinal head, fully corpus-specific
  ordinal head, generic target MLP head, and TCPS variants under the same
  target calibration split.
- Uncertainty includes 30 repeated subject-level splits and 200 paired
  participant-bootstrap draws per split for model-difference wording.

## Generated Artifacts

Primary numeric sources:

- `run_summary.json`
- `go_no_go_recommendations.csv`
- `report.md`
- `real_data_main_table.md`
- `lambda_sensitivity_table.md`
- `participant_bootstrap_delta_table.md`
- `residual_support_table.md`
- `targeted_item_error_delta_table.md`
- `simulation_table.md`

All are under
`/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv32_tcps_partial_sharing/`.
The artifact hygiene audit passes and the output package is aggregate-only.

## Final Results

- Final gate:
  `borderline_audit_guided_algorithm_candidate`.
- Real-data split-level gate:
  `real_data_partial_support`; primary TCPS shows at least one lower-error
  ordinal/calibration comparison in 1 of 2 transfer directions.
- Participant bootstrap gate:
  `bootstrap_partial_not_interval_stable`; 0 stable interval-level comparisons
  and 1 partial comparison among 16 primary TCPS-vs-extreme comparisons.
- Fixed-latent simulation gate:
  `simulation_mechanism_supported`; under planted sparse `C02/C06` threshold
  DIF, TCPS support is higher for planted shift items than anchors
  (`0.5625` vs `0.4302` mean nonzero support), but the effect is modest.

Real-data reading:

- TCPS is competitive on Macro Item MAE but not a stable superiority result.
- Shared ordinal remains stronger on held-out ordinal NLL/RPS in these runs.
- Target-only direct MLP and generic target MLP remain strong Macro Item MAE
  comparators; the manuscript cannot claim TCPS uniformly beats calibrated
  non-ordinal heads.
- Audit-weighted TCPS gives the cleanest residual sparsity pattern and points
  strongly to `C06`, but `C02` is weak and `C01` anchor residuals can be
  nonzero. Do not claim exact real-data recovery of the C02/C06 audit set.
- Targeted item-error deltas for `C02/C06` are small and intervals cross zero;
  use them as suggestive alignment/trend evidence only.

## Claim Boundary

Allowed:

- TCPS can be presented as an audit-guided algorithmic instantiation of partial
  target-contract sharing.
- The method operationalizes the idea that cross-corpus depression transfer
  should learn/test which PHQ item thresholds remain shared and which require
  target-specific residuals.
- Simulation supports the intended mechanism under known measurement
  heterogeneity, with bounded strength.
- Real data supports competitiveness and mechanism diagnostics, not uniform
  predictive superiority.

Blocked:

- Stable real-data superiority over shared ordinal, fully corpus-specific
  ordinal, direct target-only, generic target MLP, or direct multitask baselines.
- Claims that corpus-specific measurement parameterization is the independent
  source of the earlier MV24 gains.
- Claims that C02/C06 item localization is confirmed robust DIF in real data.
- Lambda tuning claims based on held-out evaluation metrics.

## Verification

Commands already run successfully:

```bash
python -m py_compile scripts/phase5_run_mv32_tcps_partial_sharing.py
git diff --check
python scripts/phase5_run_mv32_tcps_partial_sharing.py --clean --device cpu --parallel-workers 12
```

The clean full run completed with:

```text
Wrote P5_MV32_tcps_partial_sharing to /root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv32_tcps_partial_sharing with hygiene=True
```

## Next Handoff

- Rewrite the ICASSP manuscript around TCPS only as a bounded
  audit-guided method candidate.
- Use the paper identity: target-comparability / measurement-contract audit
  plus a learnable partial-sharing ordinal instantiation.
- Do not add unrelated large fusion/backbone novelty unless a new experiment
  contract directly tests a reviewer-critical concern.
- If more evidence is needed, the most valuable next experiments are
  participant-only/question-excluded leakage sensitivity and optimization-
  exposure/count reporting, not another generic network block.
