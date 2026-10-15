import io
import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import time
import traceback


# ==================================================================
# COMPATIBILITY HELPERS (alag-alag Streamlit versions me error na aaye)
# ==================================================================
def do_rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun")
    fn()


def _s(obj, name, *args, **kwargs):
    """use_container_width purane versions me, width='stretch' naye versions me."""
    kwargs.pop("use_container_width", None)
    fn = getattr(obj, name)
    try:
        return fn(*args, use_container_width=True, **kwargs)
    except Exception:
        return fn(*args, width="stretch", **kwargs)

# ==================================================================
# PAGE CONFIG
# ==================================================================
st.set_page_config(
    page_title="Tender Portal - SSS",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

NAVY = "#12264A"
BLUE = "#2F5FB3"
GREEN = "#1E9E6A"
RED = "#D64545"
AMBER = "#E8A317"
PURPLE = "#7B5EA7"
TEAL = "#17A2B8"
GREY = "#9AA5B8"
BG = "#EEF2F8"
CUR = "₹"
PALETTE = [BLUE, GREEN, AMBER, RED, PURPLE, TEAL, "#FF7F50", GREY]

CMAP_PART = {"Participated": BLUE, "Not Participated": GREY}
CMAP_RESULT = {"Won": GREEN, "Lost": RED, "Pending": AMBER, "Cancelled": GREY}
CMAP_STATUS = {"Pending": AMBER, "Completed": GREEN}
CMAP_EMD = {"Paid": BLUE, "Refunded": GREEN, "Pending": AMBER, "Forfeited": RED, "Not Applicable": GREY}

PARTICIPATION = ["Participated", "Not Participated"]
RESULTS = ["Pending", "Won", "Lost", "Cancelled"]
STATUSES = ["Pending", "Completed"]
EMD_STATUS = ["Not Applicable", "Paid", "Refunded", "Pending", "Forfeited"]
CATEGORIES = ["Works", "Supply", "Service", "Consultancy", "Maintenance", "Other"]

# ==================================================================
# CSS  (full width, official portal look)
# ==================================================================
st.markdown(
    f"""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {{display:none;}}
    header[data-testid="stHeader"] {{background:transparent;}}
    .stApp {{background:{BG};}}
    .block-container {{max-width:100% !important; padding:0.8rem 2.2rem 2rem 2.2rem;}}

    .topbar {{
        background:{NAVY}; color:#cfd9ee; font-size:.78rem; padding:6px 18px;
        border-radius:8px 8px 0 0; display:flex; justify-content:space-between; letter-spacing:.8px;
    }}
    .banner {{
        background:linear-gradient(120deg,{NAVY} 0%,{BLUE} 60%,{TEAL} 100%);
        color:white; text-align:center; padding:22px 10px; margin-bottom:16px;
        border-radius:0 0 14px 14px; box-shadow:0 6px 18px rgba(18,38,74,.30);
    }}
    .banner h1 {{margin:0; font-size:2.2rem; letter-spacing:3px; font-weight:800; color:white;}}
    .banner p {{margin:6px 0 0 0; font-size:.85rem; opacity:.9; letter-spacing:2px;}}

    div.stButton > button {{
        width:100%; height:50px; border-radius:10px; font-weight:700; letter-spacing:.4px;
        border:1px solid {BLUE}; transition:all .2s; font-size:.85rem;
    }}
    div.stButton > button[kind="secondary"], div.stButton > button[data-testid="stBaseButton-secondary"] {{
        background:white; color:{BLUE};
    }}
    div.stButton > button[kind="primary"], div.stButton > button[data-testid="stBaseButton-primary"] {{
        background:linear-gradient(135deg,{BLUE},{NAVY}); color:white; border:none;
        box-shadow:0 4px 10px rgba(47,95,179,.40);
    }}
    div.stButton > button:hover {{transform:translateY(-2px); box-shadow:0 6px 14px rgba(47,95,179,.30);}}

    .kpi {{
        background:white; border-radius:12px; padding:14px 16px; height:100%;
        box-shadow:0 2px 10px rgba(0,0,0,.07); border-left:6px solid {BLUE};
    }}
    .kpi .label {{font-size:.72rem; color:#6B7A90; text-transform:uppercase; letter-spacing:1px; font-weight:700;}}
    .kpi .value {{font-size:1.55rem; font-weight:800; color:{NAVY}; margin-top:3px;}}
    .kpi.green {{border-left-color:{GREEN};}} .kpi.red {{border-left-color:{RED};}}
    .kpi.amber {{border-left-color:{AMBER};}} .kpi.purple {{border-left-color:{PURPLE};}}
    .kpi.teal {{border-left-color:{TEAL};}} .kpi.grey {{border-left-color:{GREY};}}

    .section-title {{
        color:{NAVY}; font-weight:800; font-size:1.1rem; border-bottom:3px solid {BLUE};
        display:inline-block; padding-bottom:3px; margin:20px 0 10px 0; letter-spacing:.5px;
    }}
    .footer {{text-align:center; color:#8A97AB; font-size:.8rem; margin-top:34px;}}

    /* ---------- Data-entry fields: saaf dikhein (white bg + halka blue border) ---------- */
    div[data-testid="stWidgetLabel"] p {{color:{NAVY}; font-weight:600; font-size:.86rem;}}
    div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {{
        background:#FFFFFF !important; border:1.5px solid #B8C6DF !important; border-radius:8px !important;
        transition:border-color .15s,