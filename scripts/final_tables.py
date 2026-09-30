#!/usr/bin/env python3
"""Tables for the final campaign (dataset of record): Tables II-V vs the
manuscript, the T_ctrl sweep, and the decision-trace summary.
Published values and the FLAG rule are imported unchanged from step1_compare.py."""
import csv, glob, math, re, statistics as st, sys
from collections import defaultdict, Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import step1_compare as sc  # manuscript values + flagged()/cell_text()

import os
F = Path(os.environ.get("FINAL_OUT", str(sc.ROOT / "results" / "final_campaign")))
g = defaultdict(list)
for part in ("campaign", "trigger_off", "tctrl_sweep"):
    for r in csv.DictReader(open(F / part / f"{part}.csv")):
        g[(r["scenario"], float(r["drift_mps"]), r["variant"])].append(r)

NAMES = {"lqarp": "LQARP", "elqtp": "E-LQTP (no beacon)", "elqtp-energy": "E-LQTP+energy (18-bit)",
         "elqtp-energy-trigoff": "E-LQTP+energy, trigger OFF", "periodic": "Fixed-Periodic (T=5 s)",
         "rlor": "RLOR-inspired"}
MSKEY = {"elqtp": "elqtp", "lqarp": "lqarp", "periodic": "periodic", "rlor": "rlor"}  # manuscript rows
ORDER = ["lqarp", "elqtp", "elqtp-energy", "elqtp-energy-trigoff", "periodic", "rlor"]
MET = [("pdr", "PDR", "PDR"), ("hops", "Hops", "mean_hops"), ("te2e", "T_e2e (s)", "T_e2e_s"),
       ("ebit", "E_bit (J/bit)", "E_bit_J_per_bit"), ("octrl", "O_ctrl", "O_ctrl_byte_per_s")]


def ms(rs, c):
    return sc.mean_sd([float(r[c]) for r in rs])


def proto_table(title, ref, case):
    L = [f"### {title}", "", "| Protocol | " + " | ".join(m[1] for m in MET) + " | O_ene | **O_total** |",
         "|---|" + "---|" * (len(MET) + 2)]
    nflag = 0
    for v in ORDER:
        rs = g.get(case + (v,))
        if not rs:
            continue
        cells = []
        for kind, _, col in MET:
            mu, sd = ms(rs, col)
            cell = ref.get(MSKEY[v], {}).get(kind) if v in MSKEY else None
            if cell is not None:
                nflag += sc.flagged(mu, cell, kind)
            cells.append(sc.cell_text(mu, sd, cell, kind))
        oe, ot = ms(rs, "O_ene_byte_per_s"), ms(rs, "O_total_byte_per_s")
        L.append(f"| {NAMES[v]} | " + " | ".join(cells) + f" | {oe[0]:.2f} | **{ot[0]:.1f} ± {ot[1]:.1f}** |")
    L += ["", f"Flagged cells: {nflag}. Rows without `(ms …)` have no manuscript counterpart.", ""]
    return L, nflag


out = ["# Final campaign — Tables II–V (dataset of record)", "",
       "Scenario III carries the Step 7 live-envelope guard; Scenarios I and II are bit-identical to Step 6.", "",
       "Code: received-only z_k (Step 2), r_range = 2500 m (Step 3), quantizer fix and reception-gated "
       "HELLO/beacon writes (Step 5), 18-bit energy beacon (Step 6). Seeds 20260921–25, N=40, "
       "boundary=remove, β1=β2=0. Mean ± sample s.d. over five seeds. `(ms …)` is the published value; "
       "**FLAG** = outside published mean ± s.d. (rule from step1_compare.py). O_total = O_ctrl + O_ene "
       "(byte/s) is the headline overhead.", ""]
total = 0
for title, ref, case in (("Table II — Scenario I (static)", sc.S1, ("i", 0.0)),
                         ("Table III — Scenario II, 2 m/s", sc.S2_PROTO, ("ii", 2.0))):
    L, n = proto_table(title, ref, case); out += L; total += n
out += ["### Table IV — Scenario II drift sweep", "",
        "| v (m/s) | Protocol | PDR | T_e2e (s) | Hops | O_ctrl | O_ene | **O_total** |", "|---:|---|---|---|---|---|---|---|"]
n4 = 0
for v in sc.sorted(set()) if False else sorted({k[1] for k in g if k[0] == "ii"}):
    for p in ORDER:
        rs = g.get(("ii", v, p))
        if not rs:
            continue
        ref = sc.S2_DRIFT.get((v, p))
        cells = []
        for kind, col in (("pdr", "PDR"), ("te2e", "T_e2e_s"), ("hops", "mean_hops"), ("octrl", "O_ctrl_byte_per_s")):
            mu, sd = ms(rs, col); cell = ref[kind] if ref else None
            if cell is not None:
                n4 += sc.flagged(mu, cell, kind)
            cells.append(sc.cell_text(mu, sd, cell, kind))
        oe, ot = ms(rs, "O_ene_byte_per_s"), ms(rs, "O_total_byte_per_s")
        out.append(f"| {v:.1f} | {NAMES[p]} | " + " | ".join(cells) + f" | {oe[0]:.2f} | **{ot[0]:.1f}** |")
out += ["", f"Flagged cells: {n4}.", ""]; total += n4
L, n = proto_table("Table V — Scenario III (eddy, V = 2 m/s)", sc.S3, ("iii", 2.0)); out += L; total += n
out += [f"**Total flagged cells vs manuscript Tables II–V: {total}.**", ""]
(F / "TABLES_II_V.md").write_text("\n".join(out) + "\n")

