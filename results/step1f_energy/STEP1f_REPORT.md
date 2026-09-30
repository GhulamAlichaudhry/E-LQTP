# Step 1f — E-LQTP energy-only refresh (5 s), pose trigger unchanged

## Change

`elqtp-energy` is E-LQTP plus an independent beacon that overwrites `energy_j_zoh` every 5 s for neighbors that already have a hold. Pose and velocity (`x/y/z_j_zoh`, `vx/vy/vz_j_zoh`) still move only on bootstrap and the persistence-gated HELLO. `c_nei`, `N_stab`, the persistence gate, and reward weights are unchanged.

The energy beacons are **not** in `O_ctrl`. They are `O_ene` (same 400-bit packet, one per node per grid).

Re-run: Scenario II and III at 2 m/s, seeds 20260921–20260925, `--hopDiag`.

## Five-seed means

| Protocol | II hops | II T_e2e (s) | II pass-over | III hops | III T_e2e (s) | III pass-over | O_ctrl (byte/s) | O_ene (byte/s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E-LQTP (Step 1d) | 4.975 | 9.731 | 79.6% | 8.218 | 16.789 | 87.9% | 179 / 286 | 0 |
| LQARP-refreshed (Step 1e) | 1.000 | 1.845 | 0% | 1.000 | 1.815 | ~0% | 0 | 0 |
| **elqtp-energy** | **1.000** | **1.845** | **0%** (0/3599) | **1.001** | **1.815** | **0.1%** (2/3650) | **178.7 / 286.8** | **410** |

PDR = 1.000 on all ten `elqtp-energy` runs. Of the two Scenario III pass-overs, both had `c_nei` larger on the relay. There were no pass-overs in Scenario II, so `c_nei` did not get a chance to dominate.

`O_ene` is 410 byte/s on every run: 120 grids × 41 nodes × 50 bytes / 600 s (t = 5, 10, …, 600; t = 0 is not an extra energy beacon). `O_ctrl` matches the original E-LQTP split (event + bootstrap). The position trigger did not slow down: Scenario II event HELLOs 638 vs 642, Scenario III 1928 vs 1920.

## Reading

Refreshing **energy alone**, on the same 5 s cadence as LQARP-refreshed, is enough to take E-LQTP from ~5 / ~8 hops down to one hop. Pose holds and the event trigger stay as they were. The long paths in Step 1d needed **stale, uneven `energy_j_zoh`** so that `c_ene` could leave the zero tie and let `c_nei` inflate Q. Once energy is kept current, that tie holds and the sink is selected.

This lines up with Step 1e: a 5 s refresh of LQARP’s whole hold also went to one hop. The extra piece here is that **energy is the field that matters**. The position trigger’s own HELLO rate, and therefore `O_ctrl`, is essentially unchanged.

Nothing was retuned.
