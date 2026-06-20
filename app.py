import sys
from pathlib import Path

import streamlit as st

# Tambahkan root project ke path agar 'components' dan 'utils' bisa diimpor
# secara andal di Streamlit Cloud maupun lingkungan deployment lain.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.supabase_client import get_supabase
from utils.auth import authenticate

st.set_page_config(
    page_title="RAB & Opname Online",
    layout="wide",
    page_icon="🏗️",
)

supabase = get_supabase()

# ==================== LOGIN ====================
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.header("🔐 Login")
    col1, _ = st.columns([2, 1])
    with col1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Login", type="primary", use_container_width=True
            )

        if submitted:
            if not (username and password):
                st.warning("Mohon isi username dan password")
            else:
                try:
                    user = authenticate(supabase, username, password)
                except Exception as e:
                    st.error("Terjadi kesalahan saat menghubungi server. Coba lagi.")
                    st.caption(f"Detail teknis: {e}")
                    st.stop()

                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    # Pesan error generik (tidak membocorkan apakah username ada)
                    st.error("❌ Username atau password salah")
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
        "📂 Pilih Proyek", list(project_dict.keys())
    )
    st.session_state.current_project_id = project_dict[selected_project_name]
    st.session_state.selected_project_name = selected_project_name
    st.sidebar.caption(f"**Proyek Aktif:** {selected_project_name}")
else:
    st.sidebar.info("Belum ada proyek. Buat di halaman Projects.")

pages = [
    st.Page("pages/0_Projects.py", title="Projects", icon="🏗️"),
    st.Page("pages/1_Dashboard.py", title="Dashboard", icon="📈"),
    st.Page("pages/13_Rekap_Proyek.py", title="Rekap Proyek", icon="📑"),
    st.Page("pages/2_RAB.py", title="RAB", icon="📋"),
    st.Page("pages/12_Adendum.py", title="Adendum", icon="📌"),
    st.Page("pages/3_Opname.py", title="Opname", icon="📝"),
    st.Page("pages/3_Opname_Sub.py", title="Opname Sub", icon="📝"),
    st.Page("pages/4_RAP.py", title="RAP", icon="📊"),
    st.Page("pages/5_Laporan.py", title="Laporan", icon="🖨️"),
    st.Page("pages/15_Laporan_Proyek.py", title="Laporan Proyek", icon="📄"),
    st.Page("pages/6_AHSP.py", title="AHSP", icon="📊"),
    st.Page("pages/7_Pengeluaran.py", title="Pengeluaran", icon="💰"),
    st.Page("pages/14_Pembayaran.py", title="Pembayaran Masuk", icon="💵"),
    st.Page("pages/8_SPK.py", title="SPK Sub", icon="📄"),
    st.Page("pages/9_Kalkulator_Material.py", title="Kalkulator Material", icon="🧮"),
    st.Page("pages/10_Pengaturan.py", title="Pengaturan", icon="⚙️"),
    st.Page("pages/11_Kurva_S.py", title="Kurva-S", icon="📈"),
]

pg = st.navigation(pages)
pg.run()
