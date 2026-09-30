#!/usr/bin/env python3
"""IEEE IoT-J Section IV results figures (Figs. 3--6).

Bare panel tags (a)--(d) only. No caption text on the artwork.
Rebuild:
  python3 paper/fig_results.py

Sources (validated beta_1 = beta_2 = 0, except Fig. 6 sweeps):
  results/scenario2_headline_data.csv
  results/scenario3_headline_data.csv
  results/scenario3_beta1_scaled_sweep.csv
  results/scenario3_beta2_sweep.csv
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
OUT = os.path.join(HERE, "elqtp_figs")
RES = os.path.join(ROOT, "results")

DRIFTS = [0.5, 1.0, 2.0, 3.0, 3.5]
PROTOS = ["lqarp", "elqtp", "rlor", "periodic"]
PROTO_LABEL = {
    "lqarp": "LQARP",
    "elqtp": "E-LQTP",
    "rlor": "RLOR",
    "periodic": "Periodic",
}
# Color + hatch + marker: readable in color and grayscale.
STYLE = {
    "lqarp": dict(color="#0F4C81", marker="o", ls="-", hatch="", mfc="white"),
    "elqtp": dict(color="#D55E00", marker="s", ls="--", hatch="//", mfc="#D55E00"),
    "rlor": dict(color="#009E73", marker="^", ls=":", hatch="..", mfc="#009E73"),
    "periodic": dict(color="#4D4D4D", marker="D", ls="-.", hatch="xx", mfc="#4D4D4D"),
}
PERIODIC_OCTRL = 413.42


def apply_ieee_rc() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "mathtext.default": "regular",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.7,
            "lines.linewidth": 1.15,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.bbox": None,
            "savefig.pad_inches": 0.02,
        }
    )


def _f(row: dict, key: str) -> float:
    v = row[key]
    if v in ("", "nan", "NaN"):
        return float("nan")
    return float(v)


def load_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def stats(vals: list[float]) -> tuple[float, float]:
    a = np.asarray(vals, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return float("nan"), 0.0
    if a.size == 1:
        return float(a[0]), 0.0
    return float(a.mean()), float(a.std(ddof=1))


def grouped(rows: list[dict], proto: str, key: str, pred=None) -> tuple[float, float]:
    xs = []
    for r in rows:
        if r["protocol"] != proto:
            continue
        if pred is not None and not pred(r):
            continue
        xs.append(_f(r, key))
    return stats(xs)


def panel_tag(ax, tag: str) -> None:
    """Bold (a)/(b)/... in the top-left margin, clear of the ylabel."""
    ax.text(
        -0.18,
        1.05,
        tag,
        transform=ax.transAxes,
        fontsize=9,
        fontweight="bold",
        va="bottom",
        ha="left",
        clip_on=False,
    )


def style_ax(ax, tag: str) -> None:
    panel_tag(ax, tag)
    ax.tick_params(labelsize=8, length=3.0, width=0.6, pad=2, labelleft=True, labelbottom=True)
    ax.grid(axis="y", linestyle=":", linewidth=0.45, color="0.75")
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)
        spine.set_color("black")


def legend_handles(keys: list[str], kind: str = "line") -> list:
    hs = []
    for k in keys:
        st = STYLE[k]
        if kind == "bar":
            hs.append(
                Patch(
                    facecolor=st["color"],
                    edgecolor="black",
                    linewidth=0.5,
                    hatch=st["hatch"],
                    label=PROTO_LABEL[k],
                )
            )
        else:
            hs.append(
                Line2D(
                    [0],
                    [0],
                    color=st["color"],
                    marker=st["marker"],
                    ls=st["ls"],
                    mfc=st["mfc"],
                    mec=st["color"],
                    lw=1.15,
                    ms=5.5,
                    label=PROTO_LABEL[k],
                )
            )
    return hs


def place_legend(fig, handles, ncol: int, y: float = 0.02) -> None:
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=ncol,
        frameon=False,
        fontsize=8,
        handlelength=2.2,
        columnspacing=1.45,
        bbox_to_anchor=(0.5, y),
    )


def save(fig, stem: str) -> None:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, stem)
    fig.savefig(path + ".pdf")
    fig.savefig(path + ".png", dpi=300)
    fig.savefig(path + ".svg")
    fig.savefig(path + ".eps")
    plt.close(fig)
    print("wrote", path + ".{pdf,eps,png,svg}")


def protocol_bars(rows: list[dict], stem: str, pred=None) -> None:
    """PDR is saturated (~1.0) and lives in the tables, not on the artwork."""
    apply_ieee_rc()
    fig, axes = plt.subplots(1, 3, figsize=(7.16, 2.15))
    fig.subplots_adjust(left=0.078, right=0.990, top=0.84, bottom=0.26, wspace=0.42)
    tags = ["(a)", "(b)", "(c)"]
    panels = [
        ("mean_hops", "Mean hops", (0.0, 2.85), [0, 1, 2]),
        ("T_e2e_s", "End-to-end delay (s)", (0.0, 5.6), [0, 2, 4]),
        ("O_ctrl_byte_per_s", "Control overhead (byte/s)", (0.0, 520), [0, 200, 400]),
    ]
    x = np.arange(len(PROTOS))
    width = 0.62
    for ax, tag, (key, ylab, ylim, yticks) in zip(axes, tags, panels):
        style_ax(ax, tag)
        means, lo, hi, colors, hatches = [], [], [], [], []
        for p in PROTOS:
            m, s = grouped(rows, p, key, pred)
            m = 0.0 if not np.isfinite(m) else m
            s = 0.0 if not np.isfinite(s) else s
            lo.append(s)
            hi.append(s)
            means.append(m)
            colors.append(STYLE[p]["color"])
            hatches.append(STYLE[p]["hatch"])
        yerr = np.vstack([lo, hi])
        bars = ax.bar(
            x,
            means,
            width,
            yerr=yerr,
            color=colors,
            edgecolor="black",
            linewidth=0.55,
            capsize=2.4,
            error_kw=dict(elinewidth=0.8, capthick=0.8, ecolor="#222222"),
        )
        for bar, h in zip(bars, hatches):
            bar.set_hatch(h)
        ax.set_xticks(x)
        ax.set_xticklabels([PROTO_LABEL[p] for p in PROTOS], fontsize=8)
        ax.set_ylabel(ylab, fontsize=8)
        ax.set_ylim(*ylim)
        ax.set_yticks(yticks)
    place_legend(fig, legend_handles(PROTOS, "bar"), ncol=4, y=0.02)
    save(fig, stem)


def fig3_scenario2_protocols(s2: list[dict]) -> None:
    protocol_bars(
        s2,
        "fig3_scenario2_protocols",
        pred=lambda r: abs(_f(r, "drift_mps") - 2.0) < 1e-9,
    )


def fig5_scenario3_protocols(s3: list[dict]) -> None:
    protocol_bars(s3, "fig5_scenario3_protocols")


def fig4_scenario2_drift(s2: list[dict]) -> None:
    apply_ieee_rc()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 3.20))
    fig.subplots_adjust(left=0.095, right=0.985, top=0.90, bottom=0.14, wspace=0.38, hspace=0.42)

    def series(proto: str, key: str) -> tuple[list[float], list[float], np.ndarray]:
        xs, ys, lo, hi = [], [], [], []
        for d in DRIFTS:
            m, s = grouped(
                s2,
                proto,
                key,
                pred=lambda r, dd=d: abs(_f(r, "drift_mps") - dd) < 1e-9,
            )
            if not np.isfinite(m):
                m, s = float("nan"), 0.0
            if not np.isfinite(s):
                s = 0.0
            xs.append(d)
            ys.append(m)
            if key == "PDR":
                lo.append(min(s, max(0.0, m)))
                hi.append(min(s, max(0.0, 1.0 - m)))
            else:
                lo.append(s)
                hi.append(s)
        return xs, ys, np.vstack([lo, hi])

    # (a) envelope attrition (same for LQARP and E-LQTP)
    ax = axes[0, 0]
    style_ax(ax, "(a)")
    for p in ("lqarp", "elqtp"):
        xs, ys, es = series(p, "n_exit_tsim")
        st = STYLE[p]
        ax.errorbar(
            xs,
            ys,
            yerr=es,
            color=st["color"],
            marker=st["marker"],
            ls=st["ls"],
            mfc=st["mfc"],
            mec=st["color"],
            capsize=2.2,
            elinewidth=0.8,
            markersize=5.5,
            zorder=3 if p == "elqtp" else 2,
        )
    ax.set_ylabel("Nodes leaving envelope", fontsize=8)
    ax.set_xlabel("Drift speed (m/s)", fontsize=8)
    ax.set_xticks(DRIFTS)
    ax.set_ylim(0.0, 22.0)
    ax.set_yticks([0, 8, 16])

    # (b) hops
    ax = axes[0, 1]
    style_ax(ax, "(b)")
    for p in ("lqarp", "elqtp"):
        xs, ys, es = series(p, "mean_hops")
        st = STYLE[p]
        ax.errorbar(
            xs,
            ys,
            yerr=es,
            color=st["color"],
            marker=st["marker"],
            ls=st["ls"],
            mfc=st["mfc"],
            mec=st["color"],
            capsize=2.2,
            elinewidth=0.8,
            markersize=5.5,
            zorder=3 if p == "elqtp" else 2,
        )
    ax.set_ylabel("Mean hops", fontsize=8)
    ax.set_xlabel("Drift speed (m/s)", fontsize=8)
    ax.set_xticks(DRIFTS)
    ax.set_ylim(1.85, 2.55)
    ax.set_yticks([1.9, 2.2, 2.5])

    # (c) first-fire
    ax = axes[1, 0]
    style_ax(ax, "(c)")
    xs, ys, es = series("elqtp", "first_fire_rate")
    st = STYLE["elqtp"]
    ax.errorbar(
        xs,
        ys,
        yerr=es,
        color=st["color"],
        marker=st["marker"],
        ls=st["ls"],
        mfc=st["mfc"],
        mec=st["color"],
        capsize=2.2,
        elinewidth=0.8,
        markersize=5.5,
    )
    ax.axhline(1.0, color=STYLE["periodic"]["color"], ls=STYLE["periodic"]["ls"], lw=1.05)
    ax.set_ylabel("First-fire rate", fontsize=8)
    ax.set_xlabel("Drift speed (m/s)", fontsize=8)
    ax.set_xticks(DRIFTS)
    ax.set_ylim(0.0, 1.12)
    ax.set_yticks([0.0, 0.5, 1.0])

    # (d) O_ctrl
    ax = axes[1, 1]
    style_ax(ax, "(d)")
    xs, ys, es = series("elqtp", "O_ctrl_byte_per_s")
    st = STYLE["elqtp"]
    ax.errorbar(
        xs,
        ys,
        yerr=es,
        color=st["color"],
        marker=st["marker"],
        ls=st["ls"],
        mfc=st["mfc"],
        mec=st["color"],
        capsize=2.2,
        elinewidth=0.8,
        markersize=5.5,
    )
    ax.axhline(0.0, color=STYLE["lqarp"]["color"], ls=STYLE["lqarp"]["ls"], lw=1.05)
    ax.axhline(PERIODIC_OCTRL, color=STYLE["periodic"]["color"], ls=STYLE["periodic"]["ls"], lw=1.05)
    ax.set_ylabel("Control overhead (byte/s)", fontsize=8)
    ax.set_xlabel("Drift speed (m/s)", fontsize=8)
    ax.set_xticks(DRIFTS)
    ax.set_ylim(-15, 480)
    ax.set_yticks([0, 200, 400])

    place_legend(fig, legend_handles(["lqarp", "elqtp", "periodic"], "line"), ncol=3, y=0.018)
    save(fig, "fig4_scenario2_drift")


def fig6_reward_ablation(b1: list[dict], b2: list[dict]) -> None:
    apply_ieee_rc()
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 3.20))
    fig.subplots_adjust(left=0.095, right=0.985, top=0.90, bottom=0.14, wspace=0.38, hspace=0.42)

    def by_field(rows: list[dict], proto: str, field: str, metric: str) -> dict[float, tuple[float, float]]:
        buckets: dict[float, list[float]] = defaultdict(list)
        for r in rows:
            if r["protocol"] != proto:
                continue
            buckets[_f(r, field)].append(_f(r, metric))
        return {k: stats(v) for k, v in buckets.items()}

    def lq_mean(rows: list[dict], metric: str) -> float:
        return stats([_f(r, metric) for r in rows if r["protocol"] == "lqarp"])[0]

    st = STYLE["elqtp"]

    def draw_beta1(ax, metric: str, ylab: str, ylim, yticks) -> None:
        e1 = by_field(b1, "elqtp", "beta_1", metric)
        xs = sorted(e1)
        ys = [e1[x][0] for x in xs]
        es = [e1[x][1] for x in xs]
        xpos = np.arange(len(xs))
        ax.errorbar(
            xpos,
            ys,
            yerr=es,
            color=st["color"],
            marker=st["marker"],
            ls=st["ls"],
            mfc=st["mfc"],
            mec=st["color"],
            capsize=2.2,
            elinewidth=0.8,
            markersize=5.5,
        )
        ax.axhline(lq_mean(b1, metric), color=STYLE["lqarp"]["color"], ls=STYLE["lqarp"]["ls"], lw=1.1)
        ax.set_xlabel(r"$\beta_1$", fontsize=8)
        ax.set_ylabel(ylab, fontsize=8)
        ax.set_ylim(*ylim)
        ax.set_yticks(yticks)
        ax.set_xticks(xpos)
        ax.set_xticklabels(
            ["0" if x == 0.0 else r"$10^{%d}$" % int(round(np.log10(x))) for x in xs],
            fontsize=8,
        )

    def draw_beta2(ax, metric: str, ylab: str, ylim, yticks) -> None:
        e2 = by_field(b2, "elqtp", "beta_2", metric)
        xs = sorted(e2)
        ys = [e2[x][0] for x in xs]
        es = [e2[x][1] for x in xs]
        ax.errorbar(
            xs,
            ys,
            yerr=es,
            color=st["color"],
            marker=st["marker"],
            ls=st["ls"],
            mfc=st["mfc"],
            mec=st["color"],
            capsize=2.2,
            elinewidth=0.8,
            markersize=5.5,
        )
        ax.axhline(lq_mean(b2, metric), color=STYLE["lqarp"]["color"], ls=STYLE["lqarp"]["ls"], lw=1.1)
        ax.set_xlabel(r"$\beta_2$", fontsize=8)
        ax.set_ylabel(ylab, fontsize=8)
        ax.set_xticks([0.0, 0.5, 1.0, 1.5, 2.0])
        ax.set_ylim(*ylim)
        ax.set_yticks(yticks)

    ax = axes[0, 0]
    style_ax(ax, "(a)")
    draw_beta1(ax, "mean_hops", "Mean hops", (1.70, 2.70), [1.8, 2.2, 2.6])
    ax = axes[0, 1]
    style_ax(ax, "(b)")
    draw_beta1(ax, "T_e2e_s", "End-to-end delay (s)", (3.4, 5.6), [3.6, 4.4, 5.2])
    ax = axes[1, 0]
    style_ax(ax, "(c)")
    draw_beta2(ax, "mean_hops", "Mean hops", (1.70, 2.55), [1.8, 2.1, 2.4])
    ax = axes[1, 1]
    style_ax(ax, "(d)")
    draw_beta2(ax, "T_e2e_s", "End-to-end delay (s)", (3.4, 5.2), [3.6, 4.2, 4.8])

    place_legend(fig, legend_handles(["lqarp", "elqtp"], "line"), ncol=2, y=0.018)
    save(fig, "fig6_reward_ablation")


def main() -> None:
    s2 = load_csv(os.path.join(RES, "scenario2_headline_data.csv"))
    s3 = load_csv(os.path.join(RES, "scenario3_headline_data.csv"))
    b1 = load_csv(os.path.join(RES, "scenario3_beta1_scaled_sweep.csv"))
    b2 = load_csv(os.path.join(RES, "scenario3_beta2_sweep.csv"))
    fig3_scenario2_protocols(s2)
    fig4_scenario2_drift(s2)
    fig5_scenario3_protocols(s3)
    fig6_reward_ablation(b1, b2)


if __name__ == "__main__":
    main()
