from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import markdown


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LMC = DOCS / "lmc_submission"
DIST = ROOT / "dist"
WORK = ROOT / "outputs" / "lmc_submission_html"
ZIP_PATH = DIST / "SmartClassroom_LMC_PDF_Submission_Pack.zip"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")


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
"""


GENERATED_PDFS = [
    (
        "04_Hardware_Port_Connection_Check.pdf",
        DOCS / "LMC_Hardware_Port_Connection_EN.md",
        "Hardware Port And Wiring Reference",
    ),
    (
        "05_Feature_Logic_Guide.pdf",
        DOCS / "LMC_Feature_Logic_Guide_EN.md",
        "Feature Logic Guide",
    ),
]

COPIED_PDFS = [
    (
        "01_Project_Description_Report.pdf",
        DOCS / "submission" / "01_Final_Project_Report.pdf",
        "Primary project description report. Upload this if only one file is allowed.",
    ),
    (
        "02_Demonstration_Slides.pdf",
        DOCS / "presentation" / "SmartClassroom_IoT104TC_Demo.pdf",
        "PDF version of the demonstration PPT.",
    ),
    (
        "03_GitHub_Repository_And_Runbook.pdf",
        DOCS / "submission" / "03_GitHub_Runbook.pdf",
        "GitHub link, startup steps and verification evidence.",
    ),
]


def html_for_markdown(source: Path, title: str) -> Path:
    WORK.mkdir(parents=True, exist_ok=True)
    body = markdown.markdown(source.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="doc-kicker">Smart Classroom IOT104TC LMC PDF submission - generated from repository source</div>
  {body}
</body>
</html>
"""
    target = WORK / f"{source.stem}.html"
    target.write_text(html, encoding="utf-8")
    return target


def print_pdf(html: Path, pdf: Path) -> None:
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


def main() -> int:
    LMC.mkdir(parents=True, exist_ok=True)
    DIST.mkdir(parents=True, exist_ok=True)
    for old in LMC.iterdir():
        if old.is_file():
            old.unlink()

    readme_lines = [
        "Smart Classroom LMC PDF Submission Set",
        "",
        "Upload PDFs only. Do not upload PPTX or ZIP if LMC accepts PDF only.",
        "",
        "Recommended upload order:",
    ]

    output_files: list[tuple[str, Path]] = []
    for name, source, note in COPIED_PDFS:
        target = LMC / name
        shutil.copyfile(source, target)
        output_files.append((name, target))
        readme_lines.append(f"- {name}: {note}")

    for name, source, title in GENERATED_PDFS:
        target = LMC / name
        print_pdf(html_for_markdown(source, title), target)
        output_files.append((name, target))
        readme_lines.append(f"- {name}: English teacher-facing supporting document.")

    readme_lines.extend([
        "",
        "Do not upload the old Marking_Criteria_Response PDF unless the tutor explicitly asks for a marking self-mapping.",
        "GitHub repository: https://github.com/3351666087/desktop-tutorial",
    ])
    readme = LMC / "README_LMC_SUBMISSION.txt"
    readme.write_text("\n".join(readme_lines), encoding="utf-8")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(readme, readme.name)
        for name, target in output_files:
            archive.write(target, name)

    print(LMC)
    print(ZIP_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
