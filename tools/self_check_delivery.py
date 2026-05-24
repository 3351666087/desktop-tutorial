from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "SELF_CHECK_REPORT.md"


REQUIRED_FILES = [
    "README.md",
    "docs/presentation/SmartClassroom_IoT104TC_Demo.pptx",
    "docs/SmartClassroom_Onsite_Assembly_Checklist.pdf",
    "docs/ASSEMBLY_CHECKLIST.md",
    "docs/ENV_SETUP_ZH.md",
    "docs/TEAM_FLOWCHART_ZH.md",
    "docs/SmartClassroom_Team_Flowchart_ZH.png",
    "docs/SPEECH_SCRIPT_BILINGUAL.md",
    "UNO_Phase3_TelemetryPatch/UNO_Phase3_TelemetryPatch.ino",
    "ESP32_3B_MQTT_Gateway/ESP32_3B_MQTT_Gateway.ino",
    "SmartClassroom_WebDashboard/server.js",
    "SmartClassroom_WebDashboard/public/app.js",
    "SmartClassroom_WebDashboard/public/styles.css",
    "run_smartclassroom.py",
    "smartclassroom_launcher.py",
]

PPT_KEYWORDS = [
    "SAFETY_ALARM",
    "Arduino UNO",
    "ESP32",
    "MQTT",
    "Dashboard",
    "Qwen",
    "ACK",
    "References",
    "self-check",
]

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile("0000" + "qwerty", re.IGNORECASE),
]

EXCLUDED_SCAN_PARTS = {
    ".git",
    ".vscode",
    "node_modules",
    "outputs",
    "__pycache__",
    "data",
    "logs",
}

EXCLUDED_SCAN_FILES = {
    "credentials.h",
    "package-lock.json",
}


@dataclass
class Check:
    name: str
    status: str
    detail: str


def add(checks: list[Check], name: str, status: str, detail: str) -> None:
    checks.append(Check(name=name, status=status, detail=detail))


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def check_required_files(checks: list[Check]) -> None:
    for item in REQUIRED_FILES:
        path = ROOT / item
        if path.exists() and path.stat().st_size > 0:
            add(checks, f"required file: {item}", "PASS", f"{path.stat().st_size:,} bytes")
        else:
            add(checks, f"required file: {item}", "FAIL", "missing or empty")


def ppt_text_from_zip(pptx: Path) -> tuple[int, int, str, list[float]]:
    slide_count = 0
    media_count = 0
    chunks: list[str] = []
    font_sizes: list[float] = []
    with zipfile.ZipFile(pptx) as zf:
        for name in zf.namelist():
            if re.match(r"ppt/slides/slide\d+\.xml$", name):
                slide_count += 1
                xml = zf.read(name).decode("utf-8", errors="ignore")
                chunks.append(xml)
                font_sizes.extend(int(value) / 100 for value in re.findall(r' sz="(\d+)"', xml))
            elif name.startswith("ppt/media/"):
                media_count += 1
    return slide_count, media_count, "\n".join(chunks), font_sizes


def check_ppt(checks: list[Check]) -> None:
    pptx = ROOT / "docs/presentation/SmartClassroom_IoT104TC_Demo.pptx"
    if not pptx.exists():
        add(checks, "pptx structure", "FAIL", "PPTX missing")
        return
    try:
        slide_count, media_count, text, font_sizes = ppt_text_from_zip(pptx)
    except zipfile.BadZipFile as exc:
        add(checks, "pptx structure", "FAIL", f"not a valid PPTX zip: {exc}")
        return

    add(checks, "pptx slide count", "PASS" if slide_count >= 16 else "FAIL", f"{slide_count} slides")
    add(checks, "pptx embedded media", "PASS" if media_count >= 4 else "WARN", f"{media_count} media files")
    if font_sizes:
        min_font = min(font_sizes)
        add(checks, "pptx minimum font size", "PASS" if min_font >= 16 else "FAIL", f"{min_font:.1f} pt")
    else:
        add(checks, "pptx minimum font size", "WARN", "no explicit font sizes found")

    normalized = re.sub(r"<[^>]+>", " ", text)
    for keyword in PPT_KEYWORDS:
        status = "PASS" if keyword.lower() in normalized.lower() else "WARN"
        add(checks, f"ppt keyword: {keyword}", status, "present" if status == "PASS" else "not found in slide XML")


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        parts = set(path.relative_to(ROOT).parts)
        if parts & EXCLUDED_SCAN_PARTS:
            continue
        if path.name in EXCLUDED_SCAN_FILES:
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".pptx", ".pdf", ".zip", ".exe", ".dll"}:
            continue
        files.append(path)
    return files


