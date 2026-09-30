#!/usr/bin/env python3
"""Control: elqtp-energy with the position/SNR trigger disabled (epsilon_0=1e12).
Same matrix/seeds/r_range as Step 4. Isolates the trigger's routing effect."""
import os, sys, csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(__file__))
import step1_campaign as base, tctrl_sweep as ts
OUT = Path(os.environ.get("TRIG_OUT", str(base.ROOT / "results" / "step4_final" / "trigger_off"))); RUN = OUT / "runs"; RUN.mkdir(parents=True, exist_ok=True)
def one(c):
    sc, d, sim, seed = c
    s = f"s{sc}_elqtp-energy-trigoff_q32_d{d:.1f}_{seed}"
    cmd = [str(base.BIN), f"--dataDir={base.DATA_DIR}", f"--scenario={sc}", "--nAuv=40", f"--simTime={sim:.0f}",
           f"--seed={seed}", f"--driftSpeed={d}", "--protocol=elqtp-energy", "--boundary=remove", "--quiet",
           f"--out={RUN / (s + '.txt')}", "--beta_1=0", "--beta_2=0", "--energyBits=32", "--epsilon_0=1e12"] + base.EXTRA
    import subprocess
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode: raise RuntimeError(p.stdout[-1500:])
    r = base.parse_sweep((RUN / (s + ".txt")).read_text() + p.stdout); r["scenario"] = sc; return r
cases = [(sc, d, sim, seed) for sc, d, sim in ts.cases() for seed in base.SEEDS]
with ThreadPoolExecutor(2) as ex: rows = list(ex.map(one, cases))
with (OUT / "trigger_off.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=base.FIELDS, extrasaction="ignore"); w.writeheader(); [w.writerow(r) for r in rows]
print("rows", len(rows))
