#!/usr/bin/env python
"""
Bootstrap and launch the PySide6 Smart Classroom UNO serial console.

Usage:
  python run_console.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ENV_NAME = "smartclassroom-uno-console"
REQUIRED_PACKAGES = ("PySide6", "pyserial")
ROOT = Path(__file__).resolve().parent


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
        raise SystemExit("conda was not found. Install Miniconda/Anaconda or add conda to PATH.")

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


def ensure_python_packages() -> None:
    missing = []
    checks = {
        "PySide6": "PySide6",
        "pyserial": "serial",
    }

    for package_name, import_name in checks.items():
        result = subprocess.run(
            [sys.executable, "-c", f"import {import_name}"],
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            missing.append(package_name)

    if not missing:
        print("\nPython packages already installed: " + ", ".join(REQUIRED_PACKAGES), flush=True)
        return

    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run([sys.executable, "-m", "pip", "install", *missing])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the Smart Classroom UNO PySide6 console.")
    parser.add_argument("--env-name", default=ENV_NAME, help=f"Conda environment name. Default: {ENV_NAME}")
    parser.add_argument("--no-conda-bootstrap", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--check", action="store_true", help="Create/check the environment and dependencies, then exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bootstrap_conda_env(args)
    ensure_python_packages()

    if args.check:
        print("\nConsole environment is ready.", flush=True)
        return

    run([sys.executable, str(ROOT / "uno_console.py")])


if __name__ == "__main__":
    main()
