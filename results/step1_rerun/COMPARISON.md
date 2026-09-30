# Step-1 re-run vs manuscript Tables II–V

Held/frozen neighbor pose and energy. `c_lin`, `linkSample`, `predictPair`, and `predictForecast` still query the live channel. Seeds 20260921–20260925, N=40, January site, boundary=remove, β1=β2=0. Drift sweep 0.5–3.5 m/s. Eddy: Rankine core R=2000 m at (3000, 3000), V=2 m/s, Gauss–Markov ζ=0.95, σ=(1, 1, 0). Means are five-seed; deviations are the sample standard deviation (n−1).

### Scenario I (manuscript Table II)

| Protocol | PDR | Hops | T_e2e | E_bit | O_ctrl | First-fire |
|---|---|---|---|---|---|---|
| LQARP | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.530 ± 0.068) **FLAG** | 1.887 ± 0.1078 (ms 3.078 ± 0.071) **FLAG** | 5.360536e-03 ± 0 (ms 8.200000e-03 ± 0.00037) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — |
| E-LQTP | 0.0000 ± 0 (ms 1.0000 ± 0) **FLAG** | nan (ms 1.530 ± 0.068) **FLAG** | nan (ms 3.078 ± 0.071) **FLAG** | nan (ms 8.200000e-03 ± 0.00037) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — |
| RLOR-inspired | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) | 1.887 ± 0.1078 (ms 1.887 ± 0.108) | 5.360536e-03 ± 0 (ms 5.360000e-03 ± 0) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| Periodic | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.546 ± 0.039) **FLAG** | 1.887 ± 0.1078 (ms 3.119 ± 0.188) **FLAG** | 5.360536e-03 ± 0 (ms 8.290000e-03 ± 0.00021) **FLAG** | 411.28 ± 0 (ms 442.03 ± 0) **FLAG** | 1.000 ± 0 |

Flagged cells: 11.

**Scenario I is not numerically identical to Table II.** 11 cell(s) fall outside the manuscript band. That is the Step-1 hold applied to the identity harness, not a mobility result. Scenario I E-LQTP is constructed with the identity epsilon and with ticking disabled, so it never ingests a HELLO; under the hold the candidate set stays empty until a broadcast. LQARP/RLOR freeze pose and residual energy at first discovery, so later energy updates no longer enter c_ene or c_del. Fixed-Periodic still ingests on the T_ctrl grid, including t=0.

### Scenario II at 2 m/s (manuscript Table III)

| Protocol | PDR | Hops | T_e2e | E_bit | O_ctrl | First-fire |
|---|---|---|---|---|---|---|
| LQARP | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 2.241 ± 0.9251 (ms 2.153 ± 0.187) | 4.212 ± 1.962 (ms 4.438 ± 0.277) | 1.201496e-02 ± 0.004959 (ms 1.156000e-02 ± 0.001) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| E-LQTP | 0.0000 ± 0 (ms 0.9992 ± 0.0019) **FLAG** | nan (ms 2.154 ± 0.187) **FLAG** | nan (ms 4.439 ± 0.277) **FLAG** | nan (ms 1.156000e-02 ± 0.001) **FLAG** | 135.22 ± 22.83 (ms 135.00 ± 23) | 0.782 ± 0.0422 (ms 0.782 ± 0.042) |
| RLOR-inspired | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0.0005726 (ms 1.000 ± 0.001) | 1.845 ± 0.07412 (ms 1.845 ± 0.074) | 5.361909e-03 ± 3.07e-06 (ms 5.362000e-03 ± 0) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| Periodic | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 1.000 ± 0.0005726 (ms 2.153 ± 0.187) **FLAG** | 1.845 ± 0.07398 (ms 4.438 ± 0.277) **FLAG** | 5.361909e-03 ± 3.07e-06 (ms 1.156000e-02 ± 0.001) **FLAG** | 413.42 ± 0 (ms 413.42 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) |

Flagged cells: 7.

### Scenario II drift sweep (manuscript Table IV)

