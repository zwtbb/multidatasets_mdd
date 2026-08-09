# P5_MV02 HAMD Bridge Readiness Audit

Generated: `2026-08-09T05:16:56+00:00`

## Scope

This audit checks whether `P5_MV02 hamd17_auxiliary_bridge` can start from the current manifests and cached frozen features. It does not train a model and does not write subject-level labels, raw text, media paths, embeddings, or predictions.

## Label Coverage

| dataset | manifest subjects | HAMD total subjects | full HAMD-17 item subjects | total + full item subjects | HAMD code-9 subjects | scored item-sum mismatch subjects |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cmdc | 78 | 25 | 25 | 25 | 0 | 0 |
| pdch | 100 | 99 | 99 | 99 | 7 | 0 |

## Item-Total Consistency

| dataset | comparable subjects | raw item-sum matches | scored item-sum matches | raw delta summary | scored delta summary |
| --- | ---: | ---: | ---: | --- | --- |
| cmdc | 25 | 25 | 25 | {"0.0": 25} | {"0.0": 25} |
| pdch | 99 | 92 | 99 | {"0.0": 92, "9.0": 7} | {"0.0": 99} |

## Reusable Feature Availability

| dataset | feature family | exists | label subjects joined | model-input columns |
| --- | --- | --- | ---: | ---: |
| pdch | text_bge_subject | true | 99 | 512 |
| pdch | audio_wavlm_subject | true | 99 | 768 |
| pdch | audio_egemaps_subject | true | 99 | 352 |
| cmdc | text_bge_subject | true | 25 | 512 |
| cmdc | audio_wavlm_subject | true | 25 | 768 |
| cmdc | audio_egemaps_subject | true | 25 | 352 |

## Decision

- MV02 readiness status: `ready_pdch_only_mode`.
- Recommended first mode: `pdch_only_subject_level_hamd17_auxiliary_bridge`.
- CMDC HAMD use: `small_aligned_25_subject_external_sanity_check_only`.
- PDCH total target policy: `use_manifest_hamd17_total_and_official_9_excluded_scoring`.
- Full-method allowed by this audit: `false`.

PDCH has the only adequately sized HAMD-17 item+total supervision for the first MV02 run. CMDC HAMD is aligned after filtering placeholder item payloads, but it covers only 25 subjects and should be held for a small external sanity check or reported as limited, not used as a broad joint HAMD bridge claim.

Seven PDCH subjects contain HAMD item code `9`, which the official evaluation code treats as not sure/not applicable and excludes from total scoring. Their raw item sums are therefore `+9.0` above the manifest total, but scored item sums match after applying the official `9 -> 0 for total` convention. MV02 should use the manifest HAMD total as the primary severity target and apply the same official scoring convention when deriving totals from item heads.
