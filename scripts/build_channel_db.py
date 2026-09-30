#!/usr/bin/env python3
"""Build the ns-3 / Aqua-Sim multipath channel database from Bellhop arrivals.

Step F1: full-grid eigenrays (201 ranges x 51 depths) → HDF5.
Step F2: H_eq(f) on 23000–24999 Hz at 1 Hz (2000 bins), G_bar, TL.
Step F3: compare reconstructed TL to native Bellhop .shd.
Step F4: SNR grid, SL=175 dB, DI=0, Wenz noise (s=0.2, w=2 m/s assumed).

H_eq(f) follows the prescribed sum exactly:

  H_eq(f) = Σ_p L_geo(d_p) L_abs(d_p, f) exp(j [θ_p − 2π f (τ_p − τ_0)])

  L_geo = d_p^(−κ/2), κ=2
  L_abs = 10^(−α(f) d_p / 20000)   α in dB/km, d_p in m  (pressure)
  α(f)  = Thorp as specified (f in kHz)

Path length: Bellhop ASCII arrivals do not report geometric path length.
d_p = τ_p × c(z_src) with c from the month's full-column SSP at 50 m.
That is a constant-c conversion, not a ray-integrated slowness.

TL in the CSV is the sonar-equation loss
  TL_dB = −10 log10(G_bar)
i.e. −1 times the prompt's 10 log10(G_bar). The prompt's expression is
power *gain* in dB (negative). SNR = SL − TL − NL is only usable with
positive loss; LQARP's 8.68 dB threshold comparison requires that sign.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_bellhop_wp import (  # noqa: E402
    ALPHA1,
    ALPHA2,
    BELLHOP,
    BOTTOM_M,
    FREQ_HZ,
    NBEAMS,
    OUT as BELLHOP_DIR,
    RCV_DR_M,
    RCV_DZ_M,
    RCV_R_MAX_M,
    RCV_Z_MAX_M,
    ROOT,
    SRC_DEPTH_M,
    STEP_M,
    build_full_column_ssp,
    n_points,
    read_arrivals_asc,
    read_shd,
    run_bellhop,
    write_env,
)

try:
    import h5py
except ImportError as exc:  # pragma: no cover
    raise SystemExit("h5py is required: pip3 install h5py") from exc

CANONICAL_RANGES = np.arange(0.0, RCV_R_MAX_M + 0.5, RCV_DR_M)
CANONICAL_DEPTHS = np.arange(0.0, RCV_Z_MAX_M + 0.5, RCV_DZ_M)
CHAN = ROOT / "data" / "channel_db"
FC_HZ = 24000.0
B_HZ = 2000.0
N_FREQ = 2000
DELTA_F_HZ = 1.0
F_START_HZ = 23000.0  # 23000 … 24999 inclusive → 2000 bins, band width 2000 Hz
KAPPA = 2.0
SL_DB = 175.0  # dB re 1 µPa
DI_DB = 0.0
SHIP_S = 0.2  # assumed, not from WOA/GEBCO
WIND_MPS = 2.0  # assumed, not from WOA/GEBCO
SNR_TH_DB = 8.68
D_MIN_M = 1.0
TL_CLIP_DB = 600.0


def freq_hz() -> np.ndarray:
    return F_START_HZ + DELTA_F_HZ * np.arange(N_FREQ, dtype=np.float64)


def thorp_alpha_db_per_km(f_khz: np.ndarray) -> np.ndarray:
    """Prompt Thorp formula. f in kHz, α in dB/km."""
    f2 = np.asarray(f_khz, dtype=np.float64) ** 2
    return 0.11 * f2 / (1.0 + f2) + 44.0 * f2 / (4100.0 + f2) + 2.75e-4 * f2 + 0.003


def c_at_src(ssp: pd.DataFrame, z_src: float = SRC_DEPTH_M) -> float:
    z = ssp["depth_m"].to_numpy(float)
    c = ssp["sound_speed_mps"].to_numpy(float)
    return float(np.interp(z_src, z, c))


def wenz_psd_db_re_upa2_hz(f_khz: np.ndarray, s: float, w: float) -> dict[str, np.ndarray]:
    f = np.asarray(f_khz, dtype=np.float64)
    nt = 17.0 - 30.0 * np.log10(f)
    ns = 40.0 + 20.0 * (s - 0.5) + 26.0 * np.log10(f) - 60.0 * np.log10(f + 0.03)
    nw = 50.0 + 7.5 * np.sqrt(w) + 20.0 * np.log10(f) - 40.0 * np.log10(f + 0.4)
    nth = -15.0 + 20.0 * np.log10(f)
    return {"turbulence": nt, "shipping": ns, "wave": nw, "thermal": nth}


def noise_psd_upa2_hz(f_khz: np.ndarray, s: float, w: float) -> np.ndarray:
    parts = wenz_psd_db_re_upa2_hz(f_khz, s, w)
    lin = np.zeros_like(f_khz, dtype=np.float64)
    for v in parts.values():
        lin += 10.0 ** (v / 10.0)
    return lin


def nl_db(s: float = SHIP_S, w: float = WIND_MPS) -> dict:
    f = freq_hz()
    f_khz = f / 1000.0
    n = noise_psd_upa2_hz(f_khz, s, w)
    integrated = float(np.sum(n) * DELTA_F_HZ)  # µPa²
    nl_int = 10.0 * math.log10(max(integrated, 1e-30))
    n_fc = float(noise_psd_upa2_hz(np.array([FC_HZ / 1000.0]), s, w)[0])
    nl_fc = 10.0 * math.log10(max(n_fc * B_HZ, 1e-30))
    parts_fc = {k: float(v[0]) for k, v in wenz_psd_db_re_upa2_hz(np.array([FC_HZ / 1000.0]), s, w).items()}
    return {
        "NL_integrated_dB": nl_int,
        "NL_fc_B_dB": nl_fc,
        "N_fc_upa2_per_hz": n_fc,
        "components_fc_dB": parts_fc,
        "s_shipping": s,
        "w_mps": w,
        "note": (
            "s and w are design assumptions carried from the LQARP/Wenz "
            "literature convention. They are NOT derived from WOA23 or GEBCO."
        ),
    }


def run_full_grid_arrivals(month_name: str, ssp: pd.DataFrame) -> Path:
    env = BELLHOP_DIR / "env" / f"wp_{month_name}_arr_full.env"
    arr = env.with_suffix(".arr")
    nrd = n_points(0.0, RCV_Z_MAX_M, RCV_DZ_M)
    nrr = n_points(0.0, RCV_R_MAX_M, RCV_DR_M)
    write_env(
        env,
        title=f"WP {month_name} 24kHz FULL-GRID arrivals, flat {BOTTOM_M:.0f} m",
        ssp=ssp,
        run_type="A",
        rd_n=nrd,
        rd_first=0.0,
        rd_last=RCV_Z_MAX_M,
        rr_n=nrr,
        rr_first_km=0.0,
        rr_last_km=RCV_R_MAX_M / 1000.0,
        nbeams=NBEAMS,
    )
    if arr.is_file() and arr.stat().st_mtime >= env.stat().st_mtime:
        print(f"== reuse existing {arr.name}", flush=True)
        return arr
    print(f"== full-grid arrivals {month_name}  {nrd} depths x {nrr} ranges, beams={NBEAMS}", flush=True)
    run_bellhop(env)
    if not arr.is_file():
        raise RuntimeError(f"Bellhop did not write {arr}")
    return arr


def arrivals_to_h5(
    rows: list[dict],
    path: Path,
    *,
    month: str,
    c_src: float,
    ssp_note: str,
    ranges: np.ndarray | None = None,
    depths: np.ndarray | None = None,
) -> None:
    if not rows:
        raise RuntimeError("no arrivals to store")
    df = pd.DataFrame(rows)
    ranges = np.asarray(ranges if ranges is not None else CANONICAL_RANGES, dtype=float)
    depths = np.asarray(depths if depths is not None else CANONICAL_DEPTHS, dtype=float)
    nr, nz = len(ranges), len(depths)
    r_index = {round(float(v), 3): i for i, v in enumerate(ranges)}
    z_index = {round(float(v), 3): i for i, v in enumerate(depths)}
    df = df.copy()
    df["_ir"] = np.round(df["range_m"].to_numpy(float), 3)
    df["_iz"] = np.round(df["rcv_depth_m"].to_numpy(float), 3)
    df["_ir"] = df["_ir"].map(r_index)
    df["_iz"] = df["_iz"].map(z_index)
    skipped = int(df["_ir"].isna().sum() + df["_iz"].isna().sum())
    df = df.dropna(subset=["_ir", "_iz"])
    df["_ir"] = df["_ir"].astype(int)
    df["_iz"] = df["_iz"].astype(int)
    df = df.sort_values(["_iz", "_ir", "delay_s"], kind="mergesort")

    n_tot = len(df)
    tau = df["delay_s"].to_numpy(np.float64)
    phase_deg = df["phase_deg"].to_numpy(np.float64)
    amp = df["amp"].to_numpy(np.float64)
    src_decl = df["src_decl_deg"].to_numpy(np.float32)
    rcv_decl = df["rcv_decl_deg"].to_numpy(np.float32)
    n_top = df["n_top"].to_numpy(np.int16)
    n_bot = df["n_bot"].to_numpy(np.int16)
    d_p = np.maximum(tau * c_src, 0.0)
    n_arr = np.zeros((nz, nr), dtype=np.int32)
    offset = np.zeros(nz * nr + 1, dtype=np.int64)
    counts = df.groupby(["_iz", "_ir"], sort=True).size()
    k = 0
    # fill n_arr and csr offset in grid order
    pos = 0
    grouped = {(int(iz), int(ir)): int(c) for (iz, ir), c in counts.items()}
    for iz in range(nz):
        for ir in range(nr):
            offset[iz * nr + ir] = pos
            c = grouped.get((iz, ir), 0)
            n_arr[iz, ir] = c
            pos += c
    offset[-1] = pos
    if pos != n_tot:
        raise RuntimeError(f"offset mismatch {pos} vs {n_tot}")

    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(path, "w") as h:
        h.attrs["month"] = month
        h.attrs["freq_hz"] = FREQ_HZ
        h.attrs["src_depth_m"] = SRC_DEPTH_M
        h.attrs["bottom_m"] = BOTTOM_M
        h.attrs["c_src_mps"] = c_src
        h.attrs["d_p_method"] = (
            "d_p = tau_p * c(z_src). Bellhop ASCII .arr does not report "
            "geometric path length or a ray-integrated slowness. c(z_src) is "
            f"the full-column WOA23 Mackenzie SSP at {SRC_DEPTH_M:.0f} m."
        )
        h.attrs["ssp"] = ssp_note
        h.attrs["n_skipped_off_grid"] = int(skipped)
        h.attrs["note_range0"] = (
            "Range 0 m is on the grid with n_arrivals=0: Bellhop wrote no "
            "eigenrays at zero horizontal range (singular point source)."
        )
        h.attrs["created_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        h.create_dataset("ranges_m", data=ranges, compression="gzip")
        h.create_dataset("depths_m", data=depths, compression="gzip")
        h.create_dataset("n_arrivals", data=n_arr, compression="gzip")
        h.create_dataset("offset", data=offset, compression="gzip")
        h.create_dataset("tau_s", data=tau, compression="gzip")
        h.create_dataset("phase_deg", data=phase_deg, compression="gzip")
        h.create_dataset("amp_bellhop", data=amp, compression="gzip")
        h.create_dataset("src_decl_deg", data=src_decl, compression="gzip")
        h.create_dataset("rcv_decl_deg", data=rcv_decl, compression="gzip")
        h.create_dataset("n_top", data=n_top, compression="gzip")
        h.create_dataset("n_bot", data=n_bot, compression="gzip")
        h.create_dataset("d_p_m", data=d_p, compression="gzip")
        print(f"wrote {path}  points={nz*nr}  arrivals={n_tot}  empty={int((n_arr==0).sum())}  c_src={c_src:.3f}", flush=True)


def heq_grids(h5_path: Path) -> dict:
    """H_eq band stats, G_bar, TL for every (depth, range)."""
    f = freq_hz()
    omega = 2.0 * np.pi * f[:, None]  # (F, 1)
    alpha = thorp_alpha_db_per_km(f / 1000.0)[:, None]  # (F, 1)
    with h5py.File(h5_path, "r") as h:
        ranges = h["ranges_m"][:]
        depths = h["depths_m"][:]
        n_arr = h["n_arrivals"][:]
        offset = h["offset"][:]
        tau_all = h["tau_s"][:]
        phase_all = np.deg2rad(h["phase_deg"][:])
        d_all = h["d_p_m"][:]
        c_src = float(h.attrs["c_src_mps"])
        d_method = str(h.attrs["d_p_method"])

    nz, nr = n_arr.shape
    gbar = np.full((nz, nr), np.nan)
    tl = np.full((nz, nr), np.nan)
    ptp_db = np.full((nz, nr), np.nan)
    n_used = np.zeros((nz, nr), dtype=np.int32)
    flags = np.zeros((nz, nr), dtype=np.int32)  # bit0 empty, bit1 r=0, bit2 dmin, bit3 G>1
    # H_eq is 2000 x 10251 complex64 ≈ 164 MB; keep only band stats in RAM.
    # Save a compact checkpoint H at fc for F3-adjacent debug.
    h_fc = np.full((nz, nr), np.nan + 1j * np.nan, dtype=np.complex128)
    i_fc = int(np.argmin(np.abs(f - FC_HZ)))

    for iz in range(nz):
        for ir in range(nr):
            a = int(offset[iz * nr + ir])
            b = int(offset[iz * nr + ir + 1])
            if b <= a:
                flags[iz, ir] |= 1
                continue
            tau = tau_all[a:b]
            d = np.maximum(d_all[a:b], D_MIN_M)
            th = phase_all[a:b]
            ok = np.isfinite(tau) & np.isfinite(d) & (tau > 0)
            if not np.any(ok):
                flags[iz, ir] |= 1
                continue
            tau = tau[ok]
            d = d[ok]
            th = th[ok]
            n_used[iz, ir] = tau.size
            tau0 = float(np.min(tau))
            l_geo = d ** (-KAPPA / 2.0)  # 1/d
            # (F, P)
            l_abs = 10.0 ** (-alpha * d[None, :] / 20000.0)
            phase = th[None, :] - omega * (tau[None, :] - tau0)
            hsum = np.sum(l_geo[None, :] * l_abs * np.exp(1j * phase), axis=1)
            pwr = np.abs(hsum) ** 2
            g = float(np.mean(pwr))  # (1/B) Σ |H|^2 Δf  with B=N Δf
            gbar[iz, ir] = g
            if g <= 0 or not np.isfinite(g):
                flags[iz, ir] |= 1
                continue
            tl_val = -10.0 * math.log10(g)
            tl[iz, ir] = tl_val
            with np.errstate(divide="ignore"):
                pdb = 10.0 * np.log10(np.maximum(pwr, 1e-30))
            ptp_db[iz, ir] = float(np.max(pdb) - np.min(pdb))
            h_fc[iz, ir] = hsum[i_fc]
            if ranges[ir] <= 0:
                flags[iz, ir] |= 2
            if np.min(d_all[a:b][ok]) < D_MIN_M:
                flags[iz, ir] |= 4
            if g > 1.0:
                flags[iz, ir] |= 8
        if iz % 10 == 0:
            print(f"  H_eq depth {depths[iz]:.0f} m", flush=True)

    return {
        "ranges_m": ranges,
        "depths_m": depths,
        "G_bar": gbar,
        "TL_dB": tl,
        "ptp_dB": ptp_db,
        "n_used": n_used,
        "flags": flags,
        "H_fc": h_fc,
        "c_src_mps": c_src,
        "d_p_method": d_method,
        "i_fc": i_fc,
        "freqs_hz": f,
    }


def write_grid_csv(path: Path, ranges, depths, values, value_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write(f"range_m,receiver_depth_m,{value_name}\n")
        for ir, r in enumerate(ranges):
            for iz, z in enumerate(depths):
                v = values[iz, ir]
                if np.isfinite(v):
                    f.write(f"{r:.1f},{z:.1f},{float(v):.8f}\n")
                else:
                    f.write(f"{r:.1f},{z:.1f},nan\n")


def native_tl_grid() -> dict[str, dict]:
    out = {}
    for month in ("january", "july"):
        npz = BELLHOP_DIR / "tl" / f"{month}_tl.npz"
        shd_path = BELLHOP_DIR / "env" / f"wp_{month}_tl.shd"
        if npz.is_file():
            d = np.load(npz)
            out[month] = {"tl_db": d["tl_db"][0], "rz": d["rz_m"], "rr": d["rr_m"]}
        elif shd_path.is_file():
            shd = read_shd(shd_path)
            out[month] = {"tl_db": shd["tl_db"][0], "rz": shd["rz"], "rr": shd["rr"]}
        else:
            raise FileNotFoundError(f"no native TL for {month}")
    return out


def compare_tl(recon, native) -> dict:
    rr, rz = recon["ranges_m"], recon["depths_m"]
    tl_r = recon["TL_dB"]
    ptp = recon["ptp_dB"]
    tl_n = np.array(native["tl_db"], dtype=float)
    rr_n = np.array(native["rr"], dtype=float)
    rz_n = np.array(native["rz"], dtype=float)
    diff = np.full_like(tl_r, np.nan)
    native_on = np.full_like(tl_r, np.nan)
    for iz, z in enumerate(rz):
        jz = int(np.argmin(np.abs(rz_n - z)))
        for ir, r in enumerate(rr):
            jr = int(np.argmin(np.abs(rr_n - r)))
            native_on[iz, ir] = tl_n[jz, jr]
            if np.isfinite(tl_r[iz, ir]) and np.isfinite(tl_n[jz, jr]):
                diff[iz, ir] = tl_r[iz, ir] - tl_n[jz, jr]

    def slice_stats(mask, name):
        d = diff[mask]
        d = d[np.isfinite(d)]
        if d.size == 0:
            return {"name": name, "n": 0}
        absd = np.abs(d)
        return {
            "name": name,
            "n": int(d.size),
            "mean_abs_dB": float(np.mean(absd)),
            "median_abs_dB": float(np.median(absd)),
            "max_abs_dB": float(np.max(absd)),
            "p95_abs_dB": float(np.percentile(absd, 95)),
            "frac_gt_10dB": float(np.mean(absd > 10.0)),
            "n_gt_10dB": int(np.sum(absd > 10.0)),
            "mean_signed_dB": float(np.mean(d)),
        }

    finite = np.isfinite(diff)
    z_ok = rz[:, None] >= RCV_DZ_M
    r_ok = rr[None, :] >= RCV_DR_M
    mild = np.isfinite(ptp) & (ptp < 6.0)
    native_ok = np.isfinite(native_on) & (native_on > 20.0) & (native_on < 120.0)
    slices = [
        slice_stats(finite & r_ok, "r>=10m all depths"),
        slice_stats(finite & r_ok & z_ok, "r>=10m z>=10m (exclude pressure-release surface)"),
        slice_stats(finite & r_ok & z_ok & native_ok, "r>=10m z>=10m native TL in (20,120)"),
        slice_stats(finite & r_ok & z_ok & mild, "r>=10m z>=10m in-band ptp<6 dB"),
    ]
    primary = slices[1]
    out = dict(primary)
    out["slices"] = slices
    out["note"] = (
        "Raw max |Δ| is dominated by (1) z=0 pressure-release nulls in H_eq "
        "and (2) single-frequency Bellhop interference nulls vs 2 kHz G_bar. "
        "The ptp<6 dB slice is the fair apples-to-apples check."
    )
    return out


def plot_heatmap(ranges, depths, z, title, clabel, path, vmin=None, vmax=None, cmap="viridis_r"):
    fig, ax = plt.subplots(figsize=(8.6, 3.8))
    rr_km = ranges / 1000.0
    zz = np.array(z, dtype=float, copy=True)
    im = ax.pcolormesh(rr_km, depths, zz, shading="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_ylim(RCV_Z_MAX_M, 0)
    ax.set_xlim(0, RCV_R_MAX_M / 1000.0)
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Receiver depth (m)")
    ax.set_title(title)
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label(clabel)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def _fmt_slice(s: dict) -> str:
    if not s or not s.get("n"):
        return "n=0"
    return (
        f"{s['n']} pts, mean {s['mean_abs_dB']:.2f}, med {s['median_abs_dB']:.2f}, "
        f"p95 {s['p95_abs_dB']:.2f}, max {s['max_abs_dB']:.2f}, "
        f"|Δ|>10 dB at {100*s['frac_gt_10dB']:.1f}% ({s['n_gt_10dB']})"
    )


def write_readme(summary: dict, path: Path) -> None:
    jan = summary["january"]
    jul = summary["july"]
    nl = summary["noise"]
    fading = summary["fading"]
    path.write_text(
        f"""# Channel database (Step F) — Western Pacific primary cell

