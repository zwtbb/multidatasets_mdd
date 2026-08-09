# Phase 5 Minimal Method-Validation Protocol

Generated: `2026-08-09T09:08:46+00:00`

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
- `P5_MV06` `construct_evidence_localization` (summary_gate_blocked_no_completed_annotations): post-hoc evidence audit tied to construct predictions and protocol controls
- `P5_MV07` `aligned_bge_shared_symptom_validation` (complete_blocked_aligned_bge_identity_total_allocation): train-mean, total-allocation Ridge, and BGE itemwise Ridge with feature and prediction identity probes

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

`P5_MV01`, `P5_MV02`, `P5_MV03`, `P5_MV04`, `P5_MV05`, and `P5_MV07` have now run. `P5_MV04` now has mixed control evidence: E-DAIC/CMDC known-dataset centering passed diagnostically, source-agnostic projection remains partial, MODMA task nuisance projection passes, and EATD valence control is blocked because the SDS main task stays below train mean. `P5_MV06` has a local annotation workbench and aggregate summary gate, but evidence reporting is blocked until annotations are completed. `P5_MV07` aligned-BGE shallow validation is blocked because BGE itemwise heads do not beat the total-allocation floor consistently and identity probes remain high. Full method work remains blocked until stronger cross-dataset/control evidence is accumulated.
