#!/usr/bin/env python3
"""LQARP-style Phase 2 campaign plots and 95% CI tables."""
from __future__ import annotations

import csv
import math
import os
import sys
from collections import defaultdict

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover
    print("matplotlib unavailable:", exc)
    sys.exit(0)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 9,
        "legend.fontsize": 7.5,
        "figure.dpi": 140,
    }
)


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def t_crit_95(df: int) -> float:
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        14: 2.145, 19: 2.093, 24: 2.064, 29: 2.045, 39: 2.023,
    }
    if df in table:
        return table[df]
    if df > 99:
        return 1.96
    keys = sorted(table)
    for k in keys:
        if k >= df:
            return table[k]
    return 1.96


def mean_ci(xs):
    xs = [float(x) for x in xs if x not in (None, "")]
    n = len(xs)
    m = mean(xs)
    if n < 2:
        return m, 0.0, n
    h = t_crit_95(n - 1) * stdev(xs) / math.sqrt(n)
    return m, h, n


def fmt(m, h, n):
    return f"{m:.3g} ± {h:.3g} (n={n})"


def data_int(row, default=16.0):
    v = row.get("data_interval")
    if v in (None, ""):
        return default
    try:
        return float(v)
    except ValueError:
        return default


def load_rows(out_dir: str):
    path = os.path.join(out_dir, "fwd_metrics.csv")
    rows = []
    if os.path.isfile(path):
        rows = [r for r in load_csv(path) if r.get("seed") not in (None, "seed")]
    return rows


LABELS = {
    ("event", "snr"): "Event+SNR",
    ("event", "hold"): "ETHA (proposed)",
    ("event", "depth"): "Event+Depth (DBR)",
    ("event", "oracle"): "Oracle",
    ("periodic", "snr"): "Periodic+SNR",
    ("periodic", "hold"): "Periodic+ETHA",
}
COLORS = {
    ("event", "hold"): "#1e8449",
    ("event", "snr"): "#1f4e79",
    ("event", "depth"): "#b9770e",
    ("event", "oracle"): "#6c3483",
    ("periodic", "snr"): "#922b21",
    ("periodic", "hold"): "#c0392b",
}
ORDER = [
    ("event", "hold"),
    ("event", "snr"),
    ("event", "depth"),
    ("periodic", "snr"),
    ("periodic", "hold"),
    ("event", "oracle"),
]


