"""One test per validation rule, on tiny hand-made tables."""

import pandas as pd
import pytest

from src.consolidate import normalise_header
from src.validate import RULES, progress_cohort, to_numeric


def frame(**overrides) -> pd.DataFrame:
    row = {"Project_ID": "P1", "Indicator_ID": 1, "Unit": "Number", "Baseline": 0,
           "Mid_Target": 50, "End_Target": 100, "Actual": 40, "Survey_Value": 42}
    row.update(overrides)
    return to_numeric(pd.DataFrame([row]))


def flagged(rule: str, **overrides) -> bool:
    return bool(RULES[rule](frame(**overrides)).fillna(False).iloc[0])


def test_clean_row_has_no_errors():
    assert not any(flagged(r) for r in RULES)


@pytest.mark.parametrize("rule, overrides", [
    ("E1", {"Baseline": None}),
    ("E2", {"Mid_Target": 120}),
    ("E3", {"Mid_Target": None}),
    ("E3", {"End_Target": None}),
    ("E4", {"Actual": 400}),
    ("E5", {"Actual": "n/a"}),
    ("E5", {"Baseline": -3}),
    ("E7", {"Survey_Value": 80}),
])
def test_rule_detects_error(rule, overrides):
    assert flagged(rule, **overrides)


def test_e7_tolerates_small_differences():
    assert not flagged("E7", Actual=40, Survey_Value=45)  # 11% < 20%


def test_e6_unit_inconsistent_across_years():
    df = to_numeric(pd.DataFrame([
        {"Project_ID": "P1", "Indicator_ID": 1, "Unit": "Number", "Baseline": 0, "Mid_Target": 1,
         "End_Target": 2, "Actual": 1, "Survey_Value": 1},
        {"Project_ID": "P1", "Indicator_ID": 1, "Unit": "Thousands", "Baseline": 0, "Mid_Target": 1,
         "End_Target": 2, "Actual": 1, "Survey_Value": 1},
    ]))
    assert RULES["E6"](df).all()


@pytest.mark.parametrize("raw, expected", [
    ("End  Target ", "End_Target"), ("project id", "Project_ID"), ("Survey_Value", "Survey_Value"),
])
def test_header_normalisation(raw, expected):
    assert normalise_header(raw) == expected


@pytest.mark.parametrize("year, label", [
    (2020, "Start-up"), (2022, "Early implementation"), (2024, "Peak implementation"), (2027, "Completing phase"),
])
def test_progress_cohort(year, label):
    assert progress_cohort(year, eif=2020, completion=2027) == label
