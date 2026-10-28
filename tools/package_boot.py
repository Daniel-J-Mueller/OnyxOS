"""Package only our image, launcher, source reference and measured boot evidence."""

import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def write_member(bundle, name, content, executable=False):
    entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.create_system = 3
    entry.external_attr = (0o100755 if executable else 0o100644) << 16
    bundle.writestr(entry, content)


def package(arch, directory):
    destination = directory / f"OnyxOS-BootLab-{arch}.zip"
    disk_name = f"OnyxOS-BootLab-{arch}.img"
    launcher = ("#!/bin/bash\nset -euo pipefail\n"
                'here="$(cd -- "$(dirname -- "$0")" && pwd)"\n'
                'if ! command -v python3 >/dev/null 2>&1; then\n'
                "  echo 'Install prerequisites: brew install qemu python' >&2\n  exit 1\nfi\n"
                f'exec python3 "$here/run_vm.py" --arch {arch} --disk "$here/{disk_name}" "$@"\n')
    readme = f"""OnyxOS Boot Lab — {arch}

Experimental native UEFI application. It remains inside firmware services.
There is no Onyx kernel, process isolation, storage stack, GPU acceleration,
pointer-input implementation, or custom language compiler in this build.
Task labels describe the single app and illustrative panels, not real processes.

Mac quick start:
1. Install Homebrew if needed using its official instructions at https://brew.sh/.
2. Run: brew install qemu python
3. Unzip this folder, open Terminal here, and run: bash run-macos.command
   (If executable permissions survive extraction, double-click is also possible.)
4. Click the VM window; f toggles Fit, [ and ] cycle presets, q returns to firmware.
   F8/F9/F10 are alternatives; your Mac may require Fn for function keys.
5. Close the QEMU window to stop the VM.

Apple Silicon should use the aarch64 bundle. Intel should use x86_64.
TCG emulation is the default; no native Mac/HVF test has been performed here.
Optional same-architecture acceleration: bash run-macos.command --accel hvf
If firmware discovery fails, supply --code PATH --vars PATH from the same QEMU
firmware distribution. No firmware is bundled. No network or host folders are
attached; disk writes use a temporary overlay and NVRAM is copied per run.

See included evidence/smoke.json for the precise Linux/QEMU verification scope.
Source and detailed instructions:
https://github.com/Daniel-J-Mueller/OnyxOS
https://github.com/Daniel-J-Mueller/OnyxOS/blob/main/docs/macos-vm.md

Project distribution licensing remains undecided. This bundle contains original
Onyx project files, not QEMU, firmware, a Linux image, or other third-party code.
"""
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in (directory / disk_name, directory / "build-info.json"):
            write_member(bundle, path.name, path.read_bytes())
        write_member(bundle, "run_vm.py", (ROOT / "tools/run_vm.py").read_bytes())
        write_member(bundle, "run-macos.command", launcher.encode(), True)
        write_member(bundle, "README.txt", readme.encode())
        for path in sorted((directory / "evidence").glob("*")):
            if path.is_file():
                write_member(bundle, "evidence/" + path.name, path.read_bytes())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (directory / f"{destination.name}.sha256").write_text(f"{digest}  {destination.name}\n", encoding="ascii")
    print(f"{destination}: {destination.stat().st_size} bytes, SHA256 {digest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=("aarch64", "x86_64"))
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    package(args.arch, args.directory.resolve())
