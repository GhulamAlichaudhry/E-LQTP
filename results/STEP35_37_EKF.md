# Steps 35–37: Does EKF `x[3:5]` recover without a broadcast?

Same run as Steps 33–34: seed 20260921, N=40, ||v_drift||=2.0 m/s,
azimuth 5.968 rad, T_sim=600 s, `--boundary=remove`, β₁=β₂=1,
ε₀=4, W=5, ρ=0.6, dt=1 s. Representative pair **(1,2)** — live
AUV–AUV, never heard, `Broadcast_k=0` for the whole window.

Raw log: `results/scenario-ii-elqtp-ekf-35.txt`.
No SPEC / `c_drift` / trigger change in this step.

---

## STEP 35 — `x[3:5]` vs true relative velocity (0, 0, 0)

`x[3:5]` is the EKF’s own velocity state after the SNR update
(`P_{k|k}`). It is **not** the odometry−ZOH value `c_drift` uses.

Initialization is `x[3:5] = v_i − ZOH_0 = v_drift`:

| t (s) | `x[3:5]` (m/s) | \|x_vel\| | \|x_vel − v_true\| | \|p_EKF − p_true\| (m) |
|------:|---|---:|---:|---:|
| 0 | (1.902, −0.620, 0) | **2.000** | 2.000 | 0 |
| 50 | (1.087, −1.181, 0) | 1.605 | 1.605 | 86 |
| 100 | (0.909, −1.313, 0) | 1.597 | 1.597 | 163 |
| 200 | (0.976, −1.245, 0) | 1.582 | 1.582 | 319 |
| 400 | (1.071, −1.086, 0) | 1.525 | 1.525 | 621 |
| 600 | (1.120, −0.920, 0) | **1.450** | 1.450 | **898** |

True `v_i − v_j = (0,0,0)` at every sample. True `p_ij` is
frozen at (−2295, −1431, 17) m, |p|=2705 m (uniform drift).

**`x[3:5]` does not converge to truth.** After 600 s the speed
error is still 1.45 m/s (27% below the 2.00 m/s start, then
almost flat after t=50). The vector rotates; `v_z` stays 0
(unobservable from horizontal-range SNR, and luckily true).

What *is* weakly observed is **range**, not the 3-D velocity
vector. Horizontal range of the EKF pose locks at ~2674 m
versus the true 2705 m (31 m bias) from t=100 onward. The
remaining ~1.45 m/s is mostly **tangential**: the filter walks
the position around a constant-range circle
(|p_err| grows at ≈1.5 m/s × t → 898 m at 600 s) while keeping
predicted SNR within a few 0.01 dB of the measurement.

P₄₄ “turning over” in Step 33 was **uncertainty**, not the
state going to zero. Using `x[3:5]` in `c_drift` would replace
the 1.28 m/s ZOH phantom with a ~1.45 m/s EKF phantom that
slowly wanders. That is not a self-correcting internal signal.

---

## STEP 36 — `dSNR/drange` at this operating point

January Bellhop grid, finite difference
`(SNR(r+10 m) − SNR(r)) / 10`, receiver depth = node 2 acoustic
z = 202.8 m. True horizontal range of (1,2) is **constant**
2705.2 m (frozen geometry).

| t (s) | rangeH true (m) | rangeH EKF (m) | SNR meas (dB) | SNR pred x₆ (dB) | dSNR/dr (dB/m) | \|dSNR/dr\|×2 m (dB) |
|------:|---:|---:|---:|---:|---:|---:|
| 0 | 2705.2 | 2705.2 | 29.680 | 29.680 | **0.06032** | **0.121** |
| 50 | 2705.2 | 2671.9 | 29.680 | 29.827 | 0.06032 | 0.121 |
| 100 | 2705.2 | 2674.2 | 29.680 | 29.675 | 0.06032 | 0.121 |
| 200 | 2705.2 | 2674.2 | 29.680 | 29.675 | 0.06032 | 0.121 |
| 400 | 2705.2 | 2674.2 | 29.680 | 29.675 | 0.06032 | 0.121 |
| 600 | 2705.2 | 2674.2 | 29.680 | 29.676 | 0.06032 | 0.121 |

