"""Read every submission workbook, check its structure and stack it into one table.

File-level problems (missing sheet, missing columns, unreadable file) are not
fatal: they are written to a QC log so that the rest of the batch still runs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.config import DATA_SHEET, EXPECTED_COLUMNS, RAW_DIR

_CANONICAL = {re.sub(r"[\s_]+", "", c).lower(): c for c in EXPECTED_COLUMNS}


def normalise_header(name: object) -> str:
    """Map messy headers ('End  Target ', 'end target') to the canonical name."""
    key = re.sub(r"[\s_]+", "", str(name)).lower()
    return _CANONICAL.get(key, str(name).strip())


def read_submission(path: Path) -> tuple[pd.DataFrame | None, list[dict]]:
    log: list[dict] = []

    def note(level: str, msg: str) -> None:
        log.append({"File": path.name, "Level": level, "Message": msg})

    try:
        sheets = pd.ExcelFile(path).sheet_names
    except Exception as exc:  # corrupt or non-Excel file
        note("ERROR", f"File could not be opened: {exc}")
        return None, log
    if DATA_SHEET not in sheets:
        note("ERROR", f"Sheet '{DATA_SHEET}' not found (sheets: {sheets})")
        return None, log

    df = pd.read_excel(path, sheet_name=DATA_SHEET)
    renamed = {c: normalise_header(c) for c in df.columns}
    fixed = [f"'{a}' -> '{b}'" for a, b in renamed.items() if a != b]
    if fixed:
        note("WARNING", "Headers normalised: " + ", ".join(fixed))
    df = df.rename(columns=renamed)

    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        note("ERROR", f"Missing columns: {missing}")
        return None, log

    blank = df[EXPECTED_COLUMNS].isna().all(axis=1)
    if blank.any():
        note("WARNING", f"{int(blank.sum())} empty row(s) dropped")
    df = df.loc[~blank, EXPECTED_COLUMNS].copy()
    for c in ["EiF_Year", "Completion_Year", "Indicator_ID", "Reporting_Year"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    df["Source_File"] = path.name
    df["Source_Row"] = df.index + 2  # Excel row number (header is row 1)
    note("INFO", f"{len(df)} rows read")
    return df, log


def consolidate(raw_dir: Path = RAW_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames, logs = [], []
    files = sorted(raw_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .xlsx files in {raw_dir}")
    for path in files:
        df, log = read_submission(path)
        logs.extend(log)
        if df is not None:
            frames.append(df)
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=EXPECTED_COLUMNS)
    return data, pd.DataFrame(logs)