def check_secrets(checks: list[Check]) -> None:
    hits: list[str] = []
    for path in iter_source_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(rel(path))
                break
    if hits:
        add(checks, "sensitive key scan", "FAIL", "possible secret in: " + ", ".join(sorted(set(hits))))
    else:
        add(checks, "sensitive key scan", "PASS", "no obvious API keys in tracked delivery files")


def run_command(command: list[str], timeout: int = 60) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        shell=False,
    )
    return proc.returncode, proc.stdout.strip()


def check_optional_commands(checks: list[Check], compile_checks: bool) -> None:
    node_targets = [
        "SmartClassroom_WebDashboard/server.js",
        "SmartClassroom_WebDashboard/public/app.js",
    ]
    for target in node_targets:
        code, output = run_command(["node", "--check", target])
        add(checks, f"node syntax: {target}", "PASS" if code == 0 else "FAIL", output[-600:] or "ok")

    py_targets = ["run_smartclassroom.py", "smartclassroom_launcher.py", "tools/generate_team_flowchart.py"]
    for target in py_targets:
        code, output = run_command([sys.executable, "-m", "py_compile", target])
        add(checks, f"python syntax: {target}", "PASS" if code == 0 else "FAIL", output[-600:] or "ok")

    if not compile_checks:
        add(checks, "arduino compile", "WARN", "skipped by default; run with --compile to verify board toolchains")
        return

    commands = [
        ["arduino-cli", "compile", "--fqbn", "arduino:avr:uno", "UNO_Phase3_TelemetryPatch"],
        [
            "arduino-cli",
            "--config-file",
            "arduino-cli-esp32.yaml",
            "compile",
            "--fqbn",
            "esp32:esp32:esp32",
            "ESP32_3B_MQTT_Gateway",
        ],
    ]
    for command in commands:
        code, output = run_command(command, timeout=180)
        add(checks, "arduino compile: " + command[-1], "PASS" if code == 0 else "FAIL", output[-900:] or "ok")


def write_report(checks: list[Check]) -> None:
    counts = {key: sum(1 for item in checks if item.status == key) for key in ("PASS", "WARN", "FAIL")}
    lines = [
        "# Smart Classroom Delivery Self-Check",
        "",
        f"- Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Root: `{ROOT}`",
        f"- Summary: PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}",
        "",
        "| Status | Check | Detail |",
        "| --- | --- | --- |",
    ]
    for item in checks:
        detail = item.detail.replace("|", "\\|").replace("\n", "<br>")
        lines.append(f"| {item.status} | {item.name} | {detail} |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Self-check the Smart Classroom final delivery package.")
    parser.add_argument("--compile", action="store_true", help="also run Arduino compile checks")
    args = parser.parse_args()

    checks: list[Check] = []
    check_required_files(checks)
    check_ppt(checks)
    check_secrets(checks)
    check_optional_commands(checks, compile_checks=args.compile)
    write_report(checks)

    print(REPORT)
    for status in ("FAIL", "WARN", "PASS"):
        count = sum(1 for item in checks if item.status == status)
        print(f"{status}: {count}")
    return 1 if any(item.status == "FAIL" for item in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
