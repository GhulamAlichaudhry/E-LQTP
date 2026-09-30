# Step 5: Periodic reception-gating audit and the hop-length anomaly (2026-09-30)

Everything below uses the same setup as Steps 2–4: received-only z_k, r_range = 2500 m,
seeds 20260921–25, N=40, β1=β2=0. Manuscript files were not edited.

## Task 1: is Fixed-Periodic's HELLO reception-gated?

**No.** `ElqtpProtocol::emitPeriodicControl` (`contrib/elqtp/model/elqtp-protocol.cc:893–913`,
pre-fix) loops over every (i, j) with i ≠ j and calls `ingestBroadcastVelocity` for
each (`:905`). It never checks range or SNR, so every node's hold for every other node
is refreshed network-wide on every round.

**This is an implementation gap, not an intended flood.** The evidence:

- SPEC Part 4 defines Fixed-Periodic only as replacing the event trigger with
  `Broadcast_k = 1` every T_ctrl, "isolat[ing] broadcast timing". SPEC Part 2.1 defines the
  hold as "the most recent value **received** from j's last control-packet broadcast".
- O_ctrl bills N packets per round (`eventHelloCount_ += nodes_.size()`, `:909`). That is
  one single-hop broadcast per node. A network-wide flood would cost up to N² relays.
  Delivery and billing therefore disagree.
- The function's own comment says "every *neighbor* ZOH-updates", but the code updates
  every *node*.

**A second ungated writer exists on the E-LQTP side.** `refreshEnergyOnly`, the energy
beacon (`:916–936`), refreshes `energy_j_zoh` for every pair that was heard once, also
network-wide. The E-LQTP event-HELLO ingest (`:870–873`) is gated only indirectly: it
runs inside `updatePair`, which since Step 2 needs a recent reception from j, but it
never checks that the HELLO itself arrives.

## A bigger bug found on the way: the 32-bit energy quantizer returns NaN

`quantizeEnergy` (`:956`, pre-fix) computes `levels = (1u << bits) − 1`.

- For `bits = 32`, shifting a 32-bit unsigned by 32 is undefined behavior. On x86 the
  shift count wraps, `levels` becomes 0, and the function returns 0/0 = NaN.
- A standalone copy of the expression reproduces this (`quantizer_repro.cc`): 8, 16, 24
  and 31 bits are correct, and 32 gives NaN.
- Effect on `elqtp-energy --energyBits=32`: after the first beacon, every held neighbor
  energy is NaN, and so are `c_ene`, `c_del`, R and Q. In the pre-fix decision trace for
  II @ 2 m/s, seed 20260921 (`pre_fix_decision_trace_summary.txt`), 3524 of 3524 non-zero
  relay rewards are NaN, and the sink's Q is NaN in 632 of 669 decisions.
- `nextHop` uses strict comparisons, which are always false with NaN, so the choice falls
  through to the lowest id in the set. That is the sink (id 0).

**Consequence.** Every PDR, hop and delay figure reported for the 32-bit E-LQTP+energy
design is an artifact of NaN plus the tie-break. That covers the project's
`step1-final-campaign-summary.md` (Step 1h), Step 1i, and Steps 2–4, including the
trigger-off control. The "hop-count fix" attributed to the 32-bit beacon in Step 1g/1h is
this artifact. Overhead accounting (O_ctrl, O_ene) and trigger HELLO counts are
unaffected, because the trigger does not read energy. The 8/16/17/18-bit results from
Step 1g do not hit this bug; I have not re-examined them.

## Fix (`patches/step5-quantizer-and-reception-gating.patch`)

1. **Quantizer:** `levels = std::ldexp(1.0, bits) − 1.0`, exact up to 53 bits. More than
   53 bits throws.
