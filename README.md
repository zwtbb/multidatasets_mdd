# Cross-Scale Depression Modeling Framework

This repository manages code, configuration, public manifest schemas,
aggregate audit reports, and experiment-result summaries for a multimodal
depression modeling project. Real row-level subject manifests are generated and
used locally from licensed datasets, but are not part of the public release.

The original research frame was question-first:

- RQ1: cross-scale symptom constructs across PHQ-8, PHQ-9, HAMD-17, and SDS.
- RQ2: protocol and task-content dependence versus participant symptom evidence.
- RQ3: individual-difference moderation by age, personality, health status, and gait.
- RQ4: evidence localization as a credibility layer for severity predictions.

Post-review framing now compresses these into a target measurement-validity
paper. RQ1 label measurement is the core positive evidence; RQ2/Phase 3 is
motivating shortcut evidence; RQ3 is a population/individual-difference stress
test; RQ4 is a credibility layer, not an evidence-retrieval method
contribution.

## Current Status

Phase 1 is frozen and Phase 2 is closed for all applicable unified-baseline
rows:

- Planned runs: 67.
- Completed runs: 66.
- Conditional exclusions: 1 (`mpdd_public_p3hf`).
- Blocked runs: 0.
- Completed metric rows: 313/318.
- Not-applicable metric rows: 5/318.

`mpdd_public_p3hf` is not filled into the canonical 175-subject MPDD Phase 2
matrix because its packaged Young-only data, split, feature dimensions, and
dev+test evaluation contract do not satisfy the "code and input features match
this version" prerequisite. It can be revisited only as a separately labeled
P3HF packaged-Young-110 reproduction or under a newly defined compatible
protocol.

The Phase 2 completion gate is:

```bash
python scripts/phase2_baseline_matrix.py --strict
python scripts/phase2_export_final_table.py
python scripts/phase2_completion_audit.py
```

The expected completion audit verdict is `phase2_goal_complete=true` and
`method_design_gate_recommendation=ready`.

The active research gate is now Phase 5. Post-review minimal validations are
complete through the `P5_MV20` criterion-overlap stress test, and the
full-method gate remains
`blocked_but_publishable_diagnostic_direction` with
`full_method_allowed=false`. The paper direction is therefore reframed from a
positive full shared-symptom model to a target measurement-validity paper:
feature shift, target measurement shift, and prediction shift are distinct
layers. MV09 shows that unconditional dataset
identity should be treated as a shortcut-risk screen, while conditional
identity remains high after severity or aligned-item conditioning. MV10 adds a
label-only E-DAIC/CMDC PHQ psychometric screen with loading congruence `0.998`,
`7/8` approximate metric-loading items, `4/8` threshold/scalar items, and
candidate anchors (`C01`, `C04`, `C05`, `C07`). MV11 and MV13 preserve that
anchor/DIF pattern with no strong loading DIF and threshold DIF concentrated on
`C02` and `C06`, while AIC/BIC remain split and MV13 retains a configural
convergence warning.

MV14 now uses convergence-safe bootstrap inference. The predeclared
smoke/core/DIF tiers ran with R=`10/200/100`; full-ladder model selection has
`120/200` convergence-safe effective core draws after `185/200` fit-success
draws, configural converges in `120/200`, and the stable metric/partial/scalar
ladder has `197` effective draws. All four MV10 anchors are stable, loading DIF
is sparse, threshold DIF remains concentrated on `C02` and `C06`, full-ladder
AIC/BIC prefer `configural`/`scalar`, and stable-ladder AIC/BIC prefer
`partial_mv10`/`scalar`. Treat MV14 as item-level measurement-shift evidence
with global model-selection uncertainty, not as a bootstrap-confirmed global
partial-invariance win.

