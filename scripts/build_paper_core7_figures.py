#!/usr/bin/env python3
"""Build the seven core manuscript figures from aggregate project artifacts."""

from __future__ import annotations

import ast
import csv
import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

try:
    import yaml
except ImportError:  # pragma: no cover - local environment has PyYAML.
    yaml = None


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis/diagnostic_measurement_audit_paper/figures_core7"
PHASE3_ID = ROOT / "analysis/phase3_diagnostics/dataset_identity_probe/probe_metric_summary.csv"
MV21 = ROOT / "analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient"
MV25 = ROOT / "analysis/phase5_minimal_validation/p5_mv25_provenance_controlled_identity"
MV17A = ROOT / "analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract"
MV16 = ROOT / "analysis/phase5_minimal_validation/p5_mv16_dif_guided_calibration"

DATASET_ORDER = ["E-DAIC", "DAIC-WOZ", "CMDC", "PDCH", "MODMA", "EATD", "MPDD"]
DATASET_KEY_TO_LABEL = {
    "edaic": "E-DAIC",
    "daicwoz": "DAIC-WOZ",
    "cmdc": "CMDC",
    "pdch": "PDCH",
    "modma": "MODMA",
    "eatd": "EATD",
    "mpdd_avg_2026": "MPDD",
    "MPDD": "MPDD",
}
LANGUAGE = {
    "edaic": "English",
    "daicwoz": "English",
    "cmdc": "Chinese",
    "pdch": "Chinese",
    "modma": "Chinese",
    "eatd": "Chinese",
    "mpdd_avg_2026": "Chinese",
}

COLORS = {
    "ink": "#1f2933",
    "muted": "#697987",
    "line": "#cbd5df",
    "bg": "#f8fafc",
    "blue": "#2f6f9f",
    "blue_light": "#dceef8",
    "teal": "#2a9d8f",
    "teal_light": "#d9f2ee",
    "amber": "#d9902f",
    "amber_light": "#f7e5c5",
    "red": "#c93c4f",
    "red_light": "#f5d8dd",
    "purple": "#6d5bd0",
    "purple_light": "#e8e1f4",
    "gray": "#8a98a5",
    "gray_light": "#e8eef2",
}


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.labelsize": 10,
            "figure.dpi": 130,
            "savefig.dpi": 300,
            "svg.fonttype": "none",
            "axes.edgecolor": COLORS["line"],
            "axes.labelcolor": COLORS["ink"],
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "text.color": COLORS["ink"],
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for suffix in ("png", "svg"):
        path = OUT_DIR / f"{stem}.{suffix}"
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        if suffix == "svg":
            text = path.read_text(encoding="utf-8")
            path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")
        paths.append(path)
    plt.close(fig)
    return paths


def load_registry() -> dict:
    path = ROOT / "datasets/registry.yaml"
    if yaml is None:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_inventory() -> pd.DataFrame:
    text = (ROOT / "datasets/audit/dataset_inventory.md").read_text(encoding="utf-8")
    parsed = []
    for line in text.splitlines():
        if not line.startswith("| "):
            continue
        if line.startswith("| Dataset") or line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 8:
            parsed.append(
                {
                    "dataset": cells[0],
                    "role": cells[1],
                    "status": cells[2],
                    "subjects": int(cells[3]),
                    "sessions": int(cells[4]),
                    "segments": int(cells[5]),
                    "valid_rows": int(cells[6]),
                    "main_label": cells[7],
                    "protocol": "",
                }
            )
        elif len(cells) == 9:
            parsed.append(
                {
                    "dataset": cells[0],
                    "role": cells[1],
                    "status": cells[2],
                    "subjects": int(cells[3]),
                    "sessions": int(cells[4]),
                    "segments": int(cells[5]),
                    "valid_rows": int(cells[6]),
                    "main_label": cells[7],
                    "protocol": cells[8],
                }
            )
    return pd.DataFrame(parsed)


def wrap_text(text: str, width: int = 24) -> str:
    return textwrap.fill(text, width=width)


def add_box(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    fc: str,
    ec: str,
    fontsize: int = 10,
    weight: str = "normal",
    align: str = "center",
) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            linewidth=1.2,
            edgecolor=ec,
            facecolor=fc,
        )
    )
    ha = "center" if align == "center" else "left"
    tx = x + w / 2 if align == "center" else x + 0.02
    ax.text(tx, y + h / 2, text, ha=ha, va="center", fontsize=fontsize, weight=weight, linespacing=1.15)


def add_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = "#52606d") -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.3,
            color=color,
            shrinkA=4,
            shrinkB=4,
        )
    )


