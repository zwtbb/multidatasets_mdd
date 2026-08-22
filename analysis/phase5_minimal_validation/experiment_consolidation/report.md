# Phase 5 Experiment Consolidation

Generated: 2026-08-22T11:27:16+00:00

## Decision

Do not physically delete tracked aggregate experiment outputs. They are small, versionable traceability records used by the full-method gate and manuscript claim boundary. Consolidate them by role instead:

- Paper core: label-only PHQ psychometric evidence (`MV10/MV11/MV13/MV14/MV19`).
- Paper support: bounded controls and negative consequences (`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20`).
- Retired historical: early weak or superseded minimal validations kept only as aggregate background.
- Predeclaration contracts: design/readiness artifacts retained to prove that later runs were predeclared.
- Local workflow: MV06 workbooks and feature-generation boundaries stay local-only; tracked outputs remain schemas/hygiene summaries.

## Counts

- `local_workflow`: 6
- `paper_core`: 5
- `paper_support`: 11
- `planning_route`: 1
- `predeclaration_contract`: 9
- `retired_historical`: 13

## Active Evidence Bundle

| Evidence ID | Merge bucket | Manuscript role |
| --- | --- | --- |
| `P5_MV10` | `phq_label_only_psychometrics` | main psychometric measurement-validity evidence |
| `P5_MV11` | `phq_label_only_psychometrics` | main psychometric measurement-validity evidence |
| `P5_MV13` | `phq_label_only_psychometrics` | main psychometric measurement-validity evidence |
| `P5_MV14` | `phq_label_only_psychometrics` | main psychometric measurement-validity evidence |
| `P5_MV19` | `phq_label_only_psychometrics` | main psychometric measurement-validity evidence |
| `P5_MV02` | `bounded_hamd_internal_diagnostic` | bounded diagnostic support or negative control |
| `P5_MV04c` | `protocol_task_control_support` | bounded diagnostic support or negative control |
| `P5_MV06_summary` | `evidence_localization_credibility` | bounded diagnostic support or negative control |
| `P5_MV09` | `conditional_identity_gate` | bounded diagnostic support or negative control |
| `P5_MV12` | `latent_target_negative_chain` | bounded diagnostic support or negative control |
| `P5_MV12_analysis` | `latent_target_negative_chain` | bounded diagnostic support or negative control |
| `P5_MV15` | `latent_target_negative_chain` | bounded diagnostic support or negative control |
| `P5_MV16` | `latent_target_negative_chain` | bounded diagnostic support or negative control |
| `P5_MV17a` | `feature_contract_sensitivity` | bounded diagnostic support or negative control |
| `P5_MV18` | `same_scale_hamd_context_control` | bounded diagnostic support or negative control |
| `P5_MV20` | `criterion_overlap_contamination_stress` | bounded diagnostic support or negative control |

## Retired Or Frozen Rows

28 rows are retained for traceability but removed from the active experiment queue. They should not trigger new model iterations unless a new mechanism-changing contract is written first.

## Local Cleanup Boundary

No bytecode/notebook cache categories remain in the ignored working tree.

Local predictions, features, raw datasets, Phase 2 local outputs, MV06 workbooks, and original plan notes are not deleted by this policy. They require user approval or a storage-specific cleanup request.

## Hygiene

- `artifact_hygiene_passed`: `True`
- `violation_count`: `0`
