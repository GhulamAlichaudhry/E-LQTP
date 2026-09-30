#!/usr/bin/env python3
"""Regenerate camera-ready figures in paper/figs/ from results CSVs."""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(os.path.dirname(__file__), "figs")

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "legend.fontsize": 7.5,
        "figure.dpi": 160,
    }
)


def tcrit(df):
    table = {14: 2.145, 19: 2.093, 29: 2.045}
    return table.get(df, 1.96)


def mean_ci(xs):
    xs = [float(x) for x in xs]
    n = len(xs)
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    s = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, tcrit(n - 1) * s / math.sqrt(n)


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def data_int(row, default=16.0):
    v = row.get("data_interval")
    if v in (None, ""):
        return default
    try:
        return float(v)
    except ValueError:
        return default


def scenario():
    fig, ax = plt.subplots(figsize=(3.5, 3.35))
    ax.add_patch(
        plt.Circle((0, 0), 1.0, fill=False, ls="--", color="0.35", lw=1.2, label=r"$R^{\star}$ (SNR gate)")
    )
    rng = np.random.default_rng(1)
    n_in, n_out = 5, 6
    ang_in = np.linspace(0.12, 0.12 + 2 * np.pi, n_in, endpoint=False) + rng.uniform(-0.12, 0.12, n_in)
    r_in = rng.uniform(0.62, 0.82, n_in)
    ang_out = np.linspace(0.31, 0.31 + 2 * np.pi, n_out, endpoint=False) + rng.uniform(-0.12, 0.12, n_out)
    r_out = rng.uniform(1.02, 1.10, n_out)
    ax.scatter([0], [0], marker="s", s=70, c="#c0392b", zorder=5, label="USV sink")
    ax.scatter(r_in * np.cos(ang_in), r_in * np.sin(ang_in), marker="o", s=42, c="#1f77b4", zorder=5, label="Inner AUV")
    ax.scatter(r_out * np.cos(ang_out), r_out * np.sin(ang_out), marker="^", s=48, c="#2ca02c", zorder=5, label="Outer AUV")
    i0 = int(np.argmin(np.abs(ang_out - ang_in[0])))
    ax.plot(
        [r_out[i0] * np.cos(ang_out[i0]), r_in[0] * np.cos(ang_in[0]), 0],
        [r_out[i0] * np.sin(ang_out[i0]), r_in[0] * np.sin(ang_in[0]), 0],
        color="#8e44ad",
        lw=1.4,
        zorder=4,
        label="2-hop data path",
    )
    ax.set_aspect("equal")
    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.set_xlabel(r"East range / $R^{\star}$")
    ax.set_ylabel(r"North range / $R^{\star}$")
    ax.legend(loc="upper right", framealpha=0.92, fontsize=6.5)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "scenario.png"), dpi=200)
    plt.close()


def discovery():
    path = os.path.join(ROOT, "results/phase1/batch_metrics.csv")
    if not os.path.isfile(path):
        return
    rows = [
        r
        for r in load(path)
        if (r.get("mac", "unslotted") or "unslotted") == "unslotted"
        and abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and abs(float(r.get("tMax") or 25) - 25) < 0.5
        and (r.get("fwd_policy") or "none") in ("none", "")
    ]
    by = defaultdict(list)
    for r in rows:
        by[r["mode"]].append(r)
    metrics = [
        ("recall", "Recall"),
        ("precision", "Precision"),
        ("control_bps", "Control rate (bit/s)"),
        ("up_delay", "Link-up delay (s)"),
        ("down_delay", "Link-down delay (s)"),
        ("hold_mae", "Hold-time MAE (s)"),
        ("phy_collisions", "PHY collisions / run"),
        ("frac_multihop", "Fraction of 2+ hop pairs"),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(7.2, 3.6))
    cols = {"periodic": "#1f4e79", "event": "#c0392b"}
    for ax, (key, title) in zip(axes.ravel(), metrics):
        xs, ys, ye, cc = [], [], [], []
        for j, mode in enumerate(("periodic", "event")):
            m, h = mean_ci([r[key] for r in by[mode]])
            xs.append(j)
            ys.append(m)
            ye.append(h)
            cc.append(cols[mode])
        ax.bar(xs, ys, yerr=ye, color=cc, capsize=3, width=0.62, error_kw={"elinewidth": 1.1})
        ax.set_xticks(xs)
        ax.set_xticklabels(["Periodic", "Event"], fontsize=7)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.3)
        if key == "control_bps":
            ax.axhline(2000, color="0.4", ls=":", lw=0.8)
            ax.set_ylim(0, 2200)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "discovery_ci.png"), dpi=200)
    plt.close()


