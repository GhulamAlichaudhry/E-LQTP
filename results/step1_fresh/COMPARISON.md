# Step-1c re-run vs manuscript Tables II–V

Held/frozen neighbor pose and energy. `c_lin`, `linkSample`, `predictPair`, and `predictForecast` still query the live channel. Seeds 20260921–20260925, N=40, January site, boundary=remove, β1=β2=0. Drift sweep 0.5–3.5 m/s. Eddy: Rankine core R=2000 m at (3000, 3000), V=2 m/s, Gauss–Markov ζ=0.95, σ=(1, 1, 0). Means are five-seed; deviations are the sample standard deviation (n−1).

### Scenario I (manuscript Table II)

| Protocol | PDR | Hops | T_e2e | E_bit | O_ctrl | First-fire |
|---|---|---|---|---|---|---|
| LQARP | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.530 ± 0.068) **FLAG** | 1.887 ± 0.1078 (ms 3.078 ± 0.071) **FLAG** | 5.360536e-03 ± 0 (ms 8.200000e-03 ± 0.00037) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — |
| E-LQTP | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.530 ± 0.068) **FLAG** | 1.887 ± 0.1078 (ms 3.078 ± 0.071) **FLAG** | 5.360536e-03 ± 0 (ms 8.200000e-03 ± 0.00037) **FLAG** | 46.94 ± 1.739 (ms 0.00 ± 0) **FLAG** | — |
| RLOR-inspired | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) | 1.887 ± 0.1078 (ms 1.887 ± 0.108) | 5.360536e-03 ± 0 (ms 5.360000e-03 ± 0) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| Periodic | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.546 ± 0.039) **FLAG** | 1.887 ± 0.1078 (ms 3.119 ± 0.188) **FLAG** | 5.360536e-03 ± 0 (ms 8.290000e-03 ± 0.00021) **FLAG** | 411.28 ± 0 (ms 442.03 ± 0) **FLAG** | 1.000 ± 0 |

Flagged cells: 11.

**Scenario I is not numerically identical to Table II.** 11 cell(s) fall outside the manuscript band. PDR is 1 for every protocol. The hop, delay, and energy flags are the held residual energy: discovery and bootstrap freeze E_ini, c_ene stays 0, and the tie-break selects the sink. E-LQTP's O_ctrl flag is the bootstrap HELLO charge (event HELLOs are 0 because the EKF is not ticked). RLOR matches Table II.

### Scenario II at 2 m/s (manuscript Table III)

| Protocol | PDR | Hops | T_e2e | E_bit | O_ctrl | First-fire |
|---|---|---|---|---|---|---|
| LQARP | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 2.241 ± 0.9251 (ms 2.153 ± 0.187) | 4.212 ± 1.962 (ms 4.438 ± 0.277) | 1.201496e-02 ± 0.004959 (ms 1.156000e-02 ± 0.001) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| E-LQTP | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 4.975 ± 1.49 (ms 2.154 ± 0.187) **FLAG** | 9.731 ± 2.885 (ms 4.439 ± 0.277) **FLAG** | 2.666809e-02 ± 0.007987 (ms 1.156000e-02 ± 0.001) **FLAG** | 179.08 ± 32.83 (ms 135.00 ± 23) **FLAG** | 0.985 ± 0.01 (ms 0.782 ± 0.042) **FLAG** |
| RLOR-inspired | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0.0005726 (ms 1.000 ± 0.001) | 1.845 ± 0.07412 (ms 1.845 ± 0.074) | 5.361909e-03 ± 3.07e-06 (ms 5.362000e-03 ± 0) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| Periodic | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 1.000 ± 0.0005726 (ms 2.153 ± 0.187) **FLAG** | 1.845 ± 0.07398 (ms 4.438 ± 0.277) **FLAG** | 5.361909e-03 ± 3.07e-06 (ms 1.156000e-02 ± 0.001) **FLAG** | 413.42 ± 0 (ms 413.42 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) |

Flagged cells: 8.

### Scenario II drift sweep (manuscript Table IV)

