import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf

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

                # Hapus data RAP lama
                supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                # Salin data dari RAB ke RAP
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
            rap_items, 
            project_name, 
            "RENCANA ANGGARAN PELAKSANAAN (RAP)", 
            "RAP"
        )
        st.download_button(
            "Download Excel", 
            buffer, 
            f"RAP_{project_name.replace(' ', '_')}.xlsx"
        )

with col2:
    if st.button("🖨️ Export ke PDF (Format Profesional)", type="primary", use_container_width=True):
        rap_items = supabase.table("rap_items").select("*").eq("project_id", project_id).execute().data

        def get_rap_total(item):
            return (item.get('volume', 0) or 0) * (item.get('execution_price', 0) or 0)

        buffer = export_hierarchical_pdf(
            items=rap_items,
            project_name=project_name,
            title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
            filename_prefix="RAP",
            get_total_func=get_rap_total,
            id_key="rab_item_id",        # ← Ini kunci perbaikannya
            parent_key="parent_id"
        )
        st.download_button("Download PDF", buffer, f"RAP_{project_name}.pdf")

with col2:
    if st.button("🖨️ Export ke PDF", type="primary", use_container_width=True):
        rap_items = (
            supabase.table("rap_items")
            .select("*")
            .eq("project_id", project_id)
            .execute()
            .data
        )

        def get_rap_total(item):
            vol = item.get("volume", 0) or 0
            price = item.get("execution_price", 0) or 0
            return vol * price

        buffer = export_hierarchical_pdf(
            items=rap_items,
            project_name=project_name,
            title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
            filename_prefix="RAP",
            get_total_func=get_rap_total,
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
    st.info("Belum ada data RAP. Silakan buat RAP terlebih dahulu.")
    st.stop()

# Search
search = st.text_input(
    "🔍 Cari berdasarkan kode atau uraian", 
    placeholder="Contoh: plafon, dinding..."
).strip().lower()

filtered = rap_items
if search:
    filtered = [
        item for item in rap_items 
        if search in str(item.get("description", "")).lower() 
        or search in str(item.get("code", "")).lower()
    ]

# ==================== FUNGSI HIERARCHY RAP (DIPERBAIKI) ====================
def show_rap_hierarchy(items):
    def get_children(parent_rab_id):
        return [item for item in items if item.get("parent_id") == parent_rab_id]

    def render_node(item, level=0):
        indent = "　" * (level * 2)
        desc = item.get("description", "")
        vol = item.get("volume", 0) or 0
        planned = item.get("planned_price", 0) or 0
        exec_price = item.get("execution_price", 0) or 0
        total_exec = vol * exec_price
        unit = item.get("unit", "")

        with st.expander(f"{indent}{desc}", expanded=(level <= 1)):
            col1, col2, col3 = st.columns(3)
            col1.metric("Volume", f"{vol:,.2f} {unit}")
            col2.metric("Harga Rencana", f"Rp {planned:,.0f}")
            col3.metric("Harga Pelaksanaan", f"Rp {exec_price:,.0f}")

            st.caption(f"**Total Pelaksanaan:** Rp {total_exec:,.0f}")

            # Recursive untuk child
            children = get_children(item.get("rab_item_id"))
            for child in children:
                render_node(child, level + 1)

    # Ambil root items
    root_items = [item for item in items if not item.get("parent_id")]

    for root in root_items:
        render_node(root)

# Tampilkan data
if filtered:
    show_rap_hierarchy(filtered)
else:
    st.warning("Tidak ada item yang cocok dengan pencarian.")