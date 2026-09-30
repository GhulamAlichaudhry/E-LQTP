# Step 7 — Scenario III out-of-envelope +inf reward: fixed. Dataset is final.

Build and integrity: `PROVENANCE.md`. `lqarp-unit-check` PASS=49 FAIL=0,
`bellhop-data-loader-check` PASS=11 FAIL=0. Code snapshot: `code_snapshot.tar.gz`.
Manuscript files were not edited.

## The fix

`patches/step7-live-envelope-guard.patch` (126 changed lines across 5 files).

1. **`ChannelGate::sampleHasDefinedSnr`** (new, `channel-gate.cc:92`): returns
   `valid && !nearPressureRelease && isfinite(snr_db)`. Deliberately weaker than
   `sampleFailsCandidateSnr` — it contains **no threshold comparison**. SPEC Part 1.2 writes
   `N_SNR = { s_j : SNR(s_i,s_j) > SNR_threshold }`, which presupposes that SNR exists; this
   predicate is exactly that precondition.
2. **The guard, added to candidate admission in both protocols whose reward reads the live
   sample:** `LqarpProtocol::inNSnr` (`lqarp-protocol.cc:201`) and `ElqtpProtocol::inNSnr`
   (`elqtp-protocol.cc:350`). The held-pose threshold test is unchanged and still runs first;
   the new guard then rejects a pair whose **live** sample has no defined SNR.

Two deliberate scope limits:

- **Only definedness is tested against the live pose, never the threshold.** Testing the live
  SNR against `SNR_threshold` would have turned the filter into a live-state filter and
  destroyed the entire staleness model that Steps 1–6 built. The guard removes only the case
  where the channel is *undefined*.
- **`cLin` and the reward's `+inf` branch are untouched**, as instructed. That branch is now
  unreachable in practice and remains as a defensive check.

**RLOR-inspired was deliberately not changed.** It has no filter/reward mismatch to fix:
`RlorInspiredProtocol::pSucc` scores from `heldLinkSample` (`rlor-inspired-protocol.cc:160`),
the same held sample its filter uses, and its only live `linkSample` call is the
discovery/bootstrap gate at `:69`. This is consistent with RLOR having shown zero non-finite Q
in Step 6, and its Scenario III rows below are bit-identical to Step 6.

### Grep confirmation — filter and reward now read the same live sample

```
the reward path's live read:        lqarp-protocol.cc:284    const ChannelSample s = linkSample(i, j);
the candidate filter's live guard:  lqarp-protocol.cc:201    if (!gate_->sampleHasDefinedSnr(linkSample(i, j))) {
the reward path's live reads:       elqtp-protocol.cc:455    const ChannelSample s = linkSample(i, j);   (cPred)
                                    elqtp-protocol.cc:495    const ChannelSample s = linkSample(i, j);   (reward)
the candidate filter's live guard:  elqtp-protocol.cc:350    if (!gate_->sampleHasDefinedSnr(linkSample(i, j))) {
```

Both guards were confirmed by an awk scan to sit lexically inside `inNSnr`, and both call the
identical expression `linkSample(i, j)` that the reward path uses.

### New unit test 23g

`lqarp-unit-check` gains a test on a new `EnvelopeGate` double (valid inside 6 km,
`valid=false, snr=NaN` beyond). For **both** LQARP and E-LQTP it asserts: the pair is a
candidate while close; after the neighbour is moved to 9 km the held pose still passes
`inNRange`; the pair is nonetheless dropped from the candidate set; and Q stays finite. It
also asserts the pathology itself, that `cLin` of the live out-of-envelope sample is
non-finite, so the test fails if the guard is ever removed. Output:

```
PASS  23g. live out-of-envelope pair leaves the candidate set (LQARP and E-LQTP); Q stays finite
  live_sample_valid=no c_lin(live)=inf | LQARP in_set_before=yes held_still_in_range=yes
  dropped_after=yes Q_finite=yes | E-LQTP in_set_before=yes held_still_in_range=yes
  dropped_after=yes Q_finite=yes
```

## Non-finite Q: 1296 → 0

Full counts are in `VERIFICATION.txt`. Decisions containing at least one non-finite-Q
candidate, across five seeds:

| Scenario III variant | Step 6 | Step 7 |
|---|---:|---:|
| LQARP | 220 | **0** |
| E-LQTP (no beacon) | 251 | **0** |
| E-LQTP+energy (18-bit) | 245 | **0** |
| E-LQTP+energy, trigger OFF | 277 | **0** |
| Fixed-Periodic (T=5 s) | 303 | **0** |
| RLOR-inspired | 0 | 0 |
| **total, all scenarios and variants** | **1296** | **0** |

