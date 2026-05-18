from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "ASSEMBLY_CHECKLIST.md"
OUTPUT = ROOT / "docs" / "SmartClassroom_Onsite_Assembly_Checklist.pdf"


PAGE_W, PAGE_H = 1240, 1754  # A4-ish at 150 dpi
MARGIN_X = 72
MARGIN_Y = 64
LINE_GAP = 8


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
    ]
    for item in candidates:
        if item.exists():
            return ImageFont.truetype(str(item), size)
    return ImageFont.load_default()


F_TITLE = font(42, True)
F_H1 = font(30, True)
F_H2 = font(24, True)
F_BODY = font(19)
F_BODY_BOLD = font(19, True)
F_SMALL = font(16)


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> int:
    if not text:
        return 0
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_w: int) -> list[str]:
    text = text.replace("**", "")
    chunks = re.findall(r"[A-Za-z0-9_./:+#()<>-]+|\s+|.", text)
    lines: list[str] = []
    current = ""
    for chunk in chunks:
        if chunk.isspace():
            candidate = current + " "
        else:
            candidate = current + chunk
        if current and text_width(draw, candidate, fnt) > max_w:
            lines.append(current.rstrip())
            current = "" if chunk.isspace() else chunk
        else:
            current = candidate
    if current.strip():
        lines.append(current.rstrip())
    return lines or [""]


class PdfWriter:
    def __init__(self) -> None:
        self.pages: list[Image.Image] = []
        self.new_page()

    def new_page(self) -> None:
        self.image = Image.new("RGB", (PAGE_W, PAGE_H), "#f7f9fc")
        self.draw = ImageDraw.Draw(self.image)
        self.y = MARGIN_Y
        self.draw.rectangle((0, 0, PAGE_W, 22), fill="#0b1324")
        self.pages.append(self.image)

    def ensure(self, h: int) -> None:
        if self.y + h > PAGE_H - MARGIN_Y:
            self.footer()
            self.new_page()

    def footer(self) -> None:
        page_no = len(self.pages)
        self.draw.text((MARGIN_X, PAGE_H - 42), "Smart Classroom IoT104TC onsite checklist", fill="#64748b", font=F_SMALL)
        self.draw.text((PAGE_W - MARGIN_X - 80, PAGE_H - 42), f"{page_no}", fill="#64748b", font=F_SMALL)

    def paragraph(self, text: str, fnt=F_BODY, color="#172033", indent=0, gap=12) -> None:
        lines = wrap_text(self.draw, text, fnt, PAGE_W - 2 * MARGIN_X - indent)
        h = len(lines) * (fnt.size + LINE_GAP) + gap
        self.ensure(h)
        x = MARGIN_X + indent
        for line in lines:
            self.draw.text((x, self.y), line, fill=color, font=fnt)
            self.y += fnt.size + LINE_GAP
        self.y += gap

    def heading(self, text: str, level: int) -> None:
        if level == 1:
            fnt, color, gap = F_TITLE, "#0f172a", 22
        elif level == 2:
            fnt, color, gap = F_H1, "#0f766e", 18
        else:
            fnt, color, gap = F_H2, "#2563eb", 14
        self.ensure(fnt.size + gap + 20)
        self.draw.text((MARGIN_X, self.y), text, fill=color, font=fnt)
        self.y += fnt.size + gap

    def bullet(self, text: str) -> None:
        self.ensure(34)
        self.draw.ellipse((MARGIN_X + 4, self.y + 8, MARGIN_X + 14, self.y + 18), fill="#06b6d4")
        self.paragraph(text, indent=28, gap=4)

    def table(self, rows: list[list[str]]) -> None:
        if not rows:
            return
        cols = len(rows[0])
        max_w = PAGE_W - 2 * MARGIN_X
        weights = [1.0] * cols
        if cols == 3:
            weights = [0.55, 1.2, 2.2]
        elif cols == 4:
            weights = [0.55, 1.3, 1.0, 2.4]
        total = sum(weights)
        widths = [int(max_w * w / total) for w in weights]
        widths[-1] += max_w - sum(widths)

        wrapped: list[list[list[str]]] = []
        row_heights: list[int] = []
        for r, row in enumerate(rows):
            fnt = F_BODY_BOLD if r == 0 else F_SMALL
            cells = [wrap_text(self.draw, cell, fnt, max(40, widths[i] - 18)) for i, cell in enumerate(row)]
            wrapped.append(cells)
            row_heights.append(max(len(cell) for cell in cells) * (fnt.size + 5) + 18)

        table_h = sum(row_heights) + 10
        self.ensure(table_h)
        x0, y0 = MARGIN_X, self.y
        y = y0
        for r, cells in enumerate(wrapped):
            h = row_heights[r]
            bg = "#dbeafe" if r == 0 else ("#ffffff" if r % 2 else "#eef6ff")
            self.draw.rectangle((x0, y, x0 + max_w, y + h), fill=bg, outline="#cbd5e1")
            x = x0
            for c, lines in enumerate(cells):
                self.draw.line((x, y, x, y + h), fill="#cbd5e1", width=1)
                fnt = F_BODY_BOLD if r == 0 else F_SMALL
                yy = y + 9
                for line in lines:
                    self.draw.text((x + 9, yy), line, fill="#172033", font=fnt)
                    yy += fnt.size + 5
                x += widths[c]
            self.draw.line((x0 + max_w, y, x0 + max_w, y + h), fill="#cbd5e1", width=1)
            y += h
        self.y = y + 18

    def save(self) -> None:
        self.footer()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        self.pages[0].save(OUTPUT, save_all=True, append_images=self.pages[1:])


def parse_markdown(md: str) -> list[tuple[str, object]]:
    blocks: list[tuple[str, object]] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            i += 1
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw = lines[i].strip()
                cells = [cell.strip() for cell in raw.strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
        elif line.startswith("- "):
            blocks.append(("bullet", line[2:].strip()))
            i += 1
        else:
            paragraph = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(("#", "|", "- ")):
                paragraph.append(lines[i].strip())
                i += 1
            blocks.append(("p", " ".join(paragraph)))
    return blocks


def main() -> None:
    writer = PdfWriter()
    for kind, value in parse_markdown(SOURCE.read_text(encoding="utf-8")):
        if kind == "h1":
            writer.heading(str(value), 1)
        elif kind == "h2":
            writer.heading(str(value), 2)
        elif kind == "h3":
            writer.heading(str(value), 3)
        elif kind == "table":
            writer.table(value)  # type: ignore[arg-type]
        elif kind == "bullet":
            writer.bullet(str(value))
        else:
            writer.paragraph(str(value))
    writer.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
