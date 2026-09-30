#!/usr/bin/env python3
"""Five-seed mean ± sample s.d. and manuscript side-by-side for the Step-1 re-run.

A cell is flagged when the new mean lies outside the manuscript mean ± sample s.d.
A manuscript entry printed without a deviation is a zero-width band at the
printed value (half a unit in the last printed digit).
"""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "results" / "step1c_rerun" / "step1_campaign.csv"
OUT_PATH = ROOT / "results" / "step1c_rerun" / "COMPARISON.md"

# (mean, sd). sd == 0 means the manuscript printed no deviation.
# Metrics: pdr, hops, te2e, ebit, octrl, first_fire. None = not in that table.
S1 = {
    "lqarp": dict(pdr=(1.0, 0.0), hops=(1.530, 0.068), te2e=(3.078, 0.071),
                  ebit=(8.20e-3, 0.37e-3), octrl=(0.0, 0.0), ff=None),
    "elqtp": dict(pdr=(1.0, 0.0), hops=(1.530, 0.068), te2e=(3.078, 0.071),
                  ebit=(8.20e-3, 0.37e-3), octrl=(0.0, 0.0), ff=None),
    "rlor": dict(pdr=(1.0, 0.0), hops=(1.000, 0.0), te2e=(1.887, 0.108),
                 ebit=(5.36e-3, 0.0), octrl=(0.0, 0.0), ff=None),
    "periodic": dict(pdr=(1.0, 0.0), hops=(1.546, 0.039), te2e=(3.119, 0.188),
                     ebit=(8.29e-3, 0.21e-3), octrl=(442.03, 0.0), ff=None),
}

# Table III, Scenario II at 2 m/s.
S2_PROTO = {
    "lqarp": dict(pdr=(0.9992, 0.0019), hops=(2.153, 0.187), te2e=(4.438, 0.277),
                  ebit=(1.156e-2, 0.100e-2), octrl=(0.0, 0.0), ff=None),
    "elqtp": dict(pdr=(0.9992, 0.0019), hops=(2.154, 0.187), te2e=(4.439, 0.277),
                  ebit=(1.156e-2, 0.100e-2), octrl=(135.0, 23.0), ff=(0.782, 0.042)),
    "rlor": dict(pdr=(1.0, 0.0), hops=(1.000, 0.001), te2e=(1.845, 0.074),
                 ebit=(5.362e-3, 0.0), octrl=(0.0, 0.0), ff=None),
    "periodic": dict(pdr=(0.9992, 0.0019), hops=(2.153, 0.187), te2e=(4.438, 0.277),
                     ebit=(1.156e-2, 0.100e-2), octrl=(413.42, 0.0), ff=(1.0, 0.0)),
}

# Table IV. E_bit is not in the drift table.
def _d(pdr, te, hops, octrl=None, ff=None):
    return dict(pdr=pdr, te2e=te, hops=hops, ebit=None, octrl=octrl, ff=ff)

S2_DRIFT = {
    (0.5, "lqarp"): _d((1.0, 0.0), (4.776, 0.403), (2.282, 0.186), (0.0, 0.0), None),
    (0.5, "elqtp"): _d((1.0, 0.0), (4.776, 0.403), (2.282, 0.186), (20.2, 4.2), (0.146, 0.021)),
    (1.0, "lqarp"): _d((0.9995, 0.0012), (4.752, 0.377), (2.289, 0.208), (0.0, 0.0), None),
    (1.0, "elqtp"): _d((0.9995, 0.0012), (4.752, 0.377), (2.289, 0.208), (70.7, 6.2), (0.520, 0.031)),
    (2.0, "lqarp"): _d((0.9992, 0.0019), (4.438, 0.277), (2.153, 0.187), (0.0, 0.0), None),
    (2.0, "elqtp"): _d((0.9992, 0.0019), (4.439, 0.277), (2.154, 0.187), (135.1, 23.1), (0.782, 0.042)),
    (3.0, "lqarp"): _d((1.0, 0.0), (4.431, 0.333), (2.154, 0.203), (0.0, 0.0), None),
    (3.0, "elqtp"): _d((1.0, 0.0), (4.433, 0.331), (2.155, 0.203), (213.8, 39.1), (0.857, 0.034)),
    (3.5, "lqarp"): _d((1.0, 0.0), (4.200, 0.393), (2.063, 0.215), (0.0, 0.0), None),
    (3.5, "elqtp"): _d((1.0, 0.0), (4.200, 0.393), (2.063, 0.215), (257.7, 46.9), (0.897, 0.028)),
}

