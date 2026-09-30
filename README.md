# E-LQTP

Simulation code, input data, and the evaluation dataset for **E-LQTP**, an event-triggered
link-quality and topology-prediction routing protocol for underwater acoustic sensor networks,
extending **LQARP** (Link Quality-Aware Routing Protocol, a reinforcement-learning approach).

The protocol is implemented as an **ns-3.41 contrib module** (`contrib/elqtp/`) evaluated on top of
**Aqua-Sim-NG**, with an acoustic channel built from **BELLHOP** eigenrays over a **WOA23** sound-speed
profile and **GEBCO_2026** bathymetry.

> **Status.** This repository records a full evaluation-fidelity audit of the protocol. The audit
> found and fixed several bugs, and its corrected results **do not support the efficiency claim the
> draft manuscript was built on.** The honest finding is documented below and in
> [`results/step7_envelope_fix/REPORT.md`](results/step7_envelope_fix/REPORT.md). The manuscript
> sources under `paper/` still contain the **pre-audit** numbers and are being rewritten against this
> dataset.

---

## 1. Authoritative dataset

**[`results/step7_envelope_fix/`](results/step7_envelope_fix/) is the dataset of record.** 595 runs,
0 failures.

| File | Contents |
|---|---|
| [`REPORT.md`](results/step7_envelope_fix/REPORT.md) | What was fixed, verification, caveats |
| [`TABLES_II_V.md`](results/step7_envelope_fix/TABLES_II_V.md) | Tables II–V, each cell against the manuscript's published value |
| [`TCTRL_SWEEP.md`](results/step7_envelope_fix/TCTRL_SWEEP.md) | Fixed-Periodic `T_ctrl` sweep, `O_total` headline |
| [`DECISION_TRACE.md`](results/step7_envelope_fix/DECISION_TRACE.md) | Per-decision reward analysis (`c_nei` dominance) |
| [`VERIFICATION.txt`](results/step7_envelope_fix/VERIFICATION.txt) | Non-finite-Q audit, Scenario I/II invariance, Scenario III deltas |
| [`PROVENANCE.md`](results/step7_envelope_fix/PROVENANCE.md) | Commit hashes, binary hashes, unit-check results |
| `campaign/`, `tctrl_sweep/`, `trigger_off/`, `decision_trace/` | One CSV per part, plus `sweep_lines.txt` (the raw `SWEEP` line of every run) |
| `patches/` | The Step 7 diff |

Configuration: seeds 20260921–20260925, `N = 40`, `r_range = 2500 m`, `β₁ = β₂ = 0`,
`boundary = remove`, 18-bit energy beacon, received-only `z_k`, reception-gated HELLOs.
All values are five-seed means ± sample standard deviation.

**Earlier step directories under `results/` are kept as the audit trail and are superseded.**
Only their qualitative findings carry forward.

---

## 2. Headline results

Scenario I is a static field, Scenario II a linear drift, Scenario III a Rankine eddy with a
Gauss–Markov velocity process. `O_total = O_ctrl + O_ene` (byte/s) is the honest control-overhead
metric: `O_ctrl` is the HELLO cost and `O_ene` the energy-beacon cost, which earlier work reported
separately and so under-counted.

### Scenario II at 2 m/s

| Protocol | PDR | Hops | T_e2e (s) | O_ctrl | O_ene | **O_total** |
|---|---:|---:|---:|---:|---:|---:|
| LQARP | 0.9788 ± 0.0380 | 5.16 | 7.44 | 0 | 0 | **0** |
| E-LQTP (no beacon) | 0.9788 ± 0.0380 | 5.09 | 7.34 | 59.7 | 0 | **59.7** |
| E-LQTP + energy beacon | 0.9931 ± 0.0066 | 3.20 | 4.56 | 146.3 | 26.65 | **172.9** |
| E-LQTP + energy, **trigger OFF** | 0.9936 ± 0.0061 | 3.16 | 4.51 | 57.8 | 26.65 | **84.4** |
| Fixed-Periodic (T = 5 s) | 0.9974 ± 0.0025 | 3.20 | 4.72 | 413.4 | 0 | **413.4** |
| RLOR-inspired | 0.9907 ± 0.0146 | 1.60 | 2.36 | 0 | 0 | **0** |

### Fixed-Periodic across `T_ctrl` (all mobile cases)

| `T_ctrl` | 5 s | 10 s | 20 s | 40 s | 60 s |
|---|---:|---:|---:|---:|---:|
| `O_total` (byte/s) | 413.4 | 208.4 | 105.9 | 54.7 | **37.6** |
| PDR range | 0.996–0.998 | 0.994–0.998 | 0.995–0.998 | 0.996–0.999 | 0.993–0.999 |

### The two findings that matter

