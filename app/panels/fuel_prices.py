"""
Panel: Daily Fuel Prices (PSU OMCs + private OMC estimates).
Shows current petrol/diesel across cities with 30-day trend chart.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load_latest() -> dict | None:
    p = DATA_DIR / "fuel_prices_latest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_private() -> dict | None:
    p = DATA_DIR / "private_omc_latest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_history() -> pd.DataFrame | None:
    p = DATA_DIR / "fuel_prices_history.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None


def render() -> None:
    st.header("⛽ Daily Fuel Prices (India)")

    latest = load_latest()
    if latest is None:
        st.error("No fuel price data. Run `python -m scrapers.fuel_prices`.")
        return

    rows = latest.get("rows", [])
    df = pd.DataFrame(rows) if rows else pd.DataFrame()

    st.caption(f"Data as of: **{latest.get('as_of', 'N/A')}** · Prices updated daily at 06:00 IST by OMCs")

    if df.empty:
        st.warning("Scrapers returned no price data for today — aggregator may have changed its layout.")
        return

    # KPI row — national average
    petrol_avg = df["petrol_per_litre"].mean()
    diesel_avg = df["diesel_per_litre"].mean()

    c1, c2, c3 = st.columns(3)
    c1.metric("National avg Petrol", f"₹{petrol_avg:.2f}/L")
    c2.metric("National avg Diesel", f"₹{diesel_avg:.2f}/L")
    c3.metric("Cities tracked", f"{len(df)}")

    st.divider()

    # City bar chart
    tab1, tab2 = st.tabs(["Petrol", "Diesel"])

    with tab1:
        df_sorted = df.sort_values("petrol_per_litre", ascending=True)
        fig = px.bar(
            df_sorted, x="petrol_per_litre", y="city", orientation="h",
            color="petrol_per_litre",
            color_continuous_scale=["#2ca02c", "#ff7f0e", "#d62728"],
            labels={"petrol_per_litre": "₹/litre", "city": ""},
            title="Petrol Price by City (₹/litre)",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="white", height=380, showlegend=False,
        )
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        df_sorted = df.sort_values("diesel_per_litre", ascending=True)
        fig = px.bar(
            df_sorted, x="diesel_per_litre", y="city", orientation="h",
            color="diesel_per_litre",
            color_continuous_scale=["#2ca02c", "#ff7f0e", "#d62728"],
            labels={"diesel_per_litre": "₹/litre", "city": ""},
            title="Diesel Price by City (₹/litre)",
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="white", height=380, showlegend=False,
        )
        fig.update_coloraxes(showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # 30-day trend
    hist = load_history()
    if hist is not None and not hist.empty:
        st.subheader("30-Day Price Trend")
        cities_available = df["city"].tolist()
        selected = st.multiselect("Select cities for trend", cities_available,
                                  default=cities_available[:4], key="fuel_trend_cities")
        fuel_type = st.radio("Fuel type", ["petrol_per_litre", "diesel_per_litre"],
                             format_func=lambda x: x.split("_")[0].capitalize(), horizontal=True)

        cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
        trend_df = hist[(hist["city"].isin(selected)) & (hist["date"] >= cutoff)]

        if not trend_df.empty:
            fig2 = px.line(
                trend_df, x="date", y=fuel_type, color="city",
                labels={"date": "", fuel_type: "₹/litre", "city": "City"},
            )
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=350,
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Private OMCs
    private = load_private()
    if private:
        st.divider()
        st.subheader("Private OMC Prices (Shell · Reliance · Nayara)")
        st.warning(
            private.get("disclaimer", "Estimated figures — not official prices."),
            icon="⚠️",
        )
        priv_df = pd.DataFrame(private.get("rows", []))
        if not priv_df.empty:
            st.dataframe(
                priv_df[["city", "brand", "petrol_per_litre", "diesel_per_litre", "source", "note"]],
                use_container_width=True, hide_index=True,
            )

    # Download
    st.divider()
    st.download_button(
        "⬇️ Download today's data (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"fuel_prices_{latest.get('as_of', 'latest')}.csv",
        mime="text/csv",
    )
