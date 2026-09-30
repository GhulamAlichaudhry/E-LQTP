#!/usr/bin/env python3
"""Western Pacific Bellhop run: WOA23 SSP, GEBCO 5524 m flat bottom, 24 kHz.

Step C geometry (unchanged except bottom depth):
  source 50 m; receivers 0-500 m / 10 m; ranges 0-2000 m / 10 m;
  24 kHz; coherent ('C') Gaussian beams; January and July.

Bottom: FLAT 5524 m (GEBCO_2026 primary cell / 2 km east transect,
peak-to-peak 2.5 m). Not a 500 m lid.

SSP: NOT truncated at 500 m. Truncating the profile at 500 m while placing
the bottom at 5524 m would make Bellhop hold c(500) as an isovelocity
column through the SOFAR axis (~1050 m) and the entire abyssal layer.
That is the same class of error as a fake 500 m seafloor. The table is
WOA23 monthly 0-1500 m, WOA23 annual 1550-5500 m, Mackenzie 1981 at 5524 m
from annual T,S at 5500 m.

ns-3 still places nodes in the upper 500 m. The waveguide they sit in is
5.5 km deep; rays are not confined to the node slab.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_woa23_ssp import mackenzie_ssp  # noqa: E402

WOA_DIR = ROOT / "data" / "woa23" / "profiles"
GEBCO_CSV = ROOT / "data" / "gebco" / "bathymetry_transect_primary.csv"
OUT = ROOT / "data" / "bellhop"
BELLHOP = ROOT / "opt" / "at" / "Bellhop" / "bellhop.exe"

FREQ_HZ = 24000.0
SRC_DEPTH_M = 50.0
RCV_Z_MAX_M = 500.0
RCV_DZ_M = 10.0
RCV_R_MAX_M = 2000.0
RCV_DR_M = 10.0
BOTTOM_M = 5524.0
# Assumed abyssal clay/ooze fluid halfspace — not a GEBCO or core measurement.
BOT_CP = 1600.0
BOT_CS = 0.0
BOT_RHO = 1.8
BOT_ALPHA = 0.5  # dB / wavelength
NBEAMS = 9601  # matches Bellhop auto estimate 0.3*R*f/c0 at 2 km, 24 kHz
ALPHA1, ALPHA2 = -89.0, 89.0
STEP_M = 1.0
ZBOX_M = 5600.0
RBOX_KM = 2.10
SSPOPT = "CVWT"  # C-linear, vacuum above, dB/wavelength, Thorp volume

# Representative arrivals grid (full 10 m range grid is for TL only).
ARR_RANGES_M = (200.0, 500.0, 1000.0, 1500.0, 2000.0)
FOCUS = dict(src_m=50.0, rcv_m=50.0, range_m=1000.0)


def _jsonable(obj):
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(type(obj))


def load_primary_monthly(month: int) -> pd.DataFrame:
    name = "woa23_wp_january_profiles.csv" if month == 1 else "woa23_wp_july_profiles.csv"
    df = pd.read_csv(WOA_DIR / name)
    p = df[df["station"] == "primary"].copy().sort_values("depth_m")
    if p.empty:
        raise RuntimeError(f"no primary station in {name}")
    return p


def load_primary_annual() -> pd.DataFrame:
    df = pd.read_csv(WOA_DIR / "woa23_wp_annual_profiles.csv")
    p = df[df["station"] == "primary"].copy().sort_values("depth_m")
    p = p[np.isfinite(p["sound_speed_mps"])]
    return p


def gebco_east_stats() -> dict:
    raw = pd.read_csv(GEBCO_CSV, comment="#")
    d = raw["bottom_depth_m"].to_numpy(float)
    r = raw["range_m"].to_numpy(float)
    return {
        "origin_m": float(d[0]),
        "at_2km_m": float(d[-1]),
        "min_m": float(d.min()),
        "max_m": float(d.max()),
        "ptp_m": float(d.max() - d.min()),
        "n": int(len(d)),
        "range_max_m": float(r.max()),
        "csv": str(GEBCO_CSV),
    }


def build_full_column_ssp(month: int) -> pd.DataFrame:
    """Monthly 0-1500 + annual 1550-5500 + Mackenzie point at 5524 m."""
    monthly = load_primary_monthly(month)
    annual = load_primary_annual()
    m = monthly.loc[
        monthly["depth_m"] <= 1500.0,
        ["depth_m", "temperature_c", "salinity_pss", "sound_speed_mps"],
    ].copy()
    m["ssp_source"] = "WOA23 monthly Mackenzie1981"
    a = annual.loc[
        annual["depth_m"] > 1500.0,
        ["depth_m", "temperature_c", "salinity_pss", "sound_speed_mps"],
    ].copy()
    a["ssp_source"] = "WOA23 annual Mackenzie1981"
    deep = annual[annual["depth_m"] == 5500.0].iloc[0]
    c5524 = float(
        mackenzie_ssp(deep["temperature_c"], deep["salinity_pss"], BOTTOM_M)
    )
    extra = pd.DataFrame(
        {
            "depth_m": [BOTTOM_M],
            "temperature_c": [float(deep["temperature_c"])],
            "salinity_pss": [float(deep["salinity_pss"])],
            "sound_speed_mps": [c5524],
            "ssp_source": [
                "Mackenzie1981 at 5524 m from annual T,S at 5500 m"
            ],
        }
    )
    out = pd.concat([m, a, extra], ignore_index=True).sort_values("depth_m")
    # last depth must equal the Bellhop bottom
    if abs(float(out["depth_m"].iloc[-1]) - BOTTOM_M) > 1e-6:
        raise RuntimeError("SSP does not end at the 5524 m bottom")
    return out.reset_index(drop=True)


def build_trunc500_held_ssp(month: int) -> pd.DataFrame:
    """0-500 m monthly, then isovelocity hold of c(500) down to 5524 m.

    This is what 'SSP truncated to 0-500 m' would actually do inside Bellhop
    with a 5524 m bottom. Kept as a sensitivity, not the primary run.
    """
    monthly = load_primary_monthly(month)
    m = monthly.loc[
        monthly["depth_m"] <= 500.0,
        ["depth_m", "temperature_c", "salinity_pss", "sound_speed_mps"],
    ].copy()
    m["ssp_source"] = "WOA23 monthly Mackenzie1981"
    last = m.iloc[-1]
    extra = pd.DataFrame(
        {
            "depth_m": [BOTTOM_M],
            "temperature_c": [float(last["temperature_c"])],
            "salinity_pss": [float(last["salinity_pss"])],
            "sound_speed_mps": [float(last["sound_speed_mps"])],
            "ssp_source": ["isovelocity hold of c(500) — NOT used as primary"],
        }
    )
    return pd.concat([m, extra], ignore_index=True)


def write_ssp_txt(df: pd.DataFrame, path: Path, header: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write(f"# {header}\n")
        f.write("# depth_m sound_speed_mps source\n")
        for _, row in df.iterrows():
            f.write(
                f"{row.depth_m:.1f}  {row.sound_speed_mps:.4f}  {row.ssp_source}\n"
            )


def format_ssp_block(df: pd.DataFrame) -> str:
    lines = []
    for _, row in df.iterrows():
        lines.append(f"  {row.depth_m:8.2f}  {row.sound_speed_mps:10.4f} /")
    return "\n".join(lines)


def write_env(
    path: Path,
    *,
    title: str,
    ssp: pd.DataFrame,
    run_type: str,
    rd_n: int,
    rd_first: float,
    rd_last: float,
    rr_values_km: list[float] | None = None,
    rr_n: int | None = None,
    rr_first_km: float | None = None,
    rr_last_km: float | None = None,
    nbeams: int = NBEAMS,
    src_depth: float = SRC_DEPTH_M,
    rbox_km: float | None = None,
) -> None:
    npts = len(ssp)
    rbox = RBOX_KM if rbox_km is None else float(rbox_km)
    if rr_values_km is not None:
        rr_block = f"{len(rr_values_km)}\n" + " ".join(f"{x:.6f}" for x in rr_values_km) + " /"
    else:
        rr_block = f"{rr_n}\n{rr_first_km:.6f} {rr_last_km:.6f} /"
    text = f"""'{title}'
{FREQ_HZ:.1f}
1
'{SSPOPT}'
{npts}  0.0  {BOTTOM_M:.2f}
{format_ssp_block(ssp)}
'A'  0.0
 {BOTTOM_M:.2f}  {BOT_CP:.2f}  {BOT_CS:.2f}  {BOT_RHO:.2f}  {BOT_ALPHA:.2f} /