1. **The event trigger does not drive routing outcomes.** Disabling it entirely
   (`--epsilon_0=1e12`) leaves PDR, hop count and delay unchanged within seed noise in every
   scenario, while removing 13–68% of total overhead. Scenario III: PDR 0.9986 ± 0.0014 with the
   trigger against 0.9978 ± 0.0029 without, for 60% less control traffic.
2. **A fairly tuned periodic baseline is cheaper at equal or better delivery.** Fixed-Periodic at
   `T_ctrl = 60 s` costs 37.6 byte/s at PDR 0.993–0.999; E-LQTP + beacon costs 93.7–279.6 byte/s at
   PDR 0.957–0.999. Break-even is `T_ctrl ≈ 7–22 s`; periodic is cheaper at every `T ≥ 20 s`.
   The paper's original 5 s periodic baseline was the only setting the comparison could win against.

What the evaluation *does* establish is a mechanism worth reporting: the inherited LQARP reward's
neighbour-count term `c_nei(s_j) = exp(|I(s_j)|)` dominates next-hop choice. In **100%** of decisions
where a reachable sink is passed over, the chosen relay is worse than the sink on both energy
(`c_ene`) and depth progress (`c_del`) and wins only on `c_nei`, by a median factor of 8.1 × 10³.
Whether energy readings are fresh or stale decides whether that term can act at all.

---

## 3. The audit trail

Each step's report lives in `results/`. Steps are listed with what they changed.

| Step | Change | Report |
|---|---|---|
| 1–1h | Held/frozen neighbour state; E-LQTP bootstrap; the `c_nei` hop-count diagnosis; decoupled energy beacon; beacon bit-width sweep | `results/step1*/` |
| 1i | Rebuilt the baseline; added the `T_ctrl` sweep (`--tCtrl`) | `results/tctrl_sweep/REPORT.md` |
| 2 | **Received-only `z_k`**: the EKF and trigger now update only when a packet from the neighbour is actually demodulated, instead of querying ground truth every tick | `results/step4_final/REPORT.md` |
| 3 | **Multi-hop geometry**: `r_range` 5125 m → 2500 m, so 38–44% of nodes need ≥ 2 hops instead of 0% | `results/step3_geometry/census.md` |
| 4 | Full rerun with honest `O_total` accounting | `results/step4_final/REPORT.md` |
| 5 | **Reception-gated HELLOs** (`helloRxGate`) and the **`(1u << 32)` quantizer bug**: undefined behaviour made every 32-bit beacon energy NaN, and NaN comparisons routed packets straight to the sink — the source of the earlier "1.66 hops" result | `results/step5/REPORT.md` |
| 6 | Bit-width re-verification and the full final campaign; chose **18 bits** | `results/final_campaign/REPORT.md` |
| 7 | **Live-envelope guard**: a pair admitted on its held pose but now outside the BELLHOP grid no longer reaches the reward, where it had scored `R = +∞`. Non-finite Q: 1296 → **0** | `results/step7_envelope_fix/REPORT.md` |

Two notes on method used throughout: diagnostics were verified **non-perturbing** (a traced run's
`SWEEP` line must match its untraced twin byte-for-byte), and Scenario I/II invariance under the
Step 7 fix was verified by rerunning all 595 jobs rather than asserted — all 510 Scenario I and II
rows are bit-identical to Step 6.

---

## 4. Quick start

Ubuntu 24.04 or similar, `g++` 11+, CMake 3.16+, Python 3, Git, Ninja, wget.

```bash
# 1. Build ns-3.41 + Aqua-Sim-NG with the elqtp module (~15 min).
#    Downloads ns-3 from nsnam.org and clones Aqua-Sim-NG from GitHub.
chmod +x scripts/*.sh
./scripts/install-ns3-aqua-sim.sh

# 2. Confirm the build. Both must pass fully.
BIN=opt/ns-allinone-3.41/ns-3.41/build/contrib/elqtp
$BIN/ns3.41-lqarp-unit-check-optimized        --dataDir=data/channel_db   # expect PASS=49 FAIL=0
$BIN/ns3.41-bellhop-data-loader-check-optimized --dataDir=data/channel_db # expect PASS=11 FAIL=0

# 3. Reproduce the dataset of record (595 runs).
FINAL_OUT=results/my_rerun python3 scripts/final_campaign.py --jobs 2

# 4. Regenerate the tables from it.
FINAL_OUT=results/my_rerun python3 scripts/final_tables.py
```

If `nsnam.org` is unreachable, take ns-3.41 from its GitHub mirror instead
(`github.com/nsnam/ns-3-dev-git`, tag `ns-3.41`), clone Aqua-Sim-NG as the script does, then
configure and build with the same flags. The dataset in this repository was produced that way.

