#!/usr/bin/env python3
"""Step 69: Scenario II headline tables at validated beta_1=beta_2=0.

LQARP / RLOR rows are reused from the Step 53/54 diagnostic CSV
(those protocols do not use beta). E-LQTP and Fixed-Periodic are
re-run. Do not mix these rows with scenario2_multiseed_data.csv.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scenario2_sweep as s2

s2.CSV_PATH = s2.OUT_DIR / "scenario2_headline_data.csv"
s2.RUN_DIR = s2.OUT_DIR / "scenario2_headline"
BASELINE_CSV = s2.OUT_DIR / "scenario2_multiseed_data.csv"
BETA1 = 0.0
BETA2 = 0.0


def run_one(proto: str, seed: int, drift: float) -> dict:
    s2.RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = s2.job_key(proto, seed, drift)
    out_path = s2.RUN_DIR / f"{stem}.txt"
    cmd = [
        str(s2.BIN),
        f"--dataDir={s2.DATA_DIR}",
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
        cmd.extend([f"--beta_1={BETA1:.10e}", f"--beta_2={BETA2:.10e}"])
    env = os.environ.copy()
    env.setdefault("NS_LOG", "")
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    text = proc.stdout
    if out_path.exists():
        text = out_path.read_text() + "\n" + text
    (s2.RUN_DIR / f"{stem}.log").write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"{stem} exited {proc.returncode}\n{proc.stdout[-2000:]}")
    row = s2.parse_sweep(text)
    if row["protocol"] != proto or row["seed"] != seed:
        raise RuntimeError(f"{stem} parsed proto/seed mismatch: {row}")
    if proto in ("elqtp", "periodic"):
        b1 = float(re.search(r"beta_1=(\S+)", text).group(1))
        b2 = float(re.search(r"beta_2=(\S+)", text).group(1))
        if abs(b1 - BETA1) > 1e-12 or abs(b2 - BETA2) > 1e-12:
            raise RuntimeError(f"{stem} beta mismatch: {b1}/{b2}")
        row["beta_1"] = b1
        row["beta_2"] = b2
        return row
    row["beta_1"] = BETA1 if proto in ("elqtp", "periodic") else 0.0
    row["beta_2"] = BETA2 if proto in ("elqtp", "periodic") else 0.0
    return row


def load_baselines() -> dict[tuple, dict]:
    if not BASELINE_CSV.is_file():
        return {}
    out: dict[tuple, dict] = {}
    for r in s2.load_csv(BASELINE_CSV):
        if r["protocol"] in ("lqarp", "rlor"):
            r = dict(r)
            r["beta_1"] = 0.0
            r["beta_2"] = 0.0
            out[(r["protocol"], r["seed"], float(r["drift_mps"]))] = r
    return out


def _install_headline_stems() -> None:
    orig = s2.save_figure

    def save_headline(fig, stem: str) -> None:
        mapping = {
            "scenario2_figA_protocol": "scenario2_headline_figA_protocol",
            "scenario2_figB_drift": "scenario2_headline_figB_drift",
        }
        orig(fig, mapping.get(stem, stem))

    s2.save_figure = save_headline


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["53", "54", "all", "figures"], default="all")
    ap.add_argument("--jobs", type=int, default=max(1, os.cpu_count() or 2))
    ap.add_argument("--skip-run", action="store_true")
    args = ap.parse_args()

    existing: dict[tuple, dict] = {}
    if s2.CSV_PATH.exists():
        for r in s2.load_csv(s2.CSV_PATH):
            existing[(r["protocol"], r["seed"], float(r["drift_mps"]))] = r
    if not existing:
        existing.update(load_baselines())
        print(f"reused {len(existing)} LQARP/RLOR baseline rows from {BASELINE_CSV}")

    rows = list(existing.values())
    if args.step != "figures" and not args.skip_run:
        if not s2.BIN.exists():
            print(f"missing binary {s2.BIN}", file=sys.stderr)
            return 2
        todo = [
            j
            for j in s2.jobs_for_steps(args.step)
            if (j[0], j[1], float(j[2])) not in existing
        ]
        print(f"runs to launch: {len(todo)} (reuse {len(existing)}) jobs={args.jobs}")
        print(f"operating point: beta_1={BETA1:g} beta_2={BETA2:g}", flush=True)
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
                        f"  [{done}/{len(todo)}] {s2.job_key(*j)} "
                        f"PDR={row['PDR']:.4f} hops={row['mean_hops']:.3f} "
                        f"O_ctrl={row['O_ctrl_byte_per_s']:.2f}",
                        flush=True,
                    )
        rows = list(existing.values())
        extra_cols = list(s2.CSV_COLUMNS)
        for c in ("beta_1", "beta_2"):
            if c not in extra_cols:
                extra_cols.extend(["beta_1", "beta_2"])
                break
        orig = s2.CSV_COLUMNS
        s2.CSV_COLUMNS = extra_cols
        s2.write_csv(rows, s2.CSV_PATH)
        s2.CSV_COLUMNS = orig
        print(f"wrote {s2.CSV_PATH} n={len(rows)}")

    if not rows:
        print("no rows to plot", file=sys.stderr)
        return 1

    _install_headline_stems()
    s2.figure_a(rows)
    s2.figure_b(rows)
    print(f"figures in {s2.FIG_DIR} (headline stems)")

    print("\n=== Step 69 / Scenario II v=2.0 (beta_1=beta_2=0) ===")
    print(
        "| protocol | PDR | T_e2e (s) | E_bit (J/bit) | O_ctrl (byte/s) | hops | VOID | LOST | rising |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    print(s2.table_block(rows, 2.0, s2.PROTOS_53))

    print("\n=== Step 69 / Scenario II vs drift (beta_1=beta_2=0) ===")
    print(
        "| protocol | PDR | T_e2e (s) | E_bit (J/bit) | O_ctrl (byte/s) | hops | VOID | LOST | rising |"
    )
    print("|---|---|---|---|---|---|---|---|---|")
    for d in s2.ALL_DRIFT:
        print(s2.table_block(rows, d, s2.PROTOS_54))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