One-step false-ZOH range slip:

- worst-case 2 m × 0.06032 dB/m = **0.121 dB**
- using |x_vel|·1 s: 0.087–0.121 dB

**ε₀ = 4 dB. 0.121 dB is 33× smaller.** The “2 m of drift is
invisible” hypothesis is quantitative, not qualitative. After
the first SNR update, `epsilon_k` itself is ~6.37 dB
(`ε₀ + λ√S_k`), so the gap is even larger.

---

## STEP 37 — `e_k` on pair (1,2), t = 0 … 600 s (601 samples)

| | |
|---|---|
| min / max | −0.368 / +0.307 dB |
| mean / std | −0.0037 / 0.078 dB |
| max \|e_k\| | **0.368 dB** |
| \|e_k\| ≥ 4 dB | **0** |
| \|e_k\| ≥ ε_k | **0** |
| max consecutive exceed | **0** |
| Broadcast_k=1 samples | **0** |

Five largest |e_k|, all in a single early transient:

| t (s) | \|e_k\| (dB) |
|------:|---:|
| 35 | 0.368 |
| 36 | 0.367 |
| 34 | 0.366 |
| 37 | 0.364 |
| 33 | 0.361 |

Then |e_k| falls to ~0.2 dB by t=50 and to ~0.006 dB by t=500.
`epsilon_k` sits at 4.0 (t=0) then ~6.37 dB. Persistence
(W=5, ρ=0.6 ⇒ 3/5 exceedances) never has a single exceedance
to count.

**`e_k` stays uniformly small.** This is not “spikes that get
reset before persistence accumulates.” The trigger is behaving
as designed: per-step channel-prediction error from the wrong
velocity never approaches the threshold, because the SNR
update every 1 s wipes a 0.12 dB residual.

The full 1 Hz series is in `scenario-ii-elqtp-ekf-35.txt`
under `STEP37_E_K_SERIES`.

---

## Decision (do not implement either direction this step)

The user’s two-way split, answered from the numbers:

**`x[3:5]` does *not* meaningfully converge.** A 27% drop from
2.00 to 1.45 m/s over 600 s, with an 898 m tangential position
walk, is not a usable estimate of the true (0,0,0) relative
velocity. A scalar SNR measurement at 0.06 dB/m cannot pin down
a 3-D velocity, especially the component tangent to the range
circle. The chicken-and-egg stands:

- the trigger watches channel-prediction error, which stays
  < 0.4 dB because corrections are frequent and the grid is
  shallow (0.12 dB per 2 m);
- `c_drift` waits for a broadcast that this trigger will never
  fire, and even the EKF’s private `x[3:5]` stays ~1.5 m/s wrong.

Therefore:

1. **Do not switch `c_drift` onto `x[3:5]`.** That would still
   feed a ~1.45 m/s fabricated AUV–AUV signal. Not a principled
   fix on this evidence.
2. **The Step 34 gate (unheard pair → `c_drift = c_del`) is the
   correct permanent behavior for frozen-geometry runs**, not a
   stopgap. Scenario II should be written as: *`c_drift` provides
   no AUV–AUV signal under uniform co-moving drift, by the
   physics of the scenario (and by an estimator that only
   observes SNR), not by an implementation bug in the trigger.*
3. **Scenario III is the first real test** of whether the
   EKF / trigger / ZOH chain works at all. That is the first
   place innovations have a non-frozen reason to exist. The
   same unheard-zero ZOH will sit under any genuine
   relative-motion signal until the first HELLO; III is where
   that HELLO might actually occur.

No SPEC 2.1 / 2.4 rewrite. No Scenario III in this step.