MV19 now adds the observed-N finite-sample PHQ simulation. With 500 simulations
per world under the observed E-DAIC/CMDC PHQ N and severity distributions, the
scalar-invariant H0 has C02/C06 both-flag false rate `0.208` and top-two
false-localization `0.034`; the C02/C06 threshold-DIF H1 has both-flag recovery
`0.662`, top-two recovery `0.222`, and C01/C04/C05/C07 anchor subset recovery
`0.178`. Treat C02/C06 as repeated but finite-sample-bounded dataset-group
threshold-shift evidence, not robust standalone DIF at the observed N.

MV12 and MV15 are now legacy/supporting diagnostics from the old Chinese-BGE
chain. They remain useful because `X -> theta` is learnable within source
datasets and low-dimensional output identity is lower than upstream feature
identity, but their universal external-transfer-failure and B3-dominance
wording has been superseded by MV17a.

MV17a is the current feature-contract consequence layer. It makes BGE-M3 the
primary multilingual encoder and multilingual-E5 the sensitivity encoder,
regenerates E-DAIC/CMDC/PDCH features, and reruns MV07/MV12/MV15. Both encoders
keep MV07/MV12/MV15 blocked; both pass same-dataset theta utility, fail
same-dataset observed-scale safety, and leave theta-conditioned feature
identity BA at `1.000`. External theta transfer is encoder-dependent
(BGE-M3 passes, multilingual-E5 fails), and B3 Pareto dominance is also
encoder-dependent (false for BGE-M3, true for multilingual-E5). Treat the
stable claim as: measurement harmonization can reduce output-level dataset
identifiability, but current features do not establish observed-scale-safe or
feature-invariant cross-corpus prediction.

MV16 completed the predeclared DIF-guided few-shot measurement-calibration
test with anchors `C01/C04/C05/C07`, localized `C02/C06` threshold calibration,
k=`0/5/10/20/40`, and zero-shot, global affine/monotonic, all-threshold, and
direct target-adaptation comparators. It passes split, anchor-safety, direct
baseline, output-identity-reporting, and artifact-hygiene gates, but fails the
both-direction DIF-guided small-k mechanism gate
(`blocked_no_dif_guided_small_k_gain`). Treat it as bounded/negative
calibration evidence, not a full method pass. The Baselines, Failure-Mode
Diagnostics, and Measurement Results scaffold is now generated from aggregate
tables only, and `manuscript_draft.md` now assembles the first full
measurement-audit manuscript draft with traceability and hygiene checks.
Post-review audit added a major feature-contract caveat: the legacy
BGE-linked MV07 -> MV12 -> MV15 -> MV16 chain used
`BAAI/bge-small-zh-v1.5`, a Chinese encoder, for English E-DAIC transcripts.
MV17a now addresses the paper-critical part of that caveat by regenerating
E-DAIC/CMDC/PDCH features with BGE-M3 and multilingual-E5, then rerunning
MV07/MV12/MV15. Both multilingual encoders reproduce the blocked feature-level
pattern, but external theta transfer and B3 severity-control dominance are
encoder-dependent. Label-only MV10/MV11/MV13/MV14/MV19 are unaffected. The
bibliography registry and `references.bib` now cover all current source-context
rows, with corrected primary-source metadata for P3HF, Multi-Probe Audit,
EMNLP interviewer bias, and the final Pattern Recognition version of SCD-MLLM.
MV18 now adds the same-language/same-HAMD CMDC versus PDCH exploratory
control: within the mild/moderate HAMD overlap it flags 4 severity-conditioned
residual item shifts and 7 threshold shifts, and bidirectional frozen-feature
transfer remains weak. Treat it as exploratory context-shift support, not
formal HAMD invariance. MV20 closes the bounded protocol-label-overlap stress
test: CMDC Q1-Q12 question-position units were feasible, PDCH and E-DAIC were
excluded for missing clean protocol units, and high-overlap deletion was not
clearly worse than matched random deletion under BGE-M3 primary or
multilingual-E5 sensitivity. Current next action: freeze experiments and
finalize the manuscript with MV19-downgraded PHQ wording, MV20 bounded
negative wording, and primary-source citation verification.
Optional MV06 work is resolving the one incomplete local candidate before
stronger RQ4 wording; aggregate agreement uncertainty is now available. Theta
scores, fitted parameters, row predictions, transformed features, bootstrap
samples, calibration parameters, and model artifacts remain local-only.

