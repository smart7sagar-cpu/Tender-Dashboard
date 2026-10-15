import io
import sqlite3
import hashlib
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

    div[data-testid="stWidgetLabel"] p {{color:{NAVY}; font-weight:600; font-size:.86rem;}}
    div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {{
        background:#FFFFFF !important; border:1.5px solid #B8C6DF !important; border-radius:8px !important;
        transition:border-color .15s, box-shadow .15s;
    }}
    div[data-baseweb="base-input"] {{background:transparent !important;}}
    div[data-baseweb="input"]:hover, div[data-baseweb="textarea"]:hover, div[data-baseweb="select"] > div:hover {{
        border-color:#8FA6CF !important;
    }}
    div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {{
        border-color:{BLUE} !important; box-shadow:0 0 0 3px rgba(47,95,179,.18) !important;
    }}
    div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {{color:#1B2A44 !important;}}

    div.element-container:has(.sss-mk), div[data-testid="stElementContainer"]:has(.sss-mk),
    div[data-testid="element-container"]:has(.sss-mk) {{display:none;}}
</style>
""",
    unsafe_allow_html=True,
)

# ==================================================================
# DATABASE & AUTHENTICATION
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

def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

@st.cache_resource
def get_conn():
    conn = sqlite3.connect("tenders.db", check_same_thread=False)
    
    # Tenders Table
    conn.execute("CREATE TABLE IF NOT EXISTS tenders (id INTEGER PRIMARY KEY AUTOINCREMENT)")
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tenders)").fetchall()}
    for col, typ in DB_COLS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE tenders ADD COLUMN {col} {typ}")
            
    # Users Table (New)
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)")
    cur = conn.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", hash_pass("admin123"), "admin"))
        
    conn.commit()
    return conn

conn = get_conn()

# --- LOGIN SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown(
        f'<div class="topbar"><span>SECURE TENDER PORTAL</span>'
        f'<span>{datetime.today().strftime("%A, %d %B %Y")}</span></div>'
        '<div class="banner"><h1>🔒 LOGIN PORTAL</h1>'
        "<p>PLEASE ENTER YOUR CREDENTIALS TO ACCESS DATA</p></div>",
        unsafe_allow_html=True,
    )
    
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown('<div class="kpi" style="padding: 2rem;">', unsafe_allow_html=True)
        st.markdown('<h3 style="color:#12264A; text-align:center; margin-bottom: 20px;">Access Verification</h3>', unsafe_allow_html=True)
        
        u = st.text_input("Username", key="log_user")
        p = st.text_input("Password", type="password", key="log_pass")
        st.write("")
        
        if st.button("Secure Login", type="primary"):
            cur = conn.execute("SELECT password, role FROM users WHERE username=?", (u,))
            row = cur.fetchone()
            if row and row[0] == hash_pass(p):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = row[1]
                do_rerun()
            else:
                st.error("❌ Invalid Username or Password. Kripya sahi details dalein.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop() # Stops execution so main app doesn't load without login


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
# ENTER = AGLA FIELD (browser-side JS)
# ==================================================================
_NAV_JS = """
(function () {
  var p = window.parent, d = p.document;
  if (p.__sssEnterNav) { d.removeEventListener('keydown', p.__sssEnterNav, true); }
  function fields() {
    var s = d.querySelector('.sss-form-start'), e = d.querySelector('.sss-form-end');
    if (!s || !e) return null;
    return Array.prototype.slice.call(d.querySelectorAll('input, textarea')).filter(function (el) {
      var t = (el.type || '').toLowerCase();
      if (el.disabled || t === 'hidden' || t === 'checkbox' || t === 'radio' || t === 'button' || t === 'submit') return false;
      if (el.offsetParent === null) return false;
      return (s.compareDocumentPosition(el) & 4) && (e.compareDocumentPosition(el) & 2);
    });
  }
  function go(el) {
    if (!el) return;
    el.focus();
    try { if (el.tagName === 'INPUT' && el.getAttribute('role') !== 'combobox') el.select(); } catch (x) {}
  }
  function onKey(ev) {
    if (ev.key !== 'Enter' || ev.isComposing || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var el = ev.target;
    if (!el || (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA')) return;
    var list = fields(); if (!list) return;
    var i = list.indexOf(el); if (i < 0) return;
    if (i === list.length - 1) return;
    var isTA = el.tagName === 'TEXTAREA', isSel = el.getAttribute('role') === 'combobox';
    if (isTA && ev.shiftKey) return;
    if (isSel && el.getAttribute('aria-expanded') === 'true') {
      setTimeout(function () { var l = fields(), j = l ? l.indexOf(el) : -1; if (j >= 0 && j < l.length - 1) go(l[j + 1]); }, 150);
      return;
    }
    if (isTA || isSel) { ev.preventDefault(); ev.stopPropagation(); go(list[i + 1]); return; }
    setTimeout(function () { go(list[i + 1]); }, 0);
  }
  p.__sssEnterNav = onKey;
  d.addEventListener('keydown', onKey, true);
  if (__FOCUS_FIRST__) {
    setTimeout(function () { var l = fields(); if (l && l.length) go(l[0]); }, 400);
  }
})();
"""

def enter_nav(focus_first=False):
    try:
        import streamlit.components.v1 as components
        js = _NAV_JS.replace("__FOCUS_FIRST__", "true" if focus_first else "false")
        components.html(f"<script>{js}</script>", height=0)
    except Exception:
        pass

# ==================================================================
# RECORD FORM 
# ==================================================================
FIELD_KEYS = ["no", "name", "dept", "party", "cat", "loc", "wdesc", "est", "amt", "emd", "emds", "fee",
              "pub", "due", "open", "part", "res", "stat", "wo", "awd", "reason", "rem"]

def _init(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

def _pick(val, options, default=None):
    return val if val in options else (default if default is not None else options[0])

def record_form(prefix, rec=None, on_last=None, last_args=()):
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

    st.markdown('<span class="sss-mk sss-form-start"></span>', unsafe_allow_html=True)
    st.markdown("**📌 Basic Details**")
    c1, c2, c3 = st.columns(3)
    c1.text_input("Tender No.", key=P("no"))
    c2.text_input("Tender Name *", key=P("name"))
    c3.text_input("Department / Organization", key=P("dept"))
    c4, c5, c6 = st.columns(3)
    c4.text_input("Party Name *", key=P("party"))
    c5.selectbox("Category", cats, key=P("cat"))
    c6.text_input("Location", key=P("loc"))
    st.text_area("📝 Work Description", key=P("wdesc"), height=90)

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
    s5.number_input("Awardees Count", min_value=1, step=1, key=P("awd"))
    st.text_input("Reason (agar Not Participated hai)", key=P("reason"))
    if on_last:
        st.text_input("Remarks  ⬅ (LAST FIELD)", key=P("rem"), on_change=on_last, args=last_args)
    else:
        st.text_input("Remarks  ⬅ (LAST FIELD)", key=P("rem"))
    st.markdown('<span class="sss-mk sss-form-end"></span>', unsafe_allow_html=True)
    enter_nav(focus_first=bool(prefix == "add" and st.session_state.pop("focus_first", False)))

def collect(prefix):
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

def save_new():
    s = st.session_state
    vals = collect("add")
    if not vals["tender_name"] and not vals["party"] and time.time() - s.get("ts_add", 0) < 8:
        return
    if vals["tender_name"] and vals["party"]:
        vals["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        insert_record(vals)
        for k in FIELD_KEYS:
            s.pop(f"add_{k}", None)
        s["ts_add"] = time.time()
        s["focus_first"] = True
        s["msg_add"] = ("ok", "✅ Record save ho gaya!")
    else:
        s["msg_add"] = ("err", "❌ Tender Name aur Party Name bharna zaroori hai.")

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
        if msg[0] == "ok":
            st.success(msg[1])
        else:
            st.error(msg[1])
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
    f'<span>👤 {st.session_state.username.upper()} | {datetime.today().strftime("%A, %d %B %Y")}</span></div>'
    '<div class="banner"><h1>TENDER DASHBOARD - SSS</h1>'
    "<p>TENDER PARTICIPATION • RESULT • EMD • REPORTING SYSTEM</p></div>",
    unsafe_allow_html=True,
)

PAGES = ["Dashboard", "Add Record", "View Records", "Participated", "Not Participated",
         "Results", "EMD Tracker", "Reports", "Export & Reminder", "Backup & Import", "Settings", "Logout"]
ICONS = {"Dashboard": "📊", "Add Record": "➕", "View Records": "📋", "Participated": "✅",
         "Not Participated": "🚫", "Results": "🏆", "EMD Tracker": "💳", "Reports": "📈",
         "Export & Reminder": "🔔", "Backup & Import": "💾", "Settings": "⚙️", "Logout": "🚪"}

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

def goto_page(p):
    st.session_state.page = p
    st.session_state.pop("msg_add", None)
    st.session_state.pop("msg_edit", None)

# Update layout to support 12 buttons
for row in (PAGES[:6], PAGES[6:]):
    cols = st.columns(len(row), gap="small")
    for col, p in zip(cols, row):
        _s(col, "button", f"{ICONS[p]}  {p.upper()}", key=f"nav_{p}", on_click=goto_page, args=(p,),
                   type="primary" if st.session_state.page == p else "secondary",
                   use_container_width=True)

page = st.session_state.page
ALL = load_df()
EMPTY_MSG = "Abhi koi record nahi hai. 'ADD RECORD' se pehla tender add karein."

# ==================================================================
# MAIN PAGE ROUTING
# ==================================================================
def render_page():
    if page == "Logout":
        st.session_state.clear()
        do_rerun()

    elif page == "Settings":
        title("⚙️ User Settings & Access Control")
        
        st.markdown("### 🔑 Change My Password")
        c_old, c_new, c_conf = st.columns(3)
        old_p = c_old.text_input("Current Password", type="password")
        new_p = c_new.text_input("New Password", type="password")
        conf_p = c_conf.text_input("Confirm New Password", type="password")
        
        if st.button("Update Password", type="primary"):
            cur = conn.execute("SELECT password FROM users WHERE username=?", (st.session_state.username,))
            row = cur.fetchone()
            if row and row[0] == hash_pass(old_p):
                if new_p == conf_p and len(new_p) >= 4:
                    conn.execute("UPDATE users SET password=? WHERE username=?", (hash_pass(new_p), st.session_state.username))
                    conn.commit()
                    st.success("✅ Password successfully updated!")
                else:
                    st.error("❌ Naya password match nahi ho raha ya bahut chota hai (min 4 char).")
            else:
                st.error("❌ Purana password galat hai.")

        if st.session_state.role == "admin":
            st.markdown("---")
            title("👤 Manage Users (Admin Only)")