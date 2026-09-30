#!/usr/bin/env python3
"""Plot Phase 1 single-run traces and multi-seed 95% CI summaries."""
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
    """Two-sided 95% Student-t critical value (small table + fallback)."""
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        14: 2.145, 19: 2.093, 24: 2.064, 29: 2.045, 39: 2.023,
        49: 2.010, 59: 2.000, 99: 1.984,
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
    xs = [float(x) for x in xs]
    n = len(xs)
    m = mean(xs)
    if n < 2:
        return m, 0.0, n
    h = t_crit_95(n - 1) * stdev(xs) / math.sqrt(n)
    return m, h, n


def prediction_mae(pred_path: str, delay_path: str, horizon: float = 60.0):
    downs = []
    if os.path.exists(delay_path):
        for r in load_csv(delay_path):
            if r.get("event") == "link_down":
                downs.append((int(r["src"]), int(r["dst"]), float(r["t_true"])))
    if not downs or not os.path.exists(pred_path):
        return None, []
    by_pair = defaultdict(list)
    for r in load_csv(pred_path):
        key = (int(r["src"]), int(r["dst"]))
        by_pair[key].append(r)
    pairs = []
    errs = []
    for src, dst, t_down in downs:
        for r in by_pair.get((src, dst), []):
            t = float(r["time"])
            if t_down - horizon <= t < t_down:
                hold = float(r["hold_disc_s"])
                actual = t_down - t
                if 0.0 <= hold < 1e8:
                    errs.append(abs(hold - actual))
                    pairs.append((actual, hold))
    mae = sum(errs) / len(errs) if errs else None
    return mae, pairs


