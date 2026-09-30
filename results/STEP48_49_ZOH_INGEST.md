# Steps 48–49: HELLO writes velocity as ground truth

No Scenario III. Unit suite **PASS=30 FAIL=0**.

Same point: seed 20260921, N=40, v=2 m/s, T_sim=600 s,
`--boundary=remove`, β₁=β₂=1, ε₀=2.0, s_cap=2.0.

Raw: `results/scenario-ii-elqtp-step49.txt`,
`results/scenario-ii-lqarp-step49.txt`.

---

## Step 48 — what changed

SPEC 2.1/2.2 addendum: a received `pdot_j` is ground truth, not an
EKF measurement. On every `zohHeard` transition (event fire,
periodic HELLO, test seam):

```
x_hat[3:5]  <-  pdot_i − pdot_j_received     # overwrite, no blend
x[0:2], x[6] unchanged                         # range-corrected pose/SNR
x_forecast  <-  x_hat_{k|k}
P_forecast  <-  P_{k|k}
```

The write happens **after** that tick’s Kalman update so the filter
cannot pull the velocity back toward the stale estimate on the
same step.

---

## Step 49.1 — pair (1,2)

Unchanged, as required. max |e_trigger| = **3.613 dB**, no
exceedance, **no fire in T_sim**.

---

## Step 49.2 — first-fire fraction at T_sim

27 alive AUVs → 702 directed live AUV–AUV pairs.

| | Step 47 (before ingest) | Step 49 (this run) |
|---|---:|---:|
| heard live | 548 / 702 = **78.1%** | 548 / 702 = **78.1%** |
| never heard live | 154 | 154 |

Identical 78.1%. The ingest only changes what happens after a fire.

---

## Step 49.3–4 — rising edges, O_ctrl, and the mechanism

**On the live AUV–AUV set the loop is gone.**

| | Step 47 | Step 49 |
|---|---:|---:|
| heard live pairs | 548 | 548 |
| rising edges **on those pairs** | (not counted per pair) | **548** |
| pairs with rising = 1 | — | **548 / 548** |
| pairs with rising > 1 | — | **0** |
| \|x_forecast vel\| < 1e−6 | — | **548 / 548** |
| \|x_forecast vel\| min / median / max | — | **0 / 0 / 0** |

Earliest fire: pair **(18, 24)** at **t = 11 s**, `n_rising=1`,
`|x_fc_vel|=0`, `|x_hat_vel|=1.5×10⁻⁴` (Kalman has since nudged
`x_hat` by a fraction of a mm/s; the forecast stayed at 0).
True AUV–AUV `v_rel` is 0. After the HELLO the forecast sits on
that value for the rest of T_sim and does not re-trigger.

`x_hat` velocity among heard pairs at T_sim: median 5.8×10⁻⁴ m/s,
max 0.12 m/s. The filter can wander; the forecast does not.

**Network-wide counters did not drop the way the 2416 / 774
headline suggested**, because that headline mixed live AUV–AUV
re-triggers with everything else:

| | Step 47 | Step 49 |
|---|---:|---:|
| Broadcast_k rising (all pairs, incl. drain) | 2416 | **2602** |
| Broadcast_k ones | 20661 | 16700 |
| O_ctrl (byte/s, ctrl_tx / T_sim) | 774 | **741** |
| ctrl_tx | 9284 | 8888 |

O_ctrl is **741 vs 774** (−4%) and still **~1.8×** the analytic
Fixed-Periodic T_ctrl=5 s baseline (~413 byte/s).

The remaining mass is not the stale-EKF loop. It is:

1. **Volume-exit velocity changes (genuine).** `--boundary=remove`
   zeros an exiting AUV. Relative velocity vs every still-moving
   neighbor jumps from 0 to `v_drift`. The forecast was correctly
   at 0; truth starts changing; a second fire is the right
   behavior. 13 AUVs exit by t=600, 16 by t=721.
2. **AUV–sink pairs (genuine `v_rel`).** The sink is fixed. After
   ingest, forecast vel = `v_drift`, which is the true relative
   motion. First-fires here are real ZOH-init detections, not
   ghosts.
3. **Drain billed to T_sim.** `O_ctrl` uses `ctrl_tx` over the
   full 721 s in the numerator and T_sim=600 s in the denominator.
4. **Persistence hold.** `Broadcast_k` stays 1 for several ticks
   after a fire when |e_trigger| has not yet fallen through the
   4 dB gate (ones/rising ≈ 6.4). `countEventControlTx` emits a
   HELLO on each of those ticks.

So: the bug we set out to fix is fixed. O_ctrl is still above
periodic. That gap is now a mix of real events (exits, sink
geometry) and accounting (drain, hold time), not a silent
copy of a stale EKF velocity.

---

## Step 49.5 — LQARP vs E-LQTP

LQARP is unchanged from Steps 34/47.

| metric | LQARP | E-LQTP Step 47 (stale reset) | E-LQTP Step 49 (ingest) |
|---|---:|---:|---:|
| PDR | 1.000 | 0.9985 | **0.9955** |
| N_succ | 669 | 668 | 666 |
| mean hops | 2.121 | 2.537 | **2.374** |
| T_e2e (s) | 4.455 | 5.477 | **5.096** |
| E_bit (J/bit) | 1.137×10⁻² | 1.361×10⁻² | **1.276×10⁻²** |
| N_tx | 1419 | 1696 | 1585 |
| O_ctrl (byte/s) | 0 | 774 | **741** |
| rising (global) | 0 | 2416 | 2602 |
| LOST_NODE_EXIT | 0 | 1 | 3 |
| VOID | 0 | 0 | 0 |
| metrics finite | yes | yes | **yes** |

Hops / latency / energy moved **toward** LQARP relative to Step 47
(less path churn once live AUV–AUV pairs stop re-firing). PDR is
three envelope losses vs LQARP’s zero — still the volume-exit
story, not a routing collapse.

---

## Checkpoint

Trustworthy and done:

- First-fire rate 78.1% on the calibrated contour
- Live AUV–AUV post-HELLO forecast velocity is identically 0
- Those pairs do not re-trigger (`rising=1` on 548/548)
- Pair (1,2) still silent in T_sim
- Unit tests 30/30
- No NaN / VOID

**Not ready to call O_ctrl a win vs periodic.** 741 > 413.
The leftover is explained (exits, sink, drain accounting,
persistence hold), but it is still elevated. Scenario III would
make exit-like velocity changes indistinguishable from the
Gauss-Markov process, so the O_ctrl comparison should be settled
here — either accept 741 with that explanation, or trim drain
accounting / post-fire hold — before adding genuine mobility.
