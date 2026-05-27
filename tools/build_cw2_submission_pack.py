from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SUBMISSION = DOCS / "submission"
DIST = ROOT / "dist"
WORK = ROOT / "outputs" / "cw2_submission_html"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
FINAL_ZIP = DIST / "SmartClassroom_CW2_Final_Submission_Pack.zip"


CSS = """
@page { size: A4; margin: 15mm 14mm; }
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Aptos", "Segoe UI", Arial, sans-serif;
  color: #10202b;
  background: #f7fbff;
  line-height: 1.52;
  font-size: 12.8px;
}
body::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(circle at 85% 0%, rgba(0, 160, 210, .13), transparent 30%),
    linear-gradient(180deg, rgba(255,255,255,.98), rgba(246,251,255,.94));
}
.doc-kicker {
  color: #607789;
  font-size: 10.5px;
  border-bottom: 1px solid #cfe0ea;
  padding-bottom: 7px;
  margin-bottom: 16px;
}
h1 {
  color: #087aa4;
  font-size: 29px;
  line-height: 1.12;
  margin: 0 0 15px;
  letter-spacing: 0;
}
h2 {
  color: #008767;
  font-size: 18px;
  margin: 22px 0 8px;
  padding-left: 10px;
  border-left: 4px solid #1cc4a4;
  break-after: avoid;
}
h3 {
  color: #0a6f95;
  font-size: 15px;
  margin: 16px 0 7px;
  break-after: avoid;
}
p { margin: 6px 0 10px; }
strong { color: #061f2d; }
a { color: #006f9f; text-decoration: none; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 9px 0 16px;
  background: rgba(255,255,255,.9);
  border: 1px solid #bdd7e5;
  break-inside: auto;
}
tr { break-inside: avoid; }
th, td {
  border: 1px solid #bdd7e5;
  padding: 6px 7px;
  vertical-align: top;
  word-break: normal;
  overflow-wrap: anywhere;
}
th {
  background: #e8f6fb;
  color: #064a64;
  font-weight: 700;
}
ul, ol { padding-left: 20px; margin: 7px 0 12px; }
li { margin: 2px 0; }
code {
  font-family: Consolas, "Cascadia Mono", monospace;
  background: #eef6f8;
  color: #0b4d65;
  border-radius: 4px;
  padding: 1px 4px;
}
pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: #071722;
  color: #e8fbff;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgba(28,196,164,.35);
}
img {
  display: block;
  max-width: 100%;
  max-height: 155mm;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid rgba(18, 139, 173, .28);
  box-shadow: 0 8px 24px rgba(16, 52, 78, .10);
  margin: 7px 0 15px;
  break-inside: avoid;
}
.page-break { break-before: page; }
"""


def html_for_markdown(source: Path, title: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    base = DOCS.resolve().as_uri() + "/"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <base href="{base}">
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="doc-kicker">IOT104TC CW2 final project submission package - generated from repository source</div>
  {body}
</body>
</html>
"""
    out = WORK / f"{source.stem}.html"
    out.write_text(html, encoding="utf-8")
    return out


def print_pdf(html: Path, pdf: Path) -> None:
    if not EDGE.exists():
        raise FileNotFoundError(f"Microsoft Edge not found: {EDGE}")
    pdf.parent.mkdir(parents=True, exist_ok=True)
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


def build_pdf(source_name: str, pdf_name: str, title: str) -> Path:
    source = DOCS / source_name
    pdf = SUBMISSION / pdf_name
    html = html_for_markdown(source, title)
    print_pdf(html, pdf)
    print(pdf)
    return pdf


def write_readme() -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    readme = SUBMISSION / "README_SUBMISSION.txt"
    readme.write_text(
        "\n".join([
            "Smart Classroom IOT104TC CW2 Final Submission Pack",
            "",
            "Project: Smart Classroom Energy-Saving, Safety & Asset Monitoring System",
            "GitHub: https://github.com/3351666087/desktop-tutorial",
            "",
            "Suggested reading order:",
            "00 Cover sheet",
            "01 Final project report",
            "02 Marking criteria response",
            "03 GitHub and runbook evidence",
            "04/05 Demonstration slides",
            "06/07 Wiring and feature guide",
            "08 Automated self-check report",
        ]),
        encoding="utf-8",
    )
    return readme


def build_zip(files: list[tuple[str, Path]]) -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    if FINAL_ZIP.exists():
        FINAL_ZIP.unlink()
    with zipfile.ZipFile(FINAL_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for arcname, source in files:
            archive.write(source, arcname)
    print(FINAL_ZIP)


def main() -> int:
    cover = build_pdf("CW2_Cover_Sheet_EN.md", "00_Cover_Sheet.pdf", "CW2 Cover Sheet")
    report = build_pdf("CW2_Final_Project_Report_EN.md", "01_Final_Project_Report.pdf", "CW2 Final Project Report")
    marking = build_pdf("CW2_Marking_Criteria_Response_EN.md", "02_Marking_Criteria_Response.pdf", "CW2 Marking Criteria Response")
    runbook = build_pdf("CW2_GitHub_Runbook_EN.md", "03_GitHub_Runbook.pdf", "CW2 GitHub Runbook")
    readme = write_readme()

    shutil.copyfile(DOCS / "SmartClassroom_Assembly_Checklist_ZH.pdf", SUBMISSION / "06_Port_Connection_Check_ZH.pdf")
    shutil.copyfile(DOCS / "SmartClassroom_Feature_Logic_Guide_ZH.pdf", SUBMISSION / "07_Feature_Logic_Guide_ZH.pdf")
    shutil.copyfile(DOCS / "SELF_CHECK_REPORT.md", SUBMISSION / "08_Self_Check_Report.md")

    files = [
        ("README_SUBMISSION.txt", readme),
        ("00_Cover_Sheet.pdf", cover),
        ("01_Final_Project_Report.pdf", report),
        ("02_Marking_Criteria_Response.pdf", marking),
        ("03_GitHub_Runbook.pdf", runbook),
        ("04_Demo_PPTX.pptx", DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pptx"),
        ("05_Demo_PPT_PDF.pdf", DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pdf"),
        ("06_Port_Connection_Check_ZH.pdf", SUBMISSION / "06_Port_Connection_Check_ZH.pdf"),
        ("07_Feature_Logic_Guide_ZH.pdf", SUBMISSION / "07_Feature_Logic_Guide_ZH.pdf"),
        ("08_Self_Check_Report.md", SUBMISSION / "08_Self_Check_Report.md"),
    ]
    build_zip(files)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
