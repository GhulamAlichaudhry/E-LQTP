# Step 1e — LQARP-refreshed vs frozen LQARP vs E-LQTP

## Change (diagnostic only)

`lqarp-refreshed` is LQARP with held pose, velocity, and residual energy overwritten every **T_ctrl = 5 s** on the same grid Fixed-Periodic uses (`emitHoldRefresh`, mirroring `emitPeriodicControl` field writes). Manuscript LQARP still freezes at first discovery. **Q-learning, `c_nei`, `N_stab`, and reward weights were not changed.** O_ctrl remains 0 (refresh is not charged as HELLO traffic).

Re-run: Scenario **II** and **III** at **2 m/s**, seeds **20260921–20260925**, `--hopDiag` as in Step 1d.

## Headline comparison (five-seed mean)

| Protocol | Scenario II hops | Scenario II T_e2e (s) | Scenario III hops | Scenario III T_e2e (s) |
| --- | ---: | ---: | ---: | ---: |
| LQARP frozen (Step 1c/1d) | 2.241 | 4.212 | 4.148 | 8.408 |
| **LQARP-refreshed (Step 1e)** | **1.000** | **1.845** | **1.000** | **1.815** |
| E-LQTP (Step 1c/1d) | 4.975 | 9.731 | 8.218 | 16.789 |
| Fixed-Periodic (Step 1d) | 1.000 | 1.845 | 1.000 | 1.815 |

PDR = 1.000 for LQARP-refreshed on all ten runs.

## HopDiag — sink pass-over and `c_nei`

| Protocol | II: sink in set but relay chosen | II: `c_nei` relay > sink on pass-overs | II: live-1 path but >1 hop | III: pass-over rate | III: live-1 longer |
| --- | ---: | ---: | ---: | ---: | ---: |
| LQARP frozen | 54.5% (4310/7909) | 4310 / 4310 | 30.2% | 76.0% | 56.4% |
| LQARP-refreshed | **0.0%** (0/3599) | 0 | **0.0%** | **~0%** (1/3649) | ~0% |
| E-LQTP | 79.6% (14044/17643) | 14044 / 14044 | 51.7% | 87.9% | 81.1% |

Forwarding decisions per delivered packet: frozen LQARP ~2.2 and E-LQTP ~5–8 relay decisions; LQARP-refreshed **1** (source only, direct to sink).

On pass-overs, Step 1d already showed **`c_nei` larger on the relay on 100%** of decisions for frozen LQARP and E-LQTP, with **`c_ene` equal** at the instant of the pass-over. LQARP-refreshed never pass over the sink, so **`c_nei` never enters the comparison**.

## Interpretation (vs Step 1d hypothesis)

Step 1d asked whether **frozen LQARP energy** masks the same **`c_nei` penalty on the sink** that E-LQTP sees once `c_ene` leaves the zero tie.

**Result: neither branch of the Step 1e prompt.**

1. **LQARP-refreshed does not climb toward E-LQTP (~5 hops).** It collapses to **one hop**, matching Fixed-Periodic on the same geometry, not E-LQTP.

2. **It also does not stay near frozen LQARP (~2.2 hops).** Refresh **removes** multi-hop behavior rather than amplifying it.

Mechanism consistent with the counters:

- With **5 s full-state refresh**, held energies track live residuals and stay **mutually aligned** in each candidate set, so **`c_ene` stays at the degenerate zero tie** (`R = 0` at the sink whenever the common factor is zero). The sink wins by **id tie-break** or strict `Q` when no relay has accumulated credit.
- **Frozen LQARP** keeps **stale** `energy_j_zoh` (and pose) from **first discovery**. That does not mirror live drain uniformly across neighbors. Together with **Q backups** (`γ · max Q` along relays even when instantaneous `R = 0`), relays accumulate **`Q` > Q(sink)** while **`c_nei` inflates `R` whenever the product is non-zero**. That reproduces Step 1d’s pass-over pattern without needing `N_stab` or filter bugs.
- **E-LQTP** refreshes on **bootstrap + event HELLOs** (not a uniform 5 s grid on all pairs). Held energy stays **heterogeneous** often enough that pass-over remains **~80–88%**, with the same **`c_nei`-only** factor on every pass-over.

So the Step 1c **LQARP vs E-LQTP hop gap is not explained by “E-LQTP refreshes energy, LQARP doesn’t, therefore E-LQTP alone sees `c_nei`.”** Frozen LQARP **already** pass over the sink **more than half** the time via **`c_nei` / Q**, not via held-energy balancing (`c_ene` / `c_del` on pass-overs).

The confound runs the **other way**: **more frequent symmetric refresh pushes LQARP toward the one-hop periodic regime** by keeping **`c_ene` pinned at zero**. E-LQTP’s **event-sparse** writes leave enough stale spread for **`c_nei`-driven Q** to dominate.

## Implications (diagnostic; no retuning done)

- The **`c_nei = exp(|I(s_j)|)`** sink penalty remains a **protocol-agnostic reward-shape issue** (Step 1d), but **LQARP’s manuscript frozen hold is not hiding it**—frozen LQARP is already multi-hop on mobile scenarios because of **stale holds + Q**, not because it refreshes less than E-LQTP in a way that uniquely enables `c_nei`.
- Publishing **Step 1c LQARP vs E-LQTP hops** as a comparison of two routing designs **without** stating **different hold/refresh semantics and the `c_nei` term** would still be misleading; Step 1e adds that **giving LQARP the periodic refresh grid does not reproduce E-LQTP’s hop inflation—it removes LQARP’s**.
- **Open (unchanged):** whether a **fair** LQARP baseline would use **periodic energy refresh without** collapsing to one hop (e.g. intermediate refresh rate, or refresh that does not sync all holds to live drain)—that is **not** decided here. **Do not** cap or rescale `c_nei` from this run alone.

## Reproduce

```bash
./ns3 build scenario-i-lqarp
BIN=build/contrib/elqtp/ns3.41-scenario-i-lqarp-optimized
$BIN --scenario=ii --nAuv=40 --simTime=600 --seed=20260921 --driftSpeed=2 \
  --protocol=lqarp-refreshed --boundary=remove --hopDiag=true --quiet \
  --out=results/step1e_hopcount/sii_lqarp-refreshed_d2.0_20260921.txt
```

Raw reports: `results/step1e_hopcount/s{ii,iii}_lqarp-refreshed_d2.0_<seed>.txt`. Baselines: `results/step1d_hopcount/`.
