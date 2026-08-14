# Diagnostic Paper Bibliography Report

Generated: `2026-08-14T06:53:04+00:00`

## Decision

- Bibliography status: `ready_for_manuscript_citation_editing`.
- Source-context rows mapped: `26`.
- Unique bibliography entries: `20`.
- Unmapped source-context rows: `0`.
- Artifact hygiene passed: `True`.

Formal citation registry and BibTeX references now cover all current source-context rows; manuscript prose still needs venue-specific citation placement.

## Manuscript Citation Handoff

Use `references.bib` as the first bibliography file for the paper draft. The manuscript still needs venue-specific in-text citation formatting; this report supplies citation keys and source-context mappings.

Recommended insertion points:

- Introduction and related work: cite `gratch2014distress`, `nguyen2022improving`, `zhang2025interviewer`, `ishikawa2026comprehensive`, and `uscict2026daic` where the draft motivates dataset governance, questionnaire grounding, protocol bias, and nearby benchmark-audit positioning.
- Data Governance and Label Contracts: cite `zou2023cmdc`, `pdchrepository2026`, `cai2020modma`, `shen2022automatic`, and `fu2025mpddchallenge` where dataset roles are introduced.
- Psychometric methods: cite `samejima1969graded`, `chalmers2012mirt`, `chalmers2026mirtmultiplegroup`, `bulut2017detecting`, `galenkamp2017measurement`, `patel2019measurement`, `ma2021phqhamd`, `delamain2024measurement`, and `zhou2026depression` around invariance, IRT, DIF, PHQ/HAMD differences, and cross-scale linking.
- MPDD/personality positioning: cite `fu2026p3hf` when explaining why generic personality-aware fusion is not the paper's novelty.

## Source Context Map

| context | hint | key | status |
| --- | --- | --- | --- |
| literature_positioning:daic_lrec_2014 | Gratch et al. 2014, LREC | gratch2014distress | primary_acl_anthology |
| literature_positioning:daic_official_access | USC ICT DAIC-WOZ and Extended DAIC download page | uscict2026daic | official_dataset_page |
| literature_positioning:interviewer_bias_emnlp_2025 | Zhang and Poellabauer 2025, Findings of EMNLP | zhang2025interviewer | primary_acl_anthology |
| literature_positioning:multi_probe_audit_2026 | Ishikawa and Duke 2026, arXiv | ishikawa2026comprehensive | primary_arxiv_preprint |
| literature_positioning:questionnaire_grounding_acl_2022 | Nguyen et al. 2022, ACL | nguyen2022improving | primary_acl_anthology |
| literature_positioning:phq_hamd_irt_2021 | Ma et al. 2021, Frontiers in Psychiatry | ma2021phqhamd | primary_publisher_page |
| literature_positioning:phq9_invariance_helius_2017 | Galenkamp et al. 2017, BMC Psychiatry | galenkamp2017measurement | primary_fulltext_pmc |
| literature_positioning:phq9_measurement_invariance_us_2019 | Patel et al. 2019, Depression and Anxiety | patel2019measurement | primary_fulltext_pmc |
| literature_positioning:samejima_graded_response_1969 | Samejima 1969, Psychometrika Monograph 17 | samejima1969graded | primary_monograph_pdf |
| literature_positioning:mirt_jss_2012 | Chalmers 2012, Journal of Statistical Software | chalmers2012mirt | primary_jss_page |
| literature_positioning:mirt_multiplegroup_docs | mirt multipleGroup documentation | chalmers2026mirtmultiplegroup | official_package_documentation |
| literature_positioning:irt_lr_dif_frontiers_2017 | Bulut and Suh 2017, Frontiers in Education | bulut2017detecting | primary_publisher_page |
| literature_positioning:phq_dif_jad_2024 | Delamain et al. 2024, Journal of Affective Disorders | delamain2024measurement | pubmed_and_publisher_metadata |
| literature_positioning:scale_linking_jclinepi_2026 | Zhou et al. 2026, Journal of Clinical Epidemiology | zhou2026depression | publisher_and_pubmed_metadata |
| literature_positioning:mpdd_challenge_2025 | Fu et al. 2025, ACM MM Challenge | fu2025mpddchallenge | official_challenge_page_and_acm_metadata |
| literature_positioning:p3hf_aaai_2026 | Fu et al. 2026, AAAI | fu2026p3hf | primary_aaai_page |
| literature_positioning:pdch_dataset | PDCH dataset page | pdchrepository2026 | official_repository_page |
| source_context_data_governance:e_daic_daic | USC ICT DAIC-WOZ and Extended DAIC download page | uscict2026daic | official_dataset_page |
| source_context_data_governance:daic | Gratch et al. 2014, LREC | gratch2014distress | primary_acl_anthology |
| source_context_data_governance:cmdc | Zou et al. 2023, IEEE Transactions on Affective Computing | zou2023cmdc | doi_publisher_metadata |
| source_context_data_governance:pdch | PDCH repository and dataset paper | pdchrepository2026 | official_repository_page |
| source_context_data_governance:modma | MODMA dataset description | cai2020modma | official_dataset_page_and_arxiv_metadata |
| source_context_data_governance:eatd_corpus | EATD-Corpus repository | shen2022automatic | primary_arxiv_and_ieee_metadata |
| source_context_data_governance:mpdd | MPDD Challenge official page | fu2025mpddchallenge | official_challenge_page_and_acm_metadata |
| source_context_data_governance:phq_hamd_measurement | Ma et al. 2021, Frontiers in Psychiatry | ma2021phqhamd | primary_publisher_page |
| source_context_data_governance:phq_measurement_invariance | Delamain et al. 2024, Journal of Affective Disorders | delamain2024measurement | pubmed_and_publisher_metadata |

