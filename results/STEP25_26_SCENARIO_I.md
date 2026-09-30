# Steps 25–26: Scenario I candidate filters and four-protocol baseline

January grid, sink acoustic z = 50 m, kinematic z = 5 m, r_range = 5125 m.
Same 15 Step-22 placements. T_sim = 1600 s, 30 s/packet. Unit checks 29/29.

## Step 25 — is N_range / N_depth still binding?

Directed AUV–AUV pairs (not just the sink). D = N_range ∩ N_SNR
(RLOR’s I). I = D ∩ N_depth.

| N | AUV–AUV \|D\| frac | \|I\| frac | N_depth drop of D | N_range fail | I = {sink} only | has an AUV in I |
|---|--------------------|------------|-------------------|--------------|-----------------|-----------------|
| 20 | 0.893 | 0.446 | **0.500** | 0.106 | 0.050 | 0.950 |
| 40 | 0.912 | 0.456 | **0.500** | 0.087 | 0.030 | 0.970 |
| 60 | 0.910 | 0.455 | **0.500** | 0.089 | 0.020 | 0.980 |

Per-seed table: `results/scenario-i-candidates.md`.

**N_depth is still doing real work:** it removes exactly half of
range∩SNR AUV–AUV pairs (random-depth expectation). **N_range is also
still binding:** ~9–11% of AUV–AUV pairs sit outside 5125 m. Mean |I|
is 9 / 18 / 27 (N=20/40/60), not 1. Only 2–5% of AUVs have I = {sink};
95–98% have at least one AUV candidate, which is why LQARP’s c_nei
term can still route around a directly reachable sink. Scenario I is
saturated on PDR but is **not** a degenerate single-hop topology.

## Step 26 — four protocols, 15 placements

Identity E-LQTP: β₁=β₂=0, ε₀=1e12, event trigger off, EKF not ticked
(same configuration as the unit-level identity test). Fixed-Periodic:
β₁=β₂=0, ε₀=4, T_ctrl=5 s, EKF ticked every 1 s. RLOR: no detour.
Control packet size for O_ctrl is a first-pass 400 bits (SPEC gives no
distinct HELLO length). Control energy is **not** folded into E_bit.

### Network-level identity (required)

LQARP and identity E-LQTP match **exactly** on every one of the 15
placements: PDR, O_ctrl, T_e2e, E_bit, mean_hops, VOID, TTL,
DETOUR_hops, N_tx, N_succ (bit-identical ROW fields except `proto=`).

### Per-protocol means (5 seeds, sample std)

All four: PDR = 1.000 ± 0, VOID = SNR = ENERGY = TTL = 0.

| protocol | N | mean hops | T_e2e (s) | E_bit (J/bit) | O_ctrl (byte/s) |
|----------|---|-----------|-----------|---------------|-----------------|
| LQARP | 20 | 1.144 ± 0.025 | 2.259 ± 0.178 | 0.00613 ± 0.00014 | 0 |
| LQARP | 40 | 1.530 ± 0.068 | 3.078 ± 0.071 | 0.00820 ± 0.00037 | 0 |
| LQARP | 60 | 2.237 ± 0.139 | 4.762 ± 0.206 | 0.01199 ± 0.00074 | 0 |
| E-LQTP identity | 20 | 1.144 ± 0.025 | 2.259 ± 0.178 | 0.00613 ± 0.00014 | 0 |
| E-LQTP identity | 40 | 1.530 ± 0.068 | 3.078 ± 0.071 | 0.00820 ± 0.00037 | 0 |
| E-LQTP identity | 60 | 2.237 ± 0.139 | 4.762 ± 0.206 | 0.01199 ± 0.00074 | 0 |
| RLOR-inspired | 20 | **1.000 ± 0** | 1.918 ± 0.204 | 0.00536 ± 0 | 0 |
| RLOR-inspired | 40 | **1.000 ± 0** | 1.887 ± 0.108 | 0.00536 ± 0 | 0 |
| RLOR-inspired | 60 | **1.000 ± 0** | 1.907 ± 0.084 | 0.00536 ± 0 | 0 |
| Fixed-Periodic | 20 | 1.134 ± 0.041 | 2.230 ± 0.133 | 0.00608 ± 0.00022 | 226.41 |
| Fixed-Periodic | 40 | 1.546 ± 0.039 | 3.119 ± 0.188 | 0.00829 ± 0.00021 | 442.03 |
| Fixed-Periodic | 60 | 2.269 ± 0.120 | 4.845 ± 0.219 | 0.01216 ± 0.00064 | 657.66 |

PDR cannot separate the four protocols here (the intended Scenario I
ceiling). Hop count and E_bit can: RLOR always takes the one-hop sink
path (argmax P_succ, no c_nei). LQARP / identity E-LQTP / Periodic
still detour via busy relays, hops rising 1.14 → 1.53 → 2.24, which is
Eq. 34’s $c_{\mathrm{nei}}=e^{\mathrm{number}_{s_j}}$ preferring
$\mathrm{number}_{\mathrm{sink}}=0$ last. Fixed-Periodic is the only
nonzero O_ctrl (linear in N; one control packet per node every T_ctrl).
A few Periodic runs use 1–5 SPEC 1.5 detour hops when N_stab briefly
empties I.

Scenario II/III mobility was not implemented.
