#!/usr/bin/env python3
"""Fig. 2 — Relay velocity fields (IEEE IoT-J, two-column).

Bare panel tags (a) / (b) only. Rebuild:
  python3 paper/fig2_mobility_fields.py

Outputs (no post-edit):
  paper/elqtp_figs/fig2_mobility_fields.{pdf,eps,png}
  paper/elqtp_figs/fig2_node_positions.csv

AREA_KM is the single deployment-size constant. It currently matches
kVolumeXyM = 6000 m in scenario-i-lqarp.cc; change it here only if the
confirmed simulation domain differs.
"""
from __future__ import annotations

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "elqtp_figs")

# --- single-place geometry (edit here only) ---
AREA_KM = 6.0
N_RELAY = 40
R_CORE_KM = 2.0  # 2000 m
V_EDDY = 2.0  # m/s at the core boundary
MIN_SEP_KM = 0.45
ARROW_MAX_KM = 0.46
HEAD_W_KM = 0.10
HEAD_L_KM = 0.12
ARROW_CLEAR_KM = 0.17
MARKER_R_KM = 0.085
RNG_SEED = 20260921
DRIFT_AZ = np.deg2rad(35.0)

SINK = np.array([AREA_KM / 2.0, AREA_KM / 2.0])
# Pad past the longest shaft+head, then keep nodes inside [0, AREA_KM]
# far enough that every arrowhead stays in frame.
AXIS_PAD_KM = ARROW_MAX_KM + HEAD_L_KM + 0.08
EDGE_MARGIN_KM = ARROW_MAX_KM + 0.08

C_NODE = "#0F4C81"
C_ARROW = "#D55E00"
C_CORE = "#009E73"


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
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.bbox": None,
            "savefig.pad_inches": 0.02,
        }
    )


def v_uniform() -> np.ndarray:
    return V_EDDY * np.array([np.cos(DRIFT_AZ), np.sin(DRIFT_AZ)])


def v_rankine(xy: np.ndarray) -> np.ndarray:
    """Solid-body inside R_core; 1/r decay outside. Counterclockwise."""
    d = xy - SINK
    r = np.linalg.norm(d, axis=1)
    r_safe = np.maximum(r, 1e-12)
    e_th = np.column_stack((-d[:, 1] / r_safe, d[:, 0] / r_safe))
    inside = r <= R_CORE_KM
    vth = np.empty_like(r)
    vth[inside] = V_EDDY * (r[inside] / R_CORE_KM)
    vth[~inside] = V_EDDY * (R_CORE_KM / r_safe[~inside])
    vth[r < 1e-12] = 0.0
    return e_th * vth[:, None]


def arrow_km(vel_mps: np.ndarray) -> np.ndarray:
    """Map speed to a km displacement; |v|=V_EDDY -> ARROW_MAX_KM."""
    return (vel_mps / V_EDDY) * ARROW_MAX_KM