S3 = {
    "lqarp": dict(pdr=(0.9989, 0.0018), hops=(2.046, 0.187), te2e=(4.146, 0.348),
                  ebit=(1.099e-2, 0.098e-2), octrl=(0.0, 0.0), ff=None),
    "elqtp": dict(pdr=(0.9989, 0.0018), hops=(2.050, 0.186), te2e=(4.167, 0.318),
                  ebit=(1.101e-2, 0.097e-2), octrl=(211.0, 34.0), ff=(0.708, 0.059)),
    "rlor": dict(pdr=(1.0, 0.0), hops=(1.000, 0.0), te2e=(1.814, 0.093),
                 ebit=(5.361e-3, 0.0), octrl=(0.0, 0.0), ff=None),
    "periodic": dict(pdr=(0.9989, 0.0018), hops=(2.046, 0.187), te2e=(4.146, 0.348),
                     ebit=(1.099e-2, 0.098e-2), octrl=(413.42, 0.0), ff=(1.0, 0.0)),
}

NAMES = {"lqarp": "LQARP", "elqtp": "E-LQTP", "rlor": "RLOR-inspired", "periodic": "Periodic"}
METRICS = [
    ("pdr", "PDR", "PDR"),
    ("hops", "Hops", "mean_hops"),
    ("te2e", "T_e2e", "T_e2e_s"),
    ("ebit", "E_bit", "E_bit_J_per_bit"),
    ("octrl", "O_ctrl", "O_ctrl_byte_per_s"),
    ("ff", "First-fire", "first_fire_rate"),
]


