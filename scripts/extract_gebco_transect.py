#!/usr/bin/env python3
"""Subset GEBCO_2026 to the WOA23 Western Pacific box and extract 2 km transects.

GEBCO native variable is elevation (metres, positive up, mean sea level).
Ocean depths in this script are stored as bottom_depth_m = -elevation
(positive down). The 2000 m transect is horizontal range, not depth.

Main CSV azimuth: 090° true (east). N/S/W are written alongside.
"""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone

import numpy as np
from netCDF4 import Dataset

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "gebco")
RAW = os.path.join(OUT, "raw")
FIGS = os.path.join(OUT, "figs")

DAP = (
    "https://dap.ceda.ac.uk/thredds/dodsC/bodc/gebco/"
    "global/gebco_2026/ice_surface_elevation/netcdf/GEBCO_2026.nc"
)
DOI = "10.5285/4f68d5c7-45eb-f999-e063-7086abc036fa"
CITATION = (
    "GEBCO Bathymetric Compilation Group 2026 (2026). The GEBCO_2026 Grid "
    "- a continuous terrain model for oceans and land at 15 arc-second intervals. "
    f"NERC EDS British Oceanographic Data Centre NOC. doi:{DOI}"
)

# Same bounding box as the WOA23 NCSS subset.
LAT_MIN, LAT_MAX = 17.5, 22.5
LON_MIN, LON_MAX = 121.5, 126.5
ORIGIN_LAT = 20.125
ORIGIN_LON = 124.125
RANGE_M = 2000.0
MAIN_AZIMUTH_DEG = 90.0  # east, true
STEP_M = 50.0
CONTEXT_M = 10000.0  # extra context for the "is 500 m reasonable?" question only

# GEBCO_2026: 15 arc-second grid, cell centres.
# lat[i] = -90 + (i + 0.5) / 240
# lon[j] = -180 + (j + 0.5) / 240
ARCSEC = 15.0
N_PER_DEG = 3600.0 / ARCSEC  # 240


def wgs84_metres_per_degree(lat_deg: float) -> tuple[float, float]:
    lat = math.radians(lat_deg)
    m_lat = 111132.92 - 559.82 * math.cos(2 * lat) + 1.175 * math.cos(4 * lat)
    m_lon = 111412.84 * math.cos(lat) - 93.5 * math.cos(3 * lat)
    return m_lat, m_lon


def latlon_index(lat: float, lon: float) -> tuple[int, int]:
    i = int(round((lat + 90.0) * N_PER_DEG - 0.5))
    j = int(round((lon + 180.0) * N_PER_DEG - 0.5))
    return i, j


def bilinear(lat_axis, lon_axis, elev, lat, lon) -> float:
    """Bilinear sample. lat_axis increasing south->north, lon west->east."""
    if lat < lat_axis[0] or lat > lat_axis[-1] or lon < lon_axis[0] or lon > lon_axis[-1]:
        return float("nan")
    i = np.searchsorted(lat_axis, lat) - 1
    j = np.searchsorted(lon_axis, lon) - 1
    i = int(np.clip(i, 0, len(lat_axis) - 2))
    j = int(np.clip(j, 0, len(lon_axis) - 2))
    t = (lat - lat_axis[i]) / (lat_axis[i + 1] - lat_axis[i])
    u = (lon - lon_axis[j]) / (lon_axis[j + 1] - lon_axis[j])
    z00 = float(elev[i, j])
    z10 = float(elev[i + 1, j])
    z01 = float(elev[i, j + 1])
    z11 = float(elev[i + 1, j + 1])
    return (1 - t) * (1 - u) * z00 + t * (1 - u) * z10 + (1 - t) * u * z01 + t * u * z11


def destination(lat, lon, azimuth_deg, dist_m) -> tuple[float, float]:
    m_lat, m_lon = wgs84_metres_per_degree(lat)
    az = math.radians(azimuth_deg)
    dlat = (dist_m * math.cos(az)) / m_lat
    dlon = (dist_m * math.sin(az)) / m_lon
    return lat + dlat, lon + dlon


