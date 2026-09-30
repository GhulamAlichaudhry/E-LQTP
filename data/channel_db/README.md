# Channel database (Step F) — Western Pacific primary cell

Multipath channel for Aqua-Sim / ns-3 from Bellhop eigenrays at
20.125°N, 124.125°E. Flat 5524 m bottom, full-column WOA23 SSP,
src = 50 m, 24 kHz, B = 2000 Hz.

The 0–2 km grid never reaches the 8.68 dB SNR gate. The 0–6 km
extension (threshold crossing, band fractions, heatmaps with the
8.68 dB contour) is in
[`README_extended.md`](README_extended.md).

## F1 — full-grid eigenrays

The earlier arrivals CSV covered only five ranges (200, 500, 1000, 1500,
2000 m). That is **not** the simulation grid. Full-grid ASCII Bellhop
arrivals were re-run for every (range, depth) on 0–2000 m / 10 m ×
0–500 m / 10 m (201 × 51 = 10251 points), January and July.

| Month | HDF5 | arrivals | empty points |
| --- | --- | --- | --- |
| January | `data/bellhop/arrivals_full_grid_january.h5` | 240789 | 51 |
| July | `data/bellhop/arrivals_full_grid_july.h5` | 242626 | 51 |

Each arrival stores τ_p, Bellhop amplitude (reference only), θ_p
(phase, deg), launch/receive angles, n_top, n_bot, and d_p.

**d_p method:** Bellhop `.arr` does not report geometric path length.
`d_p = τ_p × c(z_src)` with c from the month's full-column Mackenzie SSP
at 50 m (January 1533.55 m/s, July 1540.21 m/s).
Not a ray-integrated slowness.

## F2 — H_eq(f), G_bar, TL

Frequency axis: 23000, 23001, …, 24999 Hz (2000 bins, Δf = 1 Hz, B = 2000 Hz).
κ = 2 (spherical). Thorp α as specified (not the Bellhop 3.3e−3 / 3e−4
variant). θ_p and τ_p from Bellhop; magnitude from L_geo L_abs, **not**
from Bellhop |A| (Bellhop |A| already folds Thorp, spreading, and
bottom loss — using it here would double-count).

G_bar = (1/B) Σ_k |H_eq(f_k)|² Δf.

**TL sign.** The prompt wrote `TL = 10 log10(G_bar)`. That is power
*gain* in dB and is negative. The CSV column `TL_dB` is the sonar-equation
loss used by LQARP / Aqua-Sim:

    TL_dB = −10 log10(G_bar)

so that `SNR = SL − TL − NL + DI` has the usual sign. Downstream code
that subtracts TL from SL must use this column as stored.

| Month | CSV | finite points | NaN / failed | TL < 0 |
| --- | --- | --- | --- | --- |
| January | `data/channel_db/TL_grid_january.csv` | 10200 | 51 | 0 |
| July | `data/channel_db/TL_grid_july.csv` | 10200 | 51 | 0 |

Focus (50 m, 50 m, 1000 m): January TL 58.87 dB,
July 62.77 dB.

Full complex H_eq(f) is ~164 MB/month (complex64) and is **not** stored.
It is recoverable from the HDF5 arrival lists. Per-point in-band
peak-to-trough of 10 log10(|H|²) is in `data/channel_db/fading_ptp_*.csv`.

## F3 — vs native Bellhop .shd TL (single-frequency coherent, 24 kHz)

Reconstructed TL is a 2 kHz *power average* of a spreading+Thorp coherent
sum. Native Bellhop is |p| at 24 kHz with Gaussian beams. Those are
different estimators: G_bar fills in frequency-selective nulls that a
single-frequency .shd still sees.

Primary comparison (r ≥ 10 m, z ≥ 10 m — hydrophones below the
pressure-release surface):

| Month | n | mean \|Δ\| | median | p95 | max | fraction \|Δ\|>10 dB |
| --- | --- | --- | --- | --- | --- | --- |
| January | 10000 | 4.75 | 2.57 | 17.62 | 54.48 | 14.1% |
| July | 10000 | 4.65 | 2.71 | 16.11 | 36.62 | 14.1% |