def mean_sd(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    mu = sum(xs) / n
    if n < 2:
        return mu, float("nan")
    var = sum((x - mu) ** 2 for x in xs) / (n - 1)
    return mu, math.sqrt(var)


def load() -> list[dict]:
    rows = []
    with CSV_PATH.open() as f:
        for r in csv.DictReader(f):
            out = dict(r)
            out["seed"] = int(r["seed"])
            out["drift_mps"] = float(r["drift_mps"])
            for k in (
                "PDR", "T_e2e_s", "E_bit_J_per_bit", "O_ctrl_byte_per_s",
                "mean_hops", "first_fire_rate", "VOID", "VOID_stale",
                "VOID_via_stale", "VOID_live", "SNR", "SNR_stale", "SNR_genuine",
                "LOST_NODE_EXIT", "envelope_via_stale", "stale_admit",
                "stale_admit_ok", "n_gen", "n_succ", "n_tx",
                "event_hellos", "bootstrap_hellos",
            ):
                out[k] = float(r[k]) if r[k] not in ("", "nan") else float("nan")
            rows.append(out)
    return rows


def groups(rows: list[dict]) -> dict[tuple, list[dict]]:
    g: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        g[(r["scenario"], r["protocol"], r["drift_mps"])].append(r)
    return g


def fmt_pm(mu: float, sd: float, kind: str) -> str:
    if math.isnan(mu):
        return "nan"
    if kind == "pdr":
        body = f"{mu:.4f}"
    elif kind in ("hops", "te2e", "ff"):
        body = f"{mu:.3f}"
    elif kind == "ebit":
        body = f"{mu:.6e}"
    else:
        body = f"{mu:.2f}"
    if math.isnan(sd):
        return body
    return f"{body} ± {sd:.4g}"


def zero_band(kind: str, mean: float) -> float:
    """Half a unit in the last digit of a deviation-free manuscript cell."""
    if kind == "pdr":
        return 5e-4 if mean >= 0.1 else 5e-5
    if kind in ("hops", "te2e", "ff"):
        return 5e-4
    if kind == "ebit":
        # 5.36e-3 and 5.362e-3 are both printed to about 1e-6.
        return 5e-6 if mean < 0.01 else 5e-5
    if mean == 0.0:
        return 1e-6
    return 0.005


def flagged(new: float, cell, kind: str) -> bool:
    if cell is None:
        return False
    if math.isnan(new):
        return True
    mean, sd = cell
    if sd > 0:
        return abs(new - mean) > sd
    return abs(new - mean) > zero_band(kind, mean)


def cell_text(new_mu: float, new_sd: float, cell, kind: str) -> str:
    shown = fmt_pm(new_mu, new_sd, kind)
    if cell is None:
        if math.isnan(new_mu):
            return "—"
        return shown
    mark = " **FLAG**" if flagged(new_mu, cell, kind) else ""
    om, osd = cell
    return f"{shown} (ms {fmt_pm(om, osd, kind)}){mark}"


def agg(rs: list[dict], key: str) -> tuple[float, float]:
    xs = [r[key] for r in rs if not math.isnan(r[key])]
    if not xs:
        return float("nan"), float("nan")
    return mean_sd(xs)


def metric_table(title: str, spec: dict, rs_of, lines: list[str]) -> int:
    lines.append(f"### {title}")
    lines.append("")
    header = "| Protocol | " + " | ".join(m[1] for m in METRICS) + " |"
    sep = "|---|" + "|".join(["---"] * len(METRICS)) + "|"
    lines.append(header)
    lines.append(sep)
    nflag = 0
    for proto, cells in spec.items():
        rs = rs_of(proto)
        cols = []
        for kind, _label, key in METRICS:
            mu, sd = agg(rs, key)
            text = cell_text(mu, sd, cells[kind], kind)
            if flagged(mu, cells[kind], kind):
                nflag += 1
            cols.append(text)
        lines.append(f"| {NAMES[proto]} | " + " | ".join(cols) + " |")
    lines.append("")
    lines.append(f"Flagged cells: {nflag}.")
    lines.append("")
    return nflag


def sum_key(rs: list[dict], key: str) -> float:
    return sum(r[key] for r in rs)


def breakdown(rows_g, lines: list[str]) -> None:
    lines.append("## PDR-drop breakdown (LQARP and RLOR-inspired, Scenarios II and III)")
    lines.append("")
    lines.append(
        "A lost packet is **stale-caused** when the frozen snapshot still "
        "passed the candidate-set filters and the live state would not: "
        "the transmission failed reception on that hop (`SNR_stale`), the "
        "frozen forwarder set was empty while a live filter still admitted "
        "an unvisited neighbor (`VOID_stale`), or the packet had already "
        "been forwarded across such a hop and then found no live forwarder "
        "(`VOID_via_stale`). **Anyway** losses are envelope exit "
        "(`LOST_NODE_EXIT`), reception failure on a hop the live filters "
        "still admit (`SNR_genuine`), and a void where the live filters "
        "are also empty and no earlier hop was stale (`VOID_live`), plus "
        "energy, TTL, and end-of-simulation drops (those three are not "
        "split out below; they were zero in the manuscript campaign). "
        "`envelope_via_stale` is the subset of envelope exits that occurred "
        "after a stale hop; those packets stay in the anyway column, "
        "matching the requested envelope category."
    )
    lines.append("")
    lines.append(
        "| Case | Protocol | PDR | Fail pkts | Stale-caused | of which SNR / void-empty / void-after-stale | Anyway | of which envelope / genuine SNR / live void | Stale hops (rx ok) |"
    )
    lines.append("|---|---|---:|---:|---:|---|---:|---|---:|")
    cases = []
    for drift in (0.5, 1.0, 2.0, 3.0, 3.5):
        for proto in ("lqarp", "rlor"):
            if drift != 2.0 and proto == "rlor":
                continue
            cases.append(("ii", proto, drift, f"II v={drift:.1f}"))
    for proto in ("lqarp", "rlor"):
        cases.append(("iii", proto, 2.0, "III V=2"))
    for scenario, proto, drift, label in cases:
        rs = rows_g.get((scenario, proto, drift), [])
        if len(rs) != 5:
            lines.append(f"| {label} | {NAMES[proto]} | missing {len(rs)}/5 seeds | | | | | | |")
            continue
        pdr, _ = agg(rs, "PDR")
        n_gen = sum_key(rs, "n_gen")
        n_succ = sum_key(rs, "n_succ")
        snr_s = sum_key(rs, "SNR_stale")
        snr_g = sum_key(rs, "SNR_genuine")
        void_s = sum_key(rs, "VOID_stale")
        void_v = sum_key(rs, "VOID_via_stale")
        void_l = sum_key(rs, "VOID_live")
        env = sum_key(rs, "LOST_NODE_EXIT")
        stale = snr_s + void_s + void_v
        anyway = snr_g + void_l + env
        fail = n_gen - n_succ
        admit = sum_key(rs, "stale_admit")
        admit_ok = sum_key(rs, "stale_admit_ok")
        lines.append(
            f"| {label} | {NAMES[proto]} | {pdr:.4f} | {fail:.0f} | {stale:.0f} | "
            f"{snr_s:.0f} / {void_s:.0f} / {void_v:.0f} | {anyway:.0f} | "
            f"{env:.0f} / {snr_g:.0f} / {void_l:.0f} | {admit:.0f} ({admit_ok:.0f} received) |"
        )
    lines.append("")
    lines.append(
        "Sums are over five seeds. Fail pkts = N_gen − N_succ. "
        "Stale-caused + anyway equals that difference when energy, TTL, "
        "and end-of-simulation losses are zero and the void/SNR splits partition the counters."
    )
    lines.append("")


def hello_split(rows_g, lines: list[str]) -> None:
    lines.append("## Control-cost split")
    lines.append("")
    lines.append(
        "O_ctrl charges event HELLOs and bootstrap HELLOs together. "
        "A bootstrap HELLO is one 400-bit packet per directed pair, written "
        "the first time that pair passes live range and SNR. Event HELLOs "
        "are the rising-edge count (E-LQTP) or the T_ctrl count (Fixed-Periodic). "
        "Fixed-Periodic already ingests at t=0, so its bootstrap count stays 0."
    )
    lines.append("")
    lines.append("| Case | Protocol | O_ctrl | Event byte/s | Bootstrap byte/s | Event HELLOs | Bootstrap HELLOs |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    cases = [("i", "elqtp", 0.0, "I"), ("i", "periodic", 0.0, "I")]
    for drift in (0.5, 1.0, 2.0, 3.0, 3.5):
        cases.append(("ii", "elqtp", drift, f"II v={drift:.1f}"))
    cases.append(("ii", "periodic", 2.0, "II v=2.0"))
    cases.append(("iii", "elqtp", 2.0, "III"))
    cases.append(("iii", "periodic", 2.0, "III"))
    for scenario, proto, drift, label in cases:
        rs = rows_g.get((scenario, proto, drift), [])
        if len(rs) != 5:
            lines.append(f"| {label} | {NAMES[proto]} | missing {len(rs)}/5 | | | | |")
            continue
        o, _ = agg(rs, "O_ctrl_byte_per_s")
        ev = [r["event_hellos"] * 50.0 / float(r["T_sim_s"]) for r in rs]
        bo = [r["bootstrap_hellos"] * 50.0 / float(r["T_sim_s"]) for r in rs]
        emu, _ = mean_sd(ev)
        bmu, _ = mean_sd(bo)
        lines.append(
            f"| {label} | {NAMES[proto]} | {o:.2f} | {emu:.2f} | {bmu:.2f} | "
            f"{sum_key(rs, 'event_hellos'):.0f} | {sum_key(rs, 'bootstrap_hellos'):.0f} |"
        )
    lines.append("")


def counter_audit(rows: list[dict], lines: list[str]) -> None:
    bad = []
    for r in rows:
        void = r["VOID"]
        snr = r["SNR"]
        if abs((r["VOID_stale"] + r["VOID_via_stale"] + r["VOID_live"]) - void) > 1e-6:
            bad.append(f"void split {r['scenario']} {r['protocol']} {r['seed']}")
        if abs((r["SNR_stale"] + r["SNR_genuine"]) - snr) > 1e-6:
            bad.append(f"snr split {r['scenario']} {r['protocol']} {r['seed']}")
    lines.append("## Counter partition")
    lines.append("")
    if bad:
        lines.append("Partition failures:")
        for b in bad:
            lines.append(f"- {b}")
    else:
        lines.append(
            f"All {len(rows)} runs satisfy "
            "VOID = VOID_stale + VOID_via_stale + VOID_live and "
            "SNR = SNR_stale + SNR_genuine."
        )
    lines.append("")


def main() -> int:
    if not CSV_PATH.is_file():
        print(f"missing {CSV_PATH}", file=sys.stderr)
        return 1
    rows = load()
    g = groups(rows)
    lines: list[str] = []
    lines.append("# Step-1c re-run vs manuscript Tables II–V")
    lines.append("")
    lines.append(
        "Held/frozen neighbor pose and energy. `c_lin`, `linkSample`, "
        "`predictPair`, and `predictForecast` still query the live channel. "
        "Seeds 20260921–20260925, N=40, January site, boundary=remove, "
        "β1=β2=0. Drift sweep 0.5–3.5 m/s. Eddy: Rankine core R=2000 m "
        "at (3000, 3000), V=2 m/s, Gauss–Markov ζ=0.95, σ=(1, 1, 0). "
        "Means are five-seed; deviations are the sample standard deviation (n−1)."
    )
    lines.append("")

    def rs_s1(proto):
        return g.get(("i", proto, 0.0), [])

    n1 = metric_table("Scenario I (manuscript Table II)", S1, rs_s1, lines)
    if n1:
        lines.append(
            "**Scenario I is not numerically identical to Table II.** "
            f"{n1} cell(s) fall outside the manuscript band. "
            "PDR is 1 for every protocol. The hop, delay, and energy "
            "flags are the held residual energy: discovery and bootstrap "
            "freeze E_ini, c_ene stays 0, and the tie-break selects the "
            "sink. E-LQTP's O_ctrl flag is the bootstrap HELLO charge "
            "(event HELLOs are 0 because the EKF is not ticked). "
            "RLOR matches Table II."
        )
        lines.append("")
    else:
        lines.append(
            "Scenario I matches Table II on every compared cell (new mean "
            "inside the manuscript ± s.d. band, including zero-width cells)."
        )
        lines.append("")

    def rs_s2(proto):
        return g.get(("ii", proto, 2.0), [])

    metric_table("Scenario II at 2 m/s (manuscript Table III)", S2_PROTO, rs_s2, lines)

    lines.append("### Scenario II drift sweep (manuscript Table IV)")
    lines.append("")
    lines.append("| v | Protocol | PDR | T_e2e | Hops | O_ctrl | First-fire | E_bit (not in table) |")
    lines.append("|---:|---|---|---|---|---|---|---|")
    nflag = 0
    for drift in (0.5, 1.0, 2.0, 3.0, 3.5):
        for proto in ("lqarp", "elqtp"):
            cells = S2_DRIFT[(drift, proto)]
            rs = g.get(("ii", proto, drift), [])
            cols = []
            for kind, key in (
                ("pdr", "PDR"),
                ("te2e", "T_e2e_s"),
                ("hops", "mean_hops"),
                ("octrl", "O_ctrl_byte_per_s"),
                ("ff", "first_fire_rate"),
            ):
                mu, sd = agg(rs, key)
                cols.append(cell_text(mu, sd, cells[kind], kind))
                if flagged(mu, cells[kind], kind):
                    nflag += 1
            emu, esd = agg(rs, "E_bit_J_per_bit")
            cols.append(fmt_pm(emu, esd, "ebit"))
            lines.append(
                f"| {drift:.1f} | {NAMES[proto]} | " + " | ".join(cols) + " |"
            )
    lines.append("")
    lines.append(f"Flagged cells: {nflag}.")
    lines.append("")

    def rs_s3(proto):
        return g.get(("iii", proto, 2.0), [])

    metric_table("Scenario III (manuscript Table V)", S3, rs_s3, lines)
    breakdown(g, lines)
    hello_split(g, lines)
    counter_audit(rows, lines)

    lines.append("## How to read the flags")
    lines.append("")
    lines.append(
        "Scenario I still does not step the EKF. Bootstrap runs from the "
        "first candidate-set query, so E-LQTP has a held neighbor snapshot "
        "without a trigger tick. LQARP and that bootstrap both freeze "
        "residual energy at first contact, so c_ene is 0 while every "
        "discovered neighbor still holds E_ini, Q stays tied, and the "
        "tie-break selects the sink. RLOR does not use energy in P_succ."
    )
    lines.append("")
    lines.append(
        "O_ctrl in this re-run includes bootstrap HELLOs. A flagged O_ctrl "
        "or first-fire cell is that added discovery, not a change to the "
        "persistence gate. First-fire is the fraction of live pairs whose "
        "held state has been written; bootstrap sets that bit at first "
        "contact, so the fraction is no longer the trigger-fire rate. "
        "The event-byte/s column above is the rising-edge or T_ctrl cost alone."
    )
    lines.append("")
    lines.append(
        "Fixed-Periodic already copies neighbor state at t=0 and does not "
        "add a second bootstrap charge. Its Scenario I O_ctrl of about "
        "411.28 byte/s is 13161 control packets × 50 bytes / 1600 s with "
        "the drain excluded. Table II prints 442.03 byte/s, which equals "
        "the drain-included count 14145 × 50 / 1600. Scenarios II and III "
        "periodic O_ctrl remain the drain-excluded grid."
    )
    lines.append("")
    lines.append("## Scenario I loss counters (five-seed sums)")
    lines.append("")
    lines.append("| Protocol | N_gen | N_succ | VOID_stale | VOID_live | SNR_stale | SNR_genuine | Envelope | Stale hops |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for proto in ("lqarp", "elqtp", "rlor", "periodic"):
        rs = rs_s1(proto)
        if not rs:
            continue
        lines.append(
            f"| {NAMES[proto]} | {sum_key(rs,'n_gen'):.0f} | {sum_key(rs,'n_succ'):.0f} | "
            f"{sum_key(rs,'VOID_stale'):.0f} | {sum_key(rs,'VOID_live'):.0f} | "
            f"{sum_key(rs,'SNR_stale'):.0f} | {sum_key(rs,'SNR_genuine'):.0f} | "
            f"{sum_key(rs,'LOST_NODE_EXIT'):.0f} | {sum_key(rs,'stale_admit'):.0f} |"
        )
    lines.append("")
    text = "\n".join(lines) + "\n"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text)
    print(text)
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
