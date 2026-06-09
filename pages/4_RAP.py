import streamlit as st
import sys
from pathlib import Path

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
    percentage = st.number_input(
        "Persentase Harga Pelaksanaan (%)", 
        min_value=50, 
        max_value=150, 
        value=85, 
        step=1
    )

with col2:
    if st.button("🔄 Buat / Update RAP", type="primary", use_container_width=True):
        status = st.status("Memproses...", expanded=True)
        try:
            with status:
                rab_items = (
                    supabase.table("rab_items")
                    .select("*")
                    .eq("project_id", project_id)
                    .order("level")
                    .execute()
                    .data
                )
                
                if not rab_items:
                    st.error("Tidak ada data RAB untuk proyek ini.")
                    st.stop()

                supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                for item in rab_items:
                    rap_data = {
                        "project_id": project_id,
                        "rab_item_id": item.get("id"),
                        "code": item.get("code", ""),
                        "description": item.get("description", ""),
                        "unit": item.get("unit", ""),
                        "volume": item.get("volume", 0),
                        "planned_price": item.get("unit_price", 0),
                        "execution_price": round(item.get("unit_price", 0) * percentage / 100, 2),
                        "upah": 0,
                        "level": item.get("level", 0),
                        "parent_id": item.get("parent_id"),
                    }
                    supabase.table("rap_items").insert(rap_data).execute()

                status.update(label="✅ Berhasil!", state="complete")
                st.success("RAP berhasil dibuat / diperbarui!")
                st.rerun()

        except Exception as e:
            st.error(f"Terjadi kesalahan: {str(e)}")

st.divider()

# ==================== EXPORT ====================
st.subheader("📤 Export RAP")

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Export ke Excel (Format Profesional)", type="primary", use_container_width=True):
        rap_items = (
            supabase.table("rap_items")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
        )
        buffer = export_hierarchical_excel(
            items=rap_items,
            project_name=project_name,
            title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
            filename_prefix="RAP",
            id_key="rab_item_id",
            parent_key="parent_id"
        )
        st.download_button(
            "Download Excel", 
            buffer, 
            f"RAP_{project_name.replace(' ', '_')}.xlsx"
        )

with col2:
    if st.button("🖨️ Export ke PDF (Format Profesional)", type="primary", use_container_width=True):
        rap_items = (
            supabase.table("rap_items")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
        )

        def get_rap_total(item):
            return (item.get('volume', 0) or 0) * (item.get('execution_price', 0) or 0)

        buffer = export_hierarchical_pdf(
            items=rap_items,
            project_name=project_name,
            title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
            filename_prefix="RAP",
            get_total_func=get_rap_total,
            id_key="rab_item_id",
            parent_key="parent_id"
        )
        st.download_button(
            "Download PDF", 
            buffer, 
            f"RAP_{project_name.replace(' ', '_')}.pdf"
        )

st.divider()

# ==================== TAMPILAN DATA ====================
st.subheader("📊 Daftar Item RAP")

rap_items = (
    supabase.table("rap_items")
    .select("*")
    .eq("project_id", project_id)
    .order("level")
    .execute()
    .data
)

if not rap_items:
    st.info("Belum ada data RAP.")
    st.stop()

search = st.text_input("🔍 Cari...", placeholder="Ketik kode atau uraian...").strip().lower()

filtered = rap_items
if search:
    filtered = [
        item for item in rap_items 
        if search in str(item.get('description', '')).lower() 
        or search in str(item.get('code', '')).lower()
    ]

# Gunakan komponen resmi (sudah support Upah)
display_rap_tree(
    items=filtered,
    search_term=search,
    key_prefix="rap"
)

# ==================== RINGKASAN TOTAL RAP ====================
if filtered:
    total_volume = sum((item.get('volume', 0) or 0) for item in filtered)
    total_rencana = sum((item.get('volume', 0) or 0) * (item.get('planned_price', 0) or 0) for item in filtered)
    total_pelaksanaan = sum((item.get('volume', 0) or 0) * (item.get('execution_price', 0) or 0) for item in filtered)
    total_upah = sum((item.get('volume', 0) or 0) * (item.get('upah', 0) or 0) for item in filtered)

    st.divider()
    st.subheader("📈 Ringkasan Total RAP")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Volume", f"{total_volume:,.2f}")
    col2.metric("Total Harga Rencana", f"Rp {total_rencana:,.0f}")
    col3.metric("Total Harga Pelaksanaan", f"Rp {total_pelaksanaan:,.0f}")
    col4.metric("Total Upah", f"Rp {total_upah:,.0f}")

# ==================== FORM EDIT HARGA ====================
if "edit_rap_item" in st.session_state:
    item = st.session_state.edit_rap_item
    st.divider()
    st.subheader(f"✏️ Edit Harga: {item.get('description')}")

    new_exec_price = st.number_input(
        "Harga Pelaksanaan Baru (Rp)", 
        value=float(item.get('execution_price', 0)),
        step=1000.0,
        format="%.0f"
    )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True):
            supabase.table("rap_items").update({
                "execution_price": new_exec_price
            }).eq("id", item['id']).execute()
            del st.session_state.edit_rap_item
            st.success("Harga berhasil diperbarui!")
            st.rerun()
    with col_cancel:
        if st.button("Batal", use_container_width=True):
            del st.session_state.edit_rap_item
            st.rerun()