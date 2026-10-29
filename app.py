"""Financial dashboard: HPE vs competitors (Streamlit).

Run from the project root:
    streamlit run app.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import (
    METRICS,
    clean_data,
    hpe_summary,
    latest_period,
    load_annual,
    load_quarterly,
    ranking,
    trend,
)

# Must be the first Streamlit command in the script
st.set_page_config(page_title="HPE vs competitors", page_icon="📊", layout="wide")

# ---------- Display configuration ----------
FOCUS_COMPANY = "HPE"

LABELS = {
    "gross_margin": "Gross margin",
    "operating_margin": "Operating margin",
    "profit_margin": "Net margin",
    "roe": "ROE",
    "roa": "ROA",
    "revenue_growth_yoy": "Revenue growth (YoY)",
    "debt_to_equity": "Debt / Equity",
    "current_ratio": "Current ratio",
}
# Metrics shown as percentages (the rest are shown as "x times")
PERCENT_METRICS = {
    "gross_margin", "operating_margin", "profit_margin",
    "roe", "roa", "revenue_growth_yoy",
}
COLORS = {"HPE": "#01A982", "DELL": "#2563EB", "IBM": "#F59E0B", "CSCO": "#EF4444"}


def fmt(metric: str, value) -> str:
    """Format a value according to the metric type."""
    if pd.isna(value):
        return "n/a"
    return f"{value:.1%}" if metric in PERCENT_METRICS else f"{value:.2f}x"


def fmt_diff(metric: str, value) -> str:
    """Format a difference: percentage points or times."""
    if pd.isna(value):
        return "n/a"
    if metric in PERCENT_METRICS:
        return f"{value * 100:+.1f} pp"
    return f"{value:+.2f}x"


@st.cache_data
def load(frequency: str) -> pd.DataFrame:
    """Load and clean the CSV. Streamlit caches it so it is not re-read on every click."""
    df = load_annual() if frequency == "Annual" else load_quarterly()
    return clean_data(df)


# ---------- Sidebar (filters) ----------
st.sidebar.header("Filters")
frequency = st.sidebar.radio("Frequency", ["Annual", "Quarterly"])
df_all = load(frequency)

all_companies = sorted(df_all["ticker"].unique())
companies = st.sidebar.multiselect("Companies", all_companies, default=all_companies)
metric = st.sidebar.selectbox("Metric", list(LABELS), format_func=LABELS.get)

st.title("📊 HPE vs competitors")
st.caption(
    "Data from Yahoo Finance (yfinance). Each company uses its own fiscal year. "
    "See the *Notes* tab before interpreting the results."
)

df = df_all[df_all["ticker"].isin(companies)]
if df.empty:
    st.warning("Select at least one company in the sidebar.")
    st.stop()

if frequency == "Quarterly" and metric == "revenue_growth_yoy":
    st.warning(
        "Yahoo only provides ~6 quarters, so quarterly YoY growth has almost no "
        "data. Use the annual frequency for this metric."
    )

tab_summary, tab_ranking, tab_trend, tab_data, tab_notes = st.tabs(
    ["HPE summary", "Ranking", "Trend", "Data", "Notes"]
)

# ---------- Tab 1: HPE summary ----------
with tab_summary:
    st.subheader("HPE vs competitor average (latest reported period)")
    if FOCUS_COMPANY not in companies or len(companies) < 2:
        st.info("Select HPE and at least one more company to see the comparison.")
    else:
        summary = hpe_summary(df, FOCUS_COMPANY)
        hpe = latest_period(df).set_index("ticker").loc[FOCUS_COMPANY]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("HPE period", str(hpe["period"]))
        c2.metric("Revenue", f"${hpe['Total Revenue'] / 1e9:,.1f}B")
        c3.metric("Operating margin", fmt("operating_margin", hpe["operating_margin"]))
        c4.metric("YoY growth", fmt("revenue_growth_yoy", hpe["revenue_growth_yoy"]))

        table = pd.DataFrame(
            {
                "Metric": [LABELS[m] for m in summary.index],
                "HPE": [fmt(m, v) for m, v in summary[FOCUS_COMPANY].items()],
                "Competitor average": [
                    fmt(m, v) for m, v in summary["peer_average"].items()
                ],
                "Difference": [fmt_diff(m, v) for m, v in summary["difference"].items()],
            }
        )
        st.dataframe(table, hide_index=True)
        st.caption(
            "Simple (unweighted) average of the selected competitors. "
            "'n/a' values are excluded from the average. pp = percentage points."
        )

# ---------- Tab 2: Ranking ----------
with tab_ranking:
    st.subheader(f"Ranking: {LABELS[metric]}")
    rk = ranking(df, metric)
    if rk.empty:
        st.info("No data available for this metric with the current filters.")
    else:
        is_pct = metric in PERCENT_METRICS
        fig = px.bar(
            rk,
            x="ticker",
            y=metric,
            color="ticker",
            color_discrete_map=COLORS,
            text=[fmt(metric, v) for v in rk[metric]],
            labels={"ticker": "Company", metric: LABELS[metric]},
        )
        fig.update_layout(
            showlegend=False, yaxis_tickformat=".0%" if is_pct else ".2f"
        )
        st.plotly_chart(fig)
        st.caption("Higher is better." if METRICS[metric] else "Lower is better.")

        shown = rk.assign(value=[fmt(metric, v) for v in rk[metric]])[
            ["rank", "ticker", "period", "value"]
        ]
        shown.columns = ["Rank", "Company", "Period", LABELS[metric]]
        st.dataframe(shown, hide_index=True)

# ---------- Tab 3: Trend ----------
with tab_trend:
    st.subheader(f"Trend: {LABELS[metric]}")
    tr = trend(df, metric)
    if tr.dropna(how="all").empty:
        st.info("No data available for this metric with the current filters.")
    else:
        tr.index = tr.index.astype(str)  # years as text avoids ticks like 2022.5
        fig = px.line(
            tr,
            markers=True,
            color_discrete_map=COLORS,
            labels={
                "value": LABELS[metric],
                "period": "Period",
                "ticker": "Company",
            },
        )
        fig.update_xaxes(type="category")
        fig.update_traces(connectgaps=True)
        fig.update_layout(yaxis_tickformat=".0%" if metric in PERCENT_METRICS else ".2f")
        st.plotly_chart(fig)

# ---------- Tab 4: Data ----------
with tab_data:
    st.subheader("Data")
    columns = [
        "ticker", "period", "period_end", "Total Revenue", "Gross Profit",
        "Operating Income", "Net Income", *METRICS, "negative_equity",
    ]
    columns = [c for c in columns if c in df.columns]
    st.dataframe(df[columns], hide_index=True)
    st.download_button(
        "Download CSV",
        df[columns].to_csv(index=False).encode("utf-8"),
        file_name=f"financials_{frequency.lower()}.csv",
        mime="text/csv",
    )

# ---------- Tab 5: Notes ----------
with tab_notes:
    st.subheader("Methodology notes")
    st.markdown(
        """
**Source.** Financial statements downloaded with `yfinance` (Yahoo Finance).
Yahoo provides ~4 annual years and ~6 quarters per company, so the history does
not go back to 2020.

**Fiscal years.** Each company closes its books on different dates: HPE on
October 31, Dell at the end of January, Cisco at the end of July and IBM on
December 31. "Period" is the year of each company's fiscal close, and the
quarter is the *calendar* quarter of the closing date.

**Latest period.** Rankings and the summary use each company's latest reported
period, which may not cover the same dates across companies.

**Negative stockholders' equity.** When equity is negative (Dell), ROE and
Debt/Equity are not interpretable and are shown as *n/a*.

**HPE growth.** Includes the Juniper Networks acquisition (closed during fiscal
2025), so it is not organic growth. GAAP profit for that year also reflects
acquisition-related costs.

**Competitor average.** Simple average, not weighted by company size.

**Validation.** The data passes consistency checks (margins, duplicates,
recomputations) in `src/analysis.py`.
        """
    )