#!/usr/bin/env python3
"""Re-run manuscript Scenarios I–III on the Step-1 held-neighbor build.

Same seeds, N=40, site, drift sweep, and eddy defaults as Tables II–V.
Writes results/step1_rerun/ only. Does not touch the manuscript CSVs.
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
OUT_DIR = Path(os.environ.get("STEP1_OUT", str(ROOT / "results" / "step1c_rerun")))
RUN_DIR = OUT_DIR / "runs"
CSV_PATH = OUT_DIR / "step1_campaign.csv"

SEEDS = [20260921, 20260922, 20260923, 20260924, 20260925]
PROTOS = ["lqarp", "elqtp", "rlor", "periodic"]
DRIFT = [0.5, 1.0, 2.0, 3.0, 3.5]
BETA1 = 0.0
BETA2 = 0.0
# Extra CLI flags for every run, e.g. ELQTP_EXTRA="--rRange=2500".
EXTRA = os.environ.get("ELQTP_EXTRA", "").split()

SWEEP_RE = re.compile(r"^SWEEP\s+(.*)$", re.M)
KV_RE = re.compile(r"(\w+)=(\S+)")

FIELDS = [
    "scenario",
    "protocol",
    "seed",
    "N",
    "drift_mps",
    "T_sim_s",
    "PDR",
    "T_e2e_s",
    "E_bit_J_per_bit",
    "O_ctrl_byte_per_s",
    "mean_hops",
    "first_fire_rate",
    "VOID",
    "VOID_stale",
    "VOID_via_stale",
    "VOID_live",
    "SNR",
    "SNR_stale",
    "SNR_genuine",
    "LOST_NODE_EXIT",
    "envelope_via_stale",
    "stale_admit",
    "stale_admit_ok",
    "n_gen",
    "n_succ",
    "n_tx",
    "event_hellos",
    "bootstrap_hellos",
    "beta_1",
    "beta_2",
    "O_ene_byte_per_s",
    "O_total_byte_per_s",
    "r_range_m",
    "rx_events",
    "z_updates",
]


def jobs() -> list[dict]:
    out: list[dict] = []
    for proto in PROTOS:
        for seed in SEEDS:
            out.append(
                dict(scenario="i", proto=proto, seed=seed, drift=0.0, sim=1600.0)
            )
    for drift in DRIFT:
        protos = PROTOS if drift == 2.0 else ["lqarp", "elqtp"]
        for proto in protos:
            for seed in SEEDS:
                out.append(
                    dict(
                        scenario="ii",
                        proto=proto,
                        seed=seed,
                        drift=drift,
                        sim=600.0,
                    )
                )
    for proto in PROTOS:
        for seed in SEEDS:
            out.append(
                dict(scenario="iii", proto=proto, seed=seed, drift=2.0, sim=600.0)
            )
    return out


def stem_of(job: dict) -> str:
    drift = f"{job['drift']:.1f}"
    return f"s{job['scenario']}_{job['proto']}_d{drift}_n40_{job['seed']}"


def parse_sweep(text: str) -> dict:
    m = SWEEP_RE.search(text)
    if not m:
        raise ValueError("no SWEEP line")
    kv = {k: v for k, v in KV_RE.findall(m.group(1))}

    def f(name: str) -> float:
        v = kv.get(name, "nan")
        if v in ("nan", "NaN", "-nan"):
            return float("nan")
        return float(v)

    def i(name: str) -> int:
        return int(float(kv.get(name, "0")))

    return {
        "protocol": kv["proto"],
        "seed": i("seed"),
        "N": i("N"),
        "drift_mps": f("drift"),
        "T_sim_s": f("T_sim"),
        "PDR": f("PDR"),
        "T_e2e_s": f("T_e2e"),
        "E_bit_J_per_bit": f("E_bit"),
        "O_ctrl_byte_per_s": f("O_ctrl"),
        "mean_hops": f("mean_hops"),
        "first_fire_rate": f("first_fire"),
        "VOID": i("VOID"),
        "VOID_stale": i("VOID_stale"),
        "VOID_via_stale": i("VOID_via_stale"),
        "VOID_live": i("VOID_live"),
        "SNR": i("SNR"),
        "SNR_stale": i("SNR_stale"),
        "SNR_genuine": i("SNR_genuine"),
        "LOST_NODE_EXIT": i("LOST_NODE_EXIT"),
        "envelope_via_stale": i("envelope_via_stale"),
        "stale_admit": i("stale_admit"),
        "stale_admit_ok": i("stale_admit_ok"),
        "n_gen": i("n_gen"),
        "n_succ": i("n_succ"),
        "n_tx": i("n_tx"),
        "event_hellos": i("event_hellos"),
        "bootstrap_hellos": i("bootstrap_hellos"),
        "beta_1": f("beta_1"),
        "beta_2": f("beta_2"),
        "scenario": kv.get("scenario", ""),
        # Energy beacon cost is reported apart from O_ctrl; O_total is the
        # honest headline. Older binaries lack these keys: O_ene=0.
        "O_ene_byte_per_s": f("O_ene") if "O_ene" in kv else 0.0,
        "O_total_byte_per_s": f("O_total") if "O_total" in kv else f("O_ctrl"),
        "r_range_m": f("r_range"),
        "rx_events": i("rx_events"),
        "z_updates": i("z_updates"),
    }


def run_one(job: dict) -> dict:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    stem = stem_of(job)
    out_path = RUN_DIR / f"{stem}.txt"
    log_path = RUN_DIR / f"{stem}.log"
    cmd = [
        str(BIN),
        f"--dataDir={DATA_DIR}",
        f"--scenario={job['scenario']}",
        "--nAuv=40",
        f"--simTime={job['sim']:.0f}",
        f"--seed={job['seed']}",
        f"--driftSpeed={job['drift']}",
        f"--protocol={job['proto']}",
        "--boundary=remove",
        "--quiet",
        f"--out={out_path}",
    ]
    if job["proto"] in ("elqtp", "periodic"):
        cmd.extend([f"--beta_1={BETA1:.10e}", f"--beta_2={BETA2:.10e}"])
    cmd.extend(EXTRA)
    env = os.environ.copy()
    env["NS_LOG"] = ""
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
    )
    log_path.write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"{stem} exited {proc.returncode}\n{proc.stdout[-2000:]}")
    text = out_path.read_text() if out_path.exists() else ""
    text = text + "\n" + proc.stdout
    row = parse_sweep(text)
    if row["protocol"] != job["proto"] or row["seed"] != job["seed"]:
        raise RuntimeError(f"{stem} parsed proto/seed mismatch: {row}")
    if row["scenario"] != job["scenario"]:
        raise RuntimeError(f"{stem} scenario mismatch: {row['scenario']}")
    if row["N"] != 40:
        raise RuntimeError(f"{stem} N={row['N']}")
    if job["proto"] in ("elqtp", "periodic"):
        if abs(row["beta_1"] - BETA1) > 1e-12 or abs(row["beta_2"] - BETA2) > 1e-12:
            raise RuntimeError(f"{stem} beta {row['beta_1']}/{row['beta_2']}")
    row["scenario"] = job["scenario"]
    return row


def write_csv(rows: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (r["scenario"], r["drift_mps"], r["protocol"], r["seed"]))
    with CSV_PATH.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    ap.add_argument("--limit", type=int, default=0, help="run only the first N jobs")
    args = ap.parse_args()
    if not BIN.is_file():
        print(f"missing binary: {BIN}", file=sys.stderr)
        return 1
    if not DATA_DIR.is_dir():
        print(f"missing channel db: {DATA_DIR}", file=sys.stderr)
        return 1
    pending = jobs()
    if args.limit:
        pending = pending[: args.limit]
    print(f"binary={BIN}", flush=True)
    print(f"jobs={len(pending)} workers={args.jobs}", flush=True)
    rows: list[dict] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(run_one, job): job for job in pending}
        done = 0
        for fut in as_completed(futs):
            job = futs[fut]
            done += 1
            try:
                row = fut.result()
            except Exception as exc:  # noqa: BLE001 — keep the campaign going
                failures.append(f"{stem_of(job)}: {exc}")
                print(f"[{done}/{len(pending)}] FAIL {stem_of(job)}: {exc}", flush=True)
                continue
            rows.append(row)
            write_csv(rows)
            print(
                f"[{done}/{len(pending)}] {stem_of(job)} PDR={row['PDR']:.6f} "
                f"O={row['O_ctrl_byte_per_s']:.3f}",
                flush=True,
            )
    write_csv(rows)
    print(f"wrote {CSV_PATH} rows={len(rows)} failures={len(failures)}", flush=True)
    if failures:
        (OUT_DIR / "FAILURES.txt").write_text("\n".join(failures) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