def forwarding():
    path = os.path.join(ROOT, "results/phase2/fwd_metrics.csv")
    if not os.path.isfile(path):
        return
    rows = [
        r
        for r in load(path)
        if abs(float(r.get("n_nodes") or 12) - 12) < 0.5 and abs(data_int(r) - 16) < 0.5
    ]
    order = [
        (("event", "hold"), "ETHA", "#1e8449"),
        (("event", "snr"), "Event\n+SNR", "#1f4e79"),
        (("event", "depth"), "Event\n+Depth", "#b9770e"),
        (("periodic", "snr"), "Periodic\n+SNR", "#922b21"),
        (("periodic", "hold"), "Periodic\n+ETHA", "#c0392b"),
        (("event", "oracle"), "Oracle", "#6c3483"),
    ]
    fmetrics = [
        ("pdr", "Packet delivery ratio", (0, 1.05)),
        ("tx_energy_J", "Transmit energy (J)", None),
        ("control_bps", "Control rate (bit/s)", None),
        ("mean_e2e_s", "Mean e2e delay (s)", None),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.45))
    for ax, (key, title, ylim) in zip(axes, fmetrics):
        xs, ys, ye, cc, labs = [], [], [], [], []
        for j, (k, lab, col) in enumerate(order):
            sub = [r for r in rows if r.get("mode") == k[0] and r.get("fwd_policy") == k[1]]
            if not sub:
                continue
            m, h = mean_ci([r[key] for r in sub])
            xs.append(j)
            ys.append(m)
            ye.append(h)
            cc.append(col)
            labs.append(lab)
        ax.bar(xs, ys, yerr=ye, color=cc, capsize=2.5, width=0.72, error_kw={"elinewidth": 1.0})
        ax.set_xticks(xs)
        ax.set_xticklabels(labs, fontsize=6)
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.3)
        if ylim:
            ax.set_ylim(*ylim)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "forwarding_ci.png"), dpi=200)
    plt.close()


def tmax():
    path = os.path.join(ROOT, "results/phase1/ablation_metrics.csv")
    if not os.path.isfile(path):
        return
    ab = load(path)
    tmax_rows = [
        r
        for r in ab
        if r.get("mac") == "unslotted"
        and r.get("mode") == "event"
        and abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and abs(float(r.get("multipath_margin") or 30) - 30) < 0.5
    ]
    by_t = defaultdict(list)
    for r in tmax_rows:
        by_t[float(r["tMax"])].append(r)
    ts = sorted(by_t)
    fig, ax1 = plt.subplots(figsize=(3.5, 2.4))
    ax2 = ax1.twinx()
    rec, rec_e, bps, bps_e = [], [], [], []
    for t in ts:
        m, h = mean_ci([r["recall"] for r in by_t[t]])
        rec.append(m)
        rec_e.append(h)
        m, h = mean_ci([r["control_bps"] for r in by_t[t]])
        bps.append(m)
        bps_e.append(h)
    ax1.errorbar(ts, rec, yerr=rec_e, marker="o", color="#c0392b", capsize=3, label="Recall")
    ax2.errorbar(ts, bps, yerr=bps_e, marker="s", color="#1f4e79", capsize=3, label="Control bit/s")
    ax1.set_xlabel(r"$T_{\max}$ (s)")
    ax1.set_ylabel("Recall")
    ax2.set_ylabel("Control rate (bit/s)")
    ax1.set_ylim(0.78, 0.95)
    ax1.grid(True, alpha=0.3)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="center right", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "tmax_tradeoff.png"), dpi=200)
    plt.close()


def _thorp(f):
    f2 = f * f
    return 0.11 * f2 / (1.0 + f2) + 44.0 * f2 / (4100.0 + f2) + 2.75e-4 * f2 + 0.003


def _wenz_components(f, s=0.2, w=2.0):
    nt = 17.0 - 30.0 * np.log10(f)
    ns = 40.0 + 20.0 * (s - 0.5) + 26.0 * np.log10(f) - 60.0 * np.log10(f + 0.03)
    nw = 50.0 + 7.5 * np.sqrt(w) + 20.0 * np.log10(f) - 40.0 * np.log10(f + 0.4)
    nth = -15.0 + 20.0 * np.log10(f)
    return nt, ns, nw, nth


