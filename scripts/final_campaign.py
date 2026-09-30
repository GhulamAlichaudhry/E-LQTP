#!/usr/bin/env python3
"""Step 6 FINAL campaign (dataset of record).

Code: received-only z_k (Step 2), r_range = 2500 m (Step 3), quantizer fix +
reception-gated HELLO/beacon writes (Step 5). Energy beacon width = 18 bits
(Step 6 Task 2). Seeds 20260921-25, N=40, boundary=remove, beta_1=beta_2=0.

Parts (each its own subfolder of results/final_campaign/):
  campaign/       LQARP, E-LQTP, E-LQTP+energy, Fixed-Periodic (T=5), RLOR
                  at Scenario I, II x {0.5,1,2,3,3.5} m/s, III
  tctrl_sweep/    Fixed-Periodic at T_ctrl = 5/10/20/40/60 s, same cases
  trigger_off/    E-LQTP+energy with epsilon_0 = 1e12 (trigger never fires)
  decision_trace/ the campaign + trigger-off runs repeated with
                  --decisionTrace; each trace run's SWEEP line must equal the
                  dataset run's SWEEP line byte-for-byte (non-perturbation).
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step1_campaign as base  # noqa: E402  (BIN, DATA_DIR, SEEDS, DRIFT, parse_sweep, FIELDS)

OUT = Path(os.environ.get("FINAL_OUT", str(base.ROOT / "results" / "final_campaign")))
ENERGY_BITS = 18
R_RANGE = 2500
COMMON = [f"--rRange={R_RANGE}", "--beta_1=0", "--beta_2=0", "--boundary=remove",
          "--quiet", "--nAuv=40", "--helloRxGate=1"]
T_CTRL = [5, 10, 20, 40, 60]

# protocol label -> CLI flags
VARIANTS = {
    "lqarp": ["--protocol=lqarp"],
    "elqtp": ["--protocol=elqtp"],
    "elqtp-energy": ["--protocol=elqtp-energy", f"--energyBits={ENERGY_BITS}"],
    "periodic": ["--protocol=periodic", "--tCtrl=5"],
    "rlor": ["--protocol=rlor"],
    "elqtp-energy-trigoff": ["--protocol=elqtp-energy", f"--energyBits={ENERGY_BITS}",
                             "--epsilon_0=1e12"],
}
FIELDS = ["part", "variant", "T_ctrl_s", "energy_bits"] + base.FIELDS


def cases():
    out = [("i", 0.0, 1600.0)]
    out += [("ii", d, 600.0) for d in base.DRIFT]
    out += [("iii", 2.0, 600.0)]
    return out


def jobs(parts):
    J = []
    for sc, d, sim in cases():
        for seed in base.SEEDS:
            if "campaign" in parts:
                for v in ("lqarp", "elqtp", "elqtp-energy", "periodic", "rlor"):
                    J.append(dict(part="campaign", variant=v, sc=sc, d=d, sim=sim, seed=seed, extra=[]))
            if "tctrl_sweep" in parts:
                for t in T_CTRL:
                    J.append(dict(part="tctrl_sweep", variant=f"periodic-T{t}", sc=sc, d=d, sim=sim,
                                  seed=seed, extra=["--protocol=periodic", f"--tCtrl={t}"]))
            if "trigger_off" in parts:
                J.append(dict(part="trigger_off", variant="elqtp-energy-trigoff", sc=sc, d=d, sim=sim,
                              seed=seed, extra=[]))
            if "decision_trace" in parts:
                for v in ("lqarp", "elqtp", "elqtp-energy", "periodic", "rlor", "elqtp-energy-trigoff"):
                    J.append(dict(part="decision_trace", variant=v, sc=sc, d=d, sim=sim, seed=seed,
                                  extra=["--decisionTrace=1"]))
    return J


def stem(j):
    return f"s{j['sc']}_{j['variant']}_d{j['d']:.1f}_{j['seed']}"


def run(j):
    rd = OUT / j["part"] / "runs"
    rd.mkdir(parents=True, exist_ok=True)
    out = rd / f"{stem(j)}.txt"
    flags = j["extra"] if j["part"] == "tctrl_sweep" else VARIANTS[j["variant"]] + j["extra"]
    cmd = [str(base.BIN), f"--dataDir={base.DATA_DIR}", f"--scenario={j['sc']}",
           f"--simTime={j['sim']:.0f}", f"--seed={j['seed']}", f"--driftSpeed={j['d']}",
           f"--out={out}"] + COMMON + flags
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       env=dict(os.environ, NS_LOG=""))
    (rd / f"{stem(j)}.log").write_text(" ".join(cmd) + "\n" + p.stdout)
    if p.returncode:
        raise RuntimeError(f"{stem(j)} rc={p.returncode}\n{p.stdout[-1500:]}")
    text = out.read_text() + "\n" + p.stdout
    row = base.parse_sweep(text)
    if row["seed"] != j["seed"] or row["N"] != 40 or row["scenario"] != j["sc"]:
        raise RuntimeError(f"{stem(j)} parse mismatch")
    if abs(row["r_range_m"] - R_RANGE) > 1e-9:
        raise RuntimeError(f"{stem(j)} r_range {row['r_range_m']}")
    if "energy" in j["variant"] and f"quantized to {ENERGY_BITS} bits" not in p.stdout:
        raise RuntimeError(f"{stem(j)} energy bits not echoed")
    t = re.search(r"T_ctrl=(\S+) s", p.stdout) if "periodic" in j["variant"] else None
    row.update(part=j["part"], variant=j["variant"], T_ctrl_s=(float(t.group(1)) if t else ""),
               energy_bits=(ENERGY_BITS if "energy" in j["variant"] else ""))
    sw = re.search(r"^SWEEP .*$", out.read_text(), re.M)
    row["_sweep"] = sw.group(0) if sw else ""
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", default="campaign,tctrl_sweep,trigger_off,decision_trace")
    ap.add_argument("--jobs", type=int, default=2)
    a = ap.parse_args()
    parts = a.parts.split(",")
    J = jobs(parts)
    print(f"binary={base.BIN}\njobs={len(J)}", flush=True)
    rows, fails = [], []
    with ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(run, j): j for j in J}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                rows.append(f.result())
            except Exception as e:  # noqa: BLE001
                fails.append(f"{stem(futs[f])}: {e}")
            if n % 100 == 0:
                print(f"[{n}/{len(J)}] failures={len(fails)}", flush=True)
    for part in parts:
        pr = sorted([r for r in rows if r["part"] == part],
                    key=lambda r: (r["scenario"], r["drift_mps"], r["variant"], r["seed"]))
        with (OUT / part / f"{part}.csv").open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in pr:
                w.writerow({k: r.get(k, "") for k in FIELDS})
        print(f"{part}: {len(pr)} rows", flush=True)
    # Non-perturbation: every decision-trace SWEEP line equals its dataset twin.
    if "decision_trace" in parts:
        twin = {}
        for r in rows:
            if r["part"] in ("campaign", "trigger_off"):
                twin[(r["scenario"], r["drift_mps"], r["variant"], r["seed"])] = r["_sweep"]
        bad = [k for r in rows if r["part"] == "decision_trace"
               for k in [(r["scenario"], r["drift_mps"], r["variant"], r["seed"])]
               if twin.get(k) != r["_sweep"]]
        (OUT / "decision_trace" / "NONPERTURBATION.txt").write_text(
            f"trace runs compared: {sum(r['part']=='decision_trace' for r in rows)}\n"
            f"SWEEP mismatches vs dataset runs: {len(bad)}\n" + "".join(f"{b}\n" for b in bad))
        print(f"decision_trace SWEEP mismatches: {len(bad)}", flush=True)
    if fails:
        (OUT / "FAILURES.txt").write_text("\n".join(fails) + "\n")
    print(f"total ok={len(rows)} failures={len(fails)}", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
