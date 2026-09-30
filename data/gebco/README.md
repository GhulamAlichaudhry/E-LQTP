# GEBCO_2026 bathymetry, Western Pacific box

Subset of the **GEBCO_2026** 15 arc-second grid over the same box as the
WOA23 extraction (17.5–22.5°N, 121.5–126.5°E), plus a 2 km horizontal
transect from the WOA23 primary cell.

This is bathymetry. ns-3 still places nodes in a 500 m mid-water slab.
The Bellhop run in `data/bellhop/` uses this transect as a **flat 5524 m**
bottom, not as a 500 m lid.

## Source

GEBCO Bathymetric Compilation Group 2026 (2026). The GEBCO_2026 Grid —
a continuous terrain model for oceans and land at 15 arc-second intervals.
NERC EDS British Oceanographic Data Centre NOC.
doi:[10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa](https://doi.org/10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa)

Portal: https://www.gebco.net/data_and_products/gridded_bathymetry_data/

Pulled via CEDA OPeNDAP (the global NetCDF is 7.5 GB; only this box was
read). Rebuild: `python3 scripts/extract_gebco_transect.py`

## Sign convention

GEBCO native `elevation` is metres **positive up**, relative to mean sea
level. The ocean is negative.

CSV column `bottom_depth_m` is **positive down**:
`bottom_depth_m = -elevation`.

## Transect

| Item | Value |
| --- | --- |
| Origin | 20.125°N, 124.125°E (WOA23 primary cell) |
| Horizontal range | 2000 m |
| Main azimuth | **090° true (east)** |
| Also extracted | N 000°, S 180°, W 270° in `bathymetry_transects_NEWS.csv` |
| Sampling | every 50 m, bilinear on the 15″ grid (~435–463 m cells) |

## Depths that were actually measured here

At the origin, GEBCO bottom depth is **5524 m**.

Over the requested 2 km:

| Azimuth | min (m) | max (m) | peak-to-peak (m) |
| --- | --- | --- | --- |
| N 000 | 5510.5 | 5524.2 | 13.8 |
| E 090 (main) | 5523.0 | 5525.5 | 2.5 |
| S 180 | 5524.2 | 5527.9 | 3.7 |
| W 270 | 5524.2 | 5527.5 | 3.2 |

There is no seamount, shelf break, or trench edge on this 2 km patch.
The seafloor is locally almost flat — at **five and a half kilometres**,
not at 500 m.

A 10 km context (not used for the main CSV): east and north still stay
deeper than 5100 m (peak-to-peak a few hundred metres of abyssal hills).
The full 5° box **does** include land and shelves (Luzon/Taiwan; ocean
depths from 1 m to 6573 m). That variation is in the box, not on the
primary 2 km transect. Do not cite the box range as if it were the
transect.

## Verdict on a flat 500 m ns-3 bottom

**No. A 500 m flat bottom does not match this site.**

Real GEBCO depth at the primary cell is ~5524 m. The 500 m ns-3 volume
is a truncated mid-water slab sitting about 5 km above the actual
seafloor. AUVs at 40–160 m never see that seafloor in either geometry.
Bottom bounce, a deep sound channel that interacts with the bottom, and
slope-driven shadowing are not represented by a 500 m lid.

What *is* reasonable: treating the **2 km neighbourhood** as locally
range-independent and flat, with a bottom several kilometres down, not
500 m down. The Bellhop Step C run therefore uses a **flat 5524 m**
halfspace. Flattening to 500 m would invent non-physical bottom-bounce
arrivals at this site.

## Files

```
data/gebco/
  bathymetry_transect_primary.csv   # range_m, bottom_depth_m  (east, 2 km)
  bathymetry_transects_NEWS.csv
  provenance.json
  raw/gebco_2026_wp_17p5-22p5N_121p5-126p5E.nc
  figs/gebco_transect_primary.png
```
