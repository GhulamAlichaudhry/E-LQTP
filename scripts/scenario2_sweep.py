#!/usr/bin/env python3
"""Steps 53–55 diagnostic: Scenario II multi-seed / drift sweep at beta=1/1.

Headline tables at the validated beta_1=beta_2=0 point are
scripts/scenario2_headline.py (Steps 69–70). Do not treat this
CSV as a paper result.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BIN = Path(
    os.environ.get(
        "ELQTP_BIN",
        str(
            ROOT
            / "opt/ns-allinone-3.41/ns-3.41/build/contrib/elqtp"
            / "ns3.41-scenario-i-lqarp-optimized"
        ),
    )
)
DATA_DIR = Path(os.environ.get("ELQTP_DATA", str(ROOT / "data/channel_db")))
OUT_DIR = ROOT / "results"
FIG_DIR = OUT_DIR / "figs"
RUN_DIR = OUT_DIR / "scenario2_sweep"
CSV_PATH = OUT_DIR / "scenario2_multiseed_data.csv"

SEEDS = [20260921, 20260922, 20260923, 20260924, 20260925]
PROTOS_53 = ["lqarp", "elqtp", "rlor", "periodic"]
DRIFT_53 = [2.0]
PROTOS_54 = ["lqarp", "elqtp"]
DRIFT_54_NEW = [0.5, 1.0, 3.0, 3.5]
ALL_DRIFT = [0.5, 1.0, 2.0, 3.0, 3.5]

SWEEP_RE = re.compile(r"^SWEEP\s+(.*)$", re.M)
KV_RE = re.compile(r"(\w+)=(\S+)")

PROTO_LABEL = {
    "lqarp": "LQARP",
    "elqtp": "E-LQTP",
    "rlor": "RLOR-inspired",
    "periodic": "Fixed-Periodic",
}
# Color + marker + linestyle: readable in grayscale / B&W print.
PROTO_STYLE = {
    "lqarp": dict(color="#0072B2", marker="o", linestyle="-", hatch=""),
    "elqtp": dict(color="#D55E00", marker="s", linestyle="--", hatch="//"),
    "rlor": dict(color="#009E73", marker="^", linestyle=":", hatch=".."),
    "periodic": dict(color="#000000", marker="D", linestyle="-.", hatch="xx"),
}

CSV_COLUMNS = [
    "protocol",
    "seed",
    "N",
    "drift_mps",
    "azimuth_rad",
    "T_sim_s",
    "PDR",
    "T_e2e_s",
    "E_bit_J_per_bit",
    "O_ctrl_byte_per_s",
    "mean_hops",
    "VOID",
    "LOST_NODE_EXIT",
    "Broadcast_k_rising",
    "Broadcast_k_ones",
    "ctrl_tx",
    "heard_live",
    "live_pairs",
    "first_fire_rate",
    "n_exit_tsim",
    "n_envelope",
    "attrition_tsim",
    "n_gen",
    "n_succ",
    "n_tx",
    "metrics_finite",
]


def parse_sweep(text: str) -> dict:
    m = SWEEP_RE.search(text)
    if not m:
        raise ValueError("no SWEEP line in report")
    kv = {k: v for k, v in KV_RE.findall(m.group(1))}

    def f(name, default="nan"):
        v = kv.get(name, default)
        if v in ("nan", "NaN", "-nan"):
            return float("nan")
        return float(v)

    def i(name, default="0"):
        return int(float(kv.get(name, default)))

    n = i("N", "40")
    n_exit = i("n_exit_tsim")
    live = i("live_pairs")
    heard = i("heard_live")
    first = f("first_fire")
    if live > 0 and (math.isnan(first)):
        first = heard / live
    return {
        "protocol": kv["proto"],
        "seed": i("seed"),
        "N": n,
        "drift_mps": f("drift"),
        "azimuth_rad": f("azimuth"),
        "T_sim_s": f("T_sim"),
        "PDR": f("PDR"),
        "T_e2e_s": f("T_e2e"),
        "E_bit_J_per_bit": f("E_bit"),
        "O_ctrl_byte_per_s": f("O_ctrl"),
        "mean_hops": f("mean_hops"),
        "VOID": i("VOID"),
        "LOST_NODE_EXIT": i("LOST_NODE_EXIT"),
        "Broadcast_k_rising": i("rising"),
        "Broadcast_k_ones": i("ones"),
        "ctrl_tx": i("ctrl_tx"),
        "heard_live": heard,
        "live_pairs": live,
        "first_fire_rate": first,
        "n_exit_tsim": n_exit,
        "n_envelope": i("n_envelope"),
        "attrition_tsim": n_exit / n if n else float("nan"),
        "n_gen": i("n_gen"),
        "n_succ": i("n_succ"),
        "n_tx": i("n_tx"),
        "metrics_finite": i("finite"),
    }


def job_key(proto: str, seed: int, drift: float) -> str:
    return f"{proto}_s{seed}_v{drift:.1f}"


def run_one(proto: str, seed: int, drift: float) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = job_key(proto, seed, drift)
    out_path = RUN_DIR / f"{stem}.txt"
    cmd = [
        str(BIN),
        f"--dataDir={DATA_DIR}",
        "--scenario=ii",
        "--nAuv=40",
        "--simTime=600",
        f"--seed={seed}",
        f"--driftSpeed={drift}",
        f"--protocol={proto}",
        "--boundary=remove",
        "--quiet",
        f"--out={out_path}",
    ]
    if proto in ("elqtp", "periodic"):
        cmd.extend(["--beta_1=1", "--beta_2=1"])
    env = os.environ.copy()
    env.setdefault("NS_LOG", "")
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    text = proc.stdout
    if out_path.exists():
        text = out_path.read_text() + "\n" + text
    (RUN_DIR / f"{stem}.log").write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"{stem} exited {proc.returncode}\n{proc.stdout[-2000:]}")
    row = parse_sweep(text)
    if row["protocol"] != proto or row["seed"] != seed:
        raise RuntimeError(f"{stem} parsed proto/seed mismatch: {row}")
    return row


def jobs_for_steps(step: str) -> list[tuple[str, int, float]]:
    jobs: list[tuple[str, int, float]] = []
    if step in ("53", "all"):
        for proto in PROTOS_53:
            for seed in SEEDS:
                jobs.append((proto, seed, 2.0))
    if step in ("54", "all"):
        for proto in PROTOS_54:
            for seed in SEEDS:
                for drift in DRIFT_54_NEW:
                    jobs.append((proto, seed, drift))
    # de-dup, keep order
    seen = set()
    out = []
    for j in jobs:
        if j not in seen:
            seen.add(j)
            out.append(j)
    return out


def mean_std_minmax(xs: list[float]) -> tuple[float, float, float, float]:
    vals = [float(x) for x in xs if x is not None and not math.isnan(float(x))]
    if not vals:
        return float("nan"), float("nan"), float("nan"), float("nan")
    m = sum(vals) / len(vals)
    if len(vals) == 1:
        return m, 0.0, vals[0], vals[0]
    var = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
    return m, math.sqrt(var), min(vals), max(vals)


def fmt_stat(xs: list[float], prec: int = 4, sci: bool = False) -> str:
    m, s, lo, hi = mean_std_minmax(xs)
    if math.isnan(m):
        return "—"
    if sci:
        return f"{m:.{prec}e} ± {s:.{prec}e} [{lo:.{prec}e}, {hi:.{prec}e}]"
    return f"{m:.{prec}f} ± {s:.{prec}f} [{lo:.{prec}f}, {hi:.{prec}f}]"


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["drift_mps"], x["protocol"], x["seed"])):
            w.writerow({c: r[c] for c in CSV_COLUMNS})


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        rows = []
        for raw in csv.DictReader(f):
            row = dict(raw)
            for c in CSV_COLUMNS:
                if c == "protocol":
                    continue
                row[c] = float(raw[c]) if raw[c] not in ("", "nan") else float("nan")
            row["seed"] = int(float(row["seed"]))
            row["N"] = int(float(row["N"]))
            rows.append(row)
        return rows


def apply_ieee_rc() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
            "mathtext.fontset": "dejavuserif",
            "mathtext.default": "regular",
            "axes.formatter.use_mathtext": False,
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.3,
            "lines.markersize": 6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.05,
        }
    )


def save_figure(fig, stem: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{stem}.pdf")
    fig.savefig(FIG_DIR / f"{stem}.eps")
    fig.savefig(FIG_DIR / f"{stem}.png", dpi=200)
    plt.close(fig)


def figure_a(rows: list[dict]) -> None:
    """Protocol comparison at ||v_drift||=2.0 m/s (5 seeds)."""
    apply_ieee_rc()
    data = [r for r in rows if abs(r["drift_mps"] - 2.0) < 1e-9]
    protos = ["lqarp", "elqtp", "rlor", "periodic"]
    panels = [
        ("PDR", "PDR", "Packet Delivery Ratio", (0.985, 1.002)),
        ("T_e2e_s", "T_e2e_s", "Average End-to-End Delay (s)", None),
        ("E_bit_J_per_bit", "E_bit_J_per_bit", "Energy per Bit (J/bit)", None),
        ("O_ctrl_byte_per_s", "O_ctrl_byte_per_s", "Control Overhead (bytes/s)", None),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.40))
    x = np.arange(len(protos))
    width = 0.62
    xticklabels = ["LQARP", "E-LQTP", "RLOR", "Periodic"]
    for ax, (key, _k, ylabel, ylim) in zip(axes.ravel(), panels):
        means, stds, colors, hatches = [], [], [], []
        for p in protos:
            xs = [r[key] for r in data if r["protocol"] == p]
            m, s, _, _ = mean_std_minmax(xs)
            means.append(m)
            stds.append(s)
            colors.append(PROTO_STYLE[p]["color"])
            hatches.append(PROTO_STYLE[p]["hatch"])
        bars = ax.bar(
            x,
            means,
            width,
            yerr=stds,
            color=colors,
            edgecolor="black",
            linewidth=0.6,
            capsize=3,
            error_kw=dict(elinewidth=0.9, capthick=0.9),
        )
        for bar, h in zip(bars, hatches):
            bar.set_hatch(h)
        ax.set_xticks(x)
        ax.set_xticklabels(xticklabels)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", linestyle=":", linewidth=0.5, color="0.6")
        ax.set_axisbelow(True)
        if ylim:
            ax.set_ylim(*ylim)
        if key == "O_ctrl_byte_per_s":
            ax.set_ylim(bottom=0)
    fig.tight_layout()
    save_figure(fig, "scenario2_figA_protocol")


def figure_b(rows: list[dict]) -> None:
    """LQARP vs E-LQTP vs drift magnitude."""
    apply_ieee_rc()
    protos = ["lqarp", "elqtp"]
    panels = [
        ("PDR", "Packet Delivery Ratio", (0.985, 1.002)),
        ("T_e2e_s", "Average End-to-End Delay (s)", None),
        ("E_bit_J_per_bit", "Energy per Bit (J/bit)", None),
        ("O_ctrl_byte_per_s", "Control Overhead (bytes/s)", None),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(7.16, 5.40))
    for ax, (key, ylabel, ylim) in zip(axes.ravel(), panels):
        for p in protos:
            xs, ys, es = [], [], []
            for d in ALL_DRIFT:
                vals = [
                    r[key]
                    for r in rows
                    if r["protocol"] == p and abs(r["drift_mps"] - d) < 1e-9
                ]
                m, s, _, _ = mean_std_minmax(vals)
                xs.append(d)
                ys.append(m)
                es.append(s)
            st = PROTO_STYLE[p]
            ax.errorbar(
                xs,
                ys,
                yerr=es,
                color=st["color"],
                marker=st["marker"],
                linestyle=st["linestyle"],
                label=PROTO_LABEL[p],
                capsize=2.5,
                elinewidth=0.9,
            )
        ax.set_xlabel("Drift Speed ||v_drift|| (m/s)")  # ASCII: IEEE caption expands the symbol
        ax.set_ylabel(ylabel)
        ax.set_xticks(ALL_DRIFT)
        ax.grid(True, linestyle=":", linewidth=0.5, color="0.6")
        ax.set_axisbelow(True)
        if ylim:
            ax.set_ylim(*ylim)
        if key == "O_ctrl_byte_per_s":
            ax.set_ylim(bottom=0)
            ax.legend(frameon=False, loc="upper left")
        elif key == "PDR":
            ax.legend(frameon=False, loc="lower left")
    fig.tight_layout()
    save_figure(fig, "scenario2_figB_drift")


def select_rows(
    rows: list[dict], proto: str | None = None, drift: float | None = None
) -> list[dict]:
    out = rows
    if proto is not None:
        out = [r for r in out if r["protocol"] == proto]
    if drift is not None:
        out = [r for r in out if abs(r["drift_mps"] - drift) < 1e-9]
    return out


def table_block(rows: list[dict], drift: float | None, protos: list[str]) -> str:
    lines = []
    subset = rows if drift is None else select_rows(rows, drift=drift)
    for p in protos:
        rs = [r for r in subset if r["protocol"] == p]
        if not rs:
            continue
        label = PROTO_LABEL[p]
        extra = ""
        if drift is not None:
            extra = f" | v={drift:.1f}"
        lines.append(
            f"| {label}{extra} | "
            f"{fmt_stat([r['PDR'] for r in rs], 4)} | "
            f"{fmt_stat([r['T_e2e_s'] for r in rs], 3)} | "
            f"{fmt_stat([r['E_bit_J_per_bit'] for r in rs], 3, sci=True)} | "
            f"{fmt_stat([r['O_ctrl_byte_per_s'] for r in rs], 2)} | "
            f"{fmt_stat([r['mean_hops'] for r in rs], 3)} | "
            f"{fmt_stat([r['VOID'] for r in rs], 2)} | "
            f"{fmt_stat([r['LOST_NODE_EXIT'] for r in rs], 2)} | "
            + (
                fmt_stat([r["Broadcast_k_rising"] for r in rs], 1)
                if p in ("elqtp", "periodic")
                else "—"
            )
            + " |"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["53", "54", "all", "figures"], default="all")
    ap.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 2))
    ap.add_argument("--skip-run", action="store_true")
    args = ap.parse_args()

    existing: dict[tuple, dict] = {}
    if CSV_PATH.exists():
        for r in load_csv(CSV_PATH):
            existing[(r["protocol"], r["seed"], float(r["drift_mps"]))] = r

    rows = list(existing.values())
    if args.step != "figures" and not args.skip_run:
        if not BIN.exists():
            print(f"missing binary {BIN}", file=sys.stderr)
            return 2
        todo = [
            j
            for j in jobs_for_steps(args.step)
            if (j[0], j[1], float(j[2])) not in existing
        ]
        print(f"runs to launch: {len(todo)} (reuse {len(existing)}) jobs={args.jobs}")
        if todo:
            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                futs = {pool.submit(run_one, *j): j for j in todo}
                done = 0
                for fut in as_completed(futs):
                    j = futs[fut]
                    try:
                        row = fut.result()
                    except Exception as exc:
                        print(f"FAIL {j}: {exc}", file=sys.stderr)
                        return 1
                    existing[(row["protocol"], row["seed"], float(row["drift_mps"]))] = row
                    done += 1
                    print(
                        f"  [{done}/{len(todo)}] {job_key(*j)} "
                        f"PDR={row['PDR']:.4f} O_ctrl={row['O_ctrl_byte_per_s']:.2f} "
                        f"exit={row['n_exit_tsim']}/{row['N']}",
                        flush=True,
                    )
        rows = list(existing.values())
        write_csv(rows, CSV_PATH)
        print(f"wrote {CSV_PATH} n={len(rows)}")

    if not rows:
        print("no rows to plot", file=sys.stderr)
        return 1

    figure_a(rows)
    figure_b(rows)
    print(f"figures in {FIG_DIR}")

    print("\n=== Step 53 v=2.0 ===")
    print(
        "| protocol | PDR | T_e2e (s) | E_bit (J/bit) | O_ctrl (byte/s) | hops | VOID | LOST | rising |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    print(table_block(rows, 2.0, PROTOS_53))

    print("\n=== Step 54 vs drift ===")
    print(
        "| protocol | PDR | T_e2e (s) | E_bit (J/bit) | O_ctrl (byte/s) | hops | VOID | LOST | rising |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for d in ALL_DRIFT:
        print(table_block(rows, d, PROTOS_54))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
