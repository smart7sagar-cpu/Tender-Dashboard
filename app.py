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
    page_title="Tender Dashboard - SSS",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="collapsed",
)

NAVY = "#14284B"
BLUE = "#2F5FB3"
LIGHT_BLUE = "#4472C4"
GREEN = "#1E9E6A"
RED = "#D64545"
AMBER = "#E8A317"
BG = "#F3F6FB"
CURRENCY = "₹"

# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------
st.markdown(
    f"""
<style>
    [data-testid="stSidebar"], [data-testid="collapsedControl"] {{display: none;}}
    header[data-testid="stHeader"] {{background: transparent;}}
    .stApp {{background: {BG};}}
    .block-container {{padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1300px;}}

    /* Title banner */
    .banner {{
        background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 100%);
        color: white; text-align: center; padding: 18px 10px;
        border-radius: 12px; box-shadow: 0 4px 14px rgba(20,40,75,.25);
        margin-bottom: 18px;
    }}
    .banner h1 {{margin: 0; font-size: 1.9rem; letter-spacing: 2px; font-weight: 700; color: white;}}
    .banner p {{margin: 4px 0 0 0; font-size: .85rem; opacity: .85; letter-spacing: 1px;}}

    /* Navigation buttons */
    div.stButton > button {{
        width: 100%; height: 52px; border-radius: 10px; font-weight: 700;
        letter-spacing: .5px; border: 1px solid {BLUE}; transition: all .2s;
    }}
    div.stButton > button[kind="secondary"],
    div.stButton > button[data-testid="stBaseButton-secondary"] {{
        background: white; color: {BLUE};
    }}
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, {BLUE}, {NAVY}); color: white; border: none;
        box-shadow: 0 4px 10px rgba(47,95,179,.4);
    }}
    div.stButton > button:hover {{transform: translateY(-2px); box-shadow: 0 6px 14px rgba(47,95,179,.3);}}

    /* KPI cards */
    .kpi {{
        background: white; border-radius: 12px; padding: 16px 18px;
        box-shadow: 0 2px 10px rgba(0,0,0,.07); border-left: 6px solid {BLUE};
    }}
    .kpi .label {{font-size: .78rem; color: #6B7A90; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;}}
    .kpi .value {{font-size: 1.7rem; font-weight: 800; color: {NAVY}; margin-top: 4px;}}
    .kpi.green {{border-left-color: {GREEN};}}
    .kpi.red {{border-left-color: {RED};}}
    .kpi.amber {{border-left-color: {AMBER};}}

    .section-title {{
        color: {NAVY}; font-weight: 700; font-size: 1.15rem;
        border-bottom: 3px solid {BLUE}; display: inline-block;
        padding-bottom: 3px; margin: 18px 0 10px 0;
    }}
    .card {{background: white; border-radius: 12px; padding: 14px; box-shadow: 0 2px 10px rgba(0,0,0,.06);}}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------------
@st.cache_resource
def get_conn():
    conn = sqlite3.connect("tenders.db", check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_name TEXT,
            party TEXT,
            amount REAL,
            due_date TEXT,
            status TEXT)"""
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
            lambda r: "✅ Completed"
            if r["status"] == "Completed"
            else ("🔴 Overdue" if r["days_left"] < 0 else ("🟠 Due Soon" if r["days_left"] <= 7 else "🟢 On Track")),
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


TABLE_CONFIG = {
    "id": st.column_config.NumberColumn("ID", width="small"),
    "tender_name": "Tender Name",
    "party": "Party",
    "amount": st.column_config.NumberColumn("Amount", format=f"{CURRENCY}%.2f"),
    "due_date": st.column_config.DateColumn("Due Date", format="DD MMM YYYY"),
    "status": "Status",
    "days_left": st.column_config.NumberColumn("Days Left"),
    "alert": "Alert",
}
TABLE_COLS = ["id", "tender_name", "party", "amount", "due_date", "status", "days_left", "alert"]

# ------------------------------------------------------------------
# HEADER + NAVIGATION
# ------------------------------------------------------------------
st.markdown(
    '<div class="banner"><h1>TENDER DASHBOARD - SSS</h1>'
    "<p>TENDER MANAGEMENT &amp; MONITORING SYSTEM</p></div>",
    unsafe_allow_html=True,
)

PAGES = ["Dashboard", "View Record", "Add Record", "Export & Reminder"]
ICONS = {"Dashboard": "📊", "View Record": "📋", "Add Record": "➕", "Export & Reminder": "🔔"}

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def go(p):
    st.session_state.page = p


nav_cols = st.columns(4, gap="medium")
for col, p in zip(nav_cols, PAGES):
    col.button(
        f"{ICONS[p]}  {p.upper()}",
        key=f"nav_{p}",
        on_click=go,
        args=(p,),
        type="primary" if st.session_state.page == p else "secondary",
        use_container_width=True,
    )

page = st.session_state.page
st.write("")

# ------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------
if page == "Dashboard":
    df = load_df()
    if df.empty:
        st.info("Abhi koi record nahi hai. 'ADD RECORD' se pehla tender add karein.")
    else:
        pending = df[df["status"] == "Pending"]
        completed = df[df["status"] == "Completed"]
        overdue = pending[pending["days_left"] < 0]

        k1, k2, k3, k4, k5 = st.columns(5)
        kpi(k1, "Total Tenders", len(df))
        kpi(k2, "Total Value", money(df["amount"].sum()))
        kpi(k3, "Pending Value", money(pending["amount"].sum()), "amber")
        kpi(k4, "Completed Value", money(completed["amount"].sum()), "green")
        kpi(k5, "Overdue Tenders", len(overdue), "red")

        st.markdown('<div class="section-title">Analytics</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(
                df, names="status", values="amount", hole=0.5,
                color="status", color_discrete_map={"Pending": AMBER, "Completed": GREEN},
                title="Status Breakdown (by Value)",
            )
            fig.update_layout(margin=dict(t=50, b=10, l=10, r=10), paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            by_party = df.groupby(["party", "status"], as_index=False)["amount"].sum()
            fig = px.bar(
                by_party, x="party", y="amount", color="status", barmode="group",
                color_discrete_map={"Pending": AMBER, "Completed": GREEN},
                labels={"amount": "Amount", "party": "Party"},
                title="Value by Party",
            )
            fig.update_layout(margin=dict(t=50, b=10, l=10, r=10), paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

        monthly = df.dropna(subset=["due_date"]).copy()
        if not monthly.empty:
            monthly["month"] = monthly["due_date"].dt.to_period("M").astype(str)
            m = monthly.groupby("month", as_index=False)["amount"].sum()
            fig = px.area(m, x="month", y="amount", markers=True, title="Monthly Due Value Trend",
                          color_discrete_sequence=[BLUE])
            fig.update_layout(margin=dict(t=50, b=10, l=10, r=10), paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-title">Recent Tenders</div>', unsafe_allow_html=True)
        st.dataframe(
            df.head(10)[TABLE_COLS], column_config=TABLE_CONFIG,
            hide_index=True, use_container_width=True,
        )

# ------------------------------------------------------------------
# VIEW RECORD
# ------------------------------------------------------------------
elif page == "View Record":
    st.markdown('<div class="section-title">All Tender Records</div>', unsafe_allow_html=True)
    df = load_df()
    if df.empty:
        st.info("Koi record nahi mila.")
    else:
        f1, f2, f3, f4 = st.columns([2, 2, 2, 2])
        search = f1.text_input("🔍 Search Tender", placeholder="Tender name likhein...")
        party_f = f2.selectbox("Party", ["All"] + sorted(df["party"].dropna().unique().tolist()))
        status_f = f3.selectbox("Status", ["All", "Pending", "Completed"])
        alert_f = f4.selectbox("Alert", ["All", "🔴 Overdue", "🟠 Due Soon", "🟢 On Track", "✅ Completed"])

        fdf = df.copy()
        if search:
            fdf = fdf[fdf["tender_name"].str.contains(search, case=False, na=False)]
        if party_f != "All":
            fdf = fdf[fdf["party"] == party_f]
        if status_f != "All":
            fdf = fdf[fdf["status"] == status_f]
        if alert_f != "All":
            fdf = fdf[fdf["alert"] == alert_f]

        st.caption(f"{len(fdf)} record(s) | Total value: {money(fdf['amount'].sum())}")
        st.dataframe(fdf[TABLE_COLS], column_config=TABLE_CONFIG, hide_index=True, use_container_width=True)

        st.markdown('<div class="section-title">Edit / Delete Record</div>', unsafe_allow_html=True)
        names = {int(r.id): f"#{int(r.id)} - {r.tender_name} ({r.party})" for r in df.itertuples()}
        sel = st.selectbox("Record select karein", list(names.keys()), format_func=lambda i: names[i])
        rec = df[df["id"] == sel].iloc[0]

        with st.form("edit_form"):
            e1, e2 = st.columns(2)
            name = e1.text_input("Tender Name", value=rec["tender_name"])
            party = e2.text_input("Party Name", value=rec["party"])
            e3, e4, e5 = st.columns(3)
            amount = e3.number_input("Amount", min_value=0.0, value=float(rec["amount"] or 0), step=500.0)
            due = e4.date_input(
                "Due Date",
                value=rec["due_date"].date() if pd.notna(rec["due_date"]) else date.today(),
            )
            status = e5.selectbox("Status", ["Pending", "Completed"],
                                  index=0 if rec["status"] == "Pending" else 1)
            b1, b2, _ = st.columns([1, 1, 3])
            upd = b1.form_submit_button("🔄 Update", type="primary")
            dele = b2.form_submit_button("🗑️ Delete")

            if upd:
                conn.execute(
                    "UPDATE tenders SET tender_name=?, party=?, amount=?, due_date=?, status=? WHERE id=?",
                    (name, party, amount, str(due), status, int(sel)),
                )
                conn.commit()
                st.success("✅ Record update ho gaya.")
                st.rerun()
            if dele:
                conn.execute("DELETE FROM tenders WHERE id=?", (int(sel),))
                conn.commit()
                st.warning(f"Record #{sel} delete ho gaya.")
                st.rerun()

# ------------------------------------------------------------------
# ADD RECORD
# ------------------------------------------------------------------
elif page == "Add Record":
    st.markdown('<div class="section-title">Add New Tender</div>', unsafe_allow_html=True)
    with st.form("add_form", clear_on_submit=True):
        a1, a2 = st.columns(2)
        name = a1.text_input("Tender Name *")
        party = a2.text_input("Party Name *")
        a3, a4, a5 = st.columns(3)
        amount = a3.number_input("Amount", min_value=0.0, step=500.0)
        due = a4.date_input("Due Date", value=date.today() + timedelta(days=30))
        status = a5.selectbox("Status", ["Pending", "Completed"])
        save = st.form_submit_button("💾 Save Record", type="primary")

        if save:
            if name.strip() and party.strip():
                conn.execute(
                    "INSERT INTO tenders (tender_name, party, amount, due_date, status) VALUES (?,?,?,?,?)",
                    (name.strip(), party.strip(), amount, str(due), status),
                )
                conn.commit()
                st.success("✅ Record save ho gaya!")
            else:
                st.error("❌ Tender Name aur Party Name dono bharna zaroori hai.")

    st.markdown('<div class="section-title">Last 5 Entries</div>', unsafe_allow_html=True)
    df = load_df()
    if not df.empty:
        st.dataframe(df.head(5)[TABLE_COLS], column_config=TABLE_CONFIG,
                     hide_index=True, use_container_width=True)

# ------------------------------------------------------------------
# EXPORT & REMINDER
# ------------------------------------------------------------------
elif page == "Export & Reminder":
    df = load_df()
    if df.empty:
        st.info("Export ya reminder ke liye koi data nahi hai.")
    else:
        st.markdown('<div class="section-title">Reminders</div>', unsafe_allow_html=True)
        days = st.slider("Agle kitne din ke tenders dikhane hain?", 1, 60, 7)
        pending = df[df["status"] == "Pending"]
        overdue = pending[pending["days_left"] < 0]
        upcoming = pending[(pending["days_left"] >= 0) & (pending["days_left"] <= days)]

        r1, r2 = st.columns(2)
        kpi(r1, "Overdue Tenders", len(overdue), "red")
        kpi(r2, f"Due in next {days} days", len(upcoming), "amber")
        st.write("")

        if not overdue.empty:
            st.error(f"🔴 {len(overdue)} tender(s) ki due date nikal chuki hai!")
            st.dataframe(overdue[TABLE_COLS], column_config=TABLE_CONFIG,
                         hide_index=True, use_container_width=True)
        if not upcoming.empty:
            st.warning(f"🟠 {len(upcoming)} tender(s) {days} din ke andar due hain.")
            st.dataframe(upcoming[TABLE_COLS], column_config=TABLE_CONFIG,
                         hide_index=True, use_container_width=True)
        if overdue.empty and upcoming.empty:
            st.success("🟢 Sab kuch on track hai, koi urgent reminder nahi.")

        st.markdown('<div class="section-title">Export Data</div>', unsafe_allow_html=True)
        export_df = df[["id", "tender_name", "party", "amount", "due_date", "status"]].copy()
        export_df["due_date"] = export_df["due_date"].dt.strftime("%Y-%m-%d")
        stamp = datetime.today().strftime("%Y%m%d")

        d1, d2 = st.columns(2)
        d1.download_button(
            "📥 Download CSV",
            export_df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"tenders_{stamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                export_df.to_excel(xw, index=False, sheet_name="Tenders")
            d2.download_button(
                "📥 Download Excel",
                buf.getvalue(),
                file_name=f"tenders_{stamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception:
            d2.caption("Excel export ke liye requirements.txt me `openpyxl` add karein.")

# ------------------------------------------------------------------
st.markdown(
    f"<p style='text-align:center;color:#8A97AB;font-size:.8rem;margin-top:30px;'>"
    f"© SSS Tender Management • {datetime.today().strftime('%d %b %Y')}</p>",
    unsafe_allow_html=True,
)