def _nl_db(f=24.0, b=1000.0, s=0.2, w=2.0):
    nt, ns, nw, nth = _wenz_components(f, s, w)
    n0 = sum(10 ** (x / 10.0) for x in (nt, ns, nw, nth))
    return 10.0 * np.log10(n0 * b)


def _tl(d, k=1.5, f=24.0, m=30.0):
    d = np.maximum(d, 1.0)
    return 10.0 * k * np.log10(d) + _thorp(f) * (d / 1000.0) + m


def _snr(d, sl=185.0, di=0.0):
    return sl - _tl(d) - _nl_db() + di


def _psucc(snr_db, l=400):
    snr_lin = 10 ** (np.asarray(snr_db, dtype=float) / 10.0)
    pe = 0.5 * np.array([math.erfc(math.sqrt(max(x, 0.0))) for x in snr_lin])
    pe = np.clip(pe, 0.0, 0.5)
    return (1.0 - pe) ** l


def channel():
    """LQARP-style acoustic system-model plots from the closed-form stack."""
    f = np.logspace(-1, 2, 400)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))

    ax = axes[0, 0]
    ax.semilogx(f, [_thorp(x) for x in f], color="#1f4e79", lw=1.6)
    ax.axvline(24.0, color="0.4", ls=":", lw=0.9)
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel(r"Thorp $\alpha(f)$ (dB/km)")
    ax.set_title("(a) Absorption")
    ax.grid(True, which="both", alpha=0.3)

    ax = axes[0, 1]
    nt, ns, nw, nth = _wenz_components(f)
    ax.semilogx(f, nt, label=r"$N_{\mathrm{t}}$", lw=1.2)
    ax.semilogx(f, ns, label=r"$N_{\mathrm{s}}$", lw=1.2)
    ax.semilogx(f, nw, label=r"$N_{\mathrm{w}}$", lw=1.2)
    ax.semilogx(f, nth, label=r"$N_{\mathrm{th}}$", lw=1.2)
    ax.axvline(24.0, color="0.4", ls=":", lw=0.9)
    ax.set_xlabel("Frequency (kHz)")
    ax.set_ylabel(r"Noise PSD (dB re $1\,\mu$Pa/Hz)")
    ax.set_title("(b) Wenz components")
    ax.legend(fontsize=6.5, loc="lower right")
    ax.grid(True, which="both", alpha=0.3)

    d = np.linspace(50.0, 8000.0, 400)
    ax = axes[1, 0]
    ax.plot(d / 1000.0, _tl(d), color="#c0392b", lw=1.6, label=r"$M=30$ dB")
    ax.plot(d / 1000.0, _tl(d, m=20.0), color="#1f4e79", ls="--", lw=1.2, label=r"$M=20$ dB")
    ax.plot(d / 1000.0, _tl(d, m=40.0), color="#1e8449", ls="-.", lw=1.2, label=r"$M=40$ dB")
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("TL (dB)")
    ax.set_title("(c) Transmission loss")
    ax.legend(fontsize=6.5)
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    snr = _snr(d)
    rstar = 4946.0
    ax.plot(d / 1000.0, snr, color="#1f4e79", lw=1.6, label="SNR")
    ax.axhline(8.68, color="#c0392b", ls="--", lw=1.0, label=r"$\gamma_{\mathrm{th}}=8.68$ dB")
    ax.axvline(rstar / 1000.0, color="0.35", ls=":", lw=1.0, label=r"$R^{\star}=4.95$ km")
    ax2 = ax.twinx()
    ax2.plot(d / 1000.0, _psucc(snr), color="#8e44ad", lw=1.4, label=r"$P_{\mathrm{succ}}$")
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("SNR (dB)")
    ax2.set_ylabel(r"$P_{\mathrm{succ}}$")
    ax.set_title("(d) SNR and packet success")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6.2, loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(-10, 55)
    ax2.set_ylim(-0.05, 1.05)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "channel.png"), dpi=200)
    plt.close()


