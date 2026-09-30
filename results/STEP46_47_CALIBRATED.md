# Steps 46–47: Option B + ε₀=2.0, then the first trustworthy comparison

No Scenario III. `s_cap = kSCapDb = 2.0` dB and `epsilon_0 = 2.0` dB
are now the compiled defaults (CLI still overrides `epsilon_0`).

Unit suite: **PASS=30 FAIL=0**. No test assumed the old default 4.0
or the unbounded trigger formula. Test 7 sets `epsilon_0=1.0`.
Identity tests use 1e12. Test 14 uses the new default on a
stationary field and still does not persist-trigger.

Same Scenario II point: seed 20260921, N=40, v=2 m/s, T_sim=600 s,
`--boundary=remove`, β₁=β₂=1.

Raw: `results/scenario-ii-elqtp-step47.txt`,
`results/scenario-ii-lqarp-step47.txt`.

---

## Step 46 — what changed

SPEC 2.3 addendum trigger threshold:

```
epsilon_k = epsilon_0 + λ * min(√S_k, s_cap)
s_cap = kSCapDb = √rMeas = 2.0 dB
```

`P_forecast` recursion is unchanged (still predict-only). The cap
applies only to the **trigger** `epsilonTrigger`. Kalman `epsilon_k`
(N_stab / `c_pred`) still uses the updated `P` and is unaffected.

`ElqtpConfig::epsilon_0` default is 2.0. Scenario II no longer
hard-wires 4.0 when `--epsilon_0` is omitted.

On this run the cap is doing its job: never-heard live pairs have
max `epsilon_trigger` median **4.0 dB** (was 171 dB in Step 44).

---

## Step 47.1 — pair (1,2)

| | |
|---|---|
| max \|e_trigger\| on [0, 600] | 3.613 dB (same ceiling as Step 43) |
| \|e_trigger\| ≥ ε on [0, 600] | **0** |
| first rising edge in T_sim | **none** |
| first rising edge in drain | **t = 698 s** (`heard=1`, `v_rel=0` after the copy) |

ε₀=2.0 plus `s_cap` makes the late-time gate **4.0 dB**. Pair (1,2)
saturates at 3.61 dB, so it is the intended miss inside T_sim.
It crosses during the extra 120 s of dead-reckoning after T_sim.
That is consistent with choosing 2.0 over 1.5.

---

## Step 47.2 — network-wide first-fire fraction at T_sim

27 AUVs alive at t=600 → **702** directed live AUV–AUV pairs.

| | Step 44 (ε₀=4, unbounded P) | Step 47 (ε₀=2, s_cap=2) |
|---|---:|---:|
| heard live | 100 / 702 = **14.2%** | **548 / 702 = 78.1%** |
| never heard live | 602 | 154 |

**78.1%** sits on the Step 44/45 projection (78.5% of pairs have
unheard-window max |e| ≥ 4.0 dB). The leftover 154 have median
ceiling 2.78 dB, p80 3.59 dB — the lower tail the conservative
threshold was meant to leave behind. Only 2% of that leftover
even touched 4.0 dB (not enough for W/ρ persistence).

Option B + ε₀=2.0 did what it was calibrated to do: catch the
70–80% contour of the known ZOH-init class.

---

## Step 47.3 — O_ctrl

| run | O_ctrl (byte/s) | ctrl_tx | Broadcast_k rising |
|---|---:|---:|---:|
| LQARP (this run) | **0** | 0 | 0 |
| Step 32 ungated (old one-step e_k) | 374 | — | 377 |
| Step 34 gated (old one-step e_k) | 358 | — | 372 |
| Step 42–43 dual-track, ε₀=4, unbounded P | 174 | 2093 | 473 |
| **Step 47 calibrated** | **774** | **9284** | **2416** |
| Fixed-Periodic T_ctrl=5 s, 41 nodes (analytic) | ~413 | ~4961 | — |

The calibrated trigger costs **774 byte/s**:

- 2.2× Step 34’s 358
- 4.4× the dual-track-but-still-gated Step 42–43 run (174)
- **~1.9× a 5 s Fixed-Periodic ablation (~413)**

First-fire count is in spec (548 pairs). Rising edges are not:
2416 / 548 ≈ **4.4 rising edges per pair that ever hears**. After
the first HELLO, ZOH is correct (`v_rel=0` on heard evals; 6374
heard reward evals, all exactly 0). The forecast is then reset to
`x_hat_{k|k}`, whose velocity was **never written from the new
ZOH**, so `x_forecast` keeps walking on the false 2 m/s init,
`e_k^{trigger}` grows again, and the pair re-fires. That loop is
what blew O_ctrl past periodic.

This is a leftover of the Step 42 reset rule (“copy `x_hat`”),
not a failure of Option B or of ε₀=2.0. Flag it: an
event-triggered protocol that spends **more** control traffic
than the periodic ablation is not yet a Section 4.4 result to
stand on.

---

## Step 47.4 — LQARP vs E-LQTP (same seed / N / v / T_sim)

LQARP is bit-identical to Step 34 (PDR 1, hops 2.121, T_e2e 4.455,
E_bit 1.137×10⁻²). The comparison moved only on the E-LQTP side.

| metric | LQARP | E-LQTP Step 34 (buggy trigger) | E-LQTP Step 47 (this run) |
|---|---:|---:|---:|
| PDR | 1.000 | 0.9970 | **0.9985** |
| N_gen / N_succ | 669 / 669 | 669 / 667 | 669 / 668 |
| mean hops | 2.121 | 2.429 | **2.537** |
| T_e2e (s) | 4.455 | 5.170 | **5.477** |
| E_bit (J/bit) | 1.137×10⁻² | 1.304×10⁻² | **1.361×10⁻²** |
| N_tx | 1419 | 1623 | 1696 |
| O_ctrl (byte/s) | 0 | 358 | **774** |
| Broadcast_k rising | 0 | 372 | 2416 |
| LOST_NODE_EXIT | 0 | 2 | 1 |
| VOID | 0 | 0 | 0 |
| metrics finite | yes | yes | **yes** |

Direction versus the Step 34 table: **same sign, larger
magnitude**. E-LQTP still has slightly lower PDR (one in-flight
envelope loss vs LQARP’s zero), more hops, more latency, more
energy per bit, and now much more O_ctrl. The extra hops /
T_e2e / E_bit vs Step 34 are consistent with β₂ actually turning
on: heard co-moving pairs have `v_rel=0` so
`c_drift = c_del (1 + β₂ · ½) = 1.5 c_del`, which re-ranks
AUV relays. Step 34 almost never heard, so β₂ was off and
`c_drift = c_del`.

No NaN, no VOID storm, no degenerate PDR. The routing metrics
are finite and interpretable. The number that is **off** is
O_ctrl, for the re-trigger reason above.

---

## Checkpoint before Scenario III

Trustworthy:

- Dual-track innovation (Steps 42–43)
- Option B cap (ε median 4.0 dB, not 171)
- First-fire rate 548/702 = 78.1% on the calibrated contour
- LQARP baseline unchanged
- No degenerate metrics

Not ready to treat as the paper’s E-LQTP vs periodic O_ctrl
result:

- Re-fires after a correct ZOH copy because `x_forecast` is
  reset to an `x_hat` whose velocity was never ingested from
  the HELLO. That is why 548 first-fires become 2416 rising
  edges and 774 byte/s (> periodic).

Recommend resolving that reset (write forecast / `x[3:5]` from
odometry − received ZOH at the HELLO, then reset P) **before**
Scenario III mobility, where genuine `v_rel` would be
indistinguishable from this leftover loop.
