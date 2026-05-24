"""
Panel: Strategic Petroleum Reserves (SPR / ISPRL).
Shows fill level, days of import cover, site breakdown, and data freshness.
"""
import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load() -> dict | None:
    p = DATA_DIR / "spr_status.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def render() -> None:
    st.header("🛢️ Strategic Petroleum Reserves (ISPRL)")
    data = load()

    if data is None:
        st.error("No SPR data found. Run `python -m scrapers.spr_isprl` to fetch.")
        return

    # Honest data-freshness callout
    st.info(
        f"ℹ️ **Data note:** ISPRL does not publish daily fill levels. "
        f"The figures below reflect the most recent verified parliamentary report "
        f"(**{data.get('last_verified', 'N/A')}**). "
        f"They will update when a new parliamentary statement or PIB release is detected.",
        icon=None,
    )

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Phase-1 Fill", f"{data['fill_mmt']} MMT", delta=None)
    c2.metric("Fill %", f"{data['fill_pct']:.1f}%")
    c3.metric("Days of Import Cover", f"{data['days_of_import_cover']} days")
    c4.metric("Phase-1 Capacity", f"{data['phase1_capacity_mmt']} MMT")

    st.divider()

    # Gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=data["fill_pct"],
        title={"text": "SPR Fill Level (Phase-1)", "font": {"size": 16}},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%"},
            "bar": {"color": "#FF6B00"},
            "steps": [
                {"range": [0, 40], "color": "#d62728"},
                {"range": [40, 70], "color": "#ff7f0e"},
                {"range": [70, 100], "color": "#2ca02c"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 3},
                "thickness": 0.8,
                "value": data["fill_pct"],
            },
        },
        number={"suffix": "%"},
    ))
    fig.update_layout(height=300, margin=dict(t=60, b=20, l=20, r=20),
                      paper_bgcolor="rgba(0,0,0,0)", font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    # Sites table
    st.subheader("ISPRL Storage Sites")
    sites = data.get("sites", [])
    if sites:
        import pandas as pd
        df = pd.DataFrame(sites)
        df.columns = ["Location", "State", "Capacity (MMT)"]
        st.dataframe(df, use_container_width=True, hide_index=True)

    # Phase-2 callout
    st.subheader("Phase-2 Expansion (Approved)")
    st.markdown(
        f"""
| Site | Capacity |
|---|---|
| Padur (expansion) | 2.5 MMT |
| Bikaner, Rajasthan | 2.5 MMT |
| Chandikhol, Odisha | 4.0 MMT |
| **Total Phase-2 addition** | **{data['phase2_capacity_mmt']} MMT** |
        """
    )

    # Source
    st.caption(f"Source: {data.get('source', 'N/A')} · as_of: {data.get('as_of')}")

    # PIB alert
    if data.get("latest_pib"):
        pib = data["latest_pib"]
        st.success(f"📢 Recent PIB mention: [{pib.get('headline')}]({pib.get('url', '#')})")