Fair slice (same grid, but only points whose in-band |H|² peak-to-trough
is < 6 dB — i.e. where a single-frequency snapshot *should* match G_bar):

- January: 21 pts, mean 1.25, med 1.08, p95 3.00, max 3.47, |Δ|>10 dB at 0.0% (0)
- July: 44 pts, mean 3.80, med 2.77, p95 9.05, max 10.82, |Δ|>10 dB at 2.3% (1)

**Not a silent-accept of a >10 dB bug.** The fair (low-fading) slice is
the apples-to-apples check against a single-frequency .shd. January
stays within a few dB there; July has one of 44 points at 10.8 dB.
The ~14% of the full z≥10 m grid with |Δ|>10 dB are Bellhop sitting
in a 24 kHz Lloyd-mirror null (native TL 90–110 dB) while G_bar
averages the 2 kHz fade pattern down to ~60 dB. That is the F5
frequency-selectivity result, not a summation error.

Non-physical points, kept in the CSV and flagged here:

- **Range 0 m:** Bellhop wrote no eigenrays (point-source singularity).
  TL/SNR are NaN. 51 cells/month.
- **Depth 0 m:** pressure-release surface. Direct and surface-reflected
  arrivals cancel at all frequencies; reconstructed TL is often >100 dB
  and SNR is negative. A hydrophone cannot sit in the vacuum interface.
  Native Bellhop still reports a finite TL there because of beam width.

## F4 — SNR grid

    SNR = SL − TL − NL + DI

| Quantity | Value | Provenance |
| --- | --- | --- |
| SL | 175 dB re 1 µPa | assumed source level (not a sea-trial measurement) |
| DI | 0 dB | omnidirectional, LQARP convention |
| s | 0.2 | **assumed** shipping factor; NOT from WOA/GEBCO |
| w | 2.0 m/s | **assumed** wind; NOT from WOA/GEBCO |
| NL (band-integrated) | 65.77 dB | Wenz four-component, ∫ N(f) df over B |
| NL (N(f_c)·B) | 65.77 dB | same model, prompt's compact form |
| SNR threshold | 8.68 dB | LQARP stated detection threshold |

The SNR CSV uses the **band-integrated** NL (65.77 dB).
The two NL numbers differ by 0.01 dB
because N(f) is not flat across 23–25 kHz (wind + thermal dominate).

Wenz components at 24 kHz (dB re 1 µPa²/Hz): turbulence -24.4,
shipping -13.0, wave 32.7,
thermal 12.6.

| Month | CSV | SNR>8.68 dB, r≥10 m all z | same, z≥10 m only |
| --- | --- | --- | --- |
| January | `data/channel_db/SNR_grid_january.csv` | 98.2% (10012/10200) | 100.0% (10000/10000) |
| July | `data/channel_db/SNR_grid_july.csv` | 98.5% (10042/10200) | 100.0% (10000/10000) |

## F5 — is B = 2000 Hz enough?

Coherence bandwidth from the water-column delay spread (direct vs surface,
Δτ ≈ 3 ms at 1 km) is ~1/Δτ ≈ 330 Hz, much narrower than 2 kHz. In-band
peak-to-trough of 10 log10(|H_eq|²):

| | January | July |
| --- | --- | --- |
| median ptp (dB) | 35.15 | 35.15 |
| fraction of points with ptp > 3 dB | 99.3% | 98.4% |
| max ptp (dB) | 77.28 | 77.51 |

**Verdict:** B = 2000 Hz is NOT a flat channel on this grid. Frequency-selective fading exceeds 3 dB peak-to-trough at a large fraction of points because the water-column delay spread (~3 ms) sets a coherence bandwidth of a few hundred hertz. G_bar as a 2 kHz power average is still the right scalar for an LQARP-style budget; a single-tap H(f_c) is not. Finer than 1 Hz sampling is not required.

1 Hz sampling of a 2 kHz band is fine for G_bar (2000 samples of a
smooth |H|²). The *bandwidth itself* is wide compared with the fade
scale, which is why we power-average rather than taking |H(f_c)|.

## Rebuild

```bash
pip3 install h5py
python3 scripts/build_channel_db.py
```

Native Bellhop `.shd` / `.arr` stay local (gitignored). HDF5 and CSV
are the portable products.
