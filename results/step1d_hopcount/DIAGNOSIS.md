# Step 1d — why the mobile hop count rose

Read-only counts from the Step 1c binary (`--hopDiag`). Next-hop selection, `N_stab`, the persistence gate, and the reward weights were not changed. Five seeds `20260921`–`20260925`, `N=40`, January, `β1=β2=0`, boundary removal. Scenario II and III at 2 m/s, `T_sim=600` s. Headline means match `results/step1c_rerun/` (Scenario II E-LQTP 4.975 hops, LQARP 2.241; Scenario III E-LQTP 8.218, LQARP 4.148), so the probe did not move the route.

Scenario I is not re-run here. Its collapse to 1.000 hops for LQARP, E-LQTP, and Fixed-Periodic, with every relay inside one hop of the sink, still stands: multi-hop is not required by the static geometry.

## What was counted

On every forwarding decision, after the candidate set and the Q update the protocol already performs:

1. Whether sink 0 was in the action set, and whether it was the selected hop.
2. If it was absent, the first held filter that failed (`unheard`, held range, held SNR, held depth, `N_stab`), the age of the E-LQTP hold, and the pose error of that hold against the live sink.
3. Whether the sink was a live one-hop neighbor (range ∩ candidate SNR ∩ depth), and, for each generated packet, the live breadth-first hop distance to the sink at the source.
4. When the sink was in the set and a relay was chosen: `Q`, and `c_ene`, `c_del`, `c_nei` of the relay versus the sink.

`N_stab` is `{broadcast_k = 0 or |e_k| < ε_k}`. A miss is possible only when `broadcast_k ≠ 0` and `|e_k| ≥ ε_k`.

## Result

The sink is not being filtered out.

| Run | Decisions | Sink in the action set | Sink then selected | `N_stab` misses | Held-SNR misses | Live shortest path is 1 | Of those, path was longer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| II E-LQTP | 17644 | 17643 | 3599 (20.4%) | 0 | 1 | 3598 / 3599 | 1859 (51.7%) |
| II LQARP | 7910 | 7909 | 3599 (45.5%) | 0 | 1 | 3598 / 3599 | 1085 (30.2%) |
| II Fixed-Periodic | 3600 | 3599 | 3599 (100%) | 0 | 1 | 3598 / 3599 | 0 |
| III E-LQTP | 29810 | 29810 | 3608 (12.1%) | 0 | 0 | 3608 / 3608 | 2926 (81.1%) |
| III LQARP | 15169 | 15169 | 3643 (24.0%) | 0 | 0 | 3643 / 3643 | 2054 (56.4%) |
| III Fixed-Periodic (seed 20260921) | 722 | 722 | 722 (100%) | 0 | 0 | 722 / 722 | 0 |

The single miss is the same decision in all three Scenario II protocols: seed `20260925`, node 3, `t=270` s, held SNR, pose error 0 m, and the live geometric test fails as well. E-LQTP’s hold was 270 s old because `|e_k|=0 < ε_k=4.24` and `broadcast_k=0`, so the trigger correctly did not refresh. Fixed-Periodic had refreshed 5 s earlier and failed the same way. That hop does not produce the 2–4× path length.

`N_stab` excluded the sink on none of the 74,155 decisions. The tie-break never selected a relay over the sink at equal `Q` (`chosen_worse=0`). When E-LQTP or LQARP did select the sink in Scenario II, it was a `Q` tie broken by the sink’s id, or the sink was the only action. It was not a higher-`Q` win.

## What lengthens the path

On every decision that passed over the sink, the relay’s `Q` was strictly larger. The factor that is larger for the relay on every one of those decisions is `c_nei = exp(|I(s_j)|)`.

| Pass-overs | `c_ene` relay > sink | `c_ene` equal | `c_ene` relay < sink | `c_del` relay > sink | `c_nei` relay > sink |
| --- | ---: | ---: | ---: | ---: | ---: |
| II E-LQTP, 14044 | 0 | 14044 | 0 | 0 | 14044 |
| II LQARP, 4310 | 0 | 4310 | 0 | 0 | 4310 |
| III E-LQTP, 26202 | 1608 | 23478 | 1116 | 0 | 26202 |
| III LQARP, 11526 | 0 | 11526 | 0 | 0 | 11526 |

`c_del` favors the sink on every pass-over, because the sink is the shallowest node. `c_ene` does not pick the relay: in Scenario II it is the same value on both ends (mean about `6×10⁻⁵` for E-LQTP and `2×10⁻⁵` for LQARP). In Scenario III E-LQTP the relay’s held energy is higher on 6.1% of pass-overs and lower on 4.3%. That is not an energy-balancing policy.

`c_nei(sink)` is `exp(0) = 1`, because the depth rule gives the sink an empty forward set. A relay with a populated forward set has `c_nei` of hundreds to `exp(≈30)`. Once `c_ene` is a nonzero common factor, that ratio dominates `R`, and the TD backup keeps the relay’s `Q` above the sink afterwards. Early samples at `t=90` s already show `R = 0` (energies still equal, so `c_ene = 0`) while `Q` of the relay is `~10⁵` from an earlier backup. Held energies in those samples are `10000 J` on both the relay and the sink.

Fixed-Periodic never passes over the sink. On 3285 of 3599 Scenario II decisions the sink’s `Q` is strictly best while other candidates are present, so the `c_nei` backup does not get started. That is why its data plane stays at one hop even though the same live geometry is one hop for the other two protocols.

## Classification

This is not a remaining `N_stab`, tie-break, or stale-candidate bug. The sink’s held pose error on the only exclusion is 0 m, and the live test fails with it.

It is also not held-energy balancing through `c_ene` / `c_del`. Those two factors do not prefer the relay. The extra hops are the neighbor-count term `c_nei`, amplified by the Q backup, on a geometry whose live shortest path is one hop.

E-LQTP passes over the sink more often than LQARP (80% of Scenario II decisions versus 54%; 88% versus 76% in Scenario III). Both use the same `c_nei`. LQARP’s frozen discovery energy simply stays at the zero-reward tie longer.

## Open question

LQARP freezes neighbor energy at first discovery, and E-LQTP rewrites it only on bootstrap and on a later HELLO. The hop gap is not evidence that E-LQTP is spending relays to balance energy that LQARP cannot see. A periodic energy refresh on LQARP might change how often `c_ene` leaves zero, and could move LQARP toward the one-hop periodic regime or toward E-LQTP’s longer paths. That comparison is not decided here, and neither `N_stab`, the persistence gate, nor the reward weights were retuned.