| v | Protocol | PDR | T_e2e | Hops | O_ctrl | First-fire | E_bit (not in table) |
|---:|---|---|---|---|---|---|---|
| 0.5 | LQARP | 1.0000 ± 0 (ms 1.0000 ± 0) | 2.041 ± 0.3798 (ms 4.776 ± 0.403) **FLAG** | 1.101 ± 0.2268 (ms 2.282 ± 0.186) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 5.904140e-03 ± 0.001216 |
| 0.5 | E-LQTP | 1.0000 ± 0 (ms 1.0000 ± 0) | 3.482 ± 2.079 (ms 4.776 ± 0.403) **FLAG** | 1.803 ± 0.9747 (ms 2.282 ± 0.186) **FLAG** | 127.92 ± 2.776 (ms 20.20 ± 4.2) **FLAG** | 0.939 ± 0.01556 (ms 0.146 ± 0.021) **FLAG** | 9.664987e-03 ± 0.005225 |
| 1.0 | LQARP | 1.0000 ± 0 (ms 0.9995 ± 0.0012) | 2.736 ± 0.9525 (ms 4.752 ± 0.377) **FLAG** | 1.477 ± 0.4617 (ms 2.289 ± 0.208) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 7.916790e-03 ± 0.002475 |
| 1.0 | E-LQTP | 0.9992 ± 0.001853 (ms 0.9995 ± 0.0012) | 6.259 ± 2.839 (ms 4.752 ± 0.377) **FLAG** | 3.121 ± 1.358 (ms 2.289 ± 0.208) **FLAG** | 134.52 ± 3.29 (ms 70.70 ± 6.2) **FLAG** | 0.968 ± 0.01386 (ms 0.520 ± 0.031) **FLAG** | 1.673571e-02 ± 0.007285 |
| 2.0 | LQARP | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 4.212 ± 1.962 (ms 4.438 ± 0.277) | 2.241 ± 0.9251 (ms 2.153 ± 0.187) | 0.00 ± 0 (ms 0.00 ± 0) | — | 1.201496e-02 ± 0.004959 |
| 2.0 | E-LQTP | 1.0000 ± 0 (ms 0.9992 ± 0.0019) | 9.731 ± 2.885 (ms 4.439 ± 0.277) **FLAG** | 4.975 ± 1.49 (ms 2.154 ± 0.187) **FLAG** | 179.08 ± 32.83 (ms 135.10 ± 23.1) **FLAG** | 0.985 ± 0.01 (ms 0.782 ± 0.042) **FLAG** | 2.666809e-02 ± 0.007987 |
| 3.0 | LQARP | 0.9993 ± 0.001459 (ms 1.0000 ± 0) **FLAG** | 5.276 ± 1.737 (ms 4.431 ± 0.333) **FLAG** | 2.812 ± 0.8946 (ms 2.154 ± 0.203) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 1.510095e-02 ± 0.00484 |
| 3.0 | E-LQTP | 0.9958 ± 0.00442 (ms 1.0000 ± 0) **FLAG** | 11.439 ± 2.129 (ms 4.433 ± 0.331) **FLAG** | 5.994 ± 1.114 (ms 2.155 ± 0.203) **FLAG** | 255.27 ± 55.38 (ms 213.80 ± 39.1) **FLAG** | 0.991 ± 0.01044 (ms 0.857 ± 0.034) **FLAG** | 3.232673e-02 ± 0.006054 |
| 3.5 | LQARP | 0.9987 ± 0.00141 (ms 1.0000 ± 0) **FLAG** | 5.824 ± 1.787 (ms 4.200 ± 0.393) **FLAG** | 3.128 ± 0.9253 (ms 2.063 ± 0.215) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — | 1.679613e-02 ± 0.004959 |
| 3.5 | E-LQTP | 0.9974 ± 0.002482 (ms 1.0000 ± 0) **FLAG** | 12.149 ± 1.792 (ms 4.200 ± 0.393) **FLAG** | 6.355 ± 1.004 (ms 2.063 ± 0.215) **FLAG** | 298.62 ± 62.64 (ms 257.70 ± 46.9) | 0.995 ± 0.005771 (ms 0.897 ± 0.028) **FLAG** | 3.413671e-02 ± 0.005382 |

Flagged cells: 31.

### Scenario III (manuscript Table V)

