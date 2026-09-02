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

The active research gate is now Phase 5. Post-review minimal validations have
advanced from foundation-era stress tests to a formal measurement-aware PHQ
shared-item method table. MV22 executes the first stronger
foundation-backbone stress-test slice: frozen Qwen3-Embedding-0.6B text
features for E-DAIC/CMDC/PDCH, a WavLM base-plus audio proxy view,
MV07/MV12/MV15 reruns, and lightweight ERM/CORAL/MMD/DANN/IRM/GroupDRO-style
baselines against measurement-aware MV12 aggregate references. MV23 adds the
practical multimodal completion slice: WavLM/wav2vec2 audio proxies, OpenFace
video proxy, Qwen3/BGE-M3/multilingual-E5 text-audio-video fusion views, the
same adaptation baselines, and a lightweight measurement-aware latent-total
proxy head over E-DAIC/CMDC PHQ shared-item transfer. MV24 is the current
formal method result: the official Qwen3+WavLM+OpenFace representation feeds a
shared eight-symptom layer and corpus-specific cumulative-logit ordinal heads,
with source warm-start, target-head initialization, target calibration
reconstruction. Shared-symptom MMD is now treated as an auxiliary variant rather
than part of the core measurement-aware model. MV24 now reports two explicit
supervision regimes: zero-target-label baselines are compared with each other,
while corpus-specific-head, direct target fine-tuning, direct source+target
multitask, shared ordinal head, generic target MLP head, measurement-aware, and
measurement-aware + MMD are compared under the same target-calibration label
budget. The fair shared-layer calibrated ablation gate does not pass uniformly:
the large gain over the frozen corpus-specific-head baseline is mainly evidence
for target calibration/shared-layer adaptation, while the ordinal measurement
pathway is competitive and direction-dependent. A targeted item-level analysis
does not rescue a stronger corpus-specific-head claim: shared ordinal and
measurement-aware corpus-specific ordinal heads are near tied overall and on
the measurement-gate `C02/C06` threshold-shift item set. A fixed-latent
companion simulation shows only weak item-local mechanism consistency under
planted `C02/C06` threshold DIF, so use it as an audit-to-model sanity check
rather than a real-data superiority result. MV25 then hardens
the two most
attackable diagnostics: DAIC-WOZ
is explicitly demoted to a same-lineage PHQ-8 sanity control, and corpus
identity is re-probed with language/protocol/length/severity controls. MV26
adds targeted depression-specific baseline stress tests with GNN-SDA-style
semi-supervised graph domain adaptation and QuestMF-style question-wise ordinal
fusion under the same target calibration budget. The same MV26 package now
also includes an SCD-MLLM-style heterogeneous multimodal adapter/fusion stress
test under the same contract. The SCD-MLLM-style measurement-aware row improves
reconstruction-plus-calibration in both directions, strengthening the
foundation/fusion baseline reinforcement. Treat MV22/MV23/MV26 as
supporting stress tests and MV24 as the main method table, not
as a depression-detection SOTA or a WavLM Large/HuBERT Large/VideoMAE/end-to-end
fine-tuning claim. Those heavier variants require a separate raw audio/video
feature-generation and training contract, not just a backbone-name swap. MV09 shows that unconditional dataset
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
same-dataset observed-scale validity, and leave theta-conditioned feature
identity BA at `1.000`. External theta transfer is encoder-dependent
(BGE-M3 passes, multilingual-E5 fails), and B3 Pareto dominance is also
encoder-dependent (false for BGE-M3, true for multilingual-E5). Treat the
stable claim as: measurement harmonization can reduce output-level dataset
identifiability, while representation identity and observed-scale validity remain
required gates for stronger cross-corpus claims.

MV22 adds the foundation-backbone stress-test layer on top of MV17a. Qwen3
features keep MV07/MV12/MV15 blocked: feature identity BA remains `1.000`,
prediction identity BA is `0.978`, MV12 remains
`blocked_theta_gain_not_observed_scale_safe`, and theta-conditioned feature
identity remains `1.000`. Under Qwen text features, the measurement-aware MV12
reference improves shared-item macro MAE over the direct itemwise reference in
both PHQ transfer directions (`0.733` vs `0.869` for CMDC-to-E-DAIC; `0.855`
vs `0.883` for E-DAIC-to-CMDC). Treat this as evidence that foundation
backbones do not remove the target-validity gate.

