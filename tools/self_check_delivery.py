from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from PIL import ImageFont
except ImportError:  # pragma: no cover - the check still runs with rough estimates.
    ImageFont = None


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "SELF_CHECK_REPORT.md"
LAYOUT_DIR = ROOT / "docs" / "presentation" / "layout"


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


def is_transparent(value: str | None) -> bool:
    if value is None:
        return True
    lowered = str(value).lower()
    return lowered in {"none", "transparent"} or "rgba(0, 0, 0, 0)" in lowered or lowered.endswith("00")


def bbox_area(bbox: list[float]) -> float:
    return max(0.0, bbox[2]) * max(0.0, bbox[3])


def contains_bbox(outer: list[float], inner: list[float], margin: float = 0.0) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (
        ix >= ox - margin
        and iy >= oy - margin
        and ix + iw <= ox + ow + margin
        and iy + ih <= oy + oh + margin
    )


def center_inside(outer: list[float], inner: list[float]) -> bool:
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    cx = ix + iw / 2
    cy = iy + ih / 2
    return ox <= cx <= ox + ow and oy <= cy <= oy + oh


@lru_cache(maxsize=128)
def load_font(font_size: int, bold: bool = False):
    if ImageFont is None:
        return None
    candidates = [
        Path("C:/Windows/Fonts/aptos.ttf"),
        Path("C:/Windows/Fonts/aptosdisplay.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), font_size)
    return ImageFont.load_default()


def estimate_text_width(text: str, font_size: float, bold: bool = False) -> float:
    text = text or ""
    font = load_font(max(1, round(font_size)), bold)
    if font is not None:
        left, _, right, _ = font.getbbox(text)
        return max(0, right - left)
    wide = sum(1 for ch in text if ord(ch) > 127)
    narrow = len(text) - wide
    return wide * font_size + narrow * font_size * 0.55


def text_lines(element: dict) -> list[str]:
    lines = element.get("textLayout", {}).get("lines") or []
    extracted = [str(line.get("text", "")) for line in lines if str(line.get("text", ""))]
    if extracted:
        return extracted
    return str(element.get("text", "")).splitlines() or [str(element.get("text", ""))]


def is_container_shape(element: dict) -> bool:
    if element.get("kind") != "shape" or element.get("text"):
        return False
    bbox = element.get("bbox") or [0, 0, 0, 0]
    if len(bbox) != 4:
        return False
    _, _, width, height = bbox
    if width < 50 or height < 28:
        return False
    if width > 1180 and height > 640:
        return False
    has_fill = not is_transparent(element.get("fillColor"))
    has_line = not is_transparent(element.get("lineColor")) and float(element.get("lineWidth") or 0) > 0
    return has_fill or has_line


def check_layout_text_fit(checks: list[Check]) -> None:
    if not LAYOUT_DIR.exists():
        add(checks, "ppt layout QA", "WARN", f"layout JSON not found: {rel(LAYOUT_DIR)}")
        return

    layout_files = sorted(LAYOUT_DIR.glob("slide-*.layout.json"))
    if not layout_files:
        add(checks, "ppt layout QA", "WARN", f"no slide layout JSON in {rel(LAYOUT_DIR)}")
        return

    frame_issues: list[str] = []
    overflow_issues: list[str] = []
    container_issues: list[str] = []

    for layout_file in layout_files:
        data = json.loads(layout_file.read_text(encoding="utf-8"))
        slide_no = data.get("slide", {}).get("slide") or layout_file.stem
        slide_frame = data.get("slide", {}).get("frame", {"width": 1280, "height": 720})
        slide_bbox = [0, 0, float(slide_frame.get("width", 1280)), float(slide_frame.get("height", 720))]
        elements = data.get("elements", [])
        containers = [element for element in elements if is_container_shape(element)]

        for element in elements:
            text = str(element.get("text", "")).strip()
            if not text:
                continue
            bbox = [float(value) for value in element.get("bbox", [0, 0, 0, 0])]
            if not contains_bbox(slide_bbox, bbox, margin=1):
                frame_issues.append(f"S{slide_no} text '{text[:32]}' outside slide bbox {bbox}")

            style = element.get("resolvedTextStyle", {})
            insets = style.get("insets") or {}
            font_size = float(element.get("resolvedFontSize") or style.get("fontSize") or 18)
            bold = bool(style.get("bold"))
            content_width = max(1.0, bbox[2] - float(insets.get("left", 0)) - float(insets.get("right", 0)))
            content_height = max(1.0, bbox[3] - float(insets.get("top", 0)) - float(insets.get("bottom", 0)))
            lines = text_lines(element)
            max_line_width = max((estimate_text_width(line, font_size, bold) for line in lines), default=0)
            estimated_height = len(lines) * font_size * 1.08
            width_tolerance = max(12.0, content_width * 0.08)
            height_tolerance = max(6.0, font_size * 0.28)

            if max_line_width > content_width + width_tolerance:
                overflow_issues.append(
                    f"S{slide_no} '{text[:36]}' width {max_line_width:.0f}px > box {content_width:.0f}px"
                )
            if estimated_height > content_height + height_tolerance:
                overflow_issues.append(
                    f"S{slide_no} '{text[:36]}' height {estimated_height:.0f}px > box {content_height:.0f}px"
                )

            containing = [
                container
                for container in containers
                if center_inside([float(v) for v in container.get("bbox", [0, 0, 0, 0])], bbox)
                and bbox_area(container.get("bbox", [0, 0, 0, 0])) > bbox_area(bbox) * 1.12
            ]
            if containing:
                nearest = min(containing, key=lambda item: bbox_area(item.get("bbox", [0, 0, 0, 0])))
                container_bbox = [float(v) for v in nearest.get("bbox", [0, 0, 0, 0])]
                if not contains_bbox(container_bbox, bbox, margin=3):
                    container_issues.append(
                        f"S{slide_no} '{text[:36]}' bbox {bbox} escapes container {container_bbox}"
                    )

    if frame_issues:
        add(checks, "ppt layout QA: slide bounds", "FAIL", "; ".join(frame_issues[:8]))
    else:
        add(checks, "ppt layout QA: slide bounds", "PASS", f"{len(layout_files)} slides checked")

    if overflow_issues:
        add(checks, "ppt layout QA: text overflow", "FAIL", "; ".join(overflow_issues[:10]))
    else:
        add(checks, "ppt layout QA: text overflow", "PASS", "no estimated text overflow")

    if container_issues:
        add(checks, "ppt layout QA: container fit", "FAIL", "; ".join(container_issues[:10]))
    else:
        add(checks, "ppt layout QA: container fit", "PASS", "text boxes stay inside detected containers")


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
    check_layout_text_fit(checks)
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