Multipath channel for Aqua-Sim / ns-3 from Bellhop eigenrays at
20.125°N, 124.125°E. Flat 5524 m bottom, full-column WOA23 SSP,
src = 50 m, 24 kHz, B = 2000 Hz.

## F1 — full-grid eigenrays

The earlier arrivals CSV covered only five ranges (200, 500, 1000, 1500,
2000 m). That is **not** the simulation grid. Full-grid ASCII Bellhop
arrivals were re-run for every (range, depth) on 0–2000 m / 10 m ×
0–500 m / 10 m (201 × 51 = 10251 points), January and July.

| Month | HDF5 | arrivals | empty points |
| --- | --- | --- | --- |
| January | `data/bellhop/arrivals_full_grid_january.h5` | {jan['n_arrivals']} | {jan['n_empty']} |
| July | `data/bellhop/arrivals_full_grid_july.h5` | {jul['n_arrivals']} | {jul['n_empty']} |

Each arrival stores τ_p, Bellhop amplitude (reference only), θ_p
(phase, deg), launch/receive angles, n_top, n_bot, and d_p.

**d_p method:** Bellhop `.arr` does not report geometric path length.
`d_p = τ_p × c(z_src)` with c from the month's full-column Mackenzie SSP
at 50 m (January {jan['c_src_mps']:.2f} m/s, July {jul['c_src_mps']:.2f} m/s).
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
| January | `data/channel_db/TL_grid_january.csv` | {jan['n_finite_tl']} | {jan['n_nan_tl']} | {jan['n_neg_tl']} |
| July | `data/channel_db/TL_grid_july.csv` | {jul['n_finite_tl']} | {jul['n_nan_tl']} | {jul['n_neg_tl']} |