| Protocol | PDR | Hops | T_e2e | E_bit | O_ctrl | First-fire |
|---|---|---|---|---|---|---|
| LQARP | 0.9987 ± 0.0023 (ms 0.9989 ± 0.0018) | 4.148 ± 1.61 (ms 2.046 ± 0.187) **FLAG** | 8.408 ± 3.939 (ms 4.146 ± 0.348) **FLAG** | 2.228660e-02 ± 0.008729 (ms 1.099000e-02 ± 0.00098) **FLAG** | 0.00 ± 0 (ms 0.00 ± 0) | — |
| E-LQTP | 0.9892 ± 0.01196 (ms 0.9989 ± 0.0018) **FLAG** | 8.218 ± 0.3929 (ms 2.050 ± 0.186) **FLAG** | 16.789 ± 1.09 (ms 4.167 ± 0.318) **FLAG** | 4.428326e-02 ± 0.002112 (ms 1.101000e-02 ± 0.00097) **FLAG** | 286.15 ± 24.14 (ms 211.00 ± 34) **FLAG** | 0.987 ± 0.008011 (ms 0.708 ± 0.059) **FLAG** |
| RLOR-inspired | 1.0000 ± 0 (ms 1.0000 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) | 1.814 ± 0.09341 (ms 1.814 ± 0.093) | 5.360536e-03 ± 0 (ms 5.361000e-03 ± 0) | 0.00 ± 0 (ms 0.00 ± 0) | — |
| Periodic | 1.0000 ± 0 (ms 0.9989 ± 0.0018) | 1.000 ± 0.0006317 (ms 2.046 ± 0.187) **FLAG** | 1.815 ± 0.09444 (ms 4.146 ± 0.348) **FLAG** | 5.362050e-03 ± 3.386e-06 (ms 1.099000e-02 ± 0.00098) **FLAG** | 413.42 ± 0 (ms 413.42 ± 0) | 1.000 ± 0 (ms 1.000 ± 0) |

Flagged cells: 12.

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

## Control-cost split

O_ctrl charges event HELLOs and bootstrap HELLOs together. A bootstrap HELLO is one 400-bit packet per directed pair, written the first time that pair passes live range and SNR. Event HELLOs are the rising-edge count (E-LQTP) or the T_ctrl count (Fixed-Periodic). Fixed-Periodic already ingests at t=0, so its bootstrap count stays 0.

| Case | Protocol | O_ctrl | Event byte/s | Bootstrap byte/s | Event HELLOs | Bootstrap HELLOs |
|---|---|---:|---:|---:|---:|---:|
| I | E-LQTP | 46.94 | 0.00 | 46.94 | 0 | 7511 |
| I | Periodic | 411.28 | 411.28 | 0.00 | 65805 | 0 |
| II v=0.5 | E-LQTP | 127.92 | 2.70 | 125.22 | 162 | 7513 |
| II v=1.0 | E-LQTP | 134.52 | 9.27 | 125.25 | 556 | 7515 |
| II v=2.0 | E-LQTP | 179.08 | 53.52 | 125.57 | 3211 | 7534 |
| II v=3.0 | E-LQTP | 255.27 | 129.57 | 125.70 | 7774 | 7542 |
| II v=3.5 | E-LQTP | 298.62 | 172.88 | 125.73 | 10373 | 7544 |
| II v=2.0 | Periodic | 413.42 | 413.42 | 0.00 | 24805 | 0 |
| III | E-LQTP | 286.15 | 159.97 | 126.18 | 9598 | 7571 |
| III | Periodic | 413.42 | 413.42 | 0.00 | 24805 | 0 |

## Counter partition

All 100 runs satisfy VOID = VOID_stale + VOID_via_stale + VOID_live and SNR = SNR_stale + SNR_genuine.

## How to read the flags

Scenario I still does not step the EKF. Bootstrap runs from the first candidate-set query, so E-LQTP has a held neighbor snapshot without a trigger tick. LQARP and that bootstrap both freeze residual energy at first contact, so c_ene is 0 while every discovered neighbor still holds E_ini, Q stays tied, and the tie-break selects the sink. RLOR does not use energy in P_succ.

O_ctrl in this re-run includes bootstrap HELLOs. A flagged O_ctrl or first-fire cell is that added discovery, not a change to the persistence gate. First-fire is the fraction of live pairs whose held state has been written; bootstrap sets that bit at first contact, so the fraction is no longer the trigger-fire rate. The event-byte/s column above is the rising-edge or T_ctrl cost alone.

Fixed-Periodic already copies neighbor state at t=0 and does not add a second bootstrap charge. Its Scenario I O_ctrl of about 411.28 byte/s is 13161 control packets × 50 bytes / 1600 s with the drain excluded. Table II prints 442.03 byte/s, which equals the drain-included count 14145 × 50 / 1600. Scenarios II and III periodic O_ctrl remain the drain-excluded grid.

## Scenario I loss counters (five-seed sums)

| Protocol | N_gen | N_succ | VOID_stale | VOID_live | SNR_stale | SNR_genuine | Envelope | Stale hops |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LQARP | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |
| E-LQTP | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |
| RLOR-inspired | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |
| Periodic | 10800 | 10800 | 0 | 0 | 0 | 0 | 0 | 0 |

