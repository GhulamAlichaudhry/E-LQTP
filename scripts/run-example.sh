#!/usr/bin/env bash
# Run an Aqua-Sim-NG example on the integrated NS-3.41 tree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS3_DIR="${NS3_PREFIX:-${ROOT}/opt}/ns-allinone-3.41/ns-3.41"
RESULTS="${ROOT}/results"
EXAMPLE="${1:-broadcastMAC_example}"
shift || true

if [[ ! -x "${NS3_DIR}/ns3" ]]; then
  echo "NS-3 is not installed. Run scripts/install-ns3-aqua-sim.sh first." >&2
  exit 1
fi

mkdir -p "${RESULTS}"
cd "${NS3_DIR}"

ARGS=("$@")
if [[ ${#ARGS[@]} -eq 0 && "${EXAMPLE}" == "broadcastMAC_example" ]]; then
  ARGS=(--simStop=8 --nodes=3 --sinks=1)
fi

LOG="${RESULTS}/${EXAMPLE}.log"
echo "Running: ./ns3 run \"${EXAMPLE} ${ARGS[*]}\""
echo "Log: ${LOG}"

# shellcheck disable=SC2068
./ns3 run "${EXAMPLE} ${ARGS[*]}" 2>&1 | tee "${LOG}"

echo
echo "Example finished. Output saved to ${LOG}"
