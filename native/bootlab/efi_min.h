/* Minimal declarations of the public UEFI 64-bit ABI, written for this lab.
 * ABI reference: https://uefi.org/specs/UEFI/2.10/
 * Build for x86_64-pc-windows-msvc or aarch64-pc-windows-msvc. The target
 * supplies the firmware calling convention; no host SDK or libc is used.
 */
#ifndef ONYX_EFI_MIN_H
#define ONYX_EFI_MIN_H

typedef unsigned char U8;
typedef unsigned short U16;
typedef unsigned int U32;
typedef unsigned long long U64;
typedef __SIZE_TYPE__ UINTN;
typedef U16 CHAR16;
typedef UINTN EFI_STATUS;
typedef void *EFI_HANDLE;
typedef void *EFI_EVENT;

#define EFI_SUCCESS ((EFI_STATUS)0)
#define EFI_ERROR_BIT ((EFI_STATUS)1 << 63)
#define EFI_UNSUPPORTED (EFI_ERROR_BIT | 3)
#define EFI_DEVICE_ERROR (EFI_ERROR_BIT | 7)
#define EFI_ERROR(s) (((s) & EFI_ERROR_BIT) != 0)
#define EFI_SYSTEM_SIGNATURE 0x5453595320494249ULL
#define EFI_BOOT_SIGNATURE 0x56524553544f4f42ULL
#define EFI_OFFSETOF(t, m) __builtin_offsetof(t, m)

typedef struct { U32 a; U16 b, c; U8 d[8]; } EFI_GUID;
typedef struct { U64 signature; U32 revision, size, crc32, reserved; } EFI_HEADER;
typedef struct { U16 scan, unicode; } EFI_KEY;

typedef struct EFI_INPUT EFI_INPUT;
struct EFI_INPUT {
    EFI_STATUS (*reset)(EFI_INPUT *, U8);
    EFI_STATUS (*read)(EFI_INPUT *, EFI_KEY *);
    EFI_EVENT wait_key;
};

typedef struct EFI_OUTPUT EFI_OUTPUT;
struct EFI_OUTPUT {
    void *reset;
    EFI_STATUS (*write)(EFI_OUTPUT *, CHAR16 *);
    void *test, *query, *set_mode, *set_attribute;
    EFI_STATUS (*clear)(EFI_OUTPUT *);
    void *set_cursor;
    EFI_STATUS (*enable_cursor)(EFI_OUTPUT *, U8);
    void *mode;
};

typedef struct {
    EFI_HEADER header;
    void *raise_tpl, *restore_tpl, *allocate_pages, *free_pages, *get_memory_map;
    void *allocate_pool;
    EFI_STATUS (*free_pool)(void *);
    void *create_event, *set_timer;
    EFI_STATUS (*wait_for_event)(UINTN, EFI_EVENT *, UINTN *);
    void *signal_event, *close_event, *check_event;
    void *install_protocol, *reinstall_protocol, *uninstall_protocol, *handle_protocol;
    void *reserved, *register_notify, *locate_handle, *locate_device_path;
    void *install_configuration, *load_image, *start_image, *exit_image;
    void *unload_image, *exit_boot_services, *get_monotonic_count, *stall;
    EFI_STATUS (*set_watchdog)(UINTN, U64, UINTN, CHAR16 *);
    void *connect_controller, *disconnect_controller, *open_protocol, *close_protocol;
    void *open_protocol_information, *protocols_per_handle, *locate_handle_buffer;
    EFI_STATUS (*locate_protocol)(EFI_GUID *, void *, void **);
} EFI_BOOT_SERVICES;

typedef struct {
    EFI_HEADER header;
    CHAR16 *vendor;
    U32 firmware_revision;
    EFI_HANDLE input_handle;
    EFI_INPUT *input;
    EFI_HANDLE output_handle;
    EFI_OUTPUT *output;
    EFI_HANDLE error_handle;
    EFI_OUTPUT *error_output;
    void *runtime_services;
    EFI_BOOT_SERVICES *boot;
    UINTN configuration_count;
    void *configuration_tables;
} EFI_SYSTEM_TABLE;

typedef struct { U32 red, green, blue, reserved; } EFI_PIXEL_MASK;
typedef struct {
    U32 version, width, height, format;
    EFI_PIXEL_MASK mask;
    U32 stride;
} EFI_GRAPHICS_INFO;
typedef struct {
    U32 max_mode, mode;
    EFI_GRAPHICS_INFO *info;
    UINTN info_size;
    U64 framebuffer;
    UINTN framebuffer_size;
} EFI_GRAPHICS_MODE;
typedef struct EFI_GRAPHICS EFI_GRAPHICS;
struct EFI_GRAPHICS {
    EFI_STATUS (*query_mode)(EFI_GRAPHICS *, U32, UINTN *, EFI_GRAPHICS_INFO **);
    EFI_STATUS (*set_mode)(EFI_GRAPHICS *, U32);
    void *blt;
    EFI_GRAPHICS_MODE *mode;
};

typedef struct EFI_SERIAL EFI_SERIAL;
struct EFI_SERIAL {
    U32 revision;
    void *reset;
    EFI_STATUS (*set_attributes)(EFI_SERIAL *, U64, U32, U32, U32, U8, U32);
    void *set_control, *get_control;
    EFI_STATUS (*write)(EFI_SERIAL *, UINTN *, void *);
    void *read, *mode;
};

_Static_assert(sizeof(void *) == 8, "This lab supports only 64-bit UEFI");
_Static_assert(sizeof(U32) == 4 && sizeof(U64) == 8, "Unexpected integer ABI");
_Static_assert(sizeof(EFI_HEADER) == 24, "UEFI header ABI");
_Static_assert(sizeof(EFI_GUID) == 16, "UEFI GUID ABI");
_Static_assert(EFI_OFFSETOF(EFI_SYSTEM_TABLE, input) == 48, "UEFI input ABI");
_Static_assert(EFI_OFFSETOF(EFI_SYSTEM_TABLE, output) == 64, "UEFI output ABI");
_Static_assert(EFI_OFFSETOF(EFI_SYSTEM_TABLE, boot) == 96, "UEFI system ABI");
_Static_assert(EFI_OFFSETOF(EFI_BOOT_SERVICES, wait_for_event) == 96, "UEFI event ABI");
_Static_assert(EFI_OFFSETOF(EFI_BOOT_SERVICES, set_watchdog) == 256, "UEFI watchdog ABI");
_Static_assert(EFI_OFFSETOF(EFI_BOOT_SERVICES, locate_protocol) == 320, "UEFI protocol ABI");
_Static_assert(EFI_OFFSETOF(EFI_GRAPHICS, mode) == 24, "UEFI graphics ABI");
_Static_assert(EFI_OFFSETOF(EFI_GRAPHICS_MODE, framebuffer) == 24, "UEFI framebuffer ABI");
_Static_assert(sizeof(EFI_GRAPHICS_INFO) == 36, "UEFI graphics info ABI");
_Static_assert(EFI_OFFSETOF(EFI_SERIAL, write) == 40, "UEFI serial ABI");

#endif