def plot_forwarding(out_dir: str) -> None:
    rows = load_rows(out_dir)
    if not rows:
        print("no forwarding metrics")
        return

    main = [
        r
        for r in rows
        if abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and abs(data_int(r) - 16.0) < 0.5
    ]

    def subset(mode, pol, pool=None):
        pool = main if pool is None else pool
        return [r for r in pool if r.get("mode") == mode and r.get("fwd_policy") == pol]

    metrics = [
        ("pdr", "Packet delivery ratio"),
        ("mean_e2e_s", "Mean e2e delay (s)"),
        ("tx_energy_J", "Transmit energy (J)"),
        ("control_bps", "Control rate (bit/s)"),
        ("drop_noroute", "No-route drops / run"),
        ("stale_fwd", "Stale / in-flight-dead hops"),
        ("dying_fwd", "Dying-link hops"),
        ("mean_hops", "Mean hop count"),
    ]

    present = [k for k in ORDER if subset(*k)]
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.4))
    axes = axes.ravel()
    summary = {}
    for i, (key, title) in enumerate(metrics):
        ax = axes[i]
        xs, ys, ye, cc, labs = [], [], [], [], []
        for j, k in enumerate(present):
            vals = [r.get(key) for r in subset(*k) if r.get(key) not in (None, "")]
            if not vals:
                continue
            m, h, n = mean_ci(vals)
            summary.setdefault(k, {})[key] = (m, h, n)
            xs.append(j)
            ys.append(m)
            ye.append(h)
            cc.append(COLORS[k])
            labs.append(LABELS[k].replace(" ", "\n"))
        ax.bar(xs, ys, yerr=ye, color=cc, capsize=3, width=0.7, error_kw={"elinewidth": 1.1})
        ax.set_xticks(xs)
        ax.set_xticklabels(labs, fontsize=6)
        ax.set_title(title, fontsize=10)
        ax.grid(True, axis="y", alpha=0.3)
        if key == "pdr":
            ax.set_ylim(0, 1.05)

    lines = [
        "# Paper forwarding campaign (95% CI)",
        "",
        "Unslotted ALOHA, 12 nodes, $T_{max}=10$ s, all AUVs send 400-bit packets every 16 s after $t=50$ s, 360 s runs.",
        "",
        "| Scheme | PDR | e2e (s) | Energy (J) | Control bit/s | No-route | Stale | Hops |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for k in present:
        s = summary.get(k, {})

        def g(key):
            if key not in s:
                return "—"
            return fmt(*s[key])

        lines.append(
            f"| {LABELS[k]} | {g('pdr')} | {g('mean_e2e_s')} | {g('tx_energy_J')} | "
            f"{g('control_bps')} | {g('drop_noroute')} | {g('stale_fwd')} | {g('mean_hops')} |"
        )

    # ---- scale ----
    scale_rows = [
        r
        for r in rows
        if r.get("fwd_policy") in ("hold", "snr", "depth")
        and abs(data_int(r) - 16.0) < 0.5
    ]
    by_n = defaultdict(lambda: defaultdict(list))
    for r in scale_rows:
        n = int(float(r.get("n_nodes") or 0))
        key = (r.get("mode"), r.get("fwd_policy"))
        by_n[n][key].append(r)
    if by_n:
        lines += [
            "",
            "## Scale (PDR vs node count)",
            "",
            "| Nodes | ETHA | Event+Depth | Periodic+SNR |",
            "| --- | --- | --- | --- |",
        ]
        for n in sorted(by_n):
            cells = []
            for k in (("event", "hold"), ("event", "depth"), ("periodic", "snr")):
                sub = by_n[n].get(k, [])
                if not sub:
                    cells.append("—")
                else:
                    cells.append(fmt(*mean_ci([r["pdr"] for r in sub])))
            lines.append(f"| {n} | " + " | ".join(cells) + " |")

        fig2, axes = plt.subplots(2, 2, figsize=(7.2, 5.4))
        series = (
            (("event", "hold"), "ETHA", "#1e8449", "o"),
            (("event", "depth"), "Event+Depth", "#b9770e", "s"),
            (("periodic", "snr"), "Periodic+SNR", "#922b21", "^"),
        )
        panels = [
            ("pdr", "Packet delivery ratio", (0.35, 1.02)),
            ("tx_energy_J", "Transmit energy (J)", None),
            ("mean_e2e_s", "Mean e2e delay (s)", None),
            ("control_bps", "Control rate (bit/s)", None),
        ]
        for ax, (key, ylab, ylim) in zip(axes.ravel(), panels):
            for k, lab, col, mk in series:
                ns, ms, hs = [], [], []
                for n in sorted(by_n):
                    sub = by_n[n].get(k, [])
                    if not sub:
                        continue
                    m, h, _ = mean_ci([r[key] for r in sub])
                    ns.append(n)
                    ms.append(m)
                    hs.append(h)
                if ns:
                    ax.errorbar(ns, ms, yerr=hs, marker=mk, color=col, capsize=3, label=lab)
            ax.set_xlabel("Nodes")
            ax.set_ylabel(ylab)
            if ylim:
                ax.set_ylim(*ylim)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7)
        fig2.tight_layout()
        fig2.savefig(os.path.join(out_dir, "phase2_scale.png"), dpi=160)
        plt.close(fig2)

    # ---- load ----
    load_rows_ = [
        r
        for r in rows
        if abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and (r.get("mode"), r.get("fwd_policy"))
        in (("event", "hold"), ("event", "depth"), ("periodic", "snr"))
    ]
    by_di = defaultdict(lambda: defaultdict(list))
    for r in load_rows_:
        by_di[data_int(r)][(r.get("mode"), r.get("fwd_policy"))].append(r)
    if len(by_di) >= 2:
        lines += [
            "",
            "## Load (PDR vs packet interval, 12 nodes)",
            "",
            "| Interval (s) | ETHA | Event+Depth | Periodic+SNR |",
            "| --- | --- | --- | --- |",
        ]
        for di in sorted(by_di):
            cells = []
            for k in (("event", "hold"), ("event", "depth"), ("periodic", "snr")):
                sub = by_di[di].get(k, [])
                if not sub:
                    cells.append("—")
                else:
                    cells.append(fmt(*mean_ci([r["pdr"] for r in sub])))
            lines.append(f"| {di:g} | " + " | ".join(cells) + " |")

        fig3, axes = plt.subplots(1, 2, figsize=(7.2, 2.7))
        series = (
            (("event", "hold"), "ETHA", "#1e8449", "o"),
            (("event", "depth"), "Event+Depth", "#b9770e", "s"),
            (("periodic", "snr"), "Periodic+SNR", "#922b21", "^"),
        )
        for ax, key, ylab in (
            (axes[0], "pdr", "Packet delivery ratio"),
            (axes[1], "tx_energy_J", "Transmit energy (J)"),
        ):
            for k, lab, col, mk in series:
                xs, ms, hs = [], [], []
                for di in sorted(by_di):
                    sub = by_di[di].get(k, [])
                    if not sub:
                        continue
                    m, h, _ = mean_ci([r[key] for r in sub])
                    xs.append(di)
                    ms.append(m)
                    hs.append(h)
                if xs:
                    ax.errorbar(xs, ms, yerr=hs, marker=mk, color=col, capsize=3, label=lab)
            ax.set_xlabel("Packet interval (s)")
            ax.set_ylabel(ylab)
            if key == "pdr":
                ax.set_ylim(0.35, 1.02)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7)
        fig3.tight_layout()
        fig3.savefig(os.path.join(out_dir, "phase2_load.png"), dpi=160)
        plt.close(fig3)

    fig.suptitle("ETHA forwarding on event-triggered maps (95% CI)")
    fig.tight_layout()
    out = os.path.join(out_dir, "phase2_fwd.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)

    md = os.path.join(out_dir, "fwd_ci_table.md")
    with open(md, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", md)
    print("\n".join(lines))


def main(out_dir: str) -> None:
    plot_forwarding(out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/workspace/results/phase2")
