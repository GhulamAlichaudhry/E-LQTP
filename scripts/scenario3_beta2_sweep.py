#!/usr/bin/env python3
"""Step 62: Scenario III LQARP vs E-LQTP at beta_1=0, swept beta_2."""
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
RUN_DIR = OUT_DIR / "scenario3_beta2_sweep"
CSV_PATH = OUT_DIR / "scenario3_beta2_sweep.csv"

SEEDS = [20260921, 20260922, 20260923, 20260924, 20260925]
BETA2 = [0.0, 0.25, 0.5, 1.0, 2.0]

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


def run_one(proto: str, seed: int, beta2: float) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{proto}_s{seed}_b2_{beta2:g}"
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
        cmd.extend(["--beta_1=0", f"--beta_2={beta2}"])
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
    if proto == "elqtp" and abs(row["beta_2"] - beta2) > 1e-9:
        raise RuntimeError(f"{stem} beta_2 mismatch: {row['beta_2']} vs {beta2}")
    if proto == "elqtp" and abs(row["beta_1"]) > 1e-9:
        raise RuntimeError(f"{stem} beta_1 not 0: {row['beta_1']}")
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


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["protocol"], x["beta_2"], x["seed"])):
            w.writerow({c: r[c] for c in CSV_COLUMNS})


def print_table(rows: list[dict]) -> None:
    print("\nStep 62 — Scenario III, beta_1=0, swept beta_2")
    print("mean ± std over 5 seeds. LQARP is the c_del baseline.\n")
    hdr = (
        f"{'config':<22} {'PDR':<18} {'T_e2e':<16} {'E_bit':<22} "
        f"{'O_ctrl':<16} {'hops':<16} {'hop_flight':<14} {'first-fire':<12}"
    )
    print(hdr)
    lq = [r for r in rows if r["protocol"] == "lqarp"]
    print(
        f"{'LQARP':<22} "
        f"{fmt([r['PDR'] for r in lq], 4):<18} "
        f"{fmt([r['T_e2e_s'] for r in lq], 3):<16} "
        f"{fmt([r['E_bit_J_per_bit'] for r in lq], 3, True):<22} "
        f"{fmt([r['O_ctrl_byte_per_s'] for r in lq], 2):<16} "
        f"{fmt([r['mean_hops'] for r in lq], 3):<16} "
        f"{fmt([r['hop_flight_s'] for r in lq], 3):<14} "
        f"{'—':<12}"
    )
    for b2 in BETA2:
        xs = [
            r
            for r in rows
            if r["protocol"] == "elqtp" and abs(r["beta_2"] - b2) < 1e-9
        ]
        if not xs:
            continue
        print(
            f"{'E-LQTP b1=0 b2=' + f'{b2:g}':<22} "
            f"{fmt([r['PDR'] for r in xs], 4):<18} "
            f"{fmt([r['T_e2e_s'] for r in xs], 3):<16} "
            f"{fmt([r['E_bit_J_per_bit'] for r in xs], 3, True):<22} "
            f"{fmt([r['O_ctrl_byte_per_s'] for r in xs], 2):<16} "
            f"{fmt([r['mean_hops'] for r in xs], 3):<16} "
            f"{fmt([r['hop_flight_s'] for r in xs], 3):<14} "
            f"{fmt([r['first_fire_rate'] for r in xs], 3):<12}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    args = ap.parse_args()
    if not BIN.is_file():
        print(f"missing binary {BIN}", file=sys.stderr)
        return 2
    jobs: list[tuple[str, int, float]] = []
    for seed in SEEDS:
        jobs.append(("lqarp", seed, 0.0))
    for b2 in BETA2:
        for seed in SEEDS:
            jobs.append(("elqtp", seed, b2))
    rows: list[dict] = []
    print(f"running {len(jobs)} jobs, jobs={args.jobs}", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futs = {ex.submit(run_one, p, s, b): (p, s, b) for p, s, b in jobs}
        for fut in as_completed(futs):
            p, s, b = futs[fut]
            try:
                row = fut.result()
                rows.append(row)
                print(
                    f"  ok {p} seed={s} b2={b:g} PDR={row['PDR']:.4f} "
                    f"hops={row['mean_hops']:.3f} T_e2e={row['T_e2e_s']:.3f} "
                    f"O_ctrl={row['O_ctrl_byte_per_s']:.1f}",
                    flush=True,
                )
            except Exception as e:
                print(f"  FAIL {p} seed={s} b2={b}: {e}", flush=True)
                return 1
    write_csv(rows, CSV_PATH)
    print(f"wrote {CSV_PATH}")
    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