Experiment consolidation is now explicit. The active paper evidence bundle is
generated at
`analysis/phase5_minimal_validation/experiment_consolidation/`: paper core is
limited to `MV10/MV11/MV13/MV14/MV19`, paper support is
`MV02/MV04c/MV06/MV09/MV12/MV15/MV16/MV17a/MV18/MV20`, and early weak or
superseded MV rows are frozen as historical diagnostics. Tracked aggregate outputs are not
deleted because they provide traceability for the gate and manuscript claim
boundary. Only interpreter and notebook caches were physically removed in this
cleanup; local predictions, features, Phase 2 outputs, MV06 workbooks, raw
datasets, and the local original-plan note remain local-only unless a separate
storage cleanup is approved.

## Key Paths

- Dataset registry: `datasets/registry.yaml`
- Public dataset schemas: `datasets/schemas/`
- Synthetic dataset examples: `datasets/examples/`
- Local generated manifests: `datasets/manifests/`
- Dataset audit: `datasets/audit/`
- Phase 2 matrix config: `baselines/phase2_baseline_matrix.yaml`
- Phase 2 status: `analysis/phase2_baselines/baseline_matrix_status.csv`
- Phase 2 final table: `analysis/phase2_baselines/final_table/phase2_final_baseline_table.csv`
- Phase 2 completion audit: `analysis/phase2_baselines/phase2_completion_audit/phase2_completion_audit.md`
- Chinese reproduction guide: `docs/reproduction_zh.md`
- Research direction entrypoint: `docs/experiment_direction.md`
- Main-agent control plan: `docs/master_experiment_plan.md`
- Active main-agent handoff: `memory/ACTIVE_HANDOFF.md`
- Issue and decision log: `docs/experiment_issue_log.md`
- GitHub publish workflow: `docs/github_publish_workflow.md`
- Phase 5 full-method gate: `analysis/phase5_minimal_validation/full_method_gate_audit/`
- Phase 5 experiment consolidation: `analysis/phase5_minimal_validation/experiment_consolidation/`
- MV09 conditional identity audit: `analysis/phase5_minimal_validation/p5_mv09_conditional_identity_audit/`
- MV10 psychometric invariance baseline: `analysis/phase5_minimal_validation/p5_mv10_psychometric_invariance_baseline/`
- MV11 formal psychometric confirmation: `analysis/phase5_minimal_validation/p5_mv11_formal_psychometric_confirmation/`
- MV12 two-stage latent-target design: `analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target_design/`
- MV12 two-stage latent-target run: `analysis/phase5_minimal_validation/p5_mv12_two_stage_latent_target/`
- MV12 aggregate tradeoff analysis: `analysis/phase5_minimal_validation/p5_mv12_latent_target_tradeoff_analysis/`
- MV13 external psychometric replication design: `analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication_design/`
- MV13 external psychometric replication run: `analysis/phase5_minimal_validation/p5_mv13_external_psychometric_replication/`
- MV14 measurement-uncertainty bootstrap design: `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap_design/`
- MV14 measurement-uncertainty bootstrap run: `analysis/phase5_minimal_validation/p5_mv14_measurement_uncertainty_bootstrap/`
- MV15 latent-conditioned identity design: `analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity_design/`
- MV15 latent-conditioned identity run: `analysis/phase5_minimal_validation/p5_mv15_latent_conditioned_identity/`
- MV16 DIF-guided calibration design: `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration_design/`
- MV16 DIF-guided calibration run: `analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration/`
- MV17 post-review route: `analysis/phase5_minimal_validation/p5_mv17_postreview_measurement_validity_route/`
- MV17a multilingual feature-contract sensitivity: `analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract/`
- MV18 CMDC-PDCH HAMD same-scale control: `analysis/phase5_minimal_validation/p5_mv18_cmdc_pdch_hamd_same_scale_control/`
- MV19 PHQ finite-sample simulation: `analysis/phase5_minimal_validation/p5_mv19_phq_finite_sample_psychometric_simulation/`
- Diagnostic paper outline: `docs/diagnostic_measurement_audit_paper_outline.md`
- Diagnostic paper scaffolds: `analysis/diagnostic_measurement_audit_paper/`
- Results-section scaffold generator: `scripts/build_diagnostic_paper_results_sections.py`
- Bibliography generator: `scripts/build_diagnostic_paper_bibliography.py`
- Bibliography file: `analysis/diagnostic_measurement_audit_paper/references.bib`
- Citation registry: `analysis/diagnostic_measurement_audit_paper/citation_registry.csv`
- Manuscript draft generator: `scripts/build_diagnostic_paper_manuscript_draft.py`
- Manuscript draft: `analysis/diagnostic_measurement_audit_paper/manuscript_draft.md`

