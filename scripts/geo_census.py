#!/usr/bin/env python3
"""Step 3: hop-distance-to-sink census for LQARP vs r_range (Scenario I, II@2 m/s)."""
import os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import step1_campaign as base
OUT = base.ROOT / "results" / "step3_geometry"; (OUT / "runs").mkdir(parents=True, exist_ok=True)
RANGES = [None] + [float(x) for x in (sys.argv[1:] or ["3000", "2800", "2500", "2200", "2000"])]
CASES = [("i", 0.0, 1600.0), ("ii", 2.0, 600.0)]
KEYS = ["samples", "outside_r", "route_1", "route_2", "route_3p", "route_unreach",
        "range_1", "range_2", "range_3p", "range_unreach", "r_range"]
def run(job):
    sc, d, sim, seed, r, proto = job
    tag = "Rstar" if r is None else f"R{r:g}"
    out = OUT / "runs" / f"s{sc}_{proto}_{tag}_d{d:.1f}_{seed}.txt"
    cmd = [str(base.BIN), f"--dataDir={base.DATA_DIR}", f"--scenario={sc}", "--nAuv=40",
           f"--simTime={sim:.0f}", f"--seed={seed}", f"--driftSpeed={d}", f"--protocol={proto}",
           "--boundary=remove", "--quiet", f"--out={out}", "--geoCensus=1"]
    if r is not None: cmd.append(f"--rRange={r:g}")
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode: raise RuntimeError(p.stdout[-1500:])
    txt = out.read_text() + p.stdout
    hg = dict(re.findall(r"(\w+)=(\S+)", re.search(r"^HOPGEO .*", txt, re.M).group(0)))
    sw = dict(re.findall(r"(\w+)=(\S+)", re.search(r"^SWEEP .*", txt, re.M).group(0)))
    return job, {k: float(hg[k]) for k in KEYS}, float(sw["PDR"]), float(sw["mean_hops"])
jobs = [(sc, d, sim, seed, r, "lqarp") for sc, d, sim in CASES for r in RANGES for seed in base.SEEDS]
agg = defaultdict(lambda: defaultdict(float)); pdr = defaultdict(list); hops = defaultdict(list)
with ThreadPoolExecutor(2) as ex:
    for job, hg, p, h in ex.map(run, jobs):
        k = (job[0], job[4]); [agg[k].__setitem__(x, agg[k][x] + hg[x]) for x in KEYS if x != "r_range"]
        agg[k]["r_range"] = hg["r_range"]; pdr[k].append(p); hops[k].append(h)
lines = ["| Scenario | r_range (m) | outside r_range of sink | routing graph: 1 / 2 / 3+ hops / unreachable | range-only graph: 1 / 2 / 3+ / unreach | LQARP PDR | LQARP mean hops |",
         "|---|---:|---:|---|---|---:|---:|"]
for k in sorted(agg, key=lambda k: (k[0], -(k[1] or 1e9))):
    a = agg[k]; n = a["samples"]; f = lambda x: f"{100*a[x]/n:.1f}%"
    lines.append(f"| {k[0].upper()} | {a['r_range']:.0f}{' (R*)' if k[1] is None else ''} | {f('outside_r')} | "
                 f"{f('route_1')} / {f('route_2')} / {f('route_3p')} / {f('route_unreach')} | "
                 f"{f('range_1')} / {f('range_2')} / {f('range_3p')} / {f('range_unreach')} | "
                 f"{sum(pdr[k])/5:.4f} | {sum(hops[k])/5:.3f} |")
(OUT / "census.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))
