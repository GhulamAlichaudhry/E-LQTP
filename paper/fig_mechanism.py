#!/usr/bin/env python3
"""IEEE IoT-J Figure 2 — E-LQTP mechanism (themed blocks).

Times (TeX Gyre Termes). Panel tags (a)/(b) sit in a reserved margin
so they cannot clip. Panel (a) has header arrows and card-to-card
flow arrows matching Algorithm 1.

  python3 paper/fig_mechanism.py
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "elqtp_figs")

W_FIG = 7.16
H_FIG = 3.00

C_BLUE = "#0F4C81"
C_AMBER = "#D55E00"
C_TEAL = "#009E73"
C_GREY = "#7F7F7F"

THEME = {
    "sense": {"bar": C_BLUE, "name": "Sense"},
    "estimate": {"bar": C_TEAL, "name": "Estimate"},
    "trigger": {"bar": C_AMBER, "name": "Trigger"},
    "control": {"bar": C_AMBER, "name": "Control"},
    "forward": {"bar": C_GREY, "name": "Forward"},
}

C_EDGE = "#2C2C2C"
C_TXT = "#1A1A1A"
C_MUTED = "#5A5A5A"
C_WHITE = "#FFFFFF"
C_INNER = "#FFFFFF"
HEADER_H = 0.250
ROUND = 0.038
LW = 0.90
FS = 9.5
FS_H = 10.0
FS_EQ = 8.0

_TERM_REG = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-regular.otf"
_TERM_BD = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-bold.otf"
_TERM_IT = "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyretermes-italic.otf"
if not os.path.isfile(_TERM_REG):
    _TERM_REG = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
    _TERM_BD = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
    _TERM_IT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"


def apply_ieee_rc() -> None:
    for path in (_TERM_REG, _TERM_BD, _TERM_IT):
        font_manager.fontManager.addfont(path)
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["TeX Gyre Termes", "Liberation Serif", "Times New Roman"],
            "mathtext.fontset": "custom",
            "mathtext.rm": "TeX Gyre Termes",
            "mathtext.it": "TeX Gyre Termes",
            "mathtext.bf": "TeX Gyre Termes",
            "mathtext.cal": "TeX Gyre Termes",
            "mathtext.default": "it",
            "font.size": FS,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.bbox": None,
            "savefig.pad_inches": 0.04,
        }
    )


def _fp(bold=False, size=FS):
    return font_manager.FontProperties(fname=_TERM_BD if bold else _TERM_REG, size=size)


def _txt(ax, x, y, s, *, bold=False, size=FS, color=C_TXT, **kw):
    ax.text(x, y, s, fontproperties=_fp(bold, size), color=color, clip_on=False, **kw)


def _rounded(ax, x, y, w, h, facecolor, edgecolor, lw=LW, z=1, ls="-") -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle=f"round,pad=0,rounding_size={ROUND}",
            facecolor=facecolor,
            edgecolor=edgecolor,
            linewidth=lw,
            linestyle=ls,
            mutation_aspect=1.0,
            zorder=z,
            clip_on=False,
        )
    )


def header_bar(ax, x, y, w, h, theme: str, title: str | None = None) -> None:
    t = THEME[theme]
    _rounded(ax, x, y, w, h, t["bar"], t["bar"], z=3)
    _txt(
        ax,
        x + w / 2.0,
        y + h / 2.0,
        title if title is not None else t["name"].upper(),
        bold=True,
        size=FS_H,
        color=C_WHITE,
        ha="center",
        va="center",
        zorder=5,
    )


def card(ax, x, y, w, h, theme: str, title: str, lines, eq: str | None = None, dashed=False) -> None:
    t = THEME[theme]
    _rounded(
        ax, x, y, w, h, C_INNER, t["bar"], lw=0.85, z=6,
        ls=(0, (3.0, 2.2)) if dashed else "-",
    )
    n = 1 + len(lines)
    inset_r = 0.15 if eq else 0.0
    cx = x + (w - inset_r) / 2.0
    step = min(0.155, (h - 0.10) / max(n, 1))
    y0 = y + h / 2.0 + step * (n - 1) / 2.0
    _txt(ax, cx, y0, title, bold=True, size=FS, color=t["bar"], ha="center", va="center", zorder=8)
    for j, line in enumerate(lines):
        _txt(ax, cx, y0 - (j + 1) * step, line, size=FS, ha="center", va="center", zorder=8)
    if eq:
        _txt(ax, x + w - 0.050, y + 0.036, eq, size=FS_EQ, color=C_MUTED, ha="right", va="bottom", zorder=8)


def diamond(ax, cx, cy, w, h, theme: str, line1: str, line2: str | None = None) -> None:
    t = THEME[theme]
    pts = [(cx, cy + h / 2.0), (cx + w / 2.0, cy), (cx, cy - h / 2.0), (cx - w / 2.0, cy)]
    ax.add_patch(
        Polygon(pts, closed=True, facecolor=C_WHITE, edgecolor=t["bar"], linewidth=0.90, zorder=6, clip_on=False)
    )
    if line2:
        _txt(ax, cx, cy + 0.052, line1, size=FS, ha="center", va="center", zorder=8)
        _txt(ax, cx, cy - 0.052, line2, size=8.5, color=C_MUTED, ha="center", va="center", zorder=8)
    else:
        _txt(ax, cx, cy, line1, size=FS, ha="center", va="center", zorder=8)


def arrow(ax, p0, p1, color=C_EDGE, scale=12.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle="-|>",
            mutation_scale=scale,
            lw=1.15,
            color=color,
            shrinkA=1.0,
            shrinkB=1.2,
            zorder=10,
            clip_on=False,
        )
    )


def stack(ax, x, y, w, h, theme, specs, gap) -> list[tuple[float, float, float, float]]:
    """Draw stacked cards. Returns list of (x, y, w, h) top-to-bottom."""
    n = len(specs)
    ch = (h - (n - 1) * gap) / n
    boxes = []
    for i, spec in enumerate(specs):
        cy = y + (n - 1 - i) * (ch + gap)
        card(ax, x, cy, w, ch, theme, **spec)
        boxes.append((x, cy, w, ch))
    return boxes


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    apply_ieee_rc()
    fig = plt.figure(figsize=(W_FIG, H_FIG))
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
    ax.set_xlim(0.0, W_FIG)
    ax.set_ylim(0.0, H_FIG)
    ax.set_axis_off()
    ax.set_aspect("equal", adjustable="box")

    # Left gutter is reserved for (a)/(b) so they never sit on a bar.
    tag_w = 0.28
    margin_r = 0.10
    gutter = 0.26
    n_col = 4
    col_w = (W_FIG - tag_w - margin_r - (n_col - 1) * gutter) / n_col
    xs = [tag_w + i * (col_w + gutter) for i in range(n_col)]

    # ---- (a) Discovery ----------------------------------------------------
    hy = 2.58
    _txt(ax, 0.06, hy + HEADER_H / 2.0, "(a)", bold=True, size=11.0, ha="left", va="center")
    for x, th in zip(xs, ("sense", "estimate", "trigger", "control")):
        header_bar(ax, x, hy, col_w, HEADER_H, th)
    # Header-row arrows (stage pipeline)
    mid_h = hy + HEADER_H / 2.0
    for i in range(3):
        arrow(ax, (xs[i] + col_w + 0.01, mid_h), (xs[i + 1] - 0.01, mid_h))

    body_top = 2.50
    body_bot = 1.12
    body_h = body_top - body_bot
    gap2, gap3 = 0.10, 0.065

    sense_boxes = stack(
        ax,
        xs[0],
        body_bot,
        col_w,
        body_h,
        "sense",
        [
            dict(title="Poses", lines=[r"$(p_i,\dot{p}_i)$; ZOH $\dot{p}_j$"]),
            dict(
                title="Bellhop query",
                lines=[r"$z_k\leftarrow\mathrm{SNR}(p_i,p_j)$", r"every $dt=1\,\mathrm{s}$"],
                eq="(1)",
            ),
        ],
        gap2,
    )
    sx, sy, sw, sh = sense_boxes[0]
    _, s1y, _, s1h = sense_boxes[1]
    arrow(ax, (sx + sw / 2.0, sy), (sx + sw / 2.0, s1y + s1h), THEME["sense"]["bar"])

    ch_e = (body_h - gap2) / 2.0
    est_top = (xs[1], body_bot + ch_e + gap2, col_w, ch_e)
    est_bot = (xs[1], body_bot, col_w, ch_e)
    card(ax, *est_top, "estimate", "Corrected EKF", [r"$(\hat{x},P)$  predict / update"], eq="(12)")
    card(ax, *est_bot, "estimate", "Forecast", [r"$(x^{\mathrm{fc}},P^{\mathrm{fc}})$  predict only"], eq="(12)", dashed=True)
    _txt(
        ax,
        xs[1] + col_w / 2.0,
        body_bot + ch_e + gap2 / 2.0,
        r"shared predict (12)",
        size=8.5,
        color=C_MUTED,
        ha="center",
        va="center",
        zorder=9,
    )

    trig_boxes = stack(
        ax,
        xs[2],
        body_bot,
        col_w,
        body_h,
        "trigger",
        [
            dict(title=r"$e_k^{\mathrm{tr}}$", lines=[r"$z_k-\mathrm{SNR}(x^{\mathrm{fc}})$"], eq="(13)"),
            dict(title="Variance-capped", lines=[r"threshold $\varepsilon_k^{\mathrm{tr}}$"], eq="(14)"),
            dict(title="Persistence", lines=[r"$W=5$, $\rho=0.6$", r"$|e_k^{\mathrm{tr}}|\geq\varepsilon_k^{\mathrm{tr}}$"], eq="(15)"),
        ],
        gap3,
    )

    dcy = body_top - 0.20
    dcx = xs[3] + col_w / 2.0
    diamond(ax, dcx, dcy, 0.96, 0.36, "control", r"$0\to 1$?", "rising edge")
    rest_top = dcy - 0.22
    rest_h = rest_top - body_bot
    gap_c = 0.065
    ctrl_boxes = stack(
        ax,
        xs[3],
        body_bot,
        col_w,
        rest_h,
        "control",
        [
            dict(title="No", lines=["remain silent"]),
            dict(title="Yes", lines=[r"$j$ broadcasts once"]),
        ],
        gap_c,
    )
    c0x, c0y, c0w, c0h = ctrl_boxes[0]
    c1x, c1y, c1w, c1h = ctrl_boxes[1]
    arrow(ax, (dcx, dcy - 0.18), (dcx, c0y + c0h), THEME["control"]["bar"])
    arrow(ax, (dcx, c0y), (dcx, c1y + c1h), THEME["control"]["bar"])

    # Card-to-card flow in (a): Sense → Estimate → Trigger → Control
    flow_y = est_top[1] + est_top[3] / 2.0
    arrow(ax, (sense_boxes[0][0] + sense_boxes[0][2], flow_y), (est_top[0], flow_y))
    arrow(ax, (est_top[0] + est_top[2], flow_y), (trig_boxes[0][0], flow_y))
    # Trigger (innovation card) into the rising-edge diamond
    tx, ty, tw, th = trig_boxes[0]
    arrow(ax, (tx + tw, ty + th / 2.0), (dcx - 0.48, dcy))

    # ---- (b) Forwarding ---------------------------------------------------
    lane_x = tag_w
    lane_w = W_FIG - tag_w - margin_r
    fhy = 0.78
    _txt(ax, 0.06, fhy + HEADER_H / 2.0, "(b)", bold=True, size=11.0, ha="left", va="center")
    header_bar(ax, lane_x, fhy, lane_w, HEADER_H, "forward", "FORWARD  —  inherited LQARP Q-learning")

    fy, fh = 0.26, 0.46
    n_fw = 4
    gap_b = 0.18
    fw = (lane_w - (n_fw - 1) * gap_b) / n_fw
    fxs = [lane_x + i * (fw + gap_b) for i in range(n_fw)]
    cards_b = [
        dict(
            title=r"$I_{\mathrm{ELQTP}}$",
            lines=[r"$N_{\mathrm{range}}\cap N_{\mathrm{SNR}}$", r"$N_{\mathrm{depth}}\cap N_{\mathrm{stab}}$"],
            eq="(19)",
        ),
        dict(title=r"Reward $R$", lines=[r"$\beta_1=\beta_2=0$"], eq="(18)"),
        dict(title="TD Q-update", lines=[r"over $I_{\mathrm{ELQTP}}$"], eq="(6)"),
        dict(title="Next hop", lines=[r"$\arg\max Q$"]),
    ]
    for x, spec in zip(fxs, cards_b):
        card(ax, x, fy, fw, fh, "forward", **spec)
    for i in range(n_fw - 1):
        arrow(ax, (fxs[i] + fw + 0.01, fy + fh / 2.0), (fxs[i + 1] - 0.01, fy + fh / 2.0), THEME["forward"]["bar"])

    handles = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=C_BLUE, markeredgecolor=C_BLUE, markersize=8.0, label="Sense  —  new estimator"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=C_TEAL, markeredgecolor=C_TEAL, markersize=8.0, label="Estimate  —  new estimator"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=C_AMBER, markeredgecolor=C_AMBER, markersize=8.0, label="Trigger / Control  —  event trigger"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=C_GREY, markeredgecolor=C_GREY, markersize=8.0, label="Forward  —  inherited LQARP"),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        prop=_fp(size=8.5),
        handletextpad=0.35,
        columnspacing=1.05,
        bbox_to_anchor=(0.50, 0.000),
    )

    stem = os.path.join(OUT, "fig_mechanism")
    fig.savefig(stem + ".pdf")
    fig.savefig(stem + ".png", dpi=400)
    fig.savefig(stem + ".svg")
    fig.savefig(stem + ".eps")
    plt.close(fig)
    print("wrote", stem + ".{pdf,eps,png,svg}")


if __name__ == "__main__":
    main()
