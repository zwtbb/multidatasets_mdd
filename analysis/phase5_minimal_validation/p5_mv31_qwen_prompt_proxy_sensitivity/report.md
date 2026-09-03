# P5 MV31 Qwen3 Prompt-Proxy Sensitivity

Generated: `2026-09-03T17:10:22+00:00`

## Scope

MV31 re-embeds E-DAIC transcript variants with Qwen3-Embedding-0.6B and fits fixed Ridge/Logistic heads on the official train/dev split. It is a protocol/prompt-proxy stress test, not a participant-only or interviewer-only control.

## Feasibility

| dataset | diagnostic | status | count 1 | count 2 |
| --- | --- | --- | ---: | ---: |
| E-DAIC | speaker_resolved_controls | `blocked_no_speaker_role` | 0 | 0 |
| E-DAIC | qwen3_prompt_proxy_controls | `completed_proxy_not_speaker_resolved` | 52 | 1314 |

## Variant Coverage

| control | subjects | train | dev | retained units mean | removed units mean | chunks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `back_25` | 219 | 163 | 56 | 23.776 | 69.886 | 219 |
| `front_25` | 219 | 163 | 56 | 23.776 | 69.886 | 219 |
| `full_dialogue` | 219 | 163 | 56 | 93.662 | 0.000 | 269 |
| `middle_50` | 219 | 163 | 56 | 47.607 | 46.055 | 227 |
| `train_repeated_turns_only` | 219 | 163 | 56 | 10.804 | 82.858 | 219 |
| `train_repeated_turns_removed` | 219 | 163 | 56 | 82.858 | 10.804 | 267 |

## Primary Deltas

| task | metric | control | mean | full mean | delta vs full |
| --- | --- | --- | ---: | ---: | ---: |
| PHQ-8 regression | MAE | `front_25` | 4.957 | 4.801 | 0.156 |
| PHQ-8 regression | MAE | `full_dialogue` | 4.801 | 4.801 | 0.000 |
| PHQ-8 regression | MAE | `train_repeated_turns_only` | 4.806 | 4.801 | 0.006 |
| PHQ-8 regression | MAE | `train_repeated_turns_removed` | 4.577 | 4.801 | -0.224 |
| binary depression classification | Macro-F1 | `front_25` | 0.562 | 0.665 | -0.103 |
| binary depression classification | Macro-F1 | `full_dialogue` | 0.665 | 0.665 | 0.000 |
| binary depression classification | Macro-F1 | `train_repeated_turns_only` | 0.576 | 0.665 | -0.090 |
| binary depression classification | Macro-F1 | `train_repeated_turns_removed` | 0.614 | 0.665 | -0.051 |

## Decision

- Status: `complete_qwen3_prompt_proxy_sensitivity`.
- Speaker-resolved controls: `blocked_no_speaker_role_in_manifest_or_transcript_csv`.
- Prompt-proxy reading: `no_clear_qwen3_excess_loss_from_repeated_turn_removal`.
- Artifact hygiene passed: `True`.
