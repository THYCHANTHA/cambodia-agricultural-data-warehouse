"""Cambodia Agricultural Data Warehouse: analytical dashboard over the Gold layer.

Run:  streamlit run app/streamlit_app.py
Reads only from the `gold` and `audit` schemas through the read path of the `cadw` role.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cadw import warehouse  # noqa: E402
from cadw.config import get_settings  # noqa: E402

NAVY, BLUE, LIGHT = "#0B2545", "#3B82C4", "#E8F1FA"

st.set_page_config(page_title="Cambodia Agricultural Data Warehouse", layout="wide")
st.markdown(
    f"""
    <style>
      .stApp {{ background:#FFFFFF; color:{NAVY}; }}
      h1,h2,h3 {{ color:{NAVY}; }}
      section[data-testid="stSidebar"] {{ background:{LIGHT}; }}
      div[data-testid="stMetric"] {{ background:{LIGHT}; border-radius:10px; padding:12px 16px; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def engine():
    return warehouse.make_engine(get_settings())


@st.cache_data(ttl=300, show_spinner=False)
def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


def style(fig):
    fig.update_layout(
        template="simple_white",
        font_color=NAVY,
        margin=dict(l=10, r=10, t=40, b=10),
        legend_title_text="",
    )
    return fig


def page_overview() -> None:
    st.title("Cambodia Agricultural Data Warehouse")
    st.caption(
        "Research prototype integrating FAOSTAT, World Bank, CHIRPS and geoBoundaries data. "
        "Not an official statistical product."
    )
    counts = query(
        """
        select 'fact_crop_production' as tbl, count(*) n from gold.fact_crop_production
        union all select 'fact_climate_observation', count(*) from gold.fact_climate_observation
        union all select 'fact_indicator_observation', count(*) from gold.fact_indicator_observation
        union all select 'dim_geography', count(*) from gold.dim_geography
        union all select 'dim_crop', count(*) from gold.dim_crop
        """
    ).set_index("tbl")["n"]
    cols = st.columns(len(counts))
    for col, (name, n) in zip(cols, counts.items(), strict=True):
        col.metric(name.replace("_", " "), f"{n:,}")

    st.subheader("Grain of each fact table")
    st.table(
        pd.DataFrame(
            {
                "Fact": ["fact_crop_production", "fact_climate_observation", "fact_indicator_observation"],
                "Grain": [
                    "country x year x crop (national)",
                    "province x month",
                    "country x year x indicator",
                ],
                "Source": ["FAOSTAT", "CHIRPS v3.0 aggregated to ADM1", "World Bank"],
            }
        )
    )
    st.info(
        "FAOSTAT is published at national level only. Provincial crop production or yield is NOT "
        "available in this warehouse and is never inferred from national figures."
    )


def page_crops() -> None:
    st.header("Crop production (national, FAOSTAT)")
    crops = query(
        "select crop_key, item_name, is_aggregate from gold.dim_crop where item_type = 'crop' order by item_name"
    )
    show_agg = st.sidebar.checkbox("Include FAOSTAT aggregate items", value=False)
    if not show_agg:
        crops = crops[~crops["is_aggregate"]]
    default = crops.index[crops["item_name"] == "Rice"].tolist()
    chosen = st.multiselect(
        "Crops", crops["item_name"].tolist(), default=[crops.loc[default[0], "item_name"]] if default else []
    )
    if not chosen:
        st.info("Select at least one crop.")
        return
    df = query(
        """
        select c.item_name, f.year, f.production_t, f.area_harvested_ha, f.yield_reported_kg_ha,
               f.yield_derived_kg_ha, f.yield_discrepancy_pct, f.production_flag
        from gold.fact_crop_production f join gold.dim_crop c using (crop_key)
        where c.item_name = any(:names) order by f.year
        """,
        {"names": chosen},
    )
    metric = st.radio(
        "Measure",
        ["production_t", "area_harvested_ha", "yield_reported_kg_ha"],
        format_func=lambda m: {
            "production_t": "Production (tonnes)",
            "area_harvested_ha": "Area harvested (ha)",
            "yield_reported_kg_ha": "Yield (kg/ha)",
        }[m],
        horizontal=True,
    )
    fig = px.line(
        df,
        x="year",
        y=metric,
        color="item_name",
        markers=True,
        color_discrete_sequence=[BLUE, NAVY, "#7FB2E5"],
    )
    st.plotly_chart(style(fig), use_container_width=True)
    st.caption(
        "Missing observations appear as gaps; FAOSTAT flag 'E' = estimated, 'I' = imputed by FAO, 'A' = official."
    )
    with st.expander("Data table"):
        st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV", df.to_csv(index=False), "crop_production.csv", "text/csv")


def page_rainfall() -> None:
    st.header("Rainfall by province (CHIRPS v3.0)")
    prov = query(
        "select geography_key, geography_name from gold.dim_geography where geography_level = 'province' order by 2"
    )
    available = query(
        "select min(date_key) lo, max(date_key) hi, count(distinct date_key) n from gold.fact_climate_observation"
    )
    if available.empty or pd.isna(available.loc[0, "n"]) or available.loc[0, "n"] == 0:
        st.info("No rainfall data loaded yet. Run the pipeline with the chirps source.")
        return
    st.caption(
        f"{int(available.loc[0, 'n'])} month(s) loaded: {int(available.loc[0, 'lo'])} to {int(available.loc[0, 'hi'])}"
    )
    names = st.multiselect(
        "Provinces", prov["geography_name"].tolist(), default=prov["geography_name"].tolist()[:3]
    )
    df = query(
        """
        select g.geography_name as province, d.month_start, d.year, d.month, f.precip_mean_mm,
               f.valid_pixel_ratio
        from gold.fact_climate_observation f
        join gold.dim_geography g using (geography_key) join gold.dim_date d using (date_key)
        where g.geography_name = any(:names) order by d.month_start
        """,
        {"names": names},
    )
    if df.empty:
        st.info("Select at least one province.")
        return
    if df["month_start"].nunique() == 1:
        fig = px.bar(
            df.sort_values("precip_mean_mm"),
            x="precip_mean_mm",
            y="province",
            orientation="h",
            color_discrete_sequence=[BLUE],
        )
    else:
        fig = px.line(
            df,
            x="month_start",
            y="precip_mean_mm",
            color="province",
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
    st.plotly_chart(style(fig), use_container_width=True)
    st.caption("Mean of pixel monthly totals (mm) inside each province; 0.05 degree resolution.")
    st.dataframe(df, use_container_width=True)


def page_indicators() -> None:
    st.header("Country indicators (World Bank)")
    inds = query("select indicator_key, indicator_name from gold.dim_indicator order by 2")
    if inds.empty:
        st.info("No World Bank data loaded yet.")
        return
    name = st.selectbox("Indicator", inds["indicator_name"].tolist())
    key = inds.loc[inds["indicator_name"] == name, "indicator_key"].iloc[0]
    df = query(
        "select year, value from gold.fact_indicator_observation where indicator_key = :k order by year",
        {"k": key},
    )
    fig = px.line(df, x="year", y="value", markers=True, color_discrete_sequence=[BLUE])
    st.plotly_chart(style(fig), use_container_width=True)
    missing = int(df["value"].isna().sum())
    st.caption(f"{missing} of {len(df)} years have no published value (shown as gaps).")


def page_quality() -> None:
    st.header("Data quality and lineage")
    log = query(
        """
        select source_name, status, rows_loaded, started_at, finished_at, source_version, licence
        from audit.ingestion_log order by started_at desc limit 20
        """
    )
    st.subheader("Recent ingestion runs")
    st.dataframe(log, use_container_width=True)
    dq = query(
        """
        select source_name, check_name, passed, n_violations, severity, detail
        from audit.data_quality_results
        where (source_name, checked_at) in (
            select source_name, max(checked_at) from audit.data_quality_results group by source_name
        )
        order by source_name, check_name
        """
    )
    st.subheader("Latest source-level checks")
    st.dataframe(dq, use_container_width=True)
    st.subheader("Sources and licences")
    st.dataframe(
        query(
            "select source_key, publisher, licence_summary, native_grain, latest_loaded_at from gold.dim_data_source"
        ),
        use_container_width=True,
    )


def page_about() -> None:
    st.header("About")
    st.markdown(
        """
        **Purpose.** A reproducible prototype showing how fragmented public agricultural, climate and
        development data can be integrated into one dimensional warehouse (Bronze, Silver, Gold).

        **Limitations.** National FAOSTAT figures are not provincial statistics. Rainfall is satellite-gauge
        estimates (CHIRPS), not station measurements. See `docs/limitations.md`.

        **Method and reproduction.** See `docs/methodology.md` and `README.md`.
        """
    )


PAGES = {
    "Overview": page_overview,
    "Crop production": page_crops,
    "Rainfall": page_rainfall,
    "Indicators": page_indicators,
    "Data quality": page_quality,
    "About": page_about,
}

choice = st.sidebar.radio("Navigate", list(PAGES))
try:
    PAGES[choice]()
except Exception as exc:  # show a readable error instead of a stack trace in the UI
    st.error(f"Could not load this page: {exc}")
    st.caption("Has the pipeline been run? See README for the setup steps.")
