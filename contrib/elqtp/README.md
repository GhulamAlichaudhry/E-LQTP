# contrib/elqtp — Bellhop channel lookup, LQARP, E-LQTP, RLOR-inspired

SPEC.md in this directory is the **only** authoritative source for
LQARP / E-LQTP math. `phase1/` and `paper/iotj_et_hold.tex` are an
unrelated prior testbed (event-triggered HELLO + ETHA, not
Q-learning) and are not a reference implementation.

## Layout

```
contrib/elqtp/
  SPEC.md
  CMakeLists.txt
  model/bellhop-data-loader.h/.cc
  model/channel-gate.h/.cc          # shared SNR gate
  model/link-quality.h/.cc          # shared OFDM BER + kBerFloor
  model/lqarp-protocol.h/.cc        # LQARP baseline (Part 1)
  model/elqtp-protocol.h/.cc        # E-LQTP (Part 2) + periodic ablation (Part 4)
  model/rlor-inspired-protocol.h/.cc  # RLOR-inspired (Part 3, documented simplification)
  model/gauss-markov.h/.cc          # Scenario III GM + eddy mean flow
  model/elqtp-run-config.h/.cc      # CLI / file runtime sweep (no rebuild)
  model/acoustic-energy.h             # first-pass TX/RX energy (Scenario I)
  examples/lqarp-unit-check*.cc
  examples/scenario-i-lqarp.cc        # Section 4.2 Scenarios I, II, III
```

## Shared BER floor

`kBerFloor = 1e-9` in `link-quality.h`. LQARP, E-LQTP, and the
RLOR-inspired baseline all call `elqtp::cLin` / `elqtp::pSucc` /
`effectiveBer` from that file. `E_ini = 10000 J` (Section 4.1).

`RlorInspiredProtocol` is a documented simplification, not a
faithful RLOR reimplementation (SPEC Part 3).

## Runtime sweep (no rebuild)

`ElqtpProtocol` takes `ElqtpConfig` by value. `ElqtpRunConfig`
parses `--beta_1=... --beta_2=... --epsilon_0=... --W=... --W_mp=...
--zeta=... --config=file` so a **single built binary** can sweep
those knobs. Unit tests construct their own `ElqtpConfig` and ignore
CLI values.

```bash
/tmp/lqarp-check /workspace/data/channel_db --beta_1=0.5 --beta_2=1.0
```

## Run the checks

```bash
g++ -std=c++17 -O2 -I contrib/elqtp/model -I contrib/elqtp/examples \
  contrib/elqtp/model/bellhop-data-loader.cc \
  contrib/elqtp/model/channel-gate.cc \
  contrib/elqtp/model/link-quality.cc \
  contrib/elqtp/model/lqarp-protocol.cc \
  contrib/elqtp/model/elqtp-protocol.cc \
  contrib/elqtp/model/rlor-inspired-protocol.cc \
  contrib/elqtp/model/gauss-markov.cc \
  contrib/elqtp/model/elqtp-run-config.cc \
  contrib/elqtp/examples/lqarp-unit-check-standalone.cc \
  -o /tmp/lqarp-check
/tmp/lqarp-check /workspace/data/channel_db

# Step 39 |dSNR/drange| over the January/July grids (no ns-3):
g++ -std=c++17 -O2 -I contrib/elqtp/model \
  contrib/elqtp/model/bellhop-data-loader.cc \
  contrib/elqtp/examples/snr-gradient-scan.cc \
  -o /tmp/snr-gradient-scan
/tmp/snr-gradient-scan /workspace/data/channel_db
```

## Scenario I (LQARP, stationary)

```bash
# from the ns-3 tree (contrib/elqtp is symlinked):
./ns3 run "scenario-i-lqarp --dataDir=/workspace/data/channel_db"
```

Defaults: N=20 AUVs + 1 sink, T_sim=1600 s, one 400-bit packet every
30 s per AUV, seed 20260921, ConstantPositionMobilityModel,
`--protocol=lqarp`, sink acoustic query depth 50 m (kinematic z = 5 m).
`--protocol=elqtp|rlor|periodic` runs the other three on the same
harness. `--diagCandidates` is the Step 25 N_range/N_depth check.
Report: `results/scenario-i-lqarp.txt`.

