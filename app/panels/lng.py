"""
Panel: LNG Import Dependency (the honest reframe for 'how long will reserves last').
Shows terminal utilization, JKM/HH spot prices, monthly import volumes.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load() -> dict | None:
    p = DATA_DIR / "lng_dashboard.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def render() -> None:
    st.header("🧊 LNG — Import Dependency Panel")

    st.info(
        "**Why not 'how long will LNG reserves last'?** India does not maintain a strategic LNG "
        "reserve. Petronet and GAIL hold commercial inventory only, not publicly disclosed daily. "
        "This panel instead shows the indicators that actually matter for India's LNG exposure.",
        icon="ℹ️",
    )

    data = load()
    if data is None:
        st.error("No LNG data. Run `python -m scrapers.lng_data`.")
        return

    st.caption(f"Data as of: **{data.get('as_of', 'N/A')}**")

    # Spot prices
    st.subheader("🔴 Spot Prices")
    hh = data.get("henry_hub")
    jkm = data.get("jkm_spot")

    c1, c2, c3 = st.columns(3)
    if hh:
        c1.metric(
            "Henry Hub",
            f"${hh['henry_hub_usd_mmbtu']:.3f}/MMBtu",
            help=f"Source: {hh['source']}",
        )
    if jkm:
        c2.metric(
            "JKM (Asia spot)",
            f"${jkm['jkm_usd_mmbtu']:.2f}/MMBtu",
            help=f"Source: {jkm['source']}",
        )
    if hh and jkm:
        spread = round(jkm["jkm_usd_mmbtu"] - hh["henry_hub_usd_mmbtu"], 2)
        sign = "+" if spread >= 0 else ""
        c3.metric(
            "JKM − HH Spread",
            f"{sign}${spread}/MMBtu",
            help="Higher spread = more expensive for Asia buyers vs. US domestic",
        )

    st.divider()

    # Terminal utilization
    st.subheader("🏭 LNG Terminal Capacity (India)")
    terminals = data.get("terminals", [])
    if terminals:
        df_t = pd.DataFrame(terminals)
        df_t.columns = ["Terminal", "State", "Capacity (MMTPA)", "Operator"]

        util = data.get("utilization", {})
        df_t["Utilization %"] = df_t["Terminal"].map(
            lambda t: util.get(t, {}).get("utilization_pct", None)
        )
        df_t["Data Period"] = df_t["Terminal"].map(
            lambda t: util.get(t, {}).get("as_of", "N/A")
        )

        st.dataframe(df_t, use_container_width=True, hide_index=True)

        # Utilization bar chart (where available)
        util_df = df_t.dropna(subset=["Utilization %"])
        if not util_df.empty:
            fig = px.bar(
                util_df, x="Terminal", y="Utilization %",
                color="Utilization %",
                color_continuous_scale=["#d62728", "#ff7f0e", "#2ca02c"],
                range_color=[0, 100],
                title="Petronet Terminal Utilization (%)",
                text="Utilization %",
            )
            fig.update_traces(texttemplate="%{text}%", textposition="outside")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="white", height=320, showlegend=False,
                yaxis=dict(range=[0, 115]),
            )
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Kochi's low utilization is structural — the Bangalore pipeline link (GAIL Kochi–Koottanad–Bengaluru–Mangaluru) "
            "was delayed. Dahej remains India's primary regasification hub."
        )

    # PPAC import volumes
    ppac = data.get("ppac_monthly_import")
    if ppac:
        st.divider()
        st.subheader("📦 Latest Monthly LNG Imports")
        c1, c2 = st.columns(2)
        c1.metric("Import Volume", f"{ppac['volume_mmt']} MMT", help=f"Period: {ppac['month']}")
        c2.metric("Period", ppac["month"])
        st.caption(f"Source: {ppac['source']}")

    # Context
    ctx = data.get("india_lng_imports_context", {})
    if ctx:
        st.divider()
        st.subheader("📌 India LNG — Key Context")
        st.markdown(
            f"""
- **Primary suppliers:** {', '.join(ctx.get('primary_suppliers', []))}
- **Long-term contracts:** {ctx.get('long_term_contracts', '')}
- **Spot exposure:** {ctx.get('spot_dependency', '')}
            """
        )
