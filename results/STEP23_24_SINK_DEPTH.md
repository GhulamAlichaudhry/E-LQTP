# Steps 23–24: sink acoustic depth vs Scenario I PDR

January Bellhop grid. Same 15 Step-22 placements (N ∈ {20,40,60},
seeds 20260921–20260925, UniformRandomVariable stream 1). Sink XY =
(3000, 3000) m. Kinematic sink z stays 5 m. LQARP only, detour on,
T_sim=1600 s, 30 s/packet.

## Step 23 — SNR-to-sink fraction vs query depth

SNR-feasible = N_SNR: SNR(AUV, sink) > 8.68 dB (NaN / invalid /
nearPressureRelease fail). Grid lookup only; no traffic.

r_range (canonical 50 m) = 5125 m. Every AUV is inside N_range
(max horizontal range 3439–4146 m). N_depth always holds
(AUVs z ≥ 10 m, sink kinematic z = 5 m). Therefore I-membership of
the sink equals N_SNR. The 5 m column matches Step 22’s
“AUVs with sink in I” counts exactly.

| N | seed | 5 m | 10 m | 50 m | 100 m |
|---|------|-----|------|------|-------|
| 20 | 20260921 | 4/20 (0.200) | 20/20 (1.000) | 20/20 (1.000) | 20/20 (1.000) |
| 20 | 20260922 | 5/20 (0.250) | 20/20 (1.000) | 20/20 (1.000) | 20/20 (1.000) |
| 20 | 20260923 | 3/20 (0.150) | 20/20 (1.000) | 20/20 (1.000) | 20/20 (1.000) |
| 20 | 20260924 | 6/20 (0.300) | 20/20 (1.000) | 20/20 (1.000) | 20/20 (1.000) |
| 20 | 20260925 | 7/20 (0.350) | 20/20 (1.000) | 20/20 (1.000) | 20/20 (1.000) |
| 40 | 20260921 | 11/40 (0.275) | 40/40 (1.000) | 40/40 (1.000) | 40/40 (1.000) |
| 40 | 20260922 | 9/40 (0.225) | 40/40 (1.000) | 40/40 (1.000) | 40/40 (1.000) |
| 40 | 20260923 | 9/40 (0.225) | 40/40 (1.000) | 40/40 (1.000) | 40/40 (1.000) |
| 40 | 20260924 | 7/40 (0.175) | 40/40 (1.000) | 40/40 (1.000) | 40/40 (1.000) |
| 40 | 20260925 | 12/40 (0.300) | 40/40 (1.000) | 40/40 (1.000) | 40/40 (1.000) |
| 60 | 20260921 | 15/60 (0.250) | 60/60 (1.000) | 60/60 (1.000) | 60/60 (1.000) |
| 60 | 20260922 | 13/60 (0.217) | 60/60 (1.000) | 60/60 (1.000) | 60/60 (1.000) |
| 60 | 20260923 | 11/60 (0.183) | 60/60 (1.000) | 60/60 (1.000) | 60/60 (1.000) |
| 60 | 20260924 | 12/60 (0.200) | 60/60 (1.000) | 60/60 (1.000) | 60/60 (1.000) |
| 60 | 20260925 | 14/60 (0.233) | 60/60 (1.000) | 60/60 (1.000) | 60/60 (1.000) |

Per-N mean fraction with sink in SNR-feasible set:

| N | 5 m | 10 m | 50 m | 100 m | 50 m − 5 m |
|---|-----|------|------|-------|------------|
| 20 | 0.250 | 1.000 | 1.000 | 1.000 | +0.750 |
| 40 | 0.240 | 1.000 | 1.000 | 1.000 | +0.760 |
| 60 | 0.217 | 1.000 | 1.000 | 1.000 | +0.783 |

Grand mean @5 m = 0.236; @50 m = 1.000; delta = +0.764.

**Verdict:** the fraction with sink-in-range **increases substantially**
at 50 m vs 5 m. Sink acoustic depth is a major contributor. Horizontal
range is not: N_range misses = 0 across all 15 placements. The 5 m
query sits on the z=0 / z=10 bilinear edge (grid Δz = 10 m); 10 m is
already the first exact grid row and is already 100% feasible.

## Step 24 — Step 22 sweep with sink acoustic query = 50 m

Change: `--sinkAcousticDepth=50` only. Kinematic z remains 5 m.
Same seeds, T_sim, interval, detour, LQARP.