1
{src_depth:.2f} /
{rd_n}
{rd_first:.2f} {rd_last:.2f} /
{rr_block}
'{run_type}'
{nbeams}
{ALPHA1:.1f} {ALPHA2:.1f} /
{STEP_M:.1f}  {ZBOX_M:.1f}  {rbox:.3f}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run_bellhop(env_path: Path) -> None:
    if not BELLHOP.is_file():
        raise FileNotFoundError(
            f"bellhop.exe not at {BELLHOP}; run scripts/install-bellhop.sh"
        )
    env_path = env_path.resolve()
    fileroot = str(env_path.with_suffix(""))
    proc = subprocess.run(
        [str(BELLHOP), fileroot],
        cwd=str(env_path.parent),
        capture_output=True,
        text=True,
    )
    prt = env_path.with_suffix(".prt")
    log = env_path.with_suffix(".bellhop.log")
    log.write_text(
        "STDOUT\n" + proc.stdout + "\nSTDERR\n" + proc.stderr + f"\nreturncode={proc.returncode}\n"
    )
    if proc.returncode != 0:
        tail = prt.read_text()[-4000:] if prt.exists() else proc.stderr
        raise RuntimeError(f"Bellhop failed on {env_path.name}:\n{tail}")
    # Bellhop often returns 0 even on env errors; check the print file.
    if prt.exists():
        prt_txt = prt.read_text()
        for bad in ("FATAL ERROR", "Unknown option", "Unable to open"):
            if bad in prt_txt:
                raise RuntimeError(f"Bellhop reported {bad} in {prt.name}")


