#!/usr/bin/env bash
#
# riva-log-pull.sh  --  Pull the riva XNU early-boot log ring
# ============================================================
#
# The shim reserves a 4 MiB persistent log ring at the very end of the userdata
# partition (same idea as ios-sweet's sweet-log-pull.sh) so you can read kernel
# output without photographing the screen. Boot into OrangeFox / TWRP recovery,
# then run this with the device connected via ADB.
#
set -euo pipefail
OUT="${1:-riva-boot.log}"
LOG_OFF="${RIVA_LOG_OFF:-}"
DEV="/dev/block/by-name/userdata"

echo "[+] Waiting for adb device ..."
adb wait-for-recovery 2>/dev/null || adb wait-for-device

# If the device doesn't expose the offset, fall back to dumping the last 4 MiB.
if [ -z "$LOG_OFF" ]; then
  SZ=$(adb shell blockdev --getsize64 "$DEV" 2>/dev/null || echo 0)
  if [ "$SZ" -gt 0 ] 2>/dev/null; then
    LOG_OFF=$((SZ - 4*1024*1024))
  else
    echo "[!] Cannot determine userdata size; pass RIVA_LOG_OFF=0x... explicitly"
    exit 1
  fi
fi

echo "[+] Dumping 4 MiB log ring @ offset $LOG_OFF -> $OUT"
adb shell "dd if=$DEV bs=1M skip=$((LOG_OFF/1048576)) count=4 2>/dev/null" > "$OUT"
echo "[+] Wrote $OUT ($(wc -c < "$OUT") bytes)"
echo "[+] Last lines:"
tail -n 40 "$OUT"
