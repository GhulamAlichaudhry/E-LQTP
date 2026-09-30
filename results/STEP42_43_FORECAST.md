# Steps 42–43: Dual-track forecast trigger

No Scenario III. `epsilon_0` stays **4.0 dB**. W=5, ρ=0.6, λ=1.0
unchanged.

Same run as Steps 35–41: seed 20260921, N=40, ||v_drift||=2.0 m/s,
azimuth 5.968 rad, T_sim=600 s, `--boundary=remove`, β₁=β₂=1,
dt=1 s. Pair **(1,2)**. True AUV–AUV `v_rel = 0` (uniform co-moving
drift). ZOH cold-start is still `(0,0,0)`, so the forecast is
initialized with `x[3:5] = v_drift` (2 m/s).

Raw log: `results/scenario-ii-elqtp-forecast-42.txt`.

Unit suite: **PASS=30 FAIL=0**.

---

## What changed (Step 42)

SPEC.md Parts 2.2 / 2.3 addenda were appended verbatim.

Each neighbor pair now keeps two tracks:

1. **Corrected** `x_hat_{k|k}` / `P_{k|k}` — the existing EKF
   predict/update. `c_pred`, N_stab’s `|e_k|`, and every previous
   consumer of `x_hat` are unchanged.
2. **Open-loop** `x_forecast` / `P_forecast` — same `F_k`/`Q_k`
   predict, **never** an update. Reset to `x_hat_{k|k}` / `P_{k|k}`
   only when `zohHeard` becomes fresh (`Broadcast_k=1`, periodic
   HELLO, or the test ZOH seam).

Trigger source (Part 2.4 form unchanged):

```
e_k^{trigger} = z_k − h(x_forecast_k)
epsilon_k     = epsilon_0 + λ √S_k ,   S_k = P_forecast[6,6] + R
```

`z_k` is still the per-tick ground-truth Bellhop query.

---

## STEP 42 — `x_forecast` vs `x_hat` on pair (1,2)

`x_forecast` velocity stays at the false ZOH init
`(1.902, −0.620, 0)` m/s for the whole 600 s (no HELLO on this
pair, so no reset). Position error is therefore exactly
`|v_drift| · t = 2t` metres.

| t (s) | \|p_fc − p_true\| (m) | \|p_hat − p_true\| (m) | \|r_fc − r_true\| (m) | \|r_hat − r_true\| (m) |
|------:|----------------------:|-----------------------:|----------------------:|-----------------------:|
| 0 | **0** | 0 | 0 | 0 |
| 50 | **100** | 86 | 63 | 33 |
| 100 | **200** | 163 | 124 | **31** |
| 200 | **400** | 319 | 238 | 31 |
| 400 | **800** | 621 | 430 | 31 |
| 600 | **1200** | 898 | **564** | 31 |

`x_hat` range still locks at ~2674 m vs true 2705 m (the Step 35
radial heal). `x_forecast` range walks 2705 → 2141 m and is
**never** pulled back. That is the dual-track split working:
the Kalman track is still measurement-corrected; the forecast
is pure dead-reckoning on the wrong 2 m/s ZOH.

`x_hat`’s own `e_k` series is the same as Step 37 (max
**0.368 dB**, never an exceedance). The old one-step path is
untouched.

---

## STEP 43 — `e_k^{trigger}` on pair (1,2)

601 samples, t = 0 … 600 s.

| | Kalman `e_k` (unchanged) | `e_k^{trigger}` (new) |
|---|---:|---:|
| min / max (dB) | −0.368 / +0.307 | **−3.613 / +0.851** |
| mean / std (dB) | −0.0037 / 0.078 | **−1.861 / 1.297** |
| max \|·\| (dB) | **0.368** | **3.613** |
| \|·\| ≥ 4 dB | 0 | **0** |
| \|·\| ≥ ε | 0 | **0** |
| Broadcast_k=1 samples | 0 | **0** |
| first rising edge | — | **none** |

Five largest `|e_trigger|`:

| t (s) | \|e_trigger\| (dB) | ε_trigger (dB) |
|------:|---:|---:|
| 600 | 3.613 | 23.3 |
| 216 | 3.610 | 31.6 |
| 599 | 3.609 | — |
| 598 | 3.606 | — |
| 597 | 3.602 | — |

