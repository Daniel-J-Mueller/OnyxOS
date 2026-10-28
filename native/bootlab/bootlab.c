/* OnyxOS Boot Lab: an original, freestanding UEFI application.
 * It does not leave firmware, isolate processes, access files, or drive a GPU.
 * CPU framebuffer drawing is a bootstrap baseline, not the planned compositor.
 * No allocation, timer, sleep, animation, or polling loop is used per redraw.
 */
#include "efi_min.h"
#include "font5x7.h"

typedef struct { int x, y, w, h; } Box;
typedef struct { U32 background, surface, title, border, text, muted, accent; } Palette;

static EFI_SYSTEM_TABLE *system_table;
static EFI_SERIAL *serial;
static EFI_GRAPHICS *graphics;
static volatile U32 *pixels;
static U32 width, height, stride, pixel_format, original_mode;
static int graphics_active, fit_active, preset;
static Box standard_boxes[3], saved_boxes[3], current_boxes[3];

static EFI_GUID graphics_guid = {0x9042a9de,0x23dc,0x4a38,{0x96,0xfb,0x7a,0xde,0xd0,0x80,0x51,0x6a}};
static EFI_GUID serial_guid = {0xbb25cf6f,0xf1d4,0x11d2,{0x9a,0x0c,0x00,0x90,0x27,0x3f,0xc1,0xfd}};

static const Palette palettes[3] = {
    {0x10151d,0x18222e,0x213142,0x465c72,0xe1eaf4,0x94a9be,0x75c7ff},
    {0x15181a,0x22282c,0x30383e,0x53616b,0xe8eff2,0x9db0b8,0xffc47b},
    {0x101a19,0x172a26,0x213a32,0x3c6759,0xe0f5ed,0x92b7a7,0x86e1b9}
};
static const char *preset_names[3] = {"ONYX", "WORKBENCH", "COMPACT"};

/* Compilers may lower structure copies to these freestanding primitives. */
void *memcpy(void *destination, const void *source, UINTN count) {
    U8 *out = (U8 *)destination;
    const U8 *in = (const U8 *)source;
    for (UINTN i = 0; i < count; ++i) out[i] = in[i];
    return destination;
}
void *memset(void *destination, int value, UINTN count) {
    U8 *out = (U8 *)destination;
    for (UINTN i = 0; i < count; ++i) out[i] = (U8)value;
    return destination;
}

static void console_text(const char *message) {
    CHAR16 wide[256];
    UINTN i = 0;
    while (i < 255 && message[i]) { wide[i] = (U8)message[i]; ++i; }
    wide[i] = 0;
    if (system_table->output && system_table->output->write)
        system_table->output->write(system_table->output, wide);
}

static void serial_text(const char *message) {
    UINTN count = 0;
    while (count < 255 && message[count]) ++count;
    if (serial && serial->write && count)
        serial->write(serial, &count, (void *)message);
}

static void state_marker(void) {
    static const char *standard[3] = {
        "ONYX_STATE standard preset=0\r\n", "ONYX_STATE standard preset=1\r\n",
        "ONYX_STATE standard preset=2\r\n"
    };
    static const char *fit[3] = {
        "ONYX_STATE fit preset=0\r\n", "ONYX_STATE fit preset=1\r\n",
        "ONYX_STATE fit preset=2\r\n"
    };
    const char *message = fit_active ? fit[preset] : standard[preset];
    serial_text(message);
    if (!graphics_active) console_text(message);
}

static int minimum(int a, int b) { return a < b ? a : b; }

static U32 packed_color(U32 color) {
    if (pixel_format == 0)
        return ((color & 0xff) << 16) | (color & 0xff00) | ((color >> 16) & 0xff);
    return color;
}

static void fill(Box box, U32 color) {
    int x0 = box.x < 0 ? 0 : box.x;
    int y0 = box.y < 0 ? 0 : box.y;
    int x1 = minimum((int)width, box.x + box.w);
    int y1 = minimum((int)height, box.y + box.h);
    U32 pixel = packed_color(color);
    if (box.w <= 0 || box.h <= 0 || x0 >= x1 || y0 >= y1) return;
    for (int y = y0; y < y1; ++y) {
        volatile U32 *row = pixels + (UINTN)y * stride;
        for (int x = x0; x < x1; ++x) row[x] = pixel;
    }
}

