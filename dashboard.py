"""Small presentation layer for the existing Streamlit investigation app."""
import streamlit as st


def apply_style():
    st.markdown('''<style>
    .stApp {background: #f5f7f9; color: #162d3b;}
    .stMainBlockContainer {max-width: 1480px; padding-top: 4rem; padding-bottom: 3rem;}
    [data-testid="stAppDeployButton"] {display: none;}
    h1, h2, h3 {letter-spacing: -.035em; color: #102b3b;}
    h1 {font-size: 2.8rem !important;}
    [data-testid="stSidebar"] {background: #102e3c;}
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color: #e2edf1;}
    [data-testid="stSidebar"] [data-baseweb="select"] {color: #162d3b;}
    [data-testid="stSidebar"] hr {border-color: #34515e;}
    [data-testid="stMetric"] {background: white; padding: 1rem 1.2rem; border: 1px solid #dbe5e9;
        border-radius: 12px; min-height: 112px; border-top: 3px solid #087f83;}
    [data-testid="stMetricValue"] {font-size: clamp(1.3rem, 2vw, 2rem);}
    [data-testid="stPlotlyChart"] {border-radius: 14px; overflow: hidden; border: 1px solid #e0e8eb;}
    [data-testid="stTabs"] [role="tablist"] {gap: 1.5rem; margin-bottom: 1rem;}
    [data-testid="stTabs"] [role="tab"] {font-weight: 600;}
    .eyebrow {font-size: .74rem; font-weight: 700; letter-spacing: .15em; color: #147d80; margin-bottom: .35rem;}
    .intro {font-size: 1.05rem; max-width: 900px; color: #526674; margin: 0 0 .5rem;}
    .step {font-size: .74rem; text-transform: uppercase; letter-spacing: .1em; font-weight: 700; color: #9ccdd1; margin-top: 1rem;}
    .science-note {border-left: 3px solid #087f83; padding: .2rem 0 .2rem 1rem; margin: 1rem 0; color: #385360;}
    @media (max-width: 700px) {
      .stMainBlockContainer {padding: 5rem 1rem 2rem;}
      h1 {font-size: 2.1rem !important;}
      [data-testid="stMetric"] {min-height: 90px; padding: .8rem;}
      [data-testid="stTabs"] [role="tablist"] {gap: .7rem;}
    }
    </style>''', unsafe_allow_html=True)


def render_header():
    st.markdown('<div class="eyebrow">TERRAVECT / EARTH SYSTEM INVESTIGATIONS</div>', unsafe_allow_html=True)
    st.title('TrendLens')
    st.markdown('<p class="intro">Explore a changing Earth. NASA temperature records, '
                'with the evidence and uncertainty in view.</p>', unsafe_allow_html=True)


def step(number: int, title: str):
    st.markdown(f'<div class="step">0{number} / {title}</div>', unsafe_allow_html=True)
