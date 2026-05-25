import streamlit as st
import hashlib
from utils.supabase_client import get_supabase

st.set_page_config(
    page_title="RAB & Opname Online",
    layout="wide",
    page_icon="🏗️"
)

supabase = get_supabase()

# ==================== LOGIN ====================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.header("🔐 Login")
    col1, col2 = st.columns([2, 1])
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login", type="primary", use_container_width=True):
            if username and password:
                res = supabase.table("users").select("*").eq("username", username).execute().data
                if res:
                    stored_hash = res[0].get("password_hash") or res[0].get("password")
                    input_hash = hashlib.sha256(password.encode()).hexdigest()
                    if stored_hash == input_hash:
                        st.session_state.user = res[0]
                        st.success(f"Selamat datang, {res[0].get('full_name') or username}!")
                        st.rerun()
                    else:
                        st.error("❌ Username atau password salah")
                else:
                    st.error("❌ Username atau password salah")
            else:
                st.warning("Mohon isi username dan password")
    st.stop()

# ==================== SIDEBAR ====================
user = st.session_state.user
st.sidebar.success(f"👷 {user.get('full_name') or user.get('username')}")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Project Selector
projects = supabase.table("projects").select("id, name").execute().data
if projects:
    project_dict = {p["name"]: p["id"] for p in projects}
    selected_project_name = st.sidebar.selectbox(
        "📂 Pilih Proyek", 
        list(project_dict.keys())
    )
    st.session_state.current_project_id = project_dict[selected_project_name]
    st.session_state.selected_project_name = selected_project_name
    st.sidebar.caption(f"**Proyek Aktif:** {selected_project_name}")

pages = [
    st.Page("pages/0_Projects.py", title="🏗️ Projects", icon="🏗️"),
    st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📈"),
    st.Page("pages/2_RAB.py", title="RAB", icon="📋"),
    st.Page("pages/3_Opname.py", title="Opname", icon="📝"),
    st.Page("pages/3_Opname_Sub.py", title="Opname Sub", icon="📝"),
    st.Page("pages/4_RAP.py", title="RAP", icon="📋"),
    st.Page("pages/5_Laporan.py", title="Laporan", icon="🖨️"),
    st.Page("pages/6_AHSP.py", title="AHSP", icon="📊"),   # ← Tambahkan baris ini
]

pg = st.navigation(pages)
pg.run()
