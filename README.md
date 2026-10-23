# riva-ios — port iOS (XNU) to the Xiaomi Redmi 5A (riva)

> A **porting scaffold** for bringing iOS / Apple's XNU kernel to the Redmi 5A
> (`riva`, MSM8917/8940), modeled on the [dipa-studio/ios-sweet](https://github.com/dipa-studio/ios-sweet)
> project (which runs iOS 16 on the Redmi Note 10 Pro / `sweet`).

This repository is **not** a finished, flashable, working iOS ROM. A real port
is a multi-year kernel + hardware bring-up effort (XNU build on macOS CI, real
IPSW userland, and MSM8917-specific drivers — a *different* SoC generation from
sweet's SM7150). What this scaffold *does* give you is:

- ✅ **Real extracted riva hardware facts** from the stock ROM's device tree
  (GICv2 @`0xb000000`, eMMC @`0x7824900`, framebuffer @`0x90000000`, 19.2 MHz
  timer, PSCI, Synaptics DSX touch) — see `docs/HARDWARE.md`.
- ✅ **A working Apple Device Tree generator** (`tools/mkadt-riva.py`) that
  consumes the real DTB and emits a valid ADT binary.
- ✅ **A DTB extractor**, **payload assembler**, **QEMU harness**, **log puller**.
- ✅ **A bare-metal shim** (loader ABL jumps into) with riva's real MMIO.
- ✅ **Flash scripts** adapted to riva's partition layout.
- ✅ **An XNU patch-series outline** documenting the driver work needed.
- ✅ **A runnable GitHub Actions CI** (`.github/workflows/xnu.yml`) that fetches
  XNU source and auto-builds the riva kernel on every patch push.

## 🚀 Want to actually build the kernel?

👉 **`docs/GITHUB_ACTIONS_GUIDE.md`** — a step-by-step, beginner-friendly walk
through of pushing this to GitHub and running the CI (30–60 min first time).

## Directory layout
```
riva-ios/
├── device/          real extracted artifacts (riva.dtb/.dts, generated ADT)
├── docs/HARDWARE.md hardware facts pulled from the DTB
├── shim/           bare-metal ARM64 loader (boot.S, shim.c, linker, build.sh)
├── tools/          extract-dtb, mkadt-riva, mkpayload-riva, mkiosroot,
│                   riva-log-pull, qemu-riva
├── flash/          flash_ios.sh (temporary boot), build_bootimg.sh
├── xnu/patches/    XNU patch-series outline (RIVA-specific driver work)
└── PORTING.md      full bring-up guide + honest status
```

## Quick start (what works today)
```bash
# 1) Re-generate the Apple Device Tree from the real riva DTB:
python3 tools/mkadt-riva.py
file device/riva-adt.dtb        # -> "Device Tree Blob ..."

# 2) Assemble a shim payload once you have an xnu.bin:
python3 tools/mkpayload-riva.py --kernel xnu.bin \
        --adt device/riva-adt.dtb -o payload.bin

# 3) Build the shim + boot image (needs aarch64 toolchain + mkbootimg):
(cd shim && ./build.sh)
./flash/build_bootimg.sh

# 4) Boot temporarily on an unlocked riva (stock boot is NOT overwritten):
./flash/flash_ios.sh out/ios-root.simg shim-boot.img
```

## Status
| Stage | State |
|-------|-------|
| Hardware analysis | ✅ done (this repo) |
| ADT / shim scaffold | ✅ done (needs xnu.bin to actually boot) |
| XNU kernel build for riva | ⬜ requires macOS CI + xnu-8796 + RIVA patches |
| iOS root image (IPSW → HFS+) | ⬜ requires an arm64-only IPSW + `mkiosroot.sh` wiring |
| GICv2 / eMMC / display / touch drivers | ⬜ open driver work (see `xnu/patches/`) |
| Boots to SpringBoard | ⬜ not yet (the hard part) |

See `PORTING.md` for the complete plan and the gap analysis versus ios-sweet.
