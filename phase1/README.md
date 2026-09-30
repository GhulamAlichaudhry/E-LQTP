# Phase 1–2 — Topology discovery and hold-time prediction

Simulation-only slice of the professor’s first chapter: **current network state** under meandering current, not routing.

This is the paper-experiment setup, not a single lucky seed.

## What reviewers require (and what this repo now does)

1. **Statistical validity.** `scripts/run-phase1.sh` runs **30 random seeds**. Each seed randomizes AUV placement, thrust headings, and the Caruso meander phase/scale. Metrics are reported as mean ± **95% CI** (`results/phase1/phase1_ci.png`, `batch_ci_table.md`).
2. **MAC-layer reality.** HELLOs are **unslotted ALOHA** in Aqua-Sim (`AckOn=0`, 1000 bit/s). 1-hop `AquaSimHelloRouting` broadcasts locally and never floods. Colliding beacons are dropped in the PHY (`RxColl`) / ALOHA error flag. Neighbor tables are still SNR-gated with the SOTA sonar equation after a HELLO survives the MAC.
3. **Scaled topology.** Default is **1 USV + 11 AUVs (12 nodes)**: inner ring just inside \(R^*\), outer ring just beyond \(R^*\) so about **70% of reachable directed pairs are 2+ hop**. Inner AUVs swim out and outer AUVs swim in so links actually form and break.

## 30-seed results (240 s, 12 nodes, unslotted ALOHA)

| Metric | Periodic mean [95% CI] | Event mean [95% CI] |
| --- | --- | --- |
| Recall | 0.966 ± 0.002 | 0.841 ± 0.015 |
| Precision | 0.994 ± 0.001 | 0.994 ± 0.001 |
| F1 | 0.979 ± 0.001 | 0.908 ± 0.009 |
| Control bit/s | 927 ± 1 | **212 ± 1** |
| Link-up delay (s) | 4.67 ± 0.20 | 15.1 ± 1.0 |
| Link-down delay (s) | 5.00 ± 0.26 | 5.78 ± 0.22 |
| Hold-time MAE (s) | 3.93 ± 0.07 | 8.06 ± 0.83 |
| PHY collisions / run | 195 ± 12 | 36 ± 4 |
| Fraction 2+ hop pairs | 0.705 ± 0.012 | 0.705 ± 0.012 |

Event-triggered still saves **~77% of beacons** (127 vs 556) and stays at ~11% of a 2 kbps budget. The cost is real and now measured: ALOHA collisions plus a 25 s keep-alive slow **link-up** (~15 s vs ~5 s) and inflate distributed hold-time error (~8 s vs ~4 s). Link-**down** delay stays ~6 s because the timeout is SNR-aware, not \(3T_{\max}\). Every seed had 5–14 true link-down events; none of this is a two-event anecdote.

## Appendix (20 seeds, 95% CI)

These are the Phase 1 polish runs. They do **not** replace the 30-seed main table. Figure: `results/phase1/phase1_ablations.png`.

### Unslotted vs slotted ALOHA (12 nodes, \(T_{\max}=25\,\mathrm{s}\))

UWA slot length is \(T_{\mathrm{tx}}+T_{\mathrm{prop,max}}+\mathrm{guard}\approx 5.06\,\mathrm{s}\), comparable to the 5 s HELLO period. Slotted ALOHA **synchronizes** beacons into the same slots and **raises** collisions. It is not a free win here.

| MAC | Mode | Recall | Up delay (s) | Collisions | Control bit/s |
| --- | --- | --- | --- | --- | --- |
| unslotted | periodic | 0.965 ± 0.003 | 4.63 ± 0.24 | 202 ± 15 | 927 ± 1 |
| unslotted | event | 0.846 ± 0.019 | 14.7 ± 1.3 | 37 ± 6 | 213 ± 1 |
| slotted | periodic | 0.818 ± 0.020 | 16.1 ± 2.3 | 477 ± 36 | 913 ± 1 |
| slotted | event | 0.801 ± 0.021 | 22.9 ± 2.2 | 55 ± 6 | 168 ± 1 |

Keep **unslotted** ALOHA as the main MAC. Report slotted as a negative control.

### Event \(T_{\max}\) sweep (unslotted, 12 nodes)