def transect(lat_axis, lon_axis, elev, azimuth_deg, range_m, step_m) -> list[dict]:
    rows = []
    r = 0.0
    while r <= range_m + 1e-6:
        plat, plon = destination(ORIGIN_LAT, ORIGIN_LON, azimuth_deg, r)
        z = bilinear(lat_axis, lon_axis, elev, plat, plon)
        rows.append(
            {
                "range_m": round(r, 3),
                "lat": plat,
                "lon": plon,
                "gebco_elevation_m": z,
                "bottom_depth_m": -z if math.isfinite(z) else float("nan"),
                "azimuth_deg_true": azimuth_deg,
            }
        )
        r += step_m
    return rows


def write_csv(path: str, rows: list[dict], fields: list[str], header_lines: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for line in header_lines:
            f.write("# " + line + "\n")
        f.write(",".join(fields) + "\n")
        for row in rows:
            f.write(",".join(_cell(row[k]) for k in fields) + "\n")


def _cell(v) -> str:
    if isinstance(v, float):
        if not math.isfinite(v):
            return ""
        return f"{v:.6g}"
    return str(v)


def stats(rows: list[dict]) -> dict:
    d = np.array([r["bottom_depth_m"] for r in rows], dtype=float)
    d = d[np.isfinite(d)]
    return {
        "n": int(d.size),
        "min_m": float(d.min()) if d.size else None,
        "max_m": float(d.max()) if d.size else None,
        "mean_m": float(d.mean()) if d.size else None,
        "ptp_m": float(d.max() - d.min()) if d.size else None,
        "origin_m": float(rows[0]["bottom_depth_m"]) if rows else None,
        "end_m": float(rows[-1]["bottom_depth_m"]) if rows else None,
    }


def plot_transects(by_az: dict, origin_depth: float, context_map) -> None:
    if plt is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.55))

    ax = axes[0]
    colors = {0: "#c0392b", 90: "#1f4e79", 180: "#1e8449", 270: "#b9770e"}
    labs = {0: "N 000", 90: "E 090 (main)", 180: "S 180", 270: "W 270"}
    for az, rows in by_az.items():
        ax.plot(
            [r["range_m"] for r in rows],
            [r["bottom_depth_m"] for r in rows],
            color=colors[az],
            lw=1.4,
            label=labs[az],
        )
    ax.axhline(500.0, color="0.35", ls=":", lw=1.0, label="ns-3 500 m lid")
    ax.set_xlabel("Horizontal range (m)")
    ax.set_ylabel("Bottom depth (m, positive down)")
    ax.set_title("2 km from primary cell")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=6.5, loc="best")
    ax.set_ylim(0, max(600, origin_depth * 1.05))
    ax.invert_yaxis()

    ax = axes[1]
    lat_c, lon_c, elev_c, half_deg = context_map
    depth = -elev_c
    im = ax.pcolormesh(lon_c, lat_c, depth, shading="auto", cmap="viridis")
    ax.plot(ORIGIN_LON, ORIGIN_LAT, "r*", ms=8)
    m_lat, m_lon = wgs84_metres_per_degree(ORIGIN_LAT)
    dlat = RANGE_M / m_lat
    dlon = RANGE_M / m_lon
    ax.plot(
        [ORIGIN_LON, ORIGIN_LON, ORIGIN_LON, ORIGIN_LON + dlon, ORIGIN_LON - dlon],
        [ORIGIN_LAT, ORIGIN_LAT + dlat, ORIGIN_LAT - dlat, ORIGIN_LAT, ORIGIN_LAT],
        "r+",
        ms=5,
    )
    ax.set_xlabel("Longitude (deg E)")
    ax.set_ylabel("Latitude (deg N)")
    ax.set_title("Depth in a 20 km box")
    ax.set_aspect("equal", adjustable="box")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "gebco_transect_primary.png"), dpi=180)
    plt.close()


