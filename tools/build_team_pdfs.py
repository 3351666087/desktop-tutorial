from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WORK = ROOT / "outputs" / "team_pdf_html"
DIST = ROOT / "dist"
TEAM_ZIP = DIST / "SmartClassroom_Team_Delivery_Pack.zip"
PORT_PDF = DOCS / "SmartClassroom_Port_Connection_Check_ZH.pdf"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
PPTX = DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pptx"
PPT_PDF = DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pdf"


CSS = """
@page { size: A4; margin: 16mm 14mm; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Microsoft YaHei", "Noto Sans SC", "DengXian", Arial, sans-serif;
  color: #10202b;
  background: #f7fbff;
  line-height: 1.58;
  font-size: 13px;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 82% 3%, rgba(50, 185, 230, .14), transparent 32%),
    linear-gradient(180deg, rgba(255,255,255,.95), rgba(244,250,255,.9));
  z-index: -1;
}
h1 {
  color: #0a83af;
  font-size: 30px;
  line-height: 1.16;
  margin: 0 0 18px;
  letter-spacing: 0;
}
h2 {
  color: #00986f;
  font-size: 19px;
  margin: 22px 0 9px;
  border-left: 4px solid #21c7a8;
  padding-left: 10px;
}
h3 {
  color: #0a83af;
  font-size: 16px;
  margin: 18px 0 8px;
}
p { margin: 6px 0 10px; }
strong { color: #062333; }
img {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid rgba(18, 139, 173, .28);
  box-shadow: 0 8px 28px rgba(16, 52, 78, .10);
  margin: 8px 0 18px;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 18px;
  background: rgba(255,255,255,.86);
  page-break-inside: auto;
  border: 1px solid #bfd8e6;
}
tr { page-break-inside: avoid; page-break-after: auto; }
th, td {
  border: 1px solid #bfd8e6;
  padding: 7px 8px;
  vertical-align: top;
  word-break: break-word;
}
th {
  background: #e9f7fb;
  color: #07526a;
  font-weight: 700;
}
ul, ol { padding-left: 22px; margin: 8px 0 12px; }
li { margin: 3px 0; }
code {
  font-family: Consolas, "Cascadia Mono", monospace;
  background: #edf5f8;
  color: #0f465d;
  border-radius: 4px;
  padding: 1px 4px;
}
pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: #071722;
  color: #e9fbff;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(33,199,168,.35);
}
.cover-note {
  color: #5b6f7c;
  font-size: 11px;
  margin-bottom: 14px;
  border-bottom: 1px solid #cfe1eb;
  padding-bottom: 8px;
}
"""


def clean_markdown(text: str) -> str:
    text = re.sub(r"```mermaid[\s\S]*?```", "", text, flags=re.IGNORECASE)
    text = text.replace("<br/>", "<br>")
    return text


def html_for_markdown(source: Path, title: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    md_text = clean_markdown(source.read_text(encoding="utf-8"))
    body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    base = source.parent.resolve().as_uri() + "/"
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <base href="{base}">
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="cover-note">Smart Classroom IoT104TC team PDF · generated from repository source</div>
  {body}
</body>
</html>
"""
    output = WORK / f"{source.stem}.html"
    output.write_text(html, encoding="utf-8")
    return output


def print_html_to_pdf(html: Path, pdf: Path) -> None:
    if not EDGE.exists():
        raise FileNotFoundError(f"Microsoft Edge not found: {EDGE}")
    if pdf.exists():
        pdf.unlink()
    command = [
        str(EDGE),
        "--headless",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-pdf-header-footer",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf}",
        html.as_uri(),
    ]
    subprocess.run(command, cwd=ROOT, check=True, timeout=90)


def export_ppt_to_pdf() -> None:
    try:
        import win32com.client
    except Exception as exc:
        print(f"[warn] PowerPoint COM unavailable, skip PPT PDF export: {exc}")
        return

    if PPT_PDF.exists():
        PPT_PDF.unlink()
    app = None
    presentation = None
    try:
        app = win32com.client.Dispatch("PowerPoint.Application")
        app.Visible = True
        presentation = app.Presentations.Open(str(PPTX), WithWindow=False)
        presentation.SaveAs(str(PPT_PDF), 32)
    finally:
        if presentation is not None:
            presentation.Close()
        if app is not None:
            app.Quit()



def write_team_zip() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    if PORT_PDF.exists():
        PORT_PDF.unlink()
    shutil.copyfile(DOCS / "SmartClassroom_Assembly_Checklist_ZH.pdf", PORT_PDF)
    if TEAM_ZIP.exists():
        TEAM_ZIP.unlink()
    files = [
        ("00_四人分工与演示顺序.pdf", DOCS / "SmartClassroom_4Person_Presentation_Plan_ZH.pdf"),
        ("01_功能逻辑详解.pdf", DOCS / "SmartClassroom_Feature_Logic_Guide_ZH.pdf"),
        ("02_端口接线确认.pdf", PORT_PDF),
        ("03_演示用PPTX.pptx", DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pptx"),
        ("04_演示用PPT_PDF.pdf", DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pdf"),
        ("05_中英双语演讲稿.pdf", DOCS / "SmartClassroom_Speech_Script_Bilingual.pdf"),
    ]
    with zipfile.ZipFile(TEAM_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README_先看这个.txt", "\n".join([
            "Smart Classroom Team Delivery Pack",
            "",
            "00 四人分工与演示顺序：先看这个，明确 4 个人各自讲什么、操作什么。",
            "01 功能逻辑详解：给组员讲系统功能和每条逻辑链路。",
            "02 端口接线确认：现场照着查 UNO / ESP32 / 模块接口。",
            "03 演示用 PPTX：现场汇报可编辑版本。",
            "04 演示用 PPT PDF：只读放映或发给老师版本。",
            "05 中英双语演讲稿：4 人分工时可按段落拆分。",
        ]))
        for arcname, source in files:
            archive.write(source, arcname)
    print(TEAM_ZIP)

def main() -> int:
    jobs = [
        (DOCS / "FOUR_PERSON_PRESENTATION_PLAN_ZH.md", DOCS / "SmartClassroom_4Person_Presentation_Plan_ZH.pdf", "Smart Classroom 四人演示分工说明"),
        (DOCS / "TEAM_FEATURE_GUIDE_ZH.md", DOCS / "SmartClassroom_Feature_Logic_Guide_ZH.pdf", "Smart Classroom 功能逻辑详解"),
        (DOCS / "TEAM_FLOWCHART_ZH.md", DOCS / "SmartClassroom_Team_Guide_ZH.pdf", "Smart Classroom 团队总览"),
        (DOCS / "ASSEMBLY_CHECKLIST.md", DOCS / "SmartClassroom_Assembly_Checklist_ZH.pdf", "Smart Classroom 现场组装清单"),
        (DOCS / "ENV_SETUP_ZH.md", DOCS / "SmartClassroom_Environment_Setup_ZH.pdf", "Smart Classroom 环境拉取说明"),
        (DOCS / "SPEECH_SCRIPT_BILINGUAL.md", DOCS / "SmartClassroom_Speech_Script_Bilingual.pdf", "Smart Classroom 中英双语演讲稿"),
    ]
    for source, pdf, title in jobs:
        html = html_for_markdown(source, title)
        print_html_to_pdf(html, pdf)
        print(pdf)
    export_ppt_to_pdf()
    print(PPT_PDF)
    write_team_zip()
    print(PORT_PDF)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
