# Quantized energy beacon (Step 1f, re-billed)

The 5 s energy channel is unchanged except for what it stores and how it is billed. Pose and velocity holds, `c_nei`, `N_stab`, the persistence gate, and the reward weights are untouched. A position-trigger HELLO still writes a full-precision residual when it fires; the 5 s beacon overwrites `energy_j_zoh` with the quantized value.

## Beacon

Uniform quantizer on `[0, E_ini]`, `E_ini = 10000 J`:

```
code = round(clip(E, 0, E_ini) / E_ini * (2^b - 1))
E_q  = code * E_ini / (2^b - 1)
```

Addressing is an 8-bit sender id (41 nodes). The beacon is one broadcast per node per 5 s grid (t = 5, 10, …, 600; 120 grids × 41 nodes = 4920 beacons). It is not in `O_ctrl`.

```
beacon bits = b + 8
O_ene = 4920 * (b + 8) / 8 / 600   byte/s
```

Fixed-Periodic’s control cost on these runs is 413.42 byte/s.

## What was re-measured

Full-precision Step 1f (b effectively infinite, billed at 400 bits) was 1.000 / 1.001 hops and ~0% pass-over. That does not survive coarse quantization. Every pass-over that reappeared had `c_nei` larger on the relay.

| b | step (J) | beacon (bits) | II hops | II pass-over | II O_ctrl+O_ene | III hops | III pass-over | III O_ctrl+O_ene | under 413.42 | hops ~1 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 8 | 39.22 | 16 | 1.573 | 36.9% | 195.12 | 2.546 | 61.1% | 303.08 | yes | no |
| 12 | 2.442 | 20 | 2.454 | 59.7% | 198.03 | 2.514 | 60.4% | 307.00 | yes | no |
| 16 | 0.153 | 24 | 1.000 | 0% | 203.32 | 2.040 | 51.0% | 311.25 | yes | II only |
| 17 | 0.076 | 25 | 1.000 | 0% | 204.34 | 2.116 | 53.0% | 312.19 | yes | II only |
| **18** | **0.0381** | **26** | **1.000** | **0%** | **205.37** | **1.001** | **0.05%** | **313.43** | **yes** | **yes** |
| 19 | 0.0191 | 27 | 1.000 | 0% | 206.39 | 1.001 | 0.05% | 314.46 | yes | yes |
| 20 | 0.00954 | 28 | 1.000 | 0% | 207.42 | 1.001 | 0.1% | 315.48 | yes | yes |
| 24 | 5.96e-4 | 32 | 1.000 | 0% | 211.52 | 1.001 | 0.1% | 319.58 | yes | yes |
| 32 | 2.33e-6 | 40 | 1.000 | 0% | 219.68 | 1.000 | 0% | 327.78 | yes | yes |

Five seeds `20260921`–`20260925`, Scenario II and III at 2 m/s. PDR is 0.996 / 0.993 at 8 bits and 1.000 at 18 bits and above. The 12-bit row is worse than 8-bit in Scenario II, so hop count is not monotone in `b`.

## Trade-off

Inside the 8–16 bit residual range, no width keeps both scenarios near one hop. 16 bits restores Scenario II (pass-over 0%, hops 1.000, total 203 byte/s) and leaves Scenario III at 2.04 hops with a 51% pass-over. 17 bits still fails Scenario III (2.12 hops, 53%).

The smallest width in this sweep that does both jobs is **18 bits of residual plus the 8-bit sender id (26-bit beacon)**:

- Scenario II: hops 1.000, delay 1.845 s, pass-over 0/3599, total overhead **205.37** byte/s.
- Scenario III: hops 1.001, delay 1.815 s, pass-over 2/3650, total overhead **313.43** byte/s.
- Both totals are below Fixed-Periodic’s 413.42 byte/s. The position-trigger `O_ctrl` stays about 179 byte/s in Scenario II and 287 byte/s in Scenario III. `O_ene` at 26 bits is 26.65 byte/s.

Coarser than that, the overhead is even smaller and the sink-avoiding bias comes back. Finer than that, hops stay at one and the bill rises by 1.025 byte/s per extra residual bit, still under 413.42 out to a 40-bit beacon.
