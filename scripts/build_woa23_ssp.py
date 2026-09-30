#!/usr/bin/env python3
"""Download WOA23 monthly T/S for a Western Pacific box and build SSPs.

Source: NOAA NCEI World Ocean Atlas 2023, 0.25-degree, objectively analyzed
mean fields (t_an, s_an), climatological months 01-12 plus the annual field.

Spatial subset is pulled via the NCEI THREDDS NetcdfSubset service so the
full global ~0.6-1.1 GB monthly files are not stored. Monthly WOA analyzed
fields stop at 1500 m; that limit is preserved. The annual field (0-5500 m)
is stored separately and is not mixed into the monthly SSPs.

Sound speed is Mackenzie (1981), JASA 70:807-812. No Bellhop, no eigenrays,
no invented transmission loss.

Usage:
    python3 scripts/build_woa23_ssp.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from netCDF4 import Dataset


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "data", "woa23")
RAW = os.path.join(OUT, "raw")
PROF = os.path.join(OUT, "profiles")
FIGS = os.path.join(OUT, "figs")

NCSS_T = (
    "https://www.ncei.noaa.gov/thredds-ocean/ncss/grid/"
    "woa23/DATA/temperature/netcdf/decav/0.25/{name}"
)
NCSS_S = (
    "https://www.ncei.noaa.gov/thredds-ocean/ncss/grid/"
    "woa23/DATA/salinity/netcdf/decav/0.25/{name}"
)
HTTP_T = (
    "https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/"
    "temperature/netcdf/decav/0.25/{name}"
)
HTTP_S = (
    "https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/"
    "salinity/netcdf/decav/0.25/{name}"
)

# Requested analysis box and target (user specification).
LAT_MIN, LAT_MAX = 18.0, 22.0
LON_MIN, LON_MAX = 122.0, 126.0
TARGET_LAT, TARGET_LON = 20.0, 124.0
# NCSS pad so corner grid cells are inside the downloaded cube.
SOUTH, NORTH = 17.5, 22.5
WEST, EAST = 121.5, 126.5

REQUESTED = [
    ("primary", TARGET_LAT, TARGET_LON, "requested 20.0N 124.0E"),
    ("corner_sw", 18.0, 122.0, "SW corner of analysis box"),
    ("corner_se", 18.0, 126.0, "SE corner of analysis box"),
    ("corner_nw", 22.0, 122.0, "NW corner of analysis box"),
    ("corner_ne", 22.0, 126.0, "NE corner of analysis box"),
]

MONTHS = list(range(1, 13))
MONTH_NAME = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def ncss_query(var: str) -> str:
    return (
        f"?var={var}"
        f"&north={NORTH}&west={WEST}&east={EAST}&south={SOUTH}"
        "&disableLLSubset=on&disableProjSubset=on&horizStride=1"
        "&accept=netcdf"
    )


def download(url: str, dest: str, retries: int = 5) -> dict:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    delay = 4
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "woa-ssp-builder/1.0"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = resp.read()
                info = {
                    "url": url,
                    "http_status": getattr(resp, "status", 200),
                    "bytes": len(payload),
                    "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "attempt": attempt,
                }
            with open(dest, "wb") as f:
                f.write(payload)
            if len(payload) < 1000:
                raise RuntimeError(f"download too small ({len(payload)} bytes): {url}")
            return info
        except (urllib.error.URLError, TimeoutError, RuntimeError, OSError) as exc:
            last_err = exc
            print(f"  attempt {attempt}/{retries} failed: {exc}", flush=True)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"failed to download {url}: {last_err}")


def mackenzie_ssp(temperature_c, salinity_pss, depth_m):
    """Nine-term Mackenzie (1981) sound speed, m/s.

    T in deg C, S in psu (PSS-78, treated as ppt as in the original fit),
    D in metres. Range stated by Mackenzie: 0-30 C, 30-40 ppt, 0-8000 m.
    """
    t = np.asarray(temperature_c, dtype=float)
    s = np.asarray(salinity_pss, dtype=float)
    d = np.asarray(depth_m, dtype=float)
    return (
        1448.96
        + 4.591 * t
        - 5.304e-2 * t**2
        + 2.374e-4 * t**3
        + 1.340 * (s - 35.0)
        + 1.630e-2 * d
        + 1.675e-7 * d**2
        - 1.025e-2 * t * (s - 35.0)
        - 7.139e-13 * t * d**3
    )


# Official WOA standard depths from the original NetCDF `depth` axis
# (OPeNDAP `depth` on woa23_decav_t01_04.nc / t00_04.nc). NCSS rewrites
# this axis to interval midpoints; T/S still sit on these standard levels.
WOA_DEPTH_MONTHLY_M = np.array(
    [
        0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85,
        90, 95, 100, 125, 150, 175, 200, 225, 250, 275, 300, 325, 350, 375,
        400, 425, 450, 475, 500, 550, 600, 650, 700, 750, 800, 850, 900, 950,
        1000, 1050, 1100, 1150, 1200, 1250, 1300, 1350, 1400, 1450, 1500,
    ],
    dtype=float,
)
WOA_DEPTH_ANNUAL_M = np.array(
    list(WOA_DEPTH_MONTHLY_M)
    + [
        1550, 1600, 1650, 1700, 1750, 1800, 1850, 1900, 1950, 2000, 2100,
        2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 3000, 3100, 3200,
        3300, 3400, 3500, 3600, 3700, 3800, 3900, 4000, 4100, 4200, 4300,
        4400, 4500, 4600, 4700, 4800, 4900, 5000, 5100, 5200, 5300, 5400,
        5500,
    ],
    dtype=float,
)


def nearest_index(coord: np.ndarray, value: float, lo: float | None = None, hi: float | None = None) -> int:
    """Nearest grid coordinate.

    Exact mid-cell ties (e.g. 20.0 between 19.875 and 20.125) are broken by
    preferring a point inside [lo, hi] when that interval is given, then the
    more northern/eastern candidate.
    """
    dist = np.abs(coord - value)
    mind = float(dist.min())
    cands = np.flatnonzero(np.isclose(dist, mind, atol=1e-8, rtol=0.0))
    if lo is not None and hi is not None:
        inside = [int(i) for i in cands if lo - 1e-9 <= coord[int(i)] <= hi + 1e-9]
        if inside:
            cands = np.array(inside, dtype=int)
    # Prefer the larger coordinate (N or E) among remaining ties.
    return int(cands[np.argmax(coord[cands])])


def open_oa(path: str, varname: str):
    ds = Dataset(path)
    lat = np.array(ds.variables["lat"][:], dtype=float)
    lon = np.array(ds.variables["lon"][:], dtype=float)
    depth = np.array(ds.variables["depth"][:], dtype=float)
    field = np.array(ds.variables[varname][0, :, :, :], dtype=float)
    fill = getattr(ds.variables[varname], "_FillValue", np.nan)
    missing = getattr(ds.variables[varname], "missing_value", fill)
    field = np.where((field == fill) | (field == missing), np.nan, field)
    attrs = {
        "title": getattr(ds, "title", ""),
        "id": getattr(ds, "id", ""),
        "references": getattr(ds, "references", ""),
        "institution": getattr(ds, "institution", ""),
        "time_coverage_start": getattr(ds, "time_coverage_start", ""),
        "time_coverage_duration": getattr(ds, "time_coverage_duration", ""),
        "date_created": getattr(ds, "date_created", ""),
        "geospatial_vertical_max": getattr(ds, "geospatial_vertical_max", ""),
    }
    ds.close()
    return lat, lon, depth, field, attrs


def station_table(lat: np.ndarray, lon: np.ndarray, ocean_mask: np.ndarray) -> list[dict]:
    rows = []
    for name, rlat, rlon, note in REQUESTED:
        i = nearest_index(lat, rlat, LAT_MIN, LAT_MAX)
        j = nearest_index(lon, rlon, LON_MIN, LON_MAX)
        land = not bool(ocean_mask[i, j])
        if land:
            d2 = (lat[:, None] - rlat) ** 2 + (lon[None, :] - rlon) ** 2
            in_box = (
                (lat[:, None] >= LAT_MIN)
                & (lat[:, None] <= LAT_MAX)
                & (lon[None, :] >= LON_MIN)
                & (lon[None, :] <= LON_MAX)
            )
            allowed = ocean_mask & in_box
            d2 = np.where(allowed, d2, np.inf)
            i, j = np.unravel_index(int(np.argmin(d2)), d2.shape)
            i, j = int(i), int(j)
            note = note + "; nearest cell was land-masked, snapped to nearest ocean cell in the box"
        dlat = lat[i] - rlat
        dlon = lon[j] - rlon
        dist_km = math.hypot(dlat * 110.574, dlon * 111.320 * math.cos(math.radians(rlat)))
        rows.append(
            {
                "station": name,
                "requested_lat": rlat,
                "requested_lon": rlon,
                "grid_lat": float(lat[i]),
                "grid_lon": float(lon[j]),
                "ilat": int(i),
                "ilon": int(j),
                "offset_km": round(float(dist_km), 3),
                "land_snap": int(land),
                "note": note,
            }
        )
    return rows


def write_csv(path: str, rows: list[dict], fields: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(fields) + "\n")
        for row in rows:
            f.write(",".join(_csv_cell(row[k]) for k in fields) + "\n")


def _csv_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v).replace(",", " ")


def plot_primary(jan_rows, jul_rows, station_meta) -> None:
    if plt is None:
        return
    def series(rows, key):
        z, y = [], []
        for r in rows:
            if r["station"] != "primary":
                continue
            if r[key] == "" or r[key] is None:
                continue
            z.append(float(r["depth_m"]))
            y.append(float(r[key]))
        return np.array(z), np.array(y)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 4.4), sharey=True)
    specs = [
        ("temperature_c", "Temperature (deg C)", "#c0392b"),
        ("salinity_pss", "Salinity (PSS-78)", "#1f4e79"),
        ("sound_speed_mps", "Sound speed (m/s)", "#1e8449"),
    ]
    for ax, (key, xlab, col) in zip(axes, specs):
        zj, yj = series(jan_rows, key)
        zu, yu = series(jul_rows, key)
        ax.plot(yj, zj, color=col, ls="-", lw=1.5, label="January")
        ax.plot(yu, zu, color=col, ls="--", lw=1.5, label="July")
        ax.set_xlabel(xlab)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7)
    axes[0].set_ylabel("Depth (m)")
    axes[0].invert_yaxis()
    glat = station_meta["grid_lat"]
    glon = station_meta["grid_lon"]
    fig.suptitle(
        f"WOA23 monthly OA  ·  grid {glat:.3f}N, {glon:.3f}E\n"
        "Mackenzie (1981) SSP  ·  monthly fields end at 1500 m",
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, "ssp_jan_jul_primary.png"), dpi=180)
    plt.close()


def main() -> int:
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(PROF, exist_ok=True)
    os.makedirs(FIGS, exist_ok=True)

    # Mackenzie self-check at a coefficient-only point (T=S-35=D=0).
    c0 = float(mackenzie_ssp(0.0, 35.0, 0.0))
    if abs(c0 - 1448.96) > 1e-9:
        raise RuntimeError(f"Mackenzie constant term failed: {c0}")

    provenance = {
        "product": "WOA23 0.25-degree objectively analyzed monthly climatology",
        "portal": "https://www.ncei.noaa.gov/products/world-ocean-atlas",
        "subset_method": "NCEI THREDDS NetcdfSubset (ncss/grid), not full global files",
        "bbox_request": {"south": SOUTH, "north": NORTH, "west": WEST, "east": EAST},
        "analysis_box": {"lat": [LAT_MIN, LAT_MAX], "lon": [LON_MIN, LON_MAX]},
        "target": {"lat": TARGET_LAT, "lon": TARGET_LON},
        "variables": {"temperature": "t_an", "salinity": "s_an"},
        "sound_speed": {
            "formula": "Mackenzie 1981 nine-term",
            "citation": "K. V. Mackenzie, Nine-term equation for sound speed in the oceans, J. Acoust. Soc. Am. 70, 807-812 (1981).",
            "units": "m/s from T (deg C), S (PSS-78 as ppt), D (m)",
            "not_used": "UNESCO Chen-Millero, TEOS-10, Bellhop, eigenrays",
        },
        "depth_limit": {
            "monthly_m": 1500,
            "annual_m": 5500,
            "note": "WOA monthly OA fields are defined on 57 standard levels, 0-1500 m. Annual OA has 102 levels to 5500 m. Monthly SSPs in this dataset are not spliced with the annual deep field.",
        },
        "downloads": [],
    }

    jobs = []
    for month in MONTHS:
        mm = f"{month:02d}"
        jobs.append(("t", f"woa23_decav_t{mm}_04.nc", f"t_an_m{mm}.nc", "t_an", month, "monthly"))
        jobs.append(("s", f"woa23_decav_s{mm}_04.nc", f"s_an_m{mm}.nc", "s_an", month, "monthly"))
    jobs.append(("t", "woa23_decav_t00_04.nc", "t_an_annual.nc", "t_an", 0, "annual"))
    jobs.append(("s", "woa23_decav_s00_04.nc", "s_an_annual.nc", "s_an", 0, "annual"))

    force = "--force" in sys.argv
    for kind, remote_name, local_name, var, month, period in jobs:
        dest = os.path.join(RAW, local_name)
        base = NCSS_T if kind == "t" else NCSS_S
        url = base.format(name=remote_name) + ncss_query(var)
        src = HTTP_T if kind == "t" else HTTP_S
        if (not force) and os.path.isfile(dest) and os.path.getsize(dest) > 1000:
            print(f"keeping {local_name} ({os.path.getsize(dest)} bytes)", flush=True)
            info = {
                "url": url,
                "bytes": os.path.getsize(dest),
                "utc": "existing",
                "skipped_download": True,
            }
        else:
            print(f"downloading {local_name} ...", flush=True)
            info = download(url, dest)
            print(f"  {info['bytes']} bytes  {info['utc']}", flush=True)
        info.update(
            {
                "local": os.path.relpath(dest, ROOT),
                "woa_filename": remote_name,
                "variable": var,
                "month": month,
                "period": period,
                "full_file_url": src.format(name=remote_name),
            }
        )
        provenance["downloads"].append(info)

    lat, lon, depth, t0, t_attrs = open_oa(os.path.join(RAW, "t_an_m01.nc"), "t_an")
    ocean_mask = np.isfinite(t0[0, :, :])
    stations = station_table(lat, lon, ocean_mask)
    write_csv(
        os.path.join(PROF, "stations.csv"),
        stations,
        [
            "station",
            "requested_lat",
            "requested_lon",
            "grid_lat",
            "grid_lon",
            "ilat",
            "ilon",
            "offset_km",
            "land_snap",
            "note",
        ],
    )
    provenance["woa_attributes_january_temperature"] = t_attrs
    provenance["stations"] = stations
    provenance["depth_levels_monthly_m"] = [float(z) for z in WOA_DEPTH_MONTHLY_M]
    np.savetxt(os.path.join(PROF, "woa_standard_depths_monthly_m.txt"), WOA_DEPTH_MONTHLY_M, fmt="%.1f")
    np.savetxt(os.path.join(PROF, "woa_standard_depths_annual_m.txt"), WOA_DEPTH_ANNUAL_M, fmt="%.1f")

    all_rows = []
    for month in MONTHS:
        mm = f"{month:02d}"
        _, _, z_t_ncss, t_field, _ = open_oa(os.path.join(RAW, f"t_an_m{mm}.nc"), "t_an")
        _, _, z_s_ncss, s_field, _ = open_oa(os.path.join(RAW, f"s_an_m{mm}.nc"), "s_an")
        if t_field.shape[0] != len(WOA_DEPTH_MONTHLY_M) or s_field.shape[0] != len(WOA_DEPTH_MONTHLY_M):
            raise RuntimeError(
                f"month {mm}: expected {len(WOA_DEPTH_MONTHLY_M)} levels, "
                f"got T {t_field.shape[0]} S {s_field.shape[0]} (NCSS depths {z_t_ncss[0]}..{z_t_ncss[-1]})"
            )
        z_t = WOA_DEPTH_MONTHLY_M
        for st in stations:
            i, j = st["ilat"], st["ilon"]
            for k, z in enumerate(z_t):
                t = float(t_field[k, i, j])
                s = float(s_field[k, i, j])
                if math.isnan(t) or math.isnan(s):
                    c = float("nan")
                else:
                    c = float(mackenzie_ssp(t, s, z))
                all_rows.append(
                    {
                        "station": st["station"],
                        "grid_lat": st["grid_lat"],
                        "grid_lon": st["grid_lon"],
                        "month": month,
                        "month_name": MONTH_NAME[month],
                        "period": "monthly",
                        "depth_m": float(z),
                        "temperature_c": t,
                        "salinity_pss": s,
                        "sound_speed_mps": c,
                        "ssp_formula": "Mackenzie1981",
                    }
                )

    # Annual deep field, stored separately (not spliced).
    _, _, z_ta_ncss, t_ann, _ = open_oa(os.path.join(RAW, "t_an_annual.nc"), "t_an")
    _, _, z_sa_ncss, s_ann, _ = open_oa(os.path.join(RAW, "s_an_annual.nc"), "s_an")
    if t_ann.shape[0] != len(WOA_DEPTH_ANNUAL_M):
        raise RuntimeError(f"annual T levels {t_ann.shape[0]} != {len(WOA_DEPTH_ANNUAL_M)}")
    z_ta = WOA_DEPTH_ANNUAL_M
    provenance["depth_levels_annual_m"] = [float(z) for z in z_ta]
    provenance["ncss_depth_rewrite"] = {
        "issue": "THREDDS NCSS wrote depth as contiguous-interval midpoints (0 m -> 1.25 m, 100 m -> 105 m, 1500 m -> 1487.5 m).",
        "correction": "Profiles use the original WOA standard-depth axis from the file `depth` variable via OPeNDAP. T/S values are unchanged; only the depth coordinate attached to each level is corrected.",
        "monthly_ncss_first_last_m": [float(z_t_ncss[0]), float(z_t_ncss[-1])],
        "annual_ncss_first_last_m": [float(z_ta_ncss[0]), float(z_ta_ncss[-1])],
    }
    annual_rows = []
    for st in stations:
        i, j = st["ilat"], st["ilon"]
        for k, z in enumerate(z_ta):
            t = float(t_ann[k, i, j])
            s = float(s_ann[k, i, j])
            if math.isnan(t) or math.isnan(s):
                c = float("nan")
            else:
                c = float(mackenzie_ssp(t, s, z))
            annual_rows.append(
                {
                    "station": st["station"],
                    "grid_lat": st["grid_lat"],
                    "grid_lon": st["grid_lon"],
                    "month": 0,
                    "month_name": "annual",
                    "period": "annual",
                    "depth_m": float(z),
                    "temperature_c": t,
                    "salinity_pss": s,
                    "sound_speed_mps": c,
                    "ssp_formula": "Mackenzie1981",
                }
            )

    fields = [
        "station",
        "grid_lat",
        "grid_lon",
        "month",
        "month_name",
        "period",
        "depth_m",
        "temperature_c",
        "salinity_pss",
        "sound_speed_mps",
        "ssp_formula",
    ]
    write_csv(os.path.join(PROF, "woa23_wp_monthly_profiles.csv"), all_rows, fields)
    write_csv(os.path.join(PROF, "woa23_wp_annual_profiles.csv"), annual_rows, fields)
    jan = [r for r in all_rows if r["month"] == 1]
    jul = [r for r in all_rows if r["month"] == 7]
    write_csv(os.path.join(PROF, "woa23_wp_january_profiles.csv"), jan, fields)
    write_csv(os.path.join(PROF, "woa23_wp_july_profiles.csv"), jul, fields)

    def write_ssp_column(path: str, rows: list[dict], station: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# depth_m sound_speed_mps  Mackenzie1981 from WOA23 t_an,s_an\n")
            for r in rows:
                if r["station"] != station:
                    continue
                if not (isinstance(r["sound_speed_mps"], float) and math.isfinite(r["sound_speed_mps"])):
                    continue
                f.write(f"{r['depth_m']:.1f}  {r['sound_speed_mps']:.4f}\n")

    write_ssp_column(os.path.join(PROF, "ssp_primary_january.txt"), jan, "primary")
    write_ssp_column(os.path.join(PROF, "ssp_primary_july.txt"), jul, "primary")

    primary = next(s for s in stations if s["station"] == "primary")
    plot_primary(jan, jul, primary)

    # Surface/channel summary for the primary station, Jan vs Jul, from monthly data only.
    summary = []
    for month, rows in ((1, jan), (7, jul)):
        prim = [
            r
            for r in rows
            if r["station"] == "primary"
            and isinstance(r["sound_speed_mps"], float)
            and math.isfinite(r["sound_speed_mps"])
        ]
        if not prim:
            continue
        c = np.array([r["sound_speed_mps"] for r in prim])
        z = np.array([r["depth_m"] for r in prim])
        t = np.array([r["temperature_c"] for r in prim])
        kmin = int(np.argmin(c))
        summary.append(
            {
                "month": month,
                "month_name": MONTH_NAME[month],
                "n_levels_with_data": len(prim),
                "z_min_m": float(z[0]),
                "z_max_m": float(z[-1]),
                "T_surface_c": float(t[0]),
                "T_1500_c": float(t[-1]),
                "c_surface_mps": float(c[0]),
                "c_min_mps": float(c[kmin]),
                "z_c_min_m": float(z[kmin]),
                "c_1500_mps": float(c[-1]),
            }
        )
    write_csv(
        os.path.join(PROF, "ssp_january_july_summary.csv"),
        summary,
        list(summary[0].keys()) if summary else ["month"],
    )
    provenance["january_july_summary"] = summary
    provenance["built_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _jsonable(obj):
        if isinstance(obj, dict):
            return {str(k): _jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_jsonable(v) for v in obj]
        if isinstance(obj, (np.floating, np.integer)):
            return obj.item()
        return obj

    with open(os.path.join(OUT, "provenance.json"), "w", encoding="utf-8") as f:
        json.dump(_jsonable(provenance), f, indent=2)

    print("stations:")
    for st in stations:
        print(
            f"  {st['station']:10s}  requested {st['requested_lat']:.1f}N {st['requested_lon']:.1f}E"
            f"  -> grid {st['grid_lat']:.3f}N {st['grid_lon']:.3f}E"
            f"  offset {st['offset_km']:.2f} km"
        )
    print("summary:")
    for s in summary:
        print(
            f"  {s['month_name']:9s}  T(0)={s['T_surface_c']:.2f} C  "
            f"c(0)={s['c_surface_mps']:.2f}  c_min={s['c_min_mps']:.2f} at {s['z_c_min_m']:.0f} m  "
            f"c(1500)={s['c_1500_mps']:.2f}  levels={s['n_levels_with_data']}"
        )
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