def protocol():
    """ETHA architecture: discovery (left) and forwarding (right)."""
    fig, ax = plt.subplots(figsize=(7.2, 3.55))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec):
        p = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=fc, edgecolor=ec, lw=1.1, zorder=2,
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7, zorder=3)

    def arrow(x1, y1, x2, y2):
        ax.annotate(
            "", xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", color="0.2", lw=1.05),
            zorder=1,
        )

    ax.text(3.0, 9.55, "Event-triggered discovery", ha="center", fontsize=9, fontweight="bold")
    ax.text(9.0, 9.55, "Hold-aware forwarding", ha="center", fontsize=9, fontweight="bold")

    box(0.35, 7.55, 5.3, 1.55, "Hear HELLO on unslotted ALOHA\nSNR gate + BPSK packet success", "#d6eaf8", "#1f4e79")
    box(0.35, 5.35, 5.3, 1.55, "Update neighbor record\nEWMA SNR, slope, hold H", "#d5f5e3", "#1e8449")
    box(0.35, 3.15, 5.3, 1.55, "Send-on-delta: |ds| or |dp|\nelse keep-alive Tmax", "#fdebd0", "#b9770e")
    box(0.35, 0.95, 5.3, 1.55, "Broadcast padded HELLO\n(50 B, never flooded)", "#fadbd8", "#922b21")

    arrow(3.0, 7.55, 3.0, 6.90)
    arrow(3.0, 5.35, 3.0, 4.70)
    arrow(3.0, 3.15, 3.0, 2.50)

    box(6.35, 7.55, 5.3, 1.55, "Data packet toward USV sink\nprogress 40 m, SNR above threshold", "#d6eaf8", "#1f4e79")
    box(6.35, 5.35, 5.3, 1.55, "Hold filter H >= Hmin\nfallback if the set is empty", "#d5f5e3", "#1e8449")
    box(6.35, 3.15, 5.3, 1.55, "Depth-primary score S(j)\n(sink always preferred)", "#fdebd0", "#b9770e")
    box(6.35, 0.95, 5.3, 1.55, "Unicast next hop on ALOHA\nor drop (no-route)", "#fadbd8", "#922b21")

    arrow(9.0, 7.55, 9.0, 6.90)
    arrow(9.0, 5.35, 9.0, 4.70)
    arrow(9.0, 3.15, 9.0, 2.50)
    arrow(5.65, 6.12, 6.35, 6.12)

    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.04)
    fig.savefig(os.path.join(OUT, "protocol.png"), dpi=200)
    plt.close()


def holdpred():
    """Geometric hold versus remaining range (the useful part of the contour)."""
    delta = np.linspace(5.0, 1500.0, 300)
    fig, ax = plt.subplots(figsize=(3.5, 2.45))
    for vr, ls in ((0.3, "-"), (0.6, "--"), (1.0, "-."), (1.5, ":")):
        ax.plot(delta, np.minimum(delta / vr, 300.0), ls=ls, lw=1.5, label=rf"$v_r={vr:g}$ m/s")
    ax.axhline(8.0, color="#c0392b", ls=":", lw=1.0, label=r"$H_{\min}=8$ s")
    ax.set_xlabel(r"Remaining range $R^{\star}-d$ (m)")
    ax.set_ylabel(r"Geometric hold $H_{\mathrm{geom}}$ (s)")
    ax.set_xlim(0, 250)
    ax.set_ylim(0, 80)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "hold_time.png"), dpi=200)
    plt.close()


SERIES = (
    (("event", "depth"), "Event+Depth", "#b9770e", "s"),
    (("periodic", "snr"), "Periodic+SNR", "#922b21", "^"),
    (("event", "hold"), "ETHA", "#1e8449", "o"),
)


def _errorbars(ax, xs, key, grouped, xlabel, ylabel, ylim=None):
    for k, lab, col, mk in SERIES:
        px, ms, hs = [], [], []
        for x in xs:
            sub = grouped[x].get(k, [])
            if not sub:
                continue
            m, h = mean_ci([r[key] for r in sub])
            px.append(x)
            ms.append(m)
            hs.append(h)
        if px:
            ax.errorbar(px, ms, yerr=hs, marker=mk, color=col, capsize=3, label=lab)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if ylim:
        ax.set_ylim(*ylim)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6.5)


