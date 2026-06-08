import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_rap_tree

supabase = get_supabase()


# ====================== HELPER ======================
def get_current_project():
    return (
        st.session_state.get("current_project_id"),
        st.session_state.get("selected_project_name", "Proyek")
    )


def fetch_rap_items(project_id: int) -> List[Dict]:
    if not project_id:
        return []
    return supabase.table("rap_items") \
        .select("*") \
        .eq("project_id", project_id) \
        .execute().data or []


# ====================== PAGE ======================
st.header("📋 RAP - Rencana Anggaran Pelaksanaan")

project_id, project_name = get_current_project()

if not project_id:
    st.warning("⚠️ Silakan pilih proyek di sidebar terlebih dahulu.")
    st.stop()

st.subheader(f"Proyek: **{project_name}**")
st.divider()


# ====================== 1. BUAT / UPDATE RAP ======================
st.subheader("🔄 Buat / Update RAP dari RAB")

with st.expander("Pengaturan Persentase", expanded=False):
    percentage = st.number_input(
        "Persentase Harga Pelaksanaan dari RAB (%)",
        min_value=50, max_value=150, value=85, step=1,
        help="Harga Pelaksanaan = Harga RAB × Persentase ini"
    )

if st.button("🔄 Buat / Update RAP", type="primary", use_container_width=True):
    if st.session_state.get("confirm_create_rap"):
        try:
            with st.spinner("Sedang membuat data RAP..."):
                # Hapus data RAP lama
                supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                # Ambil data RAB
                rab_items = supabase.table("rab_items") \
                    .select("*") \
                    .eq("project_id", project_id) \
                    .order("level").order("sort_order") \
                    .execute().data

                if not rab_items:
                    st.error("Tidak ada data RAB untuk proyek ini.")
                    st.stop()

                # Insert data RAP
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

                # Update parent_id untuk menjaga hierarchy
                for item in rab_items:
                    if item.get("parent_id") and item["parent_id"] in id_mapping:
                        supabase.table("rap_items") \
                            .update({"parent_id": id_mapping[item["parent_id"]]}) \
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
        st.warning("⚠️ **PERHATIAN**: Semua data RAP lama akan dihapus. Lanjutkan?")
        st.rerun()

st.divider()


# ====================== 2. EXPORT ======================
st.subheader("📤 Export RAP")

rap_items = fetch_rap_items(project_id)

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Export ke Excel", type="primary", use_container_width=True):
        if rap_items:
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
        else:
            st.warning("Tidak ada data RAP untuk diekspor.")

with col2:
    if st.button("🖨️ Export ke PDF", type="primary", use_container_width=True):
        if rap_items:
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
        else:
            st.warning("Tidak ada data RAP untuk diekspor.")

st.divider()


# ====================== 3. DAFTAR RAP + PENCARIAN ======================
st.subheader("📊 Daftar Item RAP")

if not rap_items:
    st.info("Belum ada data RAP. Silakan buat RAP dari RAB di atas.")
    st.stop()

# Input Pencarian
search_term = st.text_input(
    "🔍 Cari berdasarkan kode atau deskripsi",
    placeholder="Contoh: Pekerjaan atau A.1",
    key="rap_search_input"
).strip()

# Tampilkan Tree RAP
display_rap_tree(
    items=rap_items,
    on_edit=lambda item: st.session_state.update({"edit_rap_item": item}),
    on_delete=lambda item: st.session_state.update({"delete_rap_item_id": item["id"]}),
    search_term=search_term,
    key_prefix="rap",
    expanded_by_default=False
)


# ====================== EDIT FORM ======================
if "edit_rap_item" in st.session_state:
    item = st.session_state.edit_rap_item
    st.subheader(f"✏️ Edit Item: {item.get('code', '')} - {item.get('description', '')}")

    col1, col2 = st.columns(2)
    with col1:
        new_exec = st.number_input(
            "Harga Pelaksanaan Baru (Rp)", 
            value=float(item.get("execution_price", 0)), 
            step=1000.0
        )
    with col2:
        new_upah = st.number_input(
            "Upah Baru (Rp)", 
            value=float(item.get("upah", 0)), 
            step=1000.0
        )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True):
            supabase.table("rap_items").update({
                "execution_price": new_exec,
                "upah": new_upah
            }).eq("id", item["id"]).execute()
            st.success("✅ Harga berhasil diperbarui!")
            del st.session_state.edit_rap_item
            st.rerun()
    with col_cancel:
        if st.button("Batal", use_container_width=True):
            del st.session_state.edit_rap_item
            st.rerun()


# ====================== DELETE HANDLER ======================
if "delete_rap_item_id" in st.session_state:
    del_id = st.session_state.delete_rap_item_id
    st.warning("Apakah kamu yakin ingin menghapus item ini?")

    col_yes, col_no = st.columns(2)
    with col_yes:
        if st.button("✅ Ya, Hapus Item Ini", type="primary"):
            supabase.table("rap_items").delete().eq("id", del_id).execute()
            st.success("Item berhasil dihapus.")
            del st.session_state.delete_rap_item_id
            st.rerun()
    with col_no:
        if st.button("Batal"):
            del st.session_state.delete_rap_item_id
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
    "Selisih", 
    format_rupiah(variance),
    delta_color="inverse" if variance < 0 else "normal"
)

st.caption(f"Terakhir diperbarui: {datetime.now().strftime('%d %B %Y %H:%M')}")