def _orient(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def _on_seg(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
    return (
        min(a[0], b[0]) - 1e-12 <= c[0] <= max(a[0], b[0]) + 1e-12
        and min(a[1], b[1]) - 1e-12 <= c[1] <= max(a[1], b[1]) + 1e-12
    )


def _segments_intersect(p1: np.ndarray, p2: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> bool:
    o1, o2 = _orient(p1, p2, q1), _orient(p1, p2, q2)
    o3, o4 = _orient(q1, q2, p1), _orient(q1, q2, p2)
    if (o1 == 0 and _on_seg(p1, p2, q1)) or (o2 == 0 and _on_seg(p1, p2, q2)):
        return True
    if (o3 == 0 and _on_seg(q1, q2, p1)) or (o4 == 0 and _on_seg(q1, q2, p2)):
        return True
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def _point_seg_dist(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    ab = b - a
    den = float(np.dot(ab, ab))
    if den < 1e-18:
        return float(np.linalg.norm(p - a))
    t = float(np.clip(np.dot(p - a, ab) / den, 0.0, 1.0))
    return float(np.linalg.norm(p - (a + t * ab)))


def _seg_seg_dist(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> float:
    if _segments_intersect(a, b, c, d):
        return 0.0
    return min(
        _point_seg_dist(a, c, d),
        _point_seg_dist(b, c, d),
        _point_seg_dist(c, a, b),
        _point_seg_dist(d, a, b),
    )


def _arrows_conflict(xy: np.ndarray, vel: np.ndarray) -> bool:
    """True if any two shafts/heads would merge or a shaft hits a marker."""
    dxy = arrow_km(vel)
    n = len(xy)
    tips = xy + dxy
    for i in range(n):
        if _point_seg_dist(SINK, xy[i], tips[i]) < ARROW_CLEAR_KM:
            return True
        for j in range(i + 1, n):
            if _seg_seg_dist(xy[i], tips[i], xy[j], tips[j]) < ARROW_CLEAR_KM:
                return True
            if _point_seg_dist(xy[j], xy[i], tips[i]) < ARROW_CLEAR_KM:
                return True
            if _point_seg_dist(xy[i], xy[j], tips[j]) < ARROW_CLEAR_KM:
                return True
    return False


def place_relays() -> np.ndarray:
    """N=40, scattered, min pairwise separation, no merging arrows."""
    rng = np.random.default_rng(RNG_SEED)
    lo, hi = EDGE_MARGIN_KM, AREA_KM - EDGE_MARGIN_KM
    vu1 = v_uniform()
    pts: list[np.ndarray] = []
    attempts = 0
    while len(pts) < N_RELAY and attempts < 400000:
        attempts += 1
        p = rng.uniform(lo, hi, size=2)
        if float(np.linalg.norm(p - SINK)) < MIN_SEP_KM:
            continue
        if any(float(np.linalg.norm(p - q)) < MIN_SEP_KM for q in pts):
            continue
        cand = np.vstack([pts, p]) if pts else p.reshape(1, 2)
        vu = np.repeat(vu1[None, :], len(cand), axis=0)
        vr = v_rankine(cand)
        if _arrows_conflict(cand, vu) or _arrows_conflict(cand, vr):
            continue
        pts.append(p)
    if len(pts) < N_RELAY:
        raise RuntimeError(
            "could not place %d relays with min sep %.2f km after %d tries"
            % (N_RELAY, MIN_SEP_KM, attempts)
        )
    return np.asarray(pts)


def save_csv(path: str, xy: np.ndarray, vu: np.ndarray, vr: np.ndarray) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "role",
                "x_km",
                "y_km",
                "vx_a_mps",
                "vy_a_mps",
                "vx_b_mps",
                "vy_b_mps",
            ]
        )
        w.writerow(["sink", "sink", SINK[0], SINK[1], 0.0, 0.0, 0.0, 0.0])
        for i, (p, a, b) in enumerate(zip(xy, vu, vr), start=1):
            w.writerow([i, "relay", p[0], p[1], a[0], a[1], b[0], b[1]])


def _tick_label(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ("%.3g" % v)


def style_ax(ax, tag: str) -> None:
    lo, hi = -AXIS_PAD_KM, AREA_KM + AXIS_PAD_KM
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")
    ticks = [0.0, AREA_KM / 2.0, AREA_KM]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([_tick_label(t) for t in ticks])
    ax.set_yticklabels([_tick_label(t) for t in ticks])
    ax.set_xlabel("East x (km)", fontsize=8)
    ax.set_ylabel("North y (km)", fontsize=8)
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
    ax.tick_params(labelsize=8, length=3.0, width=0.6, pad=2, labelleft=True, labelbottom=True)
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)
        spine.set_color("black")


def draw_nodes(ax, xy: np.ndarray) -> None:
    ax.scatter(xy[:, 0], xy[:, 1], s=18, c=C_NODE, marker="o", zorder=4, linewidths=0.0)
    ax.scatter([SINK[0]], [SINK[1]], s=40, c=C_NODE, marker="s", zorder=5, linewidths=0.0)
    # Plain marker label (not a box). Offset chosen away from nearby relays.
    ax.text(
        SINK[0] + 0.14,
        SINK[1] + 0.18,
        "Sink",
        fontsize=8,
        color=C_NODE,
        ha="left",
        va="bottom",
        zorder=6,
    )


def draw_arrows(ax, xy: np.ndarray, vel_mps: np.ndarray) -> None:
    dxy = arrow_km(vel_mps)
    length = np.hypot(dxy[:, 0], dxy[:, 1])
    ok = length >= 0.04
    if not np.any(ok):
        return
    ux = np.zeros_like(length)
    uy = np.zeros_like(length)
    ux[ok] = dxy[ok, 0] / length[ok]
    uy[ok] = dxy[ok, 1] / length[ok]
    # Start just outside the marker so the shaft is not hidden under the dot.
    x0 = xy[ok, 0] + MARKER_R_KM * ux[ok]
    y0 = xy[ok, 1] + MARKER_R_KM * uy[ok]
    dx = dxy[ok, 0] - MARKER_R_KM * ux[ok]
    dy = dxy[ok, 1] - MARKER_R_KM * uy[ok]
    ax.quiver(
        x0,
        y0,
        dx,
        dy,
        color=C_ARROW,
        angles="xy",
        scale_units="xy",
        scale=1.0,
        width=0.0062,
        headwidth=3.2,
        headlength=4.0,
        headaxislength=3.4,
        minshaft=1.5,
        zorder=3,
        pivot="tail",
    )


def assert_layout(xy: np.ndarray, vu: np.ndarray, vr: np.ndarray) -> None:
    dmin = 1e9
    for i in range(len(xy)):
        dmin = min(dmin, float(np.linalg.norm(xy[i] - SINK)))
        for j in range(i + 1, len(xy)):
            dmin = min(dmin, float(np.linalg.norm(xy[i] - xy[j])))
    if dmin + 1e-9 < MIN_SEP_KM:
        raise RuntimeError("min separation %.3f km < %.3f" % (dmin, MIN_SEP_KM))
    if _arrows_conflict(xy, vu) or _arrows_conflict(xy, vr):
        raise RuntimeError("arrow shafts overlap or hit a marker")

    lo, hi = -AXIS_PAD_KM, AREA_KM + AXIS_PAD_KM
    for vel in (vu, vr):
        dxy = arrow_km(vel)
        tips = xy + dxy
        # Include a head-width margin so the arrowhead stays inside the frame.
        pad = 0.5 * HEAD_W_KM
        if np.any(tips[:, 0] < lo + pad) or np.any(tips[:, 0] > hi - pad):
            raise RuntimeError("arrow clipped on x")
        if np.any(tips[:, 1] < lo + pad) or np.any(tips[:, 1] > hi - pad):
            raise RuntimeError("arrow clipped on y")
        if np.any(xy[:, 0] < lo + pad) or np.any(xy[:, 0] > hi - pad):
            raise RuntimeError("node clipped on x")
        if np.any(xy[:, 1] < lo + pad) or np.any(xy[:, 1] > hi - pad):
            raise RuntimeError("node clipped on y")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    apply_ieee_rc()

    xy = place_relays()
    vu = np.repeat(v_uniform()[None, :], len(xy), axis=0)
    vr = v_rankine(xy)
    assert_layout(xy, vu, vr)
    csv_path = os.path.join(OUT, "fig2_node_positions.csv")
    save_csv(csv_path, xy, vu, vr)

    fig, axes = plt.subplots(1, 2, figsize=(7.16, 3.05), sharey=False)
    fig.subplots_adjust(left=0.088, right=0.985, top=0.88, bottom=0.20, wspace=0.30)

    style_ax(axes[0], "(a)")
    draw_arrows(axes[0], xy, vu)
    draw_nodes(axes[0], xy)

    style_ax(axes[1], "(b)")
    core = Circle(
        (SINK[0], SINK[1]),
        R_CORE_KM,
        fill=False,
        edgecolor=C_CORE,
        linestyle=(0, (4.0, 2.4)),
        linewidth=0.7,
        zorder=2,
    )
    axes[1].add_patch(core)
    draw_arrows(axes[1], xy, vr)
    draw_nodes(axes[1], xy)

    handles = [
        Line2D([0], [0], marker="s", color="none", markerfacecolor=C_NODE, markersize=7, label="Sink"),
        Line2D(
            [0], [0], marker="o", color="none", markerfacecolor=C_NODE, markersize=6.5, label="Relay node"
        ),
        Line2D([0], [0], color=C_ARROW, lw=1.15, label="Velocity vector"),
        Line2D(
            [0],
            [0],
            color=C_CORE,
            lw=0.9,
            ls=(0, (4.0, 2.4)),
            label=r"$R_{\mathrm{core}}$ (panel (b) only)",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=8,
        handlelength=2.0,
        columnspacing=1.35,
        bbox_to_anchor=(0.5, 0.015),
    )

    stem = os.path.join(OUT, "fig2_mobility_fields")
    fig.savefig(stem + ".pdf")
    fig.savefig(stem + ".png", dpi=300)
    fig.savefig(stem + ".svg")
    fig.savefig(stem + ".eps")
    plt.close(fig)
    print("wrote", stem + ".{pdf,eps,png,svg}")
    print("wrote", csv_path, "N=%d AREA_KM=%.3f" % (len(xy), AREA_KM))


if __name__ == "__main__":
    main()