Growth vs the Step 40 linear estimate (`~0.06 dB/m × 1.286 m/s
≈ 0.077 dB/s`):

| t (s) | e_trigger (dB) | ε_trigger (dB) | \|r_fc − r_true\| (m) | Kalman e_k (dB) |
|------:|---:|---:|---:|---:|
| 0 | 0.00 | 4.00 | 0 | 0.00 |
| 20 | +0.11 | 6.34 | 26 | +0.10 |
| 40 | −1.53 | 6.72 | 51 | −0.34 |
| 50 | −1.01 | 11.5 | 63 | −0.21 |
| 100 | +0.47 | 7.19 | 124 | +0.007 |
| 150 | −2.71 | 9.05 | 182 | +0.007 |
| 200 | −3.40 | 17.1 | 238 | +0.007 |
| 216 | **−3.61** | 31.6 | 255 | +0.007 |
| 400 | −2.31 | 19.0 | 430 | +0.007 |
| 600 | **−3.61** | 23.3 | 564 | +0.006 |

`e_k^{trigger}` is **no longer pinned under 0.4 dB**. It reaches
the few-dB band in the 40–200 s window, as Step 40’s accumulated-
divergence table said it should once the one-step wipe is
removed. It does **not** keep climbing at 0.077 dB/s out to
600 s: the January SNR field is not a constant 0.06 dB/m slope
over hundreds of metres (interference lobes), so `|SNR(r_true) −
SNR(r_forecast)|` saturates near **3.6 dB** even as range error
grows to 564 m.

`epsilon_k` computed from `P_forecast` grows without an update
(`S` from 4 to hundreds; ε from 4 to 6–32 dB, with a spike to
58.8 dB at t=180 when `|dSNR/dr|` and `P_pos` line up). That
threshold is always above the 3.6 dB peak on this pair.

---

## Does Broadcast_k fire on pair (1,2)?

**No.** Zero exceedances of `epsilon_trigger`, so the
persistence gate (3/5) never has a vote. First rising edge:
none.

This is **not** a return of the Step 41 structural wipe. The
innovation now measures the real ZOH-init error. The remaining
block on this pair is the **threshold**:

- the grid SNR difference for this geometry tops out at 3.61 dB,
  just under `epsilon_0 = 4.0`;
- `P_forecast` process-noise growth then inflates ε further.

`epsilon_0` was left at 4.0 on purpose (Step 39/40 still apply
to this quantity; retune is a later step).

---

## Point 4 — is a fire here a bug?

The init is a **real** staleness case: ZOH = 0, truth relative
velocity = 0, but the forecast is started at `v_drift = 2 m/s`
because no HELLO has ever arrived. Catching that is correct
behavior, not a phantom.

On pair (1,2) the gate does not trip, so this particular pair
does not give that confirmation. The **same run** does fire
elsewhere on the same class of error:

| | Steps 33–41 (old `e_k`) | Step 43 (dual-track) |
|---|---:|---:|
| Broadcast_k rising (network) | envelope-exit artifacts only; live AUV–AUV heard = **0/552** | **473** rising, **2489** ones |
| heard alive AUV–AUV at t=721 | **0 / 552** | **100 / 552** |
| pair (1,2) Broadcast_k | 0 | 0 |
| pair (1,2) max \|innovation\| | 0.368 dB | **3.613 dB** |

Those 100 heard AUV–AUV pairs are the ZOH-init error being
caught on geometries where `|e_trigger|` does clear
`epsilon_k`. After a HELLO, heard `|v_rel|` is identically 0
(honest ZOH), so the fires are not inventing a relative
velocity that is not there.

---

## What this does *not* do

- No Scenario III / Gauss-Markov mobility.
- No `epsilon_0` change.
- No change to the Kalman update, `c_pred`’s `e_k`, or N_stab’s
  use of the Kalman pair (test 7 still drives both seams).
- Forecast velocity is still the EKF’s `x[3:5]` at the last
  reset (init, here). A later step may want the reset to ingest
  the newly received ZOH into the forecast velocity; that is
  not in this change.
