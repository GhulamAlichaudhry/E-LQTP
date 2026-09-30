#!/usr/bin/env bash
# Install NS-3.41 and integrate Aqua-Sim Next Generation (underwater acoustic
# network simulator) as an NS-3 module, then build both together.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPT_DIR="${NS3_PREFIX:-${ROOT}/opt}"
NS_VERSION="3.41"
AQUA_REPO="https://github.com/rmartin5/aqua-sim-ng.git"
TARBALL_URL="https://www.nsnam.org/releases/ns-allinone-${NS_VERSION}.tar.bz2"
NS3_DIR="${OPT_DIR}/ns-allinone-${NS_VERSION}/ns-${NS_VERSION}"
JOBS="${JOBS:-$(nproc)}"
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"

log() { printf '\n==> %s\n' "$*"; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

log "Checking toolchain"
need_cmd g++
need_cmd python3
need_cmd cmake
need_cmd git
need_cmd wget
need_cmd tar

g++ --version | head -1
cmake --version | head -1

if [[ "$(id -u)" -eq 0 ]]; then
  APT=(apt-get)
else
  APT=(sudo apt-get)
fi

log "Installing Ubuntu packages (idempotent)"
"${APT[@]}" update -qq
DEBIAN_FRONTEND=noninteractive "${APT[@]}" install -y --no-install-recommends \
  g++ python3 cmake ninja-build git wget ca-certificates bzip2 \
  libsqlite3-dev libxml2-dev gsl-bin libgsl-dev pkg-config

mkdir -p "${OPT_DIR}" "${OPT_DIR}/downloads"

TARBALL="${OPT_DIR}/downloads/ns-allinone-${NS_VERSION}.tar.bz2"
if [[ ! -f "${TARBALL}" ]]; then
  log "Downloading NS-${NS_VERSION}"
  wget -c --progress=dot:giga -O "${TARBALL}" "${TARBALL_URL}"
else
  log "Using cached NS-${NS_VERSION} tarball"
fi

if [[ ! -d "${NS3_DIR}" ]]; then
  log "Extracting NS-${NS_VERSION} into ${OPT_DIR}"
  tar xf "${TARBALL}" -C "${OPT_DIR}"
fi

if [[ ! -d "${NS3_DIR}/src/aqua-sim-ng/.git" ]]; then
  log "Cloning Aqua-Sim-NG into NS-3 src/"
  git clone --depth 1 "${AQUA_REPO}" "${NS3_DIR}/src/aqua-sim-ng"
else
  log "Aqua-Sim-NG already present"
fi

CMAKE_LIST="${NS3_DIR}/src/aqua-sim-ng/CMakeLists.txt"
if grep -q 'NAME bMAC' "${CMAKE_LIST}" && ! grep -q 'Skip it so' "${CMAKE_LIST}"; then
  log "Disabling NetAnim-only bMAC example (no Qt required)"
  python3 - "${CMAKE_LIST}" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
old = """build_lib_example(
    NAME bMAC
    SOURCE_FILES examples/bMAC.cc
    LIBRARIES_TO_LINK ${libnetwork}
                      ${libenergy}
                      ${libmobility}
                      ${libapplications}
                      ${libnetanim}
                      ${libaqua-sim-ng}
)
"""
new = """# bMAC depends on the NetAnim module (optional Qt visualizer). Skip it so
# Aqua-Sim-NG can be built without extra GUI libraries.
# build_lib_example(
#     NAME bMAC
#     SOURCE_FILES examples/bMAC.cc
#     LIBRARIES_TO_LINK ${libnetwork}
#                       ${libenergy}
#                       ${libmobility}
#                       ${libapplications}
#                       ${libnetanim}
#                       ${libaqua-sim-ng}
# )
"""
if old in text:
    p.write_text(text.replace(old, new, 1))
    print("patched CMakeLists.txt")
else:
    print("bMAC block already patched or not found")
PY
fi

log "Configuring NS-3 with Aqua-Sim-NG (compiler ${CC}/${CXX})"
cd "${NS3_DIR}"

# Keep ELQTP out of Aqua-Sim's tree: symlink workspace contrib/ into ns-3 contrib/.
mkdir -p "${NS3_DIR}/contrib"
ln -sfn "${ROOT}/contrib/elqtp" "${NS3_DIR}/contrib/elqtp"

# Drop a previous Clang/CMake cache if present so g++ is re-detected.
rm -rf cmake-cache
./ns3 configure \
  --build-profile=optimized \
  --enable-examples \
  --disable-python \
  --disable-werror \
  --enable-modules=aqua-sim-ng,applications,mobility,energy,network,internet,elqtp

log "Building NS-3 + Aqua-Sim-NG (${JOBS} jobs)"
# Build the BroadcastMAC example and its module dependencies (not every NS-3 example).
./ns3 build broadcastMAC_example bellhop-data-loader-check lqarp-unit-check -j"${JOBS}"

log "Recording integration status"
mkdir -p "${ROOT}/results"
{
  echo "ns-3 version: ${NS_VERSION}"
  echo "aqua-sim-ng commit: $(git -C "${NS3_DIR}/src/aqua-sim-ng" rev-parse --short HEAD)"
  echo "aqua-sim-ng module: enabled"
  echo "ns3 dir: ${NS3_DIR}"
  ./ns3 show config 2>/dev/null | grep -E 'aqua-sim|Enabled|profile' || true
} | tee "${ROOT}/results/integration-status.txt"

log "Install complete"
echo "Run an example with: ${ROOT}/scripts/run-example.sh"
