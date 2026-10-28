"""Boot both real EFI binaries in QEMU and verify state changes and pixels.

Runs on Linux with QMP Unix sockets. Results are emulator evidence, not evidence
of a macOS host, HVF, physical hardware, GPU acceleration, or a post-firmware OS.
"""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

from run_vm import firmware, qemu_command


class QMP:
    def __init__(self, path, process):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(10)
        deadline = time.monotonic() + 20
        while True:
            try:
                self.socket.connect(str(path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("QEMU did not open QMP")
                time.sleep(0.1)
        self.stream = self.socket.makefile("rwb")
        greeting = json.loads(self.stream.readline())
        if "QMP" not in greeting:
            raise RuntimeError("Missing QMP greeting")
        self.sequence = 0
        self.call("qmp_capabilities")

    def call(self, name, arguments=None):
        self.sequence += 1
        command = {"execute": name, "id": self.sequence}
        if arguments is not None:
            command["arguments"] = arguments
        self.stream.write(json.dumps(command).encode() + b"\n")
        self.stream.flush()
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("QMP closed unexpectedly")
            response = json.loads(line)
            if response.get("id") != self.sequence:
                continue
            if "error" in response:
                raise RuntimeError(f"{name}: {response['error']}")
            return response.get("return")

    def close(self):
        self.stream.close()
        self.socket.close()


def wait_marker(log, marker, process, offset=0, timeout=120):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        content = log.read_bytes() if log.exists() else b""
        if marker.encode("ascii") in content[offset:]:
            return len(content)
        if process.poll() is not None:
            raise RuntimeError(f"QEMU exited before {marker}")
        time.sleep(0.05)
    raise RuntimeError(f"Timed out waiting for {marker}; inspect {log}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=("aarch64", "x86_64"))
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    output = args.directory.resolve()
    evidence = output / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    executable = shutil.which("qemu-system-" + args.arch)
    if not executable:
        raise SystemExit("QEMU is required")
    code, template = firmware(args.arch, executable)
    disk = output / f"OnyxOS-BootLab-{args.arch}.img"
    serial = evidence / "serial.log"
    report = {"architecture": args.arch, "host": "Linux CI", "accelerator": "tcg",
              "firmware_application": True, "exit_boot_services": False,
              "qemu": subprocess.check_output([executable, "--version"], text=True).splitlines()[0],
              "firmware_sha256": hashlib.sha256(code.read_bytes()).hexdigest(),
              "disk_sha256": hashlib.sha256(disk.read_bytes()).hexdigest(),
              "checks": [], "success": False}
    try:
        with tempfile.TemporaryDirectory(prefix="onyx-smoke-") as temporary:
            temp = Path(temporary)
            variables = temp / "vars.fd"
            shutil.copyfile(template, variables)
            command = qemu_command(args.arch, executable, disk, code, variables,
                                   display="none", qmp=temp / "qmp", serial=serial)
            report["command"] = command
            with (evidence / "qemu.log").open("wb") as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                qmp = None
                try:
                    qmp = QMP(temp / "qmp", process)
                    wait_marker(serial, "ONYX_BOOTLAB_READY", process)
                    wait_marker(serial, "GRAPHICS=1", process, timeout=5)
                    report["checks"].append("native EFI reached graphics-ready state")
                    qmp.call("screendump", {"filename": str(evidence / "standard.png"), "format": "png"})
                    steps = [("f", "fit", 0, "fit"), ("bracket_right", "fit", 1, "preset-next"),
                             ("bracket_left", "fit", 0, "preset-previous"), ("f", "standard", 0, "restored")]
                    for key, mode, preset, name in steps:
                        offset = serial.stat().st_size
                        qmp.call("send-key", {"keys": [{"type": "qcode", "data": key}], "hold-time": 30})
                        wait_marker(serial, f"ONYX_STATE {mode} preset={preset}", process, offset, 15)
                        qmp.call("screendump", {"filename": str(evidence / f"{name}.png"), "format": "png"})
                        report["checks"].append(f"{key}: {mode}, preset={preset}")
                    if (evidence / "standard.png").read_bytes() != (evidence / "restored.png").read_bytes():
                        raise RuntimeError("Standard-mode pixels did not restore exactly")
                    if (evidence / "standard.png").read_bytes() == (evidence / "fit.png").read_bytes():
                        raise RuntimeError("Fit mode did not change the captured desktop")
                    report["checks"].append("exact standard framebuffer restoration and distinct Fit frame")
                    offset = serial.stat().st_size
                    qmp.call("send-key", {"keys": [{"type": "qcode", "data": "q"}], "hold-time": 30})
                    wait_marker(serial, "ONYX_BOOTLAB_EXIT", process, offset, 15)
                    report["checks"].append("explicit return-to-firmware path")
                    qmp.call("quit")
                    process.wait(timeout=10)
                    report["success"] = True
                finally:
                    if qmp:
                        qmp.close()
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
    except Exception as error:
        report["failure"] = str(error)
        raise
    finally:
        (evidence / "smoke.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