def scale():
    path = os.path.join(ROOT, "results/phase2/fwd_metrics.csv")
    if not os.path.isfile(path):
        return
    rows = [r for r in load(path) if abs(data_int(r) - 16) < 0.5]
    by_n = defaultdict(lambda: defaultdict(list))
    for r in rows:
        n = int(float(r.get("n_nodes") or 0))
        by_n[n][(r.get("mode"), r.get("fwd_policy"))].append(r)
    ns = sorted(by_n)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))
    _errorbars(axes[0, 0], ns, "pdr", by_n, "Number of nodes", "Packet delivery ratio", (0.45, 1.02))
    _errorbars(axes[0, 1], ns, "tx_energy_J", by_n, "Number of nodes", "Transmit energy (J)")
    _errorbars(axes[1, 0], ns, "mean_e2e_s", by_n, "Number of nodes", "Mean e2e delay (s)")
    _errorbars(axes[1, 1], ns, "mean_hops", by_n, "Number of nodes", "Mean hop count")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "pdr_vs_nodes.png"), dpi=200)
    plt.close()


def loadfig():
    path = os.path.join(ROOT, "results/phase2/fwd_metrics.csv")
    if not os.path.isfile(path):
        return
    rows = [r for r in load(path) if abs(float(r.get("n_nodes") or 12) - 12) < 0.5]
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[data_int(r)][(r.get("mode"), r.get("fwd_policy"))].append(r)
    if len(by) < 2:
        return
    xs = sorted(by)
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.2))
    _errorbars(axes[0, 0], xs, "pdr", by, "Packet interval (s)", "Packet delivery ratio", (0.45, 1.02))
    _errorbars(axes[0, 1], xs, "tx_energy_J", by, "Packet interval (s)", "Transmit energy (J)")
    _errorbars(axes[1, 0], xs, "mean_e2e_s", by, "Packet interval (s)", "Mean e2e delay (s)")
    _errorbars(axes[1, 1], xs, "control_bps", by, "Packet interval (s)", "Control rate (bit/s)")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "load_tradeoff.png"), dpi=200)
    plt.close()