| v | Protocol | PDR | T_e2e | Hops | O_ctrl | First-fire | E_bit (not in table) |
|---:|---|---|---|---|---|---|---|
| 0.5 | LQARP | 1.0000 ± 0 (ms 1.0000 ± 0) | 2.041 ± 0.3798 (ms 4.776 ± 0.403) **FLAG** | 1.101 ± 0.2268 (ms 2.282 ± 0.186) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 5.904140e-03 ± 0.001216 |
| 0.5 | E-LQTP | 0.0000 ± 0 (ms 1.0000 ± 0) **FLAG** | nan (ms 4.776 ± 0.403) **FLAG** | nan (ms 2.282 ± 0.186) **FLAG** | 20.18 ± 4.196 (ms 20.20 ± 4.2) | 0.146 ± 0.02121 (ms 0.146 ± 0.021) | nan |
| 1.0 | LQARP | 1.0000 ± 0 (ms 0.9995 ± 0.0012) | 2.736 ± 0.9525 (ms 4.752 ± 0.377) **FLAG** | 1.477 ± 0.4617 (ms 2.289 ± 0.208) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 7.916790e-03 ± 0.002475 |
| 1.0 | E-LQTP | 0.0000 ± 0 (ms 0.9995 ± 0.0012) **FLAG** | nan (ms 4.752 ± 0.377) **FLAG** | nan (ms 2.289 ± 0.208) **FLAG** | 70.92 ± 6.535 (ms 70.70 ± 6.2) | 0.520 ± 0.03073 (ms 0.520 ± 0.031) | nan |
| 2.0 | LQARP | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 4.212 ± 1.962 (ms 4.438 ± 0.277) | 2.241 ± 0.9251 (ms 2.153 ± 0.187) | 0.00 ± 0 (ms 0.00 ± 0) | — | 1.201496e-02 ± 0.004959 |
| 2.0 | E-LQTP | 0.0000 ± 0 (ms 0.9992 ± 0.0019) **FLAG** | nan (ms 4.439 ± 0.277) **FLAG** | nan (ms 2.154 ± 0.187) **FLAG** | 135.22 ± 22.83 (ms 135.10 ± 23.1) | 0.782 ± 0.0422 (ms 0.782 ± 0.042) | nan |
| 3.0 | LQARP | 0.9993 ± 0.001459 (ms 1.0000 ± 0) **FLAG** | 5.276 ± 1.737 (ms 4.431 ± 0.333) **FLAG** | 2.812 ± 0.8946 (ms 2.154 ± 0.203) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 1.510095e-02 ± 0.00484 |
| 3.0 | E-LQTP | 0.0000 ± 0 (ms 1.0000 ± 0) **FLAG** | nan (ms 4.433 ± 0.331) **FLAG** | nan (ms 2.155 ± 0.203) **FLAG** | 213.38 ± 36.84 (ms 213.80 ± 39.1) | 0.857 ± 0.03387 (ms 0.857 ± 0.034) | nan |
| 3.5 | LQARP | 0.9987 ± 0.00141 (ms 1.0000 ± 0) **FLAG** | 5.824 ± 1.787 (ms 4.200 ± 0.393) **FLAG** | 3.128 ± 0.9253 (ms 2.063 ± 0.215) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 1.679613e-02 ± 0.004959 |
| 3.5 | E-LQTP | 0.0000 ± 0 (ms 1.0000 ± 0) **FLAG** | nan (ms 4.200 ± 0.393) **FLAG** | nan (ms 2.063 ± 0.215) **FLAG** | 258.38 ± 44.34 (ms 257.70 ± 46.9) | 0.897 ± 0.02763 (ms 0.897 ± 0.028) | nan |

Flagged cells: 25.

### Scenario III (manuscript Table V)

| Protocol | PDR | Hops | T_e2e | E_bit | O_ctrl | First-fire |
|---|---|---|---|---|---|---|
| LQARP | 0.9987 ± 0.0023 (ms 0.9989 ± 0.0018) | 4.148 ± 1.61 (ms 2.046 ± 0.187) **FLAG** | 8.408 ± 3.939 (ms 4.146 ± 0.348) **FLAG** | 2.228660e-02 ± 0.008729 (ms 1.099000e-02 ± 0.00098) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — |
| E-LQTP | 0.3391 ± 0.06626 (ms 0.9989 ± 0.0018) **FLAG** | 12.117 ± 3.963 (ms 2.050 ± 0.186) **FLAG** | 25.230 ± 9.512 (ms 4.167 ± 0.318) **FLAG** | 1.769579e-01 ± 0.07916 (ms 1.101000e-02 ± 0.00097) **FLAG** | 211.18 ± 34.96 (ms 211.00 ± 34) | 0.708 ± 0.05898 (ms 0.708 ± 0.059) |
| RLOR-inspired | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) | 1.814 ± 0.09341 (ms 1.814 ± 0.093) | 5.360536e-03 ± 0 (ms 5.361000e-03 ± 0) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| Periodic | 1.0000 ± 0 (ms 0.9989 ± 0.0018) | 1.000 ± 0.0006317 (ms 2.046 ± 0.187) **FLAG** | 1.815 ± 0.09444 (ms 4.146 ± 0.348) **FLAG** | 5.362050e-03 ± 3.386e-06 (ms 1.099000e-02 ± 0.00098) **FLAG** | 413.42 ± 0 (ms 413.42 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) |

Flagged cells: 10.

