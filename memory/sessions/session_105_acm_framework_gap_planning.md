# Session Memory: ACM Framework Gap Planning

Status: complete
Last updated: 2026-09-03 UTC
Thread/task: main-agent ACM framework positioning and future-gap planning

## Scope

This session owns the response to the user's venue/style and positioning
decisions, plus a literature-grounded plan for what future research gaps to
continue pursuing. It does not run new experiments, change manuscript content,
sync Feishu, or reintroduce MV27.

## Current State

- User confirmed ACM-style requirements as the working submission format target.
- User prefers a higher-value `Framework` positioning over a narrow method/SOTA
  architecture paper.
- User decided MV27's four-domain binary negative result can stay out of the
  main paper.
- The referenced review advice supports reframing the paper as a
  measurement-aware benchmark-validity audit plus calibrated cross-corpus
  transfer framework, with the neural measurement-aware architecture presented
  as a constructive instantiation rather than the central claim.
- Web/literature scan checked current nearby work: questionnaire-grounded
  depression detection, medical/LLM benchmark construct validity, clinical
  interview benchmark/protocol-bias audits, cross-domain/missing-modality MDD
  frameworks, MPDD personalized depression detection, DIF tooling, and clinical
  calibration guidance.

## Key Decisions

- Recommended paper positioning: ACM-style framework / benchmark-validity study:
  `target contracts can differ -> the differences can be audited -> calibrated
  transfer must separate representation adaptation from measurement modeling`.
- Do not claim corpus-specific ordinal heads are the independent performance
  source. Current robust RQ3 claim remains target calibration plus shared-layer
  adaptation; ordinal measurement modeling is competitive and direction
  dependent.
- Most valuable next work should target reviewer-visible gaps rather than chase
  an average-MAE win: target-only and label-budget controls, repeated-split /
  participant-bootstrap uncertainty, RQ2 DIF/anchor sensitivity with parameter
  uncertainty, and a concise ACM manuscript rewrite.
- MV27 remains local-only and omitted from the main paper.

## Files Owned Or Touched

- `/root/autodl-tmp/MEMORY.md`
- `/root/autodl-tmp/memory/ACTIVE_HANDOFF.md`
- `/root/autodl-tmp/memory/sessions/session_104_remote_github_cleanup.md`
- `/root/autodl-tmp/memory/sessions/session_105_acm_framework_gap_planning.md`

## Generated Artifacts

No experiment artifacts were generated.

Primary external sources checked:

- Nguyen et al., ACL 2022, questionnaire-grounded depression detection:
  `https://aclanthology.org/2022.acl-long.578/`
- Alaa et al., ICML 2025, medical LLM benchmark construct validity:
  `https://proceedings.mlr.press/v267/alaa25a.html`
- Bean et al., NeurIPS 2025 Datasets and Benchmarks / arXiv, LLM benchmark
  construct validity: `https://arxiv.org/abs/2511.04703`
- Ishikawa and Duke, 2026 clinical-interview depression benchmark audit:
  `https://arxiv.org/abs/2605.23977`
- Watawana et al., 2026 interviewer effects in semi-structured clinical
  interviews: `https://arxiv.org/html/2603.24651v1`
- Chen et al., 2026 SCD-MLLM cross-domain/missing-modality depression
  recognition: `https://arxiv.org/abs/2512.06447`
- MPDD 2025 Challenge: `https://hacilab.github.io/MPDDChallenge.github.io/`
- Choi et al., JSS 2011 `lordif` DIF package:
  `https://www.jstatsoft.org/v39/i08/`
- Van Calster et al., BMC Medicine 2019 clinical prediction calibration:
  `https://link.springer.com/article/10.1186/s12916-019-1466-7`
- ACM author submissions page:
  `https://www.acm.org/publications/authors/submissions`

## Blockers And Risks

- Exact ACM venue/track is still unspecified, so use general ACM/acmart
  manuscript-review conventions until the target call for papers is chosen.
- RQ2 DIF localization remains finite-sample fragile; future manuscript wording
  must stay hypothesis-generating unless sensitivity/uncertainty analyses make
  it stronger.
- RQ3 architecture superiority remains unsupported as a universal claim.

## Next Handoff

Next implementation pass should prioritize:

1. target-only baseline and label-budget curve;
2. repeated-split and participant-bootstrap paired uncertainty;
3. RQ2 DIF/anchor threshold sensitivity and parameter uncertainty;
4. ACM-style Abstract/Contribution/Related Work/Discussion rewrite centered on
   the framework gap, with MV27 omitted from the main paper.