## Bibliography Entries Used By Source Context

| key | year | title | contexts |
| --- | --- | --- | --- |
| bulut2017detecting | 2017 | Detecting Multidimensional Differential Item Functioning with the Multiple Indicators Multiple Causes Model, the Item Response Theory Likelihood Ratio Test, and Logistic Regression | 1 |
| cai2020modma | 2020 | A Multi-modal Open Dataset for Mental-disorder Analysis | 1 |
| chalmers2012mirt | 2012 | {mirt}: A Multidimensional Item Response Theory Package for the {R} Environment | 1 |
| chalmers2026mirtmultiplegroup | 2026 | {multipleGroup}: Multiple Group Estimation | 1 |
| delamain2024measurement | 2024 | Measurement Invariance and Differential Item Functioning of the {PHQ-9} and {GAD-7} in a Large Primary Care Sample | 2 |
| fu2025mpddchallenge | 2025 | The First Multimodal Personality-aware Depression Detection Challenge | 2 |
| fu2026p3hf | 2026 | {P3HF}: Exploring Potential Personality and Psychological Traits from Writing Patterns in Handwritten Text for AI-assisted Depression Detection | 1 |
| galenkamp2017measurement | 2017 | Measurement Invariance Testing of the {PHQ-9} in a Multi-Ethnic Population in Europe: The {HELIUS} Study | 1 |
| gratch2014distress | 2014 | The Distress Analysis Interview Corpus of Human and Computer Interviews | 2 |
| ishikawa2026comprehensive | 2026 | Comprehensive Benchmarking of Machine Learning Models for Multimodal Depression Detection | 1 |
| ma2021phqhamd | 2021 | The Patient Health Questionnaire-9 vs. the Hamilton Rating Scale for Depression in Assessing Major Depressive Disorder | 2 |
| nguyen2022improving | 2022 | Improving the Generalizability of Depression Detection by Leveraging Clinical Questionnaires | 1 |
| patel2019measurement | 2019 | Measurement Invariance of the Patient Health Questionnaire-9 ({PHQ-9}) Depression Screener in U.S. Adults Across Sex, Race/Ethnicity, and Education Level: {NHANES} 2005-2016 | 1 |
| pdchrepository2026 | 2026 | {PDCH}: A Real-world Depression Consultation Dataset | 2 |
| samejima1969graded | 1969 | Estimation of Latent Ability Using a Response Pattern of Graded Scores | 1 |
| shen2022automatic | 2022 | Automatic Depression Detection: An Emotional Audio-Textual Corpus and a {GRU/BiLSTM}-based Model | 1 |
| uscict2026daic | 2026 | {DAIC-WOZ} and Extended {DAIC} Download Page | 2 |
| zhang2025interviewer | 2025 | What if the Interviewer Asks Different Questions? Evaluating Interviewer Bias in Depression Detection Models | 1 |
| zhou2026depression | 2026 | Depression Rating Scales Demonstrate Significant Correlations but Systematic Differences: A Multicenter Prospective Cohort Study Using Equipercentile Linking | 1 |
| zou2023cmdc | 2023 | Semi-structural Interview-based Chinese Multimodal Depression Corpus Towards Automatic Preliminary Screening of Depressive Disorders | 1 |

## Outputs

- `bibliography_artifact_hygiene_audit.json`
- `bibliography_report.md`
- `bibliography_run_summary.json`
- `citation_registry.csv`
- `citation_source_map.csv`
- `references.bib`

## Regeneration

```bash
python scripts/build_diagnostic_paper_claim_tables.py
python scripts/build_diagnostic_paper_data_governance_section.py
python scripts/build_diagnostic_paper_bibliography.py
python scripts/build_diagnostic_paper_manuscript_draft.py
```
