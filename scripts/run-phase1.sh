#!/usr/bin/env bash
# Sync Phase 1 sources into NS-3 scratch, build, smoke-test, then 30-seed batch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_DIR="${NS3_PREFIX:-${ROOT}/opt}/ns-allinone-3.41/ns-3.41"
SCRATCH="${NS3_DIR}/scratch/usv-auv-phase1"
OUT="${ROOT}/results/phase1"
BATCH_DIR="${OUT}/batch"
NSEEDS="${NSEEDS:-30}"
SIMSTOP="${SIMSTOP:-240}"
NAUV="${NAUV:-11}"
JOBS="${JOBS:-$(nproc)}"
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"

if [[ ! -x "${NS3_DIR}/ns3" ]]; then
  echo "NS-3 is not installed. Run scripts/install-ns3-aqua-sim.sh first." >&2
  exit 1
fi

mkdir -p "${SCRATCH}" "${OUT}" "${BATCH_DIR}"
cp -f "${ROOT}/phase1/"*.h "${ROOT}/phase1/"*.cc "${SCRATCH}/"

echo "==> Building usv-auv-phase1"
cd "${NS3_DIR}"
./ns3 build usv-auv-phase1 -j"$(nproc)"

BIN="$(find "${NS3_DIR}/build/scratch/usv-auv-phase1" -type f -name '*usv-auv-phase1*' ! -name '*.o' | head -1)"
if [[ -z "${BIN}" || ! -x "${BIN}" ]]; then
  echo "Could not find built binary under build/scratch/usv-auv-phase1" >&2
  find "${NS3_DIR}/build/scratch" -type f | head
  exit 1
fi
echo "==> Binary ${BIN}"

run_one () {
  local mode="$1" seed="$2" dest="$3" verbose="$4"
  mkdir -p "${dest}"
  "${BIN}" --beaconMode="${mode}" --simStop="${SIMSTOP}" --nAuv="${NAUV}" \
    --outDir="${dest}" --seed="${seed}" --verboseTraces="${verbose}"
}

echo "==> Smoke seed=1 (verbose traces)"
run_one periodic 1 "${OUT}" 1
run_one event 1 "${OUT}" 1

echo "==> Batch ${NSEEDS} seeds × 2 modes (ALOHA, ${NAUV}+1 nodes)"
run_seed_mode () {
  local seed="$1" mode="$2"
  local dest="${BATCH_DIR}/seed$(printf '%02d' "${seed}")_${mode}"
  mkdir -p "${dest}"
  if [[ -f "${dest}/metrics.csv" ]]; then
    echo "skip existing ${dest}"
    return 0
  fi
  echo "seed=${seed} mode=${mode}"
  "${BIN}" --beaconMode="${mode}" --simStop="${SIMSTOP}" --nAuv="${NAUV}" \
    --outDir="${dest}" --seed="${seed}" --verboseTraces=0 \
    > "${dest}/run.log" 2>&1
}

export -f run_seed_mode
export BIN SIMSTOP NAUV BATCH_DIR

# Bound parallelism: each run is a full NS-3 process.
PAR="${PHASE1_PAR:-4}"
if [[ "${PAR}" -gt "${JOBS}" ]]; then
  PAR="${JOBS}"
fi

seq 1 "${NSEEDS}" | while read -r s; do
  echo "${s} periodic"
  echo "${s} event"
done | xargs -n 2 -P "${PAR}" bash -c 'run_seed_mode "$0" "$1"'

python3 - <<PY
import csv, glob, os
root = "${BATCH_DIR}"
out = os.path.join("${OUT}", "batch_metrics.csv")
rows = []
header = None
for path in sorted(glob.glob(os.path.join(root, "seed*_*/metrics.csv"))):
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        header = r.fieldnames
        rows.extend(list(r))
if not rows:
    raise SystemExit("no batch metrics.csv files found")
# Deduplicate header rows accidentally concatenated
clean = [row for row in rows if row.get("seed") not in (None, "seed")]
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=header)
    w.writeheader()
    w.writerows(clean)
print("wrote", out, "n=", len(clean))
PY

python3 "${ROOT}/phase1/analyze_phase1.py" "${OUT}"
echo "==> Phase 1 artifacts in ${OUT}"
ls -l "${OUT}" "${OUT}/batch" | head -50
