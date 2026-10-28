"""Deterministic GPT + FAT32 image containing only our own EFI application.

No host disks are opened, mounted, partitioned or modified. The output is a new
regular file, suitable for QEMU. Firmware is deliberately not redistributed.
"""

import struct
import uuid
import zlib
from pathlib import Path

SECTOR = 512
SECTORS = 131072  # 64 MiB, enough clusters for a genuine FAT32 volume.
START = 2048
END = SECTORS - 34
RESERVED = 32
EFI_TYPE = uuid.UUID("c12a7328-f81f-11d2-ba4b-00a0c93ec93b")
ARCH_FILES = {"aarch64": b"BOOTAA64EFI", "x86_64": b"BOOTX64 EFI"}


def _header(current, backup, entries_lba, table_crc, disk_guid):
    header = bytearray(SECTOR)
    struct.pack_into("<8sIIIIQQQQ16sQIII", header, 0,
                     b"EFI PART", 0x10000, 92, 0, 0, current, backup,
                     34, END, disk_guid.bytes_le, entries_lba, 128, 128, table_crc)
    struct.pack_into("<I", header, 16, zlib.crc32(header[:92]))
    return header


def _entry(name, attributes, cluster, size=0):
    if len(name) != 11:
        raise ValueError("FAT short name must have eleven bytes")
    result = bytearray(32)
    result[:11] = name
    result[11] = attributes
    date = ((2026 - 1980) << 9) | (1 << 5) | 1
    for offset in (16, 18, 24):
        struct.pack_into("<H", result, offset, date)
    struct.pack_into("<H", result, 20, cluster >> 16)
    struct.pack_into("<H", result, 26, cluster & 0xFFFF)
    struct.pack_into("<I", result, 28, size)
    return result


def make_image(executable: bytes, arch: str) -> bytearray:
    if arch not in ARCH_FILES:
        raise ValueError("unsupported architecture")
    if not isinstance(executable, bytes) or not 64 <= len(executable) <= 4 * 1024 * 1024:
        raise ValueError("EFI executable must be 64 bytes to 4 MiB")
    if executable[:2] != b"MZ":
        raise ValueError("expected a PE/COFF EFI executable")
    pe_offset = struct.unpack_from("<I", executable, 60)[0]
    if pe_offset > len(executable) - 94 or executable[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("invalid PE header")
    expected_machine = 0xAA64 if arch == "aarch64" else 0x8664
    if struct.unpack_from("<H", executable, pe_offset + 4)[0] != expected_machine:
        raise ValueError("PE machine does not match disk architecture")
    if struct.unpack_from("<H", executable, pe_offset + 24)[0] != 0x20B:
        raise ValueError("expected PE32+")
    if struct.unpack_from("<H", executable, pe_offset + 24 + 68)[0] != 10:
        raise ValueError("expected EFI application subsystem")

    image = bytearray(SECTORS * SECTOR)
    # Protective MBR. The firmware boots a file, not this boot sector's code.
    image[446:462] = struct.pack("<B3sB3sII", 0, b"\0\x02\0", 0xEE,
                                b"\xff\xff\xff", 1, SECTORS - 1)
    image[510:512] = b"\x55\xaa"
    table = bytearray(128 * 128)
    guid = uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/Daniel-J-Mueller/OnyxOS/{arch}")
    partition_guid = uuid.uuid5(guid, "boot-lab-esp")
    struct.pack_into("<16s16sQQQ", table, 0, EFI_TYPE.bytes_le,
                     partition_guid.bytes_le, START, END, 0)
    label = "OnyxOS Boot Lab".encode("utf-16-le")
    table[56:56 + len(label)] = label
    table_crc = zlib.crc32(table)
    image[2 * SECTOR:34 * SECTOR] = table
    image[(SECTORS - 33) * SECTOR:(SECTORS - 1) * SECTOR] = table
    image[SECTOR:2 * SECTOR] = _header(1, SECTORS - 1, 2, table_crc, guid)
    image[(SECTORS - 1) * SECTOR:] = _header(SECTORS - 1, 1, SECTORS - 33, table_crc, guid)

    total = END - START + 1
    fat_sectors = 1
    while True:
        clusters = total - RESERVED - 2 * fat_sectors
        needed = ((clusters + 2) * 4 + SECTOR - 1) // SECTOR
        if fat_sectors >= needed:
            break
        fat_sectors = needed
    clusters = total - RESERVED - 2 * fat_sectors
    if clusters < 65525:
        raise ValueError("volume is too small for FAT32")
    boot = bytearray(SECTOR)
    boot[:11] = b"\xeb\x58\x90ONYXBOOT"
    struct.pack_into("<HBHBHHBHHHII", boot, 11, SECTOR, 1, RESERVED, 2, 0, 0,
                     0xF8, 0, 63, 255, START, total)
    struct.pack_into("<IHHIHH", boot, 36, fat_sectors, 0, 0, 2, 1, 6)
    boot[64] = 0x80
    boot[66] = 0x29
    struct.pack_into("<I", boot, 67, zlib.crc32(arch.encode("ascii")))
    boot[71:82] = b"ONYXBOOT   "
    boot[82:90] = b"FAT32   "
    boot[510:512] = b"\x55\xaa"
    base = START * SECTOR
    image[base:base + SECTOR] = boot
    image[base + 6 * SECTOR:base + 7 * SECTOR] = boot
    file_clusters = (len(executable) + SECTOR - 1) // SECTOR
    info = bytearray(SECTOR)
    struct.pack_into("<I", info, 0, 0x41615252)
    struct.pack_into("<III", info, 484, 0x61417272, clusters - 3 - file_clusters, 5 + file_clusters)
    struct.pack_into("<I", info, 508, 0xAA550000)
    for relative in (1, 7):
        image[base + relative * SECTOR:base + (relative + 1) * SECTOR] = info
    fat = bytearray(fat_sectors * SECTOR)
    for index, value in enumerate((0x0FFFFFF8, 0xFFFFFFFF, 0x0FFFFFFF, 0x0FFFFFFF, 0x0FFFFFFF)):
        struct.pack_into("<I", fat, index * 4, value)
    for cluster in range(5, 5 + file_clusters):
        value = cluster + 1 if cluster < 4 + file_clusters else 0x0FFFFFFF
        struct.pack_into("<I", fat, cluster * 4, value)
    for copy in (0, 1):
        offset = base + (RESERVED + copy * fat_sectors) * SECTOR
        image[offset:offset + len(fat)] = fat
    data = base + (RESERVED + 2 * fat_sectors) * SECTOR
    root = _entry(b"ONYXBOOT   ", 0x08, 0) + _entry(b"EFI        ", 0x10, 3)
    efi = (_entry(b".          ", 0x10, 3) + _entry(b"..         ", 0x10, 0)
           + _entry(b"BOOT       ", 0x10, 4))
    boot_dir = (_entry(b".          ", 0x10, 4) + _entry(b"..         ", 0x10, 3)
                + _entry(ARCH_FILES[arch], 0x20, 5, len(executable)))
    for index, directory in enumerate((root, efi, boot_dir)):
        image[data + index * SECTOR:data + index * SECTOR + len(directory)] = directory
    image[data + 3 * SECTOR:data + 3 * SECTOR + len(executable)] = executable
    return image


def write_image(executable: Path, output: Path, arch: str) -> None:
    image = make_image(executable.read_bytes(), arch)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Refuse special devices and symlink destinations. No host disk operations.
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise ValueError("output must be a regular file")
    output.write_bytes(image)
