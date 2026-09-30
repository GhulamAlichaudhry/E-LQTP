#!/usr/bin/env python3
"""Step 60 diagnostic: Scenario III 4-protocol x 5-seed at beta=1/1.

Headline table at the validated beta_1=beta_2=0 point is
scripts/scenario3_headline.py (Step 70). Do not treat this CSV
as a paper result.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
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
RUN_DIR = OUT_DIR / "scenario3_sweep"
CSV_PATH = OUT_DIR / "scenario3_multiseed_data.csv"

SEEDS = [20260921, 20260922, 20260923, 20260924, 20260925]
PROTOS = ["lqarp", "elqtp", "rlor", "periodic"]

SWEEP_RE = __import__("re").compile(r"^SWEEP\s+(.*)$", __import__("re").M)
KV_RE = __import__("re").compile(r"(\w+)=(\S+)")

CSV_COLUMNS = [
    "protocol",
    "seed",
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
    "Broadcast_k_ones",
    "ctrl_tx",
    "heard_live",
    "live_pairs",
    "first_fire_rate",
    "n_exit_tsim",
    "n_envelope",
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
        "Broadcast_k_ones": i("ones"),
        "ctrl_tx": i("ctrl_tx"),
        "heard_live": heard,
        "live_pairs": live,
        "first_fire_rate": first,
        "n_exit_tsim": i("n_exit_tsim"),
        "n_envelope": i("n_envelope"),
        "n_gen": i("n_gen"),
        "n_succ": i("n_succ"),
        "n_tx": i("n_tx"),
        "metrics_finite": i("finite"),
    }


def job_key(proto: str, seed: int) -> str:
    return f"{proto}_s{seed}"


def run_one(proto: str, seed: int) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = job_key(proto, seed)
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
        return f"{m:.{prec}e} ± {s:.{prec}e}"
    if prec == 0:
        return f"{m:.1f} ± {s:.1f}"
    return f"{m:.{prec}f} ± {s:.{prec}f}"


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x["protocol"], x["seed"])):
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


def print_table(rows: list[dict]) -> None:
    print("\nStep 60 — Scenario III, 4 protocols × 5 seeds (V_eddy=2.0 m/s)")
    print("mean ± std over 5 seeds\n")
    hdr = (
        f"{'protocol':<16} {'PDR':<18} {'T_e2e':<18} {'E_bit':<22} "
        f"{'O_ctrl':<18} {'hops':<16} {'VOID':<14} {'LOST':<14} {'rising':<14} "
        f"{'first-fire':<14} {'exits':<12}"
    )
    print(hdr)
    for p in PROTOS:
        xs = [r for r in rows if r["protocol"] == p]
        if not xs:
            continue
        print(
            f"{p:<16} "
            f"{fmt_stat([r['PDR'] for r in xs], 4):<18} "
            f"{fmt_stat([r['T_e2e_s'] for r in xs], 3):<18} "
            f"{fmt_stat([r['E_bit_J_per_bit'] for r in xs], 3, True):<22} "
            f"{fmt_stat([r['O_ctrl_byte_per_s'] for r in xs], 2):<18} "
            f"{fmt_stat([r['mean_hops'] for r in xs], 3):<16} "
            f"{fmt_stat([r['VOID'] for r in xs], 2):<14} "
            f"{fmt_stat([r['LOST_NODE_EXIT'] for r in xs], 2):<14} "
            f"{fmt_stat([r['Broadcast_k_rising'] for r in xs], 0):<14} "
            f"{fmt_stat([r['first_fire_rate'] for r in xs], 3):<14} "
            f"{fmt_stat([r['n_envelope'] for r in xs], 2):<12}"
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--reuse", action="store_true", help="load existing CSV only")
    args = ap.parse_args()
    if args.reuse and CSV_PATH.exists():
        rows = load_csv(CSV_PATH)
        print_table(rows)
        return 0
    if not BIN.is_file():
        print(f"missing binary {BIN}", file=sys.stderr)
        return 2
    jobs = [(p, s) for p in PROTOS for s in SEEDS]
    rows: list[dict] = []
    print(f"running {len(jobs)} Scenario III jobs, jobs={args.jobs}", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futs = {ex.submit(run_one, p, s): (p, s) for p, s in jobs}
        for fut in as_completed(futs):
            p, s = futs[fut]
            try:
                row = fut.result()
                rows.append(row)
                print(
                    f"  ok {p} seed={s} PDR={row['PDR']:.4f} "
                    f"hops={row['mean_hops']:.3f} O_ctrl={row['O_ctrl_byte_per_s']:.1f} "
                    f"exits={int(row['n_envelope'])}",
                    flush=True,
                )
            except Exception as e:
                print(f"  FAIL {p} seed={s}: {e}", flush=True)
                return 1
    write_csv(rows, CSV_PATH)
    print(f"wrote {CSV_PATH}")
    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