| \(T_{\max}\) (s) | Recall | Up delay (s) | Down delay (s) | Control bit/s | Hold MAE (s) |
| --- | --- | --- | --- | --- | --- |
| 10 | 0.883 ± 0.018 | 6.14 ± 0.84 | 4.83 ± 0.26 | 488 ± 0.3 | 4.85 ± 0.13 |
| 15 | 0.859 ± 0.018 | 9.79 ± 0.80 | 5.56 ± 0.29 | 331 ± 0.7 | 5.55 ± 0.28 |
| 25 | 0.846 ± 0.019 | 14.7 ± 1.3 | 5.74 ± 0.26 | 213 ± 1 | 7.90 ± 0.98 |
| 40 | 0.847 ± 0.019 | 17.0 ± 1.8 | 6.04 ± 0.28 | 148 ± 1 | 13.9 ± 1.9 |

Down delay is almost flat (SNR-aware timeout). Stretching \(T_{\max}\) past 25 s does not buy recall; it only stale-dates hold-time. \(T_{\max}=10\,\mathrm{s}\) is the awareness-friendly point (~2.3× the 25 s control rate). Main-text \(T_{\max}=25\,\mathrm{s}\) is the budget-friendly point.

### Multipath margin (not Bellhop)

Nodes are placed as fractions of \(R^*\), so changing the 20/30/40 dB stand-in rescales the field (\(R^*\approx 6407/4946/3564\,\mathrm{m}\)) but **does not change the story**: periodic recall stays ~0.965, event ~0.83–0.85, ~70% 2-hop. This is a sensitivity check, not a TL table.

### Node count

| Nodes | 2+ hop frac | Diameter | Event recall | Event collisions |
| --- | --- | --- | --- | --- |
| 6 | 0.26 ± 0.04 | 1.47 ± 0.18 | **0.59 ± 0.06** | 5 ± 3 |
| 12 | 0.70 ± 0.02 | 4.52 ± 0.24 | 0.85 ± 0.02 | 37 ± 6 |
| 16 | 0.71 ± 0.01 | 4.09 ± 0.10 | 0.86 ± 0.02 | 79 ± 11 |

The old 6-node layout is a near-clique. Event-triggered actually **fails awareness** there when everyone sits on the \(R^*\) contour. 12 nodes is the smallest graph we will quote.

## SOTA models (analytical, not Bellhop)

Thorp absorption, practical spreading \(k=1.5\), Wenz noise, SNR gate 8.68 dB, BPSK success after MAC delivery, EWMA LQE, Caruso meandering current, event-triggered send-on-delta. A 30 dB multipath margin is an admitted Bellhop stand-in.

## Run

```bash
./scripts/run-phase1.sh              # 30-seed main table
./scripts/run-phase1-ablations.sh    # MAC / Tmax / margin / scale appendix
```

Environment knobs: `NSEEDS=30`, `ABLATION_SEEDS=20`, `SIMSTOP=240`, `NAUV=11`, `PHASE1_PAR=4`.

Smoke (seed 1, verbose traces) lands in `results/phase1/`. The 30-seed batch is summarized as `batch_metrics.csv`.

## Honest limits

- Aqua-Sim range-propagation + our SNR gate, not a Bellhop TL table or sea-trial CSI.
- Hold-time predictor is kinematic, not learned.

## Phase 2 — ETHA forwarding

Single-path geographic forwarding on this map, still not Q-learning.

```bash
./scripts/run-phase2.sh
```

All AUVs send 400-bit packets to the USV every 16 s after \(t=50\) s. **ETHA** applies a hold-time filter then a depth-primary score toward the surface sink. Baselines: SNR-greedy, DBR-like depth, periodic HELLO, oracle geometry.

Event-triggered maps, 12 nodes, 30 seeds, mean \(\pm 95\%\) CI:

| Policy | PDR | Energy (kJ) | Control (bit/s) |
| --- | --- | --- | --- |
| ETHA (proposed) | 0.755 ± 0.031 | 2.82 | 480 |
| Event+SNR | 0.651 ± 0.033 | 3.00 | 480 |
| Event+Depth | 0.755 ± 0.031 | 2.82 | 480 |
| Periodic+SNR | 0.641 ± 0.027 | 4.61 | 927 |
| Oracle | 0.817 ± 0.027 | 2.81 | 480 |

ETHA matches DBR delivery at 39% less transmit energy than periodic SNR-greedy. IEEE IoTJ draft: [`paper/iotj_et_hold.tex`](../paper/iotj_et_hold.tex).
