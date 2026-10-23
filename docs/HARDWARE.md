# Riva hardware facts (extracted from the real DTB)

All values below were pulled from the device tree inside the stock riva
`boot.img` (decompiled to `device/riva.dts`). They are the genuine inputs the
shim and the Apple Device Tree (`tools/mkadt-riva.py`) are built from.

> **Caveat:** the boot.img DTB is a *generic QRD reference tree*
> (`model = "Qualcomm Technologies, Inc. MSM8940-PMI8950 QRD SKU6"`,
> `qcom,msm-id = <0x139 0x00>`). SoC-level facts are valid for the riva
> (MSM8917/8940) family, but board-level addresses (panel timings, touch,
> regulators) must be re-read from the device's own `dtb` partition during a
> real bring-up.

## SoC / CPU
| Item | Value |
|------|-------|
| Platform | Qualcomm MSM8917 / MSM8940 (riva = MSM8917; DTB says MSM8940 QRD SKU6) |
| Cores | 4x ARM Cortex-A53, PSCI SMP (`enable-method = "psci"`) |
| `qcom,msm-id` | 0x139 (313) |

## Memory
| Item | Value |
|------|-------|
| Physical address space | **32-bit (< 4 GiB)** -- simpler than sweet's high-memory bank |
| Reserved regions | in `0x8xxxxxxx` / `0x9xxxxxxx` (eMMC-boot, modem, adsp, wcnss, splash) |
| Splash / framebuffer | **base `0x90000000`, size `0x1400000` (20 MB)** |

## Interrupts & timers
| Item | Value |
|------|-------|
| Interrupt controller | **GICv2** (`qcom,msm-qgic2`), dist `@0xb000000`, cpu `@0xb002000` |
| Arch timer | `arm,armv8-timer`, **clock-frequency `0x124f800` = 19,200,000 Hz (19.2 MHz)** |
| Memory-mapped timer | `timer@b120000`, `clock-frequency 0x124f800` |

## Storage
| Item | Value |
|------|-------|
| eMMC / SDHCI | **`sdhci@7824900`** (bootdevice `7824900.sdhci`) -- **eMMC, not UFS** |
| iOS root target | `userdata` partition (HFS+ volume, sparse-wrapped) |

## Display
| Item | Value |
|------|-------|
| MDSS MDP | `qcom,mdss_mdp@1a00000` (reg `0x1a00000`/`0x90000`, `0x1ab0000`/`0x1040`) |
| DSI panel (in DTB) | simulator default 640x480 -- **replace with riva 720x1280 (HD) real panel** |
| Framebuffer (splash) | `0x90000000`, 20 MB |

## Touch / input
| Item | Value |
|------|-------|
| Touch controller | **Synaptics DSX** (`synaptics,dsx`) @ I2C address **0x4b** |
| Display coords in DTB | `0x437 x 0x77f` (generic QRD; verify against real panel) |

## Key differences from sweet (Redmi Note 10 Pro, SM7150)
| Area | sweet | riva |
|------|-------|------|
| SoC | SM7150 (Cortex-A55) | MSM8917/8940 (Cortex-A53) |
| Interrupts | **GICv3** | **GICv2** |
| Storage | **UFS** host driver | **eMMC/SDHCI** |
| RAM | high bank `0x100000000+` | **32-bit PA, < 4 GiB** |
| Display | 1080x2400 (virtual 1125x2436) | **720x1280 (HD)** |
| Touch | Goodix GT9896 | **Synaptics DSX** |
| PMIC | SM7150 | **PMI8950** |

These differences are exactly why the ios-sweet patch series cannot be reused
verbatim -- the GICv2/eMMC/display/touch/PMIC drivers must be re-targeted
(see `xnu/patches/README.md`).

## Flash partition layout (from `rawprogram0.xml`)

The stock ROM flash table tells us exactly which eMMC partition the iOS root
goes into, and what stays untouched during the temporary bring-up flash.

| Partition | eMMC start (sector) | Size | iOS use |
|-----------|--------------------|-------|---------|
| `modem` (NON-HLOS.bin) | 131072 | 84 MB | untouched |
| `sbl1` / `tz` / `rpm` / `aboot` | 393234+ | small | **untouched** (bootloader chain) |
| `boot` | 790528 | 64 MB | **untouched** (stock Android boot) |
| `recovery` | 921600 | 64 MB | untouched (used by `riva-log-pull.sh`) |
| `system` | 1054720 | 3 GB | Android system (untouched) |
| `cache` | 7471104 | 256 MB | untouched |
| `persist` | 7995392 | 32 MB | **calibration — back up first** |
| `misc` | 8060928 | 1 MB | untouched |
| `cust` | 8781824 | 512 MB | untouched |
| **`userdata`** | **9830400** | **rest of eMMC** | **← iOS HFS+ root goes HERE** |

`sddc`/`riva bootdevice` = `7824900.sdhci`. Our `flash_ios.sh` writes only
`userdata` + `fastboot boot` the shim, so boot/recovery/modem/persist stay
stock-signed — one reboot returns to Android (no brick risk).
