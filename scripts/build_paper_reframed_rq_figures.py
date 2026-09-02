#!/usr/bin/env python3
"""Build manuscript figures for the reframed RQ narrative."""

from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis/diagnostic_measurement_audit_paper/figures_reframed_rq"
MV21_DIR = ROOT / "analysis/phase5_minimal_validation/p5_mv21_measurement_discrepancy_gradient"
MV17A_DIR = ROOT / "analysis/phase5_minimal_validation/p5_mv17a_multilingual_feature_contract"

COLORS = {
    "ink": "#1f2933",
    "muted": "#687783",
    "line": "#c9d3db",
    "bg": "#f8fafc",
    "blue": "#2f6f9f",
    "blue_light": "#d9ecf7",
    "teal": "#2a9d8f",
    "teal_light": "#d8f1ec",
    "amber": "#d9902f",
    "amber_light": "#f7e4c3",
    "red": "#c93c4f",
    "red_light": "#f4d7dc",
    "gray": "#8795a1",
    "gray_light": "#e8eef2",
    "purple": "#6d5bd0",
    "purple_light": "#e6e0f4",
}


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
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
    paths = []
    for suffix in ("png", "svg"):
        path = OUT_DIR / f"{stem}.{suffix}"
        fig.savefig(path, bbox_inches="tight", facecolor="white")
        paths.append(path)
    plt.close(fig)
    return paths


def add_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    w: float,
    h: float,
    text: str,
    fc: str,
    ec: str,
    fontsize: int = 10,
    weight: str = "normal",
) -> None:
    box = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.018",
        linewidth=1.2,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(box)
    ax.text(
        xy[0] + w / 2,
        xy[1] + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        weight=weight,
        linespacing=1.18,
    )


def add_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.4,
            color=color,
            shrinkA=4,
            shrinkB=4,
        )
    )


