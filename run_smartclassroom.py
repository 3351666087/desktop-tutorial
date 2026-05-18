#!/usr/bin/env python
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENV_NAME = "smartclassroom-uno-console"


def find_conda() -> str | None:
    found = shutil.which("conda")
    if found:
        return found
    for candidate in [
        Path("D:/conda/condabin/conda.bat"),
        Path.home() / ".conda" / "condabin" / "conda.bat",
        Path.home() / "miniconda3" / "condabin" / "conda.bat",
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def conda_cmd(conda: str, args: list[str]) -> list[str]:
    if conda.lower().endswith((".bat", ".cmd")):
        return ["cmd.exe", "/d", "/c", conda, *args]
    return [conda, *args]


def main() -> int:
    conda = find_conda()
    if not conda:
        print("conda not found")
        return 2
    envs = json.loads(subprocess.check_output(conda_cmd(conda, ["env", "list", "--json"]), text=True))
    if not any(Path(env).name == ENV_NAME for env in envs.get("envs", [])):
        subprocess.check_call(conda_cmd(conda, ["create", "-n", ENV_NAME, "python=3.11", "-y"]), cwd=ROOT)
    subprocess.check_call(conda_cmd(conda, ["run", "-n", ENV_NAME, "python", str(ROOT / "smartclassroom_launcher.py")]), cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
