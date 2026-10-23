/* linker.ld -- riva shim (ARM64, bare metal)
 * Loaded by ABL as the boot.img kernel image; entry at _start. */
OUTPUT_ARCH(aarch64)
ENTRY(_start)

MEMORY {
    /* ABL loads boot.img kernel at kerneladdr=0x80008000 (from bootimg.cfg).
       The shim is small; place it in the first MB of that window. */
    SHIM (rwx) : ORIGIN = 0x80008000, LENGTH = 0x00100000
}

SECTIONS {
    . = ORIGIN(SHIM);
    .text : {
        KEEP(*(.text.boot))
        *(.text*)
    } > SHIM

    .rodata : { *(.rodata*) } > SHIM
    .data   : { *(.data*) }   > SHIM

    .bss (NOLOAD) : {
        . = ALIGN(16);
        __bss_start = .;
        *(.bss*)
        . = ALIGN(16);
        __bss_end = .;
    } > SHIM

    . = ALIGN(16);
    __stack_top = ORIGIN(SHIM) + LENGTH(SHIM) - 0x1000;
}
