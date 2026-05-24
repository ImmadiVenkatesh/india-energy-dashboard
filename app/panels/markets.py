"""
Panel: India Markets — Nifty 50, NIFTY IT, Gold, INR/USD.
90-day chart with correlation heatmap vs Brent.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"

LABELS = {
    "nifty50":  "Nifty 50",
    "nifty_it": "NIFTY IT (Tech/AI proxy)",
    "gold_mcx": "Gold (USD/oz)",
    "inr_usd":  "INR/USD rate",
    "sensex":   "Sensex",
}

COLORS = {
    "nifty50":  "#FF6B00",
    "nifty_it": "#1f77b4",
    "gold_mcx": "#FFD700",
    "inr_usd":  "#2ca02c",
    "sensex":   "#9467bd",
}


def load_latest() -> dict | None:
    p = DATA_DIR / "markets_latest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_history() -> pd.DataFrame | None:
    p = DATA_DIR / "markets.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None


def load_crude() -> pd.DataFrame | None:
    p = DATA_DIR / "crude_benchmarks.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None


def render() -> None:
    st.header("📊 India Markets — Nifty · Gold · INR")

    latest = load_latest()
    hist = load_history()

    if latest is None and hist is None:
        st.error("No market data. Run `python -m scrapers.markets`.")
        return

    if latest:
        prices = latest.get("latest", {})
        returns = latest.get("daily_returns_pct", {})
        st.caption(f"Data as of: **{latest.get('as_of', 'N/A')}** (end-of-day)")

        # KPI row
        kpi_syms = ["nifty50", "nifty_it", "gold_mcx"]
        cols = st.columns(4)
        for i, sym in enumerate(kpi_syms):
            if sym in prices:
                ret = returns.get(sym)
                delta = f"{ret:+.2f}%" if ret is not None else None
                cols[i].metric(LABELS[sym], f"{prices[sym]:,.2f}", delta=delta)
        # INR special display
        inr_per_usd = latest.get("inr_per_usd")
        if inr_per_usd:
            ret = returns.get("inr_usd")
            cols[3].metric("INR/USD", f"₹{inr_per_usd:.2f}",
                           delta=f"{ret:+.4f}%" if ret else None)

    st.divider()

    if hist is not None and not hist.empty:
        available = [s for s in hist["symbol"].unique()]
        selected = st.multiselect(
            "Instruments",
            options=available,
            default=[s for s in ["nifty50", "nifty_it", "gold_mcx"] if s in available],
            format_func=lambda x: LABELS.get(x, x),
            key="mkt_sym_select",
        )
        max_days = st.slider("History (days)", 7, 90, 60, 7, key="mkt_days")

        cutoff = pd.Timestamp.now() - pd.Timedelta(days=max_days)
        plot_df = hist[(hist["symbol"].isin(selected)) & (hist["date"] >= cutoff)].copy()

        if not plot_df.empty:
            # Normalise to % change from first day for multi-scale comparison
            normalize = st.checkbox("Normalise to % change (for multi-scale comparison)", value=True)
            fig = go.Figure()

            for sym in selected:
                df_sym = plot_df[plot_df["symbol"] == sym].sort_values("date")
                if df_sym.empty:
                    continue
                y = df_sym["close"]
                if normalize:
                    base = y.iloc[0]
                    y = (y / base - 1) * 100

                fig.add_trace(go.Scatter(
                    x=df_sym["date"], y=y,
                    name=LABELS.get(sym, sym),
                    line=dict(color=COLORS.get(sym, "#999"), width=2),
                ))

            fig.update_layout(
                title="Market Performance" + (" (% change, rebased)" if normalize else ""),
                yaxis_title="% change" if normalize else "Price",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
            fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
            st.plotly_chart(fig, use_container_width=True)

    # Correlation with Brent
    crude = load_crude()
    if crude is not None and hist is not None:
        st.subheader("🔗 Correlation with Brent Crude (90-day daily returns)")
        brent_df = crude[crude["symbol"] == "brent"][["date", "close"]].rename(
            columns={"close": "brent"}
        )
        corr_data: dict[str, float] = {}
        for sym in hist["symbol"].unique():
            sym_df = hist[hist["symbol"] == sym][["date", "close"]].rename(
                columns={"close": sym}
            )
            merged = brent_df.merge(sym_df, on="date").dropna()
            if len(merged) >= 10:
                merged["brent_ret"] = merged["brent"].pct_change()
                merged[f"{sym}_ret"] = merged[sym].pct_change()
                merged = merged.dropna()
                if len(merged) >= 5:
                    corr_data[LABELS.get(sym, sym)] = round(
                        merged["brent_ret"].corr(merged[f"{sym}_ret"]), 3
                    )

        if corr_data:
            corr_df = pd.DataFrame.from_dict(
                corr_data, orient="index", columns=["Correlation with Brent"]
            ).sort_values("Correlation with Brent", ascending=False)
            fig_corr = px.bar(
                corr_df.reset_index(), x="Correlation with Brent", y="index",
                orientation="h",
                color="Correlation with Brent",
                color_continuous_scale=["#1f77b4", "#aaa", "#d62728"],
                range_color=[-1, 1],
                labels={"index": ""},
                title="30-day rolling correlation of daily returns vs Brent",
            )
            fig_corr.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=300,
            )
            st.plotly_chart(fig_corr, use_container_width=True)

    # Download
    if hist is not None:
        st.download_button(
            "⬇️ Download market history (CSV)",
            hist.to_csv(index=False).encode("utf-8"),
            file_name="markets.csv", mime="text/csv",
        )
