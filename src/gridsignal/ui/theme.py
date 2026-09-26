"""Light / dark dashboard chrome with forced contrast for Streamlit widgets."""

from __future__ import annotations

import streamlit as st

# Streamlit's config.toml base theme does not switch with our radio.
# Both appearances must override widget text/backgrounds with !important.

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

:root { color-scheme: light; }
html, body, [class*="css"] { font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important; }

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background:
    radial-gradient(1200px 600px at 10% -10%, #d9ebe4 0%, transparent 55%),
    radial-gradient(900px 500px at 100% 0%, #e7eef8 0%, transparent 50%),
    #f3f6fa !important;
  color: #152033 !important;
}
[data-testid="stHeader"] { background: rgba(243,246,250,0.85) !important; }

.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1240px; }

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
  background: #eef3f8 !important;
  border-right: 1px solid #d5dee8;
  color: #152033 !important;
}

/* Force readable body copy */
.stApp p, .stApp li, .stApp label, .stApp span,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"],
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebarNav"] span,
[data-testid="stSidebarNav"] a,
div[data-baseweb="select"] > div,
.stRadio label, .stSelectbox label, .stSlider label {
  color: #152033 !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
  color: #4b5d73 !important;
}
h1, h2, h3, h4 { color: #10233f !important; letter-spacing: -0.02em; }

div[data-testid="stMetric"] {
  background: rgba(255,255,255,0.92) !important;
  border: 1px solid #d7e0ea !important;
  border-radius: 14px;
  padding: 0.7rem 0.85rem;
}
div[data-testid="stAlert"] { color: #152033 !important; }

.gs-brand { font-size: 1.55rem; font-weight: 700; letter-spacing: -0.02em; color: #10233f !important; margin-bottom: 0.15rem; }
.gs-track { color: #4b5d73 !important; font-size: 0.86rem; line-height: 1.35; margin-bottom: 0.8rem; }
.gs-kicker { color: #5b6b7c !important; letter-spacing: 0.12em; text-transform: uppercase; font-size: 0.72rem; margin-bottom: 0.35rem; }
.gs-badge {
  display: inline-block; padding: 0.16rem 0.55rem; border-radius: 999px;
  background: #fff4e0 !important; color: #9a6700 !important; font-size: 0.72rem;
  font-weight: 600; margin-left: 0.35rem; font-family: "IBM Plex Mono", monospace;
}
.gs-badge-live { background: #ddf4ec !important; color: #0f6e56 !important; }
.gs-why {
  background: rgba(255,255,255,0.95) !important;
  border: 1px solid #d7e0ea; border-left: 4px solid #0f6e56;
  border-radius: 10px; padding: 0.85rem 1rem; margin: 0.4rem 0 1rem 0;
  color: #243247 !important;
}
.gs-why strong, .gs-why code { color: #0f6e56 !important; }
.gs-chart-note {
  background: rgba(255,255,255,0.78);
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  padding: 0.55rem 0.75rem;
  margin: -0.35rem 0 1rem 0;
  color: #243247 !important;
  font-size: 0.88rem;
  line-height: 1.4;
}
.gs-chart-note strong { color: #0f6e56 !important; }
.gs-pipeline {
  display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.2rem 0 1rem 0;
}
.gs-step {
  background: #fff; border: 1px solid #d7e0ea; color: #152033 !important;
  border-radius: 999px; padding: 0.28rem 0.7rem; font-size: 0.78rem; font-weight: 500;
}
</style>
"""

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

:root { color-scheme: dark; }
html, body, [class*="css"] { font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important; }

.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background:
    radial-gradient(1000px 500px at 0% 0%, #163528 0%, transparent 45%),
    radial-gradient(900px 500px at 100% 0%, #1a2438 0%, transparent 50%),
    #0b1020 !important;
  color: #e7ecf5 !important;
}
[data-testid="stHeader"] { background: rgba(11,16,32,0.9) !important; }

.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1240px; }

section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
  background: #10182b !important;
  border-right: 1px solid rgba(255,255,255,0.08);
  color: #e7ecf5 !important;
}

/* Force readable body copy on dark surfaces */
.stApp p, .stApp li, .stApp label, .stApp span,
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stCaptionContainer"],
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"],
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebarNav"] span,
[data-testid="stSidebarNav"] a,
div[data-baseweb="select"] > div,
.stRadio label, .stSelectbox label, .stSlider label,
.stNumberInput label, .stTextInput label {
  color: #e7ecf5 !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
  color: #a8b3c7 !important;
}
h1, h2, h3, h4 { color: #f3f6fb !important; letter-spacing: -0.02em; }

div[data-testid="stMetric"] {
  background: #141a2e !important;
  border: 1px solid rgba(255,255,255,0.10) !important;
  border-radius: 14px;
  padding: 0.7rem 0.85rem;
}
div[data-testid="stAlert"] { color: #e7ecf5 !important; }
div[data-testid="stDataFrame"] { color: #e7ecf5 !important; }

/* Inputs / radios on dark */
.stRadio > div, [data-baseweb="radio"] label { color: #e7ecf5 !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
  background-color: #141a2e !important;
  color: #e7ecf5 !important;
}

.gs-brand { font-size: 1.55rem; font-weight: 700; letter-spacing: -0.02em; color: #f3f6fb !important; margin-bottom: 0.15rem; }
.gs-track { color: #a8b3c7 !important; font-size: 0.86rem; line-height: 1.35; margin-bottom: 0.8rem; }
.gs-kicker { color: #a8b3c7 !important; letter-spacing: 0.12em; text-transform: uppercase; font-size: 0.72rem; margin-bottom: 0.35rem; }
.gs-badge {
  display: inline-block; padding: 0.16rem 0.55rem; border-radius: 999px;
  background: #3a2a12 !important; color: #f0c674 !important; font-size: 0.72rem;
  font-weight: 600; margin-left: 0.35rem; font-family: "IBM Plex Mono", monospace;
}
.gs-badge-live { background: #122a1c !important; color: #5eead4 !important; }
.gs-why {
  background: rgba(20,26,46,0.95) !important;
  border: 1px solid rgba(255,255,255,0.10); border-left: 4px solid #2dd4bf;
  border-radius: 10px; padding: 0.85rem 1rem; margin: 0.4rem 0 1rem 0;
  color: #e7ecf5 !important;
}
.gs-why p, .gs-why span { color: #e7ecf5 !important; }
.gs-why strong, .gs-why code { color: #5eead4 !important; }
.gs-chart-note {
  background: rgba(20,26,46,0.92);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 8px;
  padding: 0.55rem 0.75rem;
  margin: -0.35rem 0 1rem 0;
  color: #d5dceb !important;
  font-size: 0.88rem;
  line-height: 1.4;
}
.gs-chart-note strong { color: #5eead4 !important; }
.gs-pipeline {
  display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.2rem 0 1rem 0;
}
.gs-step {
  background: #141a2e; border: 1px solid rgba(255,255,255,0.12); color: #e7ecf5 !important;
  border-radius: 999px; padding: 0.28rem 0.7rem; font-size: 0.78rem; font-weight: 500;
}
</style>
"""


def get_appearance() -> str:
    return st.session_state.get("gs_appearance", "light")


def appearance_toggle() -> str:
    choice = st.sidebar.radio(
        "Appearance",
        options=["Light", "Dark"],
        index=0 if get_appearance() == "light" else 1,
        horizontal=True,
        key="gs_appearance_radio",
    )
    appearance = "light" if choice == "Light" else "dark"
    st.session_state["gs_appearance"] = appearance
    return appearance


def apply_theme() -> None:
    st.markdown(LIGHT_CSS if get_appearance() == "light" else DARK_CSS, unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    st.sidebar.markdown('<div class="gs-brand">GridSignal</div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="gs-track"><strong style="color:inherit">Track 1 — Open Grid Data.</strong> '
        "ERCOT publishes prices, load, generation, congestion. Most people stare at raw charts. "
        "GridSignal finds co-moving odd hours, cites the measurements, then asks what a virtual "
        "home-battery fleet would have done — offline from a saved week.</div>",
        unsafe_allow_html=True,
    )


def chart_note(title: str, body: str) -> None:
    """Short explainer under a chart — what the axes are and what to look for."""
    st.markdown(
        f'<div class="gs-chart-note"><strong>{title}</strong> {body}</div>',
        unsafe_allow_html=True,
    )


def why_block(html: str) -> None:
    st.markdown(f'<div class="gs-why">{html}</div>', unsafe_allow_html=True)


def pipeline_strip() -> None:
    st.markdown(
        '<div class="gs-pipeline">'
        '<span class="gs-step">1 · ERCOT ingest + cache</span>'
        '<span class="gs-step">2 · Causal anomalies</span>'
        '<span class="gs-step">3 · Stress score</span>'
        '<span class="gs-step">4 · Evidence IDs</span>'
        '<span class="gs-step">5 · Battery strategies</span>'
        "</div>",
        unsafe_allow_html=True,
    )


def mode_banner(*, synthetic: bool, scenario_id: str, text: str) -> None:
    if synthetic:
        badge = "SYNTHETIC DEMO"
    elif scenario_id.startswith("LIVE"):
        badge = "LIVE SNAPSHOT"
    else:
        badge = "LIVE ERCOT"
    badge_class = "gs-badge" if synthetic else "gs-badge gs-badge-live"
    st.markdown(
        f'<div class="gs-kicker">GridSignal <span class="{badge_class}">{badge}</span> · {scenario_id}</div>',
        unsafe_allow_html=True,
    )
    st.caption(text)


def synthetic_banner(text: str) -> None:
    mode_banner(synthetic=True, scenario_id="demo", text=text)
