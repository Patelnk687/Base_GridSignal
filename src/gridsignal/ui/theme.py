"""Dark dashboard chrome."""

from __future__ import annotations

import streamlit as st

CSS = """
<style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1240px;}
    .gs-kicker {
        color: #93a0b8; letter-spacing: 0.14em; text-transform: uppercase;
        font-size: 0.72rem; margin-bottom: 0.2rem;
    }
    .gs-badge {
        display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px;
        background: #3a2a12; color: #e2a84b; font-size: 0.75rem;
        font-weight: 600; margin-left: 0.4rem;
    }
    div[data-testid="stMetric"] {
        background: #141a2e; border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px; padding: 0.6rem 0.8rem;
    }
    .gs-note {color: #93a0b8; font-size: 0.9rem;}
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def synthetic_banner(text: str) -> None:
    st.markdown(
        '<div class="gs-kicker">GridSignal <span class="gs-badge">SYNTHETIC DEMO</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(text)
