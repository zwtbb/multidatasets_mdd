# Cross-Scale Depression Modeling Framework

This repository manages code, configuration, public manifest schemas,
aggregate audit reports, and experiment-result summaries for a multimodal
depression modeling project. Real row-level subject manifests are generated and
used locally from licensed datasets, but are not part of the public release.

The frozen paper frame is question-first:

- RQ1: cross-scale symptom constructs across PHQ-8, PHQ-9, HAMD-17, and SDS.
- RQ2: protocol and task-content dependence versus participant symptom evidence.
- RQ3: individual-difference moderation by age, personality, health status, and gait.
- RQ4: evidence localization as a credibility layer for severity predictions.

RQ1, RQ2, and RQ3 are the main contributions. RQ4 is used to test whether
predictions can be grounded in language, acoustic, facial, and gait evidence.

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

The active research gate is now Phase 5. Minimal validations are complete
through `P5_MV15` design; the full-method gate remains
`blocked_but_publishable_diagnostic_direction` with
`full_method_allowed=false`. The paper direction is therefore reframed from a
positive full shared-symptom model to a measurement-shift /
measurement-validity diagnostic paper. MV09 shows that unconditional dataset
identity should be treated as a shortcut-risk screen, while conditional
identity remains high after severity or aligned-item conditioning. MV10 adds a
label-only PHQ-8/PHQ-9 psychometric screen with loading congruence `0.998`,
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

MV12 is frozen as bounded diagnostic evidence. The `X -> theta` head improves
same-dataset theta MAE versus train mean and lowers identity versus upstream
BGE features (`0.602` conditional predicted-theta BA versus MV09 feature
reference `0.991`), but observed-scale reconstruction is worse than direct
itemwise Ridge and zero-shot source-calibrated external theta transfer fails.
The aggregate tradeoff analysis adds the key caveat: B3 direct itemwise Ridge
compressed to theta has lower pooled observed macro MAE (`0.692` versus
`0.701`) and lower conditional identity (`0.579` versus `0.602`) than M12a, so
M12a is not uniquely more invariant than a dimension-matched severity baseline.

The Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold is
now generated from aggregate tables only. Current next action: implement and
run the predeclared latent-conditioned dataset identity runner (`P5_MV15`) with
raw, total, predicted-total, item, B3 itemwise-theta, psychometric-theta,
covariate, predicted-output, and severity-only controls; then predeclare
DIF-guided few-shot measurement calibration (`P5_MV16`). Optional MV06 work is
agreement uncertainty analysis plus resolving the one incomplete local
candidate before stronger RQ4 wording. Theta scores, fitted parameters, row
predictions, transformed features, bootstrap samples, calibration parameters,
and model artifacts remain local-only.

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
- Issue and decision log: `docs/experiment_issue_log.md`
- GitHub publish workflow: `docs/github_publish_workflow.md`
- Phase 5 full-method gate: `analysis/phase5_minimal_validation/full_method_gate_audit/`
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
- Diagnostic paper outline: `docs/diagnostic_measurement_audit_paper_outline.md`
- Diagnostic paper scaffolds: `analysis/diagnostic_measurement_audit_paper/`
- Results-section scaffold generator: `scripts/build_diagnostic_paper_results_sections.py`

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
```

Phase 5 gate, MV13/MV14 psychometric checks, MV12 analysis, and MV15 design:

```bash
python scripts/phase5_plan_mv13_external_psychometric_replication.py --overwrite
python scripts/phase5_run_mv13_external_psychometric_replication.py
python scripts/phase5_plan_mv14_measurement_uncertainty_bootstrap.py --overwrite
python scripts/phase5_run_mv14_measurement_uncertainty_bootstrap.py
python scripts/phase5_analyze_mv12_latent_target_tradeoffs.py
python scripts/phase5_plan_mv15_latent_conditioned_identity.py --overwrite
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_results_sections.py
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