2. **Reception gating:** `ElqtpConfig::helloRxGate` (default true; CLI `--helloRxGate`) and
   `helloReaches(rx, tx) = ChannelGate::receptionOk(linkSample(tx, rx))`. This is the same
   condition as a data hop and as the Step 2 `noteReceptionImpl`. It is applied to all
   three hold writers:
   - the Periodic HELLO; a pair it does not reach also gets `broadcast_k = 0`, so its
     `lastZohTime` is not refreshed
   - the energy beacon
   - the E-LQTP event-HELLO ingest

   Setting `--helloRxGate=0` restores the old network-wide write, for A/B runs only.
3. **Tests:** `lqarp-unit-check` PASS=48 FAIL=0 (two new tests, 23e and 23f).
   `bellhop-data-loader-check` PASS=11 FAIL=0.
   - 23e: the quantizer is finite and within one step at 8/16/31/32 bits.
   - 23f: a Periodic HELLO writes the in-range neighbor and skips a node outside the SNR
     gate. With the gate off, the old network-wide write comes back.

## Reruns, staged so each fix can be attributed

- **Stage A, quantizer fix only (`--helloRxGate=0`).** The campaign CSV is byte-identical
  to Step 4, and the Periodic sweep rows are identical to Step 4, so the quantizer fix
  touches only energy-beacon runs.
- **Stage B, quantizer fix plus gating (default).** LQARP and RLOR rows are identical to
  Step 4.

In total there are 690 runs, all succeeded. Per-stage CSVs are under `A_quantfix_nogate/`
and `B_quantfix_gated/`, each with `campaign/`, `tctrl_sweep/` and `trigger_off/`. The
full stage-B table is in `B_quantfix_gated/summary_B.txt`.

Mean hops (five seeds): Step 4 (buggy) → A → B

| Case | E-LQTP+energy | trigger-OFF | Periodic T=5 | Periodic T=60 |
|---|---|---|---|---|
| I | 1.78 → 3.07 → 3.07 | 1.78 → 3.07 → 3.07 | 3.07 → 3.07 → 3.07 | 3.62 → 3.62 → 3.62 |
| II 0.5 | 1.73 → 3.34 → 3.34 | 1.73 → 3.35 → 3.35 | 3.28 → 3.28 → 3.28 | 4.56 → 4.56 → 4.21 |
| II 2.0 | 1.66 → 3.18 → 3.18 | 1.66 → 3.15 → 3.15 | 3.45 → 3.45 → 3.20 | 3.98 → 3.98 → 3.77 |
| II 3.5 | 1.68 → 3.06 → 3.06 | 1.68 → 3.02 → 3.02 | 3.29 → 3.29 → 3.10 | 3.56 → 3.56 → 3.50 |
| III | 1.65 → 3.07 → 3.07 | 1.65 → 3.02 → 3.02 | 3.16 → 3.16 → 3.16 | 4.00 → 4.00 → 4.03 |

**The hop anomaly was the NaN bug, not reception gating.** Once the quantizer is fixed,
E-LQTP+energy routes 3.0–3.3 hops, the same range as Periodic. In static Scenario I it is
identical to Periodic@5 s: both refresh energy every 5 s, and on a static field that is
all a HELLO carries. Gating the Periodic HELLO then shortens Periodic's paths slightly
(by up to 0.35 hops at low T) and raises its PDR at high drift, for example
0.9932 → 0.9965 at 3.5 m/s with T=5. With gating off, pairs that were out of range kept
their holds refreshed, which inflated neighbor counts and therefore `c_nei` (see below).

## What actually sets path length (stage B decision traces)

Traces cover II @ 2 m/s, five seeds, with `--decisionTrace`, which dumps each
candidate's Q, R, c_ene, c_del and c_nei at every decision. The runs are
non-perturbing (SWEEP lines are byte-identical to runs without the trace). Script:
`dec_analyze.py`; output: `B_quantfix_gated/decision_trace_summary.txt`.

| | Periodic T=5 | E-LQTP+energy, trigger OFF | LQARP |
|---|---:|---:|---:|
| Decisions with the sink in the candidate set | 7319 | 7042 | 13934 |
| Sink chosen | 49.1% | 50.8% | 25.3% |
| Sink passed over for a relay with higher Q | 3729 | 3464 | 10408 |
| … relay beats sink on c_nei | 100% | 100% | 93.3% |
| … relay beats sink on c_ene | 0% | 0% | 27.2% |
| … relay beats sink on c_del | 0% | 0% | 0% |
| Median c_nei ratio, relay/sink | 8.1×10³ | 3.0×10³ | 148 |
| NaN Q values | 0 | 0 | 0 |

