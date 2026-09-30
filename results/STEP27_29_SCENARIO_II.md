# Steps 27–29: Scenario II first correctness check

Single point, not a sweep. N=40, seed 20260921, ||v_drift||=2.0 m/s,
January Bellhop, sink acoustic query z=50 m (kinematic z=5 m).
T_sim=1600 s, 400-bit packets every 30 s (2160 generated).
Unit checks still 29/29 after the EKF/ZOH changes below.

## STEP 27 — Linear uniform current drift

### Kinematics (Section 4.2)

```
pdot_i(t)  = v_cmd_i(t) + v_drift(t)
v_cmd_i    = 0                 # no active propulsion
v_drift(t) = v_drift^(0)       # constant, identical on every AUV
pdot_sink  = 0                 # sink does not drift
```

AUV–AUV relative velocity is exactly zero. The only nonzero relative
motion is AUV-to-sink. Confirmed at end of run:
`max_AUV_AUV_pairwise_distance_change = 7.8e-10 m` (numerical noise).

### Mobility model

**`ns3::ConstantVelocityMobilityModel`** on every node. Sink velocity
is the zero vector. Protocol `LqarpNode` poses are copied from ns-3
on every forward and every 1 s tick (`setKinematics`). Scenario I
still uses `ConstantPositionMobilityModel`.

### Direction for seed 20260921 (stream 2)

| | |
|---|---|
| azimuth | 5.9681552082 rad (**341.95 deg**) |
| v_drift | **(1.901574, −0.619690, 0)** m/s |
| \|\|v_drift\|\| | 2.0 m/s |
| vz | 0 (horizontal) |

FLAG — direction is a uniform **horizontal** azimuth, not
uniform-on-a-sphere. A 3-D isotropic 2 m/s draw would exit the 500 m
depth column in at most 250 s. Ocean current is horizontal; vz=0 is
the physically motivated reading of Section 4.2.

### Volume-exit diagnosis (do not silently pick a wall policy)

Displacement over 1600 s at 2.0 m/s = **3200 m** vs a 6000 m footprint.

| | |
|---|---|
| AUVs that would leave [0,6000]² within T_sim | **26 / 40** |
| first exit time | **51.79 s** |
| z-exits ([0,500] m) | **0** (vz=0) |

**HOLD used this run: `boundary=open`.** Nodes keep drifting. They are
not reflected, clamped, or removed. Bellhop queries with horizontal
range > 6000 m return `valid=false` / NaN (same out-of-envelope rule
as always). The rigid AUV cluster stays internally connected
(relative geometry frozen); only AUV–sink links change.

**FLAG — design decision, not taken:** reflect / clamp / remove vs
letting a node leave the box and become acoustically unreachable from
the sink. Open is a correctness hold so this first point is not
contaminated by an unstated wall law. 26/40 leaving is large enough
that the choice will matter for a magnitude sweep.

PDR was still 1.0 on this seed: the cluster translates as a rigid
body, some AUVs drift toward the sink, and node 1 (the SNR trace
AUV) stays inside the box (x: 1982 → 5025 m).

## STEP 28 — EKF / event-trigger under real motion

EKF ticks every dt=1 s with real, changing Bellhop SNR. Neighbor
velocity ZOH **cold-starts at 0** (SPEC 2.1: `pdot_j` is the last
received broadcast; none yet). Predicted SNR uses horizontal range
and the neighbor’s `queryDepthM()` (sink acousticZ=50 m), matching
the measurement path. NaN / out-of-envelope measurements skip the
update and do not fire `Broadcast_k`.

### SNR-to-sink, representative AUV id=1, every 100 s

Same trajectory on both protocols (identical mobility). SNR is **not**
static. Closest approach ~t=400 s (range 1117 m, SNR 48.88 dB), then
the node recedes (t=1600 s: range 2730 m, SNR 30.91 dB, still above
8.68 dB). t=1700 s is the drain window.

