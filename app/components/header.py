"""Shared header and metadata freshness banner."""
import json
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def render_header() -> None:
    st.markdown(
        """
        <div style='
            background: linear-gradient(90deg, #FF6B00 0%, #FF8C00 50%, #FFA500 100%);
            padding: 1rem 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        '>
            <h1 style='color:white; margin:0; font-size:1.8rem;'>
                ⛽ India Energy Intelligence Dashboard
            </h1>
            <p style='color:rgba(255,255,255,0.9); margin:0.2rem 0 0 0; font-size:0.95rem;'>
                Strategic Reserves · Fuel Prices · Crude Benchmarks · LNG · Market Attribution
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metadata_banner() -> None:
    meta_path = DATA_DIR / "metadata.json"
    if not meta_path.exists():
        st.warning("⚠️ No metadata file found — data may not have been fetched yet. Run scrapers first.")
        return

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    with st.expander("🕐 Data freshness", expanded=False):
        cols = st.columns(3)
        items = list(meta.items())
        for i, (source, info) in enumerate(items):
            col = cols[i % 3]
            status = info.get("status", "unknown")
            icon = "✅" if status == "ok" else "❌"
            col.markdown(
                f"**{icon} {source}**  \n`{info.get('updated_at', 'N/A')}`"
            )