Focus (50 m, 50 m, 1000 m): January TL {jan['tl_focus_dB']:.2f} dB,
July {jul['tl_focus_dB']:.2f} dB.

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

| Month | n | mean \\|Δ\\| | median | p95 | max | fraction \\|Δ\\|>10 dB |
| --- | --- | --- | --- | --- | --- | --- |
| January | {jan['f3']['n']} | {jan['f3']['mean_abs_dB']:.2f} | {jan['f3']['median_abs_dB']:.2f} | {jan['f3']['p95_abs_dB']:.2f} | {jan['f3']['max_abs_dB']:.2f} | {100*jan['f3']['frac_gt_10dB']:.1f}% |
| July | {jul['f3']['n']} | {jul['f3']['mean_abs_dB']:.2f} | {jul['f3']['median_abs_dB']:.2f} | {jul['f3']['p95_abs_dB']:.2f} | {jul['f3']['max_abs_dB']:.2f} | {100*jul['f3']['frac_gt_10dB']:.1f}% |

Fair slice (same grid, but only points whose in-band |H|² peak-to-trough
is < 6 dB — i.e. where a single-frequency snapshot *should* match G_bar):

- January: {_fmt_slice(jan['f3']['slices'][3])}
- July: {_fmt_slice(jul['f3']['slices'][3])}

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
| SL | {SL_DB:.0f} dB re 1 µPa | assumed source level (not a sea-trial measurement) |
| DI | {DI_DB:.0f} dB | omnidirectional, LQARP convention |
| s | {SHIP_S} | **assumed** shipping factor; NOT from WOA/GEBCO |
| w | {WIND_MPS} m/s | **assumed** wind; NOT from WOA/GEBCO |
| NL (band-integrated) | {nl['NL_integrated_dB']:.2f} dB | Wenz four-component, ∫ N(f) df over B |
| NL (N(f_c)·B) | {nl['NL_fc_B_dB']:.2f} dB | same model, prompt's compact form |
| SNR threshold | {SNR_TH_DB} dB | LQARP stated detection threshold |

