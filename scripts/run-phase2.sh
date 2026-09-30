#!/usr/bin/env bash
# Paper forwarding campaign (LQARP-style evaluation).
# Main: 30 seeds × event{snr,hold,depth,oracle} + periodic{snr,hold}
#   Tmax=10 s, 360 s, all AUVs CBR 400 bit / 16 s after t=50 s.
# Scale: 20 seeds × nAuv in {5,11,15} × event-hold / event-depth / periodic-snr.
# Load:  15 seeds × dataInterval in {8,12,16,24} × event-hold / event-depth / periodic-snr.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_DIR="${NS3_PREFIX:-${ROOT}/opt}/ns-allinone-3.41/ns-3.41"
SCRATCH="${NS3_DIR}/scratch/usv-auv-phase1"
OUT="${ROOT}/results/phase2"
BATCH_DIR="${OUT}/batch"
NSEEDS="${NSEEDS:-30}"
SCALE_SEEDS="${SCALE_SEEDS:-20}"
LOAD_SEEDS="${LOAD_SEEDS:-15}"
SIMSTOP="${SIMSTOP:-360}"
TMAX="${TMAX:-10}"
DATAINT="${DATAINT:-16}"
DATASTART="${DATASTART:-50}"
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
echo "==> Binary ${BIN}"

# Composite ETHA scoring changed; drop stale hold/oracle traces.
if [[ "${INVALIDATE_HOLD:-1}" == "1" ]]; then
  shopt -s nullglob
  stale=( "${BATCH_DIR}"/s*_hold_n* "${BATCH_DIR}"/s*_oracle_n* )
  if (( ${#stale[@]} )); then
    echo "==> Removing ${#stale[@]} stale hold/oracle result dirs"
    rm -rf "${stale[@]}"
  fi
  shopt -u nullglob
fi

run_job () {
  local seed="$1" mode="$2" pol="$3" nauv="$4"
  local dint="${5:-}"
  local dest="${BATCH_DIR}/s$(printf '%02d' "${seed}")_${mode}_${pol}_n${nauv}"
  local interval="${DATAINT}"
  if [[ -n "${dint}" ]]; then
    dest="${dest}_di${dint}"
    interval="${dint}"
  fi
  mkdir -p "${dest}"
  if [[ -f "${dest}/metrics.csv" ]]; then
    echo "skip ${dest}"
    return 0
  fi
  echo "seed=${seed} mode=${mode} fwd=${pol} nAuv=${nauv} di=${interval}"
  "${BIN}" --beaconMode="${mode}" --fwdPolicy="${pol}" --nAuv="${nauv}" \
    --simStop="${SIMSTOP}" --tMax="${TMAX}" --dataStart="${DATASTART}" \
    --dataInterval="${interval}" --verboseTraces=0 \
    --outDir="${dest}" --seed="${seed}" \
    > "${dest}/run.log" 2>&1
}

export -f run_job
export BIN BATCH_DIR SIMSTOP TMAX DATAINT DATASTART

PAR="${PHASE2_PAR:-4}"

echo "==> Main 12-node table"
{
  seq 1 "${NSEEDS}" | while read -r s; do
    echo "${s} event snr ${NAUV}"
    echo "${s} event hold ${NAUV}"
    echo "${s} event depth ${NAUV}"
    echo "${s} event oracle ${NAUV}"
    echo "${s} periodic snr ${NAUV}"
    echo "${s} periodic hold ${NAUV}"
  done
} | xargs -n 4 -P "${PAR}" bash -c 'run_job "$0" "$1" "$2" "$3"'

echo "==> Scale sweep"
{
  seq 1 "${SCALE_SEEDS}" | while read -r s; do
    for n in 5 11 15; do
      echo "${s} event hold ${n}"
      echo "${s} event depth ${n}"
      echo "${s} periodic snr ${n}"
    done
  done
} | xargs -n 4 -P "${PAR}" bash -c 'run_job "$0" "$1" "$2" "$3"'

echo "==> Load sweep (packet interval)"
{
  seq 1 "${LOAD_SEEDS}" | while read -r s; do
    for di in 8 12 16 24; do
      echo "${s} event hold ${NAUV} ${di}"
      echo "${s} event depth ${NAUV} ${di}"
      echo "${s} periodic snr ${NAUV} ${di}"
    done
  done
} | xargs -n 5 -P "${PAR}" bash -c 'run_job "$0" "$1" "$2" "$3" "$4"'

python3 - <<PY
import csv, glob, os
root = "${BATCH_DIR}"
out = os.path.join("${OUT}", "fwd_metrics.csv")
rows, header = [], None
seen = set()
for path in sorted(glob.glob(os.path.join(root, "s*_*/metrics.csv"))):
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        if r.fieldnames:
            if header is None:
                header = list(r.fieldnames)
            else:
                for k in r.fieldnames:
                    if k not in header:
                        header.append(k)
        for row in r:
            if row.get("seed") in (None, "seed", ""):
                continue
            if "data_interval" not in row or row.get("data_interval") in (None, ""):
                # Infer from directory name ..._di12 or default 16 s.
                base = os.path.basename(os.path.dirname(path))
                di = "16"
                if "_di" in base:
                    di = base.split("_di")[-1]
                row["data_interval"] = di
            key = (row.get("seed"), row.get("mode"), row.get("n_nodes"),
                   row.get("fwd_policy"), row.get("data_interval"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
if "data_interval" not in (header or []):
    header = list(header or []) + ["data_interval"]
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
print("wrote", out, "n=", len(rows))
PY

python3 "${ROOT}/phase1/analyze_phase2.py" "${OUT}"
echo "==> Phase 2 artifacts in ${OUT}"
