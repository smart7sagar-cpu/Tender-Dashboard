import io
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# EXECUTIVE ULTRA-WIDE PAGE CONFIG
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Tender Intelligence Command Center - SSS",
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
# WIDESCREEN WEB VIEW ARCHITECTURE (CSS)
# ------------------------------------------------------------------
st.markdown(
    f"""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {{display: none;}}
    header[data-testid="stHeader"] {{background: transparent;}}
    .stApp {{background: {BG};}}
    
    .block-container {{
        padding-top: 1rem !important; 
        padding-bottom: 2rem !important; 
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 98% !important; 
    }}

    .banner {{
        background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 100%);
        color: white; text-align: center; padding: 20px 15px;
        border-radius: 14px; box-shadow: 0 4px 20px rgba(15,30,54,.2);
        margin-bottom: 20px; width: 100%;
    }}
    .banner h1 {{margin: 0; font-size: 2.2rem; letter-spacing: 1.5px; font-weight: 800; color: white;}}
    .banner p {{margin: 4px 0 0 0; font-size: 0.95rem; opacity: .9; letter-spacing: 1px;}}

    div.stButton > button {{
        width: 100%; height: 52px; border-radius: 12px; font-weight: 700;
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

    .kpi {{
        background: white; border-radius: 12px; padding: 20px 22px;
        box-shadow: 0 4px 12px rgba(0,0,0,.04); border-top: 6px solid {BLUE};
        transition: transform 0.2s; width: 100%;
    }}
    .kpi:hover {{transform: translateY(-2px);}}
    .kpi .label {{font-size: .8rem; color: #64748B; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;}}
    .kpi .value {{font-size: 1.9rem; font-weight: 800; color: {NAVY}; margin-top: 4px;}}
    .kpi.green {{border-top-color: {GREEN};}}
    .kpi.red {{border-top-color: {RED};}}
    .kpi.amber {{border-top-color: {AMBER};}}
    .kpi.purple {{border-top-color: {PURPLE};}}

    .section-title {{
        color: {NAVY}; font-weight: 800; font-size: 1.35rem;
        border-left: 6px solid {BLUE}; padding-left: 12px; margin: 25px 0 15px 0;
    }}
    .action-container {{
        background: white; border-radius: 14px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,.03); border: 1px solid #E2E8F0;
        margin-bottom: 25px;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# SYSTEM DATABASE ENGINE (AUTOMATIC CAPABILITIES)
# ------------------------------------------------------------------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("tenders_v3.db", check_same_thread=False)
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
# SYSTEM BANNER SETUP
# ------------------------------------------------------------------
st.markdown(
    '<div class="banner"><h1>📑 SSS TENDER COMMAND CONTROL STATION</h1>'
    "<p>A TO Z EXECUTIVE LEVEL ADMINISTRATIVE SUITE — PERSISTENT VISUAL CONTROL</p></div>",
    unsafe_allow_html=True,
)

# NAVBAR SYSTEM
PAGES = ["🏠 Home / Overview", "➕ Add Record Entry", "✏️ Edit / Delete Entry", "📊 System Exporter"]

if "page" not in st.session_state:
    st.session_state.page = "🏠 Home / Overview"

def navigate(p):
    st.session_state.page = p

nav_cols = st.columns(4, gap="small")
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
# DYNAMIC TOP CONTROL DECK PANEL (FORM CHANGES HERE)
# ------------------------------------------------------------------
st.markdown('<div class="action-container">', unsafe_allow_html=True)

if page == "🏠 Home / Overview":
    st.info("💡 Welcome to Command Center. Use the Navigation Panel above to register entries or execute live edits. Performance telemetry charts and master databases are continuously rendering below.")

elif page == "➕ Add Record Entry":
    st.subheader("📝 Register New Tender Profile")
    with st.form("master_add_form", clear_on_submit=True):
        a1, a2 = st.columns(2, gap="medium")
        name = a1.text_input("Tender ID Name/Number Code *")
        party = a2.text_input("Issuing Client/Party Name *")
        
        a3, a4, a5 = st.columns(3, gap="medium")
        amount = a3.number_input("Estimated Tender Valuation (INR)", min_value=0.0, step=1000.0)
        due = a4.date_input("Target Submission Deadline", value=date.today() + timedelta(days=15))
        status = a5.selectbox("Initial Management Status", STATUS_OPTIONS)
        
        a6, a7 = st.columns(2, gap="medium")
        submission_type = a6.selectbox("Submission Portal Type", ["Online (E-Procurement)", "Offline/Physical", "Global Tender Enquiry"])
        remarks = a7.text_area("Administrative Remarks / Notes")
        
        save = st.form_submit_button("💾 Commit Record to Database Securely", type="primary")
        if save:
            if name.strip() and party.strip():
                conn.execute(
                    "INSERT INTO tenders (tender_name, party, amount, due_date, status, remarks, submission_type) VALUES (?,?,?,?,?,?,?)",
                    (name.strip(), party.strip(), amount, str(due), status, remarks, submission_type),
                )
                conn.commit()
                st.success("🎉 Advanced Tender Profile mapped successfully into Core System Data storage.")
                st.rerun()
            else:
                st.error("❌ Process Halting: Please check that Tender Nomenclature and Party details are not empty.")

elif page == "✏️ Edit / Delete Entry":
    st.subheader("✏️ Live Database Record Manipulator & Destructor")
    if df.empty:
        st.warning("Database contains no modification files.")
    else:
        rec_choices = {int(r.id): f"Record Reference #{int(r.id)} ➡️ {r.tender_name} [{r.party}]" for r in df.itertuples()}
        sel = st.selectbox("Choose Target Profile ID to Update/Remove", list(rec_choices.keys()), format_func=lambda i: rec_choices[i])
        
        rec = df[df["id"] == sel].iloc[0]
        with st.form("live_edit_matrix"):
            e1, e2 = st.columns(2, gap="medium")
            e_name = e1.text_input("Edit Nomenclature", value=str(rec["tender_name"]))
            e_party = e2.text_input("Edit Party Group", value=str(rec["party"]))
            
            e3, e4, e5 = st.columns(3, gap="medium")
            e_amount = e3.number_input("Refine Worth", min_value=0.0, value=float(rec["amount"] or 0))
