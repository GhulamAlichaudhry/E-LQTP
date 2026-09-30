# WOA23 Western Pacific temperature, salinity, and SSP

Climatological profiles for a northern Philippine Sea box, built from
**NOAA World Ocean Atlas 2023** 0.25° objectively analyzed mean fields.
This is environmental input for a later Aqua-Sim / acoustic-propagation
step. It is **not** a Bellhop run and it is **not** a transmission-loss
table.

## What was downloaded

| Item | Value |
| --- | --- |
| Product | WOA23, `decav`, 0.25° (`*_04.nc`) |
| Fields | Objectively analyzed means `t_an`, `s_an` |
| Months | All 12 climatological months, plus the annual field |
| Transfer | NCEI THREDDS NetcdfSubset of the analysis box (not the 0.6–1.1 GB global files) |
| Full-file URLs | recorded in `provenance.json` (`full_file_url`) |
| Monthly depth | 57 WOA standard levels, **0–1500 m** |
| Annual depth | 102 WOA standard levels, **0–5500 m** (stored separately; **not spliced** into monthly SSPs) |

WOA monthly analyzed fields do not exist at 2000 m. That is a product
limit, not a download failure. The annual field reaches 2000 m and 5500 m;
use `profiles/woa23_wp_annual_profiles.csv` if a deep extension is needed,
and say so in the paper.

Portal: https://www.ncei.noaa.gov/products/world-ocean-atlas

Temperature volume (from the NetCDF `references` attribute): Locarnini
et al., *World Ocean Atlas 2023, Volume 1: Temperature*, NOAA Atlas NESDIS
89, https://doi.org/10.25923/54bh-1613.

## Site

Requested analysis box: 18–22°N, 122–126°E (waters east of Taiwan /
northern Philippine Sea).

Requested primary coordinate: **20.0°N, 124.0°E**. The WOA 0.25° grid is
centered on `*.875` / `*.125`, so 20.0°N, 124.0°E is a four-way tie.
The extractor takes the nearest cell inside the box, breaking remaining
ties to the north-east. The SW corner request (18°N, 122°E) is land-masked
in WOA (northern Luzon / coastal mask) and is snapped to the nearest
ocean cell inside the box (18.125°N, 122.375°E). That snapped cell is on
the slope: monthly OA is defined only to 1100 m there. The primary site
and the other three corners have all 57 monthly levels to 1500 m.

## Sound speed

Mackenzie nine-term equation (1981), *J. Acoust. Soc. Am.* **70**, 807–812:

```
c = 1448.96 + 4.591 T - 5.304e-2 T^2 + 2.374e-4 T^3
  + 1.340 (S-35) + 1.630e-2 D + 1.675e-7 D^2
  - 1.025e-2 T (S-35) - 7.139e-13 T D^3
```

T in °C, S in PSS-78 treated as ppt, D in metres, c in m/s.

Not used: UNESCO Chen-Millero, TEOS-10, a measured CTD, Bellhop, or any
eigenray/TL computation.

## NCSS depth-axis correction

THREDDS NetcdfSubset rewrote `depth` to interval midpoints (0 m → 1.25 m,
100 m → 105 m, 1500 m → 1487.5 m). The `t_an` / `s_an` values are still
the OA means on WOA standard levels. Profiles in `profiles/` attach the
**original** `depth` axis obtained from OPeNDAP on the same files
(`0, 5, …, 1500` monthly; `0, 5, …, 5500` annual). Provenance records
the rewrite.

## Rebuild

```bash
python3 scripts/build_woa23_ssp.py          # reuse existing raw subsets
python3 scripts/build_woa23_ssp.py --force  # re-download from NCEI
```

## Files

```
data/woa23/
  provenance.json
  raw/                      # regional NetCDF subsets (t_an, s_an)
  profiles/
    stations.csv
    woa23_wp_monthly_profiles.csv   # 12 months × 5 stations × 57 levels
    woa23_wp_january_profiles.csv
    woa23_wp_july_profiles.csv
    woa23_wp_annual_profiles.csv    # not a monthly field
    ssp_january_july_summary.csv
  figs/ssp_jan_jul_primary.png
```

January and July are the seasonal-extreme months requested for later
comparison. All twelve months are in the monthly CSV.

## What this is not

No GEBCO/ETOPO bathymetry, no bottom type. Bellhop `.env` / TL / eigenrays
for this site live in `data/bellhop/` (flat 5524 m bottom, full-column SSP).
Do not treat `sound_speed_mps` itself as a multipath loss.