def fig1_framework() -> list[Path]:
    fig, ax = plt.subplots(figsize=(10.5, 5.6))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.02,
        0.96,
        "Benchmark-validity audit: two sources of cross-corpus non-equivalence",
        fontsize=15,
        weight="bold",
        va="top",
    )

    add_box(
        ax,
        (0.04, 0.42),
        0.18,
        0.18,
        "Latent clinical\nconstruct\n(depression severity)",
        COLORS["gray_light"],
        COLORS["gray"],
        fontsize=10,
        weight="bold",
    )
    add_box(
        ax,
        (0.34, 0.63),
        0.22,
        0.18,
        "Corpus-specific\nacquisition mechanism\nP_D(X | severity)\nlanguage | setting | modality",
        COLORS["blue_light"],
        COLORS["blue"],
        fontsize=9,
    )
    add_box(
        ax,
        (0.34, 0.23),
        0.22,
        0.18,
        "Corpus-specific\nmeasurement mechanism\nP_D(Y | severity)\nscale | items | scoring",
        COLORS["amber_light"],
        COLORS["amber"],
        fontsize=9,
    )
    add_box(
        ax,
        (0.68, 0.63),
        0.21,
        0.18,
        "Observed\nrepresentation X_D\nspeech | text | video | gait",
        "#eef6fb",
        COLORS["blue"],
        fontsize=9,
    )
    add_box(
        ax,
        (0.68, 0.23),
        0.21,
        0.18,
        "Observed clinical\ntarget Y_D\nPHQ | HAMD | SDS | labels",
        "#fff4de",
        COLORS["amber"],
        fontsize=9,
    )
    add_box(
        ax,
        (0.69, 0.43),
        0.20,
        0.12,
        "Cross-corpus\nmodel evaluation",
        "#edf7f4",
        COLORS["teal"],
        fontsize=10,
        weight="bold",
    )

    add_arrow(ax, (0.22, 0.54), (0.34, 0.72), COLORS["blue"])
    add_arrow(ax, (0.22, 0.48), (0.34, 0.32), COLORS["amber"])
    add_arrow(ax, (0.56, 0.72), (0.68, 0.72), COLORS["blue"])
    add_arrow(ax, (0.56, 0.32), (0.68, 0.32), COLORS["amber"])
    add_arrow(ax, (0.785, 0.63), (0.785, 0.55), COLORS["teal"])
    add_arrow(ax, (0.785, 0.43), (0.785, 0.41), COLORS["teal"])

    ax.text(0.40, 0.84, "RQ1 representation heterogeneity", color=COLORS["blue"], weight="bold")
    ax.text(0.39, 0.16, "RQ2 measurement heterogeneity", color=COLORS["amber"], weight="bold")
    ax.text(0.70, 0.58, "RQ3 generalization consequence", color=COLORS["teal"], weight="bold")
    ax.text(
        0.04,
        0.05,
        "Core claim boundary: the paper audits whether benchmark targets are interchangeable across corpora; "
        "it does not claim a universal depression measurement shift.",
        fontsize=9,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig1_benchmark_validity_framework")


def fig2_dataset_role_map() -> list[Path]:
    rows = [
        ("DAIC-WOZ", "original WOZ benchmark view", "support", "level-1 control", "context"),
        ("E-DAIC", "extended PHQ-8 benchmark", "primary", "level 1 + 2", "primary"),
        ("CMDC", "cross-language PHQ/HAMD corpus", "primary", "level 2 + 3", "primary"),
        ("PDCH", "same-HAMD clinical corpus", "primary", "level-3 exploratory", "support"),
        ("MODMA", "protocol/task control", "support", "none", "support"),
        ("EATD", "external negative stress", "support", "none", "support"),
        ("MPDD-AVG", "acquisition/population stress", "support", "none", "support"),
    ]
    cols = ["Representation\nheterogeneity", "Measurement\nheterogeneity", "Generalization\nconsequence"]
    status_to_color = {
        "primary": COLORS["blue"],
        "support": COLORS["teal"],
        "context": COLORS["gray"],
        "level-1 control": COLORS["teal"],
        "level 1 + 2": COLORS["amber"],
        "level 2 + 3": COLORS["amber"],
        "level-3 exploratory": COLORS["amber"],
        "none": COLORS["gray_light"],
    }
    status_to_text = {
        "primary": "primary",
        "support": "support",
        "context": "context",
        "level-1 control": "L1 control",
        "level 1 + 2": "L1/L2",
        "level 2 + 3": "L2/L3",
        "level-3 exploratory": "L3 explor.",
        "none": "-",
    }

    fig, ax = plt.subplots(figsize=(11.6, 6.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.96, "Dataset/view roles after adding DAIC-WOZ", fontsize=14, weight="bold", va="top")
    ax.text(
        0.02,
        0.90,
        "Use DAIC-WOZ as a benchmark-control view, not as a fully independent third PHQ corpus.",
        fontsize=9.5,
        color=COLORS["muted"],
    )

    x_name, x_role = 0.03, 0.22
    x_cols = [0.53, 0.69, 0.85]
    badge_w, badge_h = 0.115, 0.052
    y0, dy = 0.78, 0.094
    ax.text(x_name, 0.84, "Corpus/view", weight="bold")
    ax.text(x_role, 0.84, "Paper role", weight="bold")
    for x, col in zip(x_cols, cols):
        ax.text(x, 0.84, col, ha="center", weight="bold", fontsize=9)

    for idx, (name, role, rq1, rq2, rq3) in enumerate(rows):
        y = y0 - idx * dy
        bg = "#ffffff" if idx % 2 == 0 else COLORS["bg"]
        ax.add_patch(Rectangle((0.02, y - 0.038), 0.94, 0.072, facecolor=bg, edgecolor="none"))
        ax.text(x_name, y, name, va="center", weight="bold")
        ax.text(x_role, y, role, va="center", fontsize=9, color=COLORS["muted"])
        for x, status in zip(x_cols, [rq1, rq2, rq3]):
            color = status_to_color[status]
            edge = COLORS["gray"] if status == "none" else color
            text_color = COLORS["muted"] if status == "none" else "white"
            ax.add_patch(
                FancyBboxPatch(
                    (x - badge_w / 2, y - badge_h / 2),
                    badge_w,
                    badge_h,
                    boxstyle="round,pad=0.004,rounding_size=0.012",
                    facecolor=color,
                    edgecolor=edge,
                    linewidth=1.0,
                )
            )
            ax.text(x, y, status_to_text[status], va="center", ha="center", fontsize=7.8, color=text_color)

    legend_y = 0.08
    legend = [
        ("primary", COLORS["blue"]),
        ("support/control", COLORS["teal"]),
        ("measurement-gradient", COLORS["amber"]),
        ("not used", COLORS["gray_light"]),
    ]
    lx = 0.04
    for label, color in legend:
        ax.add_patch(
            FancyBboxPatch(
                (lx, legend_y - 0.015),
                0.034,
                0.03,
                boxstyle="round,pad=0.002,rounding_size=0.006",
                facecolor=color,
                edgecolor=COLORS["gray"],
                linewidth=0.8,
            )
        )
        ax.text(lx + 0.044, legend_y, label, va="center", fontsize=8.8, color=COLORS["muted"])
        lx += 0.24
    return save_figure(fig, "fig2_dataset_view_role_map")


def get_top_abs_row(df: pd.DataFrame, value_col: str) -> pd.Series:
    non_sparse = df.loc[~df["sparse_comparison"].astype(bool)].copy()
    return non_sparse.iloc[non_sparse[value_col].abs().argmax()]


def fig3_measurement_gradient() -> list[Path]:
    daic = pd.read_csv(MV21_DIR / "daicwoz_edaic_conditioned_deltas.csv")
    phq = pd.read_csv(MV21_DIR / "phq_shared_conditioned_deltas.csv")
    hamd = pd.read_csv(MV21_DIR / "hamd_conditioned_deltas.csv")
    corr = pd.read_csv(MV21_DIR / "hamd_item_correlation_delta_summary.csv")
    summary = json.loads((MV21_DIR / "run_summary.json").read_text())

    daic_top = get_top_abs_row(daic, "item_mean_diff_left_minus_right")
    phq_top = get_top_abs_row(phq, "item_mean_diff_left_minus_right")
    hamd_top = get_top_abs_row(hamd, "item_mean_diff_left_minus_right")
    corr_top = corr.iloc[corr["abs_spearman_delta"].argmax()]

    levels = [
        {
            "label": "Level 1\nDAIC-WOZ vs E-DAIC",
            "detail": "same language + PHQ-8\npaired overlap n={}; exact-match >=0.986".format(
                summary["daicwoz_edaic_paired_subjects"]
            ),
            "value": abs(float(daic_top["item_mean_diff_left_minus_right"])),
            "callout": "{} {}, |delta|={:.3f}".format(
                daic_top["item_id"], daic_top["condition_bin"], abs(float(daic_top["item_mean_diff_left_minus_right"]))
            ),
            "color": COLORS["teal"],
        },
        {
            "label": "Level 2\nE-DAIC vs CMDC",
            "detail": "PHQ shared symptoms\nn={}/{}".format(summary["phq_edaic_subjects"], summary["phq_cmdc_subjects"]),
            "value": abs(float(phq_top["item_mean_diff_left_minus_right"])),
            "callout": "{} {} {}, delta={:.3f}".format(
                phq_top["item_id"],
                phq_top["item_label_short"],
                phq_top["condition_bin"],
                float(phq_top["item_mean_diff_left_minus_right"]),
            ),
            "color": COLORS["amber"],
        },
        {
            "label": "Level 3\nCMDC vs PDCH",
            "detail": "same HAMD, exploratory\nn={}/{}".format(
                summary["hamd_cmdc_subjects"], summary["hamd_pdch_subjects"]
            ),
            "value": abs(float(hamd_top["item_mean_diff_left_minus_right"])),
            "callout": "{} {}, delta={:.3f}\nmax corr delta: {}-{} = {:.3f}".format(
                hamd_top["item_id"],
                hamd_top["condition_bin"],
                float(hamd_top["item_mean_diff_left_minus_right"]),
                corr_top["left_item_id"],
                corr_top["right_item_id"],
                float(corr_top["abs_spearman_delta"]),
            ),
            "color": COLORS["red"],
        },
    ]

    fig, ax = plt.subplots(figsize=(10.8, 5.5))
    y = np.arange(len(levels))[::-1]
    vals = [lvl["value"] for lvl in levels]
    colors = [lvl["color"] for lvl in levels]

    ax.barh(y, vals, color=colors, alpha=0.85, height=0.42)
    ax.set_ylim(-0.58, 2.58)
    ax.set_yticks(y)
    ax.set_yticklabels([lvl["label"] for lvl in levels], fontsize=10)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Maximum non-sparse severity-conditioned item mean delta")
    ax.set_title("RQ2 measurement heterogeneity follows a discrepancy gradient", loc="left", pad=16)
    ax.grid(axis="x", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    for yi, lvl, val in zip(y, levels, vals):
        ax.text(val + 0.025, yi + 0.08, lvl["callout"], va="center", fontsize=9)
        ax.text(0.01, yi - 0.28, lvl["detail"], va="center", fontsize=8.5, color=COLORS["muted"])

    ax.text(
        0.0,
        -0.22,
        "Interpretation: same-lineage PHQ-8 is near-identical; cross-language PHQ and same-HAMD clinical-corpus comparisons show larger localized descriptive discrepancies.",
        transform=ax.transAxes,
        fontsize=9,
        color=COLORS["muted"],
    )
    return save_figure(fig, "fig3_measurement_discrepancy_gradient")


def fig4_prediction_consequence_matrix() -> list[Path]:
    encoders = ["BGE-M3", "multilingual-E5"]
    rows = [
        ("Same-dataset theta learnable", ["pass", "pass"], ["pass", "pass"]),
        ("Observed-scale safety", ["fail", "fail"], ["fail", "fail"]),
        ("External theta transfer", ["pass", "fail"], ["pass", "fail"]),
        ("Conditional output identity BA", ["0.495", "0.488"], ["pass", "pass"]),
        ("Theta-conditioned feature identity BA", ["1.000", "1.000"], ["fail", "fail"]),
        ("B3 Pareto dominates latent target", ["No", "Yes"], ["mixed", "mixed"]),
        ("Overall full-method gate", ["blocked", "blocked"], ["fail", "fail"]),
    ]
    status_colors = {
        "pass": (COLORS["teal"], "white"),
        "fail": (COLORS["red"], "white"),
        "mixed": (COLORS["amber"], "white"),
    }

    fig, ax = plt.subplots(figsize=(9.6, 5.7))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.02, 0.96, "RQ3 consequence: alignment attempts remain diagnostically blocked", fontsize=15, weight="bold", va="top")
    ax.text(
        0.02,
        0.90,
        "The useful negative result is not model failure alone; it is the persistence of corpus identity after target/feature controls.",
        fontsize=9.5,
        color=COLORS["muted"],
    )

    x_label = 0.04
    x_cells = [0.55, 0.78]
    cell_w, cell_h = 0.18, 0.075
    y0, dy = 0.79, 0.095
    ax.text(x_label, 0.84, "Gate / diagnostic", weight="bold")
    for x, enc in zip(x_cells, encoders):
        ax.text(x + cell_w / 2, 0.84, enc, ha="center", weight="bold")

    for i, (gate, vals, statuses) in enumerate(rows):
        y = y0 - i * dy
        bg = "#ffffff" if i % 2 == 0 else COLORS["bg"]
        ax.add_patch(Rectangle((0.025, y - 0.041), 0.92, 0.078, facecolor=bg, edgecolor="none"))
        ax.text(x_label, y, gate, va="center", fontsize=9.5)
        for x, val, status in zip(x_cells, vals, statuses):
            fc, tc = status_colors[status]
            ax.add_patch(
                FancyBboxPatch(
                    (x, y - cell_h / 2),
                    cell_w,
                    cell_h,
                    boxstyle="round,pad=0.006,rounding_size=0.014",
                    facecolor=fc,
                    edgecolor=fc,
                )
            )
            ax.text(x + cell_w / 2, y, val, ha="center", va="center", color=tc, fontsize=9, weight="bold")

    ax.text(0.04, 0.07, "Green = condition satisfied; red = blocked; amber = encoder-dependent.", fontsize=8.8, color=COLORS["muted"])
    return save_figure(fig, "fig4_prediction_consequence_gate_matrix")


def appendix_phq_conditioned() -> list[Path]:
    df = pd.read_csv(MV21_DIR / "phq_shared_conditioned_deltas.csv")
    df = df.loc[~df["sparse_comparison"].astype(bool)].copy()
    df["abs_delta"] = df["item_mean_diff_left_minus_right"].abs()
    top = df.sort_values("abs_delta", ascending=False).head(12).iloc[::-1]
    labels = [
        f"{row.item_id} {row.item_label_short} ({row.condition_bin})"
        for row in top.itertuples(index=False)
    ]
    vals = top["item_mean_diff_left_minus_right"].to_numpy()
    colors = np.where(vals >= 0, COLORS["blue"], COLORS["amber"])

    fig, ax = plt.subplots(figsize=(9.5, 6.0))
    ax.barh(np.arange(len(vals)), vals, color=colors, alpha=0.88)
    ax.axvline(0, color=COLORS["ink"], linewidth=0.8)
    ax.set_yticks(np.arange(len(vals)))
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.set_xlabel("Item mean delta: E-DAIC minus CMDC")
    ax.set_title("Supplement: PHQ shared-item severity-conditioned deltas", loc="left", pad=14)
    ax.grid(axis="x", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.text(
        0.0,
        -0.16,
        "Positive values indicate higher E-DAIC item response at comparable item-excluded severity; negative values indicate higher CMDC response.",
        transform=ax.transAxes,
        fontsize=8.8,
        color=COLORS["muted"],
    )
    return save_figure(fig, "supp_fig_phq_shared_item_conditioned_deltas")


def appendix_hamd_exploratory() -> list[Path]:
    items = pd.read_csv(MV21_DIR / "hamd_conditioned_deltas.csv")
    items = items.loc[~items["sparse_comparison"].astype(bool)].copy()
    items = items.loc[items["scope"].eq("all_subjects")].copy()
    items["abs_delta"] = items["item_mean_diff_left_minus_right"].abs()
    item_top = items.sort_values("abs_delta", ascending=False).head(10).iloc[::-1]
    corrs = pd.read_csv(MV21_DIR / "hamd_item_correlation_delta_summary.csv").head(10).iloc[::-1]

    fig, axes = plt.subplots(1, 2, figsize=(12.0, 6.0), gridspec_kw={"width_ratios": [1.05, 1]})
    ax = axes[0]
    vals = item_top["item_mean_diff_left_minus_right"].to_numpy()
    labels = [f"{r.item_id} ({r.condition_bin})" for r in item_top.itertuples(index=False)]
    ax.barh(np.arange(len(vals)), vals, color=np.where(vals >= 0, COLORS["blue"], COLORS["red"]), alpha=0.88)
    ax.axvline(0, color=COLORS["ink"], linewidth=0.8)
    ax.set_yticks(np.arange(len(vals)))
    ax.set_yticklabels(labels, fontsize=8.3)
    ax.set_xlabel("CMDC minus PDCH item mean")
    ax.set_title("Severity-conditioned HAMD item deltas", loc="left", fontsize=12)
    ax.grid(axis="x", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    ax = axes[1]
    vals = corrs["abs_spearman_delta"].to_numpy()
    labels = [f"{r.left_item_id}-{r.right_item_id}" for r in corrs.itertuples(index=False)]
    ax.barh(np.arange(len(vals)), vals, color=COLORS["purple"], alpha=0.82)
    ax.set_yticks(np.arange(len(vals)))
    ax.set_yticklabels(labels, fontsize=8.3)
    ax.set_xlabel("Absolute Spearman delta")
    ax.set_title("HAMD correlation-structure shifts", loc="left", fontsize=12)
    ax.grid(axis="x", color=COLORS["gray_light"], linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)

    fig.suptitle("Supplement: CMDC-HAMD vs PDCH-HAMD exploratory same-scale analysis", x=0.02, ha="left", fontsize=14, weight="bold")
    fig.text(
        0.02,
        0.005,
        "All-subjects item-delta scope shown. Exploratory descriptive evidence only: CMDC HAMD n=25 is not used for formal MIM/IRT or invariance testing.",
        fontsize=8.8,
        color=COLORS["muted"],
    )
    return save_figure(fig, "supp_fig_hamd_same_scale_exploratory")


def write_manifest(generated: dict[str, list[Path]]) -> None:
    rows = [
        {
            "figure": "Figure 1",
            "recommended_location": "Introduction or end of Method overview",
            "file_stem": "fig1_benchmark_validity_framework",
            "status": "ready_as_conceptual_schematic",
            "purpose": "Defines benchmark-validity audit and separates representation vs measurement heterogeneity.",
        },
        {
            "figure": "Figure 2",
            "recommended_location": "Datasets / Experimental design",
            "file_stem": "fig2_dataset_view_role_map",
            "status": "ready_but_can_be_hand_polished",
            "purpose": "Shows how the seven corpus/views support RQ1-RQ3 after adding DAIC-WOZ.",
        },
        {
            "figure": "Figure 3",
            "recommended_location": "Main RQ2 results",
            "file_stem": "fig3_measurement_discrepancy_gradient",
            "status": "main_text_priority",
            "purpose": "Single strongest figure for the new DAIC-WOZ/E-DAIC, E-DAIC/CMDC, CMDC/PDCH measurement-gradient story.",
        },
        {
            "figure": "Figure 4",
            "recommended_location": "Main RQ3 results or Discussion",
            "file_stem": "fig4_prediction_consequence_gate_matrix",
            "status": "main_text_priority",
            "purpose": "Summarizes why alignment/calibration/latent-target attempts remain diagnostic rather than a complete method.",
        },
        {
            "figure": "Supplementary Figure S1",
            "recommended_location": "Appendix / measurement evidence",
            "file_stem": "supp_fig_phq_shared_item_conditioned_deltas",
            "status": "supplement_priority",
            "purpose": "Item-level PHQ shared-symptom severity-conditioned evidence.",
        },
        {
            "figure": "Supplementary Figure S2",
            "recommended_location": "Appendix / measurement evidence",
            "file_stem": "supp_fig_hamd_same_scale_exploratory",
            "status": "supplement_priority",
            "purpose": "Exploratory HAMD same-scale item and correlation-structure differences.",
        },
    ]

    csv_path = OUT_DIR / "figure_recommendation_manifest.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    json_path = OUT_DIR / "figure_recommendation_manifest.json"
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    report_lines = [
        "# Recommended figure package for the reframed RQ manuscript",
        "",
        "## Main text priority",
        "",
        "1. Figure 1: benchmark-validity framework. Use as the conceptual opening figure if the paper needs a strong AI-benchmark-validity framing.",
        "2. Figure 3: measurement-discrepancy gradient. This is the most important new figure after adding DAIC-WOZ.",
        "3. Figure 4: prediction-consequence gate matrix. Use to make the negative RQ3 result legible without overclaiming a solved method.",
        "4. Figure 2: dataset/view role map. Use in the dataset section if space allows; otherwise keep it as a table or supplement.",
        "",
        "## Supplement priority",
        "",
        "- Supplementary Figure S1: PHQ shared-item severity-conditioned deltas.",
        "- Supplementary Figure S2: CMDC-HAMD vs PDCH-HAMD exploratory same-scale deltas and correlation-structure shifts.",
        "",
        "## Generated files",
        "",
    ]
    for stem, paths in generated.items():
        report_lines.append(f"- {stem}: " + ", ".join(str(p.relative_to(ROOT)) for p in paths))
    report_lines.append("")
    report_lines.append("All figures are generated from aggregate CSV/JSON artifacts only.")
    (OUT_DIR / "figure_recommendations.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> None:
    configure_matplotlib()
    generated = {
        "fig1_benchmark_validity_framework": fig1_framework(),
        "fig2_dataset_view_role_map": fig2_dataset_role_map(),
        "fig3_measurement_discrepancy_gradient": fig3_measurement_gradient(),
        "fig4_prediction_consequence_gate_matrix": fig4_prediction_consequence_matrix(),
        "supp_fig_phq_shared_item_conditioned_deltas": appendix_phq_conditioned(),
        "supp_fig_hamd_same_scale_exploratory": appendix_hamd_exploratory(),
    }
    write_manifest(generated)
    for stem, paths in generated.items():
        print(stem)
        for path in paths:
            print(f"  {path}")
    print(f"manifest: {OUT_DIR / 'figure_recommendation_manifest.csv'}")
    print(f"report: {OUT_DIR / 'figure_recommendations.md'}")


if __name__ == "__main__":
    main()