def fig1_framework_overview() -> list[Path]:
    fig, ax = plt.subplots(figsize=(12.0, 6.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.98, "Measurement-aware cross-corpus depression transfer", fontsize=15, weight="bold", va="top")
    ax.text(
        0.02,
        0.88,
        "The central object is the clinical target contract: which symptoms, response categories, raters, language, and scoring rules a corpus actually supplies.",
        fontsize=9.5,
        color=COLORS["muted"],
    )

    add_box(
        ax,
        0.04,
        0.57,
        0.20,
        0.18,
        "Corpus data $X_D$\n\ninterview transcript\nspeech signal\nvideo behavior\nprotocol context",
        COLORS["gray_light"],
        COLORS["gray"],
        fontsize=9.3,
        weight="bold",
    )
    add_box(
        ax,
        0.31,
        0.60,
        0.22,
        0.14,
        "Frozen multimodal\nfoundation representation",
        COLORS["blue_light"],
        COLORS["blue"],
        fontsize=9.7,
        weight="bold",
    )
    add_box(
        ax,
        0.63,
        0.60,
        0.23,
        0.14,
        "Shared symptom layer $S$\ncommon clinical evidence",
        COLORS["teal_light"],
        COLORS["teal"],
        fontsize=9.7,
        weight="bold",
    )
    add_box(
        ax,
        0.31,
        0.29,
        0.39,
        0.20,
        "Target contract $T_D$\nscale + item content + response categories\nrater/self-report + language + protocol\nsmall target calibration subset when available",
        COLORS["amber_light"],
        COLORS["amber"],
        fontsize=9.6,
        weight="bold",
    )
    add_box(
        ax,
        0.75,
        0.37,
        0.18,
        0.12,
        "Source corpus\nordinal head $M_s(S)$",
        "#ffffff",
        COLORS["line"],
        fontsize=9.0,
        weight="bold",
    )
    add_box(
        ax,
        0.75,
        0.18,
        0.18,
        0.12,
        "Target corpus\nordinal head $M_t(S)$",
        "#ffffff",
        COLORS["line"],
        fontsize=9.0,
        weight="bold",
    )
    add_box(
        ax,
        0.05,
        0.15,
        0.18,
        0.22,
        "Validity gates\n\nRQ1 input-side shift\nRQ2 target comparability\nRQ3 calibrated transfer",
        "#ffffff",
        COLORS["line"],
        fontsize=8.9,
        weight="bold",
    )

    add_arrow(ax, (0.24, 0.66), (0.31, 0.67), COLORS["gray"])
    add_arrow(ax, (0.53, 0.67), (0.63, 0.67), COLORS["gray"])
    add_arrow(ax, (0.74, 0.60), (0.78, 0.49), COLORS["teal"])
    add_arrow(ax, (0.74, 0.60), (0.78, 0.30), COLORS["teal"])
    add_arrow(ax, (0.70, 0.40), (0.75, 0.43), COLORS["amber"])
    add_arrow(ax, (0.70, 0.33), (0.75, 0.24), COLORS["amber"])
    add_arrow(ax, (0.23, 0.26), (0.31, 0.38), COLORS["gray"])

    ax.text(
        0.04,
        0.06,
        "Design implication: align representations only after the target contract is made visible; when thresholds differ, route shared symptom evidence through corpus-specific measurement heads.",
        color=COLORS["muted"],
        fontsize=8.8,
    )
    return save_figure(fig, "fig1_framework_overview")


def node_text(dataset_key: str, registry: dict, inventory: pd.DataFrame) -> str:
    row = inventory.loc[inventory["dataset"].eq(dataset_key)].iloc[0]
    entry = registry.get(dataset_key, {})
    label = DATASET_KEY_TO_LABEL.get(dataset_key, dataset_key.upper())
    scale = entry.get("label_type", row.get("main_label", "")).replace("_", "/")
    protocol = entry.get("protocol", row.get("protocol", "")).replace("_", " ")
    modalities = ", ".join(entry.get("modalities", []))
    return f"{label}\n{LANGUAGE.get(dataset_key, '')}\n{scale}\n{modalities}\n{int(row['subjects'])} subjects\n{protocol}"


def fig2_dataset_relationship_map() -> list[Path]:
    fig, ax = plt.subplots(figsize=(12.0, 6.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.98, "Target-contract contrasts and stress views", fontsize=15, weight="bold", va="top")
    ax.text(
        0.02,
        0.88,
        "The design separates formal target-contract contrasts from acquisition, task, and population stress views.",
        fontsize=9.3,
        color=COLORS["muted"],
    )

    add_box(
        ax,
        0.05,
        0.66,
        0.57,
        0.13,
        "L1 same-lineage PHQ-8 sanity control\nDAIC-WOZ  <->  E-DAIC\nnear-identical provenance should yield near-identical item labels",
        COLORS["teal_light"],
        COLORS["teal"],
        fontsize=9.2,
        weight="bold",
    )
    add_box(
        ax,
        0.05,
        0.45,
        0.57,
        0.14,
        "L2 primary shared-PHQ item contrast\nE-DAIC  <->  CMDC\nsame symptom family; different language, population, and setting",
        COLORS["amber_light"],
        COLORS["amber"],
        fontsize=9.2,
        weight="bold",
    )
    add_box(
        ax,
        0.05,
        0.25,
        0.57,
        0.13,
        "Exploratory same-HAMD stress view\nCMDC  <->  PDCH\nsmall aligned subset; tests whether the concern is PHQ-form specific",
        COLORS["red_light"],
        COLORS["red"],
        fontsize=9.0,
        weight="bold",
    )
    add_box(
        ax,
        0.70,
        0.36,
        0.23,
        0.33,
        "Additional stress views\n\nMODMA\nEATD\nMPDD-AVG\n\nacquisition, emotional-context,\nand population variation",
        COLORS["gray_light"],
        COLORS["gray"],
        fontsize=9.1,
        weight="bold",
    )
    ax.plot([0.64, 0.70], [0.515, 0.515], color=COLORS["gray"], linestyle="--", linewidth=1.3)
    ax.text(
        0.05,
        0.12,
        "Table 1 carries dataset sizes, modalities, and label details; this figure shows only analytical role.",
        fontsize=8.8,
        color=COLORS["muted"],
    )

    legend = [
        ("formal PHQ control", COLORS["teal"]),
        ("primary measurement contrast", COLORS["amber"]),
        ("exploratory same-scale view", COLORS["red"]),
        ("stress views", COLORS["gray"]),
    ]
    legend_pos = [(0.06, 0.05), (0.28, 0.05), (0.56, 0.05), (0.82, 0.05)]
    for (label, color), (lx, ly) in zip(legend, legend_pos):
        ax.add_patch(Rectangle((lx, ly), 0.018, 0.018, color=color))
        ax.text(lx + 0.025, ly + 0.009, label, va="center", fontsize=8.4, color=COLORS["muted"])
    return save_figure(fig, "fig2_dataset_relationship_map")


def parse_class_counts(text: str) -> list[str]:
    try:
        return list(ast.literal_eval(text).keys())
    except Exception:
        return [x for x in str(text).split(";") if x]


def fig3_representation_identity_heatmap() -> list[Path]:
    df = pd.read_csv(PHASE3_ID)
    df = df.loc[df["target_column"].eq("dataset_id")].copy()
    df["feature_label"] = df.apply(lambda r: f"{r['feature_family']} / {r['feature_space']}", axis=1)
    columns = ["E-DAIC", "DAIC-WOZ", "CMDC", "PDCH", "MODMA", "EATD", "MPDD"]
    matrix = []
    annotations = []
    for row in df.itertuples(index=False):
        covered = set(parse_class_counts(row.class_counts))
        values = []
        ann = []
        for col in columns:
            phase_label = "MPDD" if col == "MPDD" else col
            if phase_label in covered:
                values.append(float(row.balanced_accuracy))
                ann.append(f"{float(row.balanced_accuracy):.2f}")
            else:
                values.append(np.nan)
                ann.append("")
        matrix.append(values)
        annotations.append(ann)

    data = np.array(matrix)
    cmap = LinearSegmentedColormap.from_list("identity", ["#edf3f8", "#7fb8d6", "#1f5f89"])
    cmap.set_bad("#f0f3f5")

    fig, ax = plt.subplots(figsize=(11.0, 5.6))
    im = ax.imshow(data, vmin=0.5, vmax=1.0, cmap=cmap, aspect="auto")
    ax.set_xticks(np.arange(len(columns)))
    ax.set_xticklabels(columns, rotation=0)
    row_labels = [
        label.replace("wavlm", "WavLM").replace("egemaps", "eGeMAPS").replace("openface_stats", "OpenFace")
        for label in df["feature_label"]
    ]
    ax.set_yticks(np.arange(len(row_labels)))
    ax.set_yticklabels(row_labels, fontsize=8.5)
    ax.set_title("Dataset-identity probes across frozen feature spaces", loc="left", pad=16)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if annotations[i][j]:
                ax.text(j, i, annotations[i][j], ha="center", va="center", fontsize=8.5, color="white", weight="bold")
            else:
                ax.text(j, i, "-", ha="center", va="center", fontsize=8.5, color=COLORS["muted"])
    cbar = fig.colorbar(im, ax=ax, fraction=0.027, pad=0.025)
    cbar.set_label("Grouped-CV balanced accuracy")
    ax.text(
        0.0,
        -0.16,
        "Cells repeat the balanced accuracy of the dataset-identity probe covering that corpus; grey cells were not covered by the comparable feature-space contract. Dataset identifiability indicates corpus-specific signatures, not necessarily harmful shortcuts.",
        transform=ax.transAxes,
        fontsize=8.6,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig3_representation_identity_heatmap")


def fig3_controlled_identity_probe() -> list[Path]:
    df = pd.read_csv(MV25 / "controlled_identity_key_results.csv")
    order = [
        ("E-DAIC_vs_CMDC", "qwen3_text"),
        ("E-DAIC_vs_CMDC", "wavlm_audio"),
        ("E-DAIC_vs_CMDC", "openface_video_common"),
        ("E-DAIC_internal_lineage", "qwen3_text"),
        ("E-DAIC_internal_lineage", "wavlm_audio"),
        ("E-DAIC_internal_lineage", "openface_video_common"),
        ("CMDC_vs_PDCH", "qwen3_text"),
        ("CMDC_vs_PDCH", "wavlm_audio"),
    ]
    order_index = {key: idx for idx, key in enumerate(order)}
    df["order_index"] = df.apply(lambda r: order_index[(r["comparison_family"], r["view_id"])], axis=1)
    df = df.sort_values("order_index").reset_index(drop=True)

    family_labels = {
        "E-DAIC_vs_CMDC": "E-DAIC/CMDC",
        "E-DAIC_internal_lineage": "DAIC-lineage",
        "CMDC_vs_PDCH": "CMDC/PDCH",
    }
    view_labels = {
        "qwen3_text": "Qwen3 text",
        "wavlm_audio": "WavLM audio",
        "openface_video_common": "OpenFace video",
    }
    family_colors = {
        "E-DAIC_vs_CMDC": COLORS["blue"],
        "E-DAIC_internal_lineage": COLORS["teal"],
        "CMDC_vs_PDCH": COLORS["amber"],
    }

    fig, ax = plt.subplots(figsize=(11.4, 5.8))
    fig.subplots_adjust(left=0.20, right=0.98, top=0.87, bottom=0.20)
    y = np.arange(len(df))[::-1]
    ax.axvline(0.5, color=COLORS["line"], linestyle="--", linewidth=1.2)
    ax.text(0.503, -0.45, "chance", color=COLORS["muted"], fontsize=8.5, va="center")

    labels = []
    for yi, row in zip(y, df.itertuples(index=False)):
        raw = float(row.raw_balanced_accuracy_mean)
        controlled = float(row.length_severity_balanced_accuracy_mean)
        color = family_colors[row.comparison_family]
        labels.append(f"{family_labels[row.comparison_family]}\n{view_labels[row.view_id]}")
        ax.plot([raw, controlled], [yi, yi], color=color, linewidth=2.4, alpha=0.65)
        ax.scatter(raw, yi, s=42, color=COLORS["gray_light"], edgecolor=COLORS["gray"], linewidth=1.0, zorder=3)
        ax.scatter(controlled, yi, s=58, color=color, edgecolor="white", linewidth=0.8, zorder=4)
        label_x = min(controlled + 0.025, 1.01)
        ax.text(label_x, yi, f"{controlled:.3f}", va="center", fontsize=8.7, color=COLORS["ink"])

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.6)
    ax.set_xlim(0.45, 1.03)
    ax.set_xlabel("Balanced accuracy")
    ax.set_title("Control-dependent corpus identity", loc="left", pad=14)
    ax.grid(axis="x", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.scatter([], [], s=42, color=COLORS["gray_light"], edgecolor=COLORS["gray"], label="Raw probe")
    ax.scatter([], [], s=58, color=COLORS["blue"], edgecolor="white", label="Controlled probe")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.text(
        0.03,
        -0.02,
        "Controlled probes residualize length and severity inside each fold. The cross-language E-DAIC/CMDC contrast drops near chance, while same-lineage DAIC identity remains high under Qwen3 and WavLM.",
        fontsize=8.7,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig3_controlled_identity_probe")


def fig4_phq_shared_item_measurement() -> list[Path]:
    dist = pd.read_csv(MV21 / "phq_shared_item_distribution.csv")
    cond = pd.read_csv(MV21 / "phq_shared_severity_conditioned_response.csv")
    item_order = [f"C0{i}" for i in range(1, 9)]
    label_map = dist.drop_duplicates("item_id").set_index("item_id")["item_label_short"].to_dict()
    x = np.arange(len(item_order))

    fig = plt.figure(figsize=(12.5, 6.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.55, 1, 1], wspace=0.35)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])
    fig.suptitle("PHQ shared-item response patterns across E-DAIC and CMDC", x=0.03, ha="left", fontsize=15, weight="bold")

    for dataset, color, label in [("edaic", COLORS["blue"], "E-DAIC PHQ-8"), ("cmdc", COLORS["amber"], "CMDC PHQ-9")]:
        sub = dist.loc[dist["dataset"].eq(dataset)].set_index("item_id").loc[item_order]
        ax0.plot(x, sub["mean"], marker="o", linewidth=2.2, color=color, label=label)
    ax0.set_xticks(x)
    ax0.set_xticklabels(item_order, fontsize=8.4)
    ax0.set_ylabel("Mean item score")
    ax0.set_ylim(0, 1.35)
    ax0.grid(axis="y", color=COLORS["gray_light"], linewidth=0.8)
    ax0.spines[["top", "right"]].set_visible(False)
    ax0.set_title("A. Item response distribution", loc="left", fontsize=11)
    ax0.legend(frameon=False, fontsize=8.5, loc="upper right")

    def conditioned_panel(ax: plt.Axes, item: str) -> None:
        order = ["low", "middle", "high"]
        clean_label = str(label_map[item]).replace("_", "-")
        for dataset, color, label in [("edaic", COLORS["blue"], "E-DAIC"), ("cmdc", COLORS["amber"], "CMDC")]:
            sub = cond.loc[cond["dataset"].eq(dataset) & cond["item_id"].eq(item)].copy()
            sub["condition_bin"] = pd.Categorical(sub["condition_bin"], categories=order, ordered=True)
            sub = sub.sort_values("condition_bin")
            ax.plot(order, sub["p_ge_2"], marker="o", linewidth=2.0, color=color, label=label)
            for xi, yi, n in zip(range(len(order)), sub["p_ge_2"], sub["subjects"]):
                ax.text(xi, yi + 0.035, f"n={int(n)}", ha="center", fontsize=7, color=color)
        ax.set_ylim(0, 0.92)
        ax.grid(axis="y", color=COLORS["gray_light"], linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_xlabel("Item-excluded severity tertile")
        ax.set_title(f"B. {item} {clean_label}", loc="left", fontsize=11)

    conditioned_panel(ax1, "C02")
    conditioned_panel(ax2, "C06")
    ax1.set_ylabel("P(item score >= 2)")
    ax2.legend(frameon=False, fontsize=8.2, loc="upper left")
    fig.text(
        0.03,
        -0.02,
        "Item labels: C01 mood, C02 anhedonia, C03 sleep, C04 fatigue, C05 appetite, C06 self-worth, C07 concentration, C08 psychomotor. Severity conditioning uses pooled item-excluded total tertiles.",
        fontsize=8.6,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig4_phq_shared_item_measurement_analysis")


def max_non_sparse_abs_delta(path: Path, value_col: str = "item_mean_diff_left_minus_right", scope: str | None = None) -> float:
    df = pd.read_csv(path)
    if "sparse_comparison" in df:
        df = df.loc[~df["sparse_comparison"].astype(bool)].copy()
    if scope is not None and "scope" in df:
        df = df.loc[df["scope"].eq(scope)].copy()
    return float(df[value_col].abs().max())


def fig5_daicwoz_edaic_control() -> list[Path]:
    paired = pd.read_csv(MV21 / "daicwoz_edaic_paired_item_differences.csv")
    item_order = [f"C0{i}" for i in range(1, 9)]
    paired = paired.set_index("item_id").loc[item_order].reset_index()
    levels = pd.DataFrame(
        [
            {
                "level": "L1\nDAIC-WOZ/E-DAIC",
                "delta": max_non_sparse_abs_delta(MV21 / "daicwoz_edaic_conditioned_deltas.csv"),
                "color": COLORS["teal"],
            },
            {
                "level": "L2\nE-DAIC/CMDC",
                "delta": max_non_sparse_abs_delta(MV21 / "phq_shared_conditioned_deltas.csv"),
                "color": COLORS["amber"],
            },
            {
                "level": "Exploratory\nCMDC/PDCH",
                "delta": max_non_sparse_abs_delta(MV21 / "hamd_conditioned_deltas.csv", scope="all_subjects"),
                "color": COLORS["red"],
            },
        ]
    )

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(wspace=0.50)
    fig.suptitle("Same-lineage PHQ control and bounded target-contract stress views", x=0.03, ha="left", fontsize=15, weight="bold")
    ax = axes[0]
    x = np.arange(len(paired))
    ax.bar(x, paired["exact_match_rate"], color=COLORS["teal"], alpha=0.85, label="Exact match rate")
    ax.set_ylim(0.96, 1.005)
    ax.set_xticks(x)
    ax.set_xticklabels(paired["item_id"], fontsize=8.5)
    ax.set_ylabel("Paired exact-match rate")
    ax.set_title("A. Overlapping DAIC-lineage item labels", loc="left", fontsize=11)
    ax.grid(axis="y", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax2 = ax.twinx()
    ax2.plot(x, paired["mean_abs_difference"], color=COLORS["ink"], marker="o", linewidth=1.8, label="Mean abs diff")
    ax2.set_ylim(0, 0.02)
    ax2.set_ylabel("Mean abs diff")
    ax2.spines[["top"]].set_visible(False)

    ax = axes[1]
    y = np.arange(len(levels))[::-1]
    ax.barh(y, levels["delta"], color=levels["color"], height=0.45, alpha=0.88)
    ax.set_yticks(y)
    ax.set_yticklabels(levels["level"], fontsize=9.0)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Max non-sparse severity-conditioned item mean delta")
    ax.set_title("B. Target-contract contrasts", loc="left", fontsize=11)
    ax.grid(axis="x", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    for yi, val in zip(y, levels["delta"]):
        ax.text(val + 0.025, yi, f"{val:.3f}", va="center", fontsize=9)
    fig.text(
        0.03,
        -0.02,
        "The same-lineage PHQ-8 control is nearly identical. The primary shared-PHQ contrast carries the formal item-level evidence; the small same-HAMD view is exploratory context.",
        fontsize=8.7,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig5_daicwoz_edaic_controlled_comparison")


def load_encoder_summary(encoder: str, rel: str) -> pd.DataFrame:
    return pd.read_csv(MV17A / f"downstream/{encoder}/{rel}")


def fig6_latent_target_tradeoff() -> list[Path]:
    encoders = [("bge_m3", "BGE-M3"), ("multilingual_e5_base", "mE5")]
    identity_rows = []
    transfer_rows = []
    for enc, label in encoders:
        cond = load_encoder_summary(enc, "mv15_latent_conditioned_identity/conditioning_identity_summary.csv")
        mv12_id = load_encoder_summary(enc, "mv12_two_stage_latent_target/identity_probe_summary.csv")
        transfer = load_encoder_summary(enc, "mv12_two_stage_latent_target/transfer_summary.csv")
        raw = float(cond.loc[cond["ladder_id"].eq("L0_D_given_Z_raw"), "mean"].iloc[0])
        obs = float(
            mv12_id.loc[
                mv12_id["probe_id"].eq("ID2_conditional_post_mapping_identity")
                & mv12_id["model"].eq("M12a_BGE_Ridge_X_to_theta"),
                "mean",
            ].iloc[0]
        )
        theta = float(
            mv12_id.loc[
                mv12_id["probe_id"].eq("ID1_conditional_predicted_theta_identity")
                & mv12_id["model"].eq("M12a_BGE_Ridge_X_to_theta"),
                "mean",
            ].iloc[0]
        )
        identity_rows += [
            {"encoder": label, "representation": "Raw features", "ba": raw},
            {"encoder": label, "representation": "Observed item mapping", "ba": obs},
            {"encoder": label, "representation": "Latent theta", "ba": theta},
        ]
        for row in transfer.itertuples(index=False):
            direction = "CMDC -> E-DAIC" if "cmdc_to_edaic" in row.protocol else "E-DAIC -> CMDC"
            transfer_rows.append(
                {
                    "encoder": label,
                    "direction": direction,
                    "theta_delta": float(row.m12a_delta_theta_mae_vs_B0),
                    "observed_delta": float(row.m12a_delta_observed_macro_mae_vs_B3),
                }
            )
    identity = pd.DataFrame(identity_rows)
    transfer = pd.DataFrame(transfer_rows)

    fig = plt.figure(figsize=(12.0, 5.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1, 1], wspace=0.34)
    ax0, ax1, ax2 = [fig.add_subplot(gs[0, i]) for i in range(3)]
    fig.suptitle("Latent-target prediction: identity, transfer, and observed-scale metrics", x=0.03, ha="left", fontsize=15, weight="bold")

    rep_order = ["Raw features", "Observed item mapping", "Latent theta"]
    x = np.arange(len(rep_order))
    width = 0.36
    for offset, (enc, color) in zip([-width / 2, width / 2], [("BGE-M3", COLORS["blue"]), ("mE5", COLORS["teal"])]):
        vals = identity.loc[identity["encoder"].eq(enc)].set_index("representation").loc[rep_order]["ba"]
        ax0.bar(x + offset, vals, width=width, color=color, alpha=0.88, label=enc)
    ax0.axhline(0.5, color=COLORS["line"], linestyle="--", linewidth=1)
    ax0.set_xticks(x)
    ax0.set_xticklabels(["Raw\nfeatures", "Observed\nmapping", "Latent\n$\\theta$"], fontsize=8.5)
    ax0.set_ylim(0.4, 1.05)
    ax0.set_ylabel("Dataset identity BA")
    ax0.set_title("A. Identity decreases mainly at output level", loc="left", fontsize=11)
    ax0.grid(axis="y", color=COLORS["gray_light"], linewidth=0.8)
    ax0.spines[["top", "right"]].set_visible(False)
    ax0.legend(frameon=False, fontsize=8.5)

    dirs = ["CMDC -> E-DAIC", "E-DAIC -> CMDC"]
    for ax, metric, title, ylabel in [
        (ax1, "theta_delta", "B. Theta transfer vs train-mean floor", "Delta theta MAE"),
        (ax2, "observed_delta", "C. Observed-scale validity vs itemwise floor", "Delta observed macro MAE"),
    ]:
        x = np.arange(len(dirs))
        for offset, (enc, color) in zip([-width / 2, width / 2], [("BGE-M3", COLORS["blue"]), ("mE5", COLORS["teal"])]):
            vals = transfer.loc[transfer["encoder"].eq(enc)].set_index("direction").loc[dirs][metric]
            ax.bar(x + offset, vals, width=width, color=color, alpha=0.88, label=enc)
        ax.axhline(0, color=COLORS["ink"], linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(["CMDC->\nE-DAIC", "E-DAIC->\nCMDC"], fontsize=8.3)
        ax.set_title(title, loc="left", fontsize=11)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=COLORS["gray_light"], linewidth=0.8)
        ax.spines[["top", "right"]].set_visible(False)
    ax2.legend(frameon=False, fontsize=8.3)
    fig.text(
        0.03,
        -0.02,
        "Negative deltas are improvements. The stable conclusion is diagnostic: target harmonization can reduce some output-level identity, but transfer and observed-scale validity remain encoder- and direction-dependent.",
        fontsize=8.6,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig6_latent_target_tradeoff")


def fig7_evidence_summary() -> list[Path]:
    phase3 = pd.read_csv(PHASE3_ID)
    dataset_ba_min = phase3.loc[phase3["target_column"].eq("dataset_id"), "balanced_accuracy"].min()
    dataset_ba_max = phase3.loc[phase3["target_column"].eq("dataset_id"), "balanced_accuracy"].max()
    l1 = max_non_sparse_abs_delta(MV21 / "daicwoz_edaic_conditioned_deltas.csv")
    l2 = max_non_sparse_abs_delta(MV21 / "phq_shared_conditioned_deltas.csv")
    l3 = max_non_sparse_abs_delta(MV21 / "hamd_conditioned_deltas.csv", scope="all_subjects")
    m16_identity = pd.read_csv(MV16 / "output_identity_summary.csv")
    best_supported = m16_identity.loc[m16_identity["ladder_id"].eq("L4_anchor_plus_dif_joint_calibration")]
    m16_min = best_supported["mean"].min() if not best_supported.empty else m16_identity["mean"].min()

    rows = [
        ("Input representations", f"Dataset identity BA {dataset_ba_min:.2f}-{dataset_ba_max:.2f}", "Not interchangeable", COLORS["blue"]),
        ("Clinical targets", f"L1/L2/L3 max item deltas {l1:.2f}/{l2:.2f}/{l3:.2f}", "Partially aligned, heterogeneous", COLORS["amber"]),
        ("Latent target", "Identity lower, transfer validity inconsistent", "Diagnostic target layer", COLORS["teal"]),
        ("Calibration", f"Target-side calibration output identity BA >= {m16_min:.2f}", "Needs broader adaptation", COLORS["purple"]),
        ("Supervision boundary", "Target-calibrated gains are same-budget, not zero-label wins", "Measured method result", COLORS["red"]),
    ]

    fig, ax = plt.subplots(figsize=(11.5, 5.7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.98, "Evidence summary: benchmark targets are not automatically interchangeable", fontsize=14.5, weight="bold", va="top")
    ax.text(
        0.02,
        0.88,
        "The contribution is a bounded validity audit: representation signatures, measurement heterogeneity, and prediction instability are separated.",
        fontsize=9.2,
        color=COLORS["muted"],
    )

    headers = ["Question layer", "Aggregate evidence", "Conclusion"]
    xs = [0.04, 0.34, 0.74]
    widths = [0.25, 0.36, 0.20]
    for x, w, h in zip(xs, widths, headers):
        ax.text(x, 0.81, h, weight="bold", fontsize=10.5)
        ax.plot([x, x + w], [0.785, 0.785], color=COLORS["line"], linewidth=1)

    y0, dy = 0.70, 0.125
    for i, (layer, evidence, conclusion, color) in enumerate(rows):
        y = y0 - i * dy
        bg = COLORS["bg"] if i % 2 else "white"
        ax.add_patch(Rectangle((0.03, y - 0.047), 0.92, 0.087, facecolor=bg, edgecolor="none"))
        ax.add_patch(Rectangle((0.035, y - 0.025), 0.014, 0.05, facecolor=color, edgecolor=color))
        ax.text(0.058, y, wrap_text(layer, 22), va="center", fontsize=9.6, weight="bold")
        ax.text(0.34, y, wrap_text(evidence, 46), va="center", fontsize=9.0, color=COLORS["ink"], linespacing=1.1)
        ax.text(0.74, y, wrap_text(conclusion, 27), va="center", fontsize=9.0, color=COLORS["ink"], weight="bold", linespacing=1.1)

    ax.text(
        0.04,
        0.06,
        "Recommended Discussion phrasing: systematic empirical evidence for representation discrepancies and potential measurement heterogeneity, challenging interchangeable clinical targets without claiming universal construct divergence.",
        fontsize=8.8,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig7_evidence_summary")


def write_manifest(generated: dict[str, list[Path]]) -> None:
    rows = [
        ("Figure 1", "Introduction / Method opening", "fig1_framework_overview", "Target-contract-centered measurement-aware transfer framework."),
        ("Figure 2", "Datasets / design", "fig2_dataset_relationship_map", "Formal target-contract contrasts and auxiliary stress-test roles."),
        ("Figure 3", "RQ1 results", "fig3_controlled_identity_probe", "Control-dependent corpus identity under length/severity controls."),
        ("Supplementary Figure S2", "RQ1 supplement", "fig3_representation_identity_heatmap", "Raw dataset identity recoverability from comparable frozen feature spaces."),
        ("Figure 4", "RQ2 PHQ results", "fig4_phq_shared_item_measurement_analysis", "PHQ shared-item mean and severity-conditioned endorsement analysis."),
        ("Figure 5", "RQ2 controlled comparison", "fig5_daicwoz_edaic_controlled_comparison", "DAIC-WOZ/E-DAIC same-lineage control plus bounded PHQ/HAMD stress views."),
        ("Supplementary Figure S3", "RQ3 supplement", "fig6_latent_target_tradeoff", "Latent target identity/transfer/observed-scale validity tradeoff."),
        ("Supplementary Figure S4", "Discussion supplement", "fig7_evidence_summary", "Final evidence summary and claim boundary."),
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "core7_figure_manifest.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["figure", "recommended_location", "file_stem", "purpose"])
        writer.writerows(rows)
    (OUT_DIR / "core7_figure_manifest.json").write_text(
        json.dumps(
            [
                {"figure": fig, "recommended_location": loc, "file_stem": stem, "purpose": purpose}
                for fig, loc, stem, purpose in rows
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    lines = [
        "# Core 7 figure package",
        "",
        "Generated from existing registry, audit, Phase 3, MV16, MV17a, and MV21 aggregate artifacts.",
        "",
        "## Figures",
        "",
    ]
    for fig, loc, stem, purpose in rows:
        paths = generated[stem]
        lines.append(f"- {fig}: `{stem}` ({loc}) - {purpose}")
        lines.append("  - " + ", ".join(str(p.relative_to(ROOT)) for p in paths))
    lines.append("")
    lines.append("Regenerate with: `python scripts/build_paper_core7_figures.py`.")
    (OUT_DIR / "core7_figure_recommendations.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    configure_matplotlib()
    generated = {
        "fig1_framework_overview": fig1_framework_overview(),
        "fig2_dataset_relationship_map": fig2_dataset_relationship_map(),
        "fig3_controlled_identity_probe": fig3_controlled_identity_probe(),
        "fig3_representation_identity_heatmap": fig3_representation_identity_heatmap(),
        "fig4_phq_shared_item_measurement_analysis": fig4_phq_shared_item_measurement(),
        "fig5_daicwoz_edaic_controlled_comparison": fig5_daicwoz_edaic_control(),
        "fig6_latent_target_tradeoff": fig6_latent_target_tradeoff(),
        "fig7_evidence_summary": fig7_evidence_summary(),
    }
    write_manifest(generated)
    for stem, paths in generated.items():
        print(stem)
        for path in paths:
            print(f"  {path}")
    print(f"report: {OUT_DIR / 'core7_figure_recommendations.md'}")


if __name__ == "__main__":
    main()
