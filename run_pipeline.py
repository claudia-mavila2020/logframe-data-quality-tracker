"""Run the full pipeline: consolidate -> validate -> export tables -> Word reports.

    python run_pipeline.py            # uses data/synthetic/submissions
    python run_pipeline.py --no-reports
"""

from __future__ import annotations

import argparse

from src.config import OUTPUT_DIR, RAW_DIR
from src.consolidate import consolidate
from src.report import write_reports
from src.validate import run_validation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(RAW_DIR), help="Folder with .xlsx submissions")
    parser.add_argument("--no-reports", action="store_true", help="Skip Word reports")
    args = parser.parse_args()

    from pathlib import Path
    data, qc_log = consolidate(Path(args.input))
    tables = run_validation(data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data.to_csv(OUTPUT_DIR / "consolidated.csv", index=False)
    qc_log.to_csv(OUTPUT_DIR / "qc_log.csv", index=False)
    for name, df in tables.items():
        df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

    print(f"Files processed : {qc_log.File.nunique()}")
    print(f"Rows consolidated: {len(data)}")
    print(f"Projects         : {len(tables['project_list'])}")
    print("Issues by rule   :")
    print(tables["error_detail"].groupby(["Error_ID", "Error_Name"]).size().to_string())
    issues = qc_log[qc_log.Level != "INFO"]
    if not issues.empty:
        print("\nFile-level QC notes:")
        for r in issues.itertuples():
            print(f"  [{r.Level}] {r.File}: {r.Message[:120]}{'...' if len(r.Message) > 120 else ''}")

    if not args.no_reports:
        paths = write_reports(tables)
        print(f"\n{len(paths)} Word review reports written to {paths[0].parent}")


if __name__ == "__main__":
    main()
