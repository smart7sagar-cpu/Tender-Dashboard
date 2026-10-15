import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime, timedelta

# डेटाबेस कनेक्शन
conn = sqlite3.connect('tenders.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS tenders
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              tender_name TEXT,
              party TEXT,
              amount REAL,
              due_date TEXT,
              status TEXT)''')
conn.commit()

st.set_page_config(page_title="Tender Dashboard", layout="wide")
st.title("📑 Tender Management Dashboard")

menu = st.sidebar.radio("Navigation", ["Add Record", "View Records", "Dashboard", "Export & Reminder"])

# ------------------ ADD RECORD ------------------
if menu == "Add Record":
    st.subheader("➕ Add Tender Record")
    with st.form("tender_form", clear_on_submit=True):
        tender_name = st.text_input("Tender Name")
        party = st.text_input("Party Name")
        amount = st.number_input("Amount", min_value=0.0, step=500.0)
        due_date = st.date_input("Due Date")
        status = st.selectbox("Status", ["Pending", "Completed"])
        submit = st.form_submit_button("Save Record")

        if submit:
            if tender_name and party:
                c.execute("INSERT INTO tenders (tender_name, party, amount, due_date, status) VALUES (?, ?, ?, ?, ?)",
                          (tender_name, party, amount, str(due_date), status))
                conn.commit()
                st.success("✅ Record saved successfully!")
            else:
                st.error("❌ Please fill out both Tender Name and Party Name.")

# ------------------ VIEW RECORDS ------------------
elif menu == "View Records":
    st.subheader("📋 All Tender Records")
    df = pd.read_sql("SELECT * FROM tenders", conn)

    if df.empty:
        st.info("No records found. Please add a tender first.")
    else:
        # फिल्टर्स
        col1, col2 = st.columns(2)
        with col1:
            party_filter = st.selectbox("Filter by Party", ["All"] + list(df['party'].dropna().unique()))
        with col2:
            status_filter = st.selectbox("Filter by Status", ["All", "Pending", "Completed"])

        filtered_df = df.copy()
        if party_filter != "All":
            filtered_df = filtered_df[filtered_df['party'] == party_filter]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]

        st.dataframe(filtered_df, use_container_width=True)

        # एडिट और डिलीट सेक्शन
        st.markdown("---")
        st.subheader("✏️ Edit or Delete a Record")
        
        selected_id = st.selectbox("Select Tender ID to Modify", df['id'].tolist())
        record_to_edit = df[df['id'] == selected_id].iloc[0]

        with st.form("edit_form"):
            edit_name = st.text_input("Tender Name", value=record_to_edit['tender_name'])
            edit_party = st.text_input("Party Name", value=record_to_edit['party'])
            edit_amount = st.number_input("Amount", min_value=0.0, value=float(record_to_edit['amount']), step=500.0)
            
            try:
                default_date = datetime.strptime(record_to_edit['due_date'], "%Y-%m-%d").date()
            except ValueError:
                default_date = datetime.today().date()
                
            edit_due_date = st.date_input("Due Date", value=default_date)
            edit_status = st.selectbox("Status", ["Pending", "Completed"], index=["Pending", "Completed"].index(record_to_edit['status']))
            
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                update_btn = st.form_submit_button("🔄 Update Record")
            with btn_col2:
                delete_btn = st.form_submit_button("🗑️ Delete Record")

            if update_btn:
                c.execute("""UPDATE tenders SET tender_name=?, party=?, amount=?, due_date=?, status=? 
                             WHERE id=?""", (edit_name, edit_party, edit_amount, str(edit_due_date), edit_status, selected_id))
                conn.commit()
                st.success("✅ Record updated successfully!")
                st.rerun()

            if delete_btn:
                c.execute("DELETE FROM tenders WHERE id=?", (selected_id,))
                conn.commit()
                st.warning(f"⚠️ Record ID {selected_id} deleted.")
                st.rerun()

# ------------------ DASHBOARD ------------------
elif menu == "Dashboard":
    st.subheader("📊 Analytics Overview")
    df = pd.read_sql("SELECT * FROM tenders", conn)

    if df.empty:
        st.info("Add records to visualize insights.")
    else:
        # मुख्य मैट्रिक्स
        total_tenders = len(df)
        total_val = df['amount'].sum()
        pending_val = df[df['status'] == 'Pending']['amount'].sum()
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Tenders", total_tenders)
        m_col2.metric("Total Volume Value", f"${total_val:,.2f}")
        m_col3.metric("Pending Volume Value", f"${pending_val:,.2f}")

        st.markdown("---")
        
        # चार्ट्स
        fig_col1, fig_col2 = st.columns(2)
        
        with fig_col1:
            st.markdown("#### Status Breakdown")
            fig_status = px.pie(df, names='status', values='amount', hole=0.4, 
                                color_discrete_map={'Pending': '#ff4b4b', 'Completed': '#00cc96'})
            st.plotly_chart(fig_status, use_container_width=True)
            
        with fig_col2:
            st.markdown("#### Share Value by Party")
            fig_party = px.bar(df, x='party', y='amount', color='status', 
                               labels={'amount': 'Tender Amount', 'party': 'Party Name'},
                               barmode='group')
            st.plotly_chart(fig_party, use_container_width=True)

# ------------------ EXPORT & REMINDER ------------------
elif menu == "Export & Reminder":
    st.subheader("📤 Data Export")
    df = pd.read_sql("SELECT * FROM tenders", conn)

    if df.empty:
        st.info("No data available to export.")
    else:
        # CSV एक्सपोर्ट बटन
        st.markdown("#### 💾 Export Dataset")
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Dataset as CSV",
            data=csv_data,
            file_name=f"tenders_export_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
