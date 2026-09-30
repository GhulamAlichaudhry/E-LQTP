#!/usr/bin/env python3
"""Step 6 Task 1b: Step 1g's bit-width methodology on the Step-5-fixed code.
elqtp-energy, Scenario II and III @ 2 m/s, seeds 20260921-25, --hopDiag.
Geometry 'Rstar' = r_range default (R*, Step 1g's geometry); 'R2500' = final."""
import csv, os, re, subprocess, sys, statistics as st
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
import step1_campaign as base
OUT = base.ROOT / "results/final_campaign/bitwidth"; RUN = OUT / "runs"; RUN.mkdir(parents=True, exist_ok=True)
BITS = [int(b) for b in os.environ.get("BW_BITS", "8 10 12 16 17 18 19 20 24 32").split()]
GEOS = {"Rstar": [], "R2500": ["--rRange=2500"]}
def one(job):
    geo, sc, bits, seed = job
    s = f"{geo}_s{sc}_q{bits}_{seed}"
    cmd = [str(base.BIN), f"--dataDir={base.DATA_DIR}", f"--scenario={sc}", "--nAuv=40", "--simTime=600",
           f"--seed={seed}", "--driftSpeed=2.0", "--protocol=elqtp-energy", f"--energyBits={bits}",
           "--boundary=remove", "--quiet", "--hopDiag=1", f"--out={RUN / (s + '.txt')}",
           "--beta_1=0", "--beta_2=0"] + GEOS[geo]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode: raise RuntimeError(s + p.stdout[-800:])
    t = (RUN / (s + ".txt")).read_text() + p.stdout
    sw = dict(re.findall(r"(\w+)=(\S+)", re.search(r"^SWEEP .*", t, re.M).group(0)))
    hd = dict(re.findall(r"(\w+)=(\S+)", re.search(r"^HOPDIAG proto.*", t, re.M).group(0)))
    return dict(geometry=geo, scenario=sc, bits=bits, seed=seed, PDR=float(sw["PDR"]), hops=float(sw["mean_hops"]),
                T_e2e=float(sw["T_e2e"]), O_ctrl=float(sw["O_ctrl"]), O_ene=float(sw["O_ene"]), O_total=float(sw["O_total"]),
                sink_in=int(hd["sink_in"]), sink_not_chosen=int(hd["sink_not_chosen"]), r_range=float(sw["r_range"]))
jobs = [(g, sc, b, seed) for g in GEOS for sc in ("ii", "iii") for b in BITS for seed in base.SEEDS]
with ThreadPoolExecutor(2) as ex: rows = list(ex.map(one, jobs))
with open(OUT / "bitwidth_sweep.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("jobs", len(rows))
lines = []
for g in GEOS:
    lines += [f"\n### geometry {g} (r_range = {rows[[r['geometry'] for r in rows].index(g)]['r_range']:.0f} m)", "",
              "| bits | step (J) | step/E_ini | II hops | II pass-over | II PDR | II O_total | III hops | III pass-over | III PDR | III O_total |",
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for b in BITS:
        cell = []
        for sc in ("ii", "iii"):
            rs = [r for r in rows if r["geometry"] == g and r["scenario"] == sc and r["bits"] == b]
            po = sum(r["sink_not_chosen"] for r in rs) / max(1, sum(r["sink_in"] for r in rs))
            cell.append(f"{st.mean(r['hops'] for r in rs):.3f} ± {st.stdev(r['hops'] for r in rs):.3f} | {po:.1%} | "
                        f"{st.mean(r['PDR'] for r in rs):.4f} | {st.mean(r['O_total'] for r in rs):.1f}")
        step = 10000 / (2 ** b - 1)
        lines.append(f"| {b} | {step:.4g} | {step/10000:.2e} | " + " | ".join(cell) + " |")
(OUT / "bitwidth_sweep.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))
