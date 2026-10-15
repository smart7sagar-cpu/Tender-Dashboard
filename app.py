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
</style>
""",
    unsafe_allow_html=True,
)

# ==================================================================
# DATABASE (auto-migrates old table to the new columns)
# ==================================================================
DB_COLS = {
    "tender_no": "TEXT", "tender_name": "TEXT", "department": "TEXT", "party": "TEXT",
    "category": "TEXT", "location": "TEXT", "participation": "TEXT", "not_part_reason": "TEXT",
    "estimated_cost": "REAL", "amount": "REAL", "emd_amount": "REAL", "emd_status": "TEXT",
    "tender_fee": "REAL", "publish_date": "TEXT", "due_date": "TEXT", "opening_date": "TEXT",
    "result": "TEXT", "status": "TEXT", "work_order_no": "TEXT", "remarks": "TEXT",
    "work_description": "TEXT", "no_of_awardees": "INTEGER",
    "created_at": "TEXT",
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
    conn.commit()
    return conn


conn = get_conn()


def fy_of(d):
    if pd.isna(d):
        return "Unknown"
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{str(y + 1)[2:]}"


def alert_of(r):
    if r["participation"] == "Not Participated":
        return "⚪ Not Participated"
    if r["status"] == "Completed":
        return "✅ Completed"
    if r["result"] in ("Lost", "Cancelled"):
        return "⚫ Closed"
    if pd.isna(r["days_left"]):
        return "⚪ No Date"
    if r["days_left"] < 0:
        return "🔴 Overdue"
    if r["days_left"] <= 7:
        return "🟠 Due Soon"
    return "🟢 On Track"


def load_df() -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM tenders ORDER BY id DESC", conn)
    if df.empty:
        return df
    for c in TEXT_COLS:
        df[c] = df[c].fillna("")
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["no_of_awardees"] = pd.to_numeric(df["no_of_awardees"], errors="coerce").fillna(0).astype(int)
    df["participation"] = df["participation"].replace("", "Participated")
    df["result"] = df["result"].replace("", "Pending")
    df["status"] = df["status"].replace("", "Pending")
    df["emd_status"] = df["emd_status"].replace("", "Not Applicable")
    for c in DATE_COLS:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["days_left"] = (df["due_date"] - pd.Timestamp(date.today())).dt.days
    df["fy"] = df["due_date"].apply(fy_of)
    df["month"] = df["due_date"].dt.strftime("%Y-%m")
    df["alert"] = df.apply(alert_of, axis=1)
    return df


def bump():
    st.session_state["ver"] = st.session_state.get("ver", 0) + 1


def insert_record(v: dict):
    cols = list(v)
    conn.execute(
        f"INSERT INTO tenders ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", list(v.values())
    )
    conn.commit()
    bump()


def update_record(rid: int, v: dict):
    sets = ",".join(f"{c}=?" for c in v)
    conn.execute(f"UPDATE tenders SET {sets} WHERE id=?", list(v.values()) + [rid])
    conn.commit()
    bump()


# ==================================================================
# HELPERS
# ==================================================================
def inr(x: float) -> str:
    x = float(x or 0)
    if abs(x) >= 1e7:
        return f"{CUR}{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"{CUR}{x / 1e5:.2f} L"
    return f"{CUR}{x:,.0f}"


def kpi(col, label, value, cls=""):
    col.markdown(
        f'<div class="kpi {cls}"><div class="label">{label}</div><div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


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
    if value:
        g = df.groupby(col, as_index=False)[value].sum()
        vals = value
    else:
        g = df.groupby(col).size().reset_index(name="count")
        vals = "count"
    fig = px.pie(g, names=col, values=vals, hole=0.58, color=col, color_discrete_map=cmap)
    fig.update_traces(textinfo="percent", textfont_size=13)
    total = g[vals].sum()
    fig.add_annotation(text=f"<b>{inr(total) if value else int(total)}</b>", showarrow=False,
                       font=dict(size=20, color=NAVY))
    _s(st, "plotly_chart", style(fig, text, 340), use_container_width=True, key=key)


TABLE_COLS = ["id", "tender_no", "tender_name", "work_description", "department", "party", "category",
              "participation", "amount", "no_of_awardees", "due_date", "result", "status", "days_left", "alert"]
ALL_COLS = ["id", "tender_no", "tender_name", "work_description", "department", "party", "category", "location",
            "participation", "not_part_reason", "estimated_cost", "amount", "emd_amount", "emd_status",
            "tender_fee", "publish_date", "due_date", "opening_date", "result", "status",
            "work_order_no", "no_of_awardees", "remarks", "days_left", "alert", "fy"]
CFG = {
    "id": st.column_config.NumberColumn("ID", width="small"),
    "tender_no": "Tender No.", "tender_name": "Tender Name", "work_description": "Work Description",
    "no_of_awardees": st.column_config.NumberColumn("Awardees", format="%d"), "department": "Department",
    "party": "Party", "category": "Category", "location": "Location",
    "participation": "Participation", "not_part_reason": "Reason (Not Participated)",
    "estimated_cost": st.column_config.NumberColumn("Estimated Cost", format=f"{CUR}%.2f"),
    "amount": st.column_config.NumberColumn("Quoted Amount", format=f"{CUR}%.2f"),
    "emd_amount": st.column_config.NumberColumn("EMD", format=f"{CUR}%.2f"),
    "emd_status": "EMD Status",
    "tender_fee": st.column_config.NumberColumn("Tender Fee", format=f"{CUR}%.2f"),
    "publish_date": st.column_config.DateColumn("Publish Date", format="DD MMM YYYY"),
    "due_date": st.column_config.DateColumn("Submission Date", format="DD MMM YYYY"),
    "opening_date": st.column_config.DateColumn("Opening Date", format="DD MMM YYYY"),
    "result": "Result", "status": "Status", "work_order_no": "Work Order No.", "remarks": "Remarks",
    "days_left": st.column_config.NumberColumn("Days Left"), "alert": "Alert", "fy": "FY",
}


def show(df, cols=None, height=None):
    kw = {"height": height} if height else {}
    _s(st, "dataframe", df[cols or TABLE_COLS], column_config=CFG, hide_index=True, **kw)


def opts(base, current):
    return base + [current] if current and current not in base else base


# ==================================================================
# RECORD FORM (shared by Add and Edit)
# ==================================================================
FIELD_KEYS = ["no", "name", "dept", "party", "cat", "loc", "wdesc", "est", "amt", "emd", "emds", "fee",
              "pub", "due", "open", "part", "res", "stat", "wo", "awd", "reason", "rem"]


def _init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default


def _pick(val, options, default=None):
    return val if val in options else (default if default is not None else options[0])


def record_form(prefix, rec=None, on_last=None, last_args=()):
    """Normal widgets (st.form nahi) -> beech ke field me Enter dabane se save nahi hota."""
    P = lambda n: f"{prefix}_{n}"

    def g(k, d=""):
        if rec is not None and k in rec.index and pd.notna(rec[k]) and rec[k] != "":
            return str(rec[k])
        return d

    def gn(k):
        return float(rec[k]) if rec is not None and k in rec.index and pd.notna(rec[k]) else 0.0

    def gd(k, default):
        return rec[k].date() if rec is not None and k in rec.index and pd.notna(rec[k]) else default

    awd = 1
    if rec is not None and "no_of_awardees" in rec.index and pd.notna(rec["no_of_awardees"]) and int(rec["no_of_awardees"]) >= 1:
        awd = int(rec["no_of_awardees"])

    cats = opts(CATEGORIES, g("category"))
    emds = opts(EMD_STATUS, g("emd_status"))
    defaults = {
        "no": g("tender_no"), "name": g("tender_name"), "dept": g("department"), "party": g("party"),
        "cat": _pick(g("category"), cats), "loc": g("location"), "wdesc": g("work_description"),
        "est": gn("estimated_cost"), "amt": gn("amount"), "emd": gn("emd_amount"),
        "emds": _pick(g("emd_status"), emds), "fee": gn("tender_fee"),
        "pub": gd("publish_date", date.today()),
        "due": gd("due_date", date.today() + timedelta(days=15)),
        "open": gd("opening_date", date.today() + timedelta(days=16)),
        "part": _pick(g("participation", "Participated"), PARTICIPATION),
        "res": _pick(g("result", "Pending"), RESULTS), "stat": _pick(g("status", "Pending"), STATUSES),
        "wo": g("work_order_no"), "awd": awd, "reason": g("not_part_reason"), "rem": g("remarks"),
    }
    for k, v in defaults.items():
        _init(P(k), v)

    st.markdown("**📌 Basic Details**")
    c1, c2, c3 = st.columns(3)
    c1.text_input("Tender No.", key=P("no"))
    c2.text_input("Tender Name *", key=P("name"))
    c3.text_input("Department / Organization", key=P("dept"))
    c4, c5, c6 = st.columns(3)
    c4.text_input("Party Name *", key=P("party"))
    c5.selectbox("Category", cats, key=P("cat"))
    c6.text_input("Location", key=P("loc"))
    st.text_area("📝 Work Description (kaam ka vivaran)", key=P("wdesc"), height=90)

    st.markdown("**💰 Financials**")
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.number_input("Estimated Cost", min_value=0.0, step=1000.0, key=P("est"))
    f2.number_input("Quoted Amount", min_value=0.0, step=1000.0, key=P("amt"))
    f3.number_input("EMD Amount", min_value=0.0, step=500.0, key=P("emd"))
    f4.selectbox("EMD Status", emds, key=P("emds"))
    f5.number_input("Tender Fee", min_value=0.0, step=100.0, key=P("fee"))

    st.markdown("**📅 Dates**")
    d1, d2, d3 = st.columns(3)
    d1.date_input("Publish Date", key=P("pub"))
    d2.date_input("Submission (Due) Date", key=P("due"))
    d3.date_input("Opening Date", key=P("open"))

    st.markdown("**🏁 Participation & Result**")
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.selectbox("Participation", PARTICIPATION, key=P("part"))
    s2.selectbox("Result", RESULTS, key=P("res"))
    s3.selectbox("Status", STATUSES, key=P("stat"))
    s4.text_input("Work Order No.", key=P("wo"))
    s5.number_input("Tender kitne logo ko milega (No. of Awardees)", min_value=1, step=1, key=P("awd"))
    st.text_input("Reason (agar Not Participated hai)", key=P("reason"))
    if on_last:
        st.text_input("Remarks  ⬅ (LAST FIELD)", key=P("rem"), on_change=on_last, args=last_args)
    else:
        st.text_input("Remarks  ⬅ (LAST FIELD)", key=P("rem"))


def collect(prefix):
    """Session state se values padhta hai (keys na mile to safe defaults)."""
    s = st.session_state
    G = lambda n, d="": s.get(f"{prefix}_{n}", d)
    today = date.today()
    return {
        "tender_no": str(G("no")).strip(), "tender_name": str(G("name")).strip(),
        "department": str(G("dept")).strip(), "party": str(G("party")).strip(),
        "category": G("cat", CATEGORIES[0]), "location": str(G("loc")).strip(),
        "work_description": str(G("wdesc")).strip(), "participation": G("part", PARTICIPATION[0]),
        "not_part_reason": str(G("reason")).strip(), "estimated_cost": float(G("est", 0.0)),
        "amount": float(G("amt", 0.0)), "emd_amount": float(G("emd", 0.0)), "emd_status": G("emds", EMD_STATUS[0]),
        "tender_fee": float(G("fee", 0.0)), "publish_date": str(G("pub", today)),
        "due_date": str(G("due", today + timedelta(days=15))),
        "opening_date": str(G("open", today + timedelta(days=16))), "result": G("res", RESULTS[0]),
        "status": G("stat", STATUSES[0]), "work_order_no": str(G("wo")).strip(),
        "no_of_awardees": int(G("awd", 1)), "remarks": str(G("rem")).strip(),
    }


# ---------- save / update / delete callbacks ----------
def save_new():
    s = st.session_state
    vals = collect("add")
    if not vals["tender_name"] and not vals["party"] and time.time() - s.get("ts_add", 0) < 8:
        return  # abhi-abhi save hua hai (double trigger se bachav)
    if vals["tender_name"] and vals["party"]:
        vals["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_record(vals)
        for k in FIELD_KEYS:
            s.pop(f"add_{k}", None)
        s["ts_add"] = time.time()
        s["msg_add"] = ("ok", "✅ Record save ho gaya! Naya record bhar sakte hain.")
    else:
        s["msg_add"] = ("err", "❌ Tender Name aur Party Name dono bharna zaroori hai.")


def save_new_enter():
    if st.session_state.get("enter_save", True):
        save_new()


def update_cb(rid, prefix):
    s = st.session_state
    vals = collect(prefix)
    if vals["tender_name"] and vals["party"]:
        update_record(int(rid), vals)
        s["msg_edit"] = ("ok", f"✅ Record #{rid} update ho gaya.")
    else:
        s["msg_edit"] = ("err", "❌ Tender Name aur Party Name zaroori hai.")


def update_enter(rid, prefix):
    if st.session_state.get("enter_save", True):
        update_cb(rid, prefix)


def delete_cb(rid, prefix):
    s = st.session_state
    if s.get(f"{prefix}_cf"):
        conn.execute("DELETE FROM tenders WHERE id=?", (int(rid),))
        conn.commit()
        bump()
        s["msg_edit"] = ("ok", f"🗑️ Record #{rid} delete ho gaya.")
    else:
        s["msg_edit"] = ("err", "Delete karne ke liye 'Delete confirm' tick karein.")


# ==================================================================
# RECORD MANAGER (filters + table + edit/delete)
# ==================================================================
def record_manager(df, key):
    if df.empty:
        st.info("Is section me abhi koi record nahi hai.")
        return
    f1, f2, f3, f4, f5 = st.columns([2.2, 1.6, 1.4, 1.4, 1.4])
    q = f1.text_input("🔍 Search (No./Name/Work/Party/Dept)", key=f"{key}_q")
    party_f = f2.selectbox("Party", ["All"] + sorted([p for p in df["party"].unique() if p]), key=f"{key}_p")
    cat_f = f3.selectbox("Category", ["All"] + sorted([p for p in df["category"].unique() if p]), key=f"{key}_c")
    res_f = f4.selectbox("Result", ["All"] + RESULTS, key=f"{key}_r")
    al_f = f5.selectbox("Alert", ["All"] + sorted(df["alert"].unique()), key=f"{key}_a")

    fdf = df.copy()
    if q:
        m = (fdf["tender_name"].str.contains(q, case=False, na=False)
             | fdf["party"].str.contains(q, case=False, na=False)
             | fdf["tender_no"].str.contains(q, case=False, na=False)
             | fdf["department"].str.contains(q, case=False, na=False)
             | fdf["work_description"].str.contains(q, case=False, na=False))
        fdf = fdf[m]
    if party_f != "All":
        fdf = fdf[fdf["party"] == party_f]
    if cat_f != "All":
        fdf = fdf[fdf["category"] == cat_f]
    if res_f != "All":
        fdf = fdf[fdf["result"] == res_f]
    if al_f != "All":
        fdf = fdf[fdf["alert"] == al_f]

    full = st.checkbox("Saare columns dikhao", key=f"{key}_full")
    st.caption(f"{len(fdf)} record(s)  |  Quoted value: {inr(fdf['amount'].sum())}")
    show(fdf, ALL_COLS if full else TABLE_COLS, height=380)

    if fdf.empty:
        return
    title("✏️ Edit / Delete Record")
    st.checkbox("⌨️ Last field (Remarks) me Enter dabane par update karo", value=True, key="enter_save")
    names = {int(r.id): f"#{int(r.id)} | {r.tender_no} | {r.tender_name} | {r.party}" for r in fdf.itertuples()}
    sel = st.selectbox("Record select karein", list(names), format_func=lambda i: names[i], key=f"{key}_sel")
    rec = fdf[fdf["id"] == sel].iloc[0]
    prefix = f"{key}_e{sel}_v{st.session_state.get('ver', 0)}"
    record_form(prefix, rec, on_last=update_enter, last_args=(int(sel), prefix))
    msg = st.session_state.get("msg_edit")
    if msg:
        (st.success if msg[0] == "ok" else st.error)(msg[1])
    b1, b2, b3 = st.columns([1, 1, 2])
    b1.button("🔄 Update Record", type="primary", key=f"{prefix}_upd", on_click=update_cb, args=(int(sel), prefix))
    b2.button("🗑️ Delete Record", key=f"{prefix}_del", on_click=delete_cb, args=(int(sel), prefix))
    b3.checkbox("Delete confirm karta hu", key=f"{prefix}_cf")


def quick_edit(df, col, options, key):
    base = df[["id", "tender_no", "tender_name", "party", col]].reset_index(drop=True)
    edited = _s(st, "data_editor", 
        base, key=key, hide_index=True, use_container_width=True,
        disabled=["id", "tender_no", "tender_name", "party"],
        column_config={col: st.column_config.SelectboxColumn(col.replace("_", " ").title(), options=options,
                                                              required=True)},
    )
    if st.button("💾 Save Changes", key=f"{key}_save", type="primary"):
        n = 0
        for i, row in edited.iterrows():
            if row[col] != base.loc[i, col]:
                conn.execute(f"UPDATE tenders SET {col}=? WHERE id=?", (row[col], int(row["id"])))
                n += 1
        conn.commit()
        bump()
        st.success(f"✅ {n} record update hue.")
        do_rerun()


def summary(df, by):
    d = df.copy()
    d[by] = d[by].replace("", "Unknown")
    g = d.groupby(by).agg(
        Total=("id", "count"),
        Participated=("participation", lambda s: (s == "Participated").sum()),
        Not_Participated=("participation", lambda s: (s == "Not Participated").sum()),
        Won=("result", lambda s: (s == "Won").sum()),
        Lost=("result", lambda s: (s == "Lost").sum()),
        Quoted_Value=("amount", "sum"),
    ).reset_index()
    won_val = d[d["result"] == "Won"].groupby(by)["amount"].sum()
    g["Won_Value"] = g[by].map(won_val).fillna(0)
    dec = g["Won"] + g["Lost"]
    g["Win_%"] = ((g["Won"] / dec * 100).where(dec > 0, 0)).round(1)
    return g


# ==================================================================
# HEADER + NAVIGATION
# ==================================================================
st.markdown(
    f'<div class="topbar"><span>OFFICIAL TENDER MANAGEMENT PORTAL</span>'
    f'<span>{datetime.today().strftime("%A, %d %B %Y")}</span></div>'
    '<div class="banner"><h1>TENDER DASHBOARD - SSS</h1>'
    "<p>TENDER PARTICIPATION • RESULT • EMD • REPORTING SYSTEM</p></div>",
    unsafe_allow_html=True,
)

PAGES = ["Dashboard", "Add Record", "View Records", "Participated", "Not Participated",
         "Results", "EMD Tracker", "Reports", "Export & Reminder", "Backup & Import"]
ICONS = {"Dashboard": "📊", "Add Record": "➕", "View Records": "📋", "Participated": "✅",
         "Not Participated": "🚫", "Results": "🏆", "EMD Tracker": "💳", "Reports": "📈",
         "Export & Reminder": "🔔", "Backup & Import": "💾"}

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def goto_page(p):
    st.session_state.page = p
    st.session_state.pop("msg_add", None)
    st.session_state.pop("msg_edit", None)


for row in (PAGES[:5], PAGES[5:]):
    cols = st.columns(5, gap="small")
    for col, p in zip(cols, row):
        _s(col, "button", f"{ICONS[p]}  {p.upper()}", key=f"nav_{p}", on_click=goto_page, args=(p,),
                   type="primary" if st.session_state.page == p else "secondary",
                   use_container_width=True)

page = st.session_state.page
ALL = load_df()
EMPTY_MSG = "Abhi koi record nahi hai. 'ADD RECORD' se pehla tender add karein."

# ==================================================================
# DASHBOARD
# ==================================================================
def render_page():
    if page == "Dashboard":
        if ALL.empty:
            st.info(EMPTY_MSG)
        else:
            f1, f2, f3 = st.columns(3)
            fy = f1.selectbox("Financial Year", ["All"] + sorted(ALL["fy"].unique(), reverse=True))
            cat = f2.selectbox("Category", ["All"] + sorted([c for c in ALL["category"].unique() if c]))
            pty = f3.selectbox("Party", ["All"] + sorted([c for c in ALL["party"].unique() if c]))
            d = ALL.copy()
            if fy != "All":
                d = d[d["fy"] == fy]
            if cat != "All":
                d = d[d["category"] == cat]
            if pty != "All":
                d = d[d["party"] == pty]

            if d.empty:
                st.warning("Selected filter me koi record nahi.")
            else:
                part = d[d["participation"] == "Participated"]
                notp = d[d["participation"] == "Not Participated"]
                won = part[part["result"] == "Won"]
                lost = part[part["result"] == "Lost"]
                pend = part[part["result"] == "Pending"]
                decided = len(won) + len(lost)
                win_rate = len(won) / decided * 100 if decided else 0.0
                overdue = d[d["alert"] == "🔴 Overdue"]
                due_soon = d[d["alert"] == "🟠 Due Soon"]

                title("Key Indicators")
                a = st.columns(6)
                kpi(a[0], "Total Tenders", len(d))
                kpi(a[1], "Participated", len(part), "teal")
                kpi(a[2], "Not Participated", len(notp), "grey")
                kpi(a[3], "Won", len(won), "green")
                kpi(a[4], "Lost", len(lost), "red")
                kpi(a[5], "Win Rate", f"{win_rate:.1f}%", "purple")
                st.write("")
                b = st.columns(6)
                kpi(b[0], "Total Quoted Value", inr(part["amount"].sum()))
                kpi(b[1], "Won Value", inr(won["amount"].sum()), "green")
                kpi(b[2], "Result Pending Value", inr(pend["amount"].sum()), "amber")
                kpi(b[3], "EMD Locked (Paid)", inr(part[part["emd_status"] == "Paid"]["emd_amount"].sum()), "purple")
                kpi(b[4], "Overdue", len(overdue), "red")
                kpi(b[5], "Due in 7 Days", len(due_soon), "amber")

                title("Participation & Results")
                c1, c2, c3 = st.columns(3)
                with c1:
                    donut(d, "participation", "Participation Split", CMAP_PART, "dn_part")
                with c2:
                    donut(part, "result", "Result Status (Participated)", CMAP_RESULT, "dn_res")
                with c3:
                    gauge = go.Figure(go.Indicator(
                        mode="gauge+number", value=win_rate, number={"suffix": "%"},
                        gauge={"axis": {"range": [0, 100]}, "bar": {"color": GREEN},
                               "steps": [{"range": [0, 33], "color": "#F8D7D7"},
                                         {"range": [33, 66], "color": "#FBEBC8"},
                                         {"range": [66, 100], "color": "#D5F0E4"}]}))
                    _s(st, "plotly_chart", style(gauge, "Win Rate (Won ÷ Decided)", 340), use_container_width=True, key="gauge")

                c1, c2 = st.columns(2)
                with c1:
                    fdf_ = pd.DataFrame({"Stage": ["Total Tenders", "Participated", "Result Declared", "Won"],
                                         "Count": [len(d), len(part), decided, len(won)]})
                    fun = px.bar(fdf_, x="Count", y="Stage", orientation="h", color="Stage", text="Count",
                                 color_discrete_sequence=[NAVY, BLUE, TEAL, GREEN])
                    fun.update_layout(showlegend=False, yaxis=dict(autorange="reversed", title=""))
                    _s(st, "plotly_chart", style(fun, "Tender Funnel", 360), key="funnel")
                with c2:
                    m = d.dropna(subset=["month"]).groupby(["month", "participation"]).size().reset_index(name="count")
                    if m.empty:
                        st.info("Monthly trend ke liye dates chahiye.")
                    else:
                        fig = px.bar(m, x="month", y="count", color="participation", barmode="stack",
                                     color_discrete_map=CMAP_PART, labels={"month": "Month", "count": "Tenders"})
                        _s(st, "plotly_chart", style(fig, "Monthly Tenders (by Submission Date)", 360),
                                        use_container_width=True, key="monthly")

                title("Financial Analysis")
                c1, c2 = st.columns(2)
                with c1:
                    tp = part.groupby("party", as_index=False)["amount"].sum().sort_values("amount").tail(10)
                    if tp.empty or tp["amount"].sum() == 0:
                        st.info("Party-wise value ke liye Quoted Amount bharein.")
                    else:
                        fig = px.bar(tp, x="amount", y="party", orientation="h", color="amount",
                                     color_continuous_scale=["#BBD0F2", BLUE, NAVY], labels={"amount": "Quoted Amount", "party": ""})
                        fig.update_coloraxes(showscale=False)
                        _s(st, "plotly_chart", style(fig, "Top 10 Parties by Quoted Value", 380),
                                        use_container_width=True, key="topparty")
                with c2:
                    tm = d[d["amount"] > 0].copy()
                    if tm.empty:
                        st.info("Treemap ke liye Quoted Amount bharein.")
                    else:
                        tm["department"] = tm["department"].replace("", "Unknown")
                        tm["category"] = tm["category"].replace("", "Unknown")
                        tm["party"] = tm["party"].replace("", "Unknown")
                        tm["root"] = "All"
                        fig = px.treemap(tm, path=["root", "category", "department", "party"],
                                         values="amount", color_discrete_sequence=PALETTE)
                        _s(st, "plotly_chart", style(fig, "Value Map: Category → Department → Party", 380),
                                        use_container_width=True, key="treemap")

                c1, c2, c3 = st.columns(3)
                with c1:
                    donut(part[part["emd_amount"] > 0], "emd_status", "EMD by Amount", CMAP_EMD, "dn_emd", "emd_amount")
                with c2:
                    donut(d, "status", "Work Status", CMAP_STATUS, "dn_stat")
                with c3:
                    comp = won.copy()
                    comp = comp[(comp["estimated_cost"] > 0) & (comp["amount"] > 0)]
                    if comp.empty:
                        st.info("Estimated vs Quoted chart ke liye Won tenders me dono amount chahiye.")
                    else:
                        comp = comp.head(8)
                        fig = go.Figure()
                        fig.add_bar(x=comp["tender_name"], y=comp["estimated_cost"], name="Estimated", marker_color=GREY)
                        fig.add_bar(x=comp["tender_name"], y=comp["amount"], name="Quoted", marker_color=BLUE)
                        fig.update_layout(barmode="group")
                        _s(st, "plotly_chart", style(fig, "Won: Estimated vs Quoted", 340), use_container_width=True, key="estq")

                c1, c2 = st.columns(2)
                with c1:
                    al = d.groupby("alert").size().reset_index(name="count")
                    fig = px.bar(al, x="alert", y="count", color="alert", labels={"alert": "", "count": "Tenders"},
                                 color_discrete_map={"🔴 Overdue": RED, "🟠 Due Soon": AMBER, "🟢 On Track": GREEN,
                                                     "✅ Completed": TEAL, "⚪ Not Participated": GREY,
                                                     "⚫ Closed": "#555", "⚪ No Date": GREY})
                    fig.update_layout(showlegend=False)
                    _s(st, "plotly_chart", style(fig, "Deadline Alert Summary", 340), use_container_width=True, key="alerts")
                with c2:
                    fyv = d.groupby("fy").agg(Quoted=("amount", "sum")).reset_index()
                    fyw = won.groupby("fy")["amount"].sum().reset_index(name="Won")
                    fyv = fyv.merge(fyw, on="fy", how="left").fillna(0)
                    fig = px.bar(fyv, x="fy", y=["Quoted", "Won"], barmode="group",
                                 color_discrete_sequence=[BLUE, GREEN], labels={"fy": "Financial Year", "value": "Amount"})
                    _s(st, "plotly_chart", style(fig, "Financial Year-wise Value", 340), use_container_width=True, key="fyv")

                title("Quick Tables")
                t1, t2, t3, t4 = st.tabs(["🆕 Recent Tenders", "⏰ Due in next 15 days", "🔴 Overdue", "🚫 Not Participated"])
                with t1:
                    show(d.head(10))
                with t2:
                    up = d[(d["status"] == "Pending") & (d["participation"] == "Participated")
                           & (d["days_left"] >= 0) & (d["days_left"] <= 15)].sort_values("days_left")
                    show(up) if not up.empty else st.success("Agle 15 din me koi deadline nahi.")
                with t3:
                    show(overdue) if not overdue.empty else st.success("Koi overdue tender nahi.")
                with t4:
                    show(notp.head(10)) if not notp.empty else st.info("Koi record nahi.")

    # ==================================================================
    # ADD RECORD
    # ==================================================================
    elif page == "Add Record":
        title("➕ Add New Tender Record")
        st.checkbox("⌨️ Last field (Remarks) me Enter dabane par save karo", value=True, key="enter_save")
        st.caption("ℹ️ Beech ke kisi bhi field me Enter dabane se record save NAHI hoga. "
                   "Save tabhi hoga jab last field (Remarks) me Enter dabayein, ya '💾 Save Record' button dabayein.")
        record_form("add", on_last=save_new_enter)
        st.button("💾 Save Record", type="primary", key="add_save_btn", on_click=save_new)
        msg = st.session_state.get("msg_add")
        if msg:
            (st.success if msg[0] == "ok" else st.error)(msg[1])
        if not ALL.empty:
            title("Last 5 Entries")
            show(ALL.head(5))

    elif page == "View Records":
        title("📋 All Tender Records")
        record_manager(ALL, "all")

    elif page == "Participated":
        title("✅ Participated Tenders")
        if not ALL.empty:
            p = ALL[ALL["participation"] == "Participated"]
            k = st.columns(4)
            kpi(k[0], "Participated", len(p), "teal")
            kpi(k[1], "Quoted Value", inr(p["amount"].sum()))
            kpi(k[2], "Result Pending", len(p[p["result"] == "Pending"]), "amber")
            kpi(k[3], "Won", len(p[p["result"] == "Won"]), "green")
            st.write("")
            record_manager(p, "part")
        else:
            st.info(EMPTY_MSG)

    elif page == "Not Participated":
        title("🚫 Not Participated Tenders")
        if not ALL.empty:
            n = ALL[ALL["participation"] == "Not Participated"]
            k = st.columns(3)
            kpi(k[0], "Not Participated", len(n), "grey")
            kpi(k[1], "Estimated Value Missed", inr(n["estimated_cost"].sum()), "red")
            kpi(k[2], "Unique Parties", n["party"].nunique(), "purple")
            st.write("")
            if not n.empty:
                r = n.assign(reason=n["not_part_reason"].replace("", "Not specified")).groupby("reason").size().reset_index(name="count")
                fig = px.pie(r, names="reason", values="count", hole=0.55, color_discrete_sequence=PALETTE)
                _s(st, "plotly_chart", style(fig, "Reasons for Not Participating", 340), use_container_width=True, key="reasons")
            record_manager(n, "notpart")
        else:
            st.info(EMPTY_MSG)

    # ==================================================================
    # RESULTS
    # ==================================================================
    elif page == "Results":
        title("🏆 Tender Results")
        part = ALL[ALL["participation"] == "Participated"] if not ALL.empty else ALL
        if part.empty:
            st.info("Participated tenders nahi hain.")
        else:
            won, lost = part[part["result"] == "Won"], part[part["result"] == "Lost"]
            pend, canc = part[part["result"] == "Pending"], part[part["result"] == "Cancelled"]
            dec = len(won) + len(lost)
            k = st.columns(5)
            kpi(k[0], "Won", len(won), "green")
            kpi(k[1], "Lost", len(lost), "red")
            kpi(k[2], "Pending", len(pend), "amber")
            kpi(k[3], "Cancelled", len(canc), "grey")
            kpi(k[4], "Win Rate", f"{(len(won) / dec * 100 if dec else 0):.1f}%", "purple")
            st.write("")
            t1, t2, t3, t4 = st.tabs(["🏆 Won", "❌ Lost", "⏳ Pending", "🚫 Cancelled"])
            with t1:
                show(won) if not won.empty else st.info("Koi record nahi.")
            with t2:
                show(lost) if not lost.empty else st.info("Koi record nahi.")
            with t3:
                show(pend) if not pend.empty else st.info("Koi record nahi.")
            with t4:
                show(canc) if not canc.empty else st.info("Koi record nahi.")
            title("⚡ Quick Result Update")
            st.caption("Table me Result badlein aur 'Save Changes' dabayein.")
            quick_edit(part, "result", RESULTS, "qe_result")

    # ==================================================================
    # EMD TRACKER
    # ==================================================================
    elif page == "EMD Tracker":
        title("💳 EMD Tracker")
        part = ALL[(ALL["participation"] == "Participated")] if not ALL.empty else ALL
        if part.empty:
            st.info("Participated tenders nahi hain.")
        else:
            e = part[part["emd_amount"] > 0]
            k = st.columns(5)
            kpi(k[0], "Total EMD", inr(e["emd_amount"].sum()))
            kpi(k[1], "Paid (Locked)", inr(e[e["emd_status"] == "Paid"]["emd_amount"].sum()), "purple")
            kpi(k[2], "Refunded", inr(e[e["emd_status"] == "Refunded"]["emd_amount"].sum()), "green")
            kpi(k[3], "Pending", inr(e[e["emd_status"] == "Pending"]["emd_amount"].sum()), "amber")
            kpi(k[4], "Forfeited", inr(e[e["emd_status"] == "Forfeited"]["emd_amount"].sum()), "red")
            st.write("")
            c1, c2 = st.columns(2)
            with c1:
                donut(e, "emd_status", "EMD by Status (Amount)", CMAP_EMD, "emd_d", "emd_amount")
            with c2:
                if not e.empty:
                    g = e.groupby(["party", "emd_status"], as_index=False)["emd_amount"].sum()
                    fig = px.bar(g, x="party", y="emd_amount", color="emd_status", color_discrete_map=CMAP_EMD,
                                 labels={"emd_amount": "EMD", "party": "Party"})
                    _s(st, "plotly_chart", style(fig, "EMD by Party", 340), use_container_width=True, key="emd_b")
            title("⚡ Quick EMD Status Update")
            quick_edit(part, "emd_status", EMD_STATUS, "qe_emd")

    # ==================================================================
    # REPORTS
    # ==================================================================
    elif page == "Reports":
        title("📈 Reports & Analysis")
        if ALL.empty:
            st.info(EMPTY_MSG)
        else:
            tabs = st.tabs(["Party-wise", "Department-wise", "Category-wise", "Financial Year-wise", "Monthly"])
            for tab, (by, label) in zip(tabs, [("party", "Party"), ("department", "Department"),
                                               ("category", "Category"), ("fy", "Financial Year"),
                                               ("month", "Month")]):
                with tab:
                    src = ALL.dropna(subset=["month"]) if by == "month" else ALL
                    g = summary(src, by)
                    _s(st, "dataframe", g.rename(columns={by: label, "Not_Participated": "Not Participated",
                                                   "Quoted_Value": "Quoted Value", "Won_Value": "Won Value"}),
                                 hide_index=True, use_container_width=True)
                    fig = px.bar(g, x=by, y=["Quoted_Value", "Won_Value"], barmode="group",
                                 color_discrete_sequence=[BLUE, GREEN], labels={by: label, "value": "Amount"})
                    _s(st, "plotly_chart", style(fig, f"{label}-wise Quoted vs Won Value", 360),
                                    use_container_width=True, key=f"rep_{by}")

    # ==================================================================
    # EXPORT & REMINDER
    # ==================================================================
    elif page == "Export & Reminder":
        if ALL.empty:
            st.info("Export ya reminder ke liye koi data nahi hai.")
        else:
            title("🔔 Reminders")
            days = st.slider("Agle kitne din ke tenders dikhane hain?", 1, 60, 7)
            act = ALL[(ALL["participation"] == "Participated") & (ALL["status"] == "Pending")
                      & ~ALL["result"].isin(["Lost", "Cancelled"])]
            overdue = act[act["days_left"] < 0]
            upcoming = act[(act["days_left"] >= 0) & (act["days_left"] <= days)].sort_values("days_left")
            k = st.columns(2)
            kpi(k[0], "Overdue Tenders", len(overdue), "red")
            kpi(k[1], f"Due in next {days} days", len(upcoming), "amber")
            st.write("")
            if not overdue.empty:
                st.error(f"🔴 {len(overdue)} tender(s) ki due date nikal chuki hai!")
                show(overdue)
            if not upcoming.empty:
                st.warning(f"🟠 {len(upcoming)} tender(s) {days} din ke andar due hain.")
                show(upcoming)
            if overdue.empty and upcoming.empty:
                st.success("🟢 Koi urgent reminder nahi.")

            title("📤 Export Data")
            exp = ALL[[c for c in ALL_COLS if c not in ("days_left", "alert")]].copy()
            for c in DATE_COLS:
                exp[c] = exp[c].dt.strftime("%Y-%m-%d")
            stamp = datetime.today().strftime("%Y%m%d")
            d1, d2 = st.columns(2)
            _s(d1, "download_button", "📥 Download CSV (All)", exp.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"tenders_{stamp}.csv", mime="text/csv", use_container_width=True)
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                    exp.to_excel(xw, index=False, sheet_name="All Tenders")
                    exp[exp["participation"] == "Participated"].to_excel(xw, index=False, sheet_name="Participated")
                    exp[exp["participation"] == "Not Participated"].to_excel(xw, index=False, sheet_name="Not Participated")
                    exp[exp["result"] == "Won"].to_excel(xw, index=False, sheet_name="Won")
                    exp[exp["result"] == "Lost"].to_excel(xw, index=False, sheet_name="Lost")
                _s(d2, "download_button", "📥 Download Excel (Multi-sheet)", buf.getvalue(), file_name=f"tenders_{stamp}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            except Exception:
                d2.caption("Excel export ke liye requirements.txt me `openpyxl` add karein.")

    # ==================================================================
    # BACKUP & IMPORT
    # ==================================================================
    elif page == "Backup & Import":
        title("💾 Database Backup")
        try:
            with open("tenders.db", "rb") as f:
                _s(st, "download_button", "📥 Download Database Backup (tenders.db)", f.read(),
                                   file_name=f"tenders_backup_{datetime.today().strftime('%Y%m%d')}.db",
                                   use_container_width=True)
        except Exception:
            st.warning("Database file abhi available nahi hai.")
        st.caption("Streamlit Cloud par restart ke baad database reset ho sakta hai, isliye regular backup lete rahein.")

        title("📥 Import from CSV / Excel")
        st.caption("File me ye columns ho sakte hain: " + ", ".join(DB_COLS.keys()) + ". 'tender_name' zaroori hai.")
        up = st.file_uploader("File upload karein", type=["csv", "xlsx"])
        if up:
            try:
                idf = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
                keep = [c for c in idf.columns if c in DB_COLS]
                if "tender_name" not in keep:
                    st.error("'tender_name' column nahi mila.")
                else:
                    idf = idf[keep].copy()
                    for c in DATE_COLS:
                        if c in idf:
                            idf[c] = pd.to_datetime(idf[c], errors="coerce").dt.strftime("%Y-%m-%d")
                    st.write(f"{len(idf)} row(s) import ke liye ready:")
                    _s(st, "dataframe", idf.head(10), hide_index=True, use_container_width=True)
                    if st.button("✅ Import Karein", type="primary"):
                        idf["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        idf.to_sql("tenders", conn, if_exists="append", index=False)
                        conn.commit()
                        bump()
                        st.success("Import complete!")
                        do_rerun()
            except Exception as ex:
                st.error(f"File read nahi ho payi: {ex}")



try:
    render_page()
except Exception as ex:
    st.error(f"⚠️ Page load me problem aayi: {type(ex).__name__}: {ex}")
    with st.expander("Technical details"):
        st.code(traceback.format_exc())

st.markdown(
    f'<div class="footer">© SSS Tender Management Portal • {datetime.today().year}</div>',
    unsafe_allow_html=True,
)
