# Steps 33–34: ZOH initialization, staleness, and the unheard `c_drift` gate

Same run as Step 32: seed 20260921, N=40, ||v_drift||=2.0 m/s,
azimuth 5.968 rad (341.95°), v_drift=(1.902, −0.620, 0) m/s,
T_sim=600 s + 120 s drain, `--boundary=remove`, β₁=β₂=1.0,
ε₀=4, W=5, W_mp=3, ρ=0.6, λ=1, dt=1 s. Scenario III is not
implemented.

Raw log: `results/scenario-ii-elqtp-zoh-600.txt`.

Unit checks: **PASS=30 FAIL=0** (6c added: co-moving unheard
`c_drift=c_del`; 14a updated for the same gate).

---

## STEP 33.1 — What is `pdot_j` before the first broadcast?

**Explicit zero, not uninitialized garbage.**

`NeighborEkf::initEkf` stores

```
vx_j_zoh = vy_j_zoh = vz_j_zoh = 0
zohHeard = false
lastZohTime = NaN
```

and sets the EKF velocity state to own odometry minus that zero
(`x[3:5] = v_i − 0`). SPEC 2.1: `pdot_j` is the last received
broadcast; none exists yet. The zeros are a stored placeholder,
not a physical claim.

A candidate relationship **does** exist before any HELLO. At t=0
the geometry filters already produce a nonempty I (40/40 AUVs have
the sink in I; representative AUV–AUV pair in I is (1,2)).

Representative pair **(i,j)=(1,2)** at t=0, before any tick:

| quantity | value |
|---|---|
| `zohHeard` | false |
| `pdot_j` ZOH | **(0, 0, 0)** |
| `v_i` (true, = v_drift) | (1.902, −0.620, 0) |
| `v_j` true | (1.902, −0.620, 0) identical |
| protocol `v_rel` | **−1.286 m/s** |
| EKF P vel diag (P33, P44, P55) | (1, 1, 1) |

`v_rel = (v_i − 0) · p̂_ij`. Under uniform drift that is the
projection of the common current onto the pair axis — the Step 32
phantom. Physical AUV–AUV `v_rel` is identically 0
(`max_AUV_AUV_pairwise_distance_change = 3.2×10⁻¹⁰ m`).

**What `c_drift` uses at that moment (after the Step 34 gate):**
`c_drift = c_del` (β₂ omitted). It does not consume the fabricated
zero-velocity `v_rel`.

---

## STEP 33.2 — Time gap / staleness at reward evaluation

Reward-eval diagnostic (every candidate in I / detour set at
`learnFrom`, same path as Step 32):

| | all evals | AUV–AUV | to-sink |
|---|---:|---:|---:|
| count | 26207 | 24584 (94%) | 1623 |
| **heard** | **0** | **0** | **0** |
| unheard | 26207 | 24584 | 1623 |
| mean \|v_rel\| (m/s) | 1.276 | **1.278** | 1.251 |
| frac \|v_rel\| > 0.01 | 99.89% | 99.89% | 99.88% |

**ZOH staleness histogram at reward eval: n = 0.** No pair used
for a forwarding reward had ever received a HELLO. Every `c_drift`
on this path was the β₂=0 case (`c_del`).

End-of-run census (all directed pairs, including dead nodes),
t=721 s:

| | |
|---|---|
| pairs | 1640 (41×40) |
| ever heard | 96 |
| heard AUV–AUV | 95 |
| **heard alive–alive AUV–AUV** | **0 / 552** |
| heard (i, sink) | 0 |
| Broadcast_k=1 at end | 61 |
| lastZohTime among the 96 | min 414 s, mean 700 s, max 720 s |
| example heard pair | (0, 35) = sink observing an AUV |

Broadcasts that do fire (`Broadcast_k` ones=7550, rising=372) are
**envelope-exit artifacts**: a removed AUV is velocity-zeroed, so
a still-drifting neighbor sees a sudden relative-motion SNR
innovation. They are not HELLOs on the live co-moving graph.
Alive AUV–AUV geometry is frozen, SNR is constant, and the
persistence trigger (`ε₀=4`, W=5, ρ=0.6) never trips.

Representative forwarding pair (1,2): `Broadcast_k=0` and
`zohHeard=false` at every sample from t=0 through t=700 s.
Inter-broadcast gap = **never / infinite**. `v_rel` stuck at
−1.286 m/s the entire run.

### FLAG — sensitivity, not a silent patch

Broadcast gaps on the pairs that enter `c_drift` are not “a few
seconds of ZOH hold.” They are **the whole simulation**. At this
drift magnitude relative velocity among live AUVs does not change
at all, so a stale ZOH of an *honest* `v_j = v_drift` would still
be exact — but that honest value is never received.

Whether `ε₀ / W / ρ` should fire more often on AUV–sink SNR drift
(the only live relative-motion signal in Scenario II) is a
**tuning question**. It is not patched here. Silently lowering
`ε₀` would mix more control traffic into a scenario whose
AUV–AUV `v_rel` is physically zero, and would make Scenario III
harder to read.

---

## STEP 33.3 — Does P’s velocity block grow with staleness?

Reported values are **P_{k|k} after the SNR update** that runs
every dt=1 s with H = [0 … 0 1]. A ZOH copy is **not** an EKF
velocity measurement. P_{k|k-1} velocity is P_{k-1|k-1} + qVel
(F_vel = I) before that SNR update.

Pair (1,2), no ZOH update at any time:

| t (s) | P33 (vx) | P44 (vy) | P55 (vz) | \|P_vel\|_F-diag | `v_rel` |
|------:|---------:|---------:|---------:|-----------------:|--------:|
| 0 | 1.00 | 1.00 | 1.00 | 1.73 | −1.286 |
| 1 | 1.10 | 1.10 | 1.10 | 1.91 | −1.286 |
| 2 | 1.20 | 1.20 | 1.20 | 2.08 | −1.286 |
| 5 | 1.50 | 1.50 | 1.50 | 2.60 | −1.286 |
| 10 | 1.99 | 2.00 | 2.00 | 3.46 | −1.286 |
| 50 | 3.05 | 4.68 | 6.00 | 8.20 | −1.286 |
| 100 | 5.07 | 7.79 | 11.00 | 14.4 | −1.286 |
| 200 | 10.2 | 12.6 | 21.00 | 26.5 | −1.286 |
| 600 | 42.8 | 17.0 | 61.00 | 76.4 | −1.286 |
| 700 | 52.5 | 15.9 | 71.00 | 89.7 | −1.286 |

**Not frozen.** P55 = 1 + 0.1·t exactly (qVel=0.1 / s, no SNR–z
coupling: Bellhop SNR is a function of horizontal range). P33/P44
grow more slowly and P44 even turns over after ~500 s — the SNR
update *does* pull the horizontal velocity block through the
range Jacobian.

**Underestimated as a ZOH-staleness clock.** Init P_vel=1
(σ≈1 m/s) against a 2 m/s fabricated relative-velocity error.
P does not know that `pdot_j` is a ZOH; it only sees process
noise plus an SNR measurement of predicted vs true range. The
EKF state `x[3:5]` is not what `c_drift` uses (`c_drift` uses
odometry − ZOH). Growing P does not bound the phantom `v_rel`.

---

## STEP 34 — Gate: unheard pair ⇒ `c_drift = c_del`

Until i has received at least one broadcast from j, `c_drift`
returns `c_del` (SPEC 2.1 / 2.7). No fabricated `pdot_j = 0`.

### How much of the 1.28 m/s bias does this remove?

**All of it, on the quantity `c_drift` actually consumes.**

| | Step 32 (ungated) | Step 34 (gated) |
|---|---:|---:|
| AUV–AUV evals | 23937 | 24584 |
| AUV–AUV heard | (not split) | **0** |
| AUV–AUV unheard fraction | ~1 (inferred) | **1.000** |
| AUV–AUV mean \|v_rel\| (raw) | 1.279 | **1.278** |
| AUV–AUV mean \|v_rel\| entering β₂ | 1.279 | **none (β₂ off)** |
| bias removed from `c_drift` | 0 | **1.278 m/s (100%)** |

Raw `v_rel` at reward eval **does not drop toward 0**. The
phantom is not a brief t=0 cold start that a later HELLO
corrects. Live forwarding pairs never hear, so ZOH stays at 0
for 600 s and `v_rel` stays ~1.28 m/s. The gate is what stops
that number from scaling `c_del`.

If a co-moving pair *did* hear once, ZOH would copy `v_j = v_drift`
and AUV–AUV `v_rel` would be 0 forever after (constant velocity).
This run cannot show that collapse: **0/552 live AUV–AUV pairs
ever heard**.

### Routing consequence of the gate

With β₂ inactive, E-LQTP’s delay factor matches LQARP’s `c_del`.
Remaining E-LQTP vs LQARP difference is `c_pred` (β₁) and N_stab.

| metric | LQARP 600 s | E-LQTP 600 s (Step 32, ungated) | E-LQTP 600 s (Step 34, gated) |
|---|---:|---:|---:|
| PDR | 1.000 | 0.9970 | 0.9970 |
| mean hops | 2.121 | 2.339 | 2.429 |
| T_e2e (s) | 4.455 | 5.027 | 5.170 |
| E_bit (J/bit) | 1.137×10⁻² | 1.255×10⁻² | 1.304×10⁻² |
| O_ctrl (byte/s) | 0 | 374 | 358 |
| N_tx | — | 1562 | 1623 |
| Broadcast_k rising | 0 | 377 | 372 |
| LOST_NODE_EXIT | 0 | 2 | 2 |

PDR unchanged (still the two in-flight envelope losses). Hops /
T_e2e / E_bit move slightly because phantom `v_rel` no longer
re-ranks AUV relays.

---

## Verdict

1. `pdot_j` cold-starts at **written zero**. New candidates in I
   use that zero for raw `v_rel`; `c_drift` now refuses it.
2. On the forwarding graph, staleness is not a gap distribution —
   it is **no HELLO at all** (0 heard evals; 0/552 live AUV–AUV
   heard at t=721 s). FLAG `ε₀/W/ρ`; do not retune here.
3. EKF P velocity **grows** (P55 = 1+qVel·t; horizontal block
   SNR-coupled) but is **not** a ZOH-staleness clock. SNR updates
   every 1 s; ZOH is not an EKF measurement.
4. The Step 32 1.28 m/s mean is **100% an unheard / zero-ZOH
   artifact**. Gating `c_drift` removes all of it from the reward.
   Raw `v_rel` stays ~1.28 because the honest ZOH is never
   delivered to those pairs.

Scenario III remains blocked until this mechanism is treated as
part of the estimator, not as “Scenario II just has low signal.”
The same unheard-zero ZOH will sit under any genuine
relative-motion `v_rel` until the first HELLO, and live-pair HELLO
cadence at these `ε₀/W/ρ` defaults is not established.
