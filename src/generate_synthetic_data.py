"""Generate synthetic logframe submissions (one Excel workbook per country).

All projects, countries and values are fictitious. Known errors are injected at
controlled rates so that the validation pipeline has something to find. A
couple of realistic file-level problems are also injected (messy headers, an
extra blank row), mirroring what happens with real templates.

Usage:
    python -m src.generate_synthetic_data --seed 42
"""

from __future__ import annotations

import argparse
import random

from openpyxl import Workbook

from src.config import DATA_SHEET, EXPECTED_COLUMNS, RAW_DIR

COUNTRIES = {
    "Northland": "Region A", "Eastmere": "Region A", "Southvale": "Region B",
    "Westport": "Region B", "Lakeshire": "Region C", "Highcrest": "Region C",
    "Riverbend": "Region D", "Sunmoor": "Region D",
}

INDICATORS = [
    (1, "Persons receiving services promoted or supported by the project", "Outreach", "Mandatory", "Number"),
    (2, "Households reporting improved access to land, forests and water", "Outcome", "Mandatory", "Households"),
    (3, "Rural producers' organizations supported", "Output", "Optional", "Number"),
    (4, "Persons trained in income-generating activities", "Output", "Mandatory", "Persons"),
    (5, "Hectares of land brought under climate-resilient management", "Output", "Optional", "Hectares"),
    (6, "Households reporting adoption of new technologies", "Outcome", "Mandatory", "Percentage"),
    (7, "Women reporting minimum dietary diversity", "Outcome", "Optional", "Percentage"),
    (8, "Km of roads constructed or rehabilitated", "Output", "Optional", "Km"),
]

CURRENT_YEAR = 2026


def _project_rows(rng: random.Random, country: str, region: str, p_idx: int) -> list[list]:
    eif = rng.randint(2016, 2024)
    duration = rng.choice([6, 7, 8])
    completion = eif + duration - 1
    status = "Closed" if completion < CURRENT_YEAR else "Ongoing"
    pid = f"{country[:3].upper()}-{p_idx:03d}"
    name = f"{country} Rural Resilience Project {p_idx}"
    rows = []
    last_year = min(CURRENT_YEAR - 1, completion)
    years = list(range(max(eif + 1, last_year - 2), last_year + 1))
    for ind_id, ind_name, level, mult, unit in rng.sample(INDICATORS, k=rng.randint(4, 7)):
        scale = 100 if unit == "Percentage" else rng.choice([500, 2_000, 10_000])
        baseline = 0 if unit != "Percentage" else round(rng.uniform(10, 40), 1)
        end = round(scale * (0.8 if unit == "Percentage" else rng.uniform(1, 3)), 1)
        mid = round(end * rng.uniform(0.4, 0.6), 1)
        for y in years:
            progress = (y - eif + 1) / duration
            actual = round(end * progress * rng.uniform(0.7, 1.1), 1)
            survey = round(actual * rng.uniform(0.92, 1.08), 1)
            row = [pid, name, country, region, eif, completion, status, ind_id, ind_name,
                   level, mult, unit, y, baseline, mid, end, actual, survey]
            rows.append(_inject_errors(rng, row))
    return rows


def _inject_errors(rng: random.Random, row: list) -> list:
    col = {c: i for i, c in enumerate(EXPECTED_COLUMNS)}
    r = rng.random()
    if r < 0.04:
        row[col["Baseline"]] = None                                   # E1
    elif r < 0.07:
        row[col["Mid_Target"]] = round(row[col["End_Target"]] * 1.3, 1)  # E2
    elif r < 0.12:
        row[col[rng.choice(["Mid_Target", "End_Target"])]] = None    # E3
    elif r < 0.14:
        row[col["Actual"]] = row[col["Actual"]] * 100                  # E4 (unit slip)
    elif r < 0.16:
        row[col["Actual"]] = rng.choice([-50, "n/a", "TBD"])           # E5
    elif r < 0.18:
        row[col["Unit"]] = "Thousands"                                 # E6
    elif r < 0.22:
        if isinstance(row[col["Actual"]], (int, float)):
            row[col["Survey_Value"]] = round(row[col["Actual"]] * rng.choice([0.5, 1.6]), 1)  # E7
    return row


def generate(seed: int = 42) -> None:
    rng = random.Random(seed)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for old in RAW_DIR.glob("*.xlsx"):
        old.unlink()
    for i, (country, region) in enumerate(COUNTRIES.items()):
        wb = Workbook()
        info = wb.active
        info.title = "Info"
        info.append(["Country", country])
        info.append(["Template version", "2026.1"])
        ws = wb.create_sheet(DATA_SHEET)
        headers = list(EXPECTED_COLUMNS)
        if i == 2:   # messy headers, as typed by hand in a real template
            headers = [h.replace("_", " ") for h in headers]
            headers[headers.index("End Target")] = "End  Target "
        ws.append(headers)
        if i == 5:   # stray empty row after the header
            ws.append([None] * len(headers))
        for p in range(1, rng.randint(2, 4) + 1):
            for row in _project_rows(rng, country, region, p):
                ws.append(row)
        wb.save(RAW_DIR / f"logframe_submission_{country.lower()}.xlsx")
    print(f"Synthetic workbooks written to {RAW_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    generate(parser.parse_args().seed)
