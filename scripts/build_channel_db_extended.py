#!/usr/bin/env python3
"""Step G: extend the Aqua-Sim channel DB from 2 km to 6 km.

Same site, SSP, bottom, source, frequency, beams, Thorp, SL/NL/threshold
as Step F. Only the range grid changes:

  ranges  0–6000 m / 25 m   → 241 points (0 and 6000 inclusive;
          240 intervals of 25 m, the analog of 201 points on 0–2000/10)
  depths  0–500 m / 10 m    → 51 points, unchanged

RBOX is 6.15 km so rays are not killed at the old 2.1 km box.
NBEAMS stays 9601 over ±89°, same as Step F.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_channel_db import (  # noqa: E402
    BELLHOP_DIR,
    CHAN,
    DI_DB,
    KAPPA,
    NBEAMS,
    SL_DB,
    SNR_TH_DB,
    arrivals_to_h5,
    c_at_src,
    heq_grids,
    nl_db,
    write_grid_csv,
)
from run_bellhop_wp import (  # noqa: E402
    BOTTOM_M,
    RCV_DZ_M,
    RCV_Z_MAX_M,
    SRC_DEPTH_M,
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

# Inclusive 0, 25, …, 6000 m. 6000/25 = 240 intervals → 241 samples.
EXT_R_MAX_M = 6000.0
EXT_DR_M = 25.0
EXT_RANGES = np.arange(0.0, EXT_R_MAX_M + 0.5, EXT_DR_M)
EXT_DEPTHS = np.arange(0.0, RCV_Z_MAX_M + 0.5, RCV_DZ_M)
EXT_RBOX_KM = 6.15
# Exact Step-F band-integrated Wenz NL (s=0.2, w=2 m/s, 23000–24999 Hz).
NL_DB_REUSED = 65.77497291279225
CROSS_DEPTHS_M = (50.0, 10.0, 250.0, 500.0)
SPOT_RANGES_M = (4000.0, 6000.0)
SPOT_DEPTH_M = 50.0
RANGE_BANDS = (
    (0.0, 1000.0),
    (1000.0, 2000.0),
    (2000.0, 3000.0),
    (3000.0, 4000.0),
    (4000.0, 5000.0),
    (5000.0, 6000.0),
)


def run_extended_bellhop(month_name: str, ssp, *, skip: bool) -> tuple[Path, Path]:
    nrd = n_points(0.0, RCV_Z_MAX_M, RCV_DZ_M)
    nrr = n_points(0.0, EXT_R_MAX_M, EXT_DR_M)
    env_arr = BELLHOP_DIR / "env" / f"wp_{month_name}_arr_extended.env"
    env_tl = BELLHOP_DIR / "env" / f"wp_{month_name}_tl_extended.env"
    common = dict(
        ssp=ssp,
        rd_n=nrd,
        rd_first=0.0,
        rd_last=RCV_Z_MAX_M,
        rr_n=nrr,
        rr_first_km=0.0,
        rr_last_km=EXT_R_MAX_M / 1000.0,
        nbeams=NBEAMS,
        rbox_km=EXT_RBOX_KM,
    )
    write_env(
        env_arr,
        title=f"WP {month_name} 24kHz EXTENDED arrivals 0-6 km, flat {BOTTOM_M:.0f} m",
        run_type="A",
        **common,
    )
    write_env(
        env_tl,
        title=f"WP {month_name} 24kHz EXTENDED coherent TL 0-6 km, flat {BOTTOM_M:.0f} m",
        run_type="CB",
        **common,
    )
    arr = env_arr.with_suffix(".arr")
    shd = env_tl.with_suffix(".shd")
    force = not skip
    if arr.is_file() and arr.stat().st_size > 10000 and not force:
        print(f"== reuse {arr.name} ({arr.stat().st_size} bytes)", flush=True)
    else:
        print(
            f"== extended arrivals {month_name}  {nrd} depths x {nrr} ranges, "
            f"beams={NBEAMS}, RBOX={EXT_RBOX_KM} km",
            flush=True,
        )
        run_bellhop(env_arr)
    if not arr.is_file():
        raise RuntimeError(f"Bellhop did not write {arr}")
    if shd.is_file() and shd.stat().st_size > 10000 and not force:
        print(f"== reuse {shd.name} ({shd.stat().st_size} bytes)", flush=True)
    else:
        print(f"== extended TL {month_name}  {nrd}x{nrr} CB", flush=True)
        run_bellhop(env_tl)
    if not shd.is_file():
        raise RuntimeError(f"Bellhop did not write {shd}")
    return arr, shd


def pick(ranges, depths, grid, r0, z0):
    ir = int(np.argmin(np.abs(ranges - r0)))
    iz = int(np.argmin(np.abs(depths - z0)))
    return ir, iz, float(ranges[ir]), float(depths[iz]), grid[iz, ir]


def crossing_along_depth(ranges, snr_row, th: float) -> dict:
    """First range where band-averaged SNR drops below th, along one depth."""
    mask = (ranges >= EXT_DR_M) & np.isfinite(snr_row)
    rr = ranges[mask]
    ss = snr_row[mask]
    if rr.size == 0:
        return {"crossed": False, "note": "no finite SNR along this depth"}
    below = ss < th
    n_below = int(np.sum(below))
    out = {
        "n_ranges": int(rr.size),
        "n_below_th": n_below,
        "frac_below_th": float(n_below / rr.size),
        "snr_min_dB": float(np.min(ss)),
        "range_at_snr_min_m": float(rr[int(np.argmin(ss))]),
        "snr_at_6km_dB": float(ss[int(np.argmin(np.abs(rr - EXT_R_MAX_M)))]),
        "snr_at_1km_dB": float(ss[int(np.argmin(np.abs(rr - 1000.0)))]),
        "snr_at_2km_dB": float(ss[int(np.argmin(np.abs(rr - 2000.0)))]),
        "snr_at_4km_dB": float(ss[int(np.argmin(np.abs(rr - 4000.0)))]),
        "crossed": bool(np.any(below)),
    }
    if not out["crossed"]:
        out["first_below_m"] = None
        out["snr_at_first_below_dB"] = None
        out["stays_below_at_6km"] = False
        out["note"] = (
            f"SNR does not fall below {th:.2f} dB anywhere on 25–{EXT_R_MAX_M:.0f} m. "
            f"SNR at 6 km is {out['snr_at_6km_dB']:.2f} dB "
            f"(margin {out['snr_at_6km_dB'] - th:.2f} dB)."
        )
        return out
    i0 = int(np.argmax(below))  # first True
    out["first_below_m"] = float(rr[i0])
    out["snr_at_first_below_dB"] = float(ss[i0])
    out["stays_below_at_6km"] = bool(ss[-1] < th)
    # contiguous intervals below threshold
    intervals = []
    in_run = False
    start = None
    for i, flag in enumerate(below):
        if flag and not in_run:
            in_run = True
            start = float(rr[i])
        elif not flag and in_run:
            intervals.append([start, float(rr[i - 1])])
            in_run = False
    if in_run:
        intervals.append([start, float(rr[-1])])
    out["below_intervals_m"] = intervals
    out["n_intervals"] = len(intervals)
    verb = "and remains below at 6 km" if out["stays_below_at_6km"] else (
        "but recovers above threshold by 6 km"
        if ss[-1] >= th
        else ""
    )
    out["note"] = (
        f"SNR first drops below {th:.2f} dB at {out['first_below_m']:.0f} m "
        f"(SNR {out['snr_at_first_below_dB']:.2f} dB) {verb}. "
        f"{n_below}/{rr.size} ranges along this depth are below threshold."
    )
    return out


def band_fractions(ranges, depths, snr, zmin: float) -> list[dict]:
    zmask = depths[:, None] >= zmin
    rows = []
    for lo, hi in RANGE_BANDS:
        # left-closed, right-closed on the last band so 6000 m is included;
        # interior edges: r in (lo, hi] except the first band (0, 1000].
        if lo <= 0:
            rmask = (ranges[None, :] > 0) & (ranges[None, :] <= hi)
        else:
            rmask = (ranges[None, :] > lo) & (ranges[None, :] <= hi)
        sel = zmask & rmask
        vals = snr[sel]
        vals = vals[np.isfinite(vals)]
        n = int(vals.size)
        n_gt = int(np.sum(vals > SNR_TH_DB)) if n else 0
        rows.append(
            {
                "band": f"{lo:.0f}-{hi:.0f}m",
                "lo_m": lo,
                "hi_m": hi,
                "n": n,
                "n_gt_th": n_gt,
                "frac_gt_th": (n_gt / n) if n else None,
                "snr_median_dB": float(np.median(vals)) if n else None,
                "snr_min_dB": float(np.min(vals)) if n else None,
                "snr_max_dB": float(np.max(vals)) if n else None,
            }
        )
    return rows


def spot_f3(recon, native, r0: float, z0: float) -> dict:
    ir, iz, r, z, tl_r = pick(recon["ranges_m"], recon["depths_m"], recon["TL_dB"], r0, z0)
    jr = int(np.argmin(np.abs(native["rr"] - r0)))
    jz = int(np.argmin(np.abs(native["rz"] - z0)))
    tl_n = float(native["tl_db"][jz, jr])
    ptp = float(recon["ptp_dB"][iz, ir])
    return {
        "requested_range_m": r0,
        "requested_depth_m": z0,
        "used_range_m": r,
        "used_depth_m": z,
        "native_range_m": float(native["rr"][jr]),
        "native_depth_m": float(native["rz"][jz]),
        "recon_TL_dB": float(tl_r) if np.isfinite(tl_r) else None,
        "native_TL_dB": tl_n if np.isfinite(tl_n) else None,
        "abs_delta_dB": (
            float(abs(tl_r - tl_n)) if np.isfinite(tl_r) and np.isfinite(tl_n) else None
        ),
        "ptp_dB": ptp if np.isfinite(ptp) else None,
        "n_arrivals": int(recon["n_used"][iz, ir]),
        "fair_slice_ptp_lt_6dB": bool(np.isfinite(ptp) and ptp < 6.0),
    }


def plot_snr_threshold(ranges, depths, snr, path: Path) -> bool:
    fig, ax = plt.subplots(figsize=(10.6, 3.9))
    rr_km = ranges / 1000.0
    zz = np.array(snr, dtype=float, copy=True)
    im = ax.pcolormesh(rr_km, depths, zz, shading="auto", cmap="magma", vmin=0, vmax=90)
    R, Z = np.meshgrid(rr_km, depths)
    drew = False
    with np.errstate(invalid="ignore"):
        finite = np.isfinite(zz)
        if np.any(finite) and np.nanmin(zz) < SNR_TH_DB < np.nanmax(zz):
            cs = ax.contour(
                R, Z, zz, levels=[SNR_TH_DB], colors="#7ee8ff", linewidths=1.5
            )
            ax.clabel(cs, fmt={SNR_TH_DB: f"SNR = {SNR_TH_DB:.2f} dB"}, fontsize=8)
            drew = True
    ax.set_ylim(RCV_Z_MAX_M, 0)
    ax.set_xlim(0, EXT_R_MAX_M / 1000.0)
    ax.set_xlabel("Range (km)")
    ax.set_ylabel("Receiver depth (m)")
    ax.set_title(
        f"January SNR  SL={SL_DB:.0f} dB, NL={NL_DB_REUSED:.2f} dB, DI={DI_DB:.0f}  "
        f"(cyan = {SNR_TH_DB:.2f} dB)"
    )
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("SNR (dB)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return drew


def write_extended_readme(summary: dict, path: Path) -> None:
    jan = summary["january"]
    jul = summary["july"]
    c50j = jan["crossings"]["50.0"]
    c50u = jul["crossings"]["50.0"]

    def cross_line(month, rec):
        if rec["crossed"]:
            return (
                f"SNR crosses {SNR_TH_DB:.2f} dB at approximately "
                f"**{rec['first_below_m']:.0f} m** in {month} "
                f"(SNR {rec['snr_at_first_below_dB']:.2f} dB at that cell; "
                f"SNR at 6 km = {rec['snr_at_6km_dB']:.2f} dB)."
            )
        return (
            f"SNR does **not** fall below {SNR_TH_DB:.2f} dB anywhere on 25–6000 m "
            f"in {month}. SNR at 6 km / 50 m is **{rec['snr_at_6km_dB']:.2f} dB** "
            f"(margin {rec['snr_at_6km_dB'] - SNR_TH_DB:.2f} dB)."
        )

    def depth_table(month_rec):
        lines = [
            "| Depth (m) | first range SNR < 8.68 dB | SNR at crossing | SNR at 6 km | below-threshold fraction along depth |",
            "| --- | --- | --- | --- | --- |",
        ]
        for z in CROSS_DEPTHS_M:
            rec = month_rec["crossings"][f"{z:.1f}"]
            first = (
                f"{rec['first_below_m']:.0f} m" if rec["crossed"] else "does not cross"
            )
            at = (
                f"{rec['snr_at_first_below_dB']:.2f} dB" if rec["crossed"] else "—"
            )
            lines.append(
                f"| {z:.0f} | {first} | {at} | {rec['snr_at_6km_dB']:.2f} dB | "
                f"{100*rec['frac_below_th']:.1f}% ({rec['n_below_th']}/{rec['n_ranges']}) |"
            )
        return "\n".join(lines)

    def band_table():
        lines = [
            "| Range band | January frac SNR>8.68 (z≥10 m) | July frac SNR>8.68 (z≥10 m) | January median SNR | July median SNR |",
            "| --- | --- | --- | --- | --- |",
        ]
        for a, b in zip(jan["bands_zge10"], jul["bands_zge10"]):
            fj = "—" if a["frac_gt_th"] is None else f"{100*a['frac_gt_th']:.1f}% ({a['n_gt_th']}/{a['n']})"
            fu = "—" if b["frac_gt_th"] is None else f"{100*b['frac_gt_th']:.1f}% ({b['n_gt_th']}/{b['n']})"
            mj = "—" if a["snr_median_dB"] is None else f"{a['snr_median_dB']:.1f} dB"
            mu = "—" if b["snr_median_dB"] is None else f"{b['snr_median_dB']:.1f} dB"
            lines.append(f"| {a['band']} | {fj} | {fu} | {mj} | {mu} |")
        return "\n".join(lines)

    def spot_lines():
        lines = []
        for month, rec in (("January", jan), ("July", jul)):
            pts = rec["f3_spot"]
            mean_abs = float(np.mean([p["abs_delta_dB"] for p in pts if p["abs_delta_dB"] is not None]))
            lines.append(f"**{month}** mean |Δ| at the two spots: {mean_abs:.2f} dB")
            for p in pts:
                lines.append(
                    f"- r={p['used_range_m']:.0f} m, z={p['used_depth_m']:.0f} m: "
                    f"recon TL {p['recon_TL_dB']:.2f} dB, native .shd {p['native_TL_dB']:.2f} dB, "
                    f"|Δ| = {p['abs_delta_dB']:.2f} dB, in-band ptp {p['ptp_dB']:.1f} dB, "
                    f"n_arrivals={p['n_arrivals']}"
                )
        return "\n".join(lines)

    path.write_text(
        f"""# Extended-range channel database (Step G) — 0–6 km

