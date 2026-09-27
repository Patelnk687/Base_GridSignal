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

div[data-testid="stAlert"] { color: #152033 !important; }

.gs-brand,
.gs-brand * {
  font-size: 1.7rem; font-weight: 800; letter-spacing: -0.03em;
  color: #0a3d32 !important; margin-bottom: 0.2rem; line-height: 1.1;
  opacity: 1 !important;
}
.gs-track, .gs-track * { color: #243247 !important; font-size: 0.86rem; line-height: 1.35; margin-bottom: 0.8rem; opacity: 1 !important; }
.gs-topbar {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.55rem 1rem;
  margin: 0 0 0.85rem 0; padding: 0.15rem 0 0.75rem 0;
  border-bottom: 2px solid #0a3d32;
}
.stApp .gs-topbar-name,
.stApp .gs-topbar-name *,
.gs-topbar-name,
.gs-topbar-name * {
  font-size: 2.15rem !important; font-weight: 800 !important; letter-spacing: -0.04em; line-height: 1.05;
  color: #0a3d32 !important; font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important;
  opacity: 1 !important; -webkit-text-fill-color: #0a3d32 !important;
}
.stApp .gs-topbar-tag,
.stApp .gs-topbar-tag *,
.gs-topbar-tag,
.gs-topbar-tag * {
  color: #243247 !important; font-size: 0.95rem !important; font-weight: 600 !important;
  opacity: 1 !important; -webkit-text-fill-color: #243247 !important;
}
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
.gs-hero {
  background: linear-gradient(135deg, #0f6e56 0%, #147a8c 55%, #1d4ed8 100%);
  border-radius: 18px; padding: 1.25rem 1.4rem; margin: 0.35rem 0 1rem 0;
  color: #fff !important; box-shadow: 0 12px 40px rgba(15,110,86,0.22);
}
.gs-hero-brand,
.gs-hero-brand * {
  color: #ffffff !important; font-size: 2.35rem; font-weight: 800;
  letter-spacing: -0.045em; line-height: 1; margin: 0 0 0.45rem 0;
  opacity: 1 !important; -webkit-text-fill-color: #ffffff !important;
}
.gs-hero h1, .gs-hero h1 * {
  color: #ffffff !important; font-size: 1.2rem; font-weight: 600;
  margin: 0 0 0.4rem 0; letter-spacing: -0.01em; line-height: 1.3;
  opacity: 1 !important; -webkit-text-fill-color: #ffffff !important;
}
.gs-hero p, .gs-hero p * {
  color: #f0fdfa !important; margin: 0; font-size: 0.95rem; line-height: 1.45;
  opacity: 1 !important; -webkit-text-fill-color: #f0fdfa !important;
}
.gs-insight-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.75rem; margin: 0.4rem 0 1.1rem 0;
}
.gs-insight {
  border-radius: 14px; padding: 0.85rem 0.95rem; border: 1px solid #d7e0ea;
  background: #fff; box-shadow: 0 1px 0 rgba(16,35,63,0.04);
}
.gs-insight .eyebrow {
  font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
  font-weight: 600; margin-bottom: 0.25rem; font-family: "IBM Plex Mono", monospace;
}
.gs-insight .title { font-size: 1.05rem; font-weight: 700; color: #10233f !important; margin-bottom: 0.3rem; }
.gs-insight .body { font-size: 0.86rem; color: #3d4f63 !important; line-height: 1.4; }
.gs-insight.teal { border-top: 4px solid #0f6e56; }
.gs-insight.teal .eyebrow { color: #0f6e56 !important; }
.gs-insight.amber { border-top: 4px solid #c27803; }
.gs-insight.amber .eyebrow { color: #b45309 !important; }
.gs-insight.coral { border-top: 4px solid #e11d48; }
.gs-insight.coral .eyebrow { color: #be123c !important; }
.gs-insight.steel { border-top: 4px solid #2563eb; }
.gs-insight.steel .eyebrow { color: #1d4ed8 !important; }
.gs-sev {
  display: inline-block; padding: 0.12rem 0.5rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 700; font-family: "IBM Plex Mono", monospace;
}
.gs-sev-high { background: #ffe4e6; color: #be123c !important; }
.gs-sev-moderate { background: #ffedd5; color: #c2410c !important; }
.gs-sev-low { background: #e0f2fe; color: #0369a1 !important; }
div[data-testid="stMetric"] {
  background: linear-gradient(180deg, #ffffff 0%, #f7fbf9 100%) !important;
  border: 1px solid #cfe3da !important;
  border-radius: 16px;
  padding: 0.75rem 0.9rem;
  box-shadow: 0 8px 24px rgba(15,110,86,0.06);
}

/* Phone / narrow tablet */
@media (max-width: 768px) {
  .block-container {
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
    padding-top: 0.65rem !important;
    max-width: 100% !important;
  }
  .gs-brand { font-size: 1.4rem !important; }
  .gs-topbar-name { font-size: 1.65rem !important; }
  .gs-topbar-tag { font-size: 0.8rem !important; }
  .gs-hero { padding: 0.9rem 1rem !important; border-radius: 14px !important; }
  .gs-hero-brand { font-size: 1.85rem !important; }
  .gs-hero h1 { font-size: 1.05rem !important; }
  .gs-hero p { font-size: 0.88rem !important; }
  .gs-insight-grid { grid-template-columns: 1fr !important; gap: 0.55rem !important; }
  .gs-why, .gs-chart-note { padding: 0.65rem 0.75rem !important; font-size: 0.84rem !important; }
  .gs-step { font-size: 0.72rem !important; padding: 0.22rem 0.55rem !important; }
  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.5rem !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  div[data-testid="stMetric"] { padding: 0.55rem 0.7rem !important; margin-bottom: 0.25rem; }
  [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
  div[data-testid="stDataFrame"],
  div[data-testid="stTable"],
  .gs-scroll-table {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    max-width: 100%;
  }
  .gs-scroll-table table { min-width: 560px; }
  .js-plotly-plot .plotly .main-svg { max-width: 100% !important; }
  h1 { font-size: 1.45rem !important; }
  h2, h3 { font-size: 1.15rem !important; }
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
  background: linear-gradient(180deg, #182238 0%, #141a2e 100%) !important;
  border: 1px solid rgba(45,212,191,0.18) !important;
  border-radius: 16px;
  padding: 0.75rem 0.9rem;
}
div[data-testid="stAlert"] { color: #e7ecf5 !important; }
div[data-testid="stDataFrame"] { color: #e7ecf5 !important; }

.stRadio > div, [data-baseweb="radio"] label { color: #e7ecf5 !important; }
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
  background-color: #141a2e !important;
  color: #e7ecf5 !important;
}

.gs-brand,
.gs-brand * {
  font-size: 1.7rem; font-weight: 800; letter-spacing: -0.03em;
  color: #99f6e4 !important; margin-bottom: 0.2rem; line-height: 1.1;
  opacity: 1 !important;
}
.gs-track, .gs-track * { color: #d5dceb !important; font-size: 0.86rem; line-height: 1.35; margin-bottom: 0.8rem; opacity: 1 !important; }
.gs-topbar {
  display: flex; flex-wrap: wrap; align-items: baseline; gap: 0.55rem 1rem;
  margin: 0 0 0.85rem 0; padding: 0.15rem 0 0.75rem 0;
  border-bottom: 2px solid #5eead4;
}
.stApp .gs-topbar-name,
.stApp .gs-topbar-name *,
.gs-topbar-name,
.gs-topbar-name * {
  font-size: 2.15rem !important; font-weight: 800 !important; letter-spacing: -0.04em; line-height: 1.05;
  color: #99f6e4 !important; font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important;
  opacity: 1 !important; -webkit-text-fill-color: #99f6e4 !important;
}
.stApp .gs-topbar-tag,
.stApp .gs-topbar-tag *,
.gs-topbar-tag,
.gs-topbar-tag * {
  color: #e7ecf5 !important; font-size: 0.95rem !important; font-weight: 600 !important;
  opacity: 1 !important; -webkit-text-fill-color: #e7ecf5 !important;
}
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
.gs-hero {
  background: linear-gradient(135deg, #0d3f34 0%, #134e4a 40%, #1e3a5f 100%);
  border-radius: 18px; padding: 1.25rem 1.4rem; margin: 0.35rem 0 1rem 0;
  color: #fff !important; border: 1px solid rgba(45,212,191,0.25);
  box-shadow: 0 12px 40px rgba(0,0,0,0.35);
}
.gs-hero-brand,
.gs-hero-brand * {
  color: #ffffff !important; font-size: 2.35rem; font-weight: 800;
  letter-spacing: -0.045em; line-height: 1; margin: 0 0 0.45rem 0;
  opacity: 1 !important; -webkit-text-fill-color: #ffffff !important;
}
.gs-hero h1, .gs-hero h1 * {
  color: #ffffff !important; font-size: 1.2rem; font-weight: 600;
  margin: 0 0 0.4rem 0; letter-spacing: -0.01em; line-height: 1.3;
  opacity: 1 !important; -webkit-text-fill-color: #ffffff !important;
}
.gs-hero p, .gs-hero p * {
  color: #ecfeff !important; margin: 0; font-size: 0.95rem; line-height: 1.45;
  opacity: 1 !important; -webkit-text-fill-color: #ecfeff !important;
}
.gs-insight-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.75rem; margin: 0.4rem 0 1.1rem 0;
}
.gs-insight {
  border-radius: 14px; padding: 0.85rem 0.95rem;
  border: 1px solid rgba(255,255,255,0.08);
  background: #141a2e;
}
.gs-insight .eyebrow {
  font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase;
  font-weight: 600; margin-bottom: 0.25rem; font-family: "IBM Plex Mono", monospace;
}
.gs-insight .title { font-size: 1.05rem; font-weight: 700; color: #f3f6fb !important; margin-bottom: 0.3rem; }
.gs-insight .body { font-size: 0.86rem; color: #b6c2d6 !important; line-height: 1.4; }
.gs-insight.teal { border-top: 4px solid #2dd4bf; }
.gs-insight.teal .eyebrow { color: #5eead4 !important; }
.gs-insight.amber { border-top: 4px solid #f59e0b; }
.gs-insight.amber .eyebrow { color: #fbbf24 !important; }
.gs-insight.coral { border-top: 4px solid #fb7185; }
.gs-insight.coral .eyebrow { color: #fda4af !important; }
.gs-insight.steel { border-top: 4px solid #60a5fa; }
.gs-insight.steel .eyebrow { color: #93c5fd !important; }
.gs-sev {
  display: inline-block; padding: 0.12rem 0.5rem; border-radius: 999px;
  font-size: 0.72rem; font-weight: 700; font-family: "IBM Plex Mono", monospace;
}
.gs-sev-high { background: #4c0519; color: #fda4af !important; }
.gs-sev-moderate { background: #431407; color: #fdba74 !important; }
.gs-sev-low { background: #0c4a6e; color: #7dd3fc !important; }

/* Phone / narrow tablet */
@media (max-width: 768px) {
  .block-container {
    padding-left: 0.85rem !important;
    padding-right: 0.85rem !important;
    padding-top: 0.65rem !important;
    max-width: 100% !important;
  }
  .gs-brand { font-size: 1.4rem !important; }
  .gs-topbar-name { font-size: 1.65rem !important; }
  .gs-topbar-tag { font-size: 0.8rem !important; }
  .gs-hero { padding: 0.9rem 1rem !important; border-radius: 14px !important; }
  .gs-hero-brand { font-size: 1.85rem !important; }
  .gs-hero h1 { font-size: 1.05rem !important; }
  .gs-hero p { font-size: 0.88rem !important; }
  .gs-insight-grid { grid-template-columns: 1fr !important; gap: 0.55rem !important; }
  .gs-why, .gs-chart-note { padding: 0.65rem 0.75rem !important; font-size: 0.84rem !important; }
  .gs-step { font-size: 0.72rem !important; padding: 0.22rem 0.55rem !important; }
  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.5rem !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
  div[data-testid="stMetric"] { padding: 0.55rem 0.7rem !important; margin-bottom: 0.25rem; }
  [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
  div[data-testid="stDataFrame"],
  div[data-testid="stTable"],
  .gs-scroll-table {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
    max-width: 100%;
  }
  .gs-scroll-table table { min-width: 560px; }
  .js-plotly-plot .plotly .main-svg { max-width: 100% !important; }
  h1 { font-size: 1.45rem !important; }
  h2, h3 { font-size: 1.15rem !important; }
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


def render_main_brand() -> None:
    """Always-visible product name in the main pane (sidebar is collapsed on phones)."""
    st.markdown(
        '<div class="gs-topbar">'
        '<div class="gs-topbar-name">GridSignal</div>'
        '<div class="gs-topbar-tag">Open Grid Data · ERCOT anomalies, evidence &amp; virtual fleet</div>'
        "</div>",
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


def hero_block(title: str, subtitle: str, *, brand: str = "GridSignal") -> None:
    st.markdown(
        f'<div class="gs-hero">'
        f'<div class="gs-hero-brand">{brand}</div>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>",
        unsafe_allow_html=True,
    )


def insight_cards(cards: list) -> None:
    if not cards:
        return
    parts = ['<div class="gs-insight-grid">']
    for card in cards:
        parts.append(
            f'<div class="gs-insight {card.tone}">'
            f'<div class="eyebrow">{card.eyebrow}</div>'
            f'<div class="title">{card.title}</div>'
            f'<div class="body">{card.body}</div>'
            "</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def severity_pill(severity: str) -> str:
    key = str(severity).lower()
    css = {"high": "gs-sev-high", "moderate": "gs-sev-moderate", "low": "gs-sev-low"}.get(key, "gs-sev-low")
    return f'<span class="gs-sev {css}">{key}</span>'


def mode_banner(*, synthetic: bool, scenario_id: str, text: str) -> None:
    if synthetic:
        badge = "SYNTHETIC DEMO"
    elif scenario_id.startswith("LIVE"):
        badge = "LIVE SNAPSHOT"
    else:
        badge = "LIVE ERCOT"
    badge_class = "gs-badge" if synthetic else "gs-badge gs-badge-live"
    st.markdown(
        f'<div class="gs-kicker"><span class="{badge_class}">{badge}</span> · {scenario_id}</div>',
        unsafe_allow_html=True,
    )
    st.caption(text)


def synthetic_banner(text: str) -> None:
    mode_banner(synthetic=True, scenario_id="demo", text=text)
