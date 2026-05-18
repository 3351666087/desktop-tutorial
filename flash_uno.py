#!/usr/bin/env python
"""
Create/reuse a dedicated conda environment, then compile and upload the
Arduino UNO sketches for the Smart Classroom Phase 1 hardware node.

Default:
  python flash_uno.py

Relay-only test:
  python flash_uno.py --sketch relay

Phase 2 safety-module test:
  python flash_uno.py --sketch phase2test

Phase 2 integrated sketch:
  python flash_uno.py --sketch phase2

Hybrid union sketch:
  python flash_uno.py --sketch hybrid

Phase 3 UNO telemetry patch:
  python flash_uno.py --sketch phase3

Open serial monitor after upload:
  python flash_uno.py --monitor
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ENV_NAME = "smartclassroom-uno-flash"
DEFAULT_FQBN = "arduino:avr:uno"
CORE_ID = "arduino:avr"
REQUIRED_LIBRARIES: tuple[str, ...] = ()

ROOT = Path(__file__).resolve().parent
SKETCHES = {
    "phase1": ROOT / "SmartClassroom_UNO_Phase1",
    "phase2": ROOT / "SmartClassroom_UNO_Phase2",
    "phase2test": ROOT / "Phase2_SafetyModules_Test",
    "hybrid": ROOT / "SmartClassroom_UNO_Hybrid",
    "phase3": ROOT / "UNO_Phase3_TelemetryPatch",
    "relay": ROOT / "Relay_Fan_Test",
}


def quote_cmd(cmd: list[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in cmd])


def run(
    cmd: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    show_command: bool = True,
    show_output: bool = True,
) -> subprocess.CompletedProcess:
    if show_command:
        print(f"\n$ {quote_cmd(cmd)}", flush=True)
    result = subprocess.run(
        [str(part) for part in cmd],
        cwd=ROOT,
        text=True,
        capture_output=capture,
    )

    if capture and show_output:
        if result.stdout:
            print(result.stdout.rstrip(), flush=True)
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr, flush=True)

    if check and result.returncode != 0:
        raise SystemExit(result.returncode)

    return result


def find_conda() -> str | None:
    found = shutil.which("conda")
    if found:
        return found

    candidates = [
        Path("D:/conda/condabin/conda.bat"),
        Path.home() / "miniconda3" / "condabin" / "conda.bat",
        Path.home() / "anaconda3" / "condabin" / "conda.bat",
        Path.home() / "mambaforge" / "condabin" / "conda.bat",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def conda_cmd(conda: str, args: list[str]) -> list[str]:
    if conda.lower().endswith((".bat", ".cmd")):
        return ["cmd.exe", "/d", "/c", conda, *args]
    return [conda, *args]


def conda_env_exists(conda: str, env_name: str) -> bool:
    result = run(conda_cmd(conda, ["env", "list", "--json"]), capture=True, show_command=False, show_output=False)
    try:
        envs = json.loads(result.stdout).get("envs", [])
    except json.JSONDecodeError:
        return False

    return any(Path(env_path).name == env_name for env_path in envs)


def bootstrap_conda_env(args: argparse.Namespace) -> None:
    if args.no_conda_bootstrap:
        return

    if os.environ.get("CONDA_DEFAULT_ENV") == args.env_name:
        return

    conda = find_conda()
    if not conda:
        raise SystemExit(
            "conda was not found. Install Miniconda/Anaconda or add conda to PATH, "
            "then run: python flash_uno.py"
        )

    if not conda_env_exists(conda, args.env_name):
        run(conda_cmd(conda, ["create", "-n", args.env_name, "python=3.11", "-y"]))
    else:
        print(f"\nConda env already exists: {args.env_name}", flush=True)

    passthrough_args = [arg for arg in sys.argv[1:] if arg != "--no-conda-bootstrap"]
    relaunch = conda_cmd(
        conda,
        ["run", "-n", args.env_name, "python", Path(__file__).name, "--no-conda-bootstrap", *passthrough_args],
    )
    result = run(relaunch, check=False)
    raise SystemExit(result.returncode)


def find_arduino_cli() -> str:
    found = shutil.which("arduino-cli")
    if found:
        return found

    candidates = [
        Path.home() / "scoop" / "shims" / "arduino-cli.exe",
        Path.home() / "scoop" / "apps" / "arduino-cli" / "current" / "arduino-cli.exe",
        Path("C:/Program Files/Arduino CLI/arduino-cli.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise SystemExit(
        "arduino-cli was not found. Install it first, for example:\n"
        "  scoop install arduino-cli"
    )


def ensure_core(arduino_cli: str) -> None:
    result = run([arduino_cli, "core", "list"], capture=True, show_command=False, show_output=False)
    if CORE_ID in result.stdout:
        print(f"\nArduino core already installed: {CORE_ID}", flush=True)
        return

    run([arduino_cli, "core", "update-index"])
    run([arduino_cli, "core", "install", CORE_ID])


def ensure_libraries(arduino_cli: str) -> None:
    if not REQUIRED_LIBRARIES:
        print("\nNo external Arduino libraries required for the selected sketches.", flush=True)
        return

    result = run([arduino_cli, "lib", "list"], capture=True, show_command=False, show_output=False)
    installed = result.stdout

    missing = []
    for library in REQUIRED_LIBRARIES:
        if not re.search(rf"^{re.escape(library)}\s", installed, flags=re.MULTILINE):
            missing.append(library)

    if not missing:
        print("\nArduino libraries already installed: " + ", ".join(REQUIRED_LIBRARIES), flush=True)
        return

    run([arduino_cli, "lib", "install", *missing])


def detect_uno_port(arduino_cli: str, fqbn: str) -> str:
    result = run([arduino_cli, "board", "list"], capture=True, show_command=False, show_output=False)
    lines = result.stdout.splitlines()

    for line in lines:
        if fqbn in line:
            return line.split()[0]

    ports = []
    for line in lines:
        match = re.match(r"^(COM\d+)\s+", line, flags=re.IGNORECASE)
        if match:
            ports.append(match.group(1).upper())

    unique_ports = sorted(set(ports))
    if len(unique_ports) == 1:
        return unique_ports[0]

    if unique_ports:
        raise SystemExit(
            "Could not identify the UNO automatically. Available serial ports: "
            + ", ".join(unique_ports)
            + "\nRun again with: python flash_uno.py --port COM5"
        )

    raise SystemExit("No serial port found. Connect the Arduino UNO and run again.")


def compile_sketch(arduino_cli: str, fqbn: str, sketch_path: Path) -> None:
    run([arduino_cli, "compile", "--fqbn", fqbn, str(sketch_path.relative_to(ROOT))])


def upload_sketch(arduino_cli: str, fqbn: str, port: str, sketch_path: Path) -> None:
    run([arduino_cli, "upload", "-p", port, "--fqbn", fqbn, str(sketch_path.relative_to(ROOT))])


def open_monitor(arduino_cli: str, port: str, baud: int) -> None:
    print("\nOpening serial monitor. Press Ctrl+C to close it.", flush=True)
    run([arduino_cli, "monitor", "-p", port, "-c", f"baudrate={baud}"], check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile and upload Smart Classroom Arduino UNO sketches.")
    parser.add_argument("--sketch", choices=sorted(SKETCHES), default="phase1", help="Sketch to upload. Default: phase1")
    parser.add_argument("--port", help="Arduino serial port, for example COM5. Default: auto-detect")
    parser.add_argument("--fqbn", default=DEFAULT_FQBN, help=f"Arduino board FQBN. Default: {DEFAULT_FQBN}")
    parser.add_argument("--baud", type=int, default=9600, help="Serial monitor baud rate. Default: 9600")
    parser.add_argument("--monitor", action="store_true", help="Open arduino-cli serial monitor after upload")
    parser.add_argument("--no-upload", action="store_true", help="Compile only; do not upload")
    parser.add_argument("--no-compile", action="store_true", help="Upload without compiling first")
    parser.add_argument("--env-name", default=ENV_NAME, help=f"Conda environment name. Default: {ENV_NAME}")
    parser.add_argument("--no-conda-bootstrap", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bootstrap_conda_env(args)

    sketch_path = SKETCHES[args.sketch]
    if not sketch_path.exists():
        raise SystemExit(f"Sketch folder not found: {sketch_path}")

    arduino_cli = find_arduino_cli()
    print(f"\nUsing arduino-cli: {arduino_cli}", flush=True)
    print(f"Using sketch: {sketch_path.name}", flush=True)

    ensure_core(arduino_cli)
    ensure_libraries(arduino_cli)

    port = args.port or detect_uno_port(arduino_cli, args.fqbn)
    print(f"\nUsing port: {port}", flush=True)

    if not args.no_compile:
        compile_sketch(arduino_cli, args.fqbn, sketch_path)

    if not args.no_upload:
        upload_sketch(arduino_cli, args.fqbn, port, sketch_path)
        print(f"\nUpload complete: {sketch_path.name} -> {port}", flush=True)
    else:
        print("\nUpload skipped because --no-upload was set.", flush=True)

    if args.monitor:
        open_monitor(arduino_cli, port, args.baud)


if __name__ == "__main__":
    main()
