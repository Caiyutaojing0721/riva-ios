# Porting iOS to riva — bring-up guide

This guide maps the [ios-sweet](https://github.com/dipa-studio/ios-sweet) method
onto **riva** (Redmi 5A, MSM8917/8940). It is honest about what is done and what
remains. Read `docs/HARDWARE.md` first for the extracted hardware facts.

## 0. What ios-sweet actually proved
ios-sweet boots **unmodified iPhone X iOS 16 userland** (launchd → backboardd →
SpringBoard) on the Redmi Note 10 Pro by:
1. Building Apple's open **XNU** kernel (`xnu-8796`) on macOS CI with a long
   patch series (`xnu/patches/0001..0069`).
2. Synthesizing an **Apple Device Tree (ADT)** + boot-args.
3. Loading a **bare-metal shim** via `fastboot boot` that sets up MMU, parses
   the FDT, and jumps to XNU with the ADT in `x0`.
4. Mounting an **HFS+ iOS root** flashed to `userdata`.
5. Software-rendering to the framebuffer (no GPU).

Even there it is *experimental*: no GPU, no Wi-Fi/BT/cellular/audio/camera/SEP,
slow boot, security disabled. **riva is further behind** because its SoC driver
surface is different (see the GICv2/eMMC/display/touch table in HARDWARE.md).

## 1. Build the XNU kernel for riva (macOS CI — reuse ios-sweet's `xnu.yml`)
The kernel build pipeline is SoC-agnostic; reuse it as-is. The *patches* differ:
fork `xnu/patches/00NN-riva-*.patch` from ios-sweet's series and re-target:
- **GICv2** instead of GICv3 (`0002-riva-gicv2.patch`).
- **eMMC/SDHCI** root (`rd=sdhciroot0`) instead of UFS (`0003-riva-sdhci.patch`).
- **32-bit RAM** map (no highmem window) — simpler than sweet.
- **720x1280** MDSS panel + **Synaptics DSX** touch.
Output: `xnu.bin` (Mach-O). This is the single biggest unknown and requires
real kernel engineering on the XNU source.

## 2. Build the iOS root image (Linux PC)
Use `tools/mkiosroot.sh`. Differences from sweet:
- Pick an **arm64-only iOS build** (iOS 14/15/16 userland, e.g. iPhone 8 / SE2 /
  iPad baseline) — riva is arm64 (Cortex-A53) but is *not* an Apple SoC, so you
  run the userland unmodified like sweet does, just from a different IPSW.
- The root is written to **eMMC userdata**, sparse-wrapped (`img2simg`).
- `sweet-root-tweaks.py` must be ported: skip Setup, mark activated, set the
  riva display panel name (`ipanel=riva_hd`).

## 3. Generate the ADT (already working here)
```bash
python3 tools/mkadt-riva.py     # -> device/riva-adt.dtb (real riva addresses)
```
This parses the extracted `riva.dtb` and emits a valid Apple Device Tree with
GIC @`0xb000000`, eMMC @`0x7824900`, framebuffer @`0x90000000`, 19.2 MHz timer.

## 4. Assemble the payload + shim boot image
```bash
python3 tools/mkpayload-riva.py --kernel xnu.bin \
        --adt device/riva-adt.dtb -o payload.bin
(cd shim && ./build.sh)                       # needs aarch64 toolchain
./flash/build_bootimg.sh                      # -> flash/shim-boot.img
```
The shim (`shim/`) is a real ARM64 loader using riva's load addresses
(`bootimg.cfg`: kernel `0x80008000`, ramdisk `0x81000000`, pagesize `0x800`).

## 5. Flash & boot (temporary — no brick)
```bash
./flash/flash_ios.sh out/ios-root.simg shim-boot.img
```
This writes only `userdata` and `fastboot boot`s the shim. **Stock bootloader,
modem, recovery, persist are untouched** — reboot returns to Android.

## 6. Read the boot log
```bash
tools/riva-log-pull.sh        # 4 MiB persistent ring at end of userdata
```

## Honest gap analysis
| Blocking item | Effort | Notes |
|---------------|--------|-------|
| XNU riva patch series (GICv2/eMMC/display/touch/PMIC) | **very high** | real kernel/driver reverse-engineering |
| iOS root from an arm64 IPSW | medium | scriptable; needs the IPSW |
| ADT + shim + flash | **done (scaffold)** | works once `xnu.bin` exists |
| GPU / Wi-Fi / BT / cellular / audio / camera / SEP | out of scope | same as sweet, plus riva has weaker HW |

**Bottom line:** the *framework, tooling, and real hardware map* are here and
runnable. The hard, open engineering is the XNU riva port itself — exactly the
part ios-sweet spent its effort on for a *different* SoC. Treat this repo as the
starting point and the driver/porting checklist, not a finished ROM.

## Re-extracting board-accurate DT
The bundled `riva.dtb` is a **generic QRD** tree. For real bring-up:
```bash
# from a running riva (or its dtb partition):
adb pull /sys/firmware/fdt riva-dtb-real.dtb
python3 tools/mkadt-riva.py --dtb riva-dtb-real.dtb
```