| t (s) | x (m) | y (m) | z (m) | rangeH to sink (m) | SNR (dB) | valid |
|------:|------:|------:|------:|-------------------:|---------:|:-----:|
| 0 | 1982.12 | 2160.60 | 219.98 | 1319.35 | 46.28 | true |
| 100 | 2172.27 | 2098.63 | 219.98 | 1223.77 | 47.39 | true |
| 200 | 2362.43 | 2036.66 | 219.98 | 1155.21 | 48.38 | true |
| 300 | 2552.59 | 1974.69 | 219.98 | 1118.68 | 48.86 | true |
| 400 | 2742.75 | 1912.72 | 219.98 | 1117.30 | 48.88 | true |
| 500 | 2932.90 | 1850.75 | 219.98 | 1151.20 | 48.45 | true |
| 600 | 3123.06 | 1788.78 | 219.98 | 1217.45 | 47.55 | true |
| 700 | 3313.22 | 1726.81 | 219.98 | 1311.15 | 46.38 | true |
| 800 | 3503.38 | 1664.85 | 219.98 | 1426.89 | 45.07 | true |
| 900 | 3693.53 | 1602.88 | 219.98 | 1559.79 | 43.50 | true |
| 1000 | 3883.69 | 1540.91 | 219.98 | 1705.83 | 41.84 | true |
| 1100 | 4073.85 | 1478.94 | 219.98 | 1861.93 | 40.08 | true |
| 1200 | 4264.00 | 1416.97 | 219.98 | 2025.76 | 38.14 | true |
| 1300 | 4454.16 | 1355.00 | 219.98 | 2195.59 | 36.51 | true |
| 1400 | 4644.32 | 1293.03 | 219.98 | 2370.13 | 34.71 | true |
| 1500 | 4834.48 | 1231.06 | 219.98 | 2548.42 | 33.08 | true |
| 1600 | 5024.63 | 1169.09 | 219.98 | 2729.72 | 30.91 | true |

### Event trigger (Part 2.4)

E-LQTP, Step-17 defaults: ε₀=4.0 dB, W=5, W_mp=3, ρ=0.6, λ=1.0.
β₁=β₂=1.0 (first non-identity values).

| | |
|---|---|
| Broadcast_k 0→1 rising edges (directed pairs) | **96** |
| pair-ticks with Broadcast_k=1 | **5908** |
| control TX (node-slots; O_ctrl accounting) | **5908** |
| max \|e_k\| (dB) | **34.77** |
| NaN measurements skipped | 82704 (~52 directed pairs beyond the 6000 m Bellhop envelope × 1600 ticks; AUV–AUV range is frozen) |

The trigger **does fire**. ε₀=4.0 dB is not dead at 2.0 m/s on this
site. A 20 s smoke never reached |e_k|≥4 (max 1.93 dB); the full
1600 s run does. O_ctrl counts every tick a node has any neighbor
with Broadcast_k=1, not only rising edges (same convention as the
Fixed-Periodic ablation).

## STEP 29 — LQARP vs E-LQTP, one point

N=40, seed 20260921, ||v_drift||=2.0 m/s, β₁=β₂=1.0 vs LQARP
(no EKF, O_ctrl=0). Not identity: Scenario I `--protocol=elqtp`
still forces β=0 / ε₀=1e12 / tick off.

| metric | LQARP | E-LQTP (β=1,1) |
|---|---:|---:|
| PDR | 1.000 | 1.000 |
| T_e2e (s) | 4.176 | 4.574 |
| E_bit (J/bit) | 9.922×10⁻³ | 1.084×10⁻² |
| O_ctrl (byte/s) | 0 | 184.6 |
| mean hops | 1.851 | 2.022 |
| VOID | 0 | 0 |
| DETOUR hops / packets | 0 / 0 | 0 / 0 |
| SNR-reception-failure | 0 | 0 |
| ENERGY / TTL / SIM_END | 0 | 0 |
| N_gen / N_succ | 2160 / 2160 | 2160 / 2160 |
| N_tx | 3998 | 4367 |

**E-LQTP is measurably different from LQARP** (not an identity run):
more hops, higher T_e2e, higher E_bit, and nonzero O_ctrl from the
event trigger. On this single seed the difference is a modest
regression, not a win — that is a sanity check that c_drift / c_pred
/ N_stab / Broadcast_k are live under motion, not a paper claim.
PDR is still a ceiling (1.0), as in Scenario I at z_ac=50 m; VOID /
DETOUR / SNR-failure never bind here.

No 5-seed × 3-density × parameter sweep was run.
