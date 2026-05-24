"""
Panel: Attribution — What moved the Nifty today?
Honest multivariate regression decomposition (oil vs AI vs FX).
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"

COLOR_MAP = {
    "brent":       "#FF6B00",
    "nifty_it":    "#1f77b4",
    "inr":         "#2ca02c",
    "unexplained": "#7f7f7f",
}


def load() -> dict | None:
    p = DATA_DIR / "attribution_latest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def load_history() -> pd.DataFrame | None:
    p = DATA_DIR / "attribution_history.csv"
    return pd.read_csv(p, parse_dates=["date"]) if p.exists() else None


def render() -> None:
    st.header("🔬 Market Attribution — What Moved Nifty Today?")

    st.info(
        "**The honest reframe:** There is no legitimate methodology to produce a clean "
        "'X% oil shock, Y% AI disruption' headline number. What we show instead is a "
        "multivariate OLS regression that estimates how much of Nifty's daily return "
        "is attributable to Brent, NIFTY IT (tech/AI proxy), and INR/USD — with "
        "R², regression coefficients, and a 'what moved today' bar chart.",
        icon="ℹ️",
    )

    data = load()
    if data is None:
        st.error("No attribution data. Run `python -m scrapers.attribution`.")
        return

    st.caption(f"Updated: **{data.get('updated_at', data.get('as_of', 'N/A'))}** · {data.get('regression_period', '')}")

    # KPI row
    nifty_ret = data.get("nifty_return_today_pct", 0)
    r2 = data.get("r_squared", 0)

    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Nifty 50 — Today's Return",
        f"{nifty_ret:+.3f}%",
        help="Daily percentage return for Nifty 50",
    )
    c2.metric(
        "Model R²",
        f"{r2:.2%}",
        help="How much of trailing 1-year Nifty variance is explained by these 3 factors",
    )
    c3.metric(
        "Regression period",
        "1 year daily",
    )

    st.divider()

    # Today's decomposition waterfall/bar
    contrib = data.get("today_contributions_pct", {})
    labels_map = data.get("feature_labels", {})

    display_labels = []
    values = []
    colors = []

    for key, val in contrib.items():
        lbl = labels_map.get(key, key)
        display_labels.append(lbl)
        values.append(val)
        colors.append(COLOR_MAP.get(key, "#aaa"))

    fig = go.Figure(go.Bar(
        x=values,
        y=display_labels,
        orientation="h",
        marker_color=colors,
        text=[f"{v:+.3f}%" for v in values],
        textposition="outside",
    ))

    total = nifty_ret
    fig.add_vline(x=0, line_dash="dot", line_color="rgba(255,255,255,0.4)")
    fig.update_layout(
        title=f"Decomposition of today's Nifty return ({nifty_ret:+.3f}%)",
        xaxis_title="Estimated contribution (percentage points)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="white",
        height=340,
        margin=dict(l=20, r=80, t=60, b=40),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
    st.plotly_chart(fig, use_container_width=True)

    # Interpretation callout
    st.markdown(
        f"""
> **How to read:** Each bar is a regression-estimated contribution (in percentage points) to today's Nifty move.
> - **🛢️ Oil (Brent)**: oil-price shock channel
> - **💻 Tech / AI (NIFTY IT)**: technology & AI sentiment channel (NIFTY IT as proxy)
> - **💱 Currency (INR/USD)**: exchange-rate transmission
> - **⬜ Unexplained**: everything else — flows, sentiment, domestic news, idiosyncratic events
>
> R² = **{r2:.2%}** means these 3 factors explain ~{r2*100:.0f}% of historical Nifty daily variance.
        """
    )

    # Regression coefficients
    with st.expander("📐 Regression coefficients (advanced)"):
        coefs = data.get("coefficients", {})
        labels_m = data.get("feature_labels", {})
        coef_df = pd.DataFrame(
            [(labels_m.get(k, k), v) for k, v in coefs.items()],
            columns=["Factor", "Coefficient"],
        )
        st.dataframe(coef_df, use_container_width=True, hide_index=True)
        st.caption(
            "Coefficient interpretation: a coefficient of 0.3 on Brent means that "
            "a 1% rise in Brent is associated with a 0.3 percentage-point rise in Nifty, "
            "holding other factors constant."
        )

    # Caveats
    with st.expander("⚠️ Important caveats"):
        st.warning(data.get("caveat", ""))

    # Historical attribution chart
    hist = load_history()
    if hist is not None and not hist.empty:
        st.divider()
        st.subheader("Historical Attribution (last 30 days)")
        recent = hist.sort_values("date").tail(30)
        contrib_cols = [c for c in recent.columns if c.startswith("contrib_") and c.endswith("_pct")]
        if contrib_cols:
            fig2 = go.Figure()
            label_map = {
                "contrib_brent_pct":       "🛢️ Oil (Brent)",
                "contrib_nifty_it_pct":    "💻 Tech / AI",
                "contrib_inr_pct":         "💱 FX (INR)",
                "contrib_unexplained_pct": "⬜ Unexplained",
            }
            clr_map = {
                "contrib_brent_pct":       "#FF6B00",
                "contrib_nifty_it_pct":    "#1f77b4",
                "contrib_inr_pct":         "#2ca02c",
                "contrib_unexplained_pct": "#7f7f7f",
            }
            for col in contrib_cols:
                fig2.add_trace(go.Bar(
                    x=recent["date"], y=recent[col],
                    name=label_map.get(col, col),
                    marker_color=clr_map.get(col, "#aaa"),
                ))
            fig2.update_layout(
                barmode="relative",
                title="Daily Nifty return decomposition (stacked)",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=380,
                yaxis_title="pp contribution",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Download
    if hist is not None:
        st.download_button(
            "⬇️ Download attribution history (CSV)",
            hist.to_csv(index=False).encode("utf-8"),
            file_name="attribution_history.csv", mime="text/csv",
        )
