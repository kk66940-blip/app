from supabase import create_client, Client
import streamlit as st

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]   # ← Ganti ke service_role

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)