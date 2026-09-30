# Steps 50–52: O_ctrl window and rising-edge HELLO

No Scenario III. Unit suite **PASS=31 FAIL=0** (new test 14c).

Same point: seed 20260921, N=40, v=2 m/s, T_sim=600 s,
`--boundary=remove`, β₁=β₂=1, ε₀=2.0, s_cap=2.0.

Raw: `results/scenario-ii-elqtp-step52.txt`,
`results/scenario-ii-lqarp-step52.txt`,
`results/scenario-ii-periodic-step52.txt`.

---

## Step 50 — how O_ctrl was computed, and the fix

**Before (Step 49 and earlier).** One shared path in
`Pipeline::WriteReport` (not per-protocol):

```
O_ctrl = proto->controlTxCount() * 50 / T_sim
```

`controlTxCount()` is incremented inside `ElqtpProtocol::tick`
(`countEventControlTx` or `emitPeriodicControl`). Ticks are
scheduled on `[tickDt, T_sim + drain]`. Drain default is 120 s, so
the numerator covered **[0, T_sim+drain]** while the denominator
was **T_sim only**. LQARP / RLOR return 0 and were unaffected.
E-LQTP and Fixed-Periodic both inherited the mixed window.

Step 49 numbers under that definition: E-LQTP `ctrl_tx=8888`,
`O_ctrl=741` byte/s.

**Fix (option a, T_sim-only numerator).** Drain exists so in-flight
data packets can finish for PDR / latency. It is not an extension
of the control-accounting window. `OnTick` snapshots
`controlTxCount` (and pair-level rising/ones) at the first tick
with `Now() >= T_sim`. `WriteReport` uses that snapshot:

```
O_ctrl = ctrl_tx([0, T_sim]) * 50 / T_sim
```

Same function for LQARP, E-LQTP, RLOR-inspired, and Fixed-Periodic.
Full-run `ctrl_tx` is still printed, and is not used in O_ctrl.

SPEC Part 4 now states this definition once.

**Corrected O_ctrl on the Step 49 trajectory.** The data plane on
this seed is bit-identical to Step 49 (see Step 52): same PDR,
hops, T_e2e, E_bit, N_tx, pair-level `Broadcast_k` ones/rising on
the full run (16700 / 2602). Isolated window-only re-execution of
the old persist-every-tick HELLO was not run (that binary is gone).
The jointly corrected number on that same placement is Step 52
below. A Fixed-Periodic check of the shared function, same seed:

| | billed against T_sim (old) | [0, T_sim] / T_sim (new) |
|---|---:|---:|
| ctrl_tx | 5945 (includes drain) | **4961** |
| O_ctrl (byte/s) | 495.4 | **413.42** |

4961 = 41 nodes × 121 rounds (t=0, 5, …, 600). That is the
analytic T_ctrl=5 s baseline. The shared snapshot is doing the
arithmetic that the paper definition asked for.

---

## Step 51 — persist-tick HELLO was a bug

**Before.** `countEventControlTx` transmitted if any neighbor had
`Broadcast_k(i,j)=1` on that tick. Persistence hold kept
`Broadcast_k=1` for several seconds after a rising edge
(ones/rising ≈ 6.4 on the full Step 49 run), so each fire billed
about six HELLOs.

**SPEC 2.4 (now explicit).** Persistence is a gate that decides
whether to fire once. A control-packet transmission occurs on each
0→1 transition of `Broadcast_k`, not on every tick where
`Broadcast_k=1` persists.

**After.** Node j transmits iff any pair (i,j) has `now=1` and
`prev≠1`. Further ticks while the flag stays 1 are silent until it
falls and rises again.

Test 14c constructs `Broadcast_k=1` held across three flushes:
counts are 1, 1, 1, then 2 after a 1→0→1. Full suite 31/31.

Ingest of ZOH velocity still happens on the pair while
`Broadcast_k=1` (that is the state update, not a re-announce).
Only the transmitted HELLO is rising-edge.

---

## Step 52 — same comparison, both fixes

Data-plane metrics match Step 49 exactly. Control accounting does
not.

| | Step 49 (mixed window, persist TX) | Step 52 (both fixes) |
|---|---:|---:|
| ctrl_tx on [0, T_sim] | (not snapped; full=8888) | **1954** |
| ctrl_tx full run (drain incl.) | 8888 | 2452 |
| Broadcast_k rising T_sim | (full=2602) | **2067** |
| Broadcast_k ones T_sim | (full=16700) | 8519 |
| O_ctrl (byte/s) | 741 | **162.8** |
| vs Fixed-Periodic 413.4 | 1.79× | **0.39×** |

O_ctrl is **below** the Fixed-Periodic T_ctrl=5 s baseline
(162.8 < 413.4). 1954 node-level HELLOs on [0, T_sim] vs 4961
periodic.

Pair-level mechanism is unchanged from Step 49:

| live AUV–AUV at T_sim | Step 49 | Step 52 |
|---|---:|---:|
| heard | 548 / 702 = 78.1% | **548 / 702 = 78.1%** |
| rising = 1 on heard | 548 / 548 | **548 / 548** |
| rising > 1 | 0 | **0** |
| \|x_forecast vel\| = 0 | 548 / 548 | **548 / 548** |
| pair (1,2) fire in T_sim | no (max \|e_trigger\|=3.613 dB) | **no (3.613 dB)** |
| earliest fire | (18,24) t=11 s | **(18,24) t=11 s** |

Rising 2067 vs ctrl_tx 1954: a node that has two pairs rise on the
same tick still sends one HELLO. The leftover above the 548 live
AUV–AUV first-fires is exits and AUV–sink geometry — the two
contributors that were supposed to stay.

ones/rising at T_sim is 8519/2067 ≈ 4.1. The hold is still there;
it is no longer billed as extra HELLOs.

### LQARP vs E-LQTP vs Fixed-Periodic

| metric | LQARP | E-LQTP | Fixed-Periodic |
|---|---:|---:|---:|
| PDR | 1.000 | **0.9955** | 1.000 |
| N_succ | 669 | 666 | 669 |
| mean hops | 2.121 | **2.374** | 2.121 |
| T_e2e (s) | 4.455 | **5.096** | 4.455 |
| E_bit (J/bit) | 1.137×10⁻² | **1.276×10⁻²** | 1.137×10⁻² |
| N_tx | 1419 | 1585 | 1419 |
| O_ctrl (byte/s) | 0 | **162.8** | **413.4** |
| ctrl_tx T_sim | 0 | 1954 | 4961 |
| rising T_sim | 0 | 2067 | — |
| LOST_NODE_EXIT | 0 | 3 | 0 |
| VOID | 0 | 0 | 0 |
| metrics finite | yes | **yes** | yes |

LQARP is unchanged from Steps 34/47/49. Periodic data-plane
matches LQARP (β₁=β₂=0 on that ablation, as before); its O_ctrl
now matches the analytic 41×121×50/600.

---

## Checkpoint

- O_ctrl is a shared [0, T_sim] / T_sim metric. Drain is not in
  the numerator. Periodic measures 413.4, not 495.
- Event HELLO is one packet per rising edge. Test 14c. SPEC 2.4
  says so.
- E-LQTP O_ctrl = **162.8 byte/s**, under the periodic baseline.
- Live AUV–AUV still 548/548 rising=1, forecast velocity 0.
- Unit tests 31/31. No NaN / VOID.
- Scenario III not started.
