#!/usr/bin/env python3
"""
extract-dtb.py  --  Riva (MSM8917/8940) kernel DTB extractor
=============================================================

On Qualcomm 64-bit platforms the board Device Tree Blob is usually *appended*
to the kernel Image (zImage / Image.gz) rather than shipped as a separate
"second" stage. This tool scans a kernel image for the FDT magic (0xd00dfeed),
validates the length from the FDT header, and writes out a clean .dtb.

Usage:
    python3 extract-dtb.py <kernel_image> [-o output.dtb]

Example (the riva stock boot.img we are porting from):
    python3 extract-dtb.py ../device/../riva-ios-work/boot_extract/zImage -o riva.dtb

Note: the boot.img shipped in this riva fastboot package carries a *generic QRD
reference* DTB (model "MSM8940-PMI8950 QRD SKU6"). For a real bring-up you must
re-extract the DTB from the device's own `dtb` partition (or /proc/device-tree on
a running kernel) because panel/touch/regulator addresses are board-specific.
"""
import struct
import sys
import os

FDT_MAGIC = 0xD00DFEED

def find_dtb(data: bytes):
    pos = data.find(struct.pack(">I", FDT_MAGIC))
    if pos < 0:
        return None, None
    # totalsize is bytes 4..8 of the FDT header, big-endian
    totalsize = struct.unpack(">I", data[pos + 4:pos + 8])[0]
    # sanity: totalsize must be plausible
    if totalsize < 0x40 or totalsize > 0x400000:
        return None, None
    return pos, totalsize

def main():
    if len(sys.argv) < 2:
        print("usage: extract-dtb.py <kernel_image> [-o out.dtb]")
        sys.exit(1)
    img = sys.argv[1]
    out = "riva.dtb"
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]

    with open(img, "rb") as f:
        data = f.read()

    pos, size = find_dtb(data)
    if pos is None:
        print(f"[!] No FDT magic (0xd00dfeed) found in {img}")
        sys.exit(2)

    dtb = data[pos:pos + size]
    with open(out, "wb") as f:
        f.write(dtb)
    print(f"[+] DTB found at byte offset 0x{pos:x}")
    print(f"[+] DTB total size      0x{size:x} ({size} bytes)")
    print(f"[+] Wrote {out}")
    # quick model peek
    try:
        m = dtb.decode("utf-8", "ignore")
        i = m.find("model")
        if i >= 0:
            s = m[i:i + 80].split("\x00")[0]
            print(f"[+] model hint: {s}")
    except Exception:
        pass

if __name__ == "__main__":
    main()