def plot_single_run(out_dir: str) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    colors = {"periodic": "#1f77b4", "event": "#d62728"}
    maes = {}
    found = False

    for mode in ("periodic", "event"):
        aw = os.path.join(out_dir, f"awareness_{mode}.csv")
        if not os.path.exists(aw):
            continue
        found = True
        rows = load_csv(aw)
        t = [float(r["time"]) for r in rows]
        rec = [float(r["recall"]) for r in rows]
        prec = [float(r["precision"]) for r in rows]
        bps = [float(r["control_bps"]) for r in rows]
        true_e = [float(r["true_edges"]) for r in rows]
        c = colors[mode]
        axes[0, 0].plot(t, rec, label=f"{mode} recall", color=c)
        axes[0, 0].plot(t, prec, linestyle="--", label=f"{mode} precision", color=c, alpha=0.7)
        axes[0, 1].plot(t, bps, label=mode, color=c)
        axes[1, 0].plot(t, true_e, label=f"{mode} true edges", color=c)
        if "n2hop" in rows[0]:
            n2 = [float(r["n2hop"]) for r in rows]
            axes[1, 0].plot(t, n2, linestyle=":", label=f"{mode} 2-hop pairs", color=c, alpha=0.7)

        mae, pairs = prediction_mae(
            os.path.join(out_dir, f"predictions_{mode}.csv"),
            os.path.join(out_dir, f"detection_delay_{mode}.csv"),
        )
        maes[mode] = mae
        if pairs:
            actual, pred = zip(*pairs)
            axes[1, 1].scatter(actual, pred, s=12, alpha=0.45, color=c, label=f"{mode} disc MAE={mae:.1f}s")

    if not found:
        return

    axes[0, 0].set_title("Neighbor-table awareness")
    axes[0, 0].set_xlabel("time (s)")
    axes[0, 0].set_ylabel("precision / recall")
    axes[0, 0].set_ylim(0, 1.05)
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].set_title("Control overhead (ALOHA HELLOs)")
    axes[0, 1].axhline(2000, color="gray", linestyle=":", label="2 kbps cap")
    axes[0, 1].set_xlabel("time (s)")
    axes[0, 1].set_ylabel("control bits/s")
    axes[0, 1].legend(fontsize=8)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].set_title("Ground-truth acoustic graph")
    axes[1, 0].set_xlabel("time (s)")
    axes[1, 0].set_ylabel("directed pairs")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].set_title("Hold-time prediction vs actual")
    axes[1, 1].set_xlabel("actual remaining (s)")
    axes[1, 1].set_ylabel("predicted remaining (s)")
    xmax = 80
    axes[1, 1].plot([0, xmax], [0, xmax], color="gray", linestyle=":", linewidth=1)
    axes[1, 1].legend(fontsize=8)
    axes[1, 1].grid(True, alpha=0.3)
    axes[1, 1].set_xlim(0, xmax)
    axes[1, 1].set_ylim(0, xmax)

    fig.suptitle("USV–AUV discovery on unslotted ALOHA (single seed)")
    fig.tight_layout()
    out = os.path.join(out_dir, "phase1_awareness.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)
    for mode, mae in maes.items():
        print(f"{mode} hold-time MAE (60s before down): {mae}")


def load_batch(path):
    rows = []
    if os.path.isfile(path):
        rows.extend(load_csv(path))
        return rows
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for fn in files:
                if fn == "metrics.csv":
                    rows.extend(load_csv(os.path.join(root, fn)))
    return rows


def plot_batch(out_dir: str) -> None:
    batch_csv = os.path.join(out_dir, "batch_metrics.csv")
    rows = load_batch(batch_csv)
    if not rows:
        rows = load_batch(os.path.join(out_dir, "batch"))
    if not rows:
        return

    def is_main(r):
        mac = r.get("mac", "unslotted") or "unslotted"
        n = float(r.get("n_nodes") or 12)
        tmax = float(r.get("tMax") or 25)
        margin = float(r.get("multipath_margin") or 30)
        fwd = (r.get("fwd_policy") or "none").strip()
        return (
            mac == "unslotted"
            and abs(n - 12) < 0.5
            and abs(tmax - 25) < 0.5
            and abs(margin - 30) < 0.5
            and fwd in ("none", "")
        )

    rows = [r for r in rows if is_main(r)]
    by_mode = defaultdict(list)
    for r in rows:
        by_mode[r["mode"]].append(r)

    metrics = [
        ("recall", "Recall"),
        ("precision", "Precision"),
        ("f1", "F1"),
        ("control_bps", "Control bit/s"),
        ("up_delay", "Link-up delay (s)"),
        ("down_delay", "Link-down delay (s)"),
        ("hold_mae", "Hold-time MAE (s)"),
        ("phy_collisions", "PHY collisions"),
        ("frac_multihop", "Fraction 2+ hop pairs"),
        ("true_edges", "True directed edges"),
        ("hello_rx", "HELLOs delivered"),
        ("beacons", "Beacons sent"),
    ]

    modes = [m for m in ("periodic", "event") if m in by_mode]
    colors = {"periodic": "#1f77b4", "event": "#d62728"}

    fig, axes = plt.subplots(3, 4, figsize=(14, 10))
    axes = axes.ravel()
    table_lines = ["| Metric | Periodic mean [95% CI] | Event mean [95% CI] |",
                   "| --- | --- | --- |"]

    summary = {m: {} for m in modes}
    for i, (key, label) in enumerate(metrics):
        ax = axes[i]
        xs = []
        ys = []
        yerr = []
        bar_colors = []
        for j, mode in enumerate(modes):
            vals = [float(r[key]) for r in by_mode[mode] if r.get(key) not in (None, "")]
            m, h, n = mean_ci(vals)
            summary[mode][key] = (m, h, n)
            xs.append(j)
            ys.append(m)
            yerr.append(h)
            bar_colors.append(colors[mode])
        ax.bar(xs, ys, yerr=yerr, color=bar_colors, capsize=4, width=0.65, error_kw={"elinewidth": 1.4})
        ax.set_xticks(xs)
        ax.set_xticklabels(modes, fontsize=8)
        ax.set_title(label, fontsize=10)
        ax.grid(True, axis="y", alpha=0.3)
        if key == "control_bps":
            ax.axhline(2000, color="gray", linestyle=":", linewidth=1)

    def fmt(x):
        if x is None:
            return "—"
        m, h, n = x
        return f"{m:.3g} ± {h:.3g} (n={n})"

    for key, label in metrics:
        p = summary.get("periodic", {}).get(key)
        e = summary.get("event", {}).get(key)
        table_lines.append(f"| {label} | {fmt(p)} | {fmt(e)} |")

    fig.suptitle("Phase 1 paper experiment: 12-node ALOHA discovery, 95% CI across seeds")
    fig.tight_layout()
    out = os.path.join(out_dir, "phase1_ci.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)

    md = os.path.join(out_dir, "batch_ci_table.md")
    with open(md, "w") as f:
        f.write("# Multi-seed 95% CI\n\n")
        f.write("Unslotted ALOHA HELLOs, inner/outer 12-node layout, randomized seeds.\n\n")
        f.write("\n".join(table_lines) + "\n")
    print("wrote", md)
    print("\n".join(table_lines))


def _errbar(ax, xs, means, cis, **kwargs):
    ax.errorbar(xs, means, yerr=cis, capsize=4, marker="o", linewidth=1.6, **kwargs)


def plot_ablations(out_dir: str) -> None:
    path = os.path.join(out_dir, "ablation_metrics.csv")
    if not os.path.exists(path):
        return
    rows = [r for r in load_csv(path) if r.get("seed") not in (None, "seed")]
    if not rows:
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    colors = {"periodic": "#1f77b4", "event": "#d62728"}
    lines = ["# Phase 1 appendix ablations (95% CI)", ""]

    # --- MAC ---
    ax = axes[0, 0]
    lines.append("## Unslotted vs slotted ALOHA")
    lines.append("")
    lines.append("| MAC | Mode | Recall | Up delay (s) | Collisions | Control bit/s |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    mac_rows = [
        r for r in rows
        if abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and abs(float(r.get("tMax") or 25) - 25) < 0.5
        and abs(float(r.get("multipath_margin") or 30) - 30) < 0.5
    ]
    xlabels = []
    xpos = []
    k = 0
    for mac in ("unslotted", "slotted"):
        for mode in ("periodic", "event"):
            sub = [r for r in mac_rows if r.get("mac", "unslotted") == mac and r["mode"] == mode]
            if not sub:
                continue
            rec, rec_h, n = mean_ci([float(r["recall"]) for r in sub])
            up, up_h, _ = mean_ci([float(r["up_delay"]) for r in sub])
            coll, coll_h, _ = mean_ci([float(r["phy_collisions"]) for r in sub])
            bps, bps_h, _ = mean_ci([float(r["control_bps"]) for r in sub])
            ax.bar(k, rec, yerr=rec_h, capsize=3, color=colors[mode], width=0.7)
            xlabels.append(f"{mac[:4]}\n{mode[:3]}")
            xpos.append(k)
            lines.append(
                f"| {mac} | {mode} | {rec:.3f} ± {rec_h:.3f} | {up:.2f} ± {up_h:.2f} | "
                f"{coll:.1f} ± {coll_h:.1f} | {bps:.0f} ± {bps_h:.1f} |"
            )
            k += 1
    ax.set_xticks(xpos)
    ax.set_xticklabels(xlabels, fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Recall")
    ax.set_title("MAC: unslotted vs slotted ALOHA")
    ax.grid(True, axis="y", alpha=0.3)
    lines.append("")

    # --- Tmax ---
    ax = axes[0, 1]
    tmax_rows = [
        r for r in rows
        if r["mode"] == "event"
        and r.get("mac", "unslotted") == "unslotted"
        and abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and abs(float(r.get("multipath_margin") or 30) - 30) < 0.5
    ]
    by_t = defaultdict(list)
    for r in tmax_rows:
        by_t[float(r.get("tMax") or 25)].append(r)
    ts = sorted(by_t)
    recs, rec_hs, ups, up_hs, bpss, bps_hs = [], [], [], [], [], []
    lines.append("## Event-triggered $T_{max}$ sweep (unslotted, 12 nodes)")
    lines.append("")
    lines.append("| Tmax (s) | Recall | Up delay (s) | Down delay (s) | Control bit/s | Hold MAE (s) |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for t in ts:
        sub = by_t[t]
        rec, rec_h, _ = mean_ci([float(r["recall"]) for r in sub])
        up, up_h, _ = mean_ci([float(r["up_delay"]) for r in sub])
        down, down_h, _ = mean_ci([float(r["down_delay"]) for r in sub])
        bps, bps_h, _ = mean_ci([float(r["control_bps"]) for r in sub])
        mae, mae_h, _ = mean_ci([float(r["hold_mae"]) for r in sub])
        recs.append(rec); rec_hs.append(rec_h)
        ups.append(up); up_hs.append(up_h)
        bpss.append(bps); bps_hs.append(bps_h)
        lines.append(
            f"| {t:.0f} | {rec:.3f} ± {rec_h:.3f} | {up:.2f} ± {up_h:.2f} | "
            f"{down:.2f} ± {down_h:.2f} | {bps:.0f} ± {bps_h:.1f} | {mae:.2f} ± {mae_h:.2f} |"
        )
    _errbar(ax, ts, recs, rec_hs, color="#d62728", label="recall")
    ax.set_xlabel(r"$T_{\max}$ (s)")
    ax.set_ylabel("Recall")
    ax.set_ylim(0.6, 1.05)
    ax.set_title(r"Event $T_{\max}$ vs recall")
    ax.grid(True, alpha=0.3)
    lines.append("")

    # --- multipath margin ---
    ax = axes[1, 0]
    lines.append("## Multipath-margin sensitivity (analytical stand-in, not Bellhop)")
    lines.append("")
    lines.append("| Margin (dB) | Mode | R* (m) | Recall | True edges | 2+ hop frac |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    mag_rows = [
        r for r in rows
        if r.get("mac", "unslotted") == "unslotted"
        and abs(float(r.get("n_nodes") or 12) - 12) < 0.5
        and abs(float(r.get("tMax") or 25) - 25) < 0.5
    ]
    for mode in ("periodic", "event"):
        by_m = defaultdict(list)
        for r in mag_rows:
            if r["mode"] == mode:
                by_m[float(r.get("multipath_margin") or 30)].append(r)
        ms = sorted(by_m)
        recs, rec_hs = [], []
        for mgn in ms:
            sub = by_m[mgn]
            rec, rec_h, _ = mean_ci([float(r["recall"]) for r in sub])
            edges, edges_h, _ = mean_ci([float(r["true_edges"]) for r in sub])
            frac, frac_h, _ = mean_ci([float(r["frac_multihop"]) for r in sub])
            rstar = mean([float(r.get("r_star_m") or 0) for r in sub])
            recs.append(rec); rec_hs.append(rec_h)
            lines.append(
                f"| {mgn:.0f} | {mode} | {rstar:.0f} | {rec:.3f} ± {rec_h:.3f} | "
                f"{edges:.1f} ± {edges_h:.1f} | {frac:.3f} ± {frac_h:.3f} |"
            )
        if ms:
            _errbar(ax, ms, recs, rec_hs, color=colors[mode], label=mode)
    ax.set_xlabel("Multipath margin (dB)")
    ax.set_ylabel("Recall")
    ax.set_ylim(0.6, 1.05)
    ax.set_title("Margin stand-in (not Bellhop)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    lines.append("")

    # --- scale ---
    ax = axes[1, 1]
    lines.append("## Node-count scale")
    lines.append("")
    lines.append("| Nodes | Mode | Recall | Collisions | 2+ hop frac | Diameter |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    sc_rows = [
        r for r in rows
        if r.get("mac", "unslotted") == "unslotted"
        and abs(float(r.get("tMax") or 25) - 25) < 0.5
        and abs(float(r.get("multipath_margin") or 30) - 30) < 0.5
    ]
    for mode in ("periodic", "event"):
        by_n = defaultdict(list)
        for r in sc_rows:
            if r["mode"] == mode:
                by_n[int(float(r["n_nodes"]))].append(r)
        ns = sorted(by_n)
        recs, rec_hs = [], []
        for n in ns:
            sub = by_n[n]
            rec, rec_h, _ = mean_ci([float(r["recall"]) for r in sub])
            coll, coll_h, _ = mean_ci([float(r["phy_collisions"]) for r in sub])
            frac, frac_h, _ = mean_ci([float(r["frac_multihop"]) for r in sub])
            diam, diam_h, _ = mean_ci([float(r["diameter"]) for r in sub])
            recs.append(rec); rec_hs.append(rec_h)
            lines.append(
                f"| {n} | {mode} | {rec:.3f} ± {rec_h:.3f} | {coll:.1f} ± {coll_h:.1f} | "
                f"{frac:.3f} ± {frac_h:.3f} | {diam:.2f} ± {diam_h:.2f} |"
            )
        if ns:
            _errbar(ax, ns, recs, rec_hs, color=colors[mode], label=mode)
    ax.set_xlabel("Nodes")
    ax.set_ylabel("Recall")
    ax.set_ylim(0.6, 1.05)
    ax.set_title("Scale vs recall")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    fig.suptitle("Phase 1 appendix: MAC, $T_{max}$, multipath margin, scale")
    fig.tight_layout()
    out = os.path.join(out_dir, "phase1_ablations.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)

    md = os.path.join(out_dir, "ablation_ci_table.md")
    with open(md, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", md)
    print("\n".join(lines))


def main(out_dir: str) -> None:
    plot_single_run(out_dir)
    plot_batch(out_dir)
    plot_ablations(out_dir)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/workspace/results/phase1")