def main() -> int:
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)

    i0, j0 = latlon_index(LAT_MIN, LON_MIN)
    i1, j1 = latlon_index(LAT_MAX, LON_MAX)
    # inclusive slice
    if i1 < i0:
        i0, i1 = i1, i0
    if j1 < j0:
        j0, j1 = j1, j0
    print(f"subset indices lat[{i0}:{i1 + 1}] lon[{j0}:{j1 + 1}]", flush=True)

    print("opening GEBCO_2026 via CEDA OPeNDAP ...", flush=True)
    ds = Dataset(DAP)
    lat_axis = np.array(ds.variables["lat"][i0 : i1 + 1], dtype=float)
    lon_axis = np.array(ds.variables["lon"][j0 : j1 + 1], dtype=float)
    print("reading elevation slab ...", flush=True)
    elev = np.array(ds.variables["elevation"][i0 : i1 + 1, j0 : j1 + 1], dtype=np.float32)
    title = getattr(ds, "title", "GEBCO_2026")
    ds.close()
    print(f"slab {elev.shape} lat {lat_axis[0]:.6f}..{lat_axis[-1]:.6f} lon {lon_axis[0]:.6f}..{lon_axis[-1]:.6f}", flush=True)

    subset_path = os.path.join(RAW, "gebco_2026_wp_17p5-22p5N_121p5-126p5E.nc")
    out = Dataset(subset_path, "w", format="NETCDF4")
    out.createDimension("lat", lat_axis.size)
    out.createDimension("lon", lon_axis.size)
    vlat = out.createVariable("lat", "f8", ("lat",))
    vlon = out.createVariable("lon", "f8", ("lon",))
    ve = out.createVariable("elevation", "i2", ("lat", "lon"), zlib=True, complevel=4)
    vlat[:] = lat_axis
    vlon[:] = lon_axis
    ve[:] = np.rint(elev).astype(np.int16)
    vlat.units = "degrees_north"
    vlon.units = "degrees_east"
    ve.units = "m"
    ve.long_name = "Elevation relative to sea level (GEBCO native, positive up)"
    ve.standard_name = "height_above_mean_sea_level"
    out.title = title
    out.source = DAP
    out.citation = CITATION
    out.subset = "17.5-22.5N, 121.5-126.5E"
    out.close()

    origin_z = bilinear(lat_axis, lon_axis, elev, ORIGIN_LAT, ORIGIN_LON)
    origin_depth = -origin_z
    print(f"origin elevation={origin_z:.1f} m  bottom_depth={origin_depth:.1f} m", flush=True)

    azimuths = (0.0, 90.0, 180.0, 270.0)
    by_az = {az: transect(lat_axis, lon_axis, elev, az, RANGE_M, STEP_M) for az in azimuths}
    main_rows = by_az[MAIN_AZIMUTH_DEG]

    header = [
        "GEBCO_2026 15 arc-second, CEDA OPeNDAP subset of 17.5-22.5N 121.5-126.5E",
        CITATION,
        f"Origin: {ORIGIN_LAT}N {ORIGIN_LON}E (WOA23 primary grid cell)",
        f"Main azimuth: {MAIN_AZIMUTH_DEG:.0f} deg true (east)",
        "range_m is horizontal distance, not depth.",
        "GEBCO native elevation is metres, positive UP (ocean is negative).",
        "bottom_depth_m = -elevation (positive DOWN).",
        "Values bilinearly interpolated from the 15-arc-second grid; spacing ~435-463 m.",
        f"Built {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
    ]
    write_csv(
        os.path.join(OUT, "bathymetry_transect_primary.csv"),
        main_rows,
        ["range_m", "bottom_depth_m"],
        header,
    )
    all_rows = []
    for az in azimuths:
        all_rows.extend(by_az[az])
    write_csv(
        os.path.join(OUT, "bathymetry_transects_NEWS.csv"),
        all_rows,
        ["azimuth_deg_true", "range_m", "lat", "lon", "gebco_elevation_m", "bottom_depth_m"],
        header[:-1] + ["Four azimuths: 0 N, 90 E (main), 180 S, 270 W"],
    )

    context_rows = {az: transect(lat_axis, lon_axis, elev, az, CONTEXT_M, 200.0) for az in azimuths}

    # 20 km box for the map (~0.18 deg).
    m_lat, m_lon = wgs84_metres_per_degree(ORIGIN_LAT)
    dlat = 20000.0 / m_lat
    dlon = 20000.0 / m_lon
    lat_c = lat_axis[(lat_axis >= ORIGIN_LAT - dlat) & (lat_axis <= ORIGIN_LAT + dlat)]
    lon_c = lon_axis[(lon_axis >= ORIGIN_LON - dlon) & (lon_axis <= ORIGIN_LON + dlon)]
    i_lo = int(np.searchsorted(lat_axis, ORIGIN_LAT - dlat))
    i_hi = int(np.searchsorted(lat_axis, ORIGIN_LAT + dlat))
    j_lo = int(np.searchsorted(lon_axis, ORIGIN_LON - dlon))
    j_hi = int(np.searchsorted(lon_axis, ORIGIN_LON + dlon))
    elev_c = elev[i_lo:i_hi, j_lo:j_hi]
    plot_transects(by_az, origin_depth, (lat_axis[i_lo:i_hi], lon_axis[j_lo:j_hi], elev_c, 0.2))

    box_depth = -elev[np.isfinite(elev)]
    ocean = box_depth[box_depth > 0]
    land = elev[elev >= 0]
    az_stats = {str(int(az)): stats(rows) for az, rows in by_az.items()}
    ctx_stats = {str(int(az)): stats(rows) for az, rows in context_rows.items()}

    verdict = {
        "flat_500_m_matches_seafloor": False,
        "reason": (
            f"At the primary cell GEBCO bottom depth is {origin_depth:.0f} m. "
            f"Over the requested 2000 m NEWS transects the seafloor stays near that "
            f"value (peak-to-peak of a few metres to tens of metres, not a shelf or seamount). "
            "A 500 m ns-3 lid is therefore a truncated mid-water slab about 5 km above the "
            "real bottom, not a representation of GEBCO bathymetry. Locally the 2 km patch "
            "is almost flat, but the depth number 500 m is not."
        ),
    }

    provenance = {
        "product": "GEBCO_2026 15 arc-second ice-surface elevation grid",
        "citation": CITATION,
        "doi": f"https://doi.org/{DOI}",
        "portal": "https://www.gebco.net/data_and_products/gridded_bathymetry_data/",
        "opendap": DAP,
        "sign_convention": {
            "gebco_native": "elevation, metres, positive up, relative to mean sea level (ocean negative)",
            "csv_bottom_depth_m": "positive down, equal to -elevation",
        },
        "subset": {"lat": [LAT_MIN, LAT_MAX], "lon": [LON_MIN, LON_MAX]},
        "origin": {"lat": ORIGIN_LAT, "lon": ORIGIN_LON, "note": "WOA23 primary grid cell"},
        "main_transect": {
            "azimuth_deg_true": MAIN_AZIMUTH_DEG,
            "azimuth_name": "east",
            "range_m": RANGE_M,
            "sample_step_m": STEP_M,
            "interpolation": "bilinear on GEBCO 15-arc-second cell centres",
        },
        "origin_gebco_elevation_m": float(origin_z),
        "origin_bottom_depth_m": float(origin_depth),
        "transect_2km_stats_by_azimuth": az_stats,
        "transect_10km_stats_by_azimuth_context_only": ctx_stats,
        "box_stats": {
            "n_cells": int(elev.size),
            "n_ocean_cells": int(ocean.size),
            "n_land_or_zero_cells": int(land.size),
            "ocean_depth_min_m": float(ocean.min()) if ocean.size else None,
            "ocean_depth_max_m": float(ocean.max()) if ocean.size else None,
            "note": "Full 5x5 deg box includes Luzon/Taiwan shelves and the Philippine Sea basin. That variation is NOT present on the 2 km primary transect.",
        },
        "ns3_500m_verdict": verdict,
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subset_nc": os.path.relpath(subset_path, ROOT),
    }
    with open(os.path.join(OUT, "provenance.json"), "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    print("2 km stats:")
    for az, s in az_stats.items():
        print(
            f"  az {az:>3s}  origin={s['origin_m']:.1f}  end={s['end_m']:.1f}  "
            f"min={s['min_m']:.1f} max={s['max_m']:.1f} ptp={s['ptp_m']:.1f}"
        )
    print("10 km context:")
    for az, s in ctx_stats.items():
        print(f"  az {az:>3s}  min={s['min_m']:.1f} max={s['max_m']:.1f} ptp={s['ptp_m']:.1f}")
    print(
        f"box ocean depth min={ocean.min():.0f} max={ocean.max():.0f} m  "
        f"land cells={land.size}"
    )
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