static void glyph(int x, int y, char character, int scale, U32 color) {
    unsigned int code = (U8)character;
    if (code >= 'a' && code <= 'z') code -= 'a' - 'A';
    if (code < 32 || code > 126) code = '?';
    for (int row = 0; row < 7; ++row)
        for (int column = 0; column < 5; ++column)
            if (onyx_font[code - 32][row] & (1 << (4 - column)))
                fill((Box){x + column * scale, y + row * scale, scale, scale}, color);
}

static void text(int x, int y, int max_width, const char *message, int scale, U32 color) {
    int advance = 6 * scale, offset = 0;
    for (UINTN i = 0; i < 512 && message[i] && message[i] != '\n'; ++i) {
        if (offset + 5 * scale > max_width) break;
        glyph(x + offset, y, message[i], scale, color);
        offset += advance;
    }
}

/* Word wrapping has bounded input length and never writes outside the box. */
static void paragraph(Box box, const char *message, int scale, U32 color) {
    int advance = 6 * scale, line = 10 * scale, x = box.x, y = box.y;
    UINTN i = 0;
    while (i < 2048 && message[i] && y + 7 * scale <= box.y + box.h) {
        if (message[i] == '\n') { x = box.x; y += line; ++i; continue; }
        if (message[i] == ' ') {
            if (x != box.x) x += advance;
            ++i; continue;
        }
        UINTN length = 0;
        while (i + length < 2048 && message[i + length]
               && message[i + length] != ' ' && message[i + length] != '\n') ++length;
        if (x != box.x && x + (int)length * advance > box.x + box.w) {
            x = box.x; y += line;
        }
        for (UINTN j = 0; j < length; ++j) {
            if (x + 5 * scale > box.x + box.w) { x = box.x; y += line; }
            if (y + 7 * scale > box.y + box.h) return;
            glyph(x, y, message[i + j], scale, color);
            x += advance;
        }
        i += length;
    }
}

static void number(char *buffer, U32 value) {
    char reversed[10];
    UINTN count = 0;
    do { reversed[count++] = (char)('0' + value % 10); value /= 10; } while (value && count < 10);
    for (UINTN i = 0; i < count; ++i) buffer[i] = reversed[count - 1 - i];
    buffer[count] = 0;
}

static Box pane(Box box, const char *title, const char *identifier) {
    const Palette *p = &palettes[preset];
    fill(box, p->border);
    fill((Box){box.x + 2, box.y + 2, box.w - 4, box.h - 4}, p->surface);
    fill((Box){box.x + 2, box.y + 2, box.w - 4, 27}, p->title);
    fill((Box){box.x + 2, box.y + 2, 3, 27}, p->accent);
    text(box.x + 12, box.y + 10, box.w - 85, title, 1, p->text);
    text(box.x + box.w - 64, box.y + 10, 54, identifier, 1, p->muted);
    return (Box){box.x + 12, box.y + 42, box.w - 24, box.h - 54};
}

static void documents(Box box) {
    const Palette *p = &palettes[preset];
    Box body = pane(box, "DOCUMENTS", "DOC.001");
    int scale = body.w >= 440 && body.h >= 360 ? 2 : 1;
    int heading = 18 * scale;
    text(body.x, body.y, body.w, "A SMALLER SURFACE.", scale, p->accent);
    text(body.x, body.y + heading, body.w, "MORE ROOM TO WORK.", scale, p->text);
    body.y += heading * 2 + 8;
    body.h -= heading * 2 + 8;
    paragraph(body,
        "ONYXOS / BOOT LAB 01\n\n"
        "Three sample panes in one native UEFI application.\n\n"
        "F8 / F: fill desktop space. Toggle again to restore exact positions.\n\n"
        "F9 / F10 OR [ / ]: select an independent shell preset.\n\n"
        "No animation, artificial delay, or allocation per redraw.\n\n"
        "NOT A KERNEL. Files, process isolation, and GPU composition are future work.",
        scale, p->muted);
}