## PDR-drop breakdown (LQARP and RLOR-inspired, Scenarios II and III)

A lost packet is **stale-caused** when the frozen snapshot still passed the candidate-set filters and the live state would not: the transmission failed reception on that hop (`SNR_stale`), the frozen forwarder set was empty while a live filter still admitted an unvisited neighbor (`VOID_stale`), or the packet had already been forwarded across such a hop and then found no live forwarder (`VOID_via_stale`). **Anyway** losses are envelope exit (`LOST_NODE_EXIT`), reception failure on a hop the live filters still admit (`SNR_genuine`), and a void where the live filters are also empty and no earlier hop was stale (`VOID_live`), plus energy, TTL, and end-of-simulation drops (those three are not split out below; they were zero in the manuscript campaign). `envelope_via_stale` is the subset of envelope exits that occurred after a stale hop; those packets stay in the anyway column, matching the requested envelope category.

| Case | Protocol | PDR | Fail pkts | Stale-caused | of which SNR / void-empty / void-after-stale | Anyway | of which envelope / genuine SNR / live void | Stale hops (rx ok) |
|---|---|---:|---:|---:|---|---:|---|---:|
| II v=0.5 | LQARP | 1.0000 | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 | 0 (0 received) |
| II v=1.0 | LQARP | 1.0000 | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 | 0 (0 received) |
| II v=2.0 | LQARP | 1.0000 | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 | 0 (0 received) |
| II v=2.0 | RLOR-inspired | 1.0000 | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 | 0 (0 received) |
| II v=3.0 | LQARP | 0.9993 | 2 | 0 | 0 / 0 / 0 | 2 | 2 / 0 / 0 | 0 (0 received) |
| II v=3.5 | LQARP | 0.9987 | 4 | 0 | 0 / 0 / 0 | 4 | 4 / 0 / 0 | 0 (0 received) |
| III V=2 | LQARP | 0.9987 | 5 | 1 | 1 / 0 / 0 | 4 | 4 / 0 / 0 | 5 (4 received) |
| III V=2 | RLOR-inspired | 1.0000 | 0 | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 | 0 (0 received) |

Sums are over five seeds. Fail pkts = N_gen − N_succ. Stale-caused + anyway equals that difference when energy, TTL, and end-of-simulation losses are zero and the void/SNR splits partition the counters.

## Counter partition

All 100 runs satisfy VOID = VOID_stale + VOID_via_stale + VOID_live and SNR = SNR_stale + SNR_genuine.

## How to read the flags

Scenario I is not a mobility test of the hold. E-LQTP there is built with the identity epsilon and with ticking disabled, so `ingestBroadcastVelocity` never runs. All 10800 E-LQTP packets (five seeds) are `VOID_stale`: the held candidate set is empty while a live range/SNR/depth check still admits an unvisited neighbor. PDR is 0. That is the Step-1 rule applied to a harness that never broadcasts, and it is the mismatch that would be a bug if Table II were required to be unchanged.

LQARP in Scenario I still delivers every packet, but every route is one hop (hops 1.000 ± 0, E_bit 5.361×10⁻³). Discovery freezes every neighbor at E_ini, so c_ene is 0, the reward numerator is 0, Q stays tied, and `nextHop` breaks ties toward the smaller id. The sink is id 0 and is in the candidate set, so it wins. RLOR does not use energy in P_succ; its Scenario I row matches Table II.

Fixed-Periodic Scenario I also delivers only direct hops. Its O_ctrl of 411.28 byte/s is 13161 control packets × 50 bytes / 1600 s (the drain excluded). The Table II value 442.03 byte/s equals this same run's drain-included count, 14145 × 50 / 1600. Scenario II and III periodic O_ctrl match Tables III and V at 413.42 byte/s exactly, so the emission schedule is the manuscript one. The Table II periodic O_ctrl cell is the drain-included figure.

E-LQTP in Scenarios II and III keeps the manuscript trigger: O_ctrl and first-fire stay inside every Table III–V band. Delivery does not. In Scenario II every speed has PDR 0. The losses are almost all `VOID_stale` (held filters admit nobody, live filters would). A few packets fail reception on a stale-admitted hop (`SNR_stale`); `SNR_genuine` is 0. Envelope exits are the rest, plus 6 TTL drops at 2 m/s only. Scenario III E-LQTP PDR is 0.339 ± 0.066, again mostly `VOID_stale`.

## Scenario I loss counters (five-seed sums)

| Protocol | N_gen | N_succ | VOID_stale | VOID_live | SNR_stale | SNR_genuine | Envelope | Stale hops |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LQARP | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |
| E-LQTP | 10800 | 0 | 10800 | 0 | 0 | 0 | 0 | 0 |
| RLOR-inspired | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |
| Periodic | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |

