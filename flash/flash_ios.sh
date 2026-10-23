#!/usr/bin/env bash
#
# flash_ios.sh  --  Flash the riva iOS bring-up image (TEMPORARY boot)
# ====================================================================
# Modeled on ios-sweet's "fastboot flash userdata ... ; fastboot boot shim".
# We DO NOT flash the bootloader, modem, recovery, or persist -- those stay
# stock Xiaomi-signed. iOS runs from the userdata partition (an HFS+ volume
# wrapped in a sparse ext4 image) and the shim is booted temporarily with
# `fastboot boot`, so the stock Android boot is one reboot away (no brick).
#
# Prereqs: riva with UNLOCKED bootloader, fastboot, the iOS root image
# (out/ios-root.simg from tools/mkiosroot.sh) and shim-boot.img
# (flash/build_bootimg.sh).
set -euo pipefail
cd "$(dirname "$0")/.."

STOCK="${RIVA_STOCK:-../riva_images_V10.1.1.0.NCKCNFI_20181019.0000.00_7.1_cn/images}"
ROOT_IMG="${1:-out/ios-root.simg}"
SHIM_IMG="${2:-shim-boot.img}"

FB="fastboot"
echo "=== riva iOS flash (temporary bring-up) ==="
"$FB" getvar product 2>&1 | grep -q "^product: riva" || {
  echo "[!] Device is not riva (or not in fastboot). Aborting."; exit 1; }

# 0) (Recommended once) back up calibration so you can always restore stock.
if [ "${BACKUP:-0}" = "1" ]; then
  echo "[+] Backing up persist/modem/fsg (stock ROM present at $STOCK)"
  "$FB" pull /dev/block/by-name/persist  persist.img 2>/dev/null || true
  "$FB" pull /dev/block/by-name/modemst1 modemst1.img 2>/dev/null || true
  "$FB" pull /dev/block/by-name/fsg      fsg.img      2>/dev/null || true
fi

# 1) Write the iOS root filesystem to userdata (eMMC, sparse image).
echo "[+] Flashing iOS root -> userdata ($ROOT_IMG)"
"$FB" flash userdata "$ROOT_IMG"

# 2) Temporarily boot the shim. Nothing is written to the boot partition.
echo "[+] Temporarily booting shim ($SHIM_IMG) -- stock boot untouched"
"$FB" boot "$SHIM_IMG"

echo "[+] Done. First boot can take several minutes (software render)."
echo "    To return to stock: reboot; the original boot/recovery are intact."
echo "    Pull kernel log: tools/riva-log-pull.sh  (from recovery)"
