# Steps 44–45: Saturation ceilings and the P_forecast / ε_k problem

No `epsilon_0` change. No `P_forecast` cap implemented. No Scenario III.

Same run as Steps 42–43: seed 20260921, N=40, ||v_drift||=2.0 m/s,
T_sim=600 s, `--boundary=remove`, β₁=β₂=1, ε₀=4, W=5, ρ=0.6, λ=1.
Snapshot is at **T_sim** (not drain). Unit suite **PASS=30 FAIL=0**.

Raw log: `results/scenario-ii-elqtp-sat-44.txt`.

At t=600 s: 27 AUVs still alive → **702** directed live AUV–AUV pairs
(27×26). Of those, **100 heard**, **602 never heard** (the
pair-(1,2) class). Pair (1,2) itself: max |e_trigger|=**3.613 dB**,
never heard.

---

## STEP 44 — saturation ceiling of max |e_k^{trigger}|

Each pair’s number is its **unheard-window** max |e_k^{trigger}|
(the ceiling reached while ZOH-init error is the only motion
signal; the firing tick is included for pairs that do fire).

### Primary set: live AUV–AUV, never a HELLO (n = 602)

| | max \|e_trigger\| (dB) | max ε_trigger (dB) |
|---|---:|---:|
| min | 0.00 | 4.00 |
| p25 | **3.99** | **42.7** |
| median | **6.44** | **170.6** |
| p75 | **8.88** | **327.0** |
| p80 | 9.61 | 353.5 |
| max | 30.77 | 828.0 |
| mean | 6.75 | 195.5 |

Fraction of these 602 pairs whose ceiling is at least:

| threshold (dB) | 1.5 | 2.0 | 2.5 | 3.0 | 3.6 | 4.0 |
|---|---:|---:|---:|---:|---:|---:|
| fraction | 0.962 | 0.934 | 0.900 | 0.850 | 0.794 | **0.749** |

Pair (1,2)’s 3.61 dB is **below p25** — a low-ceiling geometry, not
the typical silent pair.

The typical silent pair *does* reach 6–9 dB. It stays silent
because `epsilon_k` from unbounded `P_forecast` is tens to hundreds
of dB (median **171 dB**). That is issue (2), not an unreachable
ε₀=4 on a 3.6 dB ceiling.

A few pairs at 0 dB are almost certainly out-of-envelope (NaN
`z_k`; 22 014 NaN measurements network-wide). They are a small
left tail, not the body of the distribution.

### Full ZOH-init class: all live AUV–AUV, unheard-window max (n = 702)

Every AUV–AUV pair starts with the same false-ZOH 2 m/s init.
This is the population “catch 70–80% of that error class” refers to.

| | max \|e_trigger\| (dB) |
|---|---:|
| min | 0.00 |
| p25 | **4.45** |
| median | **7.11** |
| p75 | **9.32** |
| p80 | 9.96 |
| max | 30.77 |
| mean | 7.13 |

| threshold (dB) | 1.5 | 2.0 | 2.5 | 3.0 | 3.6 | 4.0 |
|---|---:|---:|---:|---:|---:|---:|
| fraction | 0.967 | 0.943 | 0.915 | 0.872 | 0.823 | **0.785** |

### Pairs that *did* fire (n = 100, live, heard)

Unheard-window max |e_trigger|: min **6.37**, p25 7.69, median 8.78,
p75 10.25, max 27.5 dB. Every fire on this class cleared ~6 dB
*before* `P_forecast` finished running away. They are not a
different error — they won a race against a climbing threshold.

---

## What Step 44 says about ε₀=4

The earlier worry — “ε₀=4 is above the typical saturation ceiling”
— is true for the **lower tail** (pair (1,2) and ~25% of silent
pairs with ceiling < 4 dB). It is **false for the body**: 75% of
never-heard live pairs and 78% of all live pairs already reach
≥ 4.0 dB.

The reason 602/702 stay silent is not that 4 dB is unreachable.
It is that `epsilon_k = 4 + √S_forecast` has median **171 dB** on
those pairs. Lowering ε₀ to 2.0–2.5 **without** fixing that term
would still leave a ~170 dB hurdle. The retune is only meaningful
together with Step 45.

---

## STEP 45 — proposal (not implemented)

### Option A: freeze `P_forecast` after N seconds without a reset

Change the 2.2-addendum recursion:

```
if t − t_reset < T_p_cap:
    P_forecast_k = F_k P_forecast_{k-1} F_k^T + Q_k
else:
    P_forecast_k = P_forecast_{k-1}    # freeze
```

New design parameter `T_p_cap`. `epsilon_k` keeps its current
formula.

**Tradeoffs**

- `P_forecast` stops being open-loop process-noise accumulation
  after the freeze. Two pairs with the same frozen P are claimed
  to have the same uncertainty at t=N and t=10N.
- The freeze level depends on how large P already is at `T_p_cap`.
  On pair (1,2), ε was already 11.5 dB at t=50 and 17 dB at t=200.
  A 60 s cap would stabilize many pairs *above* a 4–6 dB
  innovation ceiling.
- Adds a time constant that has no existing SPEC home (W / W_mp
  are sample counts, not covariance ages).

### Option B: cap √S_k’s contribution to `epsilon_k`

Leave the `P_forecast` recursion exactly as written (honest
unbounded dead-reckoning covariance). Change only the trigger
threshold in the 2.3 / 2.4 addendum:

```
epsilon_k = epsilon_0 + λ * min(√S_k, s_cap)
```

First-pass `s_cap = √rMeas = 2.0` dB (the measurement-noise scale
the original `ε₀ ~ 2√rMeas` heuristic was built on). `P_forecast`
is still available if anything later wants a real uncertainty.

**Tradeoffs**

- `epsilon_k` is no longer a pure Mahalanobis / innovation-covariance
  gate once S exceeds `s_cap²`. It becomes a detection threshold
  on SNR mismatch plus a *bounded* allowance for forecast
  uncertainty.
- That is actually closer to the original SPEC intent: the
  `+ λ√S_k` term was written for a **Kalman-updated** S, which
  stays O(R). Transplanting the same formula onto an never-updated
  P is what created the backwards incentive.
- `e_k^{trigger}` saturates (Step 44). An unbounded competitor in
  the threshold is the wrong object. Option B makes the saturating
  statistic the one that decides.

### Which is the smaller SPEC change?

**Option B.** It is one inequality on the existing `epsilon_k`
line. Option A redefines the `P_forecast` process and introduces
`T_p_cap`.

Option A also changes the *meaning* of the covariance (it is no
longer “uncertainty if I have only dead-reckoned”). Option B
changes the *meaning* of `epsilon_k` (it is no longer a fully
covariance-tracking gate). Given that `epsilon_k` is a trigger
threshold and `P_forecast` is documented as predict-only
uncertainty, distorting the threshold is the localized fix;
distorting P is not.

**Recommendation: Option B**, `s_cap = √rMeas = 2.0` dB, λ
unchanged at 1.0.

---

## Proposed ε₀ (do not apply yet)

Conditional on Option B with `s_cap = 2.0`:

```
epsilon_k → epsilon_0 + min(√S_k, 2.0)
```

Late-time threshold = `epsilon_0 + 2.0`. Early-time threshold can
be lower (S small), which is the right incentive: a fresh
divergence is easier to declare, a long-silent pair is not
punished.

| epsilon_0 | late-time ε | all-live catch (n=702) | never-heard catch (n=602) | pair (1,2) |
|---:|---:|---:|---:|---|
| 2.0 | **4.0 dB** | **78.5%** | **74.9%** | miss (3.61) |
| 1.5 | 3.5 dB | ~82% (≥3.6 = 82.3%) | ~79% | **catch** |
| 2.5 | 4.5 dB | ~75% (p25 = 4.45) | ~70% | miss |

**Propose `epsilon_0 = 2.0` dB** with Option B / `s_cap = 2.0`.
That is the 70–80% contour of the full ZOH-init class (78.5% of
702 live pairs, 74.9% of the 602 currently silent ones). It is
the number the 4.0 dB saturation data already pointed at, once
the `+√S` term is prevented from running away.

`epsilon_0 = 1.5` is the alternative if the (1,2)-class lower
tail should be inside the majority, at the cost of more fires
on weaker SNR mismatches.

Without Option B, **do not lower ε₀**. It would not reach the
pairs whose hurdle is 171 dB.

---

## What this step did not do

- `epsilon_0` is still 4.0 in code and SPEC.
- `P_forecast` still grows without bound.
- No Scenario III / Gauss-Markov mobility.
- Calibration is for this frozen-geometry ZOH-init error only.
  Scenario III’s genuine `v_rel` will change the ceiling
  distribution; this number is the pre-III, known-ground-truth
  setting.
