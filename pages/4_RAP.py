import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_rap_tree

supabase = get_supabase()

project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name")

st.header("📋 RAP - Rencana Anggaran Pelaksanaan")

if not project_id:
    st.warning("⚠️ Silakan pilih proyek terlebih dahulu di sidebar.")
    st.stop()

st.subheader(f"Proyek: {project_name}")
st.divider()

# ==================== BUAT / UPDATE RAP ====================
st.subheader("🔄 Buat / Update RAP dari RAB")

col1, col2 = st.columns([1, 2])
with col1:
    percentage = st.number_input("Persentase Harga Pelaksanaan (%)", min_value=50, max_value=150, value=85, step=1)

with col2:
    if st.button("🔄 Buat / Update RAP", type="primary", use_container_width=True):
        status = st.status("Memproses...", expanded=True)
        try:
            with status:
                rab_items = supabase.table("rab_items").select("*").eq("project_id", project_id).order("level").execute().data
                if not rab_items:
                    st.error("Tidak ada data RAB.")
                    st.stop()

                supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                for item in rab_items:
                    rap_data = {
                        "project_id": project_id,
                        "rab_item_id": item.get('id'),
                        "code": item.get('code', ''),
                        "description": item.get('description', ''),
                        "unit": item.get('unit', ''),
                        "volume": item.get('volume', 0),
                        "planned_price": item.get('unit_price', 0),
                        "execution_price": round(item.get('unit_price', 0) * percentage / 100, 2),
                        "upah": 0,
                        "level": item.get('level', 0),
                        "parent_id": item.get('parent_id')
                    }
                    supabase.table("rap_items").insert(rap_data).execute()

                status.update(label="✅ Berhasil!", state="complete")
                st.success("RAP berhasil dibuat!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")

st.divider()

# ==================== EXPORT ====================
st.subheader("📤 Export RAP")

col1, col2 = st.columns(2)
with col1:
    if st.button("📊 Export Excel", type="primary", use_container_width=True):
        rap_items = supabase.table("rap_items").select("*").eq("project_id", project_id).execute().data
        buffer = export_hierarchical_excel(rap_items, project_name, "RENCANA ANGGARAN PELAKSANAAN (RAP)", "RAP")
        st.download_button("Download Excel", buffer, f"RAP_{project_name}.xlsx")

with col2:
    if st.button("🖨️ Export PDF", type="primary", use_container_width=True):
        rap_items = supabase.table("rap_items").select("*").eq("project_id", project_id).execute().data
        
        def get_rap_total(item):
            return (item.get('volume', 0) or 0) * (item.get('execution_price', 0) or 0)

        buffer = export_hierarchical_pdf(
            items=rap_items,
            project_name=project_name,
            title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
            filename_prefix="RAP",
            get_total_func=get_rap_total
        )
        st.download_button("Download PDF", buffer, f"RAP_{project_name}.pdf")

st.divider()

# ==================== TAMPILAN DATA ====================
st.subheader("📊 Daftar Item RAP")

rap_items = supabase.table("rap_items").select("*").eq("project_id", project_id).order("level").execute().data

if not rap_items:
    st.info("Belum ada data RAP.")
    st.stop()

search = st.text_input("Cari...").lower()
filtered = [i for i in rap_items if search in str(i.get('description','')).lower() or search in str(i.get('code','')).lower()] if search else rap_items

display_rap_tree(items=filtered, search_term=search, key_prefix="rap")

# Form Edit (sederhana)
if "edit_rap_item" in st.session_state:
    item = st.session_state.edit_rap_item
    st.subheader(f"Edit: {item.get('description')}")
    new_price = st.number_input("Harga Pelaksanaan", value=float(item.get('execution_price', 0)))
    if st.button("Simpan"):
        supabase.table("rap_items").update({"execution_price": new_price}).eq("id", item['id']).execute()
        del st.session_state.edit_rap_item
        st.rerun()