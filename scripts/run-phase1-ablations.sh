#!/usr/bin/env bash
# Phase 1 appendix: slotted vs unslotted ALOHA, Tmax sweep, multipath-margin
# sensitivity, and 6/12/16-node scale. 20 seeds, 95% CIs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_DIR="${NS3_PREFIX:-${ROOT}/opt}/ns-allinone-3.41/ns-3.41"
SCRATCH="${NS3_DIR}/scratch/usv-auv-phase1"
OUT="${ROOT}/results/phase1"
ABL="${OUT}/ablations"
NSEEDS="${ABLATION_SEEDS:-20}"
SIMSTOP="${SIMSTOP:-240}"
JOBS="${JOBS:-$(nproc)}"
PAR="${PHASE1_PAR:-4}"
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"

if [[ ! -x "${NS3_DIR}/ns3" ]]; then
  echo "NS-3 is not installed. Run scripts/install-ns3-aqua-sim.sh first." >&2
  exit 1
fi

mkdir -p "${SCRATCH}" "${OUT}" "${ABL}"
cp -f "${ROOT}/phase1/"*.h "${ROOT}/phase1/"*.cc "${SCRATCH}/"

echo "==> Building usv-auv-phase1"
cd "${NS3_DIR}"
./ns3 build usv-auv-phase1 -j"$(nproc)"
BIN="$(find "${NS3_DIR}/build/scratch/usv-auv-phase1" -type f -name '*usv-auv-phase1*' ! -name '*.o' | head -1)"
echo "==> Binary ${BIN}"

if [[ "${PAR}" -gt "${JOBS}" ]]; then
  PAR="${JOBS}"
fi

JOBS_FILE="${ABL}/jobs.txt"
python3 - <<PY
from pathlib import Path
nseeds = int("${NSEEDS}")
jobs = []
# unique (seed, mode, mac, nAuv, tMax, margin)
def add(seed, mode, mac, nauv, tmax, margin):
    jobs.append((seed, mode, mac, nauv, tmax, margin))

for s in range(1, nseeds + 1):
    add(s, "periodic", "unslotted", 11, 25, 30)
    add(s, "event", "unslotted", 11, 25, 30)
    add(s, "periodic", "slotted", 11, 25, 30)
    add(s, "event", "slotted", 11, 25, 30)
    add(s, "event", "unslotted", 11, 10, 30)
    add(s, "event", "unslotted", 11, 15, 30)
    add(s, "event", "unslotted", 11, 40, 30)
    add(s, "periodic", "unslotted", 11, 25, 20)
    add(s, "event", "unslotted", 11, 25, 20)
    add(s, "periodic", "unslotted", 11, 25, 40)
    add(s, "event", "unslotted", 11, 25, 40)
    add(s, "periodic", "unslotted", 5, 25, 30)
    add(s, "event", "unslotted", 5, 25, 30)
    add(s, "periodic", "unslotted", 15, 25, 30)
    add(s, "event", "unslotted", 15, 25, 30)

# de-duplicate
seen = set()
uniq = []
for j in jobs:
    if j not in seen:
        seen.add(j)
        uniq.append(j)
path = Path("${JOBS_FILE}")
path.write_text("\n".join(" ".join(map(str, j)) for j in uniq) + "\n")
print("jobs", len(uniq))
PY

run_job () {
  local seed="$1" mode="$2" mac="$3" nauv="$4" tmax="$5" margin="$6"
  local tag="s${seed}_${mode}_${mac}_n${nauv}_tmax${tmax}_m${margin}"
  local dest="${ABL}/${tag}"
  mkdir -p "${dest}"
  if [[ -f "${dest}/metrics.csv" ]]; then
    echo "skip ${tag}"
    return 0
  fi
  echo "run ${tag}"
  local tmin=5
  "${BIN}" --beaconMode="${mode}" --simStop="${SIMSTOP}" --nAuv="${nauv}" \
    --outDir="${dest}" --seed="${seed}" --verboseTraces=0 \
    --mac="${mac}" --tMin="${tmin}" --tMax="${tmax}" --multipathMargin="${margin}" \
    > "${dest}/run.log" 2>&1
}

export -f run_job
export BIN SIMSTOP ABL

echo "==> Ablation batch ($(wc -l < "${JOBS_FILE}") jobs, PAR=${PAR})"
xargs -n 6 -P "${PAR}" bash -c 'run_job "$@"' _ < "${JOBS_FILE}"

python3 - <<PY
import csv, glob, os
root = "${ABL}"
out = os.path.join("${OUT}", "ablation_metrics.csv")
rows, header = [], None
for path in sorted(glob.glob(os.path.join(root, "*/metrics.csv"))):
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        header = r.fieldnames
        rows.extend(list(r))
clean = [row for row in rows if row.get("seed") not in (None, "seed")]
if not clean:
    raise SystemExit("no ablation metrics")
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=header)
    w.writeheader()
    w.writerows(clean)
print("wrote", out, "n=", len(clean))
PY

python3 "${ROOT}/phase1/analyze_phase1.py" "${OUT}"
echo "==> Ablation artifacts in ${OUT}"
ls -l "${OUT}/ablation_metrics.csv" "${OUT}/phase1_ablations.png" "${OUT}/ablation_ci_table.md"