MV23 adds the lightweight multimodal completion layer. It executes 8
foundation/proxy views over E-DAIC/CMDC PHQ shared-item transfer, with 288
adapter aggregate rows and 48 measurement-aware proxy rows. The best
CMDC-to-E-DAIC row is Qwen3+WavLM+OpenFace with MMD-style alignment (macro item
MAE `0.833`); the best E-DAIC-to-CMDC row is Qwen3+wav2vec2 with MMD-style
alignment (macro item MAE `0.597`). The best measurement-aware proxy rows are
Qwen3+WavLM+OpenFace for CMDC-to-E-DAIC (macro item MAE `0.859`) and
multilingual-E5+WavLM+OpenFace for E-DAIC-to-CMDC (macro item MAE `0.754`).
Treat MV23 as a lightweight multimodal foundation stress test, not as a
WavLM Large, HuBERT Large, VideoMAE, or full end-to-end multimodal success
claim.

MV24 replaces the proxy method row with a single formal measurement-aware
ordinal architecture and the clean main table requested for the manuscript.
The architecture is fixed as frozen Qwen3 text + WavLM speech + OpenFace video
subject features, a trainable projector, an eight-dimensional shared PHQ
symptom layer, and corpus-specific cumulative-logit ordinal item heads. The
core method trains with source ordinal reconstruction and target calibration
ordinal reconstruction after source warm-start and target-head initialization;
shared-symptom MMD is reported as an auxiliary variant. The result table now separates target-label
budgets: ERM, CORAL, MMD, DANN, the strongest direct foundation baseline, and
latent-only are zero-target-label rows, while the calibrated block adds direct
target fine-tuning, direct source+target multitask, shared ordinal head, and a
generic target MLP head alongside corpus-specific-head, measurement-aware, and
measurement-aware + MMD. The fair-ablation gate is
`not_passed_uniform_measurement_pathway_superiority`: measurement-aware is best
or near-best in CMDC-to-E-DAIC, but direct source+target multitask is best in
E-DAIC-to-CMDC. The targeted item analysis also shows near ties between the
shared ordinal and corpus-specific ordinal heads on both all shared PHQ items
and the `C02/C06` threshold-shift item set. The companion fixed-latent
simulation behaves as expected directionally only under planted threshold DIF,
but the effects are small and anchors do not improve. MV24 now also reports
secondary clinical-reader metrics
following cross-domain MDD reporting practice: total MAE/CCC and a shared-PHQ
total >=10 endpoint with Macro-F1, Balanced Accuracy, AUROC, AUPRC,
Sensitivity, and Specificity. The lambda-MMD sweep is nearly flat, so the
manuscript should present MMD as a mild regularizer and present target
calibration/shared-layer adaptation separately from ordinal measurement
parameterization. The aggregate
outputs are in
`analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/`
and pass artifact hygiene.

MV26 adds the requested depression-specific baseline stress table. It uses the
same E-DAIC<->CMDC PHQ shared-item split, the same official MV24
Qwen3+WavLM+OpenFace subject representation, the same five seeds, and the same
target calibration label budget for all rows. The two families are
GNN-SDA-style semi-supervised graph domain adaptation and QuestMF-style
question-wise modality fusion. Each is evaluated with a direct ordinal item
head and with the paper's target-calibrated measurement-aware variant. QuestMF-style gains
are consistent on the primary reconstruction-plus-calibration score (`1.203 ->
1.159` for CMDC-to-E-DAIC; `1.133 -> 1.096` for E-DAIC-to-CMDC). GNN-SDA-style
is direction-sensitive (`1.121 -> 1.066` for E-DAIC-to-CMDC, but `1.339 ->
1.431` for CMDC-to-E-DAIC because calibration worsens). Use MV26 as a close
baseline stress test: it supports complementarity for question-wise ordinal
fusion and exposes that graph/domain adaptation does not by itself make the
measurement pathway trivial. The aggregate outputs are in
`analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`
and pass artifact hygiene.