def read_shd(path: Path) -> dict:
    """Porter binary shade file (direct-access records). Port of read_shd_bin.m."""
    with path.open("rb") as f:
        data = f.read()
    recl = struct.unpack_from("<i", data, 0)[0]
    rec = 4 * recl

    def rec_off(n: int) -> int:
        return n * rec

    plot_type = data[rec_off(1) : rec_off(1) + 10].decode("ascii", "replace")
    nfreq, ntheta, nsx, nsy, nsz, nrz, nrr = struct.unpack_from(
        "<7i", data, rec_off(2)
    )
    freq0, atten = struct.unpack_from("<2d", data, rec_off(2) + 28)
    sz = np.frombuffer(data, dtype="<f4", count=nsz, offset=rec_off(7)).copy()
    rz = np.frombuffer(data, dtype="<f4", count=nrz, offset=rec_off(8)).copy()
    rr = np.frombuffer(data, dtype="<f8", count=nrr, offset=rec_off(9)).copy()
    pressure = np.zeros((nsz, nrz, nrr), dtype=np.complex64)
    for isz in range(nsz):
        for irz in range(nrz):
            recnum = 10 + isz * nrz + irz
            off = rec_off(recnum)
            raw = np.frombuffer(data, dtype="<f4", count=2 * nrr, offset=off)
            pressure[isz, irz, :] = raw[0::2] + 1j * raw[1::2]
    tl = -20.0 * np.log10(np.maximum(np.abs(pressure), 1e-30))
    return {
        "plot_type": plot_type,
        "freq0": float(freq0),
        "atten": float(atten),
        "sz": sz,
        "rz": rz,
        "rr": rr,  # metres
        "pressure": pressure,
        "tl_db": tl,
        "nfreq": nfreq,
        "ntheta": ntheta,
    }


def read_arrivals_asc(path: Path) -> list[dict]:
    """ASCII 2-D Bellhop .arr (run type 'A')."""
    tok: list[str] = []
    with path.open() as f:
        for line in f:
            tok.extend(line.split())
    i = 0

    def take(n=1):
        nonlocal i
        sl = tok[i : i + n]
        i += n
        return sl

    flag = take(1)[0].strip("'\"")
    if flag != "2D":
        raise ValueError(f"{path} is not a 2D ASCII arrivals file (got {flag!r})")
    freq = float(take(1)[0])
    nsz = int(take(1)[0])
    sz = [float(x) for x in take(nsz)]
    nrz = int(take(1)[0])
    rz = [float(x) for x in take(nrz)]
    nrr = int(take(1)[0])
    rr = [float(x) for x in take(nrr)]
    rows = []
    for isd in range(nsz):
        _narrmx = int(take(1)[0])
        for irz in range(nrz):
            for irr in range(nrr):
                narr = int(take(1)[0])
                for k in range(narr):
                    amp, phase, delay_re, delay_im, src_ang, rcv_ang, ntop, nbot = (
                        float(x) for x in take(8)
                    )
                    rows.append(
                        {
                            "freq_hz": freq,
                            "src_depth_m": sz[isd],
                            "rcv_depth_m": rz[irz],
                            "range_m": rr[irr],
                            "amp": amp,
                            "phase_deg": phase,
                            "delay_s": delay_re,
                            "delay_im_s": delay_im,
                            "src_decl_deg": src_ang,
                            "rcv_decl_deg": rcv_ang,
                            "n_top": int(round(ntop)),
                            "n_bot": int(round(nbot)),
                            "arrival_index": k,
                        }
                    )
    if i != len(tok):
        # leftover is OK only if all-whitespace already consumed
        pass
    return rows


