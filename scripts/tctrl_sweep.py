#!/usr/bin/env python3
"""Fixed-Periodic T_ctrl sweep (reviewer: justify the 5 s baseline).

Same seeds, N=40, site, boundary, betas and scenario matrix as
step1_campaign.py. Only Fixed-Periodic's control period changes, via
--tCtrl. Optionally also runs elqtp-energy (--energyBits, default 32,
the Step 1g/1h choice) on the same matrix so the sweep has its
comparison point from the same build.

Writes results/tctrl_sweep/ (override with SWEEP_OUT).
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step1_campaign as base  # noqa: E402

OUT_DIR = Path(os.environ.get("SWEEP_OUT", str(base.ROOT / "results" / "tctrl_sweep")))
RUN_DIR = OUT_DIR / "runs"
CSV_PATH = OUT_DIR / "tctrl_sweep.csv"

T_CTRL = [5.0, 10.0, 20.0, 40.0, 60.0]
FIELDS = ["T_ctrl_s", "energy_bits"] + base.FIELDS


def cases() -> list[tuple[str, float, float]]:
    """(scenario, drift, sim) — the manuscript matrix."""
    out = [("i", 0.0, 1600.0)]
    out += [("ii", d, 600.0) for d in base.DRIFT]
    out += [("iii", 2.0, 600.0)]
    return out


def jobs(with_energy: bool, energy_bits: int) -> list[dict]:
    out = []
    for sc, drift, sim in cases():
        for seed in base.SEEDS:
            for t in T_CTRL:
                out.append(dict(scenario=sc, drift=drift, sim=sim, seed=seed,
                                proto="periodic", tctrl=t, ebits=None))
            if with_energy:
                out.append(dict(scenario=sc, drift=drift, sim=sim, seed=seed,
                                proto="elqtp-energy", tctrl=None, ebits=energy_bits))
    return out


def stem(j: dict) -> str:
    tag = f"T{j['tctrl']:g}" if j["tctrl"] is not None else f"q{j['ebits']}"
    return f"s{j['scenario']}_{j['proto']}_{tag}_d{j['drift']:.1f}_n40_{j['seed']}"


def run_one(j: dict) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    s = stem(j)
    out_path, log_path = RUN_DIR / f"{s}.txt", RUN_DIR / f"{s}.log"
    cmd = [str(base.BIN), f"--dataDir={base.DATA_DIR}", f"--scenario={j['scenario']}",
           "--nAuv=40", f"--simTime={j['sim']:.0f}", f"--seed={j['seed']}",
           f"--driftSpeed={j['drift']}", f"--protocol={j['proto']}",
           "--boundary=remove", "--quiet", f"--out={out_path}",
           f"--beta_1={base.BETA1:.10e}", f"--beta_2={base.BETA2:.10e}"]
    if j["tctrl"] is not None:
        cmd.append(f"--tCtrl={j['tctrl']:g}")
    if j["ebits"] is not None:
        cmd.append(f"--energyBits={j['ebits']}")
    cmd.extend(base.EXTRA)
    env = dict(os.environ, NS_LOG="")
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    log_path.write_text(p.stdout)
    if p.returncode != 0:
        raise RuntimeError(f"{s} exited {p.returncode}\n{p.stdout[-2000:]}")
    text = (out_path.read_text() if out_path.exists() else "") + "\n" + p.stdout
    row = base.parse_sweep(text)
    if row["seed"] != j["seed"] or row["N"] != 40 or row["scenario"] != j["scenario"]:
        raise RuntimeError(f"{s} parse mismatch: {row}")
    if j["tctrl"] is not None and f"T_ctrl={j['tctrl']:g} s" not in p.stdout:
        raise RuntimeError(f"{s}: binary did not echo T_ctrl={j['tctrl']:g}")
    row["T_ctrl_s"] = j["tctrl"] if j["tctrl"] is not None else ""
    row["energy_bits"] = j["ebits"] if j["ebits"] is not None else ""
    return row


def write_csv(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["scenario"], r["drift_mps"], r["protocol"],
                                       float(r["T_ctrl_s"] or 0), r["seed"]))
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    ap.add_argument("--energy", action="store_true", help="also run elqtp-energy")
    ap.add_argument("--energy-bits", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    pending = jobs(a.energy, a.energy_bits)
    if a.limit:
        pending = pending[: a.limit]
    print(f"binary={base.BIN}\njobs={len(pending)} workers={a.jobs}", flush=True)
    rows, fails = [], []
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futs = {pool.submit(run_one, j): j for j in pending}
        for n, fut in enumerate(as_completed(futs), 1):
            j = futs[fut]
            try:
                r = fut.result()
            except Exception as e:  # noqa: BLE001
                fails.append(f"{stem(j)}: {e}")
                print(f"[{n}/{len(pending)}] FAIL {stem(j)}", flush=True)
                continue
            rows.append(r)
            write_csv(rows)
            print(f"[{n}/{len(pending)}] {stem(j)} PDR={r['PDR']:.4f} "
                  f"hops={r['mean_hops']:.3f} O={r['O_ctrl_byte_per_s']:.2f}", flush=True)
    write_csv(rows)
    print(f"wrote {CSV_PATH} rows={len(rows)} failures={len(fails)}", flush=True)
    if fails:
        (OUT_DIR / "FAILURES.txt").write_text("\n".join(fails) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
