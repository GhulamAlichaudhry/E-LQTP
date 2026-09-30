#!/usr/bin/env python3
"""Step 4: new campaign (received-only z_k, r_range=2500 m) vs manuscript Tables II–V.
Published values and the flag rule are imported unchanged from step1_compare.py.
Adds the O_ene / O_total columns (O_total is the headline overhead)."""
import csv, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import step1_compare as sc
ROOT = sc.ROOT
CAMP = ROOT / "results/step4_final/campaign/step1_campaign.csv"
EN = ROOT / "results/step4_final/tctrl_sweep/tctrl_sweep.csv"
OUT = ROOT / "results/step4_final/COMPARISON.md"
g = defaultdict(list)
for p, keep in ((CAMP, None), (EN, "elqtp-energy")):
    for r in csv.DictReader(open(p)):
        if keep and r["protocol"] != keep:
            continue
        g[(r["scenario"], r["protocol"], float(r["drift_mps"]))].append(r)
def agg(rs, k):
    return sc.mean_sd([float(r[k]) for r in rs])
NAMES = dict(sc.NAMES, **{"elqtp-energy": "E-LQTP+energy (32-bit)"})
MET = [("pdr", "PDR", "PDR"), ("hops", "Hops", "mean_hops"), ("te2e", "T_e2e", "T_e2e_s"),
       ("ebit", "E_bit", "E_bit_J_per_bit"), ("octrl", "O_ctrl", "O_ctrl_byte_per_s")]
def table(title, ref, drift, protos):
    out = [f"### {title}", "", "| Protocol | " + " | ".join(m[1] for m in MET) + " | O_ene | **O_total** |",
           "|---|" + "---|" * (len(MET) + 2)]
    nflag = 0
    for p in protos:
        rs = g.get((drift[0], p, drift[1]), [])
        if not rs:
            continue
        cells = []
        for kind, _, col in MET:
            mu, sd = agg(rs, col)
            cell = ref.get(p, {}).get(kind) if p in ref else None
            nflag += sc.flagged(mu, cell, kind) if cell is not None else 0
            cells.append(sc.cell_text(mu, sd, cell, kind))
        oe = agg(rs, "O_ene_byte_per_s"); ot = agg(rs, "O_total_byte_per_s")
        out.append(f"| {NAMES[p]} | " + " | ".join(cells) + f" | {oe[0]:.1f} | **{ot[0]:.1f} ± {ot[1]:.1f}** |")
    out += ["", f"Flagged cells: {nflag} (E-LQTP+energy is not in the manuscript; no flags).", ""]
    return out
P4 = ["lqarp", "elqtp", "elqtp-energy", "rlor", "periodic"]
L = ["# Step 4 campaign vs manuscript Tables II–V", "",
     "Code: received-only z_k (Step 2) + r_range = 2500 m (Step 3). Seeds 20260921–25, N=40, "
     "boundary=remove, β1=β2=0. Mean ± sample s.d. over five seeds; `(ms …)` is the published value; "
     "**FLAG** = outside published mean ± s.d. (rule unchanged from step1_compare.py). "
     "O_total = O_ctrl + O_ene (byte/s) is the headline overhead.", ""]
L += table("Scenario I (Table II)", sc.S1, ("i", 0.0), P4)
L += table("Scenario II, 2 m/s (Table III)", sc.S2_PROTO, ("ii", 2.0), P4)
L += ["### Scenario II drift sweep (Table IV)", "", "| v | Protocol | PDR | T_e2e | Hops | O_ctrl | O_ene | **O_total** |", "|---:|---|---|---|---|---|---|---|"]
nf = 0
for v in sc.sorted(set(k[2] for k in g if k[0] == "ii")) if hasattr(sc, "sorted") else sorted(set(k[2] for k in g if k[0] == "ii")):
    for p in ("lqarp", "elqtp", "elqtp-energy"):
        rs = g.get(("ii", p, v), [])
        ref = sc.S2_DRIFT.get((v, p))
        row = []
        for kind, col in (("pdr", "PDR"), ("te2e", "T_e2e_s"), ("hops", "mean_hops"), ("octrl", "O_ctrl_byte_per_s")):
            mu, sd = agg(rs, col); cell = ref[kind] if ref else None
            nf += sc.flagged(mu, cell, kind) if cell is not None else 0
            row.append(sc.cell_text(mu, sd, cell, kind))
        oe = agg(rs, "O_ene_byte_per_s"); ot = agg(rs, "O_total_byte_per_s")
        L.append(f"| {v:.1f} | {NAMES[p]} | " + " | ".join(row) + f" | {oe[0]:.1f} | **{ot[0]:.1f}** |")
L += ["", f"Flagged cells: {nf}.", ""]
L += table("Scenario III (Table V)", sc.S3, ("iii", 2.0), P4)
OUT.write_text("\n".join(L) + "\n")
import re
print("\n".join(l for l in L if l.startswith("Flagged") or l.startswith("###")))