Same Western Pacific primary cell (20.125°N, 124.125°E), flat **5524 m**
bottom (GEBCO 2 km east transect, ptp 2.55 m — no new bathymetry), full-column
WOA23 January/July SSP (not truncated at 500 m), src = 50 m, 24 kHz, coherent
geometric Gaussian beams, Thorp volume attenuation, SL = 175 dB, DI = 0,
NL = {NL_DB_REUSED:.2f} dB (reused Step-F band-integrated Wenz; s = 0.2 and
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

- {cross_line("January", c50j)}
- {cross_line("July", c50u)}

### Crossing vs receiver depth

**January**

{depth_table(jan)}

**July**

{depth_table(jul)}

### Fraction of cells with SNR > 8.68 dB by range band

Hydrophones at z ≥ 10 m only (z = 0 is the pressure-release artifact).
Range 0 m is excluded (Bellhop singularity, NaN). Bands are (lo, hi]
except the first band which is (0, 1000].

{band_table()}

## G1/G2 files

| Month | HDF5 | arrivals | empty (r = 0) | TL CSV | SNR CSV |
| --- | --- | --- | --- | --- | --- |
| January | `data/bellhop/arrivals_full_grid_extended_january.h5` | {jan['n_arrivals']} | {jan['n_empty']} | `data/channel_db/TL_grid_extended_january.csv` | `data/channel_db/SNR_grid_extended_january.csv` |
| July | `data/bellhop/arrivals_full_grid_extended_july.h5` | {jul['n_arrivals']} | {jul['n_empty']} | `data/channel_db/TL_grid_extended_july.csv` | `data/channel_db/SNR_grid_extended_july.csv` |

Columns match Step F: `[range_m, receiver_depth_m, TL_dB]` and
`[range_m, receiver_depth_m, SNR_dB]`. Range 0 m is NaN. Depth 0 m is
kept and flagged (pressure-release). Negative TL count: January
{jan['n_neg_tl']}, July {jul['n_neg_tl']}.

d_p method: {jan['d_p_method']}

## G4 — F3-style spot check at 4 km and 6 km, z = 50 m

Native Bellhop is single-frequency coherent `.shd` on the same extended
grid (run type CB). Reconstructed TL is the 2 kHz G_bar. A few dB is
expected; large |Δ| with large in-band ptp is frequency-selective fading,
not a new long-range breakdown.

{spot_lines()}

## Rebuild

```bash
python3 scripts/build_channel_db_extended.py
```

Native `.arr` / `.shd` stay local (gitignored). HDF5 and CSV are the
portable products. The original 0–2 km Step-F files are not overwritten.
"""
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-bellhop", action="store_true", help="reuse existing .arr/.shd/HDF5")
    args = ap.parse_args()

    CHAN.mkdir(parents=True, exist_ok=True)
    (CHAN / "figs").mkdir(parents=True, exist_ok=True)
    BELLHOP_DIR.mkdir(parents=True, exist_ok=True)

    nl = nl_db()
    nl_used = NL_DB_REUSED
    print(
        f"NL reused {nl_used}  (fresh nl_db integrated {nl['NL_integrated_dB']})",
        flush=True,
    )
    if abs(nl["NL_integrated_dB"] - nl_used) > 0.02:
        print("WARNING: recomputed NL drifted from the stored Step-F value", flush=True)

    nrr = n_points(0.0, EXT_R_MAX_M, EXT_DR_M)
    nrd = n_points(0.0, RCV_Z_MAX_M, RCV_DZ_M)
    if nrr != len(EXT_RANGES) or nrd != len(EXT_DEPTHS):
        raise RuntimeError(f"grid mismatch nrr={nrr} vs {len(EXT_RANGES)}, nrd={nrd}")

    summary = {
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid": {
            "range_m": [0.0, EXT_R_MAX_M],
            "dr_m": EXT_DR_M,
            "n_ranges": int(nrr),
            "depth_m": [0.0, RCV_Z_MAX_M],
            "dz_m": RCV_DZ_M,
            "n_depths": int(nrd),
            "n_points": int(nrr * nrd),
            "rbox_km": EXT_RBOX_KM,
            "nbeams": NBEAMS,
            "note": (
                "241 ranges = 0,25,…,6000 inclusive (240 intervals). "
                "User cited 240; the inclusive count is the analog of 201 on 0–2000/10."
            ),
        },
        "unchanged": {
            "bottom_m": BOTTOM_M,
            "ssp": "full-column WOA23 monthly 0-1500 + annual 1550-5500 + Mackenzie 5524",
            "src_depth_m": SRC_DEPTH_M,
            "freq_hz": 24000.0,
            "run_type_arrivals": "A",
            "run_type_tl": "CB",
            "kappa": KAPPA,
            "SL_dB": SL_DB,
            "DI_dB": DI_DB,
            "NL_dB": nl_used,
            "SNR_th_dB": SNR_TH_DB,
            "s_shipping_assumed": 0.2,
            "w_mps_assumed": 2.0,
        },
        "reasoning_6km": (
            "6 km extends beyond LQARP's reported 4 km operational range so the "
            "grid can capture the SNR=8.68 dB transition if it exists at this site. "
            "The 0–2 km grid was too benign (100% of z>=10 m cells above threshold)."
        ),
        "january": {},
        "july": {},
    }

    for month, month_num in (("january", 1), ("july", 7)):
        ssp = build_full_column_ssp(month_num)
        c_src = c_at_src(ssp)
        h5_path = BELLHOP_DIR / f"arrivals_full_grid_extended_{month}.h5"
        arr_path, shd_path = run_extended_bellhop(month, ssp, skip=args.skip_bellhop)
        if not (args.skip_bellhop and h5_path.is_file()):
            print(f"== parse {arr_path.name}", flush=True)
            rows = read_arrivals_asc(arr_path)
            arrivals_to_h5(
                rows,
                h5_path,
                month=month,
                c_src=c_src,
                ssp_note="WOA23 monthly 0-1500 + annual 1550-5500 + Mackenzie 5524",
                ranges=EXT_RANGES,
                depths=EXT_DEPTHS,
            )
            del rows
        print(f"== H_eq extended {month}", flush=True)
        grids = heq_grids(h5_path)
        tl = grids["TL_dB"]
        snr = SL_DB - tl - nl_used + DI_DB
        ranges, depths = grids["ranges_m"], grids["depths_m"]
        write_grid_csv(CHAN / f"TL_grid_extended_{month}.csv", ranges, depths, tl, "TL_dB")
        write_grid_csv(CHAN / f"SNR_grid_extended_{month}.csv", ranges, depths, snr, "SNR_dB")
        np.savez_compressed(
            CHAN / f"grids_extended_{month}.npz",
            ranges_m=ranges,
            depths_m=depths,
            TL_dB=tl,
            SNR_dB=snr,
            G_bar=grids["G_bar"],
            ptp_dB=grids["ptp_dB"],
            flags=grids["flags"],
        )

        shd = read_shd(shd_path)
        native = {"tl_db": shd["tl_db"][0], "rz": shd["rz"], "rr": shd["rr"]}
        spots = [spot_f3(grids, native, r0, SPOT_DEPTH_M) for r0 in SPOT_RANGES_M]
        mean_spot = float(
            np.mean([p["abs_delta_dB"] for p in spots if p["abs_delta_dB"] is not None])
        )

        crossings = {}
        for z in CROSS_DEPTHS_M:
            iz = int(np.argmin(np.abs(depths - z)))
            crossings[f"{z:.1f}"] = {
                "depth_m": float(depths[iz]),
                **crossing_along_depth(ranges, snr[iz], SNR_TH_DB),
            }

        finite = np.isfinite(tl)
        rec = {
            "c_src_mps": c_src,
            "n_arrivals": int(np.sum(grids["n_used"])),
            "n_empty": int(np.sum(grids["n_used"] == 0)),
            "n_finite_tl": int(np.sum(finite)),
            "n_nan_tl": int(np.sum(~finite)),
            "n_neg_tl": int(np.sum(finite & (tl < 0))),
            "d_p_method": grids["d_p_method"],
            "crossings": crossings,
            "bands_zge10": band_fractions(ranges, depths, snr, zmin=RCV_DZ_M),
            "bands_all_z": band_fractions(ranges, depths, snr, zmin=0.0),
            "f3_spot": spots,
            "f3_spot_mean_abs_dB": mean_spot,
            "tl_50m_6km_dB": pick(ranges, depths, tl, EXT_R_MAX_M, 50.0)[-1],
            "snr_50m_6km_dB": pick(ranges, depths, snr, EXT_R_MAX_M, 50.0)[-1],
        }
        with h5py.File(h5_path, "r") as h:
            rec["n_arrivals"] = int(np.sum(h["n_arrivals"][:]))
            rec["n_empty"] = int(np.sum(h["n_arrivals"][:] == 0))
        summary[month] = rec
        print(json.dumps({month: {
            "n_arrivals": rec["n_arrivals"],
            "n_empty": rec["n_empty"],
            "n_neg_tl": rec["n_neg_tl"],
            "cross_50m": rec["crossings"]["50.0"],
            "f3_spot_mean_abs_dB": rec["f3_spot_mean_abs_dB"],
            "spots": rec["f3_spot"],
            "snr_50m_6km_dB": rec["snr_50m_6km_dB"],
        }}, indent=2), flush=True)

        if month == "january":
            fig, ax = plt.subplots(figsize=(10.6, 3.9))
            rr_km = ranges / 1000.0
            im = ax.pcolormesh(
                rr_km, depths, tl, shading="auto", cmap="viridis_r", vmin=40, vmax=140
            )
            ax.set_ylim(RCV_Z_MAX_M, 0)
            ax.set_xlim(0, EXT_R_MAX_M / 1000.0)
            ax.set_xlabel("Range (km)")
            ax.set_ylabel("Receiver depth (m)")
            ax.set_title("January TL  0–6 km  (band-averaged |H_eq|\u00b2, sonar-equation loss)")
            cb = fig.colorbar(im, ax=ax, pad=0.02)
            cb.set_label("TL (dB)")
            fig.tight_layout()
            fig.savefig(CHAN / "figs" / "TL_heatmap_extended_january.png", dpi=140)
            plt.close(fig)
            drew = plot_snr_threshold(
                ranges,
                depths,
                snr,
                CHAN / "figs" / "SNR_heatmap_extended_january_with_threshold.png",
            )
            rec["snr_contour_drawn"] = drew
            summary[month] = rec

    write_extended_readme(summary, CHAN / "README_extended.md")
    (CHAN / "summary_extended.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("wrote", CHAN / "README_extended.md", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
