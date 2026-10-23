#!/usr/bin/env bash
#
# build_bootimg.sh  --  Wrap the riva shim + payload into shim-boot.img
# =====================================================================
# Uses the exact load addresses from the stock riva boot.img (bootimg.cfg):
#   pagesize      0x800
#   kernel addr   0x80008000   -> base 0x80000000, kernel_offset 0x8000
#   ramdisk addr  0x81000000   -> ramdisk_offset 0x1000000
#   second addr   0x80f00000   -> second_offset 0xf00000
#   tags addr     0x80000100   -> tags_offset 0x100
# The ramdisk slot carries payload.bin (XNU kernel + ADT + boot-args) which the
# shim scans for. Output: flash/shim-boot.img
set -euo pipefail
cd "$(dirname "$0")/.."

SHIM_ELF="${1:-shim/out/shim.elf}"
PAYLOAD="${2:-payload.bin}"
OUT="${3:-flash/shim-boot.img}"

if [ ! -f "$SHIM_ELF" ]; then
  echo "[!] $SHIM_ELF missing. Run: (cd shim && ./build.sh)"
  exit 1
fi
if [ ! -f "$PAYLOAD" ]; then
  echo "[!] $PAYLOAD missing. Run: python3 tools/mkpayload-riva.py ..."
  exit 1
fi

echo "[+] Building shim-boot.img (riva load addresses)"
mkbootimg \
  --kernel "$SHIM_ELF" \
  --ramdisk "$PAYLOAD" \
  --base 0x80000000 \
  --kernel_offset 0x8000 \
  --ramdisk_offset 0x1000000 \
  --second_offset 0xf00000 \
  --tags_offset 0x100 \
  --pagesize 0x800 \
  --cmdline "riva-shim earlycon=msm_hsl_uart,0x78B0000" \
  --os_version 7.1.2 \
  --os_patch_level 2018-10 \
  -o "$OUT"

echo "[+] Wrote $OUT"
echo "[+] Flash it: cd flash && ./flash_ios.sh out/ios-root.simg shim-boot.img"
