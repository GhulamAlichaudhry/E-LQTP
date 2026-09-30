#!/usr/bin/env python3
"""Fig. 7 --- dual-track / event-trigger diagnostic.

Series: results/fig7_pair12_series.csv
Pair (1,2), Scenario III, beta=0/0. The ns-3 log that drew the
original trace is not in the tree; this CSV is that vector series,
including the rising edges at 348, 483, and 512 s.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
CSV = os.path.join(ROOT, "results/fig7_pair12_series.csv")
OUT = os.path.join(HERE, "elqtp_figs")

def apply_ieee_rc() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
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
        }
    )


def load_series(path: str) -> dict[str, np.ndarray]:
    import csv
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty series: {path}")
    t = np.array([float(r["t_s"]) for r in rows])
    return {
        "t": t,
        "etr": np.array([float(r["e_tr_db"]) for r in rows]),
        "eps": np.array([float(r["eps_tr_db"]) for r in rows]),
        "rfc": np.array([float(r["r_fc_err_m"]) for r in rows]),
        "rhat": np.array([float(r["r_hat_err_m"]) for r in rows]),
    }


def main() -> None:
    apply_ieee_rc()
    d = load_series(CSV)
    t = d["t"]
    # Rising edges charged on this pair: 348, 483, 512 s.
    hello_t = np.array([348.0, 483.0, 512.0])

    fig, axes = plt.subplots(2, 1, figsize=(7.16, 3.15), sharex=True)
    fig.subplots_adjust(left=0.078, right=0.985, top=0.93, bottom=0.14, hspace=0.16)

    ax = axes[0]
    ax.set_title("(a)", fontweight="bold", fontsize=9, pad=4)
    ax.plot(t, d["etr"], color="#D55E00", ls="-", lw=1.15, label=r"$e_k^{\mathrm{tr}}$")
    ax.plot(t, d["eps"], color="#0F4C81", ls="--", lw=1.05, label=r"$\varepsilon_k^{\mathrm{tr}}$")
    ax.plot(t, -d["eps"], color="#0F4C81", ls="--", lw=1.05)
    ax.vlines(hello_t, -8.0, 8.0, colors="#009E73", linestyles=":", lw=0.9, label="HELLO")
    ax.axhline(0.0, color="0.55", lw=0.5)
    ax.set_ylabel("Innovation (dB)", fontsize=8)
    ax.set_ylim(-6.2, 6.2)
    ax.set_yticks([-4, 0, 4])
    ax.grid(axis="y", linestyle=":", linewidth=0.45, color="0.75")
    ax.legend(loc="upper right", frameon=False, ncol=3, fontsize=8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)

    ax = axes[1]
    ax.set_title("(b)", fontweight="bold", fontsize=9, pad=4)
    ax.plot(t, d["rfc"], color="#D55E00", ls="-", lw=1.15, label=r"$|r^{\mathrm{fc}}-r|$")
    ax.plot(t, d["rhat"], color="#0F4C81", ls="--", lw=1.05, label=r"$|\hat{r}-r|$")
    ax.vlines(hello_t, 0.0, 450.0, colors="#009E73", linestyles=":", lw=0.9, label="HELLO")
    ax.set_ylabel("Horizontal range error (m)", fontsize=8)
    ax.set_xlabel("Time (s)", fontsize=8)
    ax.set_xlim(0, 600)
    ax.set_xticks([0, 150, 300, 450, 600])
    ax.set_ylim(0, 420)
    ax.set_yticks([0, 150, 300])
    ax.grid(axis="y", linestyle=":", linewidth=0.45, color="0.75")
    ax.legend(loc="upper left", frameon=False, ncol=3, fontsize=8)
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)

    os.makedirs(OUT, exist_ok=True)
    stem = os.path.join(OUT, "fig7_trigger_trace")
    fig.savefig(stem + ".pdf")
    fig.savefig(stem + ".png", dpi=300)
    fig.savefig(stem + ".svg")
    fig.savefig(stem + ".eps")
    plt.close(fig)
    print("wrote", stem + ".{pdf,eps,png,svg}")
    print("n=", len(t), "rising HELLO at t=", hello_t.tolist())


if __name__ == "__main__":
    main()