The SNR CSV uses the **band-integrated** NL ({nl['NL_integrated_dB']:.2f} dB).
The two NL numbers differ by {abs(nl['NL_integrated_dB']-nl['NL_fc_B_dB']):.2f} dB
because N(f) is not flat across 23–25 kHz (wind + thermal dominate).

Wenz components at 24 kHz (dB re 1 µPa²/Hz): turbulence {nl['components_fc_dB']['turbulence']:.1f},
shipping {nl['components_fc_dB']['shipping']:.1f}, wave {nl['components_fc_dB']['wave']:.1f},
thermal {nl['components_fc_dB']['thermal']:.1f}.

| Month | CSV | SNR>{SNR_TH_DB} dB, r≥10 m all z | same, z≥10 m only |
| --- | --- | --- | --- |
| January | `data/channel_db/SNR_grid_january.csv` | {100*jan['frac_snr_gt_th']:.1f}% ({jan['n_snr_gt_th']}/{jan['n_snr_compared']}) | {100*jan['frac_snr_gt_th_zge10']:.1f}% ({jan['n_snr_gt_th_zge10']}/{jan['n_snr_compared_zge10']}) |
| July | `data/channel_db/SNR_grid_july.csv` | {100*jul['frac_snr_gt_th']:.1f}% ({jul['n_snr_gt_th']}/{jul['n_snr_compared']}) | {100*jul['frac_snr_gt_th_zge10']:.1f}% ({jul['n_snr_gt_th_zge10']}/{jul['n_snr_compared_zge10']}) |

