# Riva XNU port map — mapping ios-sweet's 81 patches to riva

ios-sweet ships **81 XNU patches** (`0001`–`0081`) plus 3 staging scripts
(`stage-libpthread`, `stage-bearssl`, `stage-hfs`) and a shim with
`start.S / shim.c / loader.c / mmu.c / fdt.c / console.c / ufs.c`.

This file maps each patch to riva. Three dispositions:
- **复用 (reuse)** — SoC-agnostic, copy as-is.
- **改 (adapt)** — same idea, change addresses/values to riva's real HW.
- **替换 (replace)** — sweet-specific driver (UFS / GICv3 / Goodix) that riva
  does NOT have; write the riva equivalent (eMMC / GICv2 / Synaptics).

riva HW facts come from `docs/HARDWARE.md` (real DTB). The big three riva-unique
drivers are marked **🔴 BLOCKING** — they are the real engineering and do not
exist yet.

## Build-system / security / crypto (mostly 复用)
| Patch | Area | Riva |
|-------|------|------|
| 0001 new-clang auto-var-init | build | 复用 |
| 0002 clang UIO_STACKBUF | build | 复用 |
| 0005 non-pac-build-fixes | build/PAC | 复用 |
| 0007 stub apple-internal-headers | build | 复用 |
| 0009 drop apple-soc-only-exports | build | 复用 |
| 0013 kmem-rng w/o corecrypto | RNG | 复用 |
| 0014 kernel-hmac-prng | RNG | 复用 |
| 0015 trust-cache runtime | sec | 复用 |
| 0020 portable aes-cbc | crypto | 复用 |
| 0023 sha256 libkern | crypto | 复用 |
| 0025 amfi no-entitlements | AMFI | 复用 |
| 0027/0032/0033 bearssl md5/sha1/sha384 | crypto | 复用 |
| 0035/0036 amfi entitlements/cs-signed | AMFI | 复用 |
| 0038 applekeystore | sec | 复用 (stub) |
| 0050 sandbox-policy | sandbox | 复用 |
| 0057 no-ext-resolver | sys | 复用 |

## Machine config / device tree / timers (改 for riva)
| Patch | Area | Riva |
|-------|------|------|
| 0004 sweet-machine-config | machine | **改** → `riva-machine-config`: add `RIVA` platform, `gRiva` |
| 0006 master-config open-source asm pmap | pmap | **改** → riva pmap (Cortex-A53) |
| 0011 physmap alignment | mem | 复用 (32-bit PA simpler) |
| 0012 keep debug console after ttbr0 | console | 复用 |
| 0016 device-tree platform expert | DT | **改** → parse our ADT (`tools/mkadt-riva.py`) |
| 0017 device-tree virtual timer irq | timer/IRQ | **改** → GICv2 IRQ numbering; 19.2 MHz XO (same) |
| 0018 boot cpu driver | boot | 复用 / 改 (CPU init) |
| 0065 smp-psci | SMP | **改** → 4 cores (sweet uses 6/8) |
| 0078 smp-8-cores | SMP | **替换** → `riva-smp-4-cores` |

## Storage: UFS → eMMC/SDHCI  🔴 BLOCKING
| Patch | Area | Riva |
|-------|------|------|
| 0028 ufs-root-device | storage | **替换** → `riva-sdhci-root-device` (eMMC @0x7824900) |
| 0030 ufs-writes | storage | **替换** → `riva-sdhci-writes` |
| 0034 ufs-dma-above-4g | DMA | **替换/删除** → riva RAM < 4GiB, no high-DMA needed |
| 0069 ufs-faster | perf | **替换** → `riva-sdhci-faster` |
| shim/ufs.c | shim storage | **替换** → `shim/sdhci.c` (read HFS+ root from eMMC) |

> riva has **no UFS** — the entire UFS driver stack must become an SDHCI/eMMC
> driver. This is one of the two or three hardest pieces.

## Framebuffer / display (改 for riva's 720×1280 MDSS)
| Patch | Area | Riva |
|-------|------|------|
| 0003 framebuffer serial console | fb | **改** → framebuffer @0x90000000 (same idea) |
| 0010 early-framebuffer-debug | fb | 复用 |
| 0046 iosurface iomfb | gfx | **改** → MDSS, 720×1280 |
| 0056 fb-throttled-present | gfx | 复用 |
| 0061 iphone-x-display-size | gfx | **替换** → `riva-display-size` (720×1280, not 1125×2436) |
| 0079 display-power | pwr | **改** → MDSS/panel PMIC (PMI8950) |

## HID / touch / PMIC  🔴 BLOCKING
| Patch | Area | Riva |
|-------|------|------|
| 0058 hid-event-services | HID | 复用 (framework) |
| 0060 keys-touch-drivers | input | **改** → riva key map |
| 0062 touch-power-battery | pwr | **改** → PMI8950 |
| 0063 goodix-geni-packing | touch | **替换** → `riva-synaptics-dsx` (Synaptics @I2C 0x4b) |
| 0071 touch-edge | touch | **改** → Synaptics |
| 0040/0045 iowatchdog / pmu | wdog | **改** → PMI8950 PMU |

## Filesystem / root volume (mostly 复用)
0021/0022/0024 mockfs ramdisk root · 0026 builtin-hfs · 0029 unsealed-root ·
0031 read-write-root · 0037 bindfs · 0041/0052 hfs → **复用** (these make the
iOS HFS+ root mountable; SoC-independent).

## USB / logging / misc (复用 or 改)
0072–0081 USB stack → 复用 (framework); 0042–0044/0047/0048/0051/0053/0066/0067
console+crash logs → 复用; 0054/0055 samplers → 复用; 0064 priv-work-interval →
复用; 0070 pid-hibernate → **改**; 0080 net-trace → 复用; 0019/0026 staging → 复用.

## Device identity (改)
0059 iphone-identity → **改** → report an arm64 iPhone model XNU accepts
(e.g. iPhone8,1 / SE2 baseline) so userland loads; 0061 display-size above.

## shim changes (riva)
| ios-sweet shim file | riva |
|---------------------|------|
| `start.S` | 复用 (Cortex-A53 boot is same ARM64) |
| `mmu.c` | 复用 (identity map; riva RAM <4G simpler) |
| `fdt.c` | 复用 — parse our ADT |
| `console.c` / `font.h` | 复用 — draw to 0x90000000 |
| `loader.c` | 复用 (load XNU + ADT + bootargs) |
| `ufs.c` | **替换 → `sdhci.c`** read HFS+ root from eMMC userdata |

## The 🔴 BLOCKING list (what does NOT exist and must be written)
1. **GICv2 interrupt controller** in XNU (sweet's SM7150 is GICv3; riva is
   GICv2 @0xb000000). New driver or adapt `osfmk/arm` interrupt + `pexpert`.
2. **eMMC/SDHCI storage driver** replacing the whole UFS stack (patches
   0028/0030/0034/0069 + shim `sdhci.c`).
3. **MDSS display + 720×1280 panel** + software-present path (patches
   0046/0061/0079).
4. **Synaptics DSX touch** driver (replaces Goodix, 0063/0071).
5. **PMI8950 PMIC** regulator/PMU (0062/0045).

These five are the actual port. Everything else in the 81-patch set is reuse or
trivial adapt. See `xnu/patches/series` for the planned riva patch filenames.
