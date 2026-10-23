#!/usr/bin/env python3
"""
mkpayload-riva.py  --  Assemble the shim payload for Riva
================================================================

The riva shim (see ../shim/) is a tiny bare-metal loader that the Xiaomi ABL
jumps into. It expects a *payload* laid out as:

    [ 64-byte header ][ XNU Mach-O kernel ][ Apple Device Tree ][ boot-args ]

The header records byte offsets/sizes so the shim can find the kernel entry,
the ADT, and the boot-args string without guessing. This mirrors ios-sweet's
mkpayload.py but is self-contained and runs on Linux/Python3 with no extra deps.

Usage:
    python3 mkpayload-riva.py \
        --kernel xnu.bin --adt device/riva-adt.dtb \
        --bootargs "rd=ufsroot0 cpus=4 sw_render" \
        -o payload.bin

(Produce xnu.bin from the XNU build; adt via mkadt-riva.py.)
"""
import struct
import sys
import os

MAGIC = b"RIVAPLD1"
HDR_LEN = 64

def main():
    args = sys.argv[1:]
    kernel = adt = bootargs = None
    out = "payload.bin"
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--kernel": kernel = args[i + 1]; i += 2
        elif a == "--adt":   adt = args[i + 1]; i += 2
        elif a == "--bootargs": bootargs = args[i + 1]; i += 2
        elif a == "-o": out = args[i + 1]; i += 2
        else: i += 1

    if not (kernel and adt):
        print("usage: mkpayload-riva.py --kernel xnu.bin --adt riva-adt.dtb [--bootargs ...] -o payload.bin")
        sys.exit(1)
    bootargs = (bootargs or "rd=ufsroot0 cpus=4 sw_render ipanel=riva_hd").encode() + b"\x00"

    kd = open(kernel, "rb").read()
    ad = open(adt, "rb").read()

    # layout
    k_off = HDR_LEN
    a_off = k_off + len(kd)
    b_off = a_off + len(ad)
    total = b_off + len(bootargs)

    hdr = bytearray(HDR_LEN)
    hdr[0:8] = MAGIC
    struct.pack_into("<I", hdr, 8, 1)              # version
    struct.pack_into("<Q", hdr, 16, k_off)        # kernel offset
    struct.pack_into("<Q", hdr, 24, len(kd))       # kernel size
    struct.pack_into("<Q", hdr, 32, a_off)        # adt offset
    struct.pack_into("<Q", hdr, 40, len(ad))       # adt size
    struct.pack_into("<Q", hdr, 48, b_off)        # bootargs offset
    struct.pack_into("<Q", hdr, 56, len(bootargs))# bootargs size

    with open(out, "wb") as f:
        f.write(hdr)
        f.write(kd)
        f.write(ad)
        f.write(bootargs)
    print(f"[+] payload written: {out} ({total} bytes)")
    print(f"    kernel  off=0x{k_off:x} size=0x{len(kd):x}")
    print(f"    adt     off=0x{a_off:x} size=0x{len(ad):x}")
    print(f"    bootargs off=0x{b_off:x} size=0x{len(bootargs):x}")

if __name__ == "__main__":
    main()
