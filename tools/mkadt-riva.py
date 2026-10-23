#!/usr/bin/env python3
"""
mkadt-riva.py  --  Build an Apple Device Tree (ADT) for Riva
================================================================

ios-sweet generates an "Apple Device Tree" (ADT) that XNU expects instead of a
Linux FDT. The ADT is still a flattened device tree, but with Apple-specific
node/property conventions (device_type, "arm-io" platform node, framebuffer,
"cpu0", chosen boot-args, ...). XNU's pe_arm calls into it very early to learn
the memory map, UART, framebuffer and timer.

This tool reads the *real* riva DTB we extracted (device/riva.dtb), pulls the
genuine MMIO bases out of it, and emits an Apple-convention ADT. Where a node is
absent (e.g. the QRD DTB lacks a board-specific framebuffer reg), it falls back
to the verified riva constants captured during bring-up:

    GIC-dist      0xb000000   (GICv2, qcom,msm-qgic2)
    GIC-cpu       0xb002000
    arch timer    19.2 MHz     (clock-frequency 0x124f800 = 19,200,000)
    eMMC/SDHCI    0x7824900    (bootdevice = 7824900.sdhci)
    MDSS MDP      0x1a00000
    framebuffer   0x90000000   (splash_region, size 0x1400000 = 20 MB)
    RAM           32-bit PA, < 4 GiB (reserved regions live at 0x8xxxxxxx)

Output: device/riva-adt.dtb  (compiled via dtc)  +  a human .dts dump.

Usage:
    python3 mkadt-riva.py [--dtb device/riva.dtb] [--out device/riva-adt.dtb]
"""
import struct
import subprocess
import sys
import os

# ---- verified riva fallback constants -------------------------------------
RIVA = {
    "gic_dist":  0xB000000,
    "gic_cpu":   0xB002000,
    "timer_hz":  19200000,
    "sdhci":     0x7824900,
    "mdp":       0x1A00000,
    "fb_base":   0x90000000,
    "fb_size":   0x1400000,   # 20 MB contiguous splash
    "soc":       "MSM8917/8940 (Cortex-A53, GICv2, eMMC)",
    "model":     "Xiaomi Redmi 5A (riva)",
}

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9

def parse_dtb(data: bytes):
    """Minimal FDT parser -> nested dict tree. Returns (tree, strings)."""
    (magic, totalsize, off_dt, off_str, off_rsv, version,
     last_ver, boot_cpu, size_str, size_dt) = struct.unpack(">10I", data[:40])
    assert magic == FDT_MAGIC, "bad FDT magic"
    strings = data[off_str:off_str + size_str]
    tree = {}
    stack = [tree]
    i = off_dt
    cur_name = None
    while i < off_dt + size_dt:
        tok = struct.unpack(">I", data[i:i + 4])[0]
        i += 4
        if tok == FDT_BEGIN_NODE:
            # name until NUL
            end = data.index(b"\x00", i)
            name = data[i:end].decode("utf-8", "ignore")
            i = (end + 4) & ~3
            node = {}
            stack[-1][name] = node
            stack.append(node)
            cur_name = name
        elif tok == FDT_END_NODE:
            stack.pop()
        elif tok == FDT_PROP:
            plen, nameoff = struct.unpack(">II", data[i:i + 8])
            i += 8
            raw = data[i:i + plen]
            i += (plen + 3) & ~3
            # name
            so = strings.index(b"\x00", nameoff)
            pname = strings[nameoff:so].decode("utf-8", "ignore")
            stack[-1].setdefault("__props__", {})[pname] = raw
        elif tok == FDT_NOP:
            continue
        elif tok == FDT_END:
            break
    return tree, strings

def get_reg(node):
    """Decode a `reg` property into a list of (addr, size).

    The QRD DTB mixed #address-cells conventions: some MMIO nodes are written
    1/1 (e.g. GIC `<0xb000000 0x1000 0xb002000 0x1000>`) while others are 2/2
    (splash `<0x0 0x90000000 0x0 0x1400000>`). We try several (addr,size) cell
    layouts and keep the one whose decoded addresses are all clean 32-bit MMIO
    (high word == 0), which matches the physical SoC map.
    """
    raw = node.get("__props__", {}).get("reg")
    if not raw:
        return []
    n = len(raw) // 4
    vals = list(struct.unpack(">%dI" % n, raw))

    def decode(ac, sc):
        out = []
        stride = ac + sc
        if stride == 0 or stride > n:
            return []
        for k in range(0, n - stride + 1, stride):
            a = 0
            s = 0
            for c in range(ac):
                a = (a << 32) | vals[k + c]
            for c in range(sc):
                s = (s << 32) | vals[k + ac + c]
            out.append((a, s))
        return out

    for (ac, sc) in [(2, 2), (1, 1), (2, 1), (1, 2)]:
        r = decode(ac, sc)
        if r and all((a >> 32) == 0 for (a, _) in r):
            return r
    return decode(2, 2)  # last resort

def find_node(tree, want):
    for k, v in tree.items():
        if k == want and isinstance(v, dict):
            return v
        if isinstance(v, dict):
            r = find_node(v, want)
            if r:
                return r
    return None

def u32(x):
    return "0x%08x" % (x & 0xFFFFFFFF)

