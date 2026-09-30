#!/usr/bin/env python3
"""Step 66: Scenario III LQARP vs E-LQTP at beta_2=0, scale-consistent beta_1.

O(1) beta_1 (Step 64) swamps c_lin's BER-floor plateau (~4e-7). A typical
positive Kalman Delta e_k is ~0.014 dB (Step 63), so beta_1 ~ 1e-5 makes
beta_1*typical(delta_e) ~ 1.4e-7 — same order as c_lin — and is the scale
that can actually blend rather than replace the link-quality term.
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
RUN_DIR = OUT_DIR / "scenario3_beta1_scaled_sweep"
CSV_PATH = OUT_DIR / "scenario3_beta1_scaled_sweep.csv"

SEEDS = [20260921, 20260922, 20260923, 20260924, 20260925]
# Scale-consistent with c_lin floor ~4e-7 and typical delta_e ~0.014 dB.
BETA1 = [0.0, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]
C_LIN_FLOOR = 4.0e-7
TYPICAL_DELTA_E = 0.014

SWEEP_RE = re.compile(r"^SWEEP\s+(.*)$", re.M)
KV_RE = re.compile(r"(\w+)=(\S+)")

CSV_COLUMNS = [
    "protocol",
    "seed",
    "beta_1",
    "beta_2",
    "N",
    "V_eddy_mps",
    "T_sim_s",
    "PDR",
    "T_e2e_s",
    "E_bit_J_per_bit",
    "O_ctrl_byte_per_s",
    "mean_hops",
    "VOID",
    "LOST_NODE_EXIT",
    "Broadcast_k_rising",
    "first_fire_rate",
    "n_envelope",
    "hop_flight_s",
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

    live = i("live_pairs")
    heard = i("heard_live")
    first = f("first_fire")
    if live > 0 and math.isnan(first):
        first = heard / live
    return {
        "protocol": kv["proto"],
        "seed": i("seed"),
        "beta_1": f("beta_1", "0"),
        "beta_2": f("beta_2", "0"),
        "N": i("N", "40"),
        "V_eddy_mps": f("drift"),
        "T_sim_s": f("T_sim"),
        "PDR": f("PDR"),
        "T_e2e_s": f("T_e2e"),
        "E_bit_J_per_bit": f("E_bit"),
        "O_ctrl_byte_per_s": f("O_ctrl"),
        "mean_hops": f("mean_hops"),
        "VOID": i("VOID"),
        "LOST_NODE_EXIT": i("LOST_NODE_EXIT"),
        "Broadcast_k_rising": i("rising"),
        "first_fire_rate": first,
        "n_envelope": i("n_envelope"),
        "hop_flight_s": f("hop_flight", "nan"),
        "n_gen": i("n_gen"),
        "n_succ": i("n_succ"),
        "n_tx": i("n_tx"),
        "metrics_finite": i("finite"),
    }


def stem_beta(b1: float) -> str:
    return f"{b1:.0e}" if 0 < b1 < 1e-2 else f"{b1:g}"


def run_one(proto: str, seed: int, beta1: float) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{proto}_s{seed}_b1_{stem_beta(beta1)}"
    out_path = RUN_DIR / f"{stem}.txt"
    cmd = [
        str(BIN),
        f"--dataDir={DATA_DIR}",
        "--scenario=iii",
        "--nAuv=40",
        "--simTime=600",
        f"--seed={seed}",
        "--driftSpeed=2",
        f"--protocol={proto}",
        "--boundary=remove",
        "--quiet",
        f"--out={out_path}",
    ]
    if proto == "elqtp":
        # Scientific notation is required so 1e-7 is not rounded by %g-like
        # default formatting on some locales.
        cmd.extend([f"--beta_1={beta1:.10e}", "--beta_2=0"])
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
    if proto == "elqtp" and abs(row["beta_1"] - beta1) > max(1e-12, 1e-6 * abs(beta1)):
        raise RuntimeError(f"{stem} beta_1 mismatch: {row['beta_1']} vs {beta1}")
    if proto == "elqtp" and abs(row["beta_2"]) > 1e-12:
        raise RuntimeError(f"{stem} beta_2 not 0: {row['beta_2']}")
    return row


def mean_std(xs: list[float]) -> tuple[float, float]:
    vals = [float(x) for x in xs if x is not None and not math.isnan(float(x))]
    if not vals:
        return float("nan"), float("nan")
    m = sum(vals) / len(vals)
    if len(vals) == 1:
        return m, 0.0
    var = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
    return m, math.sqrt(var)


def fmt(xs: list[float], prec: int = 4, sci: bool = False) -> str:
    m, s = mean_std(xs)
    if math.isnan(m):
        return "—"
    if sci:
        return f"{m:.{prec}e} ± {s:.{prec}e}"
    return f"{m:.{prec}f} ± {s:.{prec}f}"


def same_beta(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-15)


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["protocol"], x["beta_1"], x["seed"])):
            w.writerow({c: r[c] for c in CSV_COLUMNS})


def print_table(rows: list[dict], betas: list[float]) -> None:
    print("\nStep 66 — Scenario III, beta_2=0, scale-consistent beta_1")
    print("mean ± std over 5 seeds. LQARP is the c_lin / c_del baseline.")
    print(
        f"c_lin floor ~ {C_LIN_FLOOR:.1e}; typical max(0,delta_e) ~ {TYPICAL_DELTA_E} dB.\n"
    )
    hdr = (
        f"{'config':<24} {'PDR':<18} {'T_e2e':<16} {'E_bit':<22} "
        f"{'O_ctrl':<16} {'hops':<16} {'vs LQARP':<10} {'corr/c_lin':<12}"
    )
    print(hdr)
    lq = [r for r in rows if r["protocol"] == "lqarp"]
    lq_hops, _ = mean_std([r["mean_hops"] for r in lq])
    print(
        f"{'LQARP':<24} "
        f"{fmt([r['PDR'] for r in lq], 4):<18} "
        f"{fmt([r['T_e2e_s'] for r in lq], 3):<16} "
        f"{fmt([r['E_bit_J_per_bit'] for r in lq], 3, True):<22} "
        f"{fmt([r['O_ctrl_byte_per_s'] for r in lq], 2):<16} "
        f"{fmt([r['mean_hops'] for r in lq], 3):<16} "
        f"{'—':<10} "
        f"{'—':<12}"
    )
    for b1 in betas:
        xs = [
            r
            for r in rows
            if r["protocol"] == "elqtp" and same_beta(r["beta_1"], b1)
        ]
        if not xs:
            continue
        hops_m, _ = mean_std([r["mean_hops"] for r in xs])
        ratio = hops_m / lq_hops if lq_hops and not math.isnan(lq_hops) else float("nan")
        corr = b1 * TYPICAL_DELTA_E
        blend = corr / C_LIN_FLOOR if C_LIN_FLOOR else float("nan")
        print(
            f"{'E-LQTP b1=' + f'{b1:.0e}' + ' b2=0':<24} "
            f"{fmt([r['PDR'] for r in xs], 4):<18} "
            f"{fmt([r['T_e2e_s'] for r in xs], 3):<16} "
            f"{fmt([r['E_bit_J_per_bit'] for r in xs], 3, True):<22} "
            f"{fmt([r['O_ctrl_byte_per_s'] for r in xs], 2):<16} "
            f"{fmt([r['mean_hops'] for r in xs], 3):<16} "
            f"{ratio:<10.3f} "
            f"{blend:<12.2f}"
        )


def parse_betas(text: str) -> list[float]:
    return [float(x) for x in text.split(",") if x.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument(
        "--betas",
        type=str,
        default=",".join(f"{b:.10e}" for b in BETA1),
        help="comma-separated beta_1 values (default: Step 66 scale set)",
    )
    ap.add_argument("--skip-lqarp", action="store_true")
    ap.add_argument("--csv", type=str, default=str(CSV_PATH))
    args = ap.parse_args()
    betas = parse_betas(args.betas)
    if not BIN.is_file():
        print(f"missing binary {BIN}", file=sys.stderr)
        return 2
    jobs: list[tuple[str, int, float]] = []
    if not args.skip_lqarp:
        for seed in SEEDS:
            jobs.append(("lqarp", seed, 0.0))
    for b1 in betas:
        for seed in SEEDS:
            jobs.append(("elqtp", seed, b1))
    rows: list[dict] = []
    print(f"running {len(jobs)} jobs, jobs={args.jobs}", flush=True)
    print(
        "scale check: "
        + ", ".join(
            f"b1={b:.0e} => b1*0.014={b * TYPICAL_DELTA_E:.2e} "
            f"({b * TYPICAL_DELTA_E / C_LIN_FLOOR:.2f} x c_lin)"
            for b in betas
        ),
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futs = {ex.submit(run_one, p, s, b): (p, s, b) for p, s, b in jobs}
        for fut in as_completed(futs):
            p, s, b = futs[fut]
            try:
                row = fut.result()
                rows.append(row)
                print(
                    f"  ok {p} seed={s} b1={b:.0e} PDR={row['PDR']:.4f} "
                    f"hops={row['mean_hops']:.3f} T_e2e={row['T_e2e_s']:.3f} "
                    f"O_ctrl={row['O_ctrl_byte_per_s']:.1f}",
                    flush=True,
                )
            except Exception as e:
                print(f"  FAIL {p} seed={s} b1={b}: {e}", flush=True)
                return 1
    csv_path = Path(args.csv)
    write_csv(rows, csv_path)
    print(f"wrote {csv_path}")
    print_table(rows, betas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
