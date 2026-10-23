#!/usr/bin/env bash
#
# build.sh -- compile the riva shim into shim-bin + wrap as shim-boot.img
# ======================================================================
# Requires an aarch64 bare-metal (or linux-gnu) toolchain. The wrapper step
# calls mkbootimg so the result is an Android boot.img v2 that ABL can
# `fastboot boot`. The ramdisk slot carries payload.bin (kernel+ADT+bootargs),
# which shim.c scans for.
set -euo pipefail
cd "$(dirname "$0")"

CC="${CC:-aarch64-none-elf-gcc}"
if ! command -v "$CC" >/dev/null 2>&1; then
  CC="aarch64-linux-gnu-gcc"
fi
if ! command -v "$CC" >/dev/null 2>&1; then
  echo "[!] No aarch64 toolchain found (tried aarch64-none-elf-gcc, aarch64-linux-gnu-gcc)."
  echo "    Install e.g. gcc-aarch64-linux-gnu, or export CC=/path/to/aarch64-gcc."
  exit 1
fi

echo "[+] Building shim with $CC"
"$CC" -nostdlib -ffreestanding -Wall -Wno-unused -c boot.S -o boot.o
"$CC" -nostdlib -ffreestanding -Wall -Wno-unused -c shim.c -o shim.o
"$CC" -nostdlib -ffreestanding -T linker.ld boot.o shim.o -o shim.elf

# Build a dummy ramdisk carrying the payload (kernel+ADT+bootargs).
# In the full flow, ../flash/build_bootimg.sh builds this from payload.bin.
mkdir -p out
cp shim.elf out/shim.elf
echo "[+] shim.elf built. Next: ../flash/build_bootimg.sh (assembles shim-boot.img)."
