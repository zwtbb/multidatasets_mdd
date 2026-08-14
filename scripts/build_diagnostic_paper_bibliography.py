#!/usr/bin/env python3
"""Build a bibliography handoff from aggregate paper source-context tables.

This is a writing-prep script. It reads only public source-context tables from
the diagnostic paper directory and emits a formal BibTeX file plus citation
registry artifacts. It does not read raw datasets, row-level experiment
outputs, local annotation workbooks, private source locators, or clinical text.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "analysis" / "diagnostic_measurement_audit_paper"
DEFAULT_OUT_DIR = PAPER_DIR

LITERATURE_CSV = PAPER_DIR / "literature_positioning.csv"
DATA_GOVERNANCE_SOURCE_CSV = PAPER_DIR / "source_context_data_governance.csv"

TRACKED_FILES = [
    "bibliography_artifact_hygiene_audit.json",
    "bibliography_report.md",
    "bibliography_run_summary.json",
    "citation_registry.csv",
    "citation_source_map.csv",
    "references.bib",
]
HYGIENE_CHECKED_FILES = [
    name for name in TRACKED_FILES if name != "bibliography_artifact_hygiene_audit.json"
]


@dataclass(frozen=True)
class Reference:
    citation_key: str
    entry_type: str
    source_ids: tuple[str, ...]
    source_urls: tuple[str, ...]
    fields: dict[str, str]
    verification_status: str
    metadata_source_url: str
    notes: str


REFERENCES = [
    Reference(
        citation_key="gratch2014distress",
        entry_type="inproceedings",
        source_ids=("daic_lrec_2014",),
        source_urls=("https://aclanthology.org/L14-1421/",),
        fields={
            "author": "Jonathan Gratch and Ron Artstein and Gale M. Lucas and Giota Stratou and Stefan Scherer and Angela Nazarian and Rachel Wood and Jill Boberg and David DeVault and Stacy Marsella and David R. Traum and Skip Rizzo and Louis-Philippe Morency",
            "title": "The Distress Analysis Interview Corpus of Human and Computer Interviews",
            "booktitle": "Proceedings of the Ninth International Conference on Language Resources and Evaluation (LREC'14)",
            "year": "2014",
            "pages": "3123--3128",
            "publisher": "European Language Resources Association (ELRA)",
            "url": "https://aclanthology.org/L14-1421/",
        },
        verification_status="primary_acl_anthology",
        metadata_source_url="https://aclanthology.org/L14-1421/",
        notes="DAIC corpus origin and interview-modality citation.",
    ),
    Reference(
        citation_key="uscict2026daic",
        entry_type="misc",
        source_ids=("daic_official_access",),
        source_urls=("https://dcapswoz.ict.usc.edu/",),
        fields={
            "author": "{USC Institute for Creative Technologies}",
            "title": "{DAIC-WOZ} and Extended {DAIC} Download Page",
            "year": "2026",
            "url": "https://dcapswoz.ict.usc.edu/",
            "note": "Accessed: 2026-08-14",
        },
        verification_status="official_dataset_page",
        metadata_source_url="https://dcapswoz.ict.usc.edu/",
        notes="Use for restricted-access and release-boundary wording.",
    ),
    Reference(
        citation_key="zhang2025interviewer",
        entry_type="inproceedings",
        source_ids=("interviewer_bias_emnlp_2025",),
        source_urls=("https://aclanthology.org/2025.findings-emnlp.650/",),
        fields={
            "author": "Xiaohua Zhang and Christian Poellabauer",
            "title": "What if the Interviewer Asks Different Questions? Evaluating Interviewer Bias in Depression Detection Models",
            "booktitle": "Findings of the Association for Computational Linguistics: EMNLP 2025",
            "year": "2025",
            "pages": "11943--11964",
            "publisher": "Association for Computational Linguistics",
            "url": "https://aclanthology.org/2025.findings-emnlp.650/",
        },
        verification_status="primary_acl_anthology",
        metadata_source_url="https://aclanthology.org/2025.findings-emnlp.650/",
        notes="Protocol and interviewer-bias positioning source.",
    ),
    Reference(
        citation_key="ishikawa2026comprehensive",
        entry_type="misc",
        source_ids=("multi_probe_audit_2026",),
        source_urls=("https://arxiv.org/abs/2605.23977",),
        fields={
            "author": "Harry Ishikawa and Brendan Duke",
            "title": "Comprehensive Benchmarking of Machine Learning Models for Multimodal Depression Detection",
            "year": "2026",
            "eprint": "2605.23977",
            "archivePrefix": "arXiv",
            "primaryClass": "cs.LG",
            "url": "https://arxiv.org/abs/2605.23977",
        },
        verification_status="primary_arxiv_preprint",
        metadata_source_url="https://arxiv.org/abs/2605.23977",
        notes="Nearby benchmark-audit positioning source; cite as preprint.",
    ),
    Reference(
        citation_key="nguyen2022improving",
        entry_type="inproceedings",
        source_ids=("questionnaire_grounding_acl_2022",),
        source_urls=("https://aclanthology.org/2022.acl-long.578/",),
        fields={
            "author": "Thong Nguyen and Andrew Yates and Ayah Zirikly and Bart Desmet and Arman Cohan",
            "title": "Improving the Generalizability of Depression Detection by Leveraging Clinical Questionnaires",
            "booktitle": "Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)",
            "year": "2022",
            "pages": "8446--8459",
            "publisher": "Association for Computational Linguistics",
            "doi": "10.18653/v1/2022.acl-long.578",
            "url": "https://aclanthology.org/2022.acl-long.578/",
        },
        verification_status="primary_acl_anthology",
        metadata_source_url="https://aclanthology.org/2022.acl-long.578/",
        notes="Questionnaire-grounded depression detection prior.",
    ),
    Reference(
        citation_key="ma2021phqhamd",
        entry_type="article",
        source_ids=("phq_hamd_irt_2021",),
        source_urls=(
            "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        ),
        fields={
            "author": "Simeng Ma and Jing Yang and Baofeng Yang and Li Kang and Peng Wang and Nannan Zhang and Wei Wang and Xiaoyu Zong and Ying Wang and Hong Bai and Qian Guo and Li Yao and Lili Fang and Zhening Liu",
            "title": "The Patient Health Questionnaire-9 vs. the Hamilton Rating Scale for Depression in Assessing Major Depressive Disorder",
            "journal": "Frontiers in Psychiatry",
            "volume": "12",
            "pages": "747139",
            "year": "2021",
            "doi": "10.3389/fpsyt.2021.747139",
            "url": "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        },
        verification_status="primary_publisher_page",
        metadata_source_url="https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2021.747139/full",
        notes="Scale-specific PHQ/HAMD psychometric motivation.",
    ),
    Reference(
        citation_key="galenkamp2017measurement",
        entry_type="article",
        source_ids=("phq9_invariance_helius_2017",),
        source_urls=("https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",),
        fields={
            "author": "Henrike Galenkamp and Karien Stronks and Marieke B. Snijder and Eske M. Derks",
            "title": "Measurement Invariance Testing of the {PHQ-9} in a Multi-Ethnic Population in Europe: The {HELIUS} Study",
            "journal": "BMC Psychiatry",
            "volume": "17",
            "number": "1",
            "pages": "349",
            "year": "2017",
            "doi": "10.1186/s12888-017-1506-9",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        },
        verification_status="primary_fulltext_pmc",
        metadata_source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC5655879/",
        notes="Classical PHQ-9 invariance template.",
    ),
    Reference(
        citation_key="patel2019measurement",
        entry_type="article",
        source_ids=("phq9_measurement_invariance_us_2019",),
        source_urls=("https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/",),
        fields={
            "author": "Jay S. Patel and Yena Oh and Kevin L. Rand and Wei Wu and Melissa A. Cyders and Kurt Kroenke and Jesse C. Stewart",
            "title": "Measurement Invariance of the Patient Health Questionnaire-9 ({PHQ-9}) Depression Screener in U.S. Adults Across Sex, Race/Ethnicity, and Education Level: {NHANES} 2005-2016",
            "journal": "Depression and Anxiety",
            "volume": "36",
            "number": "9",
            "pages": "813--823",
            "year": "2019",
            "doi": "10.1002/da.22940",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/",
        },
        verification_status="primary_fulltext_pmc",
        metadata_source_url="https://pmc.ncbi.nlm.nih.gov/articles/PMC6736700/",
        notes="PHQ-9 sociodemographic invariance source.",
    ),
    Reference(
        citation_key="samejima1969graded",
        entry_type="book",
        source_ids=("samejima_graded_response_1969", "samejima_graded_response_model"),
        source_urls=("https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",),
        fields={
            "author": "Fumiko Samejima",
            "title": "Estimation of Latent Ability Using a Response Pattern of Graded Scores",
            "series": "Psychometrika Monograph Supplement",
            "number": "17",
            "publisher": "Psychometric Society",
            "year": "1969",
            "url": "https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        },
        verification_status="primary_monograph_pdf",
        metadata_source_url="https://www.psychometricsociety.org/sites/main/files/file-attachments/mn17.pdf",
        notes="Ordinal graded-response model source.",
    ),
    Reference(
        citation_key="chalmers2012mirt",
        entry_type="article",
        source_ids=("mirt_jss_2012",),
        source_urls=("https://www.jstatsoft.org/article/view/v048i06",),
        fields={
            "author": "R. Philip Chalmers",
            "title": "{mirt}: A Multidimensional Item Response Theory Package for the {R} Environment",
            "journal": "Journal of Statistical Software",
            "volume": "48",
            "number": "6",
            "pages": "1--29",
            "year": "2012",
            "doi": "10.18637/jss.v048.i06",
            "url": "https://www.jstatsoft.org/article/view/v048i06",
        },
        verification_status="primary_jss_page",
        metadata_source_url="https://www.jstatsoft.org/article/view/v048i06",
        notes="External IRT runtime source.",
    ),
    Reference(
        citation_key="chalmers2026mirtmultiplegroup",
        entry_type="misc",
        source_ids=("mirt_multiplegroup_docs",),
        source_urls=("https://philchalmers.github.io/mirt/html/multipleGroup.html",),
        fields={
            "author": "R. Philip Chalmers and mirt contributors",
            "title": "{multipleGroup}: Multiple Group Estimation",
            "year": "2026",
            "url": "https://philchalmers.github.io/mirt/html/multipleGroup.html",
            "note": "mirt documentation. Accessed: 2026-08-14",
        },
        verification_status="official_package_documentation",
        metadata_source_url="https://philchalmers.github.io/mirt/html/multipleGroup.html",
        notes="Implementation documentation for MV13 multiple-group IRT workflow.",
    ),
    Reference(
        citation_key="bulut2017detecting",
        entry_type="article",
        source_ids=("irt_lr_dif_frontiers_2017", "irt_likelihood_ratio_dif"),
        source_urls=(
            "https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        ),
        fields={
            "author": "Okan Bulut and Youngsuk Suh",
            "title": "Detecting Multidimensional Differential Item Functioning with the Multiple Indicators Multiple Causes Model, the Item Response Theory Likelihood Ratio Test, and Logistic Regression",
            "journal": "Frontiers in Education",
            "volume": "2",
            "pages": "51",
            "year": "2017",
            "doi": "10.3389/feduc.2017.00051",
            "url": "https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        },
        verification_status="primary_publisher_page",
        metadata_source_url="https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2017.00051/full",
        notes="Corrects an earlier stale source hint for this URL.",
    ),
    Reference(
        citation_key="delamain2024measurement",
        entry_type="article",
        source_ids=("phq_dif_jad_2024",),
        source_urls=("https://pubmed.ncbi.nlm.nih.gov/37989437/",),
        fields={
            "author": "Henry Delamain and Joshua E. J. Buckman and Joshua Stott and Ann John and Sonia Singh and Stephen Pilling and Rob Saunders",
            "title": "Measurement Invariance and Differential Item Functioning of the {PHQ-9} and {GAD-7} in a Large Primary Care Sample",
            "journal": "Journal of Affective Disorders",
            "volume": "347",
            "pages": "15--22",
            "year": "2024",
            "doi": "10.1016/j.jad.2023.11.026",
            "url": "https://pubmed.ncbi.nlm.nih.gov/37989437/",
        },
        verification_status="pubmed_and_publisher_metadata",
        metadata_source_url="https://pubmed.ncbi.nlm.nih.gov/37989437/",
        notes="Active clinical-measurement DIF context.",
    ),
    Reference(
        citation_key="zhou2026depression",
        entry_type="article",
        source_ids=("scale_linking_jclinepi_2026", "cross_scale_linking_jclinepi_2026"),
        source_urls=("https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",),
        fields={
            "author": "Jia Zhou and Jia Hu and Yi Zhou and Ling Zhang and Yuan Feng and Lei Xiao and Le Chen and Xu Zhou and Jingjing Meng and Linghui Meng and Gang Wang",
            "title": "Depression Rating Scales Demonstrate Significant Correlations but Systematic Differences: A Multicenter Prospective Cohort Study Using Equipercentile Linking",
            "journal": "Journal of Clinical Epidemiology",
            "volume": "194",
            "pages": "112207",
            "year": "2026",
            "doi": "10.1016/j.jclinepi.2026.112207",
            "url": "https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",
        },
        verification_status="publisher_and_pubmed_metadata",
        metadata_source_url="https://www.jclinepi.com/article/S0895-4356(26)00082-X/abstract",
        notes="Cross-scale linking and systematic scale-difference motivation.",
    ),
    Reference(
        citation_key="fu2025mpddchallenge",
        entry_type="inproceedings",
        source_ids=("mpdd_challenge_2025",),
        source_urls=("https://hacilab.github.io/MPDDChallenge.github.io/",),
        fields={
            "author": "Changzeng Fu and Zelin Fu and Qi Zhang and Xinhe Kuang and Jiacheng Dong and Kaifeng Su and Yikai Su and Wenbo Shi and Junfeng Yao and Yuliang Zhao and Shiqi Zhao and Jiadong Wang and Siyang Song and Chaoran Liu and Yuichiro Yoshikawa and Bjorn W. Schuller and Hiroshi Ishiguro",
            "title": "The First Multimodal Personality-aware Depression Detection Challenge",
            "booktitle": "Proceedings of the 33rd ACM International Conference on Multimedia",
            "year": "2025",
            "pages": "13924--13929",
            "doi": "10.1145/3746027.3762020",
            "url": "https://hacilab.github.io/MPDDChallenge.github.io/",
        },
        verification_status="official_challenge_page_and_acm_metadata",
        metadata_source_url="https://hacilab.github.io/MPDDChallenge.github.io/",
        notes="MPDD benchmark and individual-difference challenge framing.",
    ),
    Reference(
        citation_key="fu2026p3hf",
        entry_type="article",
        source_ids=("p3hf_aaai_2026",),
        source_urls=("https://ojs.aaai.org/index.php/AAAI/article/view/37159",),
        fields={
            "author": "Changzeng Fu and Shiwen Zhao and Yunze Zhang and Zhongquan Jian and Shiqi Zhao and Chaoran Liu",
            "title": "{P3HF}: Exploring Potential Personality and Psychological Traits from Writing Patterns in Handwritten Text for AI-assisted Depression Detection",
            "journal": "Proceedings of the AAAI Conference on Artificial Intelligence",
            "volume": "40",
            "number": "3",
            "pages": "1801--1809",
            "year": "2026",
            "doi": "10.1609/aaai.v40i3.37159",
            "url": "https://ojs.aaai.org/index.php/AAAI/article/view/37159",
        },
        verification_status="primary_aaai_page",
        metadata_source_url="https://ojs.aaai.org/index.php/AAAI/article/view/37159",
        notes="Personality-aware MPDD-Young method positioning source.",
    ),
    Reference(
        citation_key="pdchrepository2026",
        entry_type="misc",
        source_ids=("pdch_dataset",),
        source_urls=("https://github.com/Miraclemarvel55/PDCH",),
        fields={
            "author": "{PDCH Dataset Authors}",
            "title": "{PDCH}: A Real-world Depression Consultation Dataset",
            "year": "2026",
            "url": "https://github.com/Miraclemarvel55/PDCH",
            "note": "GitHub repository. Accessed: 2026-08-14",
        },
        verification_status="official_repository_page",
        metadata_source_url="https://github.com/Miraclemarvel55/PDCH",
        notes="Repository source for PDCH consultation/HAMD data until a final venue-specific dataset-paper citation is selected.",
    ),
    Reference(
        citation_key="zou2023cmdc",
        entry_type="article",
        source_ids=("cmdc_dataset",),
        source_urls=("https://doi.org/10.1109/TAFFC.2022.3181210",),
        fields={
            "author": "Bochao Zou and Jiali Han and Yingxue Wang and Rui Liu and Shenghui Zhao and Lei Feng and Xiangwen Lyu and Huimin Ma",
            "title": "Semi-structural Interview-based Chinese Multimodal Depression Corpus Towards Automatic Preliminary Screening of Depressive Disorders",
            "journal": "IEEE Transactions on Affective Computing",
            "volume": "14",
            "number": "4",
            "pages": "2823--2838",
            "year": "2023",
            "doi": "10.1109/TAFFC.2022.3181210",
            "url": "https://doi.org/10.1109/TAFFC.2022.3181210",
        },
        verification_status="doi_publisher_metadata",
        metadata_source_url="https://doi.org/10.1109/TAFFC.2022.3181210",
        notes="CMDC dataset citation.",
    ),
    Reference(
        citation_key="cai2020modma",
        entry_type="misc",
        source_ids=("modma_dataset",),
        source_urls=("https://reshare.ukdataservice.ac.uk/854301/",),
        fields={
            "author": "Haoyu Cai and Zhepeng Yuan and Yafeng Gao and Shaojiang Sun and Na Li and Fushuai Tian and Hongbo Xiao and Jun Li",
            "title": "A Multi-modal Open Dataset for Mental-disorder Analysis",
            "year": "2020",
            "eprint": "2002.09283",
            "archivePrefix": "arXiv",
            "primaryClass": "cs.HC",
            "url": "https://reshare.ukdataservice.ac.uk/854301/",
            "note": "Dataset page with associated MODMA citation.",
        },
        verification_status="official_dataset_page_and_arxiv_metadata",
        metadata_source_url="https://reshare.ukdataservice.ac.uk/854301/",
        notes="MODMA controlled-task dataset citation.",
    ),
    Reference(
        citation_key="shen2022automatic",
        entry_type="inproceedings",
        source_ids=("eatd_corpus",),
        source_urls=("https://github.com/Fancy-Block/EATD-Corpus", "https://arxiv.org/abs/2202.08210"),
        fields={
            "author": "Ying Shen and Huiyu Yang and Lin Lin",
            "title": "Automatic Depression Detection: An Emotional Audio-Textual Corpus and a {GRU/BiLSTM}-based Model",
            "booktitle": "ICASSP 2022 - 2022 IEEE International Conference on Acoustics, Speech and Signal Processing (ICASSP)",
            "year": "2022",
            "pages": "6247--6251",
            "doi": "10.1109/ICASSP43922.2022.9746569",
            "url": "https://arxiv.org/abs/2202.08210",
        },
        verification_status="primary_arxiv_and_ieee_metadata",
        metadata_source_url="https://arxiv.org/abs/2202.08210",
        notes="EATD-Corpus dataset citation; source table currently points to a repository mirror.",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def require_inputs() -> None:
    for path in [LITERATURE_CSV, DATA_GOVERNANCE_SOURCE_CSV]:
        if not path.exists():
            raise FileNotFoundError(path)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def md_escape(value: Any) -> str:
    return clean_text(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(rows: list[dict[str, Any]], columns: list[str], headers: list[str]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(md_escape(row[column]) for column in columns) + " |")
    return lines


def normalize_url(url: str) -> str:
    text = clean_text(url)
    if text.endswith("/"):
        text = text[:-1]
    return text.lower()


def slug(text: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return result or "source"


def reference_indexes() -> tuple[dict[str, Reference], dict[str, Reference]]:
    by_source_id: dict[str, Reference] = {}
    by_url: dict[str, Reference] = {}
    for ref in REFERENCES:
        for source_id in ref.source_ids:
            by_source_id[source_id] = ref
        for url in ref.source_urls:
            by_url[normalize_url(url)] = ref
    return by_source_id, by_url


def load_context_rows() -> list[dict[str, str]]:
    literature = pd.read_csv(LITERATURE_CSV)
    governance = pd.read_csv(DATA_GOVERNANCE_SOURCE_CSV)
    rows: list[dict[str, str]] = []
    for _, row in literature.iterrows():
        rows.append(
            {
                "context_table": "literature_positioning",
                "context_id": clean_text(row["source_id"]),
                "topic_or_scope": clean_text(row["topic"]),
                "citation_hint": clean_text(row["citation_hint"]),
                "source_url": clean_text(row["url"]),
                "use_in_paper": clean_text(row["paper_positioning"]),
            }
        )
    for _, row in governance.iterrows():
        rows.append(
            {
                "context_table": "source_context_data_governance",
                "context_id": slug(clean_text(row["dataset_or_topic"])),
                "topic_or_scope": clean_text(row["source_role"]),
                "citation_hint": clean_text(row["citation_hint"]),
                "source_url": clean_text(row["url"]),
                "use_in_paper": clean_text(row["use_in_section"]),
            }
        )
    return rows


def match_reference(row: dict[str, str], by_source_id: dict[str, Reference], by_url: dict[str, Reference]) -> Reference:
    context_id = row["context_id"]
    url = normalize_url(row["source_url"])
    if context_id in by_source_id:
        return by_source_id[context_id]
    if url in by_url:
        return by_url[url]
    raise KeyError(f"unmapped source context row: {row['context_table']}:{context_id}:{row['source_url']}")


def build_source_map(context_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_source_id, by_url = reference_indexes()
    mapped: list[dict[str, str]] = []
    for row in context_rows:
        ref = match_reference(row, by_source_id, by_url)
        mapped.append(
            {
                **row,
                "citation_key": ref.citation_key,
                "bib_entry_type": ref.entry_type,
                "verification_status": ref.verification_status,
                "metadata_source_url": ref.metadata_source_url,
            }
        )
    return mapped


def context_summary(source_map: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in source_map:
        key = row["citation_key"]
        if key not in result:
            result[key] = {
                "context_count": 0,
                "context_tables": set(),
                "context_ids": [],
                "source_urls": set(),
            }
        result[key]["context_count"] += 1
        result[key]["context_tables"].add(row["context_table"])
        result[key]["context_ids"].append(row["context_id"])
        result[key]["source_urls"].add(row["source_url"])
    return result


def build_registry(source_map: list[dict[str, str]]) -> list[dict[str, str]]:
    summary = context_summary(source_map)
    rows: list[dict[str, str]] = []
    for ref in sorted(REFERENCES, key=lambda item: item.citation_key):
        fields = ref.fields
        usage = summary.get(
            ref.citation_key,
            {"context_count": 0, "context_tables": set(), "context_ids": [], "source_urls": set()},
        )
        rows.append(
            {
                "citation_key": ref.citation_key,
                "entry_type": ref.entry_type,
                "authors": fields.get("author", ""),
                "year": fields.get("year", ""),
                "title": fields.get("title", ""),
                "venue": fields.get("journal", fields.get("booktitle", fields.get("publisher", ""))),
                "doi": fields.get("doi", ""),
                "url": fields.get("url", ""),
                "verification_status": ref.verification_status,
                "metadata_source_url": ref.metadata_source_url,
                "source_context_count": str(usage["context_count"]),
                "source_context_tables": ";".join(sorted(usage["context_tables"])),
                "source_context_ids": ";".join(usage["context_ids"]),
                "source_urls_in_context": ";".join(sorted(usage["source_urls"])),
                "notes": ref.notes,
            }
        )
    return rows


def bib_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("\n", " ")
    return escaped


def write_bibtex(path: Path, refs: list[Reference]) -> None:
    field_order = [
        "author",
        "title",
        "journal",
        "booktitle",
        "series",
        "volume",
        "number",
        "pages",
        "publisher",
        "year",
        "doi",
        "eprint",
        "archivePrefix",
        "primaryClass",
        "url",
        "note",
    ]
    lines: list[str] = []
    for ref in sorted(refs, key=lambda item: item.citation_key):
        lines.append(f"@{ref.entry_type}{{{ref.citation_key},")
        for field in field_order:
            value = ref.fields.get(field)
            if value:
                lines.append(f"  {field} = {{{bib_value(value)}}},")
        lines.append("}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    out_dir: Path,
    run_summary: dict[str, Any],
    registry: list[dict[str, str]],
    source_map: list[dict[str, str]],
) -> None:
    used_rows = [row for row in registry if int(row["source_context_count"]) > 0]
    unused_rows = [row for row in registry if int(row["source_context_count"]) == 0]
    lines = [
        "# Diagnostic Paper Bibliography Report",
        "",
        f"Generated: `{run_summary['generated_at']}`",
        "",
        "## Decision",
        "",
        f"- Bibliography status: `{run_summary['decision']['bibliography_status']}`.",
        f"- Source-context rows mapped: `{run_summary['outputs']['source_context_rows']}`.",
        f"- Unique bibliography entries: `{run_summary['outputs']['reference_rows']}`.",
        f"- Unmapped source-context rows: `{run_summary['outputs']['unmapped_source_context_rows']}`.",
        f"- Artifact hygiene passed: `{run_summary['artifact_hygiene_passed']}`.",
        "",
        run_summary["decision"]["short_read"],
        "",
        "## Manuscript Citation Handoff",
        "",
        "Use `references.bib` as the first bibliography file for the paper draft. The manuscript still needs venue-specific in-text citation formatting; this report supplies citation keys and source-context mappings.",
        "",
        "Recommended insertion points:",
        "",
        "- Introduction and related work: cite `gratch2014distress`, `nguyen2022improving`, `zhang2025interviewer`, `ishikawa2026comprehensive`, and `uscict2026daic` where the draft motivates dataset governance, questionnaire grounding, protocol bias, and nearby benchmark-audit positioning.",
        "- Data Governance and Label Contracts: cite `zou2023cmdc`, `pdchrepository2026`, `cai2020modma`, `shen2022automatic`, and `fu2025mpddchallenge` where dataset roles are introduced.",
        "- Psychometric methods: cite `samejima1969graded`, `chalmers2012mirt`, `chalmers2026mirtmultiplegroup`, `bulut2017detecting`, `galenkamp2017measurement`, `patel2019measurement`, `ma2021phqhamd`, `delamain2024measurement`, and `zhou2026depression` around invariance, IRT, DIF, PHQ/HAMD differences, and cross-scale linking.",
        "- MPDD/personality positioning: cite `fu2026p3hf` when explaining why generic personality-aware fusion is not the paper's novelty.",
        "",
        "## Source Context Map",
        "",
    ]
    preview = [
        {
            "context": f"{row['context_table']}:{row['context_id']}",
            "hint": row["citation_hint"],
            "citation_key": row["citation_key"],
            "status": row["verification_status"],
        }
        for row in source_map
    ]
    lines.extend(markdown_table(preview, ["context", "hint", "citation_key", "status"], ["context", "hint", "key", "status"]))
    lines.extend(
        [
            "",
            "## Bibliography Entries Used By Source Context",
            "",
        ]
    )
    used_preview = [
        {
            "citation_key": row["citation_key"],
            "year": row["year"],
            "title": row["title"],
            "contexts": row["source_context_count"],
        }
        for row in used_rows
    ]
    lines.extend(markdown_table(used_preview, ["citation_key", "year", "title", "contexts"], ["key", "year", "title", "contexts"]))
    if unused_rows:
        lines.extend(
            [
                "",
                "## Registry Entries Not Yet Used By Source Context",
                "",
                "These are available for future paper edits but are not currently referenced by the source-context tables.",
                "",
            ]
        )
        unused_preview = [
            {"citation_key": row["citation_key"], "year": row["year"], "title": row["title"]}
            for row in unused_rows
        ]
        lines.extend(markdown_table(unused_preview, ["citation_key", "year", "title"], ["key", "year", "title"]))
    lines.extend(
        [
            "",
            "## Outputs",
            "",
        ]
    )
    for item in run_summary["outputs"]["tracked_outputs"]:
        lines.append(f"- `{item}`")
    lines.extend(
        [
            "",
            "## Regeneration",
            "",
            "```bash",
            "python scripts/build_diagnostic_paper_claim_tables.py",
            "python scripts/build_diagnostic_paper_data_governance_section.py",
            "python scripts/build_diagnostic_paper_bibliography.py",
            "python scripts/build_diagnostic_paper_manuscript_draft.py",
            "```",
        ]
    )
    (out_dir / "bibliography_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_hygiene(out_dir: Path) -> dict[str, Any]:
    forbidden_patterns = [
        r"/root/",
        r"/autodl-tmp/",
        r"\bsubject_id\b",
        r"\btext_path\b",
        r"\baudio_path\b",
        r"\bvideo_path\b",
        r"\bgait_path\b",
        r"\.wav\b",
        r"\.mp4\b",
        r"\.avi\b",
        r"local_annotation_workbook",
        r"local_text_locators_json",
        r"local_excerpt",
        r"local_notes",
        r"p5_mv[0-9a-z_]*_local_",
        r"raw snippet",
        r"912849287",
        r"zwt912849287",
        r"github_pat_",
        r"ghp_",
    ]
    violations: list[dict[str, str]] = []
    checked = 0
    for name in HYGIENE_CHECKED_FILES:
        path = out_dir / name
        if not path.exists():
            violations.append({"file": name, "pattern": "missing_tracked_output"})
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in forbidden_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                violations.append({"file": name, "pattern": pattern})
    return {
        "artifact_hygiene_passed": not violations,
        "audit_id": "diagnostic_paper_bibliography_hygiene",
        "files_checked": checked,
        "generated_at": utc_now(),
        "violation_count": len(violations),
        "violations": violations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    require_inputs()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_at = utc_now()

    context_rows = load_context_rows()
    source_map = build_source_map(context_rows)
    registry = build_registry(source_map)

    write_bibtex(out_dir / "references.bib", REFERENCES)
    write_csv(out_dir / "citation_source_map.csv", source_map)
    write_csv(out_dir / "citation_registry.csv", registry)

    unmapped_count = 0
    used_reference_count = sum(1 for row in registry if int(row["source_context_count"]) > 0)
    run_summary = {
        "artifact_hygiene_passed": False,
        "decision": {
            "bibliography_status": "ready_for_manuscript_citation_editing",
            "short_read": "Formal citation registry and BibTeX references now cover all current source-context rows; manuscript prose still needs venue-specific citation placement.",
        },
        "generated_at": generated_at,
        "input_contract": {
            "aggregate_source_context_tables_read": True,
            "private_review_material_read": False,
            "raw_data_scanned": False,
            "row_level_outputs_read": False,
        },
        "outputs": {
            "reference_rows": len(registry),
            "source_context_rows": len(source_map),
            "source_context_references_used": used_reference_count,
            "tracked_outputs": TRACKED_FILES,
            "unmapped_source_context_rows": unmapped_count,
        },
        "run_id": "diagnostic_paper_bibliography",
        "source_artifacts": {
            "data_governance_sources": rel(DATA_GOVERNANCE_SOURCE_CSV),
            "literature_positioning": rel(LITERATURE_CSV),
        },
        "status": "complete",
    }
    (out_dir / "bibliography_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, registry, source_map)
    hygiene = artifact_hygiene(out_dir)
    run_summary["artifact_hygiene_passed"] = bool(hygiene["artifact_hygiene_passed"])
    (out_dir / "bibliography_run_summary.json").write_text(
        json.dumps(run_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, run_summary, registry, source_map)
    (out_dir / "bibliography_artifact_hygiene_audit.json").write_text(
        json.dumps(hygiene, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not hygiene["artifact_hygiene_passed"]:
        raise SystemExit("artifact hygiene violations found; see bibliography_artifact_hygiene_audit.json")
    print(
        json.dumps(
            {
                "artifact_hygiene_passed": run_summary["artifact_hygiene_passed"],
                "bibliography_status": run_summary["decision"]["bibliography_status"],
                "out_dir": rel(out_dir),
                "reference_rows": len(registry),
                "source_context_rows": len(source_map),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