At t=0 every run reports empty I = 0/N and sink in I = N/N.

| N | seed | PDR | T_e2e (s) | E_bit (J/bit) | VOID | TTL | DETOUR hops / pkts | N_tx |
|---|------|-----|-----------|---------------|------|-----|--------------------|------|
| 20 | 20260921 | 1.000 | 2.411 | 6.105e-3 | 0 | 0 | 0 / 0 | 1230 |
| 20 | 20260922 | 1.000 | 2.321 | 6.036e-3 | 0 | 0 | 0 / 0 | 1216 |
| 20 | 20260923 | 1.000 | 2.421 | 6.085e-3 | 0 | 0 | 0 / 0 | 1226 |
| 20 | 20260924 | 1.000 | 2.111 | 6.070e-3 | 0 | 0 | 0 / 0 | 1223 |
| 20 | 20260925 | 1.000 | 2.032 | 6.373e-3 | 0 | 0 | 0 / 0 | 1284 |
| 40 | 20260921 | 1.000 | 3.067 | 7.904e-3 | 0 | 0 | 0 / 0 | 3185 |
| 40 | 20260922 | 1.000 | 3.193 | 8.671e-3 | 0 | 0 | 0 / 0 | 3494 |
| 40 | 20260923 | 1.000 | 3.087 | 7.778e-3 | 0 | 0 | 0 / 0 | 3134 |
| 40 | 20260924 | 1.000 | 3.004 | 8.247e-3 | 0 | 0 | 0 / 0 | 3323 |
| 40 | 20260925 | 1.000 | 3.038 | 8.416e-3 | 0 | 0 | 0 / 0 | 3391 |
| 60 | 20260921 | 1.000 | 4.581 | 1.138e-2 | 0 | 0 | 0 / 0 | 6880 |
| 60 | 20260922 | 1.000 | 4.836 | 1.252e-2 | 0 | 0 | 0 / 0 | 7566 |
| 60 | 20260923 | 1.000 | 4.568 | 1.101e-2 | 0 | 0 | 0 / 0 | 6653 |
| 60 | 20260924 | 1.000 | 4.757 | 1.240e-2 | 0 | 0 | 0 / 0 | 7497 |
| 60 | 20260925 | 1.000 | 5.068 | 1.265e-2 | 0 | 0 | 0 / 0 | 7644 |

SNR-reception-failure = 0, ENERGY = 0, SIMEND = 0, O_ctrl = 0
in every run. Sample std over the 5 seeds:

| N | PDR mean ± std [min, max] | T_e2e (s) | E_bit (J/bit) | mean hops |
|---|---------------------------|-----------|---------------|-----------|
| 20 | 1.000 ± 0.000 [1.000, 1.000] | 2.259 ± 0.178 | 0.00613 ± 0.00014 | 1.144 ± 0.025 |
| 40 | 1.000 ± 0.000 [1.000, 1.000] | 3.078 ± 0.071 | 0.00820 ± 0.00037 | 1.530 ± 0.068 |
| 60 | 1.000 ± 0.000 [1.000, 1.000] | 4.762 ± 0.206 | 0.01199 ± 0.00074 | 2.237 ± 0.139 |

### Versus Step 22 (sink acoustic z = 5 m)

| N | Step 22 PDR | Step 24 PDR |
|---|-------------|-------------|
| 20 | 0.855 ± 0.324 [0.275, 1.000] | 1.000 ± 0.000 |
| 40 | 0.900 ± 0.179 [0.584, 1.000] | 1.000 ± 0.000 |
| 60 | 0.504 ± 0.454 [0.000, 0.993] | 1.000 ± 0.000 |

**PDR variance comes down substantially** (std 0.32 / 0.18 / 0.45 → 0).
VOID / TTL / DETOUR all go to zero. Mean PDR is 1.0 at every density,
so the LQARP-paper rise N=20 < N=40 < N=60 **cannot appear**: the
channel is saturated (every AUV has a one-hop SNR path to the sink).
That is a ceiling, not a remaining bimodality. T_e2e and mean hops
*increase* with N because c_nei = exp(|I(s_j)|) prefers well-connected
relays over the sink (number_sink = 0 ⇒ c_nei = 1), not because the
link fails.

Sink-depth fix alone is sufficient for the PDR/variance problem.
E-LQTP / RLOR and deliberate relay placement were not added.