def network_architecture():
    """Side-view schematic of the USV--AUV acoustic network (no measured data)."""
    fig, ax = plt.subplots(figsize=(7.16, 4.05))
    ax.set_xlim(0.0, 14.4)
    ax.set_ylim(-0.05, 7.55)
    ax.axis("off")

    ax.add_patch(plt.Rectangle((0.35, 1.15), 13.55, 4.95, facecolor="#d4e6f1",
                               edgecolor="#1a5276", lw=1.05, zorder=0))
    ax.fill_between([0.35, 13.90], 5.72, 6.10, color="#a9cce3", zorder=1)
    ax.plot([0.35, 13.90], [5.72, 5.72], color="#1a5276", lw=1.4, zorder=2)
    ax.text(0.50, 5.88, "sea surface", fontsize=7.0, color="#1a5276", va="center")

    def usv(x, y):
        hull = plt.Polygon(
            [(x - 0.58, y), (x + 0.72, y), (x + 0.50, y + 0.30), (x - 0.40, y + 0.30)],
            closed=True, facecolor="#c0392b", edgecolor="#7b241c", lw=0.9, zorder=5,
        )
        cabin = plt.Rectangle((x - 0.10, y + 0.30), 0.44, 0.22, facecolor="#922b21",
                              edgecolor="#7b241c", lw=0.7, zorder=6)
        ax.add_patch(hull)
        ax.add_patch(cabin)
        ax.plot([x + 0.10, x + 0.10], [y + 0.52, y + 0.80], color="#7b241c", lw=1.1, zorder=6)
        ax.plot([x + 0.10, x + 0.32], [y + 0.80, y + 0.64], color="#7b241c", lw=1.1, zorder=6)
        ax.plot([x, x], [y, y - 0.22], color="#7b241c", lw=1.0, zorder=6)
        ax.plot(x, y - 0.28, marker="v", color="#7b241c", markersize=5, zorder=6)

    usv(7.20, 5.72)
    ax.text(7.20, 7.22, "USV sink", ha="center", fontsize=8.4, fontweight="bold", color="#7b241c")
    ax.text(7.20, 6.92, r"surface gateway $\cdot$ destination of all DATA", ha="center",
            fontsize=6.6, color="#7b241c")

    inner = [(3.35, 3.70, "I1"), (5.15, 4.05, "I2"), (9.15, 3.85, "I3"), (10.95, 4.20, "I4")]
    outer = [(3.55, 1.85, "O1"), (5.35, 1.70, "O2"), (9.35, 1.80, "O3"), (11.15, 1.95, "O4")]
    for x, y, lab in inner:
        ax.add_patch(plt.Circle((x, y), 0.27, facecolor="#1f4e79", edgecolor="#0e2f4a", lw=0.8, zorder=5))
        ax.text(x, y, lab, ha="center", va="center", fontsize=6.3, color="white", zorder=6, fontweight="bold")
    for x, y, lab in outer:
        ax.add_patch(plt.Circle((x, y), 0.27, facecolor="#1e8449", edgecolor="#145a32", lw=0.8, zorder=5))
        ax.text(x, y, lab, ha="center", va="center", fontsize=6.3, color="white", zorder=6, fontweight="bold")

    for x, y, _ in inner:
        ax.plot([7.20, x], [5.50, y + 0.27], color="#7d3c98", ls=(0, (3.5, 2.2)), lw=1.05, zorder=3)

    ax.annotate("", xy=(5.15, 3.78), xytext=(5.35, 1.97),
                arrowprops=dict(arrowstyle="-|>", color="#1a5276", lw=1.4), zorder=4)
    ax.annotate("", xy=(7.20, 5.50), xytext=(5.15, 4.32),
                arrowprops=dict(arrowstyle="-|>", color="#1a5276", lw=1.4), zorder=4)
    ax.annotate("", xy=(9.15, 3.58), xytext=(9.35, 2.07),
                arrowprops=dict(arrowstyle="-|>", color="#1a5276", lw=1.4), zorder=4)
    ax.annotate("", xy=(7.20, 5.50), xytext=(9.15, 4.12),
                arrowprops=dict(arrowstyle="-|>", color="#1a5276", lw=1.4), zorder=4)
    ax.text(4.55, 2.85, "DATA", fontsize=6.6, color="#1a5276", rotation=78)
    ax.text(9.85, 2.90, "DATA", fontsize=6.6, color="#1a5276", rotation=-78)

    hx, hy = 3.55, 1.85
    for ang, rr in ((18, 0.95), (55, 0.85), (95, 0.80)):
        rad = np.deg2rad(ang)
        ax.annotate("", xy=(hx + rr * np.cos(rad), hy + rr * np.sin(rad)), xytext=(hx + 0.30 * np.cos(rad), hy + 0.30 * np.sin(rad)),
                    arrowprops=dict(arrowstyle="->", color="#b9770e", lw=1.05), zorder=4)
    ax.text(3.55, 2.85, "HELLO", ha="center", fontsize=6.5, color="#b9770e")

    ax.annotate("", xy=(13.15, 3.55), xytext=(12.05, 3.55),
                arrowprops=dict(arrowstyle="->", color="#1a5276", lw=1.15))
    ax.annotate("", xy=(13.15, 3.15), xytext=(12.05, 3.35),
                arrowprops=dict(arrowstyle="->", color="#1a5276", lw=1.0))
    ax.text(13.28, 3.35, "MCM\ncurrent", fontsize=6.3, color="#1a5276", va="center")

    ax.annotate("", xy=(0.72, 1.55), xytext=(0.72, 5.72),
                arrowprops=dict(arrowstyle="<->", color="0.25", lw=1.0))
    ax.text(0.90, 3.70, "depth", fontsize=6.5, rotation=90, va="center", color="0.25")
    ax.text(0.92, 5.40, "USV", fontsize=6.1, color="0.25")
    ax.text(0.92, 1.70, "AUV", fontsize=6.1, color="0.25")

    ax.plot([2.10, 3.55], [3.70, 3.70], color="#1f4e79", lw=0.8, ls=":")
    ax.text(1.95, 3.70, "inner ring", fontsize=6.2, color="#1f4e79", ha="right", va="center")
    ax.plot([2.10, 3.55], [1.85, 1.85], color="#1e8449", lw=0.8, ls=":")
    ax.text(1.95, 1.85, "outer ring", fontsize=6.2, color="#1e8449", ha="right", va="center")

    ax.text(7.15, 0.78,
            r"Half-duplex $\cdot$ one $24$ kHz carrier $\cdot$ $1$ kbps BPSK $\cdot$ unslotted ALOHA",
            ha="center", fontsize=7.1, color="#1a5276")
    ax.plot([0.70, 1.45], [0.32, 0.32], color="#7d3c98", ls=(0, (3.5, 2.2)), lw=1.2)
    ax.text(1.55, 0.32, "in-range hop", va="center", fontsize=6.5, color="#7d3c98")
    ax.annotate("", xy=(4.55, 0.32), xytext=(3.85, 0.32),
                arrowprops=dict(arrowstyle="-|>", color="#1a5276", lw=1.2))
    ax.text(4.65, 0.32, "DATA unicast", va="center", fontsize=6.5, color="#1a5276")
    ax.annotate("", xy=(7.55, 0.32), xytext=(6.85, 0.32),
                arrowprops=dict(arrowstyle="->", color="#b9770e", lw=1.1))
    ax.text(7.65, 0.32, "HELLO broadcast", va="center", fontsize=6.5, color="#b9770e")
    ax.scatter([10.55], [0.32], marker="o", s=32, c="#1f4e79", zorder=5)
    ax.text(10.75, 0.32, "inner AUV", va="center", fontsize=6.5)
    ax.scatter([12.35], [0.32], marker="o", s=32, c="#1e8449", zorder=5)
    ax.text(12.55, 0.32, "outer AUV", va="center", fontsize=6.5)

    fig.subplots_adjust(left=0.01, right=0.995, top=0.99, bottom=0.02)
    fig.savefig(os.path.join(OUT, "network_arch.png"), dpi=220)
    plt.close()


