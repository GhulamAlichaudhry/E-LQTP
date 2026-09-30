# Final campaign — decision-trace summary (c_nei dominance)

trace runs compared: 210; SWEEP mismatches vs dataset runs: 1; ('iii', 2.0, 'elqtp-energy', 20260923).

Every primary forwarding decision in every trace run (all scenarios/speeds, five seeds). 'Passed over' = sink was a legal candidate but a relay with higher Q was chosen.

| Scope | Variant | decisions | sink in set | sink chosen | passed over | relay > sink on c_nei | on c_ene | on c_del | median c_nei ratio | median c_ene ratio | NaN/Inf Q |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all cases | LQARP | 102945 | 80573 | 39.6% | 48663 (60.4%) | 94.4% | 22.8% | 0.0% | 403 | 1 | 0 |
| all cases | E-LQTP (no beacon) | 103947 | 81177 | 39.2% | 49350 (60.8%) | 94.6% | 22.7% | 0.0% | 403 | 1 | 0 |
| all cases | E-LQTP+energy (18-bit) | 92622 | 61722 | 52.0% | 29611 (48.0%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.115 | 0 |
| all cases | E-LQTP+energy, trigger OFF | 91982 | 61195 | 52.5% | 29063 (47.5%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.115 | 0 |
| all cases | Fixed-Periodic (T=5 s) | 94399 | 63007 | 51.3% | 30691 (48.7%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.112 | 0 |
| all cases | RLOR-inspired | 53611 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
| II 2.0 m/s | LQARP | 16660 | 13934 | 25.3% | 10408 (74.7%) | 93.3% | 27.2% | 0.0% | 148 | 1 | 0 |
| II 2.0 m/s | E-LQTP (no beacon) | 16469 | 13799 | 25.6% | 10273 (74.4%) | 93.6% | 27.3% | 0.0% | 148 | 1 | 0 |
| II 2.0 m/s | E-LQTP+energy (18-bit) | 10452 | 7095 | 50.4% | 3520 (49.6%) | 100.0% | 0.0% | 0.0% | 2.98e+03 | 0.137 | 0 |
| II 2.0 m/s | E-LQTP+energy, trigger OFF | 10315 | 6998 | 51.1% | 3421 (48.9%) | 100.0% | 0.0% | 0.0% | 2.98e+03 | 0.138 | 0 |
| II 2.0 m/s | Fixed-Periodic (T=5 s) | 10743 | 7319 | 49.1% | 3729 (50.9%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.164 | 0 |
| II 2.0 m/s | RLOR-inspired | 5765 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
| III | LQARP | 15789 | 13257 | 27.4% | 9630 (72.6%) | 100.0% | 0.4% | 0.0% | 2.98e+03 | 1 | 0 |
| III | E-LQTP (no beacon) | 16653 | 13776 | 26.3% | 10154 (73.7%) | 100.0% | 1.5% | 0.0% | 2.98e+03 | 1 | 0 |
| III | E-LQTP+energy (18-bit) | 10139 | 7109 | 51.2% | 3466 (48.8%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.16 | 0 |
| III | E-LQTP+energy, trigger OFF | 10005 | 7036 | 51.7% | 3396 (48.3%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.166 | 0 |
| III | Fixed-Periodic (T=5 s) | 10575 | 7349 | 49.5% | 3712 (50.5%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.132 | 0 |
| III | RLOR-inspired | 5682 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
| I | LQARP | 17496 | 10746 | 100.0% | 0 (0.0%) | — | — | — | — | — | 0 |
| I | E-LQTP (no beacon) | 17496 | 10746 | 100.0% | 0 (0.0%) | — | — | — | — | — | 0 |
| I | E-LQTP+energy (18-bit) | 30548 | 19518 | 55.3% | 8729 (44.7%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.0509 | 0 |
| I | E-LQTP+energy, trigger OFF | 30548 | 19518 | 55.3% | 8729 (44.7%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.0509 | 0 |
| I | Fixed-Periodic (T=5 s) | 30677 | 19573 | 55.1% | 8782 (44.9%) | 100.0% | 0.0% | 0.0% | 8.1e+03 | 0.0536 | 0 |
| I | RLOR-inspired | 18252 | 0 | — | 0 (—) | — | — | — | — | — | 0 |
