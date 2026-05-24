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
    from PIL import Image
except ImportError:  # pragma: no cover - the check still runs with rough estimates.
    ImageFont = None
    Image = None

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "SELF_CHECK_REPORT.md"
LAYOUT_DIR = ROOT / "docs" / "presentation" / "layout"
POWERPOINT_RENDER_DIR = ROOT / "outputs" / "ppt_powerpoint_render"


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


def check_layout_arrowheads(checks: list[Check]) -> None:
    if not LAYOUT_DIR.exists():
        add(checks, "ppt layout QA: arrowheads", "WARN", f"layout JSON not found: {rel(LAYOUT_DIR)}")
        return

    triangle_issues: list[str] = []
    for layout_file in sorted(LAYOUT_DIR.glob("slide-*.layout.json")):
        data = json.loads(layout_file.read_text(encoding="utf-8"))
        slide_no = data.get("slide", {}).get("slide") or layout_file.stem
        for element in data.get("elements", []):
            geometry = str(element.get("geometry") or "").lower()
            bbox = [float(v) for v in element.get("bbox", [0, 0, 0, 0])]
            width, height = bbox[2], bbox[3]
            fill = str(element.get("fillColor") or "")
            if geometry == "triangle" and width <= 36 and height <= 36 and not is_transparent(fill):
                triangle_issues.append(f"S{slide_no} triangle arrowhead bbox {bbox}")

    if triangle_issues:
        add(
            checks,
            "ppt layout QA: arrowheads",
            "FAIL",
            "unrotated triangle arrowheads found: " + "; ".join(triangle_issues[:10]),
        )
    else:
        add(checks, "ppt layout QA: arrowheads", "PASS", "no unrotated triangle arrowheads detected")


def hex_to_rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    text = str(value).strip()
    if not text.startswith("#"):
        return None
    text = text[1:]
    if len(text) == 8:
        text = text[:6]
    if len(text) != 6:
        return None
    try:
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return None


def render_ppt_with_powerpoint(checks: list[Check]) -> dict[int, Path]:
    pptx = ROOT / "docs/presentation/SmartClassroom_IoT104TC_Demo.pptx"
    POWERPOINT_RENDER_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import win32com.client
    except Exception as exc:  # pragma: no cover - depends on Windows desktop image.
        add(checks, "ppt visual QA: PowerPoint render", "WARN", f"pywin32/PowerPoint unavailable: {exc}")
        return {}

    app = None
    presentation = None
    try:
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Open(str(pptx), WithWindow=False)
        presentation.Export(str(POWERPOINT_RENDER_DIR), "PNG", 1280, 720)
        slide_count = presentation.Slides.Count
    except Exception as exc:
        add(checks, "ppt visual QA: PowerPoint render", "WARN", f"render failed: {exc}")
        return {}
    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            app.Quit()

    rendered: dict[int, Path] = {}
    for image_path in POWERPOINT_RENDER_DIR.glob("*.PNG"):
        digits = "".join(ch for ch in image_path.stem if ch.isdigit())
        if digits:
            rendered[int(digits)] = image_path
    add(checks, "ppt visual QA: PowerPoint render", "PASS", f"{len(rendered)}/{slide_count} slides rendered")
    return rendered


def component_bboxes(mask: "np.ndarray") -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[tuple[int, int, int, int, int]] = []
    ys, xs = np.nonzero(mask)
    for start_x, start_y in zip(xs.tolist(), ys.tolist()):
        if visited[start_y, start_x] or not mask[start_y, start_x]:
            continue
        stack = [(start_x, start_y)]
        visited[start_y, start_x] = True
        min_x = max_x = start_x
        min_y = max_y = start_y
        area = 0
        while stack:
            x, y = stack.pop()
            area += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            for nx in (x - 1, x, x + 1):
                for ny in (y - 1, y, y + 1):
                    if nx == x and ny == y:
                        continue
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = True
                        stack.append((nx, ny))
        components.append((min_x, min_y, max_x + 1, max_y + 1, area))
    return components


