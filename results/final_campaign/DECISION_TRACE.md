# Final campaign — decision-trace summary (c_nei dominance)

trace runs compared: 210; SWEEP mismatches vs dataset runs: 0.

Every primary forwarding decision in every trace run (all scenarios/speeds, five seeds). 'Passed over' = sink was a legal candidate but a relay with higher Q was chosen.

| Scope | Variant | decisions | sink in set | sink chosen | passed over | relay > sink on c_nei | on c_ene | on c_del | median c_nei ratio | median c_ene ratio | NaN/Inf Q |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all cases | LQARP | 103144 | 80560 | 39.6% | 48659 (60.4%) | 94.4% | 22.8% | 0.0% | 403 | 1 | 247 |
| all cases | E-LQTP (no beacon) | 104177 | 81194 | 39.2% | 49376 (60.8%) | 94.6% | 22.7% | 0.0% | 403 | 1 | 278 |
| all cases | E-LQTP+energy (18-bit) | 92862 | 61815 | 51.9% | 29729 (48.1%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.114 | 292 |
| all cases | E-LQTP+energy, trigger OFF | 92189 | 61254 | 52.4% | 29146 (47.6%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.115 | 321 |
| all cases | Fixed-Periodic (T=5 s) | 94591 | 63046 | 51.2% | 30755 (48.8%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.112 | 362 |
| all cases | RLOR-inspired | 53611 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
| II 2.0 m/s | LQARP | 16660 | 13934 | 25.3% | 10408 (74.7%) | 93.3% | 27.2% | 0.0% | 148 | 1 | 0 |
| II 2.0 m/s | E-LQTP (no beacon) | 16469 | 13799 | 25.6% | 10273 (74.4%) | 93.6% | 27.3% | 0.0% | 148 | 1 | 0 |
| II 2.0 m/s | E-LQTP+energy (18-bit) | 10452 | 7095 | 50.4% | 3520 (49.6%) | 100.0% | 0.0% | 0.0% | 2.98e+03 | 0.137 | 0 |
| II 2.0 m/s | E-LQTP+energy, trigger OFF | 10315 | 6998 | 51.1% | 3421 (48.9%) | 100.0% | 0.0% | 0.0% | 2.98e+03 | 0.138 | 0 |
| II 2.0 m/s | Fixed-Periodic (T=5 s) | 10743 | 7319 | 49.1% | 3729 (50.9%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.164 | 0 |
| II 2.0 m/s | RLOR-inspired | 5765 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
| III | LQARP | 15988 | 13244 | 27.3% | 9626 (72.7%) | 100.0% | 0.4% | 0.0% | 2.98e+03 | 1 | 247 |
| III | E-LQTP (no beacon) | 16883 | 13793 | 26.2% | 10180 (73.8%) | 100.0% | 1.5% | 0.0% | 2.98e+03 | 1 | 278 |
| III | E-LQTP+energy (18-bit) | 10379 | 7202 | 50.2% | 3584 (49.8%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.14 | 292 |
| III | E-LQTP+energy, trigger OFF | 10212 | 7095 | 51.0% | 3479 (49.0%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.148 | 321 |
| III | Fixed-Periodic (T=5 s) | 10767 | 7388 | 48.9% | 3776 (51.1%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.128 | 362 |
| III | RLOR-inspired | 5682 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
| I | LQARP | 17496 | 10746 | 100.0% | 0 (0.0%) | — | — | — | — | — | 0 |
| I | E-LQTP (no beacon) | 17496 | 10746 | 100.0% | 0 (0.0%) | — | — | — | — | — | 0 |
| I | E-LQTP+energy (18-bit) | 30548 | 19518 | 55.3% | 8729 (44.7%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.0509 | 0 |
| I | E-LQTP+energy, trigger OFF | 30548 | 19518 | 55.3% | 8729 (44.7%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.0509 | 0 |
| I | Fixed-Periodic (T=5 s) | 30677 | 19573 | 55.1% | 8782 (44.9%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.0536 | 0 |
| I | RLOR-inspired | 18252 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
