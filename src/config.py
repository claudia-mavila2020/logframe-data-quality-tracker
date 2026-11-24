"""Shared configuration: expected schema, error catalogue and project cohorts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "synthetic" / "submissions"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = OUTPUT_DIR / "reports"

# Sheet that every submission workbook must contain
DATA_SHEET = "Logframe"

# Expected columns (canonical names, after header normalisation)
EXPECTED_COLUMNS = [
    "Project_ID",
    "Project_Name",
    "Country",
    "Region",
    "EiF_Year",
    "Completion_Year",
    "Project_Status",
    "Indicator_ID",
    "Indicator_Name",
    "Result_Level",
    "Multiplier",
    "Unit",
    "Reporting_Year",
    "Baseline",
    "Mid_Target",
    "End_Target",
    "Actual",
    "Survey_Value",
]

NUMERIC_COLUMNS = ["Baseline", "Mid_Target", "End_Target", "Actual", "Survey_Value"]

# Error catalogue: one row per validation rule
ERROR_TYPES = [
    {"Error_ID": "E1", "Error_Name": "Baseline missing", "Severity": "Medium",
     "Description": "No baseline value reported for the indicator."},
    {"Error_ID": "E2", "Error_Name": "Mid target higher than end target", "Severity": "Medium",
     "Description": "The mid-term target exceeds the end target (targets should be cumulative)."},
    {"Error_ID": "E3", "Error_Name": "Mid and/or end target missing", "Severity": "High",
     "Description": "Mid-term or end target is empty. Applies to all multipliers."},
    {"Error_ID": "E4", "Error_Name": "Actual far above end target", "Severity": "Medium",
     "Description": "Reported actual is more than 3x the end target - likely a unit or data-entry error."},
    {"Error_ID": "E5", "Error_Name": "Invalid value", "Severity": "High",
     "Description": "Negative or non-numeric value in a numeric field."},
    {"Error_ID": "E6", "Error_Name": "Unit inconsistent across years", "Severity": "Low",
     "Description": "The same indicator is reported with different units in different years."},
    {"Error_ID": "E7", "Error_Name": "Reported value inconsistent with survey/MTR data", "Severity": "High",
     "Description": "Actual differs by more than 20% from the value in the survey/MTR."},
]

# Tolerances used by the rules (kept here so they are easy to review and change)
E4_MAX_RATIO = 3.0
E7_MAX_DEVIATION = 0.20

# Year used to place ongoing projects in an implementation cohort
CURRENT_YEAR_DEFAULT = 2026

# Implementation progress cohorts: share of project duration elapsed
COHORTS = [
    (0.25, "Start-up"),
    (0.50, "Early implementation"),
    (0.75, "Peak implementation"),
    (float("inf"), "Completing phase"),
]
