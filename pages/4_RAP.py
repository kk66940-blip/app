import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Optional

# Path fix
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_hierarchical_tree

supabase = get_supabase()

# ====================== HELPER ======================
def get_current_project():
    project_id = st.session_state.get("current_project_id")
    project_name = st.session_state.get("selected_project_name", "Proyek")
    return project_id, project_name


def fetch_rap_items(project_id: int) -> List[Dict]:
    """Ambil semua item RAP untuk proyek tertentu."""
    if not project_id:
        return []
    return supabase.table("rap_items") \
        .select("*") \
        .eq("project_id", project_id) \
        .execute().data or []


# ====================== PAGE ======================
st.set_page_config(page_title="RAP - RAB & Opname Online", layout="wide")
st.header("📋 RAP - Rencana Anggaran Pelaksanaan")

project_id, project_name = get_current_project()

if not project_id:
    st.warning("⚠️ Silakan pilih proyek di sidebar terlebih dahulu.")
    st.stop()

st.subheader(f"Proyek: **{project_name}**")
st.divider()

# ====================== 1. BUAT / UPDATE RAP ======================
st.subheader("🔄 Buat / Update RAP dari RAB")

with st.expander("⚙️ Pengaturan Pembuatan RAP", expanded=True):
    col1, col2 = st.columns([1, 3])
    
    with col1:
        percentage = st.number_input(
            "Persentase Harga Pelaksanaan dari RAB (%)",
            min_value=50, max_value=150, value=85, step=1,
            help="Harga pelaksanaan = Harga RAB × Persentase ini"
        )
    
    with col2:
        st.caption("Fitur ini akan **menghapus semua data RAP lama** lalu membuat ulang dari data RAB saat ini.")

    if st.button("🔄 Buat / Update RAP Sekarang", type="primary", use_container_width=True):
        if st.session_state.get("confirm_create_rap"):
            # === PROSES PEMBUATAN RAP ===
            try:
                with st.spinner("Sedang membuat data RAP..."):
                    # 1. Hapus data RAP lama
                    supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                    # 2. Ambil data RAB
                    rab_items = supabase.table("rab_items") \
                        .select("*") \
                        .eq("project_id", project_id) \
                        .order("level").order("sort_order") \
                        .execute().data

                    if not rab_items:
                        st.error("Tidak ada data RAB untuk proyek ini.")
                        st.stop()

                    # 3. Insert dengan mapping parent_id
                    id_mapping = {}
                    for item in rab_items:
                        rap_data = {
                            "project_id": project_id,
                            "rab_item_id": item["id"],
                            "code": item.get("code", ""),
                            "description": item.get("description", ""),
                            "unit": item.get("unit", ""),
                            "volume": item.get("volume", 0),
                            "planned_price": item.get("unit_price", 0),
                            "execution_price": round(item.get("unit_price", 0) * percentage / 100, 2),
                            "upah": 0,
                            "level": item.get("level", 0),
                            "parent_id": None,
                        }
                        result = supabase.table("rap_items").insert(rap_data).execute()
                        id_mapping[item["id"]] = result.data[0]["id"]

                    # 4. Update parent_id
                    for item in rab_items:
                        if item.get("parent_id") and item["parent_id"] in id_mapping:
                            new_parent = id_mapping[item["parent_id"]]
                            supabase.table("rap_items") \
                                .update({"parent_id": new_parent}) \
                                .eq("id", id_mapping[item["id"]]) \
                                .execute()

                st.success(f"✅ Berhasil membuat {len(rab_items)} item RAP!")
                st.balloons()
                st.session_state.confirm_create_rap = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ Gagal membuat RAP: {str(e)}")
                st.session_state.confirm_create_rap = False
        else:
            st.session_state.confirm_create_rap = True
            st.warning("⚠️ **PERHATIAN**: Tindakan ini akan menghapus semua data RAP yang sudah ada. Lanjutkan?")
            st.rerun()

st.divider()

# ====================== 2. EXPORT ======================
st.subheader("📤 Export RAP")

rap_items = fetch_rap_items(project_id)

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Export ke Excel", type="primary", use_container_width=True):
        if not rap_items:
            st.warning("Tidak ada data RAP untuk diekspor.")
        else:
            buffer = export_hierarchical_excel(
                items=rap_items,
                project_name=project_name,
                title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
                filename_prefix="RAP"
            )
            filename = f"RAP_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                "⬇️ Download Excel RAP",
                data=buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

