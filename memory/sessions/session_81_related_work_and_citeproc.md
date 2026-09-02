# Session Memory: related work and citeproc setup

Status: complete
Last updated: 2026-08-25 UTC
Thread/task: install pandoc-citeproc and write Related Work

## Scope

This session installs the local citation processor required by the existing
pandoc version, writes Section 2 Related Work, renumbers downstream manuscript
sections, regenerates the Word working draft with rendered author-year
citations, and fixes minor BibTeX formatting issues surfaced by citeproc.

## Current State

`pandoc-citeproc` is installed locally:

- version: `pandoc-citeproc 0.17.0.1`
- system package: Ubuntu `pandoc-citeproc`

The main manuscript now includes a four-part Related Work section:

1. Cross-domain and foundation-model depression detection.
2. Symptom-grounded and interpretable depression modeling.
3. Benchmark validity and protocol shortcuts.
4. Clinical measurement and scale comparability.

The generated Word draft now uses rendered author-year citations and includes a
References section:

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`

## Key Decisions

- Related Work is written as a positioning section, not a generic survey.
- Existing foundation/multimodal/domain-adaptation work is framed as strong and
  relevant for modeling `P_D(X | theta)`, while the paper's gap is the
  target-validity layer `P_D(Y | theta)`.
- Symptom-grounded work is presented as a precedent we extend from clinical
  interpretability to cross-corpus item-response comparability.
- Benchmark shortcut work is used to motivate the move from input/protocol
  validity to target measurement validity.
- Clinical measurement references are used sparingly to support the framework,
  without turning the paper into a pure psychometric validation manuscript.
- Minor BibTeX cleanup was applied for `Muthen` accent rendering, `U.S.`
  capitalization, and in-text display of De Duro et al.

## Files Owned Or Touched

- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx`
- `/root/autodl-tmp/analysis/diagnostic_measurement_audit_paper/references.bib`
- `/root/autodl-tmp/memory/sessions/session_81_related_work_and_citeproc.md`

## Generated Artifacts

Regenerated Word working draft with rendered citations:

```bash
pandoc --filter pandoc-citeproc \
  --bibliography=analysis/diagnostic_measurement_audit_paper/references.bib \
  analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.md \
  -o analysis/diagnostic_measurement_audit_paper/manuscript_reframed_rq_draft.docx
```

Smoke checks passed:

- all manuscript citation keys exist in `references.bib`;
- `git diff --check` passes;
- docx export renders author-year citations and a References section.

## Blockers And Risks

No writing blocker. The Word export uses the default pandoc/citeproc citation
style; venue-specific CSL can be added later when the target venue is fixed.

## Next Handoff

Next manuscript step: tighten the Framework/Methods boundary. Section 3 should
become the compact conceptual framework, while Section 5 Methods should avoid
duplicating Section 7's measurement-aware adaptation material.

