# Steps 2–4: received-only z_k, multi-hop geometry, full rerun (2026-09-30)

Build: NS-3.41 (GitHub mirror, tag `ns-3.41`), Aqua-Sim-NG `0fbc166`, `elqtp` from the
supplied tarball. Baseline before any change: `step1_campaign.py` output is byte-identical
to `results/step1c_rerun/step1_campaign.csv`. Seeds 20260921–25, N=40, boundary=remove,
β1=β2=0 throughout. Manuscript files were not edited.

## Step 2 — received-only z_k

**Before.** `ElqtpProtocol::tick()` called `linkSample(i,j)` for all 40×39 pairs every
second and passed the result straight to `updatePair`. That fed the median filter, the
Kalman correction and the trigger innovation from ground truth, whether or not anything
had been received. SPEC Part 2.3 (Step 41) describes this design.

**After** (`patches/step2-received-only-zk.patch`):

- `noteReception(rx, tx)` accepts a reception only if
  `ChannelGate::receptionOk(linkSample(tx, rx))` passes. This is the same condition the
  data path uses: a valid sample, not near pressure release, and SNR ≥ 8.68 dB. On success
  it stores `z_k` sampled at that moment and sets `rxPending`.
- Transmissions that generate receptions:
  - event HELLO: the rising edge of `Broadcast_k` makes j broadcast
  - periodic HELLO
  - energy beacon
  - one-time bootstrap HELLO (j→i)
  - delivered data hop j→nh: harness `Forward()` → `noteDataReception`
- In `tick()`, both tracks always predict with `F_k`; that code is unchanged.
  `updatePair(i,j,z_k)` runs only if a reception from j is pending. Otherwise there is no
  correction and no new trigger sample, and `Broadcast_k=0`, the same handling the code
  already used for an out-of-envelope (NaN) measurement.
- Not changed: `F_k`, `applyPredict`, the persistence/threshold logic
  (`recomputeBroadcast`, `triggerEpsilon`), and the reward terms.

**Grep confirmation.**

- `updatePair(` has a single call site, `elqtp-protocol.cc:1037`, and it runs only under
  `if (s.rxPending)`.
- `zRxPending` is written only at `:228`, inside `noteReceptionImpl` after the
  `receptionOk` check. It is cleared at `:1035`.
- `tick()` contains no `linkSample` or `queryLink` call.

**Unit checks.** `lqarp-unit-check` PASS=46 FAIL=0; `bellhop-data-loader-check` PASS=11 FAIL=0.

- Test 23c failed after the change. Node 1 never transmits, yet the test expected node 0's
  trigger to fire; it passed only because of the oracle feed. It now registers one decoded
  packet from node 1 per tick, and its assertion is unchanged. (The first run's failure
  output is in the session log; it is not saved as a file here.)
- New test 23c′: with no packets from node 1, 12 ticks produce 0 receptions, 0 z updates,
  no fire and no pose write.

**Pre-existing oracle paths left in place** (out of scope for this task):

- `initEkf` seeds `x` from true pose/SNR at t=0.
- `c_lin`/`c_pred` in the reward read `linkSample` live. Inert at β=0.
- `emitPeriodicControl` writes the HELLO hold into every (i,j) pair network-wide,
  regardless of reception.
- `ingestBroadcastVelocity` copies the true pose.
- `z_k` keeps the EKF's (rx,tx) argument order (the i→j table depth), while the reception
  gate uses tx→rx. This is a reciprocity assumption carried over from the existing
  measurement model.

## Step 3 — multi-hop geometry

**Knob changed:** `r_range` only, for every protocol, via the new `--rRange` flag. Field
(6 km × 6 km × 500 m), N=40, SNR gate and eddy are unchanged. Enlarging the field was not
chosen because it would push links past the 6 km Bellhop grid and move the eddy geometry.

- **Old:** r_range = R* = 5125 m (`rangeAtSnrThreshold`). The farthest node is ≈4.24 km
  from the sink, so every node was one hop away.
- **New:** r_range = **2500 m**.

**Measurement.** LQARP, five seeds, a census of every live AUV every 60 s
(`scripts/geo_census.py` → `step3_geometry/census.md`). "Routing graph" is the protocol's
live filter, which is depth-progressive. "Range graph" is N_range ∩ N_SNR only.

| Scenario | r_range | ≥2 hops (range graph) | routing graph 1 / 2 / 3+ / no depth-progressive path | LQARP PDR |
|---|---:|---:|---|---:|
| I | 5125 (R*) | 0.0% | 100 / 0 / 0 / 0 % | 1.0000 |
| I | **2500** | **44.0%** | 56.0 / 32.5 / 1.5 / 10.0 % | 0.9950 |
| II @ 2 m/s | 5125 (R*) | 0.0% | 100 / 0 / 0 / 0 % | 1.0000 |
| II @ 2 m/s | **2500** | **38.5%** | 61.5 / 30.2 / 0.4 / 7.9 % | 0.9788 |

Other values tried: 3000 (19% / 15.5%), 2800 (30% / 25.4%), 2200 (55.5% / 52.7%, but II
PDR 0.919), 2000 (60.5%, II PDR 0.883). With the census off, runs are byte-identical to
runs without the new flags.

## Step 4 — outputs

- Campaign (LQARP / E-LQTP / Fixed-Periodic / RLOR): `results/step4_final/campaign/step1_campaign.csv`.
  100/100 jobs; every row has r_range = 2500.