def visual_ink_bbox(image_array: "np.ndarray", bbox: list[float], color: tuple[int, int, int], pad: int = 10) -> list[float] | None:
    height, width, _ = image_array.shape
    x, y, w, h = bbox
    left = max(0, int(x - pad))
    top = max(0, int(y - pad))
    right = min(width, int(x + w + pad))
    bottom = min(height, int(y + h + pad))
    if right <= left or bottom <= top:
        return None

    crop = image_array[top:bottom, left:right, :3].astype(np.int32)
    target = np.array(color, dtype=np.int32)
    dist = np.sqrt(((crop - target) ** 2).sum(axis=2))
    threshold = 92 if max(color) > 210 else 76
    mask = dist <= threshold

    components = []
    for c_left, c_top, c_right, c_bottom, area in component_bboxes(mask):
        cw = c_right - c_left
        ch = c_bottom - c_top
        if area < 4:
            continue
        # Remove card borders, grid lines and arrows. Text glyphs are not single-pixel rails.
        if (cw > 28 and ch <= 4) or (ch > 28 and cw <= 4):
            continue
        if area > 2500 and (cw > w * 0.85 or ch > h * 0.85):
            continue
        components.append((left + c_left, top + c_top, left + c_right, top + c_bottom, area))
    if not components:
        return None
    return [
        float(min(item[0] for item in components)),
        float(min(item[1] for item in components)),
        float(max(item[2] for item in components) - min(item[0] for item in components)),
        float(max(item[3] for item in components) - min(item[1] for item in components)),
    ]


def check_visual_text_fit(checks: list[Check]) -> None:
    if Image is None or np is None:
        add(checks, "ppt visual QA", "WARN", "Pillow or numpy unavailable")
        return
    rendered = render_ppt_with_powerpoint(checks)
    if not rendered:
        return
    if not LAYOUT_DIR.exists():
        add(checks, "ppt visual QA", "WARN", f"layout JSON missing: {rel(LAYOUT_DIR)}")
        return

    ink_box_issues: list[str] = []
    ink_container_issues: list[str] = []
    checked = 0

    for layout_file in sorted(LAYOUT_DIR.glob("slide-*.layout.json")):
        data = json.loads(layout_file.read_text(encoding="utf-8"))
        slide_no = int(data.get("slide", {}).get("slide") or re.search(r"(\d+)", layout_file.name).group(1))
        image_path = rendered.get(slide_no)
        if not image_path:
            continue
        image_array = np.array(Image.open(image_path).convert("RGB"))
        elements = data.get("elements", [])
        containers = [element for element in elements if is_container_shape(element)]
        for element in elements:
            text = str(element.get("text", "")).strip()
            if not text:
                continue
            style = element.get("resolvedTextStyle", {})
            color = hex_to_rgb(style.get("color"))
            if color is None:
                continue
            font_size = float(element.get("resolvedFontSize") or style.get("fontSize") or 18)
            bbox = [float(value) for value in element.get("bbox", [0, 0, 0, 0])]
            ink = visual_ink_bbox(image_array, bbox, color)
            if ink is None:
                continue
            checked += 1
            text_margin = max(10.0, font_size * 0.5)
            if not contains_bbox(bbox, ink, margin=text_margin):
                ink_box_issues.append(f"S{slide_no} '{text[:34]}' ink {ink} escapes text box {bbox}")

            containing = [
                container
                for container in containers
                if center_inside([float(v) for v in container.get("bbox", [0, 0, 0, 0])], bbox)
                and bbox_area(container.get("bbox", [0, 0, 0, 0])) > bbox_area(bbox) * 1.12
            ]
            if containing:
                nearest = min(containing, key=lambda item: bbox_area(item.get("bbox", [0, 0, 0, 0])))
                container_bbox = [float(v) for v in nearest.get("bbox", [0, 0, 0, 0])]
                if not contains_bbox(container_bbox, ink, margin=1):
                    ink_container_issues.append(
                        f"S{slide_no} '{text[:34]}' ink {ink} escapes container {container_bbox}"
                    )

    if ink_box_issues:
        add(checks, "ppt visual QA: ink vs text box", "FAIL", "; ".join(ink_box_issues[:10]))
    else:
        add(checks, "ppt visual QA: ink vs text box", "PASS", f"{checked} text elements checked")

    if ink_container_issues:
        add(checks, "ppt visual QA: ink vs container", "FAIL", "; ".join(ink_container_issues[:10]))
    else:
        add(checks, "ppt visual QA: ink vs container", "PASS", "rendered text ink stays inside detected containers")


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
    check_layout_arrowheads(checks)
    check_visual_text_fit(checks)
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
