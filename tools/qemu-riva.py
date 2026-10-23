#!/usr/bin/env python3
"""
qemu-riva.py  --  Boot the riva XNU + shim under QEMU (arm64 'virt') for fast
=============================================================================
iteration on kernel/driver changes without touching real hardware.

Models ios-sweet's qemu-sweet.py. We use QEMU's `virt` machine with RAM-disk
boot: the shim payload (kernel + ADT) is loaded as a generic kernel image and
the ADT is passed as the device tree. This validates MMU bring-up, UART, and
early XNU startup. Hardware-specific drivers (eMMC, MDSS, touch) are naturally
unavailable under virt and are expected to panic -- that's fine for bring-up.

Usage:
    python3 qemu-riva.py --payload payload.bin [--mem 2048] [--graphic]
"""
import argparse
import subprocess
import sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", required=True)
    ap.add_argument("--mem", type=int, default=2048, help="RAM in MB")
    ap.add_argument("--graphic", action="store_true", help="show QEMU window")
    ap.add_argument("--qemu", default="qemu-system-aarch64")
    args = ap.parse_args()

    cmd = [
        args.qemu, "-machine", "virt", "-cpu", "cortex-a53",
        "-smp", "4", "-m", str(args.mem),
        "-kernel", args.payload,
        "-append", "earlycon console=ttyAMA0 sw_render riva_qemu",
        "-serial", "mon:stdio",
        "-nographic" if not args.graphic else "-display", "gtk",
    ]
    print("[+] Launching:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("[!] qemu-system-aarch64 not found. Install: apt-get install qemu-system-arm")
        sys.exit(1)

if __name__ == "__main__":
    main()