def classify_row(row: dict) -> str:
    if row["n_bot"] > 0:
        return "bottom_interacting"
    if row["n_top"] > 0:
        return "surface_only"
    return "direct_refracted"


def energy(row: dict) -> float:
    return float(row["amp"]) ** 2


def summarise_arrivals(rows: list[dict], src, rcv, rng, band_m=0.6) -> dict:
    sel = [
        r
        for r in rows
        if abs(r["src_depth_m"] - src) <= band_m
        and abs(r["rcv_depth_m"] - rcv) <= band_m
        and abs(r["range_m"] - rng) <= band_m
    ]
    n = len(sel)
    if n == 0:
        return {
            "n": 0,
            "src_m": src,
            "rcv_m": rcv,
            "range_m": rng,
            "note": "no resolved arrivals",
        }
    labels = [classify_row(r) for r in sel]
    e = np.array([energy(r) for r in sel], dtype=float)
    e = np.maximum(e, 0.0)
    e_sum = float(e.sum()) if e.size else 0.0

    def frac_count(name):
        return labels.count(name) / n

    def frac_e(name):
        if e_sum <= 0:
            return 0.0
        mask = np.array([lab == name for lab in labels])
        return float(e[mask].sum() / e_sum)

    no_bot = sum(1 for r in sel if r["n_bot"] == 0)
    return {
        "n": n,
        "src_m": src,
        "rcv_m": rcv,
        "range_m": rng,
        "count_direct_refracted": labels.count("direct_refracted"),
        "count_surface_only": labels.count("surface_only"),
        "count_bottom_interacting": labels.count("bottom_interacting"),
        "count_no_bottom": no_bot,
        "frac_count_direct_refracted": frac_count("direct_refracted"),
        "frac_count_surface_only": frac_count("surface_only"),
        "frac_count_bottom_interacting": frac_count("bottom_interacting"),
        "frac_count_surface_or_direct": no_bot / n,
        "frac_energy_direct_refracted": frac_e("direct_refracted"),
        "frac_energy_surface_only": frac_e("surface_only"),
        "frac_energy_bottom_interacting": frac_e("bottom_interacting"),
        "frac_energy_surface_or_direct": float(
            e[np.array([r["n_bot"] == 0 for r in sel])].sum() / e_sum
        )
        if e_sum
        else 0.0,
        "delay_min_s": min(r["delay_s"] for r in sel),
        "delay_max_s": max(r["delay_s"] for r in sel),
        "amp_max": max(abs(r["amp"]) for r in sel),
    }