## Rebuild Commands

Dataset audit:

```bash
python scripts/audit_datasets.py
```

Subject split layer and baseline matrix:

```bash
python scripts/phase2_build_subject_splits.py
python scripts/phase2_baseline_matrix.py --strict
```

Final table and completion gate:

```bash
python scripts/phase2_export_final_table.py
python scripts/phase2_completion_audit.py
```

Metric helper self-test:

```bash
python scripts/phase2_metrics.py --self-test
```

Diagnostic paper writing scaffolds:

```bash
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_data_governance_section.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/phase5_consolidate_experiment_inventory.py
python scripts/phase5_plan_mv17_postreview_measurement_validity_route.py --overwrite
python scripts/build_diagnostic_paper_manuscript_draft.py
```

Phase 5 gate, MV13/MV14 psychometric checks, MV12 analysis, MV15, and MV16:

```bash
python scripts/phase5_plan_mv13_external_psychometric_replication.py --overwrite
python scripts/phase5_run_mv13_external_psychometric_replication.py
python scripts/phase5_plan_mv14_measurement_uncertainty_bootstrap.py --overwrite
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
python scripts/phase5_analyze_mv12_latent_target_tradeoffs.py
python scripts/phase5_plan_mv15_latent_conditioned_identity.py --overwrite
python scripts/phase5_run_mv15_latent_conditioned_identity.py
python scripts/phase5_plan_mv16_dif_guided_calibration.py --overwrite
python scripts/phase5_run_mv16_dif_guided_calibration.py
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```

## Version Policy

Track code, configs, docs, public dataset schemas/examples, lightweight
aggregate audits, memory files, and small summaries for the project's own
diagnostics and method experiments. Keep Phase 2 baseline reproduction scripts
and matrix config, but do not track generated Phase 2 baseline result artifacts
by default.

Do not track raw datasets, real row-level subject manifests, real row-level
file-integrity tables, real subject split maps, audio/video, archives,
pretrained weights, model checkpoints, caches, local runtime files, raw
clinical text, raw prompts, raw model responses, large extracted features,
bulky prediction/embedding artifacts, or generated `analysis/phase2_baselines/`
baseline outputs. These stay local and are regenerated through scripts.

Use `datasets/registry.yaml` and locally generated manifests as experiment
inputs. Avoid ad hoc raw-directory scans in training code.

The GitHub repository tracks only the clean reproducible experiment skeleton.
Local `main` has historical server-working commits that must not be pushed
directly. Use `scripts/publish_clean_github_snapshot.py` and the workflow in
`docs/github_publish_workflow.md` for clean remote updates.