# ---- T_ctrl sweep table
S = ["# Final campaign — Fixed-Periodic T_ctrl sweep vs E-LQTP+energy (O_total headline)", "",
     "| Case | Variant | PDR | Hops | T_e2e (s) | O_ctrl | O_ene | **O_total** |", "|---|---|---:|---:|---:|---:|---:|---:|"]
cases = sorted({k[:2] for k in g}, key=lambda c: (c[0], c[1]))
for case in cases:
    for v in ["elqtp-energy", "elqtp-energy-trigoff"] + [f"periodic-T{t}" for t in (5, 10, 20, 40, 60)]:
        rs = g.get(case + (v,))
        if not rs:
            continue
        nm = NAMES.get(v, v.replace("periodic-T", "Fixed-Periodic T=") + " s")
        f = lambda c, d=4: f"{ms(rs, c)[0]:.{d}f} ± {ms(rs, c)[1]:.{d}f}"
        S.append(f"| {case[0].upper()} {case[1]:.1f} | {nm} | {f('PDR')} | {f('mean_hops', 2)} | {ms(rs,'T_e2e_s')[0]:.2f} | "
                 f"{ms(rs,'O_ctrl_byte_per_s')[0]:.1f} | {ms(rs,'O_ene_byte_per_s')[0]:.2f} | **{ms(rs,'O_total_byte_per_s')[0]:.1f}** |")
mob = [c for c in cases if c[0] != "i"]
eo = [ms(g[c + ("elqtp-energy",)], "O_total_byte_per_s")[0] for c in mob]
pp = [ms(g[c + (f"periodic-T{t}",)], "PDR")[0] for c in mob for t in (40, 60)]
ep = [ms(g[c + ("elqtp-energy",)], "PDR")[0] for c in mob]
share = [1 - ms(g[c + ("elqtp-energy-trigoff",)], "O_total_byte_per_s")[0] / ms(g[c + ("elqtp-energy",)], "O_total_byte_per_s")[0] for c in mob]
S += ["", f"- E-LQTP+energy O_total over Scenarios II/III: {min(eo):.1f}–{max(eo):.1f} B/s; PDR {min(ep):.4f}–{max(ep):.4f}.",
      f"- Fixed-Periodic at T = 40–60 s: O_total 37.6–54.7 B/s; PDR {min(pp):.4f}–{max(pp):.4f}.",
      f"- Periodic break-even T_ctrl (O_P(T) ≈ 2000/T + 3.33 B/s): {2000/(max(eo)-10/3):.1f}–{2000/(min(eo)-10/3):.1f} s.",
      "- Trigger share of E-LQTP+energy O_total (1 − O_total(trigger off)/O_total): " +
      ", ".join(f"{c[0].upper()} {c[1]:.1f}: {s:.0%}" for c, s in zip(mob, share)) + "."]
(F / "TCTRL_SWEEP.md").write_text("\n".join(S) + "\n")

# ---- decision trace summary
def parse(path):
    for line in open(path):
        if not line.startswith("DEC "):
            continue
        head, *cands = line.rstrip().split(" |")
        kv = dict(re.findall(r"(\w+)=(\S+)", head))
        C = {}
        for c in cands:
            j, vals = c.split(":")
            q, R, ce, cd, cn = map(float, vals.split(","))
            C[int(j)] = dict(q=q, R=R, ce=ce, cd=cd, cn=cn)
        yield int(kv["nh"]), C

D = ["# Final campaign — decision-trace summary (c_nei dominance)", "",
     (F / "decision_trace" / "NONPERTURBATION.txt").read_text().strip().replace("\n", "; ") + ".", "",
     "Every primary forwarding decision in every trace run (all scenarios/speeds, five seeds). "
     "'Passed over' = sink was a legal candidate but a relay with higher Q was chosen.", "",
     "| Scope | Variant | decisions | sink in set | sink chosen | passed over | relay > sink on c_nei | on c_ene | on c_del | median c_nei ratio | median c_ene ratio | NaN/Inf Q |",
     "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
def summarize(files):
    n = si = ch = po = wn = we = wd = bad = 0; rn = []; re_ = []
    for f in files:
        for nh, C in parse(f):
            n += 1
            bad += sum(1 for v in C.values() if not math.isfinite(v["q"]))
            if 0 not in C:
                continue
            si += 1
            if nh == 0:
                ch += 1; continue
            if nh not in C:
                continue
            po += 1; s, r = C[0], C[nh]
            wn += r["cn"] > s["cn"]; we += r["ce"] > s["ce"]; wd += r["cd"] > s["cd"]
            if s["cn"] > 0: rn.append(r["cn"] / s["cn"])
            if s["ce"] > 0 and r["ce"] > 0: re_.append(r["ce"] / s["ce"])
    p = lambda a, b: f"{a/b:.1%}" if b else "—"
    med = lambda x: f"{st.median(x):.3g}" if x else "—"
    return f"{n} | {si} | {p(ch,si)} | {po} ({p(po,si)}) | {p(wn,po)} | {p(we,po)} | {p(wd,po)} | {med(rn)} | {med(re_)} | {bad}"
T = F / "decision_trace" / "runs"
for scope, pat in (("all cases", "s*"), ("II 2.0 m/s", "sii_*_d2.0_"), ("III", "siii_*"), ("I", "si_*")):
    for v in ORDER:
        files = [f for f in glob.glob(str(T / f"{pat}*.txt")) if re.search(rf"_{re.escape(v)}_d", f)]
        if files:
            D.append(f"| {scope} | {NAMES[v]} | " + summarize(files) + " |")
(F / "DECISION_TRACE.md").write_text("\n".join(D) + "\n")
print(f"flags total={total}")
