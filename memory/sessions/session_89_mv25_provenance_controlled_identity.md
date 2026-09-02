# Session Memory: MV25 Provenance Controlled Identity

Status: complete
Last updated: 2026-08-27 UTC
Thread/task: DAIC/E-DAIC provenance and controlled corpus-identity diagnostics

## Scope

This session owns two reviewer-sensitive diagnostic repairs:

- DAIC-WOZ/E-DAIC label provenance and overlap wording.
- Corpus-identity probes with language/protocol/length/severity controls.

It does not reopen large backbone training, WavLM Large/HuBERT Large/VideoMAE,
end-to-end multimodal fine-tuning, HAMD MIM/IRT, or a new depression-detection
leaderboard.

## Current State

MV25 is complete at
`analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity/`.
The run is aggregate-only and passes artifact hygiene.

DAIC-WOZ/E-DAIC is now explicitly a same-lineage PHQ-8 sanity control rather
than an independent corpus. The complete item-labeled DAIC-WOZ train/dev rows
overlap E-DAIC train/dev labels for `141` subjects; across all eight shared
PHQ-8 items, exact item agreement is `0.993` and mean absolute item difference
is `0.007`. The local DAIC-WOZ extracted folders are symlinked into the E-DAIC
extracted tree.

Controlled corpus-identity probes show that the old raw E-DAIC/CMDC identity
`1.000` should not carry the representation claim by itself: after fold-internal
length and severity residualization, E-DAIC/CMDC drops to near chance in Qwen3
text (`0.497`), WavLM audio (`0.484`), and OpenFace video (`0.522`). The stronger
defensible evidence against a pure English-vs-Chinese explanation comes from
same-language probes. Within E-DAIC English PHQ-8 virtual-interview data,
DAIC-WOZ-lineage versus extended-lineage identity remains high after controls
for Qwen3 text (`0.839`) and WavLM audio (`0.897`), with OpenFace modest
(`0.599`). CMDC/PDCH same-Chinese HAMD text is modest after controls (`0.572`).

## Key Decisions

- In the manuscript, DAIC-WOZ/E-DAIC should be called a same-lineage sanity
  control and label-contract check, not an independent dataset or third
  independent PHQ corpus.
- Do not make the raw E-DAIC/CMDC `1.000` identity score carry the
  representation-heterogeneity claim alone. Write it as a raw shortcut-risk
  screen, then use MV25 same-language lineage probes as the controlled evidence
  that corpus/protocol identity is not reducible to English-vs-Chinese text
  recognition.
- The more polished story is that raw corpus identity is partly protocol/length
  driven, while acquisition/lineage signatures remain detectable even when
  language and severity are held fixed.

## Files Owned Or Touched

- `scripts/phase5_run_mv25_provenance_controlled_identity.py`
- `analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity/`
- `README.md`
- `MEMORY.md`
- `memory/ACTIVE_HANDOFF.md`
- `docs/experiment_issue_log.md`
- `analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `analysis/diagnostic_measurement_audit_paper/foundation_backbone_measurement_aware_validation_contract.md`

## Generated Artifacts

Regeneration command:

```bash
python scripts/phase5_run_mv25_provenance_controlled_identity.py --clean
```

Primary artifact directory:

```text
analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity/
```

Key files:

- `daic_edaic_label_provenance.csv`
- `daic_edaic_overlap_agreement.csv`
- `identity_control_design.csv`
- `controlled_identity_by_seed.csv`
- `controlled_identity_summary.csv`
- `controlled_identity_key_results.csv`
- `report.md`
- `run_summary.json`
- `artifact_hygiene_audit.json`

## Blockers And Risks

- MV25 explains away much of the raw E-DAIC/CMDC identity score after length and
  severity controls. This is not a defect if written correctly: it prevents an
  overclaim and moves the main identity evidence to same-language controlled
  probes.
- The E-DAIC lineage probe is an ID-lineage/protocol proxy, not a fully
  randomized protocol experiment.
- CMDC/PDCH controlled identity is modest after length controls and CMDC HAMD
  supervision remains small.

## Next Handoff

Update manuscript tables/captions so:

- DAIC-WOZ/E-DAIC is a sanity-control row.
- Representation heterogeneity uses raw identity as a shortcut-risk screen and
  MV25 same-language probes as the controlled support.
- MV24 method superiority is reported within target-calibrated supervision
  budget, not as a zero-target-label full-vs-all claim.