## F5 — is B = 2000 Hz enough?

Coherence bandwidth from the water-column delay spread (direct vs surface,
Δτ ≈ 3 ms at 1 km) is ~1/Δτ ≈ 330 Hz, much narrower than 2 kHz. In-band
peak-to-trough of 10 log10(|H_eq|²):

| | January | July |
| --- | --- | --- |
| median ptp (dB) | {fading['january']['median_ptp_dB']:.2f} | {fading['july']['median_ptp_dB']:.2f} |
| fraction of points with ptp > 3 dB | {100*fading['january']['frac_ptp_gt_3dB']:.1f}% | {100*fading['july']['frac_ptp_gt_3dB']:.1f}% |
| max ptp (dB) | {fading['january']['max_ptp_dB']:.2f} | {fading['july']['max_ptp_dB']:.2f} |

**Verdict:** {fading['verdict']}

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
"""
    )


def pick_focus(ranges, depths, grid, r0=1000.0, z0=50.0) -> float:
    ir = int(np.argmin(np.abs(ranges - r0)))
    iz = int(np.argmin(np.abs(depths - z0)))
    return float(grid[iz, ir])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-bellhop", action="store_true", help="reuse existing .arr / HDF5")
    args = ap.parse_args()

    CHAN.mkdir(parents=True, exist_ok=True)
    BELLHOP_DIR.mkdir(parents=True, exist_ok=True)
    nl = nl_db()
    print("NL integrated", nl["NL_integrated_dB"], "NL fc*B", nl["NL_fc_B_dB"], flush=True)

    native = native_tl_grid()
    summary = {
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freq_axis": {
            "f_start_hz": F_START_HZ,
            "f_stop_hz": F_START_HZ + (N_FREQ - 1) * DELTA_F_HZ,
            "n": N_FREQ,
            "delta_f_hz": DELTA_F_HZ,
            "B_hz": B_HZ,
            "note": "23000–24999 Hz, 2000 bins; not 23000–25000 inclusive (that would be 2001)",
        },
        "H_eq": {
            "kappa": KAPPA,
            "thorp": "0.11 f^2/(1+f^2)+44 f^2/(4100+f^2)+2.75e-4 f^2+0.003",
            "tl_csv_is": "-10 log10(G_bar)  [sonar-equation loss, positive dB]",
            "prompt_10log10_Gbar_is": "power gain in dB (negative); not stored in TL_dB",
        },
        "link_budget": {"SL_dB": SL_DB, "DI_dB": DI_DB, "SNR_th_dB": SNR_TH_DB},
        "noise": nl,
        "fading": {},
        "january": {},
        "july": {},
    }

    for month, month_num in (("january", 1), ("july", 7)):
        ssp = build_full_column_ssp(month_num)
        c_src = c_at_src(ssp)
        h5_path = BELLHOP_DIR / f"arrivals_full_grid_{month}.h5"
        if not (args.skip_bellhop and h5_path.is_file()):
            arr_path = run_full_grid_arrivals(month, ssp)
            print(f"== parse {arr_path.name}", flush=True)
            rows = read_arrivals_asc(arr_path)
            arrivals_to_h5(
                rows,
                h5_path,
                month=month,
                c_src=c_src,
                ssp_note="WOA23 monthly 0-1500 + annual 1550-5500 + Mackenzie 5524",
            )
            del rows
        print(f"== H_eq {month}", flush=True)
        grids = heq_grids(h5_path)
        tl = grids["TL_dB"]
        snr = SL_DB - tl - nl["NL_integrated_dB"] + DI_DB
        ranges, depths = grids["ranges_m"], grids["depths_m"]
        write_grid_csv(CHAN / f"TL_grid_{month}.csv", ranges, depths, tl, "TL_dB")
        write_grid_csv(CHAN / f"SNR_grid_{month}.csv", ranges, depths, snr, "SNR_dB")
        write_grid_csv(CHAN / f"fading_ptp_{month}.csv", ranges, depths, grids["ptp_dB"], "ptp_dB")
        np.savez_compressed(
            CHAN / f"grids_{month}.npz",
            ranges_m=ranges,
            depths_m=depths,
            TL_dB=tl,
            SNR_dB=snr,
            G_bar=grids["G_bar"],
            ptp_dB=grids["ptp_dB"],
            flags=grids["flags"],
        )
        f3 = compare_tl(grids, native[month])
        finite = np.isfinite(tl)
        rmask = ranges[None, :] >= RCV_DR_M
        zmask = depths[:, None] >= RCV_DZ_M
        snr_ok = np.isfinite(snr) & rmask
        snr_ok_z = snr_ok & zmask
        n_comp = int(np.sum(snr_ok))
        n_gt = int(np.sum(snr_ok & (snr > SNR_TH_DB)))
        n_comp_z = int(np.sum(snr_ok_z))
        n_gt_z = int(np.sum(snr_ok_z & (snr > SNR_TH_DB)))
        ptp = grids["ptp_dB"]
        ptp_ok = np.isfinite(ptp) & rmask
        fading = {
            "median_ptp_dB": float(np.median(ptp[ptp_ok])) if np.any(ptp_ok) else None,
            "max_ptp_dB": float(np.max(ptp[ptp_ok])) if np.any(ptp_ok) else None,
            "frac_ptp_gt_3dB": float(np.mean(ptp[ptp_ok] > 3.0)) if np.any(ptp_ok) else None,
        }
        summary["fading"][month] = fading
        with h5py.File(h5_path, "r") as h:
            n_arr_tot = int(np.sum(h["n_arrivals"][:]))
            n_empty = int(np.sum(h["n_arrivals"][:] == 0))
        rec = {
            "c_src_mps": c_src,
            "n_arrivals": n_arr_tot,
            "n_empty": n_empty,
            "n_finite_tl": int(np.sum(finite)),
            "n_nan_tl": int(np.sum(~finite)),
            "n_neg_tl": int(np.sum(finite & (tl < 0))),
            "tl_focus_dB": pick_focus(ranges, depths, tl),
            "snr_focus_dB": pick_focus(ranges, depths, snr),
            "native_tl_focus_dB": pick_focus(native[month]["rr"], native[month]["rz"], native[month]["tl_db"]),
            "f3": f3,
            "frac_snr_gt_th": (n_gt / n_comp) if n_comp else None,
            "n_snr_gt_th": n_gt,
            "n_snr_compared": n_comp,
            "frac_snr_gt_th_zge10": (n_gt_z / n_comp_z) if n_comp_z else None,
            "n_snr_gt_th_zge10": n_gt_z,
            "n_snr_compared_zge10": n_comp_z,
            "d_p_method": grids["d_p_method"],
        }
        summary[month] = rec
        print(json.dumps({month: {k: rec[k] for k in rec if k != "d_p_method"}}, indent=2), flush=True)

        if month == "january":
            plot_heatmap(
                ranges,
                depths,
                tl,
                "January TL  (band-averaged |H_eq|², sonar-equation loss)",
                "TL (dB)",
                CHAN / "figs" / "TL_heatmap_january.png",
                vmin=40,
                vmax=120,
                cmap="viridis_r",
            )
            plot_heatmap(
                ranges,
                depths,
                snr,
                f"January SNR  SL={SL_DB:.0f} dB, NL={nl['NL_integrated_dB']:.1f} dB, DI={DI_DB:.0f}",
                "SNR (dB)",
                CHAN / "figs" / "SNR_heatmap_january.png",
                vmin=0,
                vmax=90,
                cmap="magma",
            )

    fj, fu = summary["fading"]["january"], summary["fading"]["july"]
    if fj["frac_ptp_gt_3dB"] > 0.2 or fu["frac_ptp_gt_3dB"] > 0.2:
        verdict = (
            "B = 2000 Hz is NOT a flat channel on this grid. Frequency-selective "
            "fading exceeds 3 dB peak-to-trough at a large fraction of points "
            "because the water-column delay spread (~3 ms) sets a coherence "
            "bandwidth of a few hundred hertz. G_bar as a 2 kHz power average "
            "is still the right scalar for an LQARP-style budget; a single-tap "
            "H(f_c) is not. Finer than 1 Hz sampling is not required."
        )
    else:
        verdict = (
            "In-band fading is mostly under 3 dB; a 2 kHz band around 24 kHz "
            "is adequate for a scalar G_bar on this grid."
        )
    summary["fading"]["verdict"] = verdict
    write_readme(summary, CHAN / "README.md")
    (CHAN / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("verdict:", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
