import struct
import unittest
import zlib

from tools.boot_image import END, SECTOR, SECTORS, START, make_image
from tools.run_vm import qemu_command


def fake_pe(arch="x86_64"):
    data = bytearray(2049)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, 0x8664 if arch == "x86_64" else 0xAA64)
    struct.pack_into("<H", data, 88, 0x20B)
    struct.pack_into("<H", data, 156, 10)
    data[-7:] = b"PAYLOAD"
    return bytes(data)


class DiskFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = fake_pe()
        cls.image = make_image(cls.payload, "x86_64")

    def test_primary_and_backup_gpt_crc_and_locations(self):
        image = self.image
        self.assertEqual(len(image), SECTORS * SECTOR)
        self.assertEqual(image[510:512], b"\x55\xaa")
        for lba, peer, table_lba in ((1, SECTORS - 1, 2), (SECTORS - 1, 1, SECTORS - 33)):
            header = bytearray(image[lba * SECTOR:lba * SECTOR + 92])
            self.assertEqual(header[:8], b"EFI PART")
            crc = struct.unpack_from("<I", header, 16)[0]
            struct.pack_into("<I", header, 16, 0)
            self.assertEqual(crc, zlib.crc32(header))
            self.assertEqual(struct.unpack_from("<QQ", header, 24), (lba, peer))
            self.assertEqual(struct.unpack_from("<Q", header, 72)[0], table_lba)
            table = image[table_lba * SECTOR:table_lba * SECTOR + 16384]
            self.assertEqual(struct.unpack_from("<I", header, 88)[0], zlib.crc32(table))
            self.assertEqual(struct.unpack_from("<QQ", table, 32), (START, END))

    def test_fat32_directory_chain_and_payload_roundtrip(self):
        image = self.image
        base = START * SECTOR
        reserved = struct.unpack_from("<H", image, base + 14)[0]
        fat_sectors = struct.unpack_from("<I", image, base + 36)[0]
        total = struct.unpack_from("<I", image, base + 32)[0]
        self.assertGreaterEqual(total - reserved - 2 * fat_sectors, 65525)
        fat = base + reserved * SECTOR
        self.assertEqual(image[fat:fat + fat_sectors * SECTOR],
                         image[fat + fat_sectors * SECTOR:fat + 2 * fat_sectors * SECTOR])
        data = fat + 2 * fat_sectors * SECTOR
        self.assertEqual(image[data + 32:data + 43], b"EFI        ")
        self.assertEqual(image[data + SECTOR + 64:data + SECTOR + 75], b"BOOT       ")
        entry = data + 2 * SECTOR + 64
        self.assertEqual(image[entry:entry + 11], b"BOOTX64 EFI")
        cluster = struct.unpack_from("<H", image, entry + 26)[0]
        size = struct.unpack_from("<I", image, entry + 28)[0]
        recovered = bytearray()
        seen = set()
        while cluster < 0x0FFFFFF8:
            self.assertNotIn(cluster, seen)
            seen.add(cluster)
            offset = data + (cluster - 2) * SECTOR
            recovered += image[offset:offset + SECTOR]
            cluster = struct.unpack_from("<I", image, fat + cluster * 4)[0] & 0x0FFFFFFF
        self.assertEqual(recovered[:size], self.payload)
        self.assertEqual(image[base:base + SECTOR], image[base + 6 * SECTOR:base + 7 * SECTOR])

    def test_wrong_architecture_and_malformed_pe_rejected(self):
        for payload, arch in ((self.payload, "aarch64"), (b"MZ", "x86_64"),
                              (b"MZ" + b"\xff" * 128, "x86_64"), (self.payload, "other")):
            with self.assertRaises(ValueError):
                make_image(payload, arch)

    def test_aarch64_removable_boot_path(self):
        image = make_image(fake_pe("aarch64"), "aarch64")
        self.assertIn(b"BOOTAA64EFI", image)

    def test_deterministic_image(self):
        self.assertEqual(self.image, make_image(self.payload, "x86_64"))


class LauncherTests(unittest.TestCase):
    def test_no_network_snapshot_and_separate_nvram(self):
        command = qemu_command("aarch64", "qemu", "disk with space.img", "code.fd", "private.fd")
        self.assertEqual(command[command.index("-nic") + 1], "none")
        self.assertTrue(any("snapshot=on" in part for part in command))
        self.assertTrue(any("readonly=on,file=code.fd" in part for part in command))
        self.assertTrue(any("unit=1,file=private.fd" in part for part in command))
        self.assertNotIn("-virtfs", command)
        self.assertIn("cortex-a72", command)

    def test_qemu_filename_delimiter_escaped(self):
        command = qemu_command("x86_64", "qemu", "a,b.img", "c,d.fd", "v.fd")
        self.assertTrue(any("file=a,,b.img" in part for part in command))


if __name__ == "__main__":
    unittest.main()
