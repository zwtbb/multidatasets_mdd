# MV32 TCPS Method Contract

TCPS learns item-level target measurement residuals instead of forcing either a shared ordinal head or a fully corpus-specific ordinal head.

- Primary residual: threshold-only cumulative-logit residuals with proximal group-lasso; lambda `1.0`.
- PCA projection scope: `source_target_calibration`.
- Participant bootstrap draws per split: `200`.
- Lambda policy: the primary lambda is fixed before real-data interpretation; grid results are sensitivity only.
- Optional ablations: threshold+slope residuals and audit-weighted threshold residuals.
- Fair comparison: same frozen MV24 representation, same shared symptom layer size, same ordinal loss, same optimizer family, same target calibration split, and same target-label budget.
- The audit-weighted variant computes item penalty weights only from source labels and the current target calibration subset.
- Proper ordinal metrics are first-class outputs: held-out ordinal NLL and ranked probability score, alongside MAE and calibration.
- Targeted item error is reported for audit anchors and the C02/C06 threshold-shift candidates.