**Mechanism.** `c_nei(s_j) = exp(|I_LQARP(s_j)|)` (LQARP reward, inherited unchanged).
The sink is the unique shallowest node, so its forward set is always empty and its
`c_nei = 1`. A relay with k shallower neighbors gets `e^k`, in the thousands to 10¹¹.

In every decision where Periodic or E-LQTP+energy passed over a reachable sink, the chosen
relay was worse than the sink on energy (median `c_ene` ratio about 0.15) and on
depth-progress (`c_del` ratio 0.19). It won only through `c_nei`. So the protocols route
about 3 hops where a live BFS needs about 1.4 (Step 3 census), and the extra hops come
from the reward's neighbor-count term, not from the control plane.

Periodic and E-LQTP+energy have the same decision structure because both hold fresh
energy. LQARP holds frozen E_ini, so `c_ene` is mostly 0 and Q ties more often; it passes
the sink over in 75% of decisions and routes 4.7–5.2 hops under drift.

## Does the Step 2–4 verdict still stand?

- **(a) Trigger-dependent multi-hop routing: still NO.** With NaN removed, the trigger-off
  control still matches E-LQTP+energy within seed noise everywhere. For example, at
  II 2.0 m/s: PDR 0.9939 vs 0.9931, hops 3.15 vs 3.18, T_e2e 4.49 vs 4.53 s. The trigger
  costs 11% of E-LQTP+energy's total overhead at 0.5 m/s, 27% at 1 m/s, and 48–64% at
  2 m/s and above.
- **(b) Total-overhead advantage over a fairly tuned Periodic: still NO, and wider after
  the fix.**
  - Gated Periodic at T=40–60 s: O_total 37.6–54.7 B/s, PDR 0.992–0.999.
  - E-LQTP+energy: 108–294 B/s, PDR 0.955–0.998.
  - Periodic breaks even at T ≈ 7–19 s and is cheaper at every T ≥ 20 s.
  - At 3.0–3.5 m/s E-LQTP+energy's PDR (0.976 / 0.955) is below every Periodic setting
    (≥ 0.993).
  - The one metric where E-LQTP+energy leads is delay: 4.3–4.9 s vs 5.1–6.2 s for Periodic
    at T=60. That comes from its 5 s energy refresh, not the trigger (the trigger-off
    control gets the same delay), and Periodic@5 s matches it.

## Plain-language summary

The fairness gap was real: Periodic's HELLO and the energy beacon both updated every
node's table, including nodes out of range. Fixing it helps Periodic slightly and
doesn't change the E-LQTP results. The anomaly came from a different bug. The 32-bit
energy beacon filled every neighbor's energy with NaN, and the resulting tie-break sent
packets straight to the sink. That produced the "1.66 hops" and the earlier "hop-count
fix". With both bugs fixed, E-LQTP+energy, its trigger-off control and Periodic make
nearly identical routing decisions. They all route about three hops, and the reason is
the inherited LQARP neighbor-count reward term: it rates any relay with many neighbors
thousands of times above the sink. The Step 2–4 verdict stands and is stronger. The event
trigger doesn't affect routing, and a tuned Periodic baseline is cheaper at equal or
better PDR. The honest finding for the paper is the reward's latent sensitivity. The
`c_nei` term dominates next-hop choice whenever neighbor state is fresh, and
stale-versus-fresh energy decides whether it can act at all. The control-plane trigger is
not a finding.

**To correct in the project record:** `paper/step1-final-campaign-summary.md` (Step 1h)
and `paper/step2-4-rxonly-geometry-rerun-verdict.md` both report NaN-affected routing
numbers for the 32-bit beacon. Step 1g's choice of 32 bits was based on those numbers.