static void task_graph(Box box) {
    const Palette *p = &palettes[preset];
    Box body = pane(box, "TASK GRAPH", "SIM.002");
    int scale = body.w >= 440 && body.h >= 260 ? 2 : 1;
    int step = minimum(25 * scale, (body.h - 30 * scale - 12) / 3);
    text(body.x, body.y, body.w, "SIMULATED TASK GRAPH", scale, p->accent);
    text(body.x, body.y + 13 * scale, body.w, "ONE APP / NO PROCESS ISOLATION", 1, p->muted);
    int top = body.y + 30 * scale;
    const char *names[4] = {"UEFI FIRMWARE", "BOOTLAB.EFI", "INPUT: WAIT FOR EVENT", "RENDER: ON DEMAND"};
    for (int i = 0; i < 4; ++i) {
        int y = top + i * step;
        if (y + 12 > body.y + body.h) break;
        if (i) fill((Box){body.x + 3, y - step + 8, 1, step}, p->border);
        fill((Box){body.x, y + 2, 7, 7}, i == 1 ? p->accent : p->border);
        fill((Box){body.x + 7, y + 5, 10, 1}, p->border);
        text(body.x + 23, y + 2, body.w - 23, names[i], 1, i == 1 ? p->text : p->muted);
    }
}

static void image_preview(Box box) {
    const Palette *p = &palettes[preset];
    Box body = pane(box, "IMAGE PREVIEW", "IMG.003");
    text(body.x, body.y, body.w, "PROCEDURAL SAMPLE / 16:9 CONTAIN", 1, p->muted);
    body.y += 18; body.h -= 18;
    if (body.w < 16 || body.h < 9) return;
    int image_width = body.w;
    int image_height = image_width * 9 / 16;
    if (image_height > body.h) { image_height = body.h; image_width = image_height * 16 / 9; }
    Box image = {body.x + (body.w - image_width) / 2,
                 body.y + (body.h - image_height) / 2, image_width, image_height};
    fill(body, 0x0c121c);
    /* Integer-coordinate landscape uses all of the sample image without crop. */
    for (int y = 0; y < image.h; ++y) {
        int logical_y = y * 180 / image.h;
        for (int x = 0; x < image.w; ++x) {
            int logical_x = x * 320 / image.w;
            int ridge_a = 130 - (logical_x < 150 ? logical_x : 300 - logical_x) / 2;
            int ridge_b = 160 - (logical_x < 230 ? logical_x : 460 - logical_x) / 3;
            U32 color = 0x182b43 + ((U32)(logical_y / 12) << 8);
            if ((logical_x - 246) * (logical_x - 246) + (logical_y - 37) * (logical_y - 37) < 225)
                color = p->accent;
            if (logical_y > ridge_a) color = 0x305574;
            if (logical_y > ridge_b) color = 0x203e55;
            if (logical_y > 145) color = 0x132b3e;
            pixels[(UINTN)(image.y + y) * stride + (UINTN)(image.x + x)] = packed_color(color);
        }
    }
}

static void initialize_boxes(void) {
    int w = (int)width, h = (int)height;
    standard_boxes[0] = (Box){20, 100, w * 52 / 100, h - 178};
    standard_boxes[1] = (Box){w * 55 / 100, 116, w * 42 / 100, (h - 174) * 52 / 100};
    standard_boxes[2] = (Box){w * 51 / 100, h * 56 / 100, w * 45 / 100, h * 34 / 100};
    for (int i = 0; i < 3; ++i) current_boxes[i] = standard_boxes[i];
}