def qlearning_framework():
    """Watkins Q-learning loop as used by QELAR/LQARP. Pedagogical; no trained table."""
    fig, ax = plt.subplots(figsize=(7.16, 3.70))
    ax.set_xlim(0.0, 12.6)
    ax.set_ylim(0.0, 8.35)
    ax.axis("off")

    def box(x, y, w, h, text, fc, ec, fs=7.1):
        p = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
            facecolor=fc, edgecolor=ec, lw=1.15, zorder=2,
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=3)

    ax.text(6.3, 8.05, "Q-learning routing loop (Watkins)", ha="center", fontsize=9.2, fontweight="bold")

    box(0.40, 5.45, 3.70, 2.05,
        "Agent (current node $i$)\n"
        r"$\pi(s)=\arg\max_{a} Q(s,a)$",
        "#d6eaf8", "#1f4e79", 7.3)
    box(8.50, 5.45, 3.70, 2.05,
        "Environment $\\mathcal{G}(t)$\n"
        "ALOHA, SNR gate, energy",
        "#fdebd0", "#b9770e", 7.3)
    box(3.55, 3.05, 5.50, 1.70,
        "Watkins update\n"
        r"$Q(s,a)\leftarrow(1-\alpha_Q)Q(s,a)+\alpha_Q[r+\eta\max_{a'} Q(s',a')]$",
        "#d5f5e3", "#1e8449", 7.0)
    box(0.40, 0.85, 3.70, 1.70,
        "State $s$: node $i$\n"
        r"Action $a$: next hop $j$",
        "#fadbd8", "#922b21", 7.1)
    box(8.50, 0.85, 3.70, 1.70,
        "Reward $r(s,a)$\n"
        "link quality, depth, energy",
        "#e8daef", "#6c3483", 7.1)

    ax.annotate("", xy=(8.50, 6.85), xytext=(4.10, 6.85),
                arrowprops=dict(arrowstyle="-|>", color="0.15", lw=1.2), zorder=1)
    ax.text(6.30, 7.12, r"action $a=$ next hop $j$", ha="center", fontsize=6.7)
    ax.annotate("", xy=(4.10, 6.05), xytext=(8.50, 6.05),
                arrowprops=dict(arrowstyle="-|>", color="0.15", lw=1.2), zorder=1)
    ax.text(6.30, 5.72, r"next state $s'$, scalar reward $r$", ha="center", fontsize=6.7)

    ax.annotate("", xy=(6.30, 4.75), xytext=(6.30, 5.45),
                arrowprops=dict(arrowstyle="-|>", color="0.15", lw=1.15), zorder=1)
    ax.annotate("", xy=(4.10, 2.55), xytext=(4.70, 3.05),
                arrowprops=dict(arrowstyle="-|>", color="0.15", lw=1.05), zorder=1)
    ax.annotate("", xy=(8.50, 2.55), xytext=(7.90, 3.05),
                arrowprops=dict(arrowstyle="-|>", color="0.15", lw=1.05), zorder=1)

    ax.text(6.30, 0.28,
            r"Feasible actions: $a\in\widehat{\mathcal{N}}_i(t)$. Unheard nodes are not in the Q-table.",
            ha="center", fontsize=7.1, color="#922b21")

    fig.subplots_adjust(left=0.015, right=0.985, top=0.96, bottom=0.03)
    fig.savefig(os.path.join(OUT, "qlearning.png"), dpi=220)
    plt.close()


