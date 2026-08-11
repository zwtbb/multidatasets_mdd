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
through `P5_MV13` external psychometric replication, and `P5_MV14` measurement
uncertainty/bootstrap is now predeclared as a design contract; the full-method gate remains
`blocked_but_publishable_diagnostic_direction` with
`full_method_allowed=false`. The paper direction is therefore reframed from a
positive full shared-symptom model to a measurement-shift /
measurement-invariance diagnostic paper. MV09 shows that unconditional dataset
identity should be treated as a shortcut-risk screen, while conditional
identity remains high after severity or aligned-item conditioning. MV10 adds a
label-only PHQ-8/PHQ-9 psychometric screen: both datasets pass the one-factor
configural screen, loading congruence is `0.998`, `7/8` items pass the
approximate metric-loading screen, but only `4/8` items pass the approximate
threshold/scalar screen. Treat MV10 as partial measurement-shift evidence and
candidate anchors (`C01`, `C04`, `C05`, `C07`). MV11 then fits a label-only
multi-group graded-response IRT confirmation: all four MV10 anchors are
preserved, no loading-DIF items are strongly flagged, `C02` and `C06` show
threshold DIF, and AIC/BIC disagree between the partial and scalar core models.
MV12 then runs that two-stage test. The `X -> theta` head improves same-dataset
theta MAE versus train mean on E-DAIC and CMDC, and conditional shared-latent
identity BA falls to `0.602`, but observed-scale reconstruction is worse than
the direct itemwise floor and external theta transfer does not pass.
Cross-dataset observed-scale transfer is nevertheless better through the
latent route than direct item transfer, so treat MV12 as a predictive
fidelity-dataset identifiability trade-off, not a simple failed model. The
aggregate MV12
tradeoff/failure-mode analysis freezes the current latent-target line rather
than adding another small shallow-head variant. MV13 installs a version-captured
external R psychometric runtime and reruns the PHQ multi-group graded-response
model ladder with `mirt::multipleGroup`. It qualitatively replicates MV11:
four MV10 anchors are confirmed, no loading DIF is strongly flagged, threshold
DIF remains concentrated on `C02` and `C06`, AIC prefers the partial model, and
BIC prefers scalar. The configural model retains a convergence warning, so MV13
is bounded external measurement evidence, not a full-method pass. MV14 now
fixes the bootstrap tiers, local-only boundaries, stability metrics, and
pass/downgrade rules for quantifying anchor, DIF, model-selection, convergence,
and SE/CI-availability uncertainty before stronger item-level wording.

The Baselines, Failure-Mode Diagnostics, and Measurement Results scaffold is
now generated from aggregate tables only. Current next action: implement and
run measurement-uncertainty bootstrap (`P5_MV14`), then latent-conditioned
dataset identity (`P5_MV15`) and cross-dataset theta calibration / few-shot
scale linking (`P5_MV16`) if their gates remain coherent. Optionally expand
E-DAIC MV06 double annotation before stronger RQ4 wording. Theta scores, fitted
parameters, row predictions, transformed features, bootstrap samples,
calibration parameters, and model artifacts remain local-only.

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

Phase 5 gate, MV13 external psychometric replication, and MV14 bootstrap design:

```bash
python scripts/phase5_plan_mv13_external_psychometric_replication.py --overwrite
python scripts/phase5_run_mv13_external_psychometric_replication.py
python scripts/phase5_plan_mv14_measurement_uncertainty_bootstrap.py --overwrite
python scripts/phase5_full_method_gate_audit.py
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