static void toggle_fit(void) {
    if (fit_active) {
        for (int i = 0; i < 3; ++i) current_boxes[i] = saved_boxes[i];
        fit_active = 0;
    } else {
        for (int i = 0; i < 3; ++i) saved_boxes[i] = current_boxes[i];
        int left = (int)width * 57 / 100;
        int usable = (int)height - 136;
        int upper = usable * 55 / 100;
        current_boxes[0] = (Box){0, 86, left, usable};
        current_boxes[1] = (Box){left, 86, (int)width - left, upper};
        current_boxes[2] = (Box){left, 86 + upper, (int)width - left, usable - upper};
        fit_active = 1;
    }
}

static void render(void) {
    if (!graphics_active) return;
    const Palette *p = &palettes[preset];
    fill((Box){0, 0, (int)width, (int)height}, p->background);
    fill((Box){0, 0, (int)width, 3}, p->accent);
    text(20, 18, 240, "ONYXOS", 3, p->text);
    text(20, 48, 280, "BOOT LAB / NATIVE UEFI", 1, p->muted);
    int status_x = (int)width - 250;
    text(status_x, 18, 230, fit_active ? "FIT MODE" : "STANDARD MODE", 2, p->accent);
    text(status_x, 43, 95, "PRESET", 1, p->muted);
    text(status_x + 48, 43, 180, preset_names[preset], 1, p->text);
    text(20, 69, (int)width - 40,
         "F8 / F  FIT     F9 / [  PREVIOUS     F10 / ]  NEXT     Q  FIRMWARE", 1, p->muted);
    documents(current_boxes[0]);
    task_graph(current_boxes[1]);
    image_preview(current_boxes[2]);
    int bottom = (int)height - 36;
    fill((Box){0, (int)height - 48, (int)width, 1}, p->border);
    text(14, bottom, (int)width - 28,
         "2PX BORDERS / CPU FRAMEBUFFER / FIRMWARE OWNED / NO ANIMATION", 1, p->muted);
    text(14, bottom + 17, 240, "ONYX_BOOTLAB_READY", 1, p->accent);
    char value[11];
    number(value, width);
    text((int)width - 140, bottom + 17, 40, value, 1, p->muted);
    text((int)width - 105, bottom + 17, 12, "X", 1, p->muted);
    number(value, height);
    text((int)width - 90, bottom + 17, 40, value, 1, p->muted);
#if defined(__aarch64__) || defined(_M_ARM64)
    text((int)width - 48, bottom + 17, 42, "ARM64", 1, p->muted);
#else
    text((int)width - 48, bottom + 17, 42, "X64", 1, p->muted);
#endif
}

static int initialize_graphics(void) {
    EFI_BOOT_SERVICES *boot = system_table->boot;
    if (EFI_ERROR(boot->locate_protocol(&graphics_guid, 0, (void **)&graphics))
        || !graphics || !graphics->mode) return 0;
    original_mode = graphics->mode->mode;
    /* Query allocations happen only at startup and are released immediately. */
    U32 selected = original_mode, area = 0;
    U32 count = graphics->mode->max_mode;
    if (count > 256) count = 256;
    if (graphics->query_mode && graphics->set_mode && boot->free_pool) {
        for (U32 index = 0; index < count; ++index) {
            EFI_GRAPHICS_INFO *info = 0;
            UINTN size = 0;
            EFI_STATUS status = graphics->query_mode(graphics, index, &size, &info);
            if (!EFI_ERROR(status) && info && size >= sizeof(*info)
                && info->format <= 1 && info->width >= 640 && info->height >= 480
                && info->width <= 1280 && info->height <= 800) {
                U32 candidate_area = info->width * info->height;
                if (candidate_area > area) { area = candidate_area; selected = index; }
            }
            if (info) boot->free_pool(info);
        }
        if (area && selected != original_mode) graphics->set_mode(graphics, selected);
    }
    EFI_GRAPHICS_MODE *mode = graphics->mode;
    if (!mode || !mode->info || mode->info_size < sizeof(*mode->info)) return 0;
    EFI_GRAPHICS_INFO *info = mode->info;
    if (info->format > 1 || info->width < 640 || info->height < 480
        || info->width > 4096 || info->height > 2160
        || info->stride < info->width || info->stride > 8192
        || !mode->framebuffer || (mode->framebuffer & 3)) return 0;
    UINTN bytes = (UINTN)info->stride * info->height * 4;
    if (bytes > mode->framebuffer_size || mode->framebuffer > (~(U64)0) - bytes) return 0;
    width = info->width; height = info->height; stride = info->stride; pixel_format = info->format;
    pixels = (volatile U32 *)(UINTN)mode->framebuffer;
    initialize_boxes();
    return 1;
}

