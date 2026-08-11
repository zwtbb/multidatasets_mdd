# Session Memory: Phase 5 MV10 Psychometric Invariance Baseline

Status: active
Last updated: 2026-08-11 UTC
Thread/task: main agent continuation

## Scope

This session owns the P5_MV10 label-only PHQ-8/PHQ-9 psychometric invariance
baseline, plus the associated full-method gate, paper scaffold, issue-log, and
memory updates. It should not start a new multimodal head iteration, train a
full method, export subject-level factor scores, or commit fitted
psychometric/model parameters.

## Current State

- MV10 is complete at
  `/root/autodl-tmp/analysis/phase5_minimal_validation/p5_mv10_psychometric_invariance_baseline/`.
- The script uses only manifest-governed E-DAIC PHQ-8 and CMDC PHQ-9 item
  labels. It reads no raw text/media, multimodal feature caches, private review
  material, row-level model outputs, or subject-level predictions.
- Current runtime has `numpy`, `pandas`, `scipy`, and `sklearn`, but does not
  have `Rscript`, `lavaan`, `mirt`, `semopy`, `factor_analyzer`, or related
  formal psychometric tooling. Therefore MV10 is an approximate label-only
  invariance screen, not formal multi-group ordinal CFA or graded-response IRT.
- Input coverage: E-DAIC has 219 PHQ-8 item-labeled train/dev subjects; CMDC
  has 77 PHQ-9 item-labeled valid subjects.
- MV10 status is `complete_partial_invariance_supported_approx`.
- Artifact hygiene passed; tracked outputs are aggregate-only.

## Key Decisions

- Use MV10 as measurement-shift evidence and a candidate anchor map only.
- Candidate PHQ anchors are `C01` depressed mood, `C04` fatigue, `C05`
  appetite, and `C07` concentration.
- `C02` anhedonia, `C03` sleep, and `C06` self-worth are metric-only but should
  be threshold-free under the current screen.
- `C08` psychomotor should be freed for loading or threshold differences.
- Full method remains blocked. The next RQ1 gate is formal ordinal CFA/IRT or
  equivalent psychometric confirmation, then a predeclared two-stage target
  only if the measurement target is stable: first `Y -> theta`, then
  `X -> theta`.

## Files Owned Or Touched

- `scripts/phase5_run_mv10_psychometric_invariance_baseline.py`
- `scripts/phase5_full_method_gate_audit.py`
- `scripts/build_diagnostic_paper_claim_tables.py`
- `analysis/phase5_minimal_validation/experiment_matrix.csv`
- `analysis/phase5_minimal_validation/p5_mv10_psychometric_invariance_baseline/`
- `analysis/phase5_minimal_validation/full_method_gate_audit/`
- `analysis/diagnostic_measurement_audit_paper/`
- `README.md`
- `docs/diagnostic_measurement_audit_paper_outline.md`
- `docs/experiment_issue_log.md`
- `MEMORY.md`
- `memory/sessions/session_master_orchestration.md`
- `memory/sessions/session_40_mv10_psychometric_invariance_baseline.md`

## Generated Artifacts

Regenerate MV10 with:

```bash
python scripts/phase5_run_mv10_psychometric_invariance_baseline.py
```

Key aggregate outputs:

- `psychometric_input_audit.csv`
- `reliability_dimensionality_summary.csv`
- `bootstrap_reliability_summary.csv`
- `loading_invariance_summary.csv`
- `threshold_dif_summary.csv`
- `partial_invariance_summary.csv`
- `empirical_score_linking_summary.csv`
- `gate_recommendations.csv`
- `stage_summary.csv`
- `source_context_psychometric_baseline.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

Regenerate the downstream claim boundary and paper tables with:

```bash
python scripts/phase5_full_method_gate_audit.py
python scripts/build_diagnostic_paper_claim_tables.py
```

## Blockers And Risks

- MV10 is approximate because formal ordinal CFA/IRT tooling is not installed
  locally.
- Threshold/scalar invariance is partial: only 4/8 shared PHQ items pass the
  approximate threshold-location screen.
- CMDC has only 77 PHQ item-labeled subjects, so formal models may need careful
  regularization, bootstrap stability checks, or a documented fallback.
- Do not write or commit subject-level factor scores, fitted parameters,
  bootstrap subject rows, or row diagnostics.

## External Source Context

- PHQ-9 measurement invariance methods: Galenkamp et al. 2017,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/
- PHQ-9 sociodemographic invariance: Patel et al. 2019,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/
- PHQ/HAMD psychometric differences: Ma et al. 2021,
  https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full
- Cross-scale linking motivation: Zhou et al. 2026,
  https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract

## Next Handoff

Run or package formal ordinal CFA/IRT confirmation for the MV10 PHQ anchor map.
If formal fit and DIF results confirm a stable partial-invariance target,
predeclare a two-stage latent-target experiment. Keep all subject-level factor
scores, fitted parameters, and row diagnostics local-only.
