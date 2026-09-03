# Figure and Table Integration Guide

Last updated: 2026-08-29 UTC

## Writing Templates Being Followed

The figure layout follows the selected writing templates:

- Nguyen et al. ACL 2022: keep the clinical symptom layer visible rather than
  treating depression as an opaque label.
- Chen et al. Pattern Recognition 2026 / SCD-MLLM: acknowledge the
  foundation-era multimodal setting, but do not turn the paper into a generic
  fusion leaderboard.
- Zhang and Poellabauer Findings EMNLP 2025: use benchmark-validity evidence
  to motivate a constructive modeling component.

The visual strategy is therefore: one overview figure, one dataset/role map,
three evidence figures for the validity gates, and one prediction tradeoff
figure. Avoid making the main text look like a log of every experiment.

## Main-Text Figures

### Figure 1: Hand-Drawn Overview

You can replace the current temporary programmatic Figure 1 with a hand-drawn
total figure. It should contain five blocks:

1. Depression corpora and acquisition differences:
   E-DAIC, DAIC-WOZ, CMDC, PDCH, MODMA, EATD, MPDD.
2. Two mechanisms:
   representation/acquisition mechanism `P_D(X | theta)` and measurement
   mechanism `P_D(Y | theta)`.
3. Measurement-discrepancy contrasts:
   DAIC-WOZ/E-DAIC same-lineage control, E-DAIC/CMDC PHQ shared symptoms,
   and CMDC/PDCH exploratory same-HAMD view.
4. Measurement-aware model path:
   foundation encoder -> shared depression representation -> latent symptom
   layer -> corpus-specific measurement head -> PHQ/HAMD reconstruction.
5. Three gates:
   representation gate, measurement gate, prediction gate.

Suggested visual style: left-to-right pipeline with the measurement mechanism
drawn as a separate lower branch, not as a small note. The main visual contrast
should be between "align representations" and "validate target." Keep the
handwritten conclusion close to: "before aligning representations, validate
the target."

### Figure 2: Dataset Relationship Map

Use the generated map to establish corpus roles. This figure prevents reviewer
confusion about DAIC-WOZ/E-DAIC and makes the six-plus-one design legible.

### Figure 3: Raw-to-Controlled Representation Identity Probe

Use as the RQ1 figure. It is stronger than the raw heatmap because it shows
what remains after length and severity residualization. The key story is that
E-DAIC/CMDC drops near chance after controls, while same-lineage DAIC identity
remains high under Qwen3 text and WavLM audio. This keeps RQ1 useful without
letting a raw 1.000 identity number look like a language-only result.

### Figure 4: PHQ Shared-Item Analysis

Use as the RQ2 item-level figure. It visualizes shared item means and
severity-conditioned endorsement for C02/C06 without overclaiming formal DIF.

### Figure 5: Measurement-Discrepancy Contrasts

Use as the RQ2 contrast figure. It connects DAIC-WOZ/E-DAIC, E-DAIC/CMDC, and
CMDC/PDCH into one visual story, but the caption should say "graded empirical
pattern" or "contrasts," not a causal or strictly monotonic gradient.

### Figure 6: Latent-Target Prediction Tradeoff

Use as the RQ3 figure. It shows why output-level target harmonization is useful
but not enough by itself.

## Supplement / Backup Figures

- Supplementary Figure S2 (`fig3_representation_identity_heatmap`) keeps the
  full raw identity matrix. It should not be the primary RQ1 visual.
- Figure 7 (`fig7_evidence_summary`) is useful as a discussion or supplement
  figure, but it is not currently inserted into the main manuscript. The main
  text already says the claim boundary clearly, so adding this figure to the
  main text may feel repetitive.

## Main Tables

### Table 1: Dataset Roles

Placed in Section 4. It defines each corpus as an analytical role rather than
as a pooled dataset member.

### Table 2: Validity Gate Summary

Placed at the start of Section 6. It gives reviewers a compact map from gates
to evidence to modeling implication.

### Table 3: Supervision-Aware Main Result

Placed in Section 6.3. Keep zero-target-label baselines and target-calibrated
rows visually separated. The fair claim is now bounded: the frozen
corpus-specific-head ablation is a weak legacy comparator, and MV28 target-only
repeated-split audits show that target-label calibration regime, not
corpus-specific ordinal parameterization, is the robust factor. Do not write
Table 3 as a zero-target-label win or as a measurement-aware superiority table.

### Table 4: Secondary Clinical Endpoint

Placed after Table 3. Use it to connect with MDD detection literature and to
show direction asymmetry. Keep Macro Item MAE and binned item calibration MAE
as the primary evidence.

## Regeneration

Programmatic figures are generated from aggregate artifacts with:

```bash
python scripts/build_paper_core7_figures.py
```

The Word draft is regenerated with:

```bash
pandoc --filter pandoc-citeproc --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx
```
