import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from collections import defaultdict

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header("📝 SPK - Surat Perintah Kerja")
st.subheader(f"Proyek: {project_name}")

if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu")
    st.stop()
