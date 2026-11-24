"""Interactive dashboard: "Find your project's data issues".

    streamlit run app/streamlit_app.py

Runs the pipeline on the synthetic submissions (or on .xlsx files uploaded in
the sidebar) and lets users filter and download the issues.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parents[1]))
from src.config import RAW_DIR  # noqa: E402
from src.consolidate import consolidate  # noqa: E402
from src.validate import run_validation  # noqa: E402

st.set_page_config(page_title="Logframe Data Quality Tracker", layout="wide")


@st.cache_data
def load(folder: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    data, qc_log = consolidate(Path(folder))
    return run_validation(data), qc_log, data


st.title("Logframe Data Quality Tracker")
st.caption("Find your project's data issues · synthetic demonstration data")

with st.sidebar:
    st.header("Data")
    uploads = st.file_uploader("Upload submission workbooks (.xlsx)", type="xlsx", accept_multiple_files=True)
    folder = str(RAW_DIR)
    if uploads:
        tmp = Path(tempfile.mkdtemp())
        for f in uploads:
            (tmp / f.name).write_bytes(f.getbuffer())
        folder = str(tmp)
        st.success(f"{len(uploads)} file(s) loaded")

tables, qc_log, data = load(folder)
det, proj, et = tables["error_detail"], tables["project_list"], tables["error_type"]

with st.sidebar:
    st.header("Filters")
    def pick(label: str, values) -> list:
        opts = sorted(pd.Series(values).dropna().unique())
        return st.multiselect(label, opts, default=opts)
    regions = pick("Region", proj.Region)
    countries = pick("Country", proj[proj.Region.isin(regions)].Country)
    status = pick("Project status", proj.Project_Status)
    cohorts = pick("Implementation progress cohort", proj.Implementation_Progress_Cohort)
    errors = st.multiselect("Error type", et.Error_ID, default=list(et.Error_ID),
                            format_func=lambda e: f"{e} - {et.set_index('Error_ID').Error_Name[e]}")

p = proj[proj.Region.isin(regions) & proj.Country.isin(countries)
         & proj.Project_Status.isin(status) & proj.Implementation_Progress_Cohort.isin(cohorts)]
d = det[det.Project_ID.isin(p.Project_ID) & det.Error_ID.isin(errors)]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Projects", len(p))
k2.metric("Projects with issues", d.Project_ID.nunique())
k3.metric("Issues", len(d))
k4.metric("High-severity issues", int((d.Severity == "High").sum()))

tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Project drill-down", "File QC log", "Error catalogue"])

with tab1:
    c1, c2 = st.columns(2)
    by_type = d.groupby(["Error_ID", "Error_Name"]).size().rename("Issues").reset_index()
    c1.plotly_chart(px.bar(by_type, x="Issues", y="Error_Name", orientation="h", title="Issues by error type")
                    .update_layout(yaxis_title=None), width="stretch")
    by_country = d.groupby(["Country", "Severity"]).size().rename("Issues").reset_index()
    c2.plotly_chart(px.bar(by_country, x="Country", y="Issues", color="Severity", title="Issues by country",
                           color_discrete_map={"High": "#c0392b", "Medium": "#e67e22", "Low": "#95a5a6"}),
                    width="stretch")
    by_cohort = d.groupby("Implementation_Progress_Cohort").size().rename("Issues").reset_index()
    st.plotly_chart(px.bar(by_cohort, x="Implementation_Progress_Cohort", y="Issues",
                           title="Issues by implementation progress cohort")
                    .update_layout(xaxis_title=None), width="stretch")

with tab2:
    project = st.selectbox("Project", p.Project_ID, format_func=lambda x: f"{x} - {p.set_index('Project_ID').Project_Name[x]}")
    rows = d[d.Project_ID == project].drop(columns=["Project_ID"])
    rows = rows.astype({c: str for c in ["Baseline", "Mid_Target", "End_Target", "Actual", "Survey_Value"]})
    st.write(f"**{len(rows)} issue(s)** found for {project}")
    st.dataframe(rows, width="stretch", hide_index=True)
    st.download_button("Download issues (CSV)", rows.to_csv(index=False), f"issues_{project}.csv")

with tab3:
    st.dataframe(qc_log, width="stretch", hide_index=True)

with tab4:
    st.dataframe(et, width="stretch", hide_index=True)

st.download_button("Download all filtered issues (CSV)", d.to_csv(index=False), "logframe_issues.csv")