### Running one simulation

```bash
opt/ns-allinone-3.41/ns-3.41/build/contrib/elqtp/ns3.41-scenario-i-lqarp-optimized \
  --dataDir=data/channel_db --scenario=iii --nAuv=40 --simTime=600 --seed=20260921 \
  --driftSpeed=2.0 --protocol=elqtp-energy --energyBits=18 --rRange=2500 \
  --beta_1=0 --beta_2=0 --boundary=remove --helloRxGate=1 --quiet --out=/tmp/run.txt
```

`--protocol` accepts `lqarp`, `lqarp-refreshed`, `elqtp`, `elqtp-energy`, `rlor`, `periodic`.
Useful flags: `--tCtrl` (periodic period), `--epsilon_0=1e12` (disable the trigger),
`--hopDiag=1`, `--decisionTrace=1`, `--geoCensus=1`.

---

## 5. Layout

```
contrib/elqtp/             ns-3 contrib module: the protocols under evaluation
  model/                     LQARP, E-LQTP, RLOR-inspired, channel gate, EKF, energy model
  examples/                  scenario harness (scenario-i-lqarp.cc) and unit checks
  SPEC.md                    authoritative system model and equations
scripts/                   build, campaign and analysis drivers
  install-ns3-aqua-sim.sh    ns-3.41 + Aqua-Sim-NG + elqtp build
  final_campaign.py          the dataset-of-record campaign
  final_tables.py            Tables II–V, T_ctrl sweep, decision-trace summary
  step1_campaign.py          five-seed multi-scenario campaign
  tctrl_sweep.py             Fixed-Periodic T_ctrl sweep
  bitwidth_sweep.py          energy-beacon bit-width sweep
  geo_census.py              hop-distance-to-sink census
  trigger_ablation.py        trigger-off control
  dec_analyze.py             per-decision reward analysis
  step7_verify.py            non-finite-Q and invariance verification
  build_channel_db*.py       BELLHOP eigenrays to ns-3 TL/SNR grids
  run_bellhop_wp.py          24 kHz coherent BELLHOP run
  build_woa23_ssp.py         WOA23 sound-speed profile
  extract_gebco_transect.py  GEBCO_2026 bathymetry transect
data/
  channel_db/                TL/SNR grids the simulator reads (required)
  bellhop/                   BELLHOP products and full-grid eigenrays
  woa23/, gebco/             sound-speed and bathymetry inputs
paper/                     IEEE IoT-J manuscript sources and figures (pre-audit numbers)
phase1/                    earlier USV–AUV discovery and forwarding study
results/                   reports, CSVs and figures — see sections 1 and 3
```

---

## 6. What is not in git

- **`opt/`** — the ns-3 + Aqua-Sim-NG build tree. Recreate with `scripts/install-ns3-aqua-sim.sh`.
- **`results/**/runs/`** — raw per-run simulator output, about 5,700 files and 1.6 GB. Regenerate
  with the scripts; a run is byte-reproducible for a fixed command line. The aggregate CSVs and the
  `sweep_lines.txt` files hold every measured quantity these files contain.

One documented reproducibility caveat: for **Scenario III, E-LQTP + energy beacon, seed 20260923
only**, the event-HELLO count varies by ≤ 2.3% with process memory layout, while every delivery
metric stays bit-identical. An exhaustive A/B over 90 scenario × variant × seed combinations found
exactly this one. The cause is most likely alignment-dependent vectorised arithmetic in the EKF under
`-march=native`; for a fully reproducible artifact, rebuild with `-DNS3_NATIVE_OPTIMIZATIONS=OFF` and
rerun the campaign. Details and the full diagnosis are in
[`results/step7_envelope_fix/REPORT.md`](results/step7_envelope_fix/REPORT.md).

---

## 7. Licensing and attribution

Files under `contrib/elqtp/` carry `SPDX-License-Identifier: GPL-2.0-only`, matching ns-3 and
Aqua-Sim-NG, both GPL-2.0. **No repository-wide `LICENSE` file has been added** — that is the
author's decision to make. Adding `LICENSE` with GPL-2.0 would be consistent with the module headers
and with the dependencies.

Third-party components, not redistributed here:

- **ns-3.41** — <https://www.nsnam.org/> (GPL-2.0)
- **Aqua-Sim-NG** — <https://github.com/rmartin5/aqua-sim-ng>, University of Connecticut
- **BELLHOP / Acoustics Toolbox** — M. Porter
- **WOA23** — NOAA NCEI World Ocean Atlas 2023
- **GEBCO_2026** — General Bathymetric Chart of the Oceans

Baseline protocol: LQARP, "Link Quality-Aware Routing Protocol for Underwater Wireless Sensor
Networks: A Reinforcement Learning Approach."
