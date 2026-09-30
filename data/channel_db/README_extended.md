# Extended-range channel database (Step G) — 0–6 km

Same Western Pacific primary cell (20.125°N, 124.125°E), flat **5524 m**
bottom (GEBCO 2 km east transect, ptp 2.55 m — no new bathymetry), full-column
WOA23 January/July SSP (not truncated at 500 m), src = 50 m, 24 kHz, coherent
geometric Gaussian beams, Thorp volume attenuation, SL = 175 dB, DI = 0,
NL = 65.77 dB (reused Step-F band-integrated Wenz; s = 0.2 and
w = 2 m/s remain **design assumptions**, not WOA/GEBCO).

**Why 6 km.** The 0–2 km grid had SNR > 8.68 dB at 100% of z ≥ 10 m cells
and ~50 dB of margin at 1 km, so link-quality voids could not appear.
6 km is past LQARP's reported 4 km operational range, so the grid can
capture the SNR = 8.68 dB transition if it exists at this site.

Range grid: 0, 25, …, 6000 m (**241 points**, 240 × 25 m intervals; the
inclusive analog of the 201-point 0–2000/10 m grid). Depths unchanged
(0–500 m / 10 m, 51). RBOX = 6.15 km (was 2.10 km). NBEAMS = 9601.

H_eq, Thorp, κ = 2, d_p = τ_p × c(z_src), and TL = −10 log10(G_bar) are
**identical** to Step F.

## G3 — threshold crossing (key result)

Horizontal link, receiver depth = 50 m (matches source):

- SNR crosses 8.68 dB at approximately **5125 m** in January (SNR 8.30 dB at that cell; SNR at 6 km = 6.31 dB). Isolated fades appear from 5125 m; the last contiguous below-threshold interval runs **5800–6000 m**.
- SNR crosses 8.68 dB at approximately **4525 m** in July (SNR 8.03 dB at that cell; SNR at 6 km = 2.58 dB). Isolated fades from 4525 m; SNR stays below from **5150 m to 6000 m**.

The crossing is **not** a single depth-independent range. First-drop values span ~4.2–5.7 km across the four probe depths. January at 10 m almost never stays below threshold (2 of 240 ranges; SNR at 6 km is still 10.42 dB). July is harsher at every depth.

### Crossing vs receiver depth

**January**

| Depth (m) | first range SNR < 8.68 dB | SNR at crossing | SNR at 6 km | below-threshold fraction along depth |
| --- | --- | --- | --- | --- |
| 50 | 5125 m | 8.30 dB | 6.31 dB | 12.5% (30/240) |
| 10 | 4600 m | 7.38 dB | 10.42 dB | 0.8% (2/240) |
| 250 | 5200 m | 6.51 dB | 8.94 dB | 5.4% (13/240) |
| 500 | 5650 m | 8.49 dB | 7.27 dB | 3.8% (9/240) |

**July**

| Depth (m) | first range SNR < 8.68 dB | SNR at crossing | SNR at 6 km | below-threshold fraction along depth |
| --- | --- | --- | --- | --- |
| 50 | 4525 m | 8.03 dB | 2.58 dB | 17.5% (42/240) |
| 10 | 4250 m | 7.11 dB | -0.18 dB | 18.3% (44/240) |
| 250 | 4650 m | 6.43 dB | 7.70 dB | 10.0% (24/240) |
| 500 | 5050 m | 6.04 dB | 4.39 dB | 8.8% (21/240) |

### Fraction of cells with SNR > 8.68 dB by range band

Hydrophones at z ≥ 10 m only (z = 0 is the pressure-release artifact).
Range 0 m is excluded (Bellhop singularity, NaN). Bands are (lo, hi]
except the first band which is (0, 1000].