- elqtp-energy (32-bit beacon) and the Fixed-Periodic T_ctrl sweep (5/10/20/40/60 s):
  `results/step4_final/tctrl_sweep/tctrl_sweep.csv`. 210/210 jobs.
- Control, elqtp-energy with the position/SNR trigger off (`--epsilon_0=1e12`):
  `results/step4_final/trigger_off/trigger_off.csv`. 35/35 jobs.
- vs manuscript Tables II–V: `results/step4_final/COMPARISON.md`. 85 cells are outside the
  published mean ± s.d. (18 / 17 / 33 / 17).
- Every CSV now has `O_ene_byte_per_s` and `O_total_byte_per_s` columns. O_total is the
  headline figure in the tables below.

### E-LQTP variants vs Fixed-Periodic across T_ctrl (five-seed means)

| Case | Variant | PDR | Hops | T_e2e (s) | **O_total** (B/s) |
|---|---|---:|---:|---:|---:|
| II 2 m/s | LQARP | 0.9788 | 5.16 | 7.44 | 0 |
| | E-LQTP (no beacon) | 0.9788 | 5.09 | 7.34 | 59.7 |
| | E-LQTP+energy | 0.9978 | 1.66 | 2.45 | **186.0** |
| | E-LQTP+energy, trigger OFF | 0.9967 | 1.66 | 2.44 | **98.8** |
| | Periodic T=5 / 10 / 20 / 40 / 60 | 0.995 / 0.994 / 0.992 / 0.993 / 0.990 | 3.45 – 3.98 | 5.19 – 5.95 | 413.4 / 208.4 / 105.9 / 54.7 / **37.6** |
| II 3.5 m/s | E-LQTP (no beacon) | 0.9360 | 4.76 | 6.66 | 67.0 |
| | E-LQTP+energy | 0.9560 | 1.68 | 2.42 | 294.4 |
| | E-LQTP+energy, trigger OFF | 0.9571 | 1.68 | 2.42 | 104.7 |
| | Periodic T=5 … 60 | 0.993 … 0.988 | 3.29 – 3.61 | 4.95 – 5.40 | 413.4 … 37.6 |
| III | E-LQTP (no beacon) | 0.9903 | 5.00 | 7.07 | 63.6 |
| | E-LQTP+energy | 0.9978 | 1.65 | 2.45 | 229.9 |
| | E-LQTP+energy, trigger OFF | 0.9978 | 1.66 | 2.45 | 100.8 |
| | Periodic T=5 … 60 | 0.995 … 0.997 | 3.16 – 4.00 | 4.66 – 5.83 | 413.4 … 37.6 |

The full per-case table covers Scenario I and all drift speeds; see the CSVs.
E-LQTP+energy's O_total is 108–294 B/s across Scenarios II/III. Periodic breaks even with
it at T_ctrl ≈ 7–19 s, and at every T ≥ 20 s it costs less.

Trigger activity with received-only z_k (event HELLOs per run, five-seed mean):

| Case | E-LQTP (no beacon) | E-LQTP+energy |
|---|---:|---:|
| II 0.5 m/s | 0 | 147 |
| II 2 m/s | 26 | 1068 |
| II 3.5 m/s | 77 | 2359 |
| III | 46 | 1565 |

Without the beacon, a silent neighbor produces no measurements, so its trigger never
fires; the trigger needs other traffic to run.

## Verdict

**(a) Multi-hop routing that depends on the staleness/trigger mechanism: NO.**

The geometry is now genuinely multi-hop. 38–44% of nodes need ≥2 hops, and protocols
route 1.6–5.2 hops on average. But the event trigger does not drive routing outcomes:

- Plain E-LQTP barely fires under received-only z_k (26 HELLOs/run at 2 m/s), and its
  results track LQARP.
- In E-LQTP+energy, switching the position/SNR trigger off changes PDR, hops and delay
  only within seed noise, in every scenario and at every drift speed. It removes 11–64% of
  the total overhead (11% at 0.5 m/s, where the trigger rarely fires; 47–64% from 2 m/s up).
- The shorter routes (1.66 vs 3.2–5.2 hops) come from the energy beacon interacting with
  the inherited LQARP reward (the c_nei/c_ene lock-in from Step 1d), not from tracking
  topology staleness.

**(b) Total-overhead advantage over a fairly tuned periodic baseline: NO.**

- Periodic at T_ctrl = 40–60 s costs 37.6–54.7 B/s with PDR 0.987–0.997 in every mobile
  case.
- E-LQTP+energy costs 108–294 B/s, 2–8× more, with PDR that is equal within noise, or
  worse at 3.0–3.5 m/s (0.956 vs 0.988 at 3.5 m/s).
- Plain E-LQTP (55–67 B/s) is also costlier than Periodic at T=60 s, and its PDR is lower
  at high drift (0.936 vs 0.988).
- The one real advantage E-LQTP+energy has over Periodic is path length and delay (about
  2.4 s vs 5–6 s). The trigger-off control gets that same delay for about 100 B/s, so the
  trigger isn't what produces it. It has not yet been explained why Periodic, whose full
  HELLOs also refresh energy, routes longer. One untouched asymmetry is a candidate:
  Periodic HELLOs write every pair network-wide without a reception check. That needs a
  diagnosis before any delay claim goes into the paper.
