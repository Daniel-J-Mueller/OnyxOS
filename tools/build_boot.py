"""Cross-compile the bootstrap-only UEFI demonstrator with Clang and LLD."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from boot_image import write_image

ROOT = Path(__file__).resolve().parents[1]


def build(arch, output):
    clang = shutil.which(os.environ.get("CLANG", "clang"))
    linker = shutil.which(os.environ.get("LLD_LINK", "lld-link"))
    if not clang or not linker:
        raise SystemExit("Install LLVM Clang and lld-link, or set CLANG and LLD_LINK to their paths.")
    output.mkdir(parents=True, exist_ok=True)
    target = "aarch64-pc-windows-msvc" if arch == "aarch64" else "x86_64-pc-windows-msvc"
    obj = output / "bootlab.obj"
    efi = output / ("BOOTAA64.EFI" if arch == "aarch64" else "BOOTX64.EFI")
    command = [clang, f"--target={target}", "-std=c11", "-O2", "-ffreestanding",
               "-fno-stack-protector", "-fno-builtin", "-mno-stack-arg-probe",
               "-Wall", "-Wextra", "-Werror", "-g0", "-c",
               str(ROOT / "native/bootlab/bootlab.c"), "-o", str(obj)]
    command += ["-mgeneral-regs-only"] if arch == "aarch64" else ["-mno-red-zone"]
    subprocess.run(command, check=True)
    link = [linker, "/subsystem:efi_application", "/entry:efi_main", "/nodefaultlib",
            "/machine:" + ("arm64" if arch == "aarch64" else "x64"),
            "/dynamicbase", "/nxcompat", "/timestamp:0", "/opt:ref", "/opt:icf",
            f"/out:{efi}", str(obj)]
    subprocess.run(link, check=True)
    disk = output / f"OnyxOS-BootLab-{arch}.img"
    write_image(efi, disk, arch)
    metadata = {
        "architecture": arch, "stage": "firmware-application-not-kernel",
        "clang": subprocess.check_output([clang, "--version"], text=True).splitlines()[0],
        "linker": subprocess.check_output([linker, "--version"], text=True).strip(),
        "compile_arguments": command[1:], "link_arguments": link[1:],
        "files": {path.name: {"bytes": path.stat().st_size,
                              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in (efi, disk)},
    }
    (output / "build-info.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=("aarch64", "x86_64"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    build(args.arch, (args.output or ROOT / "build" / args.arch).resolve())
