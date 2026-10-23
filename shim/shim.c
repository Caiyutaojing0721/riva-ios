/* shim.c -- riva iOS shim, stage 1 (C)
 * --------------------------------------------------------------
 * Responsibilities (mirrors ios-sweet's shim/):
 *   1. Locate the payload (kernel + ADT + boot-args) that ABL appended to the
 *      shim boot.img ramdisk region, parse the 64-byte RIVAPLD1 header.
 *   2. Map the framebuffer (0x90000000, splash_region) and print early status
 *      so boot progress is visible without a serial cable.
 *   3. Parse the Apple Device Tree (ADT) and pass it to XNU as needed.
 *   4. Jump to the XNU kernel entry with the ADT pointer in x0 (Mach-O entry).
 *
 * This is a faithful scaffold: the hardcoded addresses come from the REAL riva
 * DTB we extracted (see ../docs/HARDWARE.md). The XNU entry hand-off and ADT
 * consumption are intentionally left as the integration point against the
 * actual xnu-riva build.
 */
#include <stdint.h>

#define RIVA_FB_BASE   0x90000000u   /* splash_region, 32-bit PA */
#define RIVA_FB_SIZE   0x01400000u   /* 20 MB contiguous */
#define RIVA_FB_W      720
#define RIVA_FB_H      1280
#define RIVA_FB_STRIDE (RIVA_FB_W * 4)   /* 32 bpp */

struct payload_hdr {
    char     magic[8];      /* "RIVAPLD1" */
    uint32_t version;
    uint64_t kernel_off;
    uint64_t kernel_size;
    uint64_t adt_off;
    uint64_t adt_size;
    uint64_t bootargs_off;
    uint64_t bootargs_size;
};

static volatile uint32_t *fb = (volatile uint32_t *)RIVA_FB_BASE;

static void fb_clear(uint32_t color) {
    for (int y = 0; y < RIVA_FB_H; y++)
        for (int x = 0; x < RIVA_FB_W; x++)
            fb[y * (RIVA_FB_STRIDE / 4) + x] = color;
}

/* Tiny 8x8 glyph blit (replace with a real font in the xnu-riva build). */
static void fb_puts(const char *s) {
    (void)s;  /* scaffold: real text rendering belongs in the console driver */
}

/* Locate payload. ABL places the ramdisk right after the kernel in boot.img;
 * the shim build (build.sh) concatenates payload.bin into the ramdisk slot. */
static const struct payload_hdr *find_payload(uintptr_t base, uintptr_t limit) {
    for (uint64_t p = base; p + sizeof(struct payload_hdr) < limit; p += 16) {
        const struct payload_hdr *h = (const struct payload_hdr *)p;
        if (h->magic[0]=='R' && h->magic[1]=='I' && h->magic[2]=='V' &&
            h->magic[3]=='A' && h->magic[4]=='P' && h->magic[5]=='L' &&
            h->magic[6]=='D' && h->magic[7]=='1')
            return h;
    }
    return 0;
}

void shim_main(void) {
    fb_clear(0x00101830);   /* dark blue boot screen */

    /* In the real build, base/limit come from the DTB memory node + ramdisk
     * location passed by ABL. We scan a conservative DRAM window here. */
    const struct payload_hdr *h =
        find_payload(0x80000000u, 0x80000000u + (1u << 30));
    if (!h) {
        fb_puts("riva-shim: payload not found");
        return;
    }

    const uint8_t *base = (const uint8_t *)h;
    const uint8_t *kernel = base + h->kernel_off;
    const uint8_t *adt    = base + h->adt_off;
    const char    *args   = (const char *)(base + h->bootargs_off);

    /* Draw a progress marker, then transfer to XNU.
     * XNU's arm64 entry expects: x0 = ADT virt addr, other args per XNU PE.
     * ((void(*)(uintptr_t))kernel_entry)(adt_vaddr); */
    (void)kernel; (void)adt; (void)args;

    /* Integration point: invalidate caches, set up XNU's expected CPU state,
     * and branch to the Mach-O entry. Left as TODO against xnu-riva. */
    for (;;) { __asm__ volatile ("wfi"); }
}