def void_area():
    """Schematic of a geographic/depth void. Not a measured Aqua-Sim layout."""
    fig, ax = plt.subplots(figsize=(3.55, 3.70))
    ax.set_xlim(-0.08, 1.18)
    ax.set_ylim(-0.16, 1.20)
    ax.set_aspect("equal")
    ax.axis("off")

    void = plt.Circle((0.52, 0.46), 0.27, facecolor="#fadbd8", edgecolor="#922b21",
                      lw=1.2, ls="--", zorder=1)
    ax.add_patch(void)
    ax.text(0.52, 0.46, "void", ha="center", va="center", fontsize=8.2,
            color="#922b21", fontweight="bold", zorder=2)

    sink = (0.52, 1.08)
    n1, n2, n3 = (0.22, 0.86), (0.52, 0.90), (0.82, 0.86)
    k = (0.08, 0.62)
    i = (0.52, 0.14)
    b1, b2 = (0.28, 0.30), (0.76, 0.30)

    ax.scatter(*sink, marker="s", s=92, c="#c0392b", zorder=5)
    ax.text(sink[0] + 0.07, sink[1], "USV sink", fontsize=7.0, va="center", color="#7b241c")
    for p in (n1, n2, n3):
        ax.scatter(*p, marker="o", s=54, c="#1f4e79", zorder=5)
    ax.scatter(*k, marker="o", s=64, c="#b9770e", zorder=5)
    ax.scatter(*i, marker="D", s=78, c="#6c3483", zorder=6)
    ax.scatter(*b1, marker="o", s=50, c="#1e8449", zorder=5)
    ax.scatter(*b2, marker="o", s=50, c="#1e8449", zorder=5)

    ax.text(i[0] + 0.07, i[1] - 0.01, r"$i$ (local min.)", fontsize=6.8, color="#6c3483", va="center")
    ax.text(k[0] - 0.01, k[1] + 0.07, r"$k$", fontsize=7.2, color="#b9770e")
    ax.text(n2[0] + 0.08, n2[1] + 0.02, "progress\nneighbors", fontsize=6.1, color="#1f4e79", va="bottom")
    ax.text(b2[0] + 0.07, b2[1], "no geographic\nprogress", fontsize=6.0, color="#1e8449", va="center")

    ax.annotate("", xy=b1, xytext=i,
                arrowprops=dict(arrowstyle="->", color="#1e8449", lw=1.05), zorder=3)
    ax.annotate("", xy=b2, xytext=i,
                arrowprops=dict(arrowstyle="->", color="#1e8449", lw=1.05), zorder=3)
    ax.annotate("", xy=n2, xytext=i,
                arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.05, ls=(0, (3, 2))), zorder=3)
    ax.text(0.63, 0.52, "greedy\nfails", fontsize=6.1, color="#c0392b")

    ax.annotate("", xy=k, xytext=i,
                arrowprops=dict(arrowstyle="-|>", color="#b9770e", lw=1.45), zorder=4)
    ax.annotate("", xy=n1, xytext=k,
                arrowprops=dict(arrowstyle="-|>", color="#b9770e", lw=1.45), zorder=4)
    ax.annotate("", xy=sink, xytext=n1,
                arrowprops=dict(arrowstyle="-|>", color="#b9770e", lw=1.45), zorder=4)
    ax.text(0.00, 0.86, "detour", fontsize=6.6, color="#b9770e")

    ax.plot([n1[0], n2[0], n3[0]], [n1[1], n2[1], n3[1]], color="#1f4e79", lw=0.7, ls=":", zorder=2)
    ax.plot([n1[0], sink[0], n3[0]], [n1[1], sink[1], n3[1]], color="#1f4e79", lw=0.7, ls=":", zorder=2)

    ax.text(0.52, -0.12,
            r"No neighbor of $i$ reduces depth or range to the sink.",
            ha="center", fontsize=6.3, color="0.3")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "void_area.png"), dpi=220, bbox_inches="tight")
    plt.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    qlearning_framework()
    void_area()
    scenario()
    channel()
    protocol()
    holdpred()
    discovery()
    forwarding()
    tmax()
    scale()
    loadfig()
    print("wrote", OUT, sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
