# Step 6 — bit-width re-verification and the FINAL campaign (dataset of record)

Build and integrity: `PROVENANCE.md` (ns-3.41 `e503909`, Aqua-Sim-NG `0fbc166`, binary and
source hashes, `lqarp-unit-check` PASS=48 FAIL=0, `bellhop-data-loader-check` PASS=11 FAIL=0).
Code snapshot: `code_snapshot.tar.gz`. Manuscript files were not edited.

## Task 1a — which bit-widths were NaN-clean in the pre-Step-5 quantizer

`bitwidth/prepatch_quantizer_check.cc` compiles the **pre-patch** expression verbatim
(`levels = (1u << bits) - 1u`, with `bits` held in a `volatile int` so the shift happens at
runtime as in the simulator) and compares it against the fixed `ldexp` version over a dense
sweep: 1,000,001 energy values spanning [0, E_ini] plus the two out-of-range edges
(−1 J, E_ini+1 J), at every width 1–32, built at both `-O0` and `-O2`.

Result (`bitwidth/prepatch_check_all_1_32.txt`, `prepatch_check_step1g_widths.txt`):

| bits | levels (pre-patch) | non-finite outputs | max error vs input | step/2 | identical to fixed version |
|---:|---:|---:|---:|---:|---|
| 8 | 255 | 0 | 19.61 J | 19.61 J | yes |
| 12 | 4095 | 0 | 1.221 J | 1.221 J | yes |
| 16 | 65535 | 0 | 0.0763 J | 0.0763 J | yes |
| 17 | 131071 | 0 | 0.0381 J | 0.0381 J | yes |
| 18 | 262143 | 0 | 0.0191 J | 0.0191 J | yes |
| 32 | **0** | **1,000,003 (all)** | — | — | (both return NaN) |

**Every width 1–31 is NaN-clean, correct to within half a quantizer step, and bit-identical
to the fixed implementation. Only `bits = 32` is degenerate**, and there it is degenerate for
*every* input, not just some. So Step 1g's 8/12/16/17/18 rows were not corrupted by this bug;
only its 32-bit row (and 24-bit and 28-bit are fine too — I checked all widths, not just the
ones Step 1g swept). `-O0` and `-O2` agree everywhere except for printing NaN vs Inf for the
degenerate 32-bit step size, which is cosmetic.

## Task 1b — Step 1g's sweep re-run on the Step-5-fixed code

`scripts/bitwidth_sweep.py`, `elqtp-energy`, Scenario II and III at 2 m/s, five seeds,
`--hopDiag`, widths {8, 10, 12, 16, 17, 18, 19, 20, 24, 32} = 200 runs, all succeeded.
Run in **both** geometries, because Step 1g predates the Step 3 geometry change and the two
answer different questions. Full tables: `bitwidth/bitwidth_sweep.md`, raw
`bitwidth/bitwidth_sweep.csv`.

**Step 1g's geometry (r_range = R\* = 5125 m), hops vs width:**

| bits | 8 | 10 | 12 | 16 | 17 | 18 | 19 | 20 | 24 | 32 |
|---|---|---|---|---|---|---|---|---|---|---|
| Scenario II | 1.748 | 2.355 | 2.490 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Scenario III | 2.287 | 2.582 | 2.475 | 1.758 | 1.396 | 1.001 | 1.001 | 1.001 | 1.001 | 1.001 |

**Step 1g's non-monotone finding survives, and it was not a bug artifact.** 8 bits still gives
fewer hops than 10 or 12 bits in Scenario II (1.748 vs 2.355 / 2.490), reproducing the shape
Step 1g reported (it had 1.573 at 8 bits vs 2.454 at 12). Both widths are NaN-clean by Task 1a,
so the non-monotonicity is a real property of coarse energy quantization interacting with the
reward, not numerical corruption. The mechanism is visible in the per-decision counters
(`bitwidth/` runs): at 8 bits, 25.1% of sink selections come from a **Q-tie broken toward the
lowest id** (the sink is id 0), against 2.4–5.4% at every other width. Coarse quantization
collapses distinct neighbor energies onto the same code, `c_ene` ties, and the tie-break
happens to favor the sink. That accidental benefit disappears at 10–12 bits, where energies
separate enough to differ but `c_nei` then dominates, and it is replaced from 16–18 bits up by
genuinely near-1-hop routing. So the curve is non-monotone for a real reason, and the coarse-end
"good" result is an artifact of tie-breaking, not of good routing.