## Scenario II (linear uniform drift)

```bash
./ns3 run "scenario-i-lqarp --dataDir=/workspace/data/channel_db \
  --scenario=ii --nAuv=40 --seed=20260921 --driftSpeed=2 \
  --protocol=lqarp --quiet --out=/workspace/results/scenario-ii-lqarp.txt"

./ns3 run "scenario-i-lqarp --dataDir=/workspace/data/channel_db \
  --scenario=ii --nAuv=40 --seed=20260921 --driftSpeed=2 \
  --protocol=elqtp --beta_1=0 --beta_2=0 --quiet \
  --out=/workspace/results/scenario-ii-elqtp.txt"
```

AUVs use `ns3::ConstantVelocityMobilityModel` with shared horizontal
`v_drift` (`v_cmd=0`); the sink stays fixed. E-LQTP is the validated
operating point (`beta_1`/`beta_2` default to 0.0, event trigger on,
EKF ticks). `beta_1=beta_2=1` is the diagnostic placeholder from
Steps 53 / 60, not the paper default. Until a neighbor HELLO has
been received, `c_drift = c_del` (no fabricated `pdot_j = 0`).
Default volume-exit policy is
`--boundary=remove`: an AUV that leaves `[0,6000]²` is taken out
(OUT_OF_ENVELOPE); in-flight packets at that node fail as
LOST_NODE_EXIT. `--boundary=open` is the HOLD ablation. Direction is
stream-2 uniform azimuth, reported per seed.

Headline five-seed × drift tables at the validated \(\beta=0/0\)
point (Steps 69–70), IEEE Fig. A/B, and CSV:

```bash
python3 scripts/scenario2_headline.py --step all --jobs 4
```

Writes `results/scenario2_headline_data.csv` and
`results/figs/scenario2_headline_figA_protocol.{pdf,eps}`,
`results/figs/scenario2_headline_figB_drift.{pdf,eps}`. Report:
`results/STEP68_70.md`. The older `scripts/scenario2_sweep.py` /
`results/scenario2_multiseed_data.csv` pair is the Step 53–55
diagnostic artifact at \(\beta_1=\beta_2=1\).

## Scenario III (Rankine eddy + Gauss-Markov)

σ_z=0 is permanent (geostrophic / horizontal; SPEC Part 9).
Kinematics (radial vs tangential):

```bash
./ns3 run "scenario-i-lqarp --diagKinematics --nAuv=40 --seed=20260921 \
  --driftSpeed=2 --out=/workspace/results/STEP59_RADIAL.md"
```

Headline four-protocol comparison (Step 70) at the validated
\(\beta_1=\beta_2=0\) default, same seeds / N / T_sim as Scenario II:

```bash
./ns3 run "scenario-i-lqarp --dataDir=/workspace/data/channel_db \
  --scenario=iii --nAuv=40 --simTime=600 --seed=20260921 \
  --driftSpeed=2 --protocol=elqtp --beta_1=0 --beta_2=0 --quiet \
  --out=/workspace/results/scenario-iii-elqtp.txt"

python3 scripts/scenario3_headline.py --jobs 4
```

Writes `results/scenario3_headline_data.csv`. Report:
`results/STEP68_70.md`. The older `scripts/scenario3_compare.py` /
`results/scenario3_multiseed_data.csv` pair is the Step 60
diagnostic artifact at \(\beta_1=\beta_2=1\).

Sign-persistence + β₁=0 / β₂ sweep (Steps 61–62):

```bash
./ns3 run "scenario-i-lqarp --diagKinematics --nAuv=40 --seed=20260921 \
  --driftSpeed=2 --out=/workspace/results/STEP61_PERSISTENCE.md"
python3 scripts/scenario3_beta2_sweep.py --jobs 4
python3 scripts/scenario3_beta1_sweep.py --jobs 4
```