The MV26 package also completes the requested public close-baseline sweep with
an SCD-MLLM-style heterogeneous multimodal/foundation fusion stress test.
SCD-MLLM-style measurement-aware target modeling improves the primary
reconstruction-plus-calibration score in both directions (`1.485 -> 1.238` for
CMDC-to-E-DAIC; `1.100 -> 1.084` for E-DAIC-to-CMDC), making it the cleanest
foundation/fusion baseline reinforcement. These rows are merged into the same
aggregate outputs at
`analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`,
which now contains 60 seed-level rows and passes artifact hygiene.

MV25 reruns the two most reviewer-sensitive diagnostics. DAIC-WOZ/E-DAIC is
now documented with explicit label provenance: the 141 complete item-labeled
DAIC-WOZ train/dev subjects overlap the E-DAIC train/dev label rows, the
all-item exact-match rate is `0.993`, and the mean absolute item difference is
`0.007`; this is a same-lineage sanity control, not independent-corpus
evidence. Controlled identity probes show why the old raw `1.000` corpus
identity should be used carefully: the cross-language E-DAIC/CMDC identity
score is largely explained by length/protocol controls, while same-language
E-DAIC lineage probes remain high after fold-internal length and severity
residualization (`0.839` Qwen3 text, `0.897` WavLM audio). The aggregate
outputs are in
`analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity/`
and pass artifact hygiene.

MV16 completed the predeclared DIF-guided few-shot measurement-calibration
test with anchors `C01/C04/C05/C07`, localized `C02/C06` threshold calibration,
k=`0/5/10/20/40`, and zero-shot, global affine/monotonic, all-threshold, and
direct target-adaptation comparators. It passes split, anchor-consistency, direct
baseline, output-identity-reporting, and artifact-hygiene gates, but fails the
both-direction DIF-guided small-k mechanism gate
(`blocked_no_dif_guided_small_k_gain`). Treat it as a calibration stress test:
localized measurement information can be actionable, but a robust framework
needs corpus-specific measurement heads and validity gates. The Baselines, Failure-Mode
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
encoder-dependent. Label-only MV10/MV11/MV19 remain the primary PHQ
psychometric evidence; corrected MV13/MV14 now provide anchor-linked `mirt`
qualitative/uncertainty corroboration while retaining configural convergence
and MV19 finite-sample caveats. The
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
negative wording, the foundation-backbone framework positioning, and
primary-source citation verification.
Optional MV06 work is resolving the one incomplete local candidate before
stronger RQ4 wording; aggregate agreement uncertainty is now available. Theta
scores, fitted parameters, row predictions, transformed features, bootstrap
samples, calibration parameters, and model artifacts remain local-only.

Experiment consolidation is now explicit. The active paper evidence bundle is
generated at
`analysis/phase5_minimal_validation/experiment_consolidation/`: paper core
uses `MV10/MV11/MV19` as primary PHQ psychometric evidence and keeps
`MV13/MV14` only as limited `mirt` qualitative screens, paper support is
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
- Foundation-backbone validation contract: `analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`
- MV22 foundation-backbone validation: `analysis/phase5_minimal_validation/p5_mv22_foundation_backbone_validation/`
- MV23 foundation multimodal completion: `analysis/phase5_minimal_validation/p5_mv23_foundation_multimodal_completion/`
- MV24 formal measurement-aware ordinal main table: `analysis/phase5_minimal_validation/p5_mv24_measurement_aware_ordinal_model/`
- MV24 fixed-latent measurement-head DIF simulation: `analysis/phase5_minimal_validation/p5_mv24_measurement_head_dif_simulation/`
- MV25 provenance and controlled corpus-identity diagnostics: `analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity/`
- MV26 depression-specific baseline stress test: `analysis/phase5_minimal_validation/p5_mv26_depression_specific_baselines/`
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
