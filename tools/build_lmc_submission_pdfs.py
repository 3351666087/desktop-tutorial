from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LMC = DOCS / "lmc_submission"
DIST = ROOT / "dist"
ZIP_PATH = DIST / "SmartClassroom_LMC_PDF_Submission_Pack.zip"


FILES = [
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
    (
        "04_Hardware_Port_Connection_Check.pdf",
        DOCS / "SmartClassroom_Port_Connection_Check_ZH.pdf",
        "Wiring and port confirmation checklist.",
    ),
    (
        "05_Feature_Logic_Guide_ZH.pdf",
        DOCS / "SmartClassroom_Feature_Logic_Guide_ZH.pdf",
        "Detailed Chinese feature logic guide. Optional supporting PDF.",
    ),
]


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

    copied: list[tuple[str, Path]] = []
    for name, source, note in FILES:
        target = LMC / name
        shutil.copyfile(source, target)
        copied.append((name, target))
        readme_lines.append(f"- {name}: {note}")

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
        for name, target in copied:
            archive.write(target, name)

    print(LMC)
    print(ZIP_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
