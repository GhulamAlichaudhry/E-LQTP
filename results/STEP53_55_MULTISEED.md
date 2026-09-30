# Steps 53–55: Scenario II multi-seed coverage

No Scenario III. Unit suite unchanged (31/31). Sixty runs:
4 protocols × 5 seeds at \(\|\mathbf{v}_{\mathrm{drift}}\|=2.0\) m/s,
then LQARP vs E-LQTP at 0.5 / 1.0 / 3.0 / 3.5 m/s on the same seeds.

January grid, N=40, \(T_{\mathrm{sim}}=600\) s, `--boundary=remove`,
30 s/packet/node. E-LQTP and Fixed-Periodic use the validated
defaults \(\beta_1=\beta_2=1\), \(\varepsilon_0=2.0\), \(s_{\mathrm{cap}}=2.0\),
\(T_{\mathrm{ctrl}}=5\) s. Periodic now shares those \(\beta\) values so
the ablation isolates HELLO timing, not the reward weights.

CSV: `results/scenario2_multiseed_data.csv` (60 rows).
Figures: `results/figs/scenario2_figA_protocol.{pdf,eps,png}`,
`results/figs/scenario2_figB_drift.{pdf,eps,png}`.
Runner: `scripts/scenario2_sweep.py`.

Sample std is the unbiased 5-seed estimator (\(n-1\)).

---

## Seeds and azimuths (stream 2)

Placement uses stream 1 (same as Scenario I / Step 22). Azimuth is
an independent Uniform\([0,2\pi)\) on stream 2, so the five
topologies stay bit-identical to Step 22/26 and the current is
reproducible per seed.

| seed | azimuth (rad) | azimuth (deg) | exits at \(v=2\) by \(T_{\mathrm{sim}}\) |
|---:|---:|---:|---:|
| 20260921 | 5.9681552082 | 341.95 | 13/40 |
| 20260922 | 4.0355876288 | 231.22 | 11/40 |
| 20260923 | 2.1030200494 | 120.49 | 12/40 |
| 20260924 | 0.1704193437 | 9.76 | 7/40 |
| 20260925 | 4.5210370700 | 259.04 | 4/40 |

Seed 20260921 matches Steps 49/52 (PDR 0.9955, \(O_{\mathrm{ctrl}}=162.83\),
first-fire 548/702).

---

## Step 53 — four protocols, \(v=2.0\) m/s

Mean ± std [min, max] over 5 seeds.

| protocol | PDR | \(T_{\mathrm{e2e}}\) (s) | \(E_{\mathrm{bit}}\) (J/bit) | \(O_{\mathrm{ctrl}}\) (byte/s) | hops | VOID | LOST | rising |
|---|---|---|---|---|---|---|---|---|
| LQARP | 0.9992 ± 0.0019 [0.9958, 1.0000] | 4.438 ± 0.277 [4.127, 4.880] | 1.156e-2 ± 1.000e-3 | 0 | 2.153 ± 0.187 | 0 | 0.60 ± 1.34 [0, 3] | — |
| E-LQTP | 0.9968 ± 0.0024 [0.9944, 1.0000] | 5.263 ± 0.623 [4.719, 6.176] | 1.347e-2 ± 1.664e-3 | **135.10 ± 22.99 [113.17, 162.83]** | 2.498 ± 0.323 | 0 | 2.20 ± 1.64 [0, 4] | 1699 ± 300 |
| RLOR-inspired | 1.0000 ± 0 | 1.845 ± 0.074 [1.744, 1.926] | 5.362e-3 ± 3e-6 | 0 | 1.000 ± 0.001 | 0 | 0 | — |
| Fixed-Periodic | 0.9974 ± 0.0031 [0.9927, 1.0000] | 4.999 ± 0.638 [4.208, 5.795] | 1.306e-2 ± 1.819e-3 | **413.42 ± 0** | 2.421 ± 0.361 | 0 | 1.80 ± 2.17 [0, 5] | 196800 |

All 20 runs: `metrics_finite=1`, VOID=0.

**\(O_{\mathrm{ctrl}}\) holds up statistically.** E-LQTP is
135 ± 23 byte/s against a flat periodic 413.42 (41 × 121 × 50 / 600)
on every seed — 0.33× periodic, never above 163. LQARP / RLOR stay 0.

PDR does not separate the four (all ≥ 0.993). The cost of E-LQTP vs
LQARP is hops / delay / energy (same direction as the single-seed
story) plus a few more LOST_NODE_EXIT packets at envelope exits.
RLOR is still the one-hop sink greedy (\(T_{\mathrm{e2e}}\approx 1.85\) s,
hops = 1). Periodic with \(\beta=1\) now tracks E-LQTP’s data plane
and is no longer the identity-β Scenario I ablation.

Fixed-Periodic “rising” is pair-level \(Broadcast_k\) sets on the
\(T_{\mathrm{ctrl}}\) grid (41 × 40 × 120 = 196800), not an event
count. Compare protocols on \(O_{\mathrm{ctrl}}\), not that column.

### E-LQTP first-fire rate at \(v=2.0\)

Live AUV–AUV pairs that fire at least once by \(T_{\mathrm{sim}}\):

| seed | heard / live | first-fire |
|---:|---:|---:|
| 20260921 | 548 / 702 | **0.781** |
| 20260922 | 687 / 812 | 0.846 |
| 20260923 | 583 / 756 | 0.771 |
| 20260924 | 769 / 1056 | 0.728 |
| 20260925 | 989 / 1260 | 0.785 |

**0.782 ± 0.042 [0.728, 0.846].** The Step 49/52 ~78% is the
five-seed mean. Topology moves it by about ±5–6 points (more live
pairs when fewer nodes exit). It does not collapse on any seed.

---

## Step 54 — drift magnitude, LQARP vs E-LQTP

Same 5 seeds. Displacement \(= \|\mathbf{v}\|\,T_{\mathrm{sim}}\).

| \(v\) (m/s) | protocol | PDR | \(T_{\mathrm{e2e}}\) (s) | \(E_{\mathrm{bit}}\) | \(O_{\mathrm{ctrl}}\) | hops | first-fire | LOST | exits / 40 |
|---|---|---|---|---|---|---|---|---|---|
| 0.5 | LQARP | 1.000 ± 0 | 4.776 ± 0.403 | 1.223e-2 | 0 | 2.282 ± 0.186 | — | 0 | 1.8 ± 1.6 |
| 0.5 | E-LQTP | 1.000 ± 0 | 5.286 ± 0.455 | 1.341e-2 | **20.2 ± 4.2** | 2.502 ± 0.264 | 0.146 ± 0.021 | 0 | 1.8 ± 1.6 |
| 1.0 | LQARP | 0.9995 ± 0.0012 | 4.752 ± 0.377 | 1.228e-2 | 0 | 2.289 ± 0.208 | — | 0.40 ± 0.89 | 4.4 ± 2.7 |
| 1.0 | E-LQTP | 0.9986 ± 0.0024 | 5.506 ± 0.338 | 1.396e-2 | **70.9 ± 6.4** | 2.600 ± 0.196 | 0.520 ± 0.031 | 1.00 ± 1.73 | 4.4 ± 2.7 |
| 2.0 | LQARP | 0.9992 ± 0.0019 | 4.438 ± 0.277 | 1.156e-2 | 0 | 2.153 ± 0.187 | — | 0.60 ± 1.34 | 9.4 ± 3.8 |
| 2.0 | E-LQTP | 0.9968 ± 0.0024 | 5.263 ± 0.623 | 1.347e-2 | **135.1 ± 23.0** | 2.498 ± 0.323 | 0.782 ± 0.042 | 2.20 ± 1.64 | 9.4 ± 3.8 |
| 3.0 | LQARP | 1.000 ± 0 | 4.431 ± 0.333 | 1.155e-2 | 0 | 2.154 ± 0.203 | — | 0 | 14.4 ± 4.8 |
| 3.0 | E-LQTP | 0.9973 ± 0.0027 | 5.140 ± 0.419 | 1.312e-2 | **211.4 ± 36.1** | 2.445 ± 0.229 | 0.857 ± 0.034 | 1.80 ± 1.92 | 14.4 ± 4.8 |
| 3.5 | LQARP | 1.000 ± 0 | 4.200 ± 0.393 | 1.106e-2 | 0 | 2.063 ± 0.215 | — | 0 | 16.0 ± 5.4 |
| 3.5 | E-LQTP | 0.9991 ± 0.0014 | 5.203 ± 0.392 | 1.331e-2 | **256.4 ± 46.0** | 2.478 ± 0.224 | 0.897 ± 0.028 | 0.60 ± 0.89 | 16.0 ± 5.4 |

VOID = 0 on every run. All metrics finite.

E-LQTP \(O_{\mathrm{ctrl}}\) / periodic 413.4: **0.05, 0.17, 0.33,
0.51, 0.62** at 0.5 / 1 / 2 / 3 / 3.5 m/s. Still under periodic at
the top of Section 4.1’s range. The overhead *advantage shrinks as
drift grows* (more AUV–sink geometry plus more exits) but does not
disappear.

First-fire is **not** a constant 78%. It is a function of
\(\|\mathbf{v}_{\mathrm{rel}}\|\) to the sink (and of how many pairs
remain live): 15% at 0.5 m/s → 52% at 1.0 → 78% at 2.0 → 86% at 3.0
→ 90% at 3.5. The 78% contour was calibrated on the \(v=2\)
ZOH-init class; slower drift simply accumulates less
\(|e_k^{\mathrm{trigger}}|\) in 600 s.

PDR / hops / \(E_{\mathrm{bit}}\) stay flat-ish in \(v\). The
visible mobility signature is \(O_{\mathrm{ctrl}}\) and first-fire.

### Attrition vs \(\|\mathbf{v}_{\mathrm{drift}}\|\)

Exits by \(T_{\mathrm{sim}}\) (predicted XY leave of \([0,6000]^2\);
same geometry for both protocols):

| \(v\) (m/s) | displacement (m) | mean exits | fraction | [min, max] | counts |
|---:|---:|---:|---:|---|---|
| 0.5 | 300 | 1.8 | 0.045 ± 0.041 | [0.00, 0.10] | 3, 1, 4, 1, 0 |
| 1.0 | 600 | 4.4 | 0.110 ± 0.068 | [0.03, 0.20] | 8, 4, 6, 3, 1 |
| 2.0 | 1200 | 9.4 | 0.235 ± 0.095 | [0.10, 0.33] | 13, 11, 12, 7, 4 |
| 3.0 | 1800 | 14.4 | 0.360 ± 0.121 | [0.18, 0.45] | 18, 17, 18, 12, 7 |
| 3.5 | 2100 | 16.0 | 0.400 ± 0.135 | [0.18, 0.50] | 20, 19, 19, 15, 7 |

Fraction / \(v\) is 0.09–0.12 per (m/s): **roughly linear in
displacement**, as expected for a uniform field sliding out of a
fixed square. Azimuth sets the intercept (seed 20260925 at 259°
exits only 7/40 even at 3.5 m/s).

**FLAG at 3.5 m/s:** mean attrition is **40%**. One seed
(20260921) hits **exactly 50%** (20/40). No seed exceeds 50%.
\(T_{\mathrm{sim}}=600\) s is still usable at the high end of the
Section 4.1 range. Shrinking \(T_{\mathrm{sim}}\) only for 3.5 m/s
would break the magnitude comparison, so it was left at 600 s.
If a later run parks at 3.5 m/s for a long window (or adds
Gauss–Markov wander on top), revisit the envelope.

---

## Step 55 — CSV schema and figures

`results/scenario2_multiseed_data.csv`: one row per
protocol × seed × magnitude.

| column | meaning |
|---|---|
| protocol | `lqarp` / `elqtp` / `rlor` / `periodic` |
| seed | 20260921–20260925 |
| N | AUVs (40) |
| drift_mps | \(\|\mathbf{v}_{\mathrm{drift}}\|\) |
| azimuth_rad | stream-2 heading |
| T_sim_s | 600 |
| PDR, T_e2e_s, E_bit_J_per_bit, O_ctrl_byte_per_s, mean_hops | paper metrics |
| VOID, LOST_NODE_EXIT | failure counts |
| Broadcast_k_rising, Broadcast_k_ones, ctrl_tx | \(T_{\mathrm{sim}}\)-window |
| heard_live, live_pairs, first_fire_rate | live AUV–AUV first-fire |
| n_exit_tsim, n_envelope, attrition_tsim | exits by \(T_{\mathrm{sim}}\) / drain / fraction |
| n_gen, n_succ, n_tx | traffic |
| metrics_finite | 1 on every row |

Style map (keep for Scenario III later):

| protocol | color | marker | linestyle | hatch |
|---|---|---|---|---|
| LQARP | `#0072B2` | circle | solid | none |
| E-LQTP | `#D55E00` | square | dashed | `//` |
| RLOR-inspired | `#009E73` | triangle | dotted | `..` |
| Fixed-Periodic | `#000000` | diamond | dash-dot | `xx` |

**Fig. A.** Protocol comparison under linear uniform current drift
(\(\|\mathbf{v}_{\mathrm{drift}}\|=2.0\) m/s, \(N=40\),
\(T_{\mathrm{sim}}=600\) s, mean ± std over 5 seeds). Four panels:
packet delivery ratio, average end-to-end delay (s), energy per bit
(J/bit), control overhead (bytes/s). Bars are 5-seed means; error
bars are sample standard deviation. Protocols are distinguished by
color and hatch for grayscale / B&W.

**Fig. B.** LQARP vs E-LQTP as a function of drift speed
(\(N=40\), \(T_{\mathrm{sim}}=600\) s, mean ± std over the same 5
seeds). Same four metrics. Markers and linestyles match Fig. A.
E-LQTP control overhead rises with \(\|\mathbf{v}_{\mathrm{drift}}\|\)
and stays below the Fixed-Periodic 413 byte/s baseline at every
point in Section 4.1’s range.

Vector files are PDF and EPS (IEEE submission); PNG is a draft
preview. Axis text is Liberation Serif 8–9 pt on a 7.16 in
full-width canvas.

---

## Checkpoint

- 5-seed, 4-protocol table at \(v=2\) exists and is finite.
- E-LQTP \(O_{\mathrm{ctrl}}=135\pm 23 < 413\) on every seed.
- First-fire at \(v=2\) is 78.2% ± 4.2%, not a single-seed fluke.
- Drift sweep: overhead advantage shrinks with \(v\) but remains;
  first-fire *is* drift-dependent (15% → 90%).
- Attrition is ~linear in \(v\). At 3.5 m/s mean 40%, max 50% —
  flagged, \(T_{\mathrm{sim}}\) not shortened.
- CSV + IEEE Fig. A/B written.
- Scenario III not started.
