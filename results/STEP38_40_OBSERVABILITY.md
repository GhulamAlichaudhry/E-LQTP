# Steps 38–40: Rank-deficient H_k, grid-wide |dSNR/dr|, ε₀ before Scenario III

No Scenario III mobility. No ε₀ retune. Pair (1,2) H_k from the
same seed 20260921 / N=40 / v=2 / 600 s run.
Grid scan: `contrib/elqtp/examples/snr-gradient-scan.cc`,
output `results/snr-gradient-scan.txt`.
SPEC 2.2 now carries the observability note (broadcast = sole
full-vector velocity channel).

---

## STEP 38 — H_k at t=0 and t=400 s, pair (1,2)

Two Jacobians exist in the code. They agree on the kinematic
claim.

**Kalman update** (what `updatePair` uses):  
H = [0 0 0 0 0 0 1] — the measurement is the SNR state.

**Measurement function** for predicted SNR,  
h = SNR(range_H(p_x, p_y), depth_query):

| | t = 0 | t = 400 s |
|---|---|---|
| EKF (p_x, p_y) (m) | (−2295, −1431) | (−1885, −1897) |
| range_H (m) | 2705 | 2674 |
| dSNR/dr (dB/m) | 0.06032 | 0.06032 |
| u_radial = p_horiz/‖p_horiz‖ | (−0.8485, −0.5291, 0) | (−0.7047, −0.7095, 0) |
| **∂h/∂p_x, ∂h/∂p_y, ∂h/∂p_z** | **(−0.05118, −0.03192, 0)** | **(−0.04251, −0.04279, 0)** |
| **∂h/∂pdot (all three)** | **(0, 0, 0)** | **(0, 0, 0)** |
| ‖H_p‖ | 0.06032 | 0.06032 |
| H_p · u_radial / ‖H_p‖ | **1.000** | **1.000** |

H_p = (dSNR/dr) · u_radial exactly. Nonzero only along the
instantaneous **horizontal** LOS. ∂h/∂p_z = 0 (Bellhop is
(range, receiver depth), not Δz). Velocity block is identically
zero: SNR has no direct dependence on pdot; velocity enters only
by integrating into position over dt, which is in F, not H.

That is the rank-deficient measurement. One scalar, one
geometric direction. Tangential p and all of x[3:5] are
unobservable from SNR alone. The Step 35 898 m sideways walk
is this structure, not a tuning failure.

SPEC 2.2 addendum (verbatim intent of the requested note): the
event-triggered broadcast is the **sole** channel for
trustworthy 3-D relative velocity, not merely a bandwidth
optimization.

---

## STEP 39 — Grid-wide |dSNR/dr| (January and July)

Same 10 m forward difference as Step 36. Native grid: every
25 m × 10 m cell with r≥25 m, z≥5 m (12 000 finite points per
month). Dense sample: every 50 m × 20 m (3 000 points) matches
the requested stride.

### Overall

| | January native | July native |
|---|---:|---:|
| min (dB/m) | 8.5×10⁻⁶ | 3.8×10⁻⁶ |
| p25 | 0.0098 | 0.0117 |
| **p50 (median)** | **0.0149** | **0.0226** |
| p75 | 0.0585 | 0.101 |
| p90 | 0.131 | 0.189 |
| p99 | 0.245 | 0.448 |
| max | 0.369 | 1.061 |
| frac > 0.5 dB/m | **0 / 12000** | **81 / 12000 (0.675%)** |
| frac > 2.0 dB/m | **0** | **0** |

Pair (1,2)’s 0.0603 dB/m is **January ~p75**, not a flat outlier.
It is slightly *steeper* than the grid median (0.015 dB/m).

A 2 m false-ZOH step reaches ε₀=4 dB only if |dSNR/dr| ≥ 2.0 dB/m.
**That cell does not exist on either month.** July’s 81 cells
above 0.5 dB/m give 2 m × 0.5 = 1.0 dB, still 4× under ε₀.

### Where the slope lives

Dense-sample range bins, January p50 / p90 (dB/m):

| range (m) | p50 | p90 |
|---|---:|---:|
| 0–1000 | 0.016 | 0.030 |
| 1000–2000 | 0.011 | 0.016 |
| **2000–3000 (pair 1,2)** | **0.010** | **0.150** |
| 3000–4000 | 0.016 | 0.165 |
| 4000–4500 | 0.051 | 0.160 |
| 4500–5000 | 0.035 | 0.103 |
| 5000–5500 (Jan crossing ~5125) | 0.043 | 0.123 |
| 5500–6000 | 0.059 | 0.136 |

