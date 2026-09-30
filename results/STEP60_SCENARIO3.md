# Step 60: Scenario III four-protocol × five-seed comparison

Steps 58–59 confirmed the design is sound (\(\sigma_z=0\) permanent;
full-GM \(\|v_{\mathrm{rad}}\|\) mean 1.06 m/s vs \(\|v_{\mathrm{tan}}\|\)
2.54 m/s). This is the first full-network Scenario III run.

Same structure as Scenario II Step 53: 4 protocols, seeds
20260921–20260925, \(N=40\), \(T_{\mathrm{sim}}=600\) s, January grid,
`--boundary=remove`, 30 s/packet/node. E-LQTP and Fixed-Periodic use
\(\beta_1=\beta_2=1\), \(\varepsilon_0=2.0\), \(s_{\mathrm{cap}}=2.0\),
\(T_{\mathrm{ctrl}}=5\) s. Mobility is the documented Rankine eddy
plus horizontal Gauss-Markov (\(V_{\mathrm{eddy}}=2.0\) m/s,
\(R_{\mathrm{core}}=2000\) m, \(\zeta=0.95\), \(\sigma=(1,1,0)\)),
not Scenario II’s uniform drift.

CSV: `results/scenario3_multiseed_data.csv` (20 rows).
Runner: `scripts/scenario3_compare.py`.
Kinematics gate: `results/STEP58_59.md`.

Sample std is the unbiased 5-seed estimator (\(n-1\)).

All 20 runs: `metrics_finite=1`, VOID=0.

---

## Step 60 — four protocols, \(V_{\mathrm{eddy}}=2.0\) m/s

Mean ± std [min, max] over 5 seeds.

| protocol | PDR | \(T_{\mathrm{e2e}}\) (s) | \(E_{\mathrm{bit}}\) (J/bit) | \(O_{\mathrm{ctrl}}\) (byte/s) | hops | VOID | LOST | rising |
|---|---|---|---|---|---|---|---|---|
| LQARP | 0.9989 ± 0.0018 [0.9958, 1.0000] | 4.146 ± 0.348 [3.781, 4.635] | 1.099e-2 ± 9.79e-4 | 0 | 2.046 ± 0.187 | 0 | 0.80 ± 1.30 [0, 3] | — |
| E-LQTP | 0.9986 ± 0.0014 [0.9972, 1.0000] | 6.961 ± 0.285 [6.670, 7.425] | 1.746e-2 ± 7.77e-4 | **211.25 ± 34.51 [162.58, 246.08]** | 3.250 ± 0.141 | 0 | 1.00 ± 1.00 [0, 2] | 2724 ± 463 |
| RLOR-inspired | 1.0000 ± 0 | 1.814 ± 0.093 [1.737, 1.940] | 5.361e-3 ± 0 | 0 | 1.000 ± 0 | 0 | 0 | — |
| Fixed-Periodic | 0.9989 ± 0.0011 [0.9974, 1.0000] | 6.586 ± 0.697 [5.357, 7.048] | 1.661e-2 ± 2.02e-3 | **413.42 ± 0** | 3.094 ± 0.375 | 0 | 0.80 ± 0.84 [0, 2] | 196800 |

Envelope exits (runtime, same for every protocol on a seed):
**6.40 ± 1.14 [5, 8]** of 40. Seed 20260921 max pairwise AUV–AUV
distance change is 1110 m (Scenario II this is ~0).

### E-LQTP first-fire rate

Live AUV–AUV pairs that fire at least once by \(T_{\mathrm{sim}}\):

| seed | heard / live | first-fire | exits |
|---:|---:|---:|---:|
| 20260921 | 798 / 1056 | 0.756 | 7 |
| 20260922 | 731 / 992 | 0.737 | 8 |
| 20260923 | 834 / 1122 | 0.743 | 6 |
| 20260924 | 822 / 1190 | 0.691 | 5 |
| 20260925 | 728 / 1190 | 0.612 | 6 |

**0.708 ± 0.059 [0.612, 0.756].** The trigger is firing. Scenario II
at \(v=2\) was 0.782 ± 0.042.

---

## Does E-LQTP’s routing cost shrink or reverse vs Scenario II?

It does **neither**. It **grows**.

E-LQTP relative to LQARP, same 5 seeds, same \(N\), \(T_{\mathrm{sim}}\),
\(\beta\), \(\varepsilon_0\):

| metric | Scenario II (uniform drift) | Scenario III (eddy + GM) |
|---|---|---|
| hops E / hops L | 2.498 / 2.153 = **1.16×** (+0.345) | 3.250 / 2.046 = **1.59×** (+1.204) |
| \(T_{\mathrm{e2e}}\) E / L | 5.263 / 4.438 = **1.19×** (+0.825 s) | 6.961 / 4.146 = **1.68×** (+2.815 s) |
| \(E_{\mathrm{bit}}\) E / L | 1.347e-2 / 1.156e-2 = **1.17×** | 1.746e-2 / 1.099e-2 = **1.59×** |
| \(O_{\mathrm{ctrl}}\) E vs periodic | 135 / 413 = 0.33× | 211 / 413 = 0.51× |
| first-fire | 0.782 ± 0.042 | 0.708 ± 0.059 |

This is the first scenario in which \(c_{\mathrm{drift}}\) has a
genuine per-pair AUV–AUV \(v_{\mathrm{rel}}\) (Step 57/59). The
trigger uses it: rising 2724 ± 463 vs Scenario II’s 1699 ± 300,
\(O_{\mathrm{ctrl}}\) 211 vs 135, still well under the analytic
periodic 413.42 byte/s. Seed 20260921 pairwise range change is
a kilometre, not a millimetre.

What that signal does to the *data plane* is the opposite of a
routing advantage. LQARP hops fall slightly (2.15 → 2.05) because
the eddy retains more nodes than a uniform 2 m/s translation
(6.4 exits vs Scenario II’s 4–13). E-LQTP hops rise (2.50 → 3.25)
and sit next to Fixed-Periodic-with-\(\beta=1\) (3.09). The hop
inflation is the \(\beta=1\) reward (\(c_{\mathrm{pred}}\) /
\(c_{\mathrm{drift}}\)) acting on real relative motion, not a
HELLO-timing artefact.

PDR still does not separate the four (all ≥ 0.995). RLOR remains
the one-hop sink greedy (BER-floor + id-0 tie, Step 56); hops = 1
on every seed.

**Honest sentence:** Scenario III is the first kinematics that
could have shown E-LQTP beating LQARP on hops / delay / energy.
It does not. The cost widens. The remaining E-LQTP claim vs
Periodic is still control overhead (0.51×), not a shorter path.

---

## Checkpoint

- \(\sigma_z=0\) is permanent and documented (Step 58).
- Full-GM radial range-rate is \(O(1)\) m/s (Step 59). Green light
  was correct: the trigger had something to see, and it fired.
- Seeing it did not produce a routing-level win over LQARP.
- Unit suite unchanged: PASS=39 FAIL=0.
