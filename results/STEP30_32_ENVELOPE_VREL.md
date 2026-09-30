# Steps 30–32: envelope removal, T_sim=600 s, v_rel diagnostic

Same placement as Step 29: N=40, seed 20260921, ||v_drift||=2.0 m/s,
azimuth 5.968 rad (341.95°), v_drift=(1.902, −0.620, 0) m/s,
β₁=β₂=1.0, January, sink acoustic z=50 m. Boundary default is now
`--boundary=remove`. Scenario III is not implemented.

## STEP 30 — Remove on XY exit

An AUV that leaves `[0,6000]²` is taken out of the active simulation:
velocity zeroed, excluded from I and from new traffic. Node event:
**OUT_OF_ENVELOPE**. Packets at or arriving at that node fail as
**LOST_NODE_EXIT**, not VOID. Future packets from a removed source are
not generated (`gen_skipped_dead_src`; not a packet failure).

`--boundary=open` remains as the HOLD ablation. Reflect/clamp are not
implemented. z is unused (0 z-exits).

### Effective node count, seed 20260921, N=40, v=2.0 m/s

Same census on LQARP and E-LQTP (identical mobility). Drain (120 s)
continues SweepExits, so the end-of-run OUT_OF_ENVELOPE count is one
or a few nodes higher than the T_sim snapshot.

| t (s) | alive AUVs | exited | fraction gone |
|------:|----------:|-------:|--------------:|
| 0 | 40/40 | 0 | 0% |
| 200 | 33/40 | 7 | 17.5% |
| 400 | 31/40 | 9 | 22.5% |
| 600 | 27/40 | 13 | **32.5%** |
| 800 | 23/40 | 17 | 42.5% |
| 1000 | 21/40 | 19 | 47.5% |
| 1200 | 19/40 | 21 | 52.5% |
| 1400 | 18/40 | 22 | 55.0% |
| 1600 | 14/40 | 26 | **65.0%** |

At T_sim=1600 s: 26/40 predicted and 26/40 removed inside the
generation window; OUT_OF_ENVELOPE=27 includes one drain exit.

### LQARP vs E-LQTP at T_sim=1600 s, remove vs previous open/HOLD

| metric | LQARP open | LQARP remove | E-LQTP open | E-LQTP remove |
|---|---:|---:|---:|---:|
| PDR | 1.000 | 1.000 | 1.000 | 0.9985 |
| T_e2e (s) | 4.176 | 3.101 | 4.574 | 3.381 |
| E_bit (J/bit) | 9.92×10⁻³ | 8.35×10⁻³ | 1.08×10⁻² | 8.94×10⁻³ |
| O_ctrl (byte/s) | 0 | 0 | 185 | 1194 |
| mean hops | 1.851 | 1.557 | 2.022 | 1.665 |
| N_gen / N_succ | 2160 / 2160 | 1365 / 1365 | 2160 / 2160 | 1365 / 1363 |
| VOID / DETOUR / SNR | 0 | 0 | 0 | 0 |
| OUT_OF_ENVELOPE | — | 27 | — | 27 |
| LOST_NODE_EXIT | — | 0 | — | 2 |
| gen_skipped | — | 795 | — | 795 |

**The numbers do change once exited nodes are removed rather than
left as silent NaNs.** N_gen drops by 37% (dead sources stop
emitting). Conditional PDR among generated packets stays 1.0 for
LQARP; E-LQTP loses two in-flight packets to LOST_NODE_EXIT (PDR
0.9985). Mean hops and T_e2e fall because the remaining population is
the 14 AUVs that have not yet hit the +x/−y wall — a biased subset,
not a healthier protocol. E-LQTP O_ctrl jumps (185 → 1194 byte/s):
frozen removed nodes (v=0) vs still-drifting live nodes create large
EKF innovations on those pairs even though they are excluded from I.

Alive–alive AUV–AUV pairwise distance change remains ~10⁻¹⁰ m
(physical relative velocity still zero among nodes that are both
still moving).

## STEP 31 — T_sim=600 s

Traffic: 30 s interval → 20 packets/node if the source stays alive
(800 scheduled; 669 generated + 131 skipped).

| t (s) | alive | exited | fraction |
|------:|------:|-------:|---------:|
| 0 | 40 | 0 | 0% |
| 200 | 33 | 7 | 17.5% |
| 400 | 31 | 9 | 22.5% |
| 600 | 27 | 13 | **32.5%** |

Predicted XY exits inside 600 s: 13/40. OUT_OF_ENVELOPE=16 includes
three more during the 120 s drain (another 240 m of drift).

**600 s does not keep attrition under ~20% or ~25%.** 13/40 = 32.5%
are gone by the end of the generation window.

