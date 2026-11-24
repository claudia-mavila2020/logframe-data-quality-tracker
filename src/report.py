"""Write one Word review report per project, listing its data issues to fix."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from docx import Document
from docx.shared import Pt, RGBColor

from src.config import REPORT_DIR

SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def _fmt(v: object) -> str:
    return "" if pd.isna(v) else str(v)


def project_report(project: pd.Series, errors: pd.DataFrame, error_type: pd.DataFrame, out_dir: Path) -> Path:
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)

    doc.add_heading(f"Logframe data review - {project.Project_ID}", level=1)
    doc.add_paragraph(f"{project.Project_Name}  |  {project.Country} ({project.Region})  |  "
                      f"Status: {project.Project_Status}  |  Cohort: {project.Implementation_Progress_Cohort}")
    doc.add_paragraph(f"Generated on {date.today():%d %B %Y}. Synthetic data - for demonstration only.").runs[0].italic = True

    doc.add_heading("Summary", level=2)
    if errors.empty:
        doc.add_paragraph("No data issues were found. Thank you.")
    else:
        summary = (errors.groupby(["Error_ID", "Error_Name", "Severity"]).size()
                   .rename("Rows").reset_index()
                   .sort_values("Severity", key=lambda s: s.map(SEVERITY_ORDER)))
        t = doc.add_table(rows=1, cols=4)
        t.style = "Light Grid Accent 1"
        for cell, h in zip(t.rows[0].cells, ["Code", "Issue", "Severity", "Rows"]):
            cell.text = h
        for r in summary.itertuples():
            for cell, v in zip(t.add_row().cells, [r.Error_ID, r.Error_Name, r.Severity, r.Rows]):
                cell.text = str(v)

        doc.add_heading("Issues to correct", level=2)
        detail = errors.sort_values(["Severity", "Indicator_ID", "Reporting_Year"],
                                    key=lambda s: s.map(SEVERITY_ORDER) if s.name == "Severity" else s)
        cols = ["Error_ID", "Indicator_ID", "Reporting_Year", "Baseline", "Mid_Target",
                "End_Target", "Actual", "Survey_Value", "Source_Row"]
        t = doc.add_table(rows=1, cols=len(cols))
        t.style = "Light Grid Accent 1"
        for cell, h in zip(t.rows[0].cells, ["Code", "Ind.", "Year", "Baseline", "Mid", "End",
                                              "Actual", "Survey", "Excel row"]):
            cell.text = h
        for r in detail[cols].itertuples(index=False):
            for cell, v in zip(t.add_row().cells, r):
                cell.text = _fmt(v)

        doc.add_heading("What each code means", level=2)
        for et in error_type[error_type.Error_ID.isin(errors.Error_ID)].itertuples():
            p = doc.add_paragraph(style="List Bullet")
            run = p.add_run(f"{et.Error_ID} - {et.Error_Name}: ")
            run.bold = True
            p.add_run(et.Description)

    footer = doc.add_paragraph("Please correct the values in the template and resubmit.")
    footer.runs[0].font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"review_{project.Project_ID}.docx"
    doc.save(path)
    return path


def write_reports(tables: dict[str, pd.DataFrame], out_dir: Path = REPORT_DIR) -> list[Path]:
    det, proj, et = tables["error_detail"], tables["project_list"], tables["error_type"]
    return [project_report(p, det[det.Project_ID == p.Project_ID], et, out_dir) for p in proj.itertuples()]
