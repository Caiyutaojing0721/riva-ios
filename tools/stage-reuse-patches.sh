#!/usr/bin/env bash
#
# stage-reuse-patches.sh -- Pull + stage the REUSABLE ios-sweet XNU patches
# =========================================================================
#
# ios-sweet's XNU port is 81 patches. RIVA doesn't need to reinvent the
# SoC-agnostic ones (crypto, filesystem/HFS, security/AMFI, sandbox, console
# logging, USB framework, staging scripts). This script fetches the reference
# repo and copies those reusable patches into xnu/patches/reuse/ so our CI
# (/.github/workflows/xnu.yml) can hand them to the builder alongside the
# riva-specific series.
#
# The "reuse" selection is driven by docs: RIVA_PORT_MAP.md (the per-patch
# disposition table). Only the BLOCKING riva-unique drivers (GICv2 / eMMC /
# MDSS display / Synaptics touch / PMI8950 PMIC) are intentionally EXCLUDED
# here -- those are the real port and must be authored as 00NN-riva-*.patch.
#
# Usage:
#   ./stage-reuse-patches.sh [ref-tag-or-sha]   (default: main)
# Re-run anytime to refresh the pinned set.

set -euo pipefail
cd "$(dirname "$0")/.."

REF="${1:-main}"
SRC="$(mktemp -d)"
trap 'rm -rf "$SRC"' EXIT
DEST="xnu/patches/reuse"
mkdir -p "$DEST"

echo "[+] Cloning reference repo @ $REF (shallow)..."
git clone -q --depth 1 --branch "$REF" \
    https://github.com/dipa-studio/ios-sweet "$SRC/sweet" || {
  echo "[!] Clone failed. Check network / tag name. Aborting."
  exit 1
}

# Patch families from RIVA_PORT_MAP.md marked "复用" (reuse).
# (KEYS = ios-sweet's own patch IDs; we map them to our naming below.)
REUSE_CATEGORIES=(
  "build|0001|0002|0005|0007|0009"        # build-system / clang compat
  "crypto|0013|0014|0020|0023|0027|0032|0033"  # RNG / AES / SHA / MD5 / BearSSL
  "security|0015|0025|0035|0036|0038|0050"     # trust-cache / AMFI / keystore / sandbox
  "fs|0021|0022|0024|0026|0029|0031|0037|0041|0052"  # ramdisk root / HFS / bindfs
  "log|0042|0043|0044|0047|0048|0051|0053|0057|0066|0067"  # console + crash logging
  "perf|0054|0055|0064"                     # samplers / work-interval
  "usb|0072|0073|0074|0075|0076|0077|0081"  # USB stack framework
  "misc|0018|0040|0045|0080"                # boot-cpu / watchdog / net-trace
)

copied=0
for entry in "${REUSE_CATEGORIES[@]}"; do
  label="${entry%%|*}"; ids="${entry#*|}"
  echo "-- category: $label --"
  for id in ${ids//|/ }; do
    pat="$SRC/sweet/xnu/patches/$(printf '%04d' "${id#0}")-"*".patch"
    # shellcheck disable=SC2086
    for f in $pat; do
      [ -e "$f" ] || { echo "   (missing $id)"; continue; }
      cp -f "$f" "$DEST/"
      copied=$((copied+1))
    done
  done
done

# Also copy the staging scripts (stage-*.sh) -- needed by the build.
cp -f "$SRC/sweet"/xnu/patches/stage-*.sh "$DEST/" 2>/dev/null || true

echo "[+] Staged $copied reusable patch files into $DEST/"
echo "    (plus any stage-*.sh). Excluded intentionally:"
echo "    0004/0006 (machine-config, pmap -> riva), 0016/0017 (DT/timer -> riva),"
echo "    0028/0030/0034/0069 (UFS -> riva eMMC), 0046/0056/0061/0079 (display -> riva MDSS),"
echo "    0058/0060/0062/0063/0071 (HID/touch -> riva Synaptics), 0065/0078 (SMP -> riva 4-core)," 
echo "    0059/0070 (identity/hibernate -> riva). Author these as 00NN-riva-*.patch."
echo
echo "Next: add the staged set to CI by ensuring they land in dxb/patches,"
echo "then run the riva-xnu-build workflow."