import io
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Advanced Tender Intelligence Dashboard - SSS",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

NAVY = "#0F1E36"
BLUE = "#1D4ED8"
LIGHT_BLUE = "#3B82F6"
GREEN = "#10B981"
RED = "#EF4444"
AMBER = "#F59E0B"
PURPLE = "#8B5CF6"
BG = "#F8FAFC"
CURRENCY = "₹"

# ------------------------------------------------------------------
# ENHANCED CSS
# ------------------------------------------------------------------
st.markdown(
    f"""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {{display: none;}}
    header[data-testid="stHeader"] {{background: transparent;}}
    .stApp {{background: {BG};}}
    .block-container {{padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px;}}

    /* Advanced Banner */
    .banner {{
        background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 100%);
        color: white; text-align: center; padding: 22px 10px;
        border-radius: 14px; box-shadow: 0 4px 20px rgba(15,30,54,.2);
        margin-bottom: 20px;
    }}
    .banner h1 {{margin: 0; font-size: 2.2rem; letter-spacing: 1.5px; font-weight: 800; color: white;}}
    .banner p {{margin: 6px 0 0 0; font-size: .95rem; opacity: .9; letter-spacing: 1px;}}

    /* Custom Responsive Buttons */
    div.stButton > button {{
        width: 100%; height: 54px; border-radius: 12px; font-weight: 700;
        letter-spacing: .5px; border: 1px solid {BLUE}; transition: all .25s ease;
        font-size: 0.9rem !important;
    }}
    div.stButton > button[kind="secondary"],
    div.stButton > button[data-testid="stBaseButton-secondary"] {{
        background: white; color: {BLUE};
    }}
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {BLUE}, {NAVY}); color: white; border: none;
        box-shadow: 0 4px 12px rgba(29,78,216,.3);
    }}
    div.stButton > button:hover {{transform: translateY(-2px); box-shadow: 0 6px 16px rgba(29,78,216,.25);}}

    /* Premium Metric Grid */
    .kpi {{
        background: white; border-radius: 12px; padding: 18px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,.04); border-top: 5px solid {BLUE};
        transition: transform 0.2s;
    }}
    .kpi:hover {{transform: translateY(-2px);}}
    .kpi .label {{font-size: .8rem; color: #64748B; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}}
    .kpi .value {{font-size: 1.8rem; font-weight: 800; color: {NAVY}; margin-top: 6px;}}
    .kpi.green {{border-top-color: {GREEN};}}
    .kpi.red {{border-top-color: {RED};}}
    .kpi.amber {{border-top-color: {AMBER};}}
    .kpi.purple {{border-top-color: {PURPLE};}}

    .section-title {{
        color: {NAVY}; font-weight: 800; font-size: 1.3rem;
        border-left: 5px solid {BLUE}; padding-left: 10px; margin: 25px 0 15px 0;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# EXTENDED DATABASE ARCHITECTURE
# ------------------------------------------------------------------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("tenders_v2.db", check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_name TEXT,
            party TEXT,
            amount REAL,
            due_date TEXT,
            status TEXT,
            remarks TEXT,
            submission_type TEXT)"""
    )
    conn.commit()
    return conn

conn = get_conn()

def load_df() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM tenders ORDER BY id DESC", conn)
    if not df.empty:
        df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
        today = pd.Timestamp(date.today())
        df["days_left"] = (df["due_date"] - today).dt.days
        df["alert"] = df.apply(
            lambda r: "✅ Completed" if r["status"] == "Completed"
            else ("🔷 Participated" if "Bidded" in str(r["status"])
            else ("❌ Dropped" if "Dropped" in str(r["status"])
            else ("🔴 Overdue" if r["days_left"] < 0 else ("🟠 Due Soon" if r["days_left"] <= 7 else "🟢 On Track")))),
            axis=1,
        )
    return df

def money(x: float) -> str:
    return f"{CURRENCY}{x:,.2f}"

