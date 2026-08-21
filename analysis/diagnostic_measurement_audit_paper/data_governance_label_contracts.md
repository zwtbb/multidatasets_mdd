# Data Governance and Label Contracts

Generated: `2026-08-21T16:14:49+00:00`

## Draft Section

This study treats cross-dataset depression detection as a measurement problem before it treats it as a model-capacity problem. The data layer is governed by a registry-first workflow: each corpus is assigned a scientific role, protocol axis, modality set, and label contract before any pooled modeling claim is considered. Raw datasets and real row-level tables remain local-only; the public repository contains scripts, schemas, synthetic examples, aggregate audits, claim gates, and paper-critical summaries.

The governed corpus currently spans `6` datasets and `891` audited subjects. Phase 4 defines `15` symptom constructs and `54` mapped scale items. Item-level supervision is available for `4` dataset-scale contracts and absent or total-only for `3` contracts. This difference is central to the paper: PHQ-8/PHQ-9 provide the cleanest C01-C08 shared bridge, PDCH provides the strongest HAMD-17 item-level clinical validation, CMDC HAMD remains a small sanity subset, and EATD/MODMA/MPDD primarily serve stress-test or context roles rather than item-level construct supervision.

The release boundary is deliberately conservative. Real identifiers, labels at row granularity, local file references, media, raw transcripts, learned parameters, embeddings, row predictions, private evidence workbooks, and verbatim evidence excerpts remain local-only. Public artifacts are limited to code, schemas, synthetic examples, aggregate audit summaries, and paper-facing tables that pass artifact hygiene. This policy preserves reproducibility of the experimental logic without redistributing licensed or privacy-sensitive material.

## Dataset Governance Summary

| dataset | role | protocol | modalities | subjects | valid rows | main label | claim role | quality note |
| --- | --- | --- | --- | ---: | ---: | --- | --- | --- |
| E-DAIC | primary_development | virtual_interview | text;audio;video | 275 | 275 | PHQ8 | E-DAIC is the primary development set | E-DAIC is the primary development set |
| CMDC | chinese_cross_protocol_language_validation | clinical_interview | text;audio;video | 78 | 908 | PHQ9_HAMD17 | Local files match the official-style layout | Metadata has duplicate/omitted subject-info entries; modality availability varies by row. |
| PDCH | hospital_consultation_hamd_validation | face_to_face_consultation | text;audio | 100 | 165 | HAMD17 | Annotation files are present | One consultation subject lacks HAMD annotation; supervised HAMD rows use labeled subset only. |
| MODMA | controlled_speech_task_stress_test | interview_reading_picture | audio | 52 | 1503 | diagnosis_or_PHQ9 | Official-style layout is present | 5 invalid audio rows are excluded; task type is a stress-test axis. |
| EATD-Corpus | chinese_valence_stress_test | positive_neutral_negative_emotion_tasks | text;audio | 162 | 486 | SDS | Use positive, neutral, and negative tasks to separate depression signal from transient emotional valence | Use positive, neutral, and negative tasks to separate depression signal from transient emotional valence |
| MPDD-AVG-2026 | individual_difference_psychomotor_validation | age_personality_gait_multimodal | audio;video;gait;personality | 224 | 602 | PHQ9 | Raw/feature layout is present | Local labels cover train subjects only; gender/health structured fields remain incomplete. |

## Label Contract Summary

| dataset | scale | total subjects | item subjects | supervision | paper boundary |
| --- | --- | ---: | ---: | --- | --- |
| E-DAIC | PHQ-8 | 275 | 219 | item_level_available | eligible for item-level minimal validation under subject-level splits |
| CMDC | PHQ-9 | 77 | 77 | item_level_available | eligible for item-level minimal validation under subject-level splits |
| CMDC | HAMD-17 | 25 | 25 | item_level_available | sanity subset only; do not claim complete CMDC HAMD supervision |
| PDCH | HAMD-17 | 99 | 99 | item_level_available | eligible for item-level minimal validation under subject-level splits |
| MODMA | PHQ-9 | 52 | 0 | total_only | use as total/severity stress or context target only; no item-level construct claim |
| EATD-Corpus | SDS | 162 | 0 | total_only | use as total/severity stress or context target only; no item-level construct claim |
| MPDD-AVG-2026 | PHQ-9 | 175 | 0 | total_only | use as total/severity stress or context target only; no item-level construct claim |