def main():
    dtb_path = "device/riva.dtb"
    out_path = "device/riva-adt.dtb"
    if "--dtb" in sys.argv:
        dtb_path = sys.argv[sys.argv.index("--dtb") + 1]
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]

    vals = dict(RIVA)
    try:
        with open(dtb_path, "rb") as f:
            tree, _ = parse_dtb(f.read())
        # GIC
        gic = find_node(tree, "interrupt-controller@b000000")
        if gic:
            regs = get_reg(gic)
            if regs:
                vals["gic_dist"] = regs[0][0]
                if len(regs) > 1:
                    vals["gic_cpu"] = regs[1][0]
        # timer
        timer = find_node(tree, "timer")
        if timer:
            tf = timer.get("__props__", {}).get("clock-frequency")
            if tf:
                vals["timer_hz"] = struct.unpack(">I", tf[:4])[0]
        # sdhci / eMMC
        sdhci = find_node(tree, "sdhci@7824900")
        if sdhci:
            regs = get_reg(sdhci)
            if regs:
                vals["sdhci"] = regs[0][0]
        # MDSS MDP
        mdp = find_node(tree, "qcom,mdss_mdp@1a00000")
        if mdp:
            regs = get_reg(mdp)
            if regs:
                vals["mdp"] = regs[0][0]
        # splash / framebuffer
        splash = find_node(tree, "splash_region@83000000")
        if splash:
            regs = get_reg(splash)
            if regs:
                vals["fb_base"] = regs[0][0]
                vals["fb_size"] = regs[0][1]
        print("[+] Parsed real DTB: %s" % dtb_path)
    except Exception as e:
        print("[!] Could not parse DTB (%s); using verified riva fallbacks" % e)

    dts = build_adt_dts(vals)
    dts_path = out_path.replace(".dtb", ".dts")
    with open(dts_path, "w") as f:
        f.write(dts)
    # compile with dtc (Apple DT is still a DTB)
    try:
        subprocess.run(["dtc", "-I", "dts", "-O", "dtb", "-o", out_path, dts_path],
                       check=True, capture_output=True)
        print("[+] Wrote Apple Device Tree: %s" % out_path)
    except Exception as e:
        print("[!] dtc failed (%s); kept .dts at %s" % (e, dts_path))
    print("[+] framebuffer base : %s  size %s" % (u32(vals["fb_base"]), u32(vals["fb_size"])))
    print("[+] gic-dist        : %s" % u32(vals["gic_dist"]))
    print("[+] arch timer      : %d Hz (%.1f MHz)" % (vals["timer_hz"], vals["timer_hz"] / 1e6))
    print("[+] eMMC sdhci      : %s" % u32(vals["sdhci"]))

def build_adt_dts(v):
    fb = v["fb_base"]
    fbsz = v["fb_size"]
    gicd = v["gic_dist"]
    return f"""\
/dts-v1/;

/ {{
    device_type = "boot";
    model = "{v['model']}";
    compatible = "apple,arm-io", "riva";
    #address-cells = <0x2>;
    #size-cells = <0x2>;

    chosen {{
        boot-args = "rd=ufsroot0 cpus=4 rivafb=0x{fb:08x},0x{fbsz:08x} gic=0x{gicd:08x} sw_render ipanel=riva_hd";
        memory-map = <0x0 0x0 0x0 0x0>;   // filled at shim time from real DRAM
        boot-version = <0x1>;
    }};

    // Apple "arm-io" platform node: SoC MMIO the XNU drivers bind to.
    arm-io@0 {{
        device_type = "arm-io";
        compatible = "riva-io";
        #address-cells = <0x2>;
        #size-cells = <0x2>;
        ranges;

        // GICv2 (riva uses GICv2, NOT the GICv3 sweet has)
        interrupt-controller@0 {{
            device_type = "interrupt-controller";
            compatible = "arm,gic-400";
            interrupt-cells = <0x3>;
            reg = <0x0 0x{gicd:08x} 0x0 0x1000
                   0x0 0x{gicd+0x2000:08x} 0x0 0x1000>;
        }};

        // arch timer, 19.2 MHz XO (same as sweet's reference clock)
        timer {{
            device_type = "timer";
            compatible = "arm,armv8-timer";
            clock-frequency = <{v['timer_hz']}>;
        }};

        // eMMC host (riva stores iOS root here, not UFS)
        sdhci@0 {{
            device_type = "sdhci";
            compatible = "qcom,sdhci-msm-v5";
            reg = <0x0 0x{v['sdhci']:08x} 0x0 0x2000>;
            riva-root = <0x1>;   // userdata holds the HFS+ iOS root
        }};

        // MDSS display subsystem
        mdp@0 {{
            device_type = "display-pipe";
            compatible = "qcom,mdss_mdp";
            reg = <0x0 0x{v['mdp']:08x} 0x0 0x90000>;
        }};
    }};

    // Early framebuffer console (ABL leaves splash @ 0x90000000)
    framebuffer@0x{fb:08x} {{
        device_type = "framebuffer";
        compatible = "riva-fb";
        reg = <0x0 0x{fb:08x} 0x0 0x{fbsz:08x}>;
        width = <0x2d0>;    // 720
        height = <0x500>;   // 1280
        depth = <0x20>;     // 32 bpp
        stride = <0xb40>;   // 720*4 = 2880
    }};

    cpus {{
        #address-cells = <0x1>;
        #size-cells = <0x0>;
        cpu0 {{
            device_type = "cpu";
            compatible = "arm,cortex-a53";
            reg = <0x0>;
            enable-method = "psci";
        }};
        cpu1 {{ device_type = "cpu"; compatible = "arm,cortex-a53"; reg = <0x1>; enable-method = "psci"; }};
        cpu2 {{ device_type = "cpu"; compatible = "arm,cortex-a53"; reg = <0x2>; enable-method = "psci"; }};
        cpu3 {{ device_type = "cpu"; compatible = "arm,cortex-a53"; reg = <0x3>; enable-method = "psci"; }};
    }};
}};
"""

if __name__ == "__main__":
    main()
