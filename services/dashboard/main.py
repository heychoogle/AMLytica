import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime
from config import DATABASE_URL, REFRESH_INTERVAL

# Setup engine
engine = create_engine(DATABASE_URL)

# fetching data
def get_service_health():
    query = text("""
        SELECT worker_name, status
        FROM job_events 
        WHERE timestamp > NOW() - INTERVAL '30 seconds'
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if df.empty:
        return 0, 0, 0
        
    extractors = df[df['status'].str.contains('EXTRACT', case=False, na=False)]['worker_name'].nunique()
    analysts = df[df['status'].str.contains('ANALYS', case=False, na=False)]['worker_name'].nunique()
    reporters = df[df['status'].str.contains('REPORT', case=False, na=False)]['worker_name'].nunique()
    return extractors, analysts, reporters

def get_live_jobs():
    query = text("""
        SELECT j.job_id, c.name as customer, j.current_status as status, j.created_at
        FROM jobs j
        JOIN customers c ON j.customer_id = c.customer_id
        WHERE j.current_status NOT IN ('COMPLETED', 'FAILED', 'EXTRACTION_FAILED', 'ANALYSIS_FAILED', 'QUEUE_FAILED')
        ORDER BY j.created_at DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def get_completed_summary():
    query = text("""
        SELECT j.job_id, c.name as customer, j.created_at, e.message
        FROM jobs j
        JOIN customers c ON j.customer_id = c.customer_id
        JOIN job_events e ON j.job_id = e.job_id
        WHERE j.current_status = 'COMPLETED'
          AND e.status = 'COMPLETED'
        ORDER BY j.created_at DESC LIMIT 10
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if df.empty:
        return pd.DataFrame()

    df = df.drop_duplicates(subset=['job_id'])
    processed_rows = []

    for _, row in df.iterrows():
        h_count, s_count = 0, 0
        try:
            if row['message']:
                msg = row['message'].replace("'", '"')
                data = json.loads(msg)
                alerts = data.get('alerts', {})
                h_count = len(alerts.get('hard_flags', []))
                s_count = len(alerts.get('soft_flags', []))
        except:
            pass 
            
        processed_rows.append({
            'job_id': row['job_id'],
            'customer': row['customer'],
            'created_at': row['created_at'],
            'h_flags': h_count,
            's_flags': s_count
        })
    return pd.DataFrame(processed_rows)

# ui config

st.set_page_config(page_title="AMLytica Dashboard", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    .stAlert { padding: 0.5rem !important; margin-bottom: 0.2rem !important; }
    </style>
""", unsafe_allow_html=True)

st.title("AMLytica Dashboard")

# dashboard refresh

@st.fragment(run_every=REFRESH_INTERVAL)
def main_dashboard():
    # metrics
    ext_count, ana_count, rep_count = get_service_health()
    h1, h2, h3, h4, h5 = st.columns(5)
    
    with h1:
        st.metric("Extraction Fleet", f"{ext_count} Workers")
    with h2:
        st.metric("Analysis Fleet", f"{ana_count} Workers")
    with h3:
        st.metric("Report Fleet", f"{rep_count} Workers")
    with h4:
        is_active = (ext_count + ana_count + rep_count) > 0
        st.metric("System Status", "✅ Healthy" if is_active else "⚠️ Offline")
    with h5:
        st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))

    st.divider()

    # live jobs
    st.subheader("Live Jobs")
    live_df = get_live_jobs()
    if not live_df.empty:
        st.dataframe(live_df, width="stretch", hide_index=True)
    else:
        st.info("No active jobs currently in queue.")

    st.divider()

    # completed jobs
    st.subheader("Recently Completed")
    comp_df = get_completed_summary()

    if not comp_df.empty:
        for _, row in comp_df.iterrows():
            with st.container(border=True):
                st.markdown(f"**Job:** `{row['job_id'][:12]}...` | **Customer:** **{row['customer']}**")
                c1, c2, c3 = st.columns([1, 1, 3])
                with c1:
                    if row['h_flags'] > 0:
                        st.error(f"Hard Flags: {row['h_flags']}")
                    else:
                        st.success(f"Hard Flags: 0")
                with c2:
                    st.warning(f"Soft Flags: {row['s_flags']}")
                with c3:
                    st.caption(f"Processed at: {row['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.info("No completed jobs found.")

main_dashboard()