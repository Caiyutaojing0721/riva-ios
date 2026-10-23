#!/usr/bin/env bash
#
# mkiosroot.sh  --  Build the riva iOS root filesystem image
# ==========================================================
#
# ios-sweet builds an HFS+ (or APFS) image containing the *unmodified* iPhone
# userland (launchd, backboardd, SpringBoard, frameworks, apps) and flashes it
# to the userdata partition. For riva the steps are identical in spirit, but:
#   * the source IPSW must be an iOS build whose shared cache + dyld are
#     arm64 (A9+); riva is arm64 (Cortex-A53), so iOS 14/15/16 userland is the
#     candidate target (NOT the iPhone X 16.7.16 that sweet uses -- pick an
#     arm64-only build, e.g. an iPhone 8 / SE2 / iPad baseline).
#   * storage is eMMC userdata (sparse ext4 wrapper around the HFS+ volume),
#     not UFS. flash_ios.sh handles the eMMC write.
#
# Prereqs (run on a Linux PC, sudo needed for loop devices / mtools / hfsprogs):
#   apfs-fuse  hfsprogs  mtools  simg2img/img2simg  p7zip  openssl
#
# Usage:
#   sudo ./mkiosroot.sh <iPhone_xxx_xxx_iOS_xx.ipsw> out/ios-root.simg
#
set -euo pipefail

IPSW="${1:-}"
OUT="${2:-out/ios-root.simg}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -z "$IPSW" ]; then
  echo "usage: sudo $0 <firmware.ipsw> [out.simg]"
  exit 1
fi

echo "[+] Extracting IPSW (it's a zip) ..."
mkdir -p "$WORK/ipsw"
7z x -y "$IPSW" -o"$WORK/ipsw" >/dev/null

# iOS 10+ store the OS in a DMG inside the IPSW (098-...dmg / 058-...dmg)
DMG=$(ls "$WORK/ipsw"/*.dmg 2>/dev/null | head -1)
echo "[+] Found DMG: $DMG"
mkdir -p "$WORK/mnt"
if command -v apfs-fuse >/dev/null 2>&1; then
  apfs-fuse "$DMG" "$WORK/mnt"
else
  # older HFS DMG
  sudo mount -o loop,ro -t hfsplus "$DMG" "$WORK/mnt"
fi

echo "[+] Building HFS+ root volume from /mnt ..."
# NOTE: this is the ios-sweet "mkiosroot.sh" step ported to riva. The real
# tooling copies /System, /Library, /usr, the dyld shared cache, and applies
# sweet-root-tweaks (skip Setup, mark activated). Those tweaks must be riva-
# adapted (different device identity, different display panel name).
hdiutil_equivalent() {
  echo "  -> copy System/Library/usr + dyld shared cache"
  echo "  -> apply riva-root-tweaks.py (TODO: port from ios-sweet)"
}
hdiutil_equivalent

echo "[+] Wrapping HFS+ volume into an eMMC-sparce userdata image ..."
# The output is what flash_ios.sh writes to the 'userdata' partition.
# img2simg converts a raw image to the Android sparse format the partition expects.
echo "  -> img2simg root.hfs.raw $OUT"
echo "[+] DONE (scaffold). Wire in the real copy/tweak steps above."

# After building, sign/hash and hand off to flash_ios.sh:
echo "[*] Next: python3 tools/mkadt-riva.py && \\"
echo "        python3 tools/mkpayload-riva.py --kernel xnu.bin --adt device/riva-adt.dtb -o payload.bin && \\"
echo "        cd flash && ./build_bootimg.sh && ./flash_ios.sh"
