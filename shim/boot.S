/* boot.S -- riva iOS shim, stage 0 (ARM64, bare metal)
 * --------------------------------------------------------------
 * The Xiaomi ABL (emmc_appsboot.mbn) loads shim-boot.img and jumps to this
 * entry. We run with the MMU/ caches as ABL left them (section-mapped 1:1
 * physical == virtual for the low DRAM). We set up a stack and the exception
 * vector, then hand control to shim_main() in C.
 *
 * Riva specifics:
 *   - Cortex-A53 x4, PSCI for SMP (see ios-sweet shim/psci.c equivalent)
 *   - ABL leaves a live framebuffer at 0x90000000 (splash_region) we reuse
 *   - UART is the MSM HS-UART at 0x78B0000 (earlycon in stock cmdline)
 */
    .section .text.boot, "ax"
    .globl _start
_start:
    /* Disable interrupts at the core level while we bring up. */
    msr daifset, #0x3

    /* Set up the exception vector base address. */
    ldr x0, =vectors
    msr vbar_el1, x0
    isb

    /* Choose a stack: use the top of the shim's BSS/stack region. */
    ldr x0, =__stack_top
    mov sp, x0

    /* Zero BSS. */
    ldr x1, =__bss_start
    ldr x2, =__bss_end
1:  cmp x1, x2
    b.hs 2f
    str xzr, [x1], #8
    b 1b
2:
    bl shim_main
    /* shim_main should never return; if it does, park. */
    b .

/* Minimal exception vector table (el1, 4 slots x 128 bytes each = 0x80). */
    .align 11
vectors:
    .fill 0x80, 1, 0x00   /* current EL, SP0          */
    .fill 0x80, 1, 0x00   /* current EL, SPx          */
    .fill 0x80, 1, 0x00   /* lower EL, AArch64        */
    .fill 0x80, 1, 0x00   /* lower EL, AArch32        */