July is steeper past 4 km (p50 0.07–0.11, p90 0.26–0.35) and
that is where the 0.5 dB/m tail sits (2.8% of those bins, 0.14%
in-band r<4275 m). **Typical forwarding pairs (Step 25: well
inside r_range, not at the crossing) sit in the flat 0.01–0.06
dB/m body, January or July.**

### Why this does not contradict ~35 dB in-band fading

35 dB peak-to-trough over a ~2 km interference band is
35/2000 ≈ **0.018 dB/m** — the same order as the median 10 m
slope. The fringes are hundreds of metres wide. A 10 m
difference (the EKF’s one-step world) never sees a cliff.

---

## STEP 40 — Back-of-envelope: will genuine GM relative motion trip ε₀=4?

Do not build Scenario III from this. Numbers only.

Compiled GM (SPEC / `gauss-markov.h`), not yet a network
scenario:

```
v_{k+1} = ζ v_k + (1-ζ) μ + √(1-ζ²) σ w_k
ζ = 0.95, dt = 1 s, σ = 1.0 m/s per axis (first-pass)
```

The Scenario II drift sweep ||μ|| ∈ [0.5, 3.5] m/s is a **shared
mean**. It cancels in v_i − v_j. Relative motion is the
independent GM residual. Stationary Var(v_axis)=σ² per node, so
σ(v_rel, one axis) = σ√2 = 1.41 m/s.  
β = −ln(ζ)/dt = 0.0513 s⁻¹, τ ≈ 19.5 s.

### What the trigger actually sees (per-step e_k)

The EKF applies a range-derived SNR update every 1 s. e_k is
**not** the accumulated Δr since the last HELLO. It is the
one-step prediction residual:

e_k ≈ |dSNR/dr| · |v_radial_true − v_radial_EKF| · dt

Two brackets for the unknown radial speed:

| residual Δv | January median g=0.0149 | January p90 g=0.131 | July p90 g=0.189 | July max g=1.06 |
|---|---:|---:|---:|---:|
| one-step GM innovation √(1−ζ²)σ√2 ≈ 0.44 m/s | 0.007 dB | 0.058 dB | 0.083 dB | 0.47 dB |
| fully unknown v_rel (σ√2 ≈ 1.41 m/s) | 0.021 dB | 0.185 dB | 0.267 dB | 1.50 dB |
| 2 m slip (Step 36 style) | 0.030 dB | 0.263 dB | 0.378 dB | 2.12 dB |

All of these, except the single steepest July cell at a full
2 m slip, are **far below ε₀=4 dB**. Persistence (W=5, ρ=0.6)
never gets a single exceedance at the median or at p90.

### What accumulated Δr would look like *if* the trigger saw it

Integrated relative position, one axis, two independent nodes:

σ_Δp(T) = (2σ/√β) √(T − (1−e^{−βT})/β)

| T | σ_Δp (m) | e at Jan median | e at Jan p90 | e at Jul p90 |
|---:|---:|---:|---:|---:|
| 20 s (≈τ) | 24 | 0.36 dB | 3.2 dB | 4.6 dB |
| 60 s | 57 | 0.85 dB | 7.4 dB | 10.7 dB |
| 120 s | 89 | 1.32 dB | 11.6 dB | 16.7 dB |
| 200 s | 119 | 1.77 dB | 15.6 dB | 22.4 dB |

At the **median** gradient, even 200 s of un-wiped geometry
change stays under 4 dB. At p90, a 20–60 s accumulation would
cross 4 dB — **but that is not the EKF innovation.** The filter
wipes range every second, so the trigger never integrates those
tens of metres.

### Verdict

1. Pair (1,2)’s 0.060 dB/m is typical-to-steep (Jan p75), not
   an anomalously flat pocket.
2. **No cell on the January grid, and no cell on July with
   |dSNR/dr|>2 dB/m, can put a 2 m / 1 s residual over ε₀=4.**
3. Genuine GM relative motion at the **median** gradient will
   not trip the event trigger. That is a property of ε₀ versus
   the local slope, not of frozen Scenario II geometry.
4. **Reconsider ε₀ (and/or what the trigger watches) before
   investing in Scenario III mobility.** Building Gauss-Markov
   traffic on the current 4 dB threshold is likely to reproduce
   “Broadcast_k never fires on live pairs” for a more expensive
   reason.

ε₀=4 is sized like a few √R (R=4 dB²) of *assumed* SNR
measurement noise. The Bellhop lookup is deterministic, so that
noise is not in the simulation; the threshold sits above both
the model noise that isn’t there and the physical one-step
slope that is. That mismatch is the thing to decide, not a
mobility-model detail.

No ε₀ change and no Scenario III in this step.