Zero non-finite Q values remain anywhere in the dataset, across all five seeds and all six
variants.

## Scenarios I and II are untouched — verified, not assumed

I reran the **whole** 595-job campaign rather than Scenario III alone, specifically so that
Scenario I/II invariance is an empirical result. 595/595 succeeded, no `FAILURES.txt`. Every
numeric field of every row was compared against Step 6 (`VERIFICATION.txt` section 2):

| Part | Scenario I | Scenario II | Scenario III |
|---|---|---|---|
| campaign | 25 rows IDENTICAL | 125 rows IDENTICAL | 8/25 rows changed |
| tctrl_sweep | 25 rows IDENTICAL | 125 rows IDENTICAL | 10/25 rows changed |
| trigger_off | 5 rows IDENTICAL | 25 rows IDENTICAL | 2/5 rows changed |
| decision_trace | 30 rows IDENTICAL | 150 rows IDENTICAL | 9/30 rows changed |

**All 510 Scenario I and II rows are bit-identical to Step 6**, so Step 6's Tables II–IV
stand exactly as published there, and the guard provably never fires outside Scenario III.

## Corrected Scenario III numbers (Table V), Step 6 → Step 7

| Protocol | PDR | Hops | T_e2e (s) | O_ctrl | O_ene | **O_total** |
|---|---|---|---|---|---|---|
| LQARP | 0.9917 → **0.9941** | 4.69 → **4.63** | 6.58 → **6.49** | 0 | 0 | **0** |
| E-LQTP (no beacon) | 0.9903 → **0.9927** | 5.00 → **4.93** | 7.07 → **6.97** | 63.6 → **63.7** | 0 | **63.7** |
| E-LQTP+energy (18-bit) | 0.9918 → **0.9986** | 3.06 → **3.00** | 4.51 → **4.42** | 188.1 → **188.3** | 26.65 | **215.0** |
| E-LQTP+energy, trigger OFF | 0.9912 → **0.9978** | 3.02 → **2.97** | 4.43 → **4.37** | 59.8 → **59.8** | 26.65 | **86.4** |
| Fixed-Periodic (T=5 s) | 0.9901 → **0.9969** | 3.16 → **3.11** | 4.66 → **4.60** | 413.4 | 0 | **413.4** |
| RLOR-inspired | 0.9966 → 0.9966 | 1.56 → 1.56 | 2.29 → 2.29 | 0 | 0 | **0** |

T_ctrl sweep, Scenario III: PDR 0.9901→0.9969 (T=5), 0.9897→0.9978 (10), 0.9899→0.9980 (20),
0.9922→0.9960 (40), 0.9961→0.9989 (60). O_total is unchanged at every T.

**The shift is small and in the expected direction.** PDR rises by 0.002–0.007 for every
affected protocol, because the packets previously sent to a neighbour whose channel was
unknown are now sent to a neighbour with a real channel. Hop count falls by 0.05–0.07 and
delay by 0.06–0.10 s. Overhead is essentially unchanged (≤0.3 B/s) because the guard changes
which neighbour is chosen, not how often HELLOs fire. Every movement is far inside the
five-seed sample s.d. (for example E-LQTP+energy PDR 0.9986 ± 0.0014, hops 3.00 ± 0.36),
consistent with only 1.4–2.8% of decisions having been affected.

## The verdict for Scenario III does not change — with numbers

- **Trigger does not drive routing.** Trigger on vs off: PDR 0.9986 vs 0.9978 (s.d. 0.0014 and
  0.0029, so the gap is inside one s.d.), hops 3.00 vs 2.97, T_e2e 4.42 vs 4.37 s. Switching
  the trigger off removes **60%** of total overhead (215.0 → 86.4 B/s) and changes no outcome
  metric beyond seed noise.
- **Periodic still wins on total overhead.** Fixed-Periodic costs 37.6 B/s at T=60 s with PDR
  0.9989 ± 0.0018, against E-LQTP+energy's 215.0 B/s at PDR 0.9986 ± 0.0014 — equal delivery
  at **5.7× less** control traffic. Break-even is at T_ctrl ≈ 9.4 s, and Periodic is cheaper at
  every T ≥ 20 s.
