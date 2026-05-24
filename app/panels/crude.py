"""
Panel: Crude Oil Benchmarks — Brent, WTI, Indian Basket, INR/USD.
90-day historical chart + latest prices + spread analysis.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"

BENCHMARK_LABELS = {
    "brent":          "Brent Crude (USD/bbl)",
    "wti":            "WTI Crude (USD/bbl)",
    "indian_basket":  "Indian Basket (USD/bbl)",
    "dubai":          "Dubai/Oman (USD/bbl)",
}

COLORS = {
    "brent":         "#FF6B00",
    "wti":           "#1f77b4",
    "indian_basket": "#2ca02c",
    "dubai":         "#9467bd",
}


def load_latest() -> dict | None:
    p = DATA_DIR / "crude_latest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_history() -> pd.DataFrame | None:
    p = DATA_DIR / "crude_benchmarks.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    return df


def render() -> None:
    st.header("📈 Crude Oil Benchmarks")

    latest = load_latest()
    hist = load_history()

    if latest is None and hist is None:
        st.error("No crude data found. Run `python -m scrapers.crude_benchmarks`.")
        return

    if latest:
        prices = latest.get("prices_usd_bbl", {})
        st.caption(f"Data as of: **{latest.get('as_of', 'N/A')}** (end-of-day, yfinance)")

        # KPI row
        cols = st.columns(len(prices))
        for i, (sym, price) in enumerate(prices.items()):
            label = BENCHMARK_LABELS.get(sym, sym)
            if price is not None:
                cols[i].metric(label, f"${price:,.2f}")

        # Spread
        brent = prices.get("brent")
        wti = prices.get("wti")
        if brent and wti:
            spread = round(brent - wti, 2)
            sign = "+" if spread >= 0 else ""
            st.caption(f"**Brent–WTI spread:** {sign}${spread}/bbl")

    st.divider()

    if hist is not None and not hist.empty:
        # Symbol selector
        available = [s for s in hist["symbol"].unique() if s != "inr_usd"]
        selected = st.multiselect(
            "Benchmarks to display",
            options=available,
            default=[s for s in ["brent", "wti", "indian_basket"] if s in available],
            format_func=lambda x: BENCHMARK_LABELS.get(x, x),
            key="crude_sym_select",
        )

        # Date range
        max_days = st.slider("History (days)", min_value=7, max_value=90, value=60, step=7)

        cutoff = pd.Timestamp.now() - pd.Timedelta(days=max_days)
        plot_df = hist[(hist["symbol"].isin(selected)) & (hist["date"] >= cutoff)].copy()

        if plot_df.empty:
            st.info("No data in selected range.")
            return

        fig = go.Figure()
        for sym in selected:
            df_sym = plot_df[plot_df["symbol"] == sym].sort_values("date")
            fig.add_trace(go.Scatter(
                x=df_sym["date"], y=df_sym["close"],
                name=BENCHMARK_LABELS.get(sym, sym),
                line=dict(color=COLORS.get(sym, "#999"), width=2),
                mode="lines",
            ))

        fig.update_layout(
            title="Crude Oil Price History (USD/bbl)",
            xaxis_title="",
            yaxis_title="USD / barrel",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=420,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        st.plotly_chart(fig, use_container_width=True)

        # OHLCV candlestick for selected single symbol
        if len(selected) == 1:
            sym = selected[0]
            df_sym = plot_df[plot_df["symbol"] == sym].sort_values("date")
            candle = go.Figure(go.Candlestick(
                x=df_sym["date"],
                open=df_sym["open"], high=df_sym["high"],
                low=df_sym["low"], close=df_sym["close"],
                name=BENCHMARK_LABELS.get(sym, sym),
                increasing_line_color="#2ca02c",
                decreasing_line_color="#d62728",
            ))
            candle.update_layout(
                title=f"{BENCHMARK_LABELS.get(sym, sym)} — Candlestick",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=350, xaxis_rangeslider_visible=False,
            )
            st.plotly_chart(candle, use_container_width=True)

        # Download
        st.download_button(
            "⬇️ Download crude history (CSV)",
            plot_df.to_csv(index=False).encode("utf-8"),
            file_name="crude_benchmarks.csv",
            mime="text/csv",
        )