## Construct Coverage

| scale | direct | partial | secondary | absent | interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| PHQ-8 | 8 | 0 | 0 | 7 | cleanest core PHQ bridge, especially C01-C08; PHQ-9 alone includes C09 |
| PHQ-9 | 9 | 0 | 0 | 6 | cleanest core PHQ bridge, especially C01-C08; PHQ-9 alone includes C09 |
| HAMD-17 | 5 | 5 | 3 | 2 | clinician-rated HAMD includes core items plus anxiety/somatic/insight content |
| SDS | 5 | 9 | 0 | 1 | SDS is broad self-report and currently total-only in EATD; use cautiously for stress testing |

## Release Boundary

| artifact family | examples | policy | rationale |
| --- | --- | --- | --- |
| raw data and media | audio; video; raw transcripts; archives | local_only | dataset licenses, consent boundaries, and file size |
| real row-level tables | real subject manifests; real file-integrity rows; real split maps | local_only | contains identifiers, labels, or local file references |
| model internals and private review | row predictions; learned parameters; embeddings; verbatim excerpts; annotation workbooks | local_only_by_default | privacy and artifact-hygiene boundary |
| public reproducibility skeleton | scripts; registry roles; schemas; synthetic examples; aggregate audits | track_in_git | supports reproducibility without redistributing sensitive data |
| paper-critical summaries | claim gates; aggregate metric tables; hygiene audits; writing scaffolds | track_in_git_after_hygiene | needed for manuscript traceability and does not expose row-level material |

## Source Context

| dataset or topic | source role | citation hint | URL | use in section |
| --- | --- | --- | --- | --- |
| E-DAIC/DAIC | official access and consent boundary | USC ICT DAIC-WOZ and Extended DAIC download page | https://dcapswoz.ict.usc.edu/ | Supports restricted-data governance and local-only real manifest policy. |
| DAIC | clinical-interview corpus origin | Gratch et al. 2014, LREC | https://aclanthology.org/L14-1421/ | Supports the clinical-interview framing and multimodal questionnaire/transcript context. |
| CMDC | Chinese semi-structured interview corpus | Zou et al. 2023, IEEE Transactions on Affective Computing | https://doi.org/10.1109/TAFFC.2022.3181210 | Supports CMDC as Chinese clinical-interview validation with PHQ-9 and HAMD labels. |
| PDCH | real consultation and HAMD-17 source | PDCH repository and dataset paper | https://github.com/Miraclemarvel55/PDCH | Supports PDCH as a bounded HAMD-17 consultation validation dataset. |
| MODMA | controlled task stress-test source | MODMA dataset description | https://reshare.ukdataservice.ac.uk/854301/ | Supports MODMA as an interview/reading/picture-description task robustness dataset. |
| EATD-Corpus | Chinese valence stress-test source | EATD-Corpus repository | https://github.com/Fancy-Block/EATD-Corpus | Supports EATD as Chinese audio/text depression data with emotion-related tasks. |
| MPDD | individual-difference benchmark source | MPDD Challenge official page | https://hacilab.github.io/MPDDChallenge.github.io/ | Supports MPDD as the age/personality/health/gait context dataset. |
| PHQ/HAMD measurement | scale-specific psychometric motivation | Ma et al. 2021, Frontiers in Psychiatry | https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full | Supports not treating PHQ and HAMD as interchangeable raw item spaces. |
| PHQ measurement invariance | measurement invariance and DIF context | Delamain et al. 2024, Journal of Affective Disorders | https://pubmed.ncbi.nlm.nih.gov/37989437/ | Supports the label-contract framing around measurement invariance and DIF. |

## Manuscript Guardrails

- Do not describe EATD, MODMA, or MPDD as item-level construct-supervision datasets under the current manifest.
- Do not claim CMDC HAMD as a complete bridge; it is a small sanity subset.
- Do not use public tables as substitutes for the local manifest layer when running experiments.
- Re-check official dataset and scale citations before final manuscript submission.