with col2:
    if st.button("🖨️ Export ke PDF", type="primary", use_container_width=True):
        if not rap_items:
            st.warning("Tidak ada data RAP untuk diekspor.")
        else:
            buffer = export_hierarchical_pdf(
                items=rap_items,
                project_name=project_name,
                title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
                filename_prefix="RAP"
            )
            filename = f"RAP_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            st.download_button(
                "⬇️ Download PDF RAP",
                data=buffer,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )

st.divider()

# ====================== 3. TAMPILAN RAP (MENGGUNAKAN KOMPONEN) ======================
st.subheader("📊 Daftar Item RAP (Hirarkis)")

if not rap_items:
    st.info("Belum ada data RAP. Silakan buat RAP dari RAB di atas.")
    st.stop()

# Fungsi render konten di dalam expander
def render_rap_content(item: Dict):
    vol = item.get("volume") or 0
    unit = item.get("unit", "")
    planned = item.get("planned_price") or 0
    exec_price = item.get("execution_price") or 0
    upah = item.get("upah") or 0

    total_rencana = vol * planned
    total_pelaksanaan = vol * exec_price

    col1, col2, col3 = st.columns(3)
    col1.metric("Volume", f"{vol:,.2f} {unit}")
    col2.metric("Harga Rencana", format_rupiah(planned))
    col3.metric("Harga Pelaksanaan", format_rupiah(exec_price))

    st.caption(
        f"**Total Rencana:** {format_rupiah(total_rencana)} | "
        f"**Total Pelaksanaan:** {format_rupiah(total_pelaksanaan)}"
    )

    # Tombol aksi
    col_edit, col_del = st.columns(2)
    with col_edit:
        if st.button("✏️ Edit Harga", key=f"edit_{item['id']}", use_container_width=True):
            st.session_state.edit_rap_item = item
            st.rerun()

    with col_del:
        if st.button("🗑️ Hapus", key=f"del_{item['id']}", use_container_width=True):
            st.session_state.delete_rap_item_id = item["id"]
            st.rerun()

# Tampilkan tree menggunakan komponen reusable
display_hierarchical_tree(
    items=rap_items,
    render_content=render_rap_content,
    expanded_by_default=False,
    key_prefix="rap_tree"
)

# ====================== EDIT FORM (Global) ======================
if "edit_rap_item" in st.session_state:
    item = st.session_state.edit_rap_item
    st.subheader(f"✏️ Edit Item: {item.get('code', '')} - {item.get('description', '')}")

    col1, col2 = st.columns(2)
    with col1:
        new_exec = st.number_input(
            "Harga Pelaksanaan Baru (Rp)", 
            value=float(item.get("execution_price", 0)), 
            step=1000.0, format="%.2f"
        )
    with col2:
        new_upah = st.number_input(
            "Upah Baru (Rp)", 
            value=float(item.get("upah", 0)), 
            step=1000.0, format="%.2f"
        )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True):
            try:
                supabase.table("rap_items").update({
                    "execution_price": new_exec,
                    "upah": new_upah
                }).eq("id", item["id"]).execute()
                st.success("✅ Harga berhasil diperbarui!")
                del st.session_state.edit_rap_item
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

    with col_cancel:
        if st.button("Batal", use_container_width=True):
            del st.session_state.edit_rap_item
            st.rerun()

st.divider()

# ====================== 4. RINGKASAN ======================
st.subheader("📈 Ringkasan RAP")

total_rencana = sum((i.get("volume") or 0) * (i.get("planned_price") or 0) for i in rap_items)
total_pelaksanaan = sum((i.get("volume") or 0) * (i.get("execution_price") or 0) for i in rap_items)
total_upah = sum((i.get("volume") or 0) * (i.get("upah") or 0) for i in rap_items)
variance = total_rencana - total_pelaksanaan

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Rencana (RAB)", format_rupiah(total_rencana))
col2.metric("Total Pelaksanaan (RAP)", format_rupiah(total_pelaksanaan))
col3.metric("Total Upah", format_rupiah(total_upah))
col4.metric(
    "Selisih (Rencana - Pelaksanaan)", 
    format_rupiah(variance),
    delta_color="inverse" if variance < 0 else "normal"
)

st.caption(f"Terakhir diupdate: {datetime.now().strftime('%d %B %Y %H:%M')}")