**The final geometry (r_range = 2500 m), hops vs width:**

| bits | 8 | 10 | 12 | 16 | 17 | 18 | 19 | 20 | 24 | 32 |
|---|---|---|---|---|---|---|---|---|---|---|
| Scenario II | 3.160 | 3.146 | 3.198 | 3.166 | 3.214 | 3.199 | 3.205 | 3.194 | 3.177 | 3.177 |
| Scenario III | 3.254 | 3.082 | 3.055 | 3.065 | 3.063 | 3.068 | 3.083 | 3.075 | 3.075 | 3.075 |

**Flat.** Every width from 8 to 32 bits lands within seed noise (± 0.09–0.41), and the
sink-pass-over rate is 49–53% at every width. In the multi-hop geometry the bit-width does not
matter at all: `c_nei` dominates the decision regardless of how finely energy is resolved.
The 1.000-hop results at the top of the R\* table were a single-hop-geometry effect, which
Step 3 already showed was not a routing result.

## Task 2 — final bit-width: **18 bits** (26-bit beacon with the 8-bit sender id)

Two candidate tolerances, stated before choosing:

1. **Relative to E_ini** (the tolerance suggested in the task): step < 0.1% of E_ini = 10 J
   requires 2^b − 1 > 1000, so **b ≥ 10**. This criterion is too loose to be meaningful here:
   the R\* sweep shows 10- and 12-bit quantization visibly perturbing routing, so E_ini is not
   the scale that matters.
2. **Relative to the smallest energy event the beacon must resolve.** The energy model gives
   air time 400 bit / 1000 bit·s⁻¹ = 0.4 s, E_tx = 2.104 J and **E_rx = 0.040 J**. A quantizer
   whose step exceeds E_rx cannot represent a single packet reception, so two neighbors that
   differ by one reception can collapse onto the same code — exactly the tie-collapse seen at
   8 bits.

**18 bits is the smallest width whose step (0.03815 J) is below E_rx (0.0400 J)**; 17 bits gives
0.07629 J, which is 1.9× E_rx and fails. In the other units, 0.03815 J is 0.00038% of E_ini
(260× finer than the 0.1% suggestion) and 1.8% of E_tx. The corrected sweep independently
supports it: 18 bits is also the smallest width that is clean in *both* scenarios of the R\*
geometry (Scenario III: 1.001 hops at 18 bits vs 1.396 at 17), and 18/19/20/24/32 are
numerically indistinguishable in both geometries. The beacon is 18 + 8 = 26 bits, so
**O_ene = 26.65 byte/s** (4920 beacons × 26 bits / 8 / 600 s), against the 41.0 byte/s the
40-bit beacon cost. "32 for margin" is retired: the margin it bought was zero, and at 32 bits
the code was degenerate.

## Task 3 — the FINAL campaign

`scripts/final_campaign.py`, **595 jobs, 595 succeeded, 0 failures** (`run.log`, no
`FAILURES.txt`). Every run asserts, and aborts on mismatch: parsed seed / N / scenario,
`r_range = 2500`, the echoed energy width, and the echoed T_ctrl.

| Part | Rows | File |
|---|---:|---|
| campaign (LQARP, E-LQTP, E-LQTP+energy, Fixed-Periodic T=5, RLOR) | 175 | `campaign/campaign.csv` |
| T_ctrl sweep (Fixed-Periodic 5/10/20/40/60 s) | 175 | `tctrl_sweep/tctrl_sweep.csv` |
| trigger-off control (E-LQTP+energy, ε₀ = 1e12) | 35 | `trigger_off/trigger_off.csv` |
| decision traces (all six variants, every case) | 210 | `decision_trace/decision_trace.csv` + `runs/` |

Matrix: Scenario I, Scenario II at 0.5 / 1.0 / 2.0 / 3.0 / 3.5 m/s, Scenario III, five seeds.
(`base.DRIFT` holds the five manuscript speeds; the task's "six" counts 2.0 m/s twice, once in
Table III and once in Table IV.)

**Non-perturbation check:** each of the 210 decision-trace runs is compared against its dataset
twin, and all 210 `SWEEP` lines match byte-for-byte
(`decision_trace/NONPERTURBATION.txt`: `SWEEP mismatches vs dataset runs: 0`). The
`c_nei`-dominance numbers therefore come from exactly the same runs as the tables.

Rendered tables (generated by `scripts/final_tables.py`, which imports the published values and
the FLAG rule unchanged from `step1_compare.py`):

- `TABLES_II_V.md` — Tables II–V vs the manuscript, protocol × PDR / hops / T_e2e / E_bit /
  O_ctrl / O_ene / O_total. **85 cells outside the published mean ± s.d.** (18 / 16 / 33 / 18).
- `TCTRL_SWEEP.md` — the sweep, O_total headline.
- `DECISION_TRACE.md` — decision-trace summary.

### Headline numbers

| Case | Protocol | PDR | Hops | T_e2e (s) | O_ctrl | O_ene | **O_total** |
|---|---|---:|---:|---:|---:|---:|---:|
| I | LQARP | 0.9950 | 1.93 | 2.90 | 0 | 0 | **0** |
| | E-LQTP (no beacon) | 0.9950 | 1.93 | 2.90 | 20.4 | 0 | **20.4** |
| | E-LQTP+energy | 0.9990 | 3.06 | 4.57 | 20.4 | 26.65 | **47.1** |
| | trigger OFF | 0.9990 | 3.06 | 4.57 | 20.4 | 26.65 | **47.1** |
| | Fixed-Periodic T=5 | 0.9992 | 3.07 | 4.59 | 411.3 | 0 | **411.3** |
| | RLOR-inspired | 0.9850 | 1.68 | 2.48 | 0 | 0 | **0** |
| II 2.0 | LQARP | 0.9788 | 5.16 | 7.44 | 0 | 0 | **0** |
| | E-LQTP (no beacon) | 0.9788 | 5.09 | 7.34 | 59.7 | 0 | **59.7** |
| | E-LQTP+energy | 0.9931 | 3.20 | 4.56 | 146.3 | 26.65 | **172.9** |
| | trigger OFF | 0.9936 | 3.16 | 4.51 | 57.8 | 26.65 | **84.4** |
| | Fixed-Periodic T=5 | 0.9974 | 3.20 | 4.72 | 413.4 | 0 | **413.4** |
| | RLOR-inspired | 0.9907 | 1.60 | 2.36 | 0 | 0 | **0** |
| III | LQARP | 0.9917 | 4.69 | 6.58 | 0 | 0 | **0** |
| | E-LQTP (no beacon) | 0.9903 | 5.00 | 7.07 | 63.6 | 0 | **63.6** |
| | E-LQTP+energy | 0.9918 | 3.06 | 4.51 | 188.1 | 26.65 | **214.7** |
| | trigger OFF | 0.9912 | 3.02 | 4.43 | 59.8 | 26.65 | **86.4** |
| | Fixed-Periodic T=5 | 0.9901 | 3.16 | 4.66 | 413.4 | 0 | **413.4** |
| | RLOR-inspired | 0.9966 | 1.56 | 2.29 | 0 | 0 | **0** |

T_ctrl sweep, Fixed-Periodic O_total is geometry-independent: 413.4 / 208.4 / 105.9 / 54.7 /
37.6 byte/s at T = 5 / 10 / 20 / 40 / 60 s, with PDR 0.9897–0.9987 and hops 3.07–4.21 across
all mobile cases. E-LQTP+energy is 93.7–279.6 byte/s at PDR 0.9572–0.9979. **Periodic breaks
even at T_ctrl ≈ 7–22 s** and is cheaper at every T ≥ 40 s in every case. The trigger accounts
for 13% (0.5 m/s), 30% (1.0), 51% (2.0), 63% (3.0), 68% (3.5) and 60% (III) of
E-LQTP+energy's O_total.

Decision trace, all cases pooled: E-LQTP+energy, its trigger-off control and Fixed-Periodic pass
the sink over in 48–49% of decisions where it is a legal candidate, and in **100%** of those the
chosen relay is worse than the sink on `c_ene` and on `c_del` and wins only on `c_nei`, median
ratio 8.1 × 10³. LQARP and plain E-LQTP pass it over in ~60% of decisions, winning on `c_nei` in
94% (median ratio 403). RLOR never has the sink in its set under this geometry. Both verdicts
hold on the final dataset: the trigger does not drive routing, and a tuned periodic baseline is
cheaper at equal or better PDR.

## One new issue found while auditing this dataset (Scenario III only, not fixed)

The decision traces contain non-finite Q values, and only in Scenario III: 1.4% (LQARP), 1.5%
(E-LQTP), 2.4% (E-LQTP+energy), 2.7% (trigger-off) and 2.8% (Fixed-Periodic) of decisions have
at least one candidate with Q = +∞, and in nearly all of those that candidate is the one chosen.
Scenarios I and II have exactly zero.

Traced mechanism, verified against the shipped functions and the real channel grid
(`/tmp` scan reproduced in this report; grid scan covers 0–6000 m × 5–500 m):

1. The candidate filters `inNRange` / `inNSnr` read the **held** neighbor pose
   (`x_j_zoh`, `query_z_j_zoh`), so a pair admitted to the candidate set was within
   r_range and above the SNR gate *as of its last HELLO*.
2. `cPred`/`reward` call `linkSample(i, j)` at the **live** pose. In Scenario III the eddy plus
   Gauss–Markov drift can carry an AUV–AUV pair beyond the 6 km Bellhop grid.
3. Outside the grid the loader returns `valid = false, snr = NaN`; `cLin` then returns +∞
   (its `p_e >= 1.0` branch), so `c_pred` is non-finite.
4. `reward()` has an explicit branch for that case: `R = copysign(inf, num)`, i.e. **+∞ for a
   link whose channel is unknown and in practice unusable** — the most attractive possible
   reward. Inside the grid, `c_lin` is finite at all 119,600 sampled cells (the `kBerFloor`
   plateau is 4 × 10⁻⁷), so this is purely an out-of-envelope effect.
5. Once a Q entry is +∞ it never returns to a finite value, and `maxNext` propagates it to
   predecessors, which is why 1,500 candidate entries carry +∞ while only 108 show `R = +∞` at
   the moment of the dump.

This is pre-existing (the `!isfinite(c_pred)` branch is inherited LQARP reward code, untouched by
Steps 2–6), it affects **every** protocol at a similar rate, so Table V's comparisons remain
like-for-like, and the qualitative conclusions do not rest on it — Scenarios I and II are clean
and show the same mechanism. I have **not** changed it, because the fix is a reward-semantics
decision rather than a coding error: options are to exclude out-of-envelope pairs from the
candidate set (make the filters read the live sample the reward uses), to give such a link
R = 0, or to clamp `c_lin` at the far-field plateau. Table V should carry a footnote until this
is decided.

## Status of earlier numbers

**This campaign supersedes the numeric tables of Steps 1h, 1i, 2–4 and 5. Only the qualitative
mechanism findings carry forward: `c_nei` dominance of next-hop choice, the event trigger not
driving routing outcomes, and the reception-gating and quantizer fixes themselves.** Nothing
else in the project should be cited as authoritative going forward. In particular
`paper/step1-final-campaign-summary.md`, `paper/step1i-baseline-check-and-tctrl-sweep.md`,
`paper/step2-4-rxonly-geometry-rerun-verdict.md` and the numeric tables inside
`paper/step5-periodic-gating-and-hop-anomaly-report.md` all contain figures that this dataset
replaces; Step 1g's 32-bit selection is retired in favor of the 18-bit choice above.
