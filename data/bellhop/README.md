# Bellhop Western Pacific run (24 kHz, 5524 m flat bottom)

Porter BELLHOP coherent transmission loss and eigenray arrivals at the
WOA23 / GEBCO primary cell **20.125°N, 124.125°E**. This is an acoustic
propagation calculation for later Aqua-Sim use. It is **not** an ns-3
result and it is **not** a sea trial.

## Why the bottom is 5524 m, not 500 m

ns-3 places network nodes only in the upper 500 m. Sound rays are not
confined to that slab. GEBCO_2026 at this cell is **5524.25 m**
down. The 2 km east transect (`data/gebco/bathymetry_transect_primary.csv`) varies by only
**2.55 m** peak-to-peak (min 5523.0, max 5525.6).
A range-independent flat bottom at **5524 m** matches that transect.

A 500 m seafloor would insert non-physical bottom-bounce arrivals that
do not exist at this site and would corrupt the multipath transfer
function.

## SSP is the full water column, not 0–500 m

The receiver *grid* is 0–500 m / 10 m, as specified. The *profile* is
not truncated at 500 m. Truncating SSP at 500 m with a 5524 m bottom
makes Bellhop hold `c(500) ≈ 1497 m/s` as an isovelocity fill through
the SOFAR axis (January `c_min = 1481.76 m/s` at 1050 m) and the whole
abyssal layer. That is the same class of error as the 500 m lid.

Construction:

| Depth | Source |
| --- | --- |
| 0–1500 m | WOA23 monthly (January or July), Mackenzie 1981 |
| 1550–5500 m | WOA23 annual at the same cell, Mackenzie 1981 |
| 5524 m | Mackenzie 1981 using annual T,S at 5500 m |

A sensitivity arrivals run with the 0–500 m hold is stored under
`arrivals/*_trunc500_*` so the difference can be cited; it is not the
primary TL.

## Bellhop configuration

| Item | Value |
| --- | --- |
| Model | BELLHOP (Acoustics Toolbox 2024_12_25, Porter) |
| Frequency | 24 kHz |
| Run type (TL) | `CB` coherent, geometric Gaussian, Cartesian |
| Run type (arrivals) | `A` ASCII |
| Source depth | 50 m |
| Receiver depths | 0–500 m, 10 m |
| Receiver ranges | 0–2000 m, 10 m (TL and full-grid arrivals). A 5-range subset (200, 500, 1000, 1500, 2000 m) was the Step E sanity check only. |
| Bottom | flat 5524 m acoustic halfspace |
| Bottom (assumed, not measured) | cp=1600 m/s, cs=0, ρ=1.8 g/cm³, α=0.5 dB/λ |
| Volume attenuation | Thorp (`SSPOPT=CVWT`) |
| Beams | 9601 over [-89.0, 89.0] deg |
| Step / box | 1.0 m, ZBOX=5600.0 m, RBOX=2.1 km |

The halfspace is an assumption. No grab, core, or reflection-coefficient
measurement was used.

## Rebuild

```bash
./scripts/install-bellhop.sh
python3 scripts/run_bellhop_wp.py
```

## Eigenray fractions at src=50 m, rcv=50 m, range=1000 m

Geometric count vs energy (|A|²). At 24 kHz a 5.5 km round-trip to the
seafloor is tens of dB of Thorp plus extra spreading, so count and
energy disagree: many steep rays *exist* and almost none *matter*.

### January (full-column SSP)

| Class | count | count fraction | energy fraction |
| --- | --- | --- | --- |
| Direct / refracted (no bounce) | 2 | 0.083 | 0.670 |
| Surface only | 1 | 0.042 | 0.329 |
| Bottom interacting | 21 | 0.875 | 0.001 |
| Surface-only + direct (no bottom) | 3 | 0.125 | 0.999 |

Resolved arrivals: **24**. Delay span 0.652–29.33 s.
The first bottom cluster is at ~7.28 s (one round trip to 5524 m).

### July (full-column SSP)

| Class | count | count fraction | energy fraction |
| --- | --- | --- | --- |
| Direct / refracted (no bounce) | 1 | 0.040 | 0.550 |
| Surface only | 1 | 0.040 | 0.448 |
| Bottom interacting | 23 | 0.920 | 0.001 |
| Surface-only + direct (no bottom) | 2 | 0.080 | 0.999 |

Resolved arrivals: **25**. Delay span 0.649–29.33 s.

**Count vs energy at this pair.** Bellhop traces ±89°, so it *does* find
steep eigenrays that hit 5524 m (launch angle ≈ 85°). Those are the
majority by count:

- January: **88%** of 24 arrivals hit the bottom;
  only **12%** are surface-only or direct/refracted.
- July: **92%** / **8%**.

They carry almost no energy at 24 kHz. One round trip to 5524 m is an
extra ~11 km; Thorp plus extra spreading puts the first bottom cluster
~40 dB below the water-column arrivals. Energy-weighted:

- January: **99.9%** surface/direct,
  **0.08%** bottom.
- July: **99.9%** /
  **0.12%**.

So: many *resolved geometric paths* reach the seafloor; the *transfer
function on this 0–500 m / 0–2000 m grid at 24 kHz* does not. A fake
500 m lid would have bounced those steep rays 5 km too soon and written
non-physical early bottom arrivals into the CIR.

## Files

```
data/bellhop/
  provenance.json
  ssp/ssp_full_january.csv          ssp_full_july.csv
  env/*.env                         including wp_*_arr_full.env
  tl/january_tl.npz  july_tl.npz
  arrivals/*.csv                    Step E 5-range subset
  arrivals_full_grid_january.h5     201 x 51 grid, CSR eigenrays
  arrivals_full_grid_july.h5
  arrivals_full_grid_extended_january.h5   241 x 51, 0–6 km / 25 m
  arrivals_full_grid_extended_july.h5
  figs/*.png
```

Full-grid HDF5 is the Aqua-Sim input (τ_p, θ_p, n_top/n_bot, d_p).
Channel TL/SNR CSVs built from it: [`data/channel_db/README.md`](../channel_db/README.md).

Raw `.shd` / `.arr` / `.prt` stay next to the env files when the run is
local; they are not required to read the npz/csv/HDF5 products.