- **`c_nei` dominance is unchanged** (`DECISION_TRACE.md`). In Scenario III, E-LQTP+energy,
  its trigger-off control and Fixed-Periodic pass over a legal sink in 48.3–50.5% of
  decisions, and in **100%** of those the chosen relay is worse on `c_ene` and on `c_del` and
  wins only on `c_nei`, median ratio 8.1 × 10³. LQARP and plain E-LQTP pass it over in ~73%
  of decisions, winning on `c_nei` in 100% (median ratio 3.0 × 10³).

## One reproducibility caveat, found while auditing this rerun (disclosed, not fixed)

The rerun's non-perturbation check reported 1 mismatch out of 210 decision-trace runs (Step 6
had 0). Investigated in full:

- **What differs:** for Scenario III, E-LQTP+energy, **seed 20260923 only**, the event-HELLO
  count varies between 1795 and 1836 (≤2.3%), and with it O_ctrl (200.5–203.9 B/s). Every
  delivery metric — PDR, mean hops, T_e2e, E_bit, n_gen, n_succ, VOID, bootstrap HELLOs,
  energy HELLOs, first-fire — is **bit-identical** across all variants of the run.
- **It is not nondeterminism.** Five invocations of an identical command line give
  bit-identical output. The value shifts only when a *string argument* changes, e.g. passing
  `--dataDir` as a relative rather than absolute path (1798 vs 1795), which alters heap
  layout. Out-path length alone does not do it, and neither does environment padding: a sweep
  of 4 memory layouts × 5 seeds × 6 variants found every field stable.
- **Scope, measured exhaustively:** an A/B over both `--dataDir` spellings across 3 scenarios
  × 6 variants × 5 seeds = 90 combinations found **exactly one** sensitive combination, the
  one above. The other 89 are bit-identical.
- **Not a knife-edge comparison.** I instrumented the trigger to count decisions where
  `|e_trigger|` lands within 1e-9 of its threshold: zero, for all five seeds. So this is the
  accumulated amplification of last-bit rounding differences through the
  trigger → HELLO → ZOH-reset feedback loop, not a single borderline test. Consistent with
  this, the trigger-off variant (threshold 1e12) and every non-event-triggered protocol are
  stable.
- **Likely cause:** the tree is built with `NS3_NATIVE_OPTIMIZATIONS=ON` (`-march=native`,
  release `-O3`), so the EKF's 7×7 matrix products over heap-allocated `NeighborEkf` objects
  are auto-vectorized in an alignment-dependent way. Adding the diagnostic counter, which
  shifts code layout, made the run stable — itself evidence of layout sensitivity rather than
  a logic error. I did **not** prove the vectorization mechanism, because doing so requires a
  non-native rebuild that would perturb every number in the dataset; that is the honest limit
  of this diagnosis.
- **Impact on the paper:** one seed of one variant in one scenario, affecting only control
  overhead, by 3.4 B/s in that one seed — 0.7 B/s in the five-seed mean, whose sample s.d. is 12.7 B/s, so 5% of one s.d..
  No conclusion depends on it. For a reproducible artifact, rebuild with
  `-DNS3_NATIVE_OPTIMIZATIONS=OFF` (and optionally `-ffp-contract=off`) and regenerate; that
  changes last-bit rounding everywhere, so it must be a full-campaign rerun, not a patch.
- The probe counter was reverted and the binary rebuilt; the restored binary reproduces the
  stored run **byte-identically** under its original command line, so this dataset's
  provenance is intact.

## Status: this dataset is final and authoritative

`results/step7_envelope_fix/` — 595 runs, 0 failures.

| Content | Path |
|---|---|
| Tables II–V vs manuscript (85 flagged cells) | `TABLES_II_V.md` |
| T_ctrl sweep, O_total headline | `TCTRL_SWEEP.md` |
| Decision-trace / `c_nei` dominance | `DECISION_TRACE.md` |
| Verification log (non-finite Q, I/II identity, III deltas) | `VERIFICATION.txt` |
| Per-run CSVs | `campaign/`, `tctrl_sweep/`, `trigger_off/`, `decision_trace/` |
| Fix diff | `patches/step7-live-envelope-guard.patch` |

Scenarios I and II are bit-identical to Step 6, so this directory is the complete dataset of
record on its own. **It supersedes the numeric tables of Steps 1h, 1i, 2–4, 5 and 6's Table V.
Only the qualitative mechanism findings carry forward: `c_nei` dominance of next-hop choice,
the event trigger not driving routing outcomes, and the reception-gating, quantizer and
live-envelope fixes themselves.** The 18-bit beacon choice and the bit-width analysis from
Step 6 stand unchanged.
