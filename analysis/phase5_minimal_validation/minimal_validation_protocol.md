# Phase 5 Minimal Method-Validation Protocol

Generated: `2026-08-11T12:13:34+00:00`

## Purpose

This protocol freezes what must be validated before full method construction. It consumes the Phase 3 failure-mode synthesis and the Phase 4 symptom ontology. It does not train models.

## Gate

Minimal validation may begin only with subject-level splits, frozen or explicitly documented feature contracts, dataset/protocol/task/subgroup reporting, and artifact hygiene. Direct pooled-performance claims remain disallowed until identity and protocol controls pass.

## Experiment Rows

- `P5_MV01` `phq_core_construct_bridge` (complete_diagnostic_weak_asymmetric): shared construct heads plus PHQ-8/PHQ-9 scale-specific measurement heads
- `P5_MV02` `hamd17_auxiliary_bridge` (complete_pdch_only_diagnostic): shared core construct heads with HAMD-specific auxiliary heads
- `P5_MV03` `sds_total_external_stress` (complete_negative_sds_audio_text_stress): scale-specific SDS total/severity head attached only for external validation
- `P5_MV04` `dataset_protocol_control_ablation` (complete_mixed_dataset_protocol_control): baseline shared heads versus dataset-balanced, protocol-balanced, or adversarial identity-control variants
- `P5_MV05` `mpdd_context_calibration` (complete_negative_context_calibration): calibration/context module versus AV baseline and shuffled-personality controls
- `P5_MV06` `construct_evidence_localization` (complete_ready_limited_aggregate_evidence): post-hoc evidence audit tied to construct predictions and protocol controls
- `P5_MV07` `aligned_bge_shared_symptom_validation` (complete_blocked_aligned_bge_identity_total_allocation): train-mean, total-allocation Ridge, and BGE itemwise Ridge with feature and prediction identity probes
- `P5_MV08` `partial_invariance_measurement_design` (design_ready_partial_invariance): compare total-score floors, fixed construct-map heads, and partial-invariance ordinal latent measurement heads
- `P5_MV08b` `total_anchored_residual_measurement` (design_ready_total_anchored_residual): compare train-mean items, total-score floor, fixed construct-map floor, and total-anchored sparse residual item heads with pooled/collapsed threshold policy

## Mandatory Controls

- Dataset-stratified and protocol/task-stratified metrics before any pooled claim.
- Dataset/protocol identity probe for learned representations used in pooled or cross-dataset claims.
- Phase 2 total-score baselines as the comparator floor.
- MPDD age/personality subgroup calibration and shuffled/counterfactual controls for context claims.
- Explicit blocking of gender/health claims until structured MPDD metadata is available.
- Explicit-evidence-only handling for C09 death/self-harm.

## Output Files

- `experiment_matrix.csv`
- `metric_contract.csv`
- `output_policy.csv`
- `readiness_audit.json`

## Next Handoff

`P5_MV01`, `P5_MV02`, `P5_MV03`, `P5_MV04`, `P5_MV05`, and `P5_MV07` have now run. `P5_MV06` now has first-round aggregate evidence with dataset-stratified agreement, but E-DAIC agreement remains underpowered. `P5_MV07` aligned-BGE shallow validation is blocked because BGE itemwise heads do not beat the total-allocation floor consistently and identity probes remain high. `P5_MV08` is the next design-ready row: partial measurement invariance with ordinal latent measurement over E-DAIC, CMDC, and PDCH. Full method work remains blocked until MV08 or another genuinely changed measurement contract produces evidence.
