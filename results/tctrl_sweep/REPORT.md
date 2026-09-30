# Baseline check and Fixed-Periodic T_ctrl sweep (2026-09-30)

## Build

NS-3.41 from the official GitHub mirror (`nsnam/ns-3-dev-git`, tag `ns-3.41`,
commit 40a8e01). The nsnam.org tarball was unreachable from the build host.
Aqua-Sim-NG is at `0fbc166`, the same commit as `results/EXAMPLE_RUN.md`.
Configure flags are identical to `scripts/install-ns3-aqua-sim.sh`.
`lqarp-unit-check` gives PASS=45 FAIL=0 and `bellhop-data-loader-check`
gives PASS=11 FAIL=0.

## Reproduction

`scripts/step1_campaign.py` (unchanged) → `results/step1_fresh/step1_campaign.csv`:
100/100 jobs succeeded. The CSV is **byte-identical** to the committed
`results/step1c_rerun/step1_campaign.csv`, so the current code is the Step 1c state.

Against manuscript Tables II–V (`results/step1_fresh/COMPARISON.md`),
62 cells fall outside the published mean ± s.d. (11 / 8 / 31 / 12). This is
intentional: the published tables were produced before the Step 1 audit,
when every protocol read live oracle state. The only rows that still match
are the RLOR-inspired rows and Fixed-Periodic's O_ctrl in Tables III and V.
Table II's periodic O_ctrl of 442.03 includes the drain period; the code
reports 411.28 without it.

## Code change for the sweep

`scenario-i-lqarp.cc` gets a new `--tCtrl` option that affects
Fixed-Periodic only. The default is unchanged at 5 s, and the reproduction
above ran before the change. Driver: `scripts/tctrl_sweep.py`. It uses the
same seeds, N=40, boundary=remove and β1=β2=0, and runs the full
Scenario I / II (0.5–3.5 m/s) / III matrix. It also runs `elqtp-energy
--energyBits=32` (the Step 1g/1h design) on the same matrix. 210/210 jobs
succeeded → `tctrl_sweep.csv`.

## Result 1: Fixed-Periodic is insensitive to T_ctrl from 5 to 60 s

Every scenario and every drift speed gives PDR = 1.0000 and hops = 1.000–1.003.
T_e2e is identical to three decimals, and VOID = SNR-fail = envelope-exit = 0.
Only the overhead changes:

| T_ctrl (s) | 5 | 10 | 20 | 40 | 60 |
|---|---:|---:|---:|---:|---:|
| O_ctrl, Scen. II/III (byte/s) | 413.42 | 208.42 | 105.92 | 54.67 | 37.58 |
| O_ctrl, Scen. I (byte/s) | 411.28 | 206.28 | 103.78 | 52.53 | 34.59 |

## Result 2: E-LQTP's true overhead includes O_ene

For `elqtp-energy`, the binary reports the 40-bit energy beacon as `O_ene`
(41.0 byte/s) and leaves it out of `O_ctrl`. The Step 1h summary table in the
project quoted `O_ctrl` alone. With O_total = O_ctrl + O_ene:

| Case | O_ctrl | O_ene | O_total | vs Periodic@5 s | Periodic break-even T_ctrl |
|---|---:|---:|---:|---:|---:|
| I | 46.9 | 41.0 | 87.9 | 0.21× | ≈23 s |
| II 0.5 | 127.9 | 41.0 | 168.9 | 0.41× | ≈12 s |
| II 1.0 | 134.5 | 41.0 | 175.5 | 0.42× | ≈12 s |
| II 2.0 | 178.7 | 41.0 | 219.7 | 0.53× | ≈9 s |
| II 3.0 | 254.8 | 41.0 | 295.8 | 0.72× | ≈7 s |
| II 3.5 | 299.5 | 41.0 | 340.5 | 0.82× | ≈6 s |
| III | 286.8 | 41.0 | 327.8 | 0.79× | ≈6 s |

E-LQTP delivers the same PDR, hops and T_e2e as Periodic at every T_ctrl.
Periodic at T_ctrl ≥ 10 s is cheaper than E-LQTP in every mobile case.

## Why

In this geometry every node reaches the sink in one hop throughout the run
(hops ≈ 1.000 for every protocol, and no voids even at T_ctrl = 60 s at
3.5 m/s). Neighbor state can be up to a minute stale without changing a
routing decision, so no control schedule can outperform another on delivery.
This matches the Step 1h observation that "multi-hop was never
geometrically necessary." The T_ctrl sweep cannot justify 5 s, or any other
value, until the multi-hop geometry fix in `revision-plan-evaluation-fidelity.md`
is made. After that fix, the sweep should be rerun with the same driver.