| metric | LQARP 600 s | E-LQTP 600 s |
|---|---:|---:|
| PDR | 1.000 | 0.9970 |
| T_e2e (s) | 4.455 | 5.027 |
| E_bit (J/bit) | 1.137×10⁻² | 1.255×10⁻² |
| O_ctrl (byte/s) | 0 | 374 |
| mean hops | 2.121 | 2.339 |
| N_gen / N_succ | 669 / 669 | 669 / 667 |
| VOID / DETOUR / SNR | 0 / 0 / 0 | 0 / 0 / 0 |
| OUT_OF_ENVELOPE | 16 | 16 |
| LOST_NODE_EXIT | 0 | 2 |
| Broadcast_k rising | 0 | 377 |

E-LQTP is still a small regression: +10% hops, +13% T_e2e, +10%
E_bit, two LOST_NODE_EXIT, nonzero O_ctrl. PDR is no longer a hard
ceiling once removal is real, but the drop is those two in-flight
losses, not VOID/SNR.

### T_sim recommendation (not finalized)

From this seed/azimuth at 2.0 m/s:

| T_sim | exited at T_sim | fraction | displacement |
|------:|----------------:|---------:|-------------:|
| 200 s | 7/40 | 17.5% | 400 m |
| 400 s | 9/40 | 22.5% | 800 m |
| 600 s | 13/40 | 32.5% | 1200 m |
| 1600 s | 26/40 | 65.0% | 3200 m |

To hold attrition under ~20%: **T_sim ≈ 200 s** on this seed.
To hold under ~25%: **T_sim ≈ 400 s** (9/40 = 22.5%).
600 s overshoots. Other seeds and headings will differ (attrition
is directional). Drain should either freeze mobility or be short,
or OUT_OF_ENVELOPE will keep climbing after T_sim.

Not adopted here — waiting on a decision.

## STEP 32 — Is Scenario II structurally low-signal for c_drift?

Physical kinematics: yes, AUV–AUV relative velocity is zero.
`max_AUV_AUV_pairwise_distance_change` among still-alive pairs is
~3×10⁻¹⁰ m at 600 s.

Protocol `v_rel` (SPEC 2.1, the input to `c_drift`) is **not** zero
on AUV–AUV reward evaluations. E-LQTP 600 s, every candidate in I at
each `learnFrom` (the actual forwarding reward path):

| | all evals | AUV–AUV | to-sink |
|---|---:|---:|---:|
| count | 25499 | 23937 (94%) | 1562 (6%) |
| mean \|v_rel\| (m/s) | 1.278 | **1.279** | 1.254 |
| max \|v_rel\| (m/s) | 1.999 | 1.999 | 1.997 |
| fraction \|v_rel\| > 0.01 | 99.88% | **99.88%** | 99.87% |
| fraction \|v_rel\| > 0.05 | 98.22% | — | — |

Histogram, AUV–AUV (600 s): none below 10⁻⁶ m/s; 29 in [10⁻⁶, 0.01);
563 in [0.01, 0.1); 3146 in [0.1, 0.5); 4543 in [0.5, 1); **15656 in
[1, 2)**. Mean 1.279 m/s is 2 × (2/π) to a few parts in 10³ — the
2-D average of |v_drift · p̂_ij| when neighbor ZOH velocity is 0.

**What this means**

- True relative motion between AUVs is identically zero under uniform
  drift. `c_drift` cannot see closing/opening among relays as a
  physical fact.
- The protocol still feeds `c_drift` a large, geometry-dependent
  `v_rel` on ~94% of reward evaluations (AUV–AUV) because neighbor
  velocity ZOH cold-starts at 0 (SPEC 2.1: no broadcast yet) and the
  event trigger updates ZOH only on the firing pair. Until that
  pair’s HELLO, every neighbor looks stationary, so `v_rel` is the
  projection of the common current onto the pair axis.
- That *does* rank AUV relays (heading vs current), but it is an
  artifact of unknown neighbor velocity, not the paper’s
  non-uniform-relative-motion story. After a successful ZOH update
  on a pair, AUV–AUV `v_rel` should collapse to 0 and `c_drift`
  becomes a uniform 1.5× scale (`sigmoid(0)=0.5`, β₂=1) that does
  not differentiate among AUV relays at all; only AUV–sink keeps a
  real LOS rate (sink is actually still).

**Finding, not a re-run:** Scenario II is a near-null / mixed
setting for the paper’s central claim. E-LQTP is measurably
different from LQARP here, but the difference is ZOH-cold-start +
AUV–sink LOS rate + control overhead, not AUV–AUV relative
kinematics. Scenario III (non-uniform relative motion) is where
`c_drift` has a physical signal on relay-to-relay decisions.

The 1600 s remove run shows the same pattern (AUV–AUV mean
\|v_rel\|=1.272 m/s, 99.9% > 0.01, 31094/33366 evals AUV–AUV).