| Range band | January frac SNR>8.68 (z≥10 m) | July frac SNR>8.68 (z≥10 m) | January median SNR | July median SNR |
| --- | --- | --- | --- | --- |
| 0-1000m | 100.0% (2000/2000) | 100.0% (2000/2000) | 53.3 dB | 53.3 dB |
| 1000-2000m | 100.0% (2000/2000) | 100.0% (2000/2000) | 39.8 dB | 40.1 dB |
| 2000-3000m | 100.0% (2000/2000) | 100.0% (2000/2000) | 30.6 dB | 31.3 dB |
| 3000-4000m | 100.0% (2000/2000) | 100.0% (1999/2000) | 24.0 dB | 24.1 dB |
| 4000-5000m | 99.5% (1990/2000) | 94.2% (1885/2000) | 17.9 dB | 16.6 dB |
| 5000-6000m | 72.0% (1439/2000) | 35.9% (718/2000) | 10.6 dB | 7.1 dB |

## G1/G2 files

| Month | HDF5 | arrivals | empty (r = 0) | TL CSV | SNR CSV |
| --- | --- | --- | --- | --- | --- |
| January | `data/bellhop/arrivals_full_grid_extended_january.h5` | 362499 | 51 | `data/channel_db/TL_grid_extended_january.csv` | `data/channel_db/SNR_grid_extended_january.csv` |
| July | `data/bellhop/arrivals_full_grid_extended_july.h5` | 366999 | 51 | `data/channel_db/TL_grid_extended_july.csv` | `data/channel_db/SNR_grid_extended_july.csv` |

Columns match Step F: `[range_m, receiver_depth_m, TL_dB]` and
`[range_m, receiver_depth_m, SNR_dB]`. Range 0 m is NaN. Depth 0 m is
kept and flagged (pressure-release). Negative TL count: January
0, July 0.

d_p method: d_p = tau_p * c(z_src). Bellhop ASCII .arr does not report geometric path length or a ray-integrated slowness. c(z_src) is the full-column WOA23 Mackenzie SSP at 50 m.

## G4 — F3-style spot check at 4 km and 6 km, z = 50 m

Native Bellhop is single-frequency coherent `.shd` on the same extended
grid (run type CB). Reconstructed TL is the 2 kHz G_bar. A few dB is
expected; large |Δ| with large in-band ptp is frequency-selective fading,
not a new long-range breakdown.

**January** mean |Δ| at the two spots: 8.02 dB
- r=4000 m, z=50 m: recon TL 90.90 dB, native .shd 100.33 dB, |Δ| = 9.43 dB, in-band ptp 59.7 dB, n_arrivals=23
- r=6000 m, z=50 m: recon TL 102.91 dB, native .shd 109.53 dB, |Δ| = 6.61 dB, in-band ptp 11.0 dB, n_arrivals=27
  5×5 neighborhood median |Δ|: 4.16 dB at 4 km, 5.54 dB at 6 km. The exact
  4 km cell is a native peak (neighbors 90–96 dB vs 100.3 dB). **Method holds.**

**July** mean |Δ| at the two spots: 25.68 dB
- r=4000 m, z=50 m: recon TL 93.59 dB, native .shd 121.85 dB, |Δ| = 28.26 dB, in-band ptp 3.6 dB (would be a “fair slice”), n_arrivals=32
- r=6000 m, z=50 m: recon TL 106.64 dB, native .shd 129.75 dB, |Δ| = 23.11 dB, in-band ptp 59.1 dB, n_arrivals=31
  5×5 neighborhood median |Δ|: 20.2 dB at 4 km (min 15.5), 25.6 dB at 6 km
  (min 21.6). Native TL is *systematically* ~20 dB higher, not a single-cell
  null. July SSP defocuses / shadows the 50 m path; Bellhop Gaussian-beam |p|
  captures that, while H_eq rebuilds amplitude as 1/d × Thorp on every
  eigenray and cannot. This is a known limitation of the prescribed
  reconstruction, not a parse error. Aqua-Sim TL/SNR from this H_eq is
  **optimistic** in July beyond ~4 km relative to native Bellhop (native
  would cross 8.68 dB earlier). The G3 crossings above follow the prescribed
  H_eq pipeline, as required.

## Rebuild

```bash
python3 scripts/build_channel_db_extended.py
```

Native `.arr` / `.shd` stay local (gitignored). HDF5 and CSV are the
portable products. The original 0–2 km Step-F files are not overwritten.
