import streamlit as st
import pandas as pd

st.set_page_config(page_title="Technician Dashboard", layout="wide")
st.title("🛠️ Technician Report Dashboard")

@st.cache_data(ttl=10) # Refreshes data automatically
def load_data():
    file_path = "Technician Report - Updated (1).xlsx"
    df = pd.read_excel(file_path, sheet_name="Service report", header=2)
    df = df.dropna(subset=['SN'])
    df['TANGGAL_PARSED'] = pd.to_datetime(df['TANGGAL'], errors='coerce')
    df = df.sort_values(by='TANGGAL_PARSED', ascending=False)
    return df

df = load_data()

st.subheader("🔍 Find Equipment Status")
search_sn = st.selectbox("Search or select a Serial Number (SN):", options=[""] + df['SN'].astype(str).unique().tolist(), index=0)

if search_sn:
    sn_data = df[df['SN'].astype(str) == search_sn]
    if not sn_data.empty:
        latest = sn_data.iloc[0]
        st.success(f"Latest Update Found for SN: **{search_sn}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Status", str(latest.get('STATUS', 'N/A')))
            st.write(f"**Technician:** {latest.get('PELAKSANA', 'N/A')}")
        with col2:
            st.write(f"**Date:** {latest.get('TANGGAL', 'N/A')}")
            st.write(f"**Tool:** {latest.get('NAMA ALAT', 'N/A')}")
        with col3:
            st.write(f"**Customer:** {latest.get('NAMA CUSTOMER', 'N/A')}")
            st.write(f"**Job Type:** {latest.get('JENIS PEKERJAAN', 'N/A')}")

        st.info(f"**Job Description:**\n\n{latest.get('URAIAN PEKERJAAN', 'No description.')}")