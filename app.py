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
# COMPATIBILITY HELPERS
# ==================================================================
def do_rerun():
    fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun")
    fn()

def _s(obj, name, *args, **kwargs):
    kwargs.pop("use_container_width", None)
    fn = getattr(obj, name)
    try:
        return fn(*args, use_container_width=True, **kwargs)
    except Exception:
        return fn(*args, width="stretch", **kwargs)

# ==================================================================
# PAGE CONFIG & STYLING
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
    div[data-testid="stWidgetLabel"] p {{color:{NAVY}; font-weight:600; font-size:.86rem;}}
    div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {{
        background:#FFFFFF !important; border:1.5px solid #B8C6DF !important; border-radius:8px !important;
    }}
    div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {{color:#1B2A44 !important;}}
</style>
""",
    unsafe_allow_html=True,
)

# ==================================================================
# DATABASE SETUP WITH USER TABLE
# ==================================================================
DB_COLS = {
    "tender_no": "TEXT", "tender_name": "TEXT", "department": "TEXT", "party": "TEXT",
    "category": "TEXT", "location": "TEXT", "participation": "TEXT", "not_part_reason": "TEXT",
    "estimated_cost": "REAL", "amount": "REAL", "emd_amount": "REAL", "emd_status": "TEXT",
    "tender_fee": "REAL", "publish_date": "TEXT", "due_date": "TEXT", "opening_date": "TEXT",
    "result": "TEXT", "status": "TEXT", "work_order_no": "TEXT", "remarks": "TEXT",
    "work_description": "TEXT", "no_of_awardees": "INTEGER", "created_at": "TEXT",
}
TEXT_COLS = [c for c, t in DB_COLS.items() if t == "TEXT" and not c.endswith("_date") and c != "created_at"]
NUM_COLS = ["estimated_cost", "amount", "emd_amount", "tender_fee"]
DATE_COLS = ["publish_date", "due_date", "opening_date"]

@st.cache_resource
def get_conn():
    conn = sqlite3.connect("tenders.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS tenders (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tenders)").fetchall()}
    for col, typ in DB_COLS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE tenders ADD COLUMN {col} {typ}")
            
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "Admin"))
    conn.commit()
    return conn

conn = get_conn()

# ==================================================================
# CORE FUNCTIONS
# ==================================================================
def fy_of(d):
    if pd.isna(d): return "Unknown"
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"

def alert_of(r):
    if r["participation"] == "Not Participated": return "⚪ Not Participated"
    if r["status"] == "Completed": return "✅ Completed"
    if r["result"] in ("Lost", "Cancelled"): return "⚫ Closed"
    if pd.isna(r["days_left"]): return "⚪ No Date"
    if r["days_left"] < 0: return "🔴 Overdue"
    if r["days_left"] <= 7: return "🟠 Due Soon"
    return "🟢 On Track"

def load_df() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM tenders ORDER BY id DESC", conn)
    if df.empty: return df
    for c in TEXT_COLS: df[c] = df[c].fillna("")
    for c in NUM_COLS: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["no_of_awardees"] = pd.to_numeric(df["no_of_awardees"], errors="coerce").fillna(0).astype(int)
    df["participation"] = df["participation"].replace("", "Participated")
    df["result"] = df["result"].replace("", "Pending")
    df["status"] = df["status"].replace("", "Pending")
    df["emd_status"] = df["emd_status"].replace("", "Not Applicable")
    for c in DATE_COLS: df[c] = pd.to_datetime(df[c], errors="coerce")
    df["days_left"] = (df["due_date"] - pd.Timestamp(date.today())).dt.days
    df["fy"] = df["due_date"].apply(fy_of)
    df["month"] = df["due_date"].dt.strftime("%Y-%m")
    df["alert"] = df.apply(alert_of, axis=1)
    return df

def bump():
    st.session_state["ver"] = st.session_state.get("ver", 0) + 1

def insert_record(v: dict):
    cols = list(v)
    conn.execute(f"INSERT INTO tenders ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(v.values()))
    conn.commit()
    bump()

def update_record(rid: int, v: dict):
    sets = ",".join(f"{c}=?" for c in v)
    conn.execute(f"UPDATE tenders SET {sets} WHERE id=?", list(v.values()) + [rid])
    conn.commit()
    bump()

def inr(x: float) -> str:
    x = float(x or 0)
    if abs(x) >= 1e7: return f"{CUR}{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5: return f"{CUR}{x / 1e5:.2f} L"
    return f"{CUR}{x:,.0f}"

def kpi(col, label, value, cls=""):
    col.markdown(f'<div class="kpi {cls}"><div class="label">{label}</div><div class="value">{value}</div></div>', unsafe_allow_html=True)

def title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)

def style(fig, text, h=360):
    fig.update_layout(
        title=dict(text=text, font=dict(size=16, color=NAVY)),
        height=h, margin=dict(t=55, b=15, l=15, r=15),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(color="#33415C"), legend=dict(orientation="h", y=-0.12),
    )
    return fig

def donut(df, col, text, cmap, key, value=None):
    if df.empty:
        st.info(f"{text}: data nahi hai")
        return
    g = df.groupby(col, as_index=False)[value].sum() if value else df.groupby(col).size().reset_index(name="count")
    vals = value if value else "count"
    fig = px.pie(g, names=col, values=vals, hole=0.58, color=col, color_discrete_map=cmap)
    fig.update_traces(textinfo="percent", textfont_size=13)
