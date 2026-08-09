# Cross-Scale Depression Modeling Framework

This repository manages code, configuration, subject-level manifests, audit
reports, and experiment-result summaries for a multimodal depression modeling
project.

The frozen paper frame is question-first:

- RQ1: cross-scale symptom constructs across PHQ-8, PHQ-9, HAMD-17, and SDS.
- RQ2: protocol and task-content dependence versus participant symptom evidence.
- RQ3: individual-difference moderation by age, personality, health status, and gait.
- RQ4: evidence localization as a credibility layer for severity predictions.

RQ1, RQ2, and RQ3 are the main contributions. RQ4 is used to test whether
predictions can be grounded in language, acoustic, facial, and gait evidence.

## Current Status

Phase 1 is frozen. Phase 2 is now closed for all applicable unified-baseline
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

The current method-design gate is:

```bash
python scripts/phase2_baseline_matrix.py --strict
python scripts/phase2_export_final_table.py
python scripts/phase2_completion_audit.py
```

The expected completion audit verdict is `phase2_goal_complete=true` and
`method_design_gate_recommendation=ready`.

## Key Paths

- Dataset registry: `datasets/registry.yaml`
- Dataset manifests: `datasets/manifests/`
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

## Version Policy

Track code, configs, docs, lightweight generated dataset manifests/audits,
memory files, and small summaries for the project's own diagnostics and method
experiments. Keep Phase 2 baseline reproduction scripts and matrix config, but
do not track generated Phase 2 baseline result artifacts by default.

Do not track raw datasets, audio/video, archives, pretrained weights, model
checkpoints, caches, local runtime files, raw clinical text, raw prompts, raw
model responses, large extracted features, or bulky prediction/embedding
artifacts, or generated `analysis/phase2_baselines/` baseline outputs. These
stay local and are regenerated through scripts.

Use `datasets/registry.yaml` and generated manifests as experiment inputs.
Avoid ad hoc raw-directory scans in training code.

The GitHub repository tracks only the clean reproducible experiment skeleton.
Local `main` has historical server-working commits that must not be pushed
directly. Use `scripts/publish_clean_github_snapshot.py` and the workflow in
`docs/github_publish_workflow.md` for clean remote updates.
