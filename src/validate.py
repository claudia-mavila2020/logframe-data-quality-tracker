"""Validation rules E1-E7.

Each rule is a small function that receives the consolidated table and returns
a boolean mask (True = the row has that error). Errors are always recalculated
from the raw value columns - never read from pre-computed error columns in the
source file, which may be stale or broken.
"""

from __future__ import annotations

import pandas as pd

from src.config import COHORTS, E4_MAX_RATIO, E7_MAX_DEVIATION, ERROR_TYPES, NUMERIC_COLUMNS, CURRENT_YEAR_DEFAULT


def to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Add <col>_num columns: numeric version of each value column (NaN if not a number)."""
    out = df.copy()
    for c in NUMERIC_COLUMNS:
        out[f"{c}_num"] = pd.to_numeric(out[c], errors="coerce")
    return out


def e1_baseline_missing(d: pd.DataFrame) -> pd.Series:
    return d["Baseline"].isna()


def e2_mid_above_end(d: pd.DataFrame) -> pd.Series:
    return d["Mid_Target_num"] > d["End_Target_num"]


def e3_target_missing(d: pd.DataFrame) -> pd.Series:
    return d["Mid_Target"].isna() | d["End_Target"].isna()


def e4_actual_far_above_target(d: pd.DataFrame) -> pd.Series:
    return (d["End_Target_num"] > 0) & (d["Actual_num"] > E4_MAX_RATIO * d["End_Target_num"])


def e5_invalid_value(d: pd.DataFrame) -> pd.Series:
    bad = pd.Series(False, index=d.index)
    for c in NUMERIC_COLUMNS:
        non_numeric = d[c].notna() & d[f"{c}_num"].isna()
        negative = d[f"{c}_num"] < 0
        bad |= non_numeric | negative
    return bad


def e6_unit_inconsistent(d: pd.DataFrame) -> pd.Series:
    n_units = d.groupby(["Project_ID", "Indicator_ID"])["Unit"].transform("nunique")
    return n_units > 1


def e7_survey_mismatch(d: pd.DataFrame) -> pd.Series:
    base = d["Survey_Value_num"].abs()
    dev = (d["Actual_num"] - d["Survey_Value_num"]).abs() / base.where(base > 0)
    return dev > E7_MAX_DEVIATION


RULES = {
    "E1": e1_baseline_missing,
    "E2": e2_mid_above_end,
    "E3": e3_target_missing,
    "E4": e4_actual_far_above_target,
    "E5": e5_invalid_value,
    "E6": e6_unit_inconsistent,
    "E7": e7_survey_mismatch,
}


def progress_cohort(year: int, eif: int, completion: int) -> str:
    duration = completion - eif + 1
    share = (year - eif + 1) / duration if duration > 0 else 0
    for upper, label in COHORTS:
        if share <= upper:
            return label
    return COHORTS[-1][1]


def run_validation(data: pd.DataFrame, current_year: int = CURRENT_YEAR_DEFAULT) -> dict[str, pd.DataFrame]:
    """Return the three tables used by the dashboard: Error_Detail, Project_List, Error_Type."""
    d = to_numeric(data)
    keep = ["Project_ID", "Country", "Region", "Indicator_ID", "Indicator_Name", "Result_Level",
            "Multiplier", "Unit", "Reporting_Year", "Baseline", "Mid_Target", "End_Target",
            "Actual", "Survey_Value", "Source_File", "Source_Row"]
    hits = []
    for error_id, rule in RULES.items():
        mask = rule(d).fillna(False).astype(bool)
        if mask.any():
            hits.append(d.loc[mask, keep].assign(Error_ID=error_id))
    error_detail = pd.concat(hits, ignore_index=True) if hits else pd.DataFrame(columns=keep + ["Error_ID"])

    error_type = pd.DataFrame(ERROR_TYPES)
    error_detail = error_detail.merge(error_type[["Error_ID", "Error_Name", "Severity"]], on="Error_ID")

    projects = (d.groupby("Project_ID")
                 .agg(Project_Name=("Project_Name", "first"), Country=("Country", "first"),
                      Region=("Region", "first"), EiF_Year=("EiF_Year", "first"),
                      Completion_Year=("Completion_Year", "first"), Project_Status=("Project_Status", "first"),
                      Indicators=("Indicator_ID", "nunique"), Rows=("Indicator_ID", "size"))
                 .reset_index())
    projects["Implementation_Progress_Cohort"] = [
        progress_cohort(min(current_year, c), e, c)
        for e, c in zip(projects["EiF_Year"], projects["Completion_Year"])
    ]
    counts = error_detail.groupby("Project_ID").size().rename("Errors")
    projects = projects.merge(counts, on="Project_ID", how="left").fillna({"Errors": 0})
    projects["Errors"] = projects["Errors"].astype(int)

    error_detail = error_detail.merge(
        projects[["Project_ID", "Project_Status", "Implementation_Progress_Cohort"]], on="Project_ID")
    return {"error_detail": error_detail, "project_list": projects, "error_type": error_type}