def kpi(col, label, value, cls=""):
    col.markdown(
        f'<div class="kpi {cls}"><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )

STATUS_OPTIONS = ["Pending", "Completed", "Bidded (Participated)", "Dropped (Not Participated)"]

TABLE_CONFIG = {
    "id": st.column_config.NumberColumn("Tender ID", width="small"),
    "tender_name": "Tender Nomenclature",
    "party": "Authority / Party",
    "amount": st.column_config.NumberColumn("Valuation", format=f"{CURRENCY}%.2f"),
    "due_date": st.column_config.DateColumn("Deadline Date", format="DD MMM YYYY"),
    "status": "Current Status",
    "submission_type": "Mode",
    "days_left": st.column_config.NumberColumn("Days Remaining"),
    "alert": "Operational Lifecycle",
}
TABLE_COLS = ["id", "tender_name", "party", "amount", "due_date", "status", "submission_type", "days_left", "alert"]

# ------------------------------------------------------------------
# SMART TELEMETRY & BANNER
# ------------------------------------------------------------------
st.markdown(
    '<div class="banner"><h1>📑 TENDER COMMAND STATION & INTELLIGENCE</h1>'
    "<p>A TO Z EXECUTIVE LEVEL ADMINISTRATIVE SUITE</p></div>",
    unsafe_allow_html=True,
)

# UPGRADED 5 SYSTEM NAV BUTTONS
PAGES = ["Dashboard", "Manage A-Z Records", "🛡️ Participated", "❌ Not Participated", "📊 Advanced Analytics"]

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

def navigate(p):
    st.session_state.page = p

nav_cols = st.columns(5, gap="small")
for col, p in zip(nav_cols, PAGES):
    col.button(
        p.upper(),
        key=f"nav_{p}",
        on_click=navigate,
        args=(p,),
        type="primary" if st.session_state.page == p else "secondary",
        use_container_width=True,
    )

page = st.session_state.page
st.write("")
df = load_df()

# ------------------------------------------------------------------
# INTERACTIVE SUITE VIEW ROUTING
# ------------------------------------------------------------------
if df.empty and page != "Manage A-Z Records":
    st.info("⚡ System Database is empty. Please open 'Manage A-Z Records' to register your initial data.")
else:
    # --------------------------------------------------------------
    # MODULE 1: COMPREHENSIVE DASHBOARD
    # --------------------------------------------------------------
    if page == "Dashboard":
        part_count = len(df[df["status"] == "Bidded (Participated)"])
        not_part_count = len(df[df["status"] == "Dropped (Not Participated)"])
        pending = df[df["status"] == "Pending"]
        overdue = pending[pending["days_left"] < 0]

        # Metric Command Rows
        k1, k2, k3, k4, k5 = st.columns(5)
        kpi(k1, "Total Pipeline Records", len(df))
        kpi(k2, "Gross Cumulative Value", money(df["amount"].sum()), "purple")
        kpi(k3, "👍 Participated Count", part_count, "green")
        kpi(k4, "👎 Not Participated", not_part_count, "amber")
        kpi(k5, "🔴 Critical Overdue", len(overdue), "red")

        # Visual Dashboard Split Analytics
        st.markdown('<div class="section-title">Core Performance Architecture</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(
                df, names="status", values="amount", hole=0.6,
                color="status",
                color_discrete_map={
                    "Pending": AMBER, "Completed": GREEN, 
                    "Bidded (Participated)": BLUE, "Dropped (Not Participated)": RED
                },
                title="Monetary Value Split Distribution (Donut Level)",
            )
            fig.update_layout(margin=dict(t=50, b=10, l=10, r=10), paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            by_party = df.groupby(["party", "status"], as_index=False)["amount"].sum()
            fig = px.bar(
                by_party, x="party", y="amount", color="status", barmode="stack",
                color_discrete_map={
                    "Pending": AMBER, "Completed": GREEN, 
                    "Bidded (Participated)": BLUE, "Dropped (Not Participated)": RED
                },
                title="Operational Exposure Breakdown by Party Stack",
            )
            fig.update_layout(margin=dict(t=50, b=10, l=10, r=10), paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-title">Recent High-Value Strategic Tenders</div>', unsafe_allow_html=True)
        st.dataframe(
            df.head(10)[TABLE_COLS], column_config=TABLE_CONFIG,
            hide_index=True, use_container_width=True,
        )

    # --------------------------------------------------------------
    # MODULE 2: MASTER A-Z MANAGEMENT (ADD / EDIT / SEARCH)
    # --------------------------------------------------------------
    elif page == "Manage A-Z Records":
        t1, t2 = st.tabs(["➕ Add New Record Entry", "🔍 Master A-Z Directory & Editor"])
        
        with t1:
            st.markdown('<div class="section-title">Register New Tender Details</div>', unsafe_allow_html=True)
            with st.form("master_add_form", clear_on_submit=True):
                a1, a2 = st.columns(2)
