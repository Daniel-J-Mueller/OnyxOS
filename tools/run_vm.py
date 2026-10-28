"""Run a disposable OnyxOS Boot Lab VM. Never attaches host disks or networking."""

import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile


def firmware(arch, executable, code=None, variables=None):
    roots = [Path("/opt/homebrew/share/qemu"), Path("/usr/local/share/qemu"),
             Path("/usr/share/qemu"), Path("/usr/share/AAVMF"), Path("/usr/share/OVMF")]
    if executable:
        roots.insert(0, Path(executable).resolve().parent.parent / "share/qemu")
    pairs = ([('edk2-aarch64-code.fd', 'edk2-aarch64-vars.fd'),
              ('edk2-aarch64-code.fd', 'edk2-arm-vars.fd'),
              ('AAVMF_CODE.fd', 'AAVMF_VARS.fd')]
             if arch == "aarch64" else
             [('edk2-x86_64-code.fd', 'edk2-i386-vars.fd'),
              ('edk2-x86_64-code.fd', 'edk2-x86_64-vars.fd'),
              ('OVMF_CODE_4M.fd', 'OVMF_VARS_4M.fd'),
              ('OVMF_CODE.fd', 'OVMF_VARS.fd')])
    if (code is None) != (variables is None):
        raise ValueError("Provide both --code and --vars from the same firmware build")
    if code is not None:
        found = (Path(code).resolve(), Path(variables).resolve())
    else:
        found = next(((root / c, root / v) for root in roots for c, v in pairs
                      if (root / c).is_file() and (root / v).is_file()), None)
    if found is None or not all(path.is_file() for path in found):
        raise ValueError("UEFI firmware not found; install QEMU firmware or provide --code and --vars")
    return found


def qemu_command(arch, executable, disk, code, variables, accel="tcg", display="none", qmp=None, serial=None):
    if arch not in ("aarch64", "x86_64") or accel not in ("tcg", "hvf"):
        raise ValueError("unsupported architecture or accelerator")
    # QEMU's comma-delimited drive grammar is escaped by doubling literal commas.
    escaped = lambda path: str(path).replace(",", ",,")
    args = [str(executable), "-machine", "virt" if arch == "aarch64" else "q35",
            "-accel", accel, "-cpu", "host" if accel == "hvf" else ("cortex-a72" if arch == "aarch64" else "qemu64"),
            "-m", "512", "-smp", "2", "-no-reboot", "-nic", "none",
            "-drive", f"if=pflash,format=raw,unit=0,readonly=on,file={escaped(code)}",
            "-drive", f"if=pflash,format=raw,unit=1,file={escaped(variables)}",
            "-drive", f"if=none,id=onyxdisk,format=raw,snapshot=on,file={escaped(disk)}",
            "-device", "virtio-blk-pci,drive=onyxdisk", "-device", "ramfb" if arch == "aarch64" else "VGA",
            "-device", "qemu-xhci", "-device", "usb-kbd", "-boot", "menu=off,strict=on",
            "-display", display, "-monitor", "none"]
    args += ["-serial", f"file:{serial}" if serial else "stdio"]
    if qmp:
        args += ["-qmp", f"unix:{qmp},server=on,wait=off"]
    return args


@contextmanager
def session_variables(template):
    # QEMU may update UEFI NVRAM. Copy it to a fresh directory for each run.
    with tempfile.TemporaryDirectory(prefix="onyx-bootlab-") as directory:
        destination = Path(directory) / "variables.fd"
        shutil.copyfile(template, destination)
        yield destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=("aarch64", "x86_64"))
    parser.add_argument("--disk", required=True, type=Path)
    parser.add_argument("--code", type=Path)
    parser.add_argument("--vars", type=Path)
    parser.add_argument("--accel", choices=("tcg", "hvf"), default="tcg")
    parser.add_argument("--display", choices=("cocoa", "gtk", "none"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    executable = shutil.which("qemu-system-" + args.arch)
    if not executable:
        parser.error(f"qemu-system-{args.arch} is not installed or is not on PATH")
    disk = args.disk.resolve()
    if not disk.is_file() or disk.is_symlink():
        parser.error("--disk must identify a regular image file")
    if args.accel == "hvf":
        host = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x86_64"}.get(platform.machine())
        if platform.system() != "Darwin" or host != args.arch:
            parser.error("HVF requires macOS and a guest matching the host CPU architecture; use TCG")
    try:
        code, template = firmware(args.arch, executable, args.code, args.vars)
    except ValueError as error:
        parser.error(str(error))
    display = args.display or ("cocoa" if platform.system() == "Darwin" else "gtk")
    with session_variables(template) as variables:
        command = qemu_command(args.arch, executable, disk, code, variables, args.accel, display)
        print("OnyxOS Boot Lab: firmware application, no kernel isolation or persistent storage.", flush=True)
        print("F/f: Fit | [/]: presets | Q/q: firmware exit. Close the VM window to stop.", flush=True)
        if args.dry_run:
            print(json.dumps(command, indent=2))
            return 0
        return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