def plot_ssp(jan: pd.DataFrame, jul: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.2, 7.4))
    ax.plot(jan.sound_speed_mps, jan.depth_m, color="#1f4e79", lw=1.8, label="January")
    ax.plot(jul.sound_speed_mps, jul.depth_m, color="#c45911", lw=1.8, label="July")
    ax.axhline(500.0, color="0.4", ls="--", lw=0.9, label="ns-3 node lid (500 m)")
    ax.axhline(BOTTOM_M, color="0.2", ls=":", lw=1.0, label=f"GEBCO bottom ({BOTTOM_M:.0f} m)")
    ax.set_ylim(BOTTOM_M + 50, -50)
    ax.set_xlabel("Sound speed (m/s)")
    ax.set_ylabel("Depth (m)")
    ax.set_title("WOA23 primary SSP, full water column")
    ax.legend(loc="lower left", fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_tl(shd: dict, title: str, path: Path) -> None:
    tl = shd["tl_db"][0]
    rr_km = shd["rr"] / 1000.0
    rz = shd["rz"]
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    clipped = np.clip(tl, 40, 120)
    im = ax.pcolormesh(rr_km, rz, clipped, shading="auto", cmap="viridis_r")
    ax.set_ylim(RCV_Z_MAX_M, 0)
    ax.set_xlim(0, RCV_R_MAX_M / 1000.0)
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Depth (m)")
    ax.set_title(title)
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("TL (dB re 1 m)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_arrivals(rows: list[dict], src, rcv, rng, title: str, path: Path) -> None:
    sel = [
        r
        for r in rows
        if abs(r["src_depth_m"] - src) < 0.6
        and abs(r["rcv_depth_m"] - rcv) < 0.6
        and abs(r["range_m"] - rng) < 0.6
    ]
    colors = {
        "direct_refracted": "#1f4e79",
        "surface_only": "#2e7d32",
        "bottom_interacting": "#c45911",
    }
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), sharey=True)
    if not sel:
        axes[0].text(0.5, 0.5, "no arrivals", ha="center", transform=axes[0].transAxes)
    else:
        for ax, (lo, hi, xlab) in zip(
            axes,
            ((0.64, 0.67, "Delay (s), water-column paths"), (0.0, 31.0, "Delay (s), full including bottom")),
        ):
            for r in sel:
                t = r["delay_s"]
                if t < lo or t > hi:
                    continue
                lab = classify_row(r)
                mag = 20.0 * math.log10(max(abs(r["amp"]), 1e-12))
                ax.vlines(t, mag - 10, mag, color=colors[lab], lw=1.8)
            ax.set_xlim(lo, hi)
            ax.set_xlabel(xlab)
            ax.grid(True, alpha=0.3)
        handles = [
            plt.Line2D([0], [0], color=c, lw=2, label=k.replace("_", " "))
            for k, c in colors.items()
        ]
        axes[1].legend(handles=handles, loc="lower right", fontsize=8)
        axes[0].set_ylabel("Arrival amplitude (dB)")
    fig.suptitle(title)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_fractions(summaries: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.6), sharey=True)
    cats = ["direct / refracted", "surface only", "bottom interacting"]
    for ax, season in zip(axes, ("january", "july")):
        s = summaries[season]["focus"]
        counts = [
            s["frac_count_direct_refracted"],
            s["frac_count_surface_only"],
            s["frac_count_bottom_interacting"],
        ]
        energy_f = [
            s["frac_energy_direct_refracted"],
            s["frac_energy_surface_only"],
            s["frac_energy_bottom_interacting"],
        ]
        x = np.arange(len(cats))
        ax.bar(x - 0.18, counts, 0.36, color="#5b9bd5", label="by count")
        ax.bar(x + 0.18, energy_f, 0.36, color="#ed7d31", label="by |A|²")
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=18, ha="right")
        ax.set_ylim(0, 1.05)
        ax.set_title(season.capitalize() + f"  n={s['n']}")
        ax.grid(True, axis="y", alpha=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("Fraction of resolved arrivals")
    fig.suptitle("src 50 m, rcv 50 m, range 1000 m  —  5524 m flat bottom")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def write_readme(summary: dict, path: Path) -> None:
    jan_f = summary["january"]["focus"]
    jul_f = summary["july"]["focus"]
    geb = summary["gebco"]
    gebco_rel = "data/gebco/bathymetry_transect_primary.csv"
    path.write_text(
        f"""# Bellhop Western Pacific run (24 kHz, 5524 m flat bottom)

Porter BELLHOP coherent transmission loss and eigenray arrivals at the
WOA23 / GEBCO primary cell **20.125°N, 124.125°E**. This is an acoustic
propagation calculation for later Aqua-Sim use. It is **not** an ns-3
result and it is **not** a sea trial.

## Why the bottom is 5524 m, not 500 m

ns-3 places network nodes only in the upper 500 m. Sound rays are not
confined to that slab. GEBCO_2026 at this cell is **{geb['origin_m']:.2f} m**
down. The 2 km east transect (`{gebco_rel}`) varies by only
**{geb['ptp_m']:.2f} m** peak-to-peak (min {geb['min_m']:.1f}, max {geb['max_m']:.1f}).
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
| Receiver ranges | 0–2000 m, 10 m (TL); 200, 500, 1000, 1500, 2000 m (arrivals) |
| Bottom | flat 5524 m acoustic halfspace |
| Bottom (assumed, not measured) | cp=1600 m/s, cs=0, ρ=1.8 g/cm³, α=0.5 dB/λ |
| Volume attenuation | Thorp (`SSPOPT=CVWT`) |
| Beams | {NBEAMS} over [{ALPHA1}, {ALPHA2}] deg |
| Step / box | {STEP_M} m, ZBOX={ZBOX_M} m, RBOX={RBOX_KM} km |

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
| Direct / refracted (no bounce) | {jan_f['count_direct_refracted']} | {jan_f['frac_count_direct_refracted']:.3f} | {jan_f['frac_energy_direct_refracted']:.3f} |
| Surface only | {jan_f['count_surface_only']} | {jan_f['frac_count_surface_only']:.3f} | {jan_f['frac_energy_surface_only']:.3f} |
| Bottom interacting | {jan_f['count_bottom_interacting']} | {jan_f['frac_count_bottom_interacting']:.3f} | {jan_f['frac_energy_bottom_interacting']:.3f} |
| Surface-only + direct (no bottom) | {jan_f['count_no_bottom']} | {jan_f['frac_count_surface_or_direct']:.3f} | {jan_f['frac_energy_surface_or_direct']:.3f} |

Resolved arrivals: **{jan_f['n']}**. Delay span {jan_f['delay_min_s']:.3f}–{jan_f['delay_max_s']:.2f} s.
The first bottom cluster is at ~7.28 s (one round trip to 5524 m).

### July (full-column SSP)

| Class | count | count fraction | energy fraction |
| --- | --- | --- | --- |
| Direct / refracted (no bounce) | {jul_f['count_direct_refracted']} | {jul_f['frac_count_direct_refracted']:.3f} | {jul_f['frac_energy_direct_refracted']:.3f} |
| Surface only | {jul_f['count_surface_only']} | {jul_f['frac_count_surface_only']:.3f} | {jul_f['frac_energy_surface_only']:.3f} |
| Bottom interacting | {jul_f['count_bottom_interacting']} | {jul_f['frac_count_bottom_interacting']:.3f} | {jul_f['frac_energy_bottom_interacting']:.3f} |
| Surface-only + direct (no bottom) | {jul_f['count_no_bottom']} | {jul_f['frac_count_surface_or_direct']:.3f} | {jul_f['frac_energy_surface_or_direct']:.3f} |

Resolved arrivals: **{jul_f['n']}**. Delay span {jul_f['delay_min_s']:.3f}–{jul_f['delay_max_s']:.2f} s.

**Count vs energy at this pair.** Bellhop traces ±89°, so it *does* find
steep eigenrays that hit 5524 m (launch angle ≈ 85°). Those are the
majority by count:

- January: **{100*jan_f['frac_count_bottom_interacting']:.0f}%** of {jan_f['n']} arrivals hit the bottom;
  only **{100*jan_f['frac_count_surface_or_direct']:.0f}%** are surface-only or direct/refracted.
- July: **{100*jul_f['frac_count_bottom_interacting']:.0f}%** / **{100*jul_f['frac_count_surface_or_direct']:.0f}%**.

They carry almost no energy at 24 kHz. One round trip to 5524 m is an
extra ~11 km; Thorp plus extra spreading puts the first bottom cluster
~40 dB below the water-column arrivals. Energy-weighted:

- January: **{100*jan_f['frac_energy_surface_or_direct']:.1f}%** surface/direct,
  **{100*jan_f['frac_energy_bottom_interacting']:.2f}%** bottom.
- July: **{100*jul_f['frac_energy_surface_or_direct']:.1f}%** /
  **{100*jul_f['frac_energy_bottom_interacting']:.2f}%**.

So: many *resolved geometric paths* reach the seafloor; the *transfer
function on this 0–500 m / 0–2000 m grid at 24 kHz* does not. A fake
500 m lid would have bounced those steep rays 5 km too soon and written
non-physical early bottom arrivals into the CIR.

## Files

```
data/bellhop/
  provenance.json
  ssp/ssp_full_january.csv          ssp_full_july.csv
  env/*.env
  tl/january_tl.npz  july_tl.npz
  arrivals/*.csv
  figs/*.png
```

Raw `.shd` / `.arr` / `.prt` stay next to the env files when the run is
local; they are not required to read the npz/csv products.
"""
    )


def _write_pairs_csv(summary: dict) -> None:
    rows = []
    for season in ("january", "july"):
        for p in summary[season].get("pairs", []):
            q = dict(p)
            q["season"] = season
            rows.append(q)
        foc = dict(summary[season].get("focus", {}))
        if foc:
            foc["season"] = season
            foc["pair"] = "focus_50_50_1000"
    if not rows:
        return
    pd.DataFrame(rows).to_csv(OUT / "arrivals" / "pairs_summary.csv", index=False)


def n_points(first, last, step) -> int:
    return int(round((last - first) / step)) + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer beams, coarser TL grid")
    ap.add_argument("--skip-tl", action="store_true")
    ap.add_argument("--skip-arrivals", action="store_true")
    ap.add_argument("--skip-trunc500", action="store_true")
    ap.add_argument("--plots-only", action="store_true", help="regenerate figures from existing csv/npz")
    args = ap.parse_args()

    nbeams = 801 if args.quick else NBEAMS
    dz = 50.0 if args.quick else RCV_DZ_M
    dr = 50.0 if args.quick else RCV_DR_M
    nrd = n_points(0.0, RCV_Z_MAX_M, dz)
    nrr = n_points(0.0, RCV_R_MAX_M, dr)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "env").mkdir(exist_ok=True)
    (OUT / "ssp").mkdir(exist_ok=True)
    (OUT / "tl").mkdir(exist_ok=True)
    (OUT / "arrivals").mkdir(exist_ok=True)
    (OUT / "figs").mkdir(exist_ok=True)

    geb = gebco_east_stats()
    if args.plots_only:
        summary = json.loads((OUT / "provenance.json").read_text())
        for name, month_label in (("january", "January"), ("july", "July")):
            rows = pd.read_csv(OUT / "arrivals" / f"{name}_arrivals.csv").to_dict("records")
            plot_arrivals(
                rows,
                FOCUS["src_m"],
                FOCUS["rcv_m"],
                FOCUS["range_m"],
                f"{month_label} arrivals  src=50 m  rcv=50 m  R=1000 m",
                OUT / "figs" / f"arrivals_{name}_50_50_1000.png",
            )
            tl = np.load(OUT / "tl" / f"{name}_tl.npz")
            shd = {
                "tl_db": tl["tl_db"],
                "rz": tl["rz_m"],
                "rr": tl["rr_m"],
                "sz": tl["sz_m"],
            }
            plot_tl(
                shd,
                f"{month_label} coherent TL, 24 kHz, src 50 m, bottom {BOTTOM_M:.0f} m",
                OUT / "figs" / f"tl_{name}.png",
            )
        jan = pd.read_csv(OUT / "ssp" / "ssp_full_january.csv")
        jul = pd.read_csv(OUT / "ssp" / "ssp_full_july.csv")
        plot_ssp(jan, jul, OUT / "figs" / "ssp_full_column.png")
        plot_fractions(summary, OUT / "figs" / "eigenray_fractions_50_50_1000.png")
        write_readme(summary, OUT / "README.md")
        _write_pairs_csv(summary)
        return 0

    ssp = {}
    trunc = {}
    for month, name in ((1, "january"), (7, "july")):
        ssp[name] = build_full_column_ssp(month)
        trunc[name] = build_trunc500_held_ssp(month)
        write_ssp_txt(
            ssp[name],
            OUT / "ssp" / f"ssp_full_{name}.txt",
            f"full-column SSP {name} to {BOTTOM_M:.0f} m",
        )
        ssp[name].to_csv(OUT / "ssp" / f"ssp_full_{name}.csv", index=False)
        trunc[name].to_csv(OUT / "ssp" / f"ssp_trunc500_{name}.csv", index=False)

    plot_ssp(ssp["january"], ssp["july"], OUT / "figs" / "ssp_full_column.png")

    summary = {
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freq_hz": FREQ_HZ,
        "src_depth_m": SRC_DEPTH_M,
        "bottom_m": BOTTOM_M,
        "bottom_justification": (
            "GEBCO_2026 east 2 km transect ptp "
            f"{geb['ptp_m']:.2f} m about {geb['origin_m']:.1f} m; flat 5524 m"
        ),
        "ssp_policy": (
            "full column: monthly 0-1500 + annual 1550-5500 + Mackenzie 5524; "
            "not truncated at 500 m"
        ),
        "bottom_halfspace_assumed": {
            "cp": BOT_CP,
            "cs": BOT_CS,
            "rho": BOT_RHO,
            "alpha_db_per_wavelength": BOT_ALPHA,
            "note": "assumed abyssal clay/ooze; not measured",
        },
        "gebco": geb,
        "nbeams": nbeams,
        "quick": bool(args.quick),
        "january": {},
        "july": {},
    }

    rr_km = [r / 1000.0 for r in ARR_RANGES_M]

    for name, month_label in (("january", "January"), ("july", "July")):
        env_tl = OUT / "env" / f"wp_{name}_tl.env"
        env_arr = OUT / "env" / f"wp_{name}_arr.env"
        env_tr = OUT / "env" / f"wp_{name}_arr_trunc500.env"

        write_env(
            env_tl,
            title=f"WP {month_label} 24kHz coherent TL, flat {BOTTOM_M:.0f} m",
            ssp=ssp[name],
            run_type="CB",
            rd_n=nrd,
            rd_first=0.0,
            rd_last=RCV_Z_MAX_M,
            rr_n=nrr,
            rr_first_km=0.0,
            rr_last_km=RCV_R_MAX_M / 1000.0,
            nbeams=nbeams,
        )
        write_env(
            env_arr,
            title=f"WP {month_label} 24kHz arrivals, flat {BOTTOM_M:.0f} m",
            ssp=ssp[name],
            run_type="A",
            rd_n=nrd,
            rd_first=0.0,
            rd_last=RCV_Z_MAX_M,
            rr_values_km=rr_km,
            nbeams=nbeams,
        )
        write_env(
            env_tr,
            title=f"WP {month_label} arrivals SENSITIVITY trunc500 SSP hold",
            ssp=trunc[name],
            run_type="A",
            rd_n=n_points(0.0, RCV_Z_MAX_M, 50.0),
            rd_first=0.0,
            rd_last=RCV_Z_MAX_M,
            rr_values_km=[1.0],
            nbeams=nbeams,
        )

        season = {"env_tl": str(env_tl.relative_to(ROOT)), "env_arr": str(env_arr.relative_to(ROOT))}

        if not args.skip_tl:
            print(f"== TL {name} beams={nbeams} grid={nrd}x{nrr}", flush=True)
            run_bellhop(env_tl)
            shd_path = env_tl.with_suffix(".shd")
            shd = read_shd(shd_path)
            np.savez_compressed(
                OUT / "tl" / f"{name}_tl.npz",
                tl_db=shd["tl_db"],
                rz_m=shd["rz"],
                rr_m=shd["rr"],
                sz_m=shd["sz"],
                freq0=np.array([shd["freq0"]]),
            )
            # CSV of TL along src-depth row nearest 50 m, for easy inspection
            iz = int(np.argmin(np.abs(shd["rz"] - SRC_DEPTH_M)))
            with (OUT / "tl" / f"{name}_tl_z{shd['rz'][iz]:.0f}m.csv").open("w") as f:
                f.write("range_m,tl_db\n")
                for r, v in zip(shd["rr"], shd["tl_db"][0, iz, :]):
                    f.write(f"{r:.1f},{float(v):.4f}\n")
            plot_tl(
                shd,
                f"{month_label} coherent TL, 24 kHz, src 50 m, bottom {BOTTOM_M:.0f} m",
                OUT / "figs" / f"tl_{name}.png",
            )
            # TL at focus receiver
            ir = int(np.argmin(np.abs(shd["rr"] - FOCUS["range_m"])))
            izf = int(np.argmin(np.abs(shd["rz"] - FOCUS["rcv_m"])))
            season["tl_focus_db"] = float(shd["tl_db"][0, izf, ir])
            season["tl_median_db"] = float(np.median(shd["tl_db"][0]))
            season["tl_shape"] = list(shd["tl_db"].shape)

        if not args.skip_arrivals:
            print(f"== arrivals {name}", flush=True)
            run_bellhop(env_arr)
            arr_path = env_arr.with_suffix(".arr")
            rows = read_arrivals_asc(arr_path)
            csv_path = OUT / "arrivals" / f"{name}_arrivals.csv"
            if rows:
                pd.DataFrame(rows).to_csv(csv_path, index=False)
            else:
                csv_path.write_text("no arrivals\n")
            focus = summarise_arrivals(
                rows, FOCUS["src_m"], FOCUS["rcv_m"], FOCUS["range_m"]
            )
            extra_pairs = []
            for rcv in (0.0, 50.0, 100.0, 250.0, 500.0):
                for rng in ARR_RANGES_M:
                    extra_pairs.append(summarise_arrivals(rows, SRC_DEPTH_M, rcv, rng))
            season["focus"] = focus
            season["pairs"] = extra_pairs
            plot_arrivals(
                rows,
                FOCUS["src_m"],
                FOCUS["rcv_m"],
                FOCUS["range_m"],
                f"{month_label} arrivals  src=50 m  rcv=50 m  R=1000 m",
                OUT / "figs" / f"arrivals_{name}_50_50_1000.png",
            )

            if not args.skip_trunc500:
                print(f"== arrivals trunc500 sensitivity {name}", flush=True)
                run_bellhop(env_tr)
                tr_rows = read_arrivals_asc(env_tr.with_suffix(".arr"))
                pd.DataFrame(tr_rows).to_csv(
                    OUT / "arrivals" / f"{name}_arrivals_trunc500.csv", index=False
                )
                season["focus_trunc500"] = summarise_arrivals(
                    tr_rows, FOCUS["src_m"], FOCUS["rcv_m"], FOCUS["range_m"], band_m=30.0
                )

        summary[name] = season

    if "focus" in summary["january"] and "focus" in summary["july"]:
        plot_fractions(summary, OUT / "figs" / "eigenray_fractions_50_50_1000.png")
        write_readme(summary, OUT / "README.md")
        _write_pairs_csv(summary)

    (OUT / "provenance.json").write_text(json.dumps(summary, indent=2, default=_jsonable) + "\n")
    slim = {
        "bottom_m": summary["bottom_m"],
        "ssp_policy": summary["ssp_policy"],
        "january_focus": summary.get("january", {}).get("focus"),
        "july_focus": summary.get("july", {}).get("focus"),
        "january_tl_focus_db": summary.get("january", {}).get("tl_focus_db"),
        "july_tl_focus_db": summary.get("july", {}).get("tl_focus_db"),
    }
    print(json.dumps(slim, indent=2, default=_jsonable))
    return 0


if __name__ == "__main__":
    sys.exit(main())
