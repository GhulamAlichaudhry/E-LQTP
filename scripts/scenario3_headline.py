#!/usr/bin/env python3
"""Step 70: Scenario III headline table at validated beta_1=beta_2=0.

LQARP / RLOR rows are reused from the Step 60 diagnostic CSV.
E-LQTP and Fixed-Periodic are re-run. Do not mix these rows with
scenario3_multiseed_data.csv.
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
import scenario3_compare as s3

s3.CSV_PATH = s3.OUT_DIR / "scenario3_headline_data.csv"
s3.RUN_DIR = s3.OUT_DIR / "scenario3_headline"
BASELINE_CSV = s3.OUT_DIR / "scenario3_multiseed_data.csv"
BETA1 = 0.0
BETA2 = 0.0


def run_one(proto: str, seed: int) -> dict:
    s3.RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = s3.job_key(proto, seed)
    out_path = s3.RUN_DIR / f"{stem}.txt"
    cmd = [
        str(s3.BIN),
        f"--dataDir={s3.DATA_DIR}",
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
        cmd.extend([f"--beta_1={BETA1:.10e}", f"--beta_2={BETA2:.10e}"])
    env = os.environ.copy()
    env.setdefault("NS_LOG", "")
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    text = proc.stdout
    if out_path.exists():
        text = out_path.read_text() + "\n" + text
    (s3.RUN_DIR / f"{stem}.log").write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"{stem} exited {proc.returncode}\n{proc.stdout[-2000:]}")
    row = s3.parse_sweep(text)
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
    for r in s3.load_csv(BASELINE_CSV):
        if r["protocol"] in ("lqarp", "rlor"):
            r = dict(r)
            r["beta_1"] = 0.0
            r["beta_2"] = 0.0
            out[(r["protocol"], r["seed"])] = r
    return out


def print_table(rows: list[dict]) -> None:
    print("\nStep 70 — Scenario III headline, beta_1=beta_2=0")
    print("mean ± std over 5 seeds. Replaces Step 60 as the paper table.\n")
    s3.print_table(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--reuse", action="store_true")
    args = ap.parse_args()
    if args.reuse and s3.CSV_PATH.exists():
        rows = s3.load_csv(s3.CSV_PATH)
        print_table(rows)
        return 0
    if not s3.BIN.is_file():
        print(f"missing binary {s3.BIN}", file=sys.stderr)
        return 2

    existing = load_baselines()
    print(f"reused {len(existing)} LQARP/RLOR baseline rows from {BASELINE_CSV}")
    jobs = [
        (p, s)
        for p in s3.PROTOS
        for s in s3.SEEDS
        if (p, s) not in existing
    ]
    rows = list(existing.values())
    print(
        f"running {len(jobs)} Scenario III jobs, jobs={args.jobs}, "
        f"beta_1={BETA1:g} beta_2={BETA2:g}",
        flush=True,
    )
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
    extra = list(s3.CSV_COLUMNS)
    for c in ("beta_1", "beta_2"):
        if c not in extra:
            extra.extend(["beta_1", "beta_2"])
            break
    orig = s3.CSV_COLUMNS
    s3.CSV_COLUMNS = extra
    s3.write_csv(rows, s3.CSV_PATH)
    s3.CSV_COLUMNS = orig
    print(f"wrote {s3.CSV_PATH}")
    print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
