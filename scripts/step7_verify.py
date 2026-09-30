#!/usr/bin/env python3
"""Step 7 verification: non-finite Q before/after, Scenario I/II identity,
Scenario III before/after deltas. Compares results/final_campaign (Step 6)
with results/step7_envelope_fix (Step 7)."""
import csv, glob, math, re, statistics as st, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S6, S7 = ROOT / "results/final_campaign", ROOT / "results/step7_envelope_fix"
PARTS = ("campaign", "tctrl_sweep", "trigger_off", "decision_trace")
VARS = ["lqarp", "elqtp", "elqtp-energy", "elqtp-energy-trigoff", "periodic", "rlor"]


def rows(base, part):
    return list(csv.DictReader(open(base / part / f"{part}.csv")))


def key(r):
    return (r["scenario"], r["drift_mps"], r["variant"], r["seed"], r.get("T_ctrl_s", ""))


# ---- 1. non-finite Q in decision traces, per scenario/variant
def nonfinite(base):
    out = defaultdict(lambda: [0, 0, 0])  # decisions, dec_with_inf, inf_chosen
    for f in glob.glob(str(base / "decision_trace/runs/*.txt")):
        m = re.match(r"s(i+)_(.+?)_d[\d.]+_\d+\.txt", Path(f).name)
        if not m:
            continue
        k = (m.group(1), m.group(2))
        for line in open(f):
            if not line.startswith("DEC "):
                continue
            head, *cands = line.rstrip().split(" |")
            nh = int(re.search(r"nh=(-?\d+)", head).group(1))
            C = {}
            for c in cands:
                j, vals = c.split(":")
                C[int(j)] = float(vals.split(",")[0])
            out[k][0] += 1
            bad = [j for j, q in C.items() if not math.isfinite(q)]
            if bad:
                out[k][1] += 1
                out[k][2] += nh in bad
    return out


print("=" * 100)
print("1. NON-FINITE Q IN DECISION TRACES  (decisions with a non-finite-Q candidate / of those, chosen)")
print("=" * 100)
b6, b7 = nonfinite(S6), nonfinite(S7)
total7 = 0
print(f"{'sc':4}{'variant':26}{'decisions (S6->S7)':>24}{'Step 6 inf':>14}{'Step 7 inf':>14}{'S7 inf chosen':>15}")
for k in sorted(set(b6) | set(b7)):
    d6, d7 = b6.get(k, [0, 0, 0]), b7.get(k, [0, 0, 0])
    total7 += d7[1]
    if d6[1] or d7[1]:
        print(f"{k[0]:4}{k[1]:26}{str(d6[0]) + ' -> ' + str(d7[0]):>24}{d6[1]:>14}{d7[1]:>14}{d7[2]:>15}")
print(f"\nStep 6 total decisions with a non-finite-Q candidate: {sum(v[1] for v in b6.values())}")
print(f"Step 7 total decisions with a non-finite-Q candidate: {total7}")
print(f"Step 7 across ALL scenarios and variants: {'ZERO non-finite Q' if total7 == 0 else 'STILL NON-ZERO'}")

# ---- 2. Scenario I/II identity, Scenario III changed
print()
print("=" * 100)
print("2. SCENARIO I / II UNTOUCHED, SCENARIO III CHANGED  (per-row, all numeric fields)")
print("=" * 100)
NUM = ["PDR", "mean_hops", "T_e2e_s", "E_bit_J_per_bit", "O_ctrl_byte_per_s",
       "O_ene_byte_per_s", "O_total_byte_per_s", "n_gen", "n_succ", "event_hellos", "VOID"]
for part in PARTS:
    a = {key(r): r for r in rows(S6, part)}
    b = {key(r): r for r in rows(S7, part)}
    assert set(a) == set(b), f"{part}: row sets differ"
    stat = defaultdict(lambda: [0, 0])
    for k in a:
        sc = k[0]
        same = all(a[k][c] == b[k][c] for c in NUM)
        stat[sc][0] += 1
        stat[sc][1] += 0 if same else 1
    for sc in sorted(stat):
        n, diff = stat[sc]
        verdict = "IDENTICAL" if diff == 0 else f"{diff}/{n} rows changed"
        print(f"  {part:16} scenario {sc:4} rows={n:4}  {verdict}")

# ---- 3. Scenario III headline, before vs after
print()
print("=" * 100)
print("3. SCENARIO III HEADLINE, STEP 6 -> STEP 7")
print("=" * 100)


def g(base):
    d = defaultdict(list)
    for part in ("campaign", "trigger_off"):
        for r in rows(base, part):
            if r["scenario"] == "iii":
                d[r["variant"]].append(r)
    for r in rows(base, "tctrl_sweep"):
        if r["scenario"] == "iii":
            d[r["variant"]].append(r)
    return d


g6, g7 = g(S6), g(S7)
m = lambda rs, c: st.mean(float(r[c]) for r in rs)
sd = lambda rs, c: st.stdev(float(r[c]) for r in rs)
print(f"{'variant':28}{'PDR':>22}{'hops':>20}{'T_e2e':>18}{'O_ctrl':>16}{'O_ene':>8}{'O_total':>16}")
for v in VARS + [f"periodic-T{t}" for t in (5, 10, 20, 40, 60)]:
    if v not in g7:
        continue
    r6, r7 = g6.get(v), g7[v]
    def pair(c, d=4):
        if not r6:
            return f"{m(r7,c):.{d}f}"
        return f"{m(r6,c):.{d}f}->{m(r7,c):.{d}f}"
    print(f"{v:28}{pair('PDR'):>22}{pair('mean_hops',2):>20}{pair('T_e2e_s',2):>18}"
          f"{pair('O_ctrl_byte_per_s',1):>16}{m(r7,'O_ene_byte_per_s'):>8.2f}{pair('O_total_byte_per_s',1):>16}")
print()
print("Scenario III, Step 7 values with dispersion (five seeds, mean +/- sample s.d.):")
for v in VARS:
    rs = g7[v]
    print(f"  {v:26} PDR {m(rs,'PDR'):.4f} +/- {sd(rs,'PDR'):.4f} | hops {m(rs,'mean_hops'):.2f} +/- {sd(rs,'mean_hops'):.2f} | "
          f"T_e2e {m(rs,'T_e2e_s'):.2f} | O_ctrl {m(rs,'O_ctrl_byte_per_s'):.1f} | O_ene {m(rs,'O_ene_byte_per_s'):.2f} | "
          f"O_total {m(rs,'O_total_byte_per_s'):.1f}")

# ---- 4. verdict checks for Scenario III on the corrected data
print()
print("=" * 100)
print("4. SCENARIO III VERDICT CHECKS ON CORRECTED DATA")
print("=" * 100)
en, off = g7["elqtp-energy"], g7["elqtp-energy-trigoff"]
print(f"  trigger on  vs off : PDR {m(en,'PDR'):.4f} vs {m(off,'PDR'):.4f} (s.d. {sd(en,'PDR'):.4f} / {sd(off,'PDR'):.4f})"
      f" | hops {m(en,'mean_hops'):.2f} vs {m(off,'mean_hops'):.2f} | T_e2e {m(en,'T_e2e_s'):.2f} vs {m(off,'T_e2e_s'):.2f}")
print(f"  trigger share of O_total: {1 - m(off,'O_total_byte_per_s')/m(en,'O_total_byte_per_s'):.0%}"
      f"  ({m(en,'O_total_byte_per_s'):.1f} -> {m(off,'O_total_byte_per_s'):.1f} B/s)")
for t in (5, 10, 20, 40, 60):
    p = g7[f"periodic-T{t}"]
    print(f"  Fixed-Periodic T={t:2}s : PDR {m(p,'PDR'):.4f} +/- {sd(p,'PDR'):.4f} | hops {m(p,'mean_hops'):.2f} | O_total {m(p,'O_total_byte_per_s'):.1f} B/s")
eo = m(en, "O_total_byte_per_s")
print(f"  E-LQTP+energy O_total {eo:.1f} B/s; Periodic break-even T_ctrl = {2000/(eo-10/3):.1f} s"
      f"; cheaper than E-LQTP+energy at every T >= 20 s: "
      f"{all(m(g7[f'periodic-T{t}'],'O_total_byte_per_s') < eo for t in (20,40,60))}")