EFI_STATUS efi_main(EFI_HANDLE image, EFI_SYSTEM_TABLE *table) {
    (void)image;
    if (!table || table->header.signature != EFI_SYSTEM_SIGNATURE
        || table->header.size < sizeof(*table) || !table->boot
        || table->boot->header.signature != EFI_BOOT_SIGNATURE
        || table->boot->header.size < sizeof(EFI_BOOT_SERVICES)
        || !table->boot->locate_protocol || !table->boot->wait_for_event) return EFI_UNSUPPORTED;
    system_table = table;
    if (table->boot->set_watchdog) table->boot->set_watchdog(0, 0, 0, 0);
    table->boot->locate_protocol(&serial_guid, 0, (void **)&serial);
    if (serial && serial->set_attributes)
        serial->set_attributes(serial, 115200, 0, 1000, 1, 8, 1);
    if (table->output && table->output->enable_cursor) table->output->enable_cursor(table->output, 0);
    console_text("OnyxOS Boot Lab - firmware application, not a kernel.\r\n");
    if (!table->input || !table->input->read || !table->input->wait_key) {
        console_text("ONYX_BOOTLAB_ERROR no keyboard event interface\r\n");
        serial_text("ONYX_BOOTLAB_ERROR no keyboard event interface\r\n");
        return EFI_UNSUPPORTED;
    }
    graphics_active = initialize_graphics();
    if (!graphics_active) {
        console_text("Text fallback: unsupported GOP mode; RGB/BGR framebuffer required.\r\n");
        console_text("F8/f fit | F9/[ previous | F10/] next | q return to firmware\r\n");
        serial_text("ONYX_BOOTLAB_GRAPHICS=0\r\n");
    } else serial_text("ONYX_BOOTLAB_GRAPHICS=1\r\n");
    /* In graphics mode the marker is drawn as text in the status bar. Do not
     * send an earlier console marker: a serial-backed console could make a
     * boot harness capture the framebuffer before the first redraw finishes.
     */
    if (!graphics_active) console_text("ONYX_BOOTLAB_READY\r\n");
    render();
    state_marker();
    serial_text("ONYX_BOOTLAB_READY\r\n");
    for (;;) {
        UINTN event_index = 0;
        EFI_EVENT event = table->input->wait_key;
        EFI_STATUS status = table->boot->wait_for_event(1, &event, &event_index);
        if (EFI_ERROR(status)) {
            serial_text("ONYX_BOOTLAB_ERROR wait_for_event\r\n");
            return EFI_DEVICE_ERROR;
        }
        EFI_KEY key = {0, 0};
        if (EFI_ERROR(table->input->read(table->input, &key))) continue;
        int changed = 1;
        if (key.unicode == 'q' || key.unicode == 'Q') break;
        if (key.scan == 0x12 || key.unicode == 'f' || key.unicode == 'F') toggle_fit();
        else if (key.scan == 0x13 || key.unicode == '[') preset = (preset + 2) % 3;
        else if (key.scan == 0x14 || key.unicode == ']') preset = (preset + 1) % 3;
        else changed = 0;
        if (changed) { render(); state_marker(); }
    }
    serial_text("ONYX_BOOTLAB_EXIT\r\n");
    if (graphics && graphics->set_mode && graphics->mode && graphics->mode->mode != original_mode)
        graphics->set_mode(graphics, original_mode);
    if (table->output && table->output->clear) table->output->clear(table->output);
    if (table->output && table->output->enable_cursor) table->output->enable_cursor(table->output, 1);
    console_text("OnyxOS Boot Lab returned to firmware.\r\n");
    return EFI_SUCCESS;
}
