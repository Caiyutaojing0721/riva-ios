# XNU patches for Riva (`xnu-riva`)

ios-sweet ports XNU `xnu-8796` (iOS 16) to **sweet** (Redmi Note 10 Pro,
SM7150) via a numbered patch series `0001..0069`. For **riva** (Redmi 5A,
MSM8917/8940) the kernel bring-up is *broadly the same* (both are ARM64
Qualcomm, PSCI SMP, 19.2 MHz XO) but the **driver surface is different**:

| Subsystem | sweet (SM7150)        | riva (MSM8917/8940)        | Patch impact                  |
|-----------|-----------------------|----------------------------|-------------------------------|
| Interrupt | GICv3                 | **GICv2** (qgic2 @0xb000000) | replace GICv3 driver with GICv2 |
| Storage   | UFS host driver       | **eMMC/SDHCI** @0x7824900  | swap UFS for sdhci-msm         |
| RAM       | high bank 0x100000000+| **32-bit PA, < 4GiB**       | no highmem window needed      |
| Display   | panel virtual 1125x2436 | **MDSS, 720x1280 (HD)**   | new panel/display timing       |
| Touch     | Goodix GT9896 (I2C)   | **Synaptics DSX** (I2C 0x4b) | new touch driver              |
| PMIC      | SM7150 PMIC           | **PMI8950**                | pmic/SPMI changes              |
| CPU       | Cortex-A55 x6         | **Cortex-A53 x4**          | cpu-topology / PSCI           |

## Layout
Patches live alongside the XNU source after `xnu-8796` is fetched (ios-sweet
uses `gh workflow run xnu.yml` on macOS runners -- that step is SoC-agnostic
and reusable as-is). Each patch is named `00NN-<topic>.patch`.

## Categories to port (start from ios-sweet's series, fork per topic)
1. `00xx-riva-machine-add`      -- add a `RIVA` machine type / `gRiva` platform
2. `00xx-riva-gicv2`            -- GICv2 interrupt controller support
3. `00xx-riva-sdhci`            -- eMMC/SDHCI root device (`rd=ufsroot0` becomes
                                   `rd=sdhciroot0` or keep `rd=` naming, map to eMMC)
4. `00xx-riva-fb`               -- early framebuffer console at 0x90000000
5. `00xx-riva-timer`            -- armv8 arch timer @ 19.2 MHz (same as sweet)
6. `00xx-riva-psci`             -- PSCI CPU bring-up (4 cores)
7. `00xx-riva-display`          -- MDSS + 720x1280 panel
8. `00xx-riva-touch`            -- Synaptics DSX HID
9. `00xx-riva-deviceid`         -- report an iPhone identity for userland
10. `00xx-riva-adt`             -- consume the ADT from `tools/mkadt-riva.py`

> The `series` file lists the planned patch set. These are **scaffold
> placeholders** -- the real diffs require the XNU source + a working
> aarch64 toolchain (see PORTING.md step 1).

## Building
```
# fork ios-sweet, enable the xnu.yml workflow, download the artifact
# then (locally) drop these patches into xnu/ and:
git -C xnu-8796 am ../riva-ios/xnu/patches/00*.patch
# build per ios-sweet's kernel build (macOS runner) -> xnu.bin
```
