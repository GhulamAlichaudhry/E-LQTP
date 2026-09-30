#!/usr/bin/env bash
# Download Porter's Acoustics Toolbox (OALIB) and compile bellhop.exe.
# The toolbox is GPL-3.0. Source is not vendored in git (opt/ is gitignored).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OPT="${ROOT}/opt"
AT="${OPT}/at"
ZIP_URL="${BELLHOP_AT_URL:-http://oalib.hlsresearch.com/AcousticsToolbox/at_2024_12_25.zip}"
ZIP_PATH="${OPT}/at_2024_12_25.zip"

mkdir -p "${OPT}"

if [[ ! -x "${AT}/Bellhop/bellhop.exe" ]]; then
  if [[ ! -f "${ZIP_PATH}" ]]; then
    echo "Downloading Acoustics Toolbox from ${ZIP_URL}"
    curl -L --fail --max-time 120 -o "${ZIP_PATH}" "${ZIP_URL}"
  fi
  if [[ ! -d "${AT}/Bellhop" ]]; then
    unzip -q -o "${ZIP_PATH}" -d "${OPT}"
  fi
fi

if ! command -v gfortran >/dev/null 2>&1; then
  echo "gfortran is required (sudo apt-get install gfortran)" >&2
  exit 1
fi

export FC=gfortran
export FFLAGS="-march=native -O2 -std=gnu -Wno-tabs -I../misc -I../tslib"

make -C "${AT}/misc" all
make -C "${AT}/Bellhop" all
mkdir -p "${AT}/bin"
cp -p "${AT}/Bellhop/bellhop.exe" "${AT}/bin/bellhop.exe"

echo "bellhop.exe -> ${AT}/Bellhop/bellhop.exe"
"${AT}/Bellhop/bellhop.exe" 2>/dev/null | head -3 || true
