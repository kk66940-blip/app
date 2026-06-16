import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_hierarchical_tree

supabase = get_supabase()

# ==================== HELPER ====================
project_id: Optional[int] = st.session_state.get("current_project_id")
project_name: str = st.session_state.get("selected_project_name", "")

def get_rap_items(project_id: int) -> List[Dict]:
    return (
        supabase.table("rap_items")
        .select("*")
        .eq("project_id", project_id)
        .order("level")
        .execute()
        .data
    ) or []

# ==================== UI ====================
st.header("📋 RAP - Rencana Anggaran Pelaksanaan (Advanced)")

if not project_id:
    st.warning("⚠️ Silakan pilih proyek terlebih dahulu di sidebar.")
    st.stop()

st.subheader(f"Proyek: {project_name}")
st.divider()

# ==================== 1. GENERATE RAP ====================
with st.expander("🔄 Generate / Update RAP dari RAB", expanded=False):
    col1, col2 = st.columns([1, 3])
    with col1:
        percentage = st.number_input(
            "Persentase Harga Pelaksanaan (%)",
            min_value=50, max_value=150, value=85, step=1
        )
    with col2:
        if st.button("Generate RAP Sekarang", type="primary", use_container_width=True):
            with st.status("Memproses...", expanded=True) as status:
                try:
                    rab_items = (
                        supabase.table("rab_items")
                        .select("*")
                        .eq("project_id", project_id)
                        .order("level")
                        .execute()
                        .data
                    )
                    if not rab_items:
                        st.error("Data RAB kosong.")
                        status.update(label="Gagal", state="error")
                        st.stop()

                    supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                    count = 0
                    for item in rab_items:
                        unit_price = item.get("unit_price") or 0
                        # Coba ambil upah dari RAB jika ada
                        rab_upah = item.get("upah") or item.get("labor_cost") or 0
                        
                        rap_data = {
                            "project_id": project_id,
                            "rab_item_id": item.get("id"),
                            "code": item.get("code", ""),
                            "description": item.get("description", ""),
                            "unit": item.get("unit", ""),
                            "volume": item.get("volume", 0),
                            "planned_price": unit_price,
                            "execution_price": round(unit_price * percentage / 100, 2),
                            "upah": rab_upah,           # ← Sekarang mengambil dari RAB
                            "level": item.get("level", 0),
                            "parent_id": item.get("parent_id"),
                        }
                        supabase.table("rap_items").insert(rap_data).execute()
                        count += 1

                    status.update(label=f"✅ Berhasil generate {count} item", state="complete")
                    st.success(f"RAP berhasil dibuat dengan persentase {percentage}%")
                    st.rerun()
                except Exception as e:
                    status.update(label="❌ Error", state="error")
                    st.error(str(e))

st.divider()

# ==================== 2. EXPORT ====================
st.subheader("📤 Export")
rap_items = get_rap_items(project_id)

col1, col2 = st.columns(2)
with col1:
    if st.button("📊 Export Excel", type="primary", use_container_width=True) and rap_items:
        buffer = export_hierarchical_excel(rap_items, project_name, "RENCANA ANGGARAN PELAKSANAAN (RAP)", "RAP")
        st.download_button("Download Excel", buffer, f"RAP_{project_name}.xlsx")

with col2:
    if st.button("🖨️ Export PDF", type="primary", use_container_width=True) and rap_items:
        def get_total(item):
            return (item.get("volume", 0) or 0) * (item.get("execution_price", 0) or 0)
        buffer = export_hierarchical_pdf(
            items=rap_items, project_name=project_name,
            title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
            filename_prefix="RAP",
            get_total_func=get_total,
            id_key="rab_item_id", parent_key="parent_id"
        )
        st.download_button("Download PDF", buffer, f"RAP_{project_name}.pdf")

st.divider()

# ==================== 3. SEARCH & DATA ====================
st.subheader("📊 Daftar Item RAP + Perbandingan")

search_term = st.text_input("🔍 Cari...", placeholder="Ketik kode atau uraian...").strip().lower()
rap_items = get_rap_items(project_id)

if not rap_items:
    st.info("Belum ada data RAP. Silakan generate terlebih dahulu.")
    st.stop()

filtered_items = [
    item for item in rap_items
    if search_term in str(item.get("description", "")).lower() or
       search_term in str(item.get("code", "")).lower()
] if search_term else rap_items

# ==================== EDIT FORM (Harga + Upah) ====================
if st.session_state.get("edit_rap_item"):
    item = st.session_state.edit_rap_item
    with st.form("edit_form"):
        st.write(f"**Edit:** {item.get('code', '')} - {item.get('description', '')}")
        
        new_execution_price = st.number_input(
            "Harga Pelaksanaan Baru (Rp)", 
            value=float(item.get("execution_price", 0)), 
            step=1000.0
        )
        new_upah = st.number_input(
            "Upah Baru (Rp)", 
            value=float(item.get("upah", 0)), 
            step=1000.0,
            help="Upah tenaga kerja per satuan"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Simpan Perubahan", type="primary"):
                supabase.table("rap_items").update({
                    "execution_price": new_execution_price,
                    "upah": new_upah
                }).eq("id", item["id"]).execute()
                del st.session_state.edit_rap_item
                st.success("Harga & Upah berhasil diperbarui!")
                st.rerun()
        with col2:
            if st.form_submit_button("Batal"):
                del st.session_state.edit_rap_item
                st.rerun()

# ==================== DELETE CONFIRMATION ====================
if st.session_state.get("delete_confirm_id"):
    del_id = st.session_state.delete_confirm_id
    st.warning(f"⚠️ Yakin ingin menghapus item ini? (ID: {del_id})")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Ya, Hapus", type="primary"):
            supabase.table("rap_items").delete().eq("id", del_id).execute()
            del st.session_state.delete_confirm_id
            st.success("Item berhasil dihapus.")
            st.rerun()
    with col2:
        if st.button("❌ Batal"):
            del st.session_state.delete_confirm_id
            st.rerun()

# ==================== RENDERER RAP (bentuk seperti RAB) ====================
def render_rap_content(item: Dict[str, Any]):
    """Renderer RAP: bentuk metric 3-kolom seperti RAB, info perbandingan di caption.

    Selisih = Rencana - Pelaksanaan (hemat = positif, boros = negatif).
    """
    vol = item.get("volume", 0) or 0
    planned = item.get("planned_price", 0) or 0
    exec_price = item.get("execution_price", 0) or 0
    upah = item.get("upah", 0) or 0

    total_rencana = vol * planned
    total_pelaksanaan = vol * exec_price
    total_upah = vol * upah
    # Selisih = penghematan: positif jika pelaksanaan lebih murah dari rencana.
    selisih = total_rencana - total_pelaksanaan
    persen_selisih = (selisih / total_rencana * 100) if total_rencana > 0 else 0

    # Metric utama (3 kolom, selaras dengan RAB)
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume", f"{vol:,.2f} {item.get('unit', '')}")
    c2.metric("Harga Pelaksanaan", format_rupiah(exec_price))
    c3.metric("Total Pelaksanaan", format_rupiah(total_pelaksanaan))

    # Info perbandingan RAP di caption (delta positif = hemat)
    st.caption(
        f"Harga Rencana: {format_rupiah(planned)} &nbsp;|&nbsp; "
        f"Selisih (hemat): {format_rupiah(selisih)} ({persen_selisih:+.1f}%) &nbsp;|&nbsp; "
        f"Total Upah: {format_rupiah(total_upah)}"
    )

    # Tombol aksi
    col_edit, col_del = st.columns(2)
    with col_edit:
        if st.button("✏️ Edit Harga & Upah", key=f"rap_edit_{item['id']}", use_container_width=True):
            st.session_state.edit_rap_item = item
            st.rerun()
    with col_del:
        if st.button("🗑️ Hapus", key=f"rap_del_{item['id']}", use_container_width=True):
            st.session_state.delete_confirm_id = item["id"]
            st.rerun()


# ==================== RENDER TREE (komponen reusable, sama dgn RAB) ====================
# rap_items memakai rab_item_id sebagai referensi parent, jadi id_key diset
# ke 'rab_item_id' agar tree terbentuk benar.
display_hierarchical_tree(
    items=filtered_items,
    render_content=render_rap_content,
    search_term=search_term,
    key_prefix="rap_page",
    id_key="rab_item_id",
    parent_key="parent_id",
)

# ==================== SUMMARY ====================
if filtered_items:
    st.divider()
    st.subheader("📈 Ringkasan Keseluruhan")

    total_vol = sum((i.get("volume", 0) or 0) for i in filtered_items)
    total_rencana = sum((i.get("volume", 0) or 0) * (i.get("planned_price", 0) or 0) for i in filtered_items)
    total_pelaksanaan = sum((i.get("volume", 0) or 0) * (i.get("execution_price", 0) or 0) for i in filtered_items)
    total_upah = sum((i.get("volume", 0) or 0) * (i.get("upah", 0) or 0) for i in filtered_items)
    # Selisih = penghematan (Rencana - Pelaksanaan)
    total_selisih = total_rencana - total_pelaksanaan

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Volume", f"{total_vol:,.2f}")
    c2.metric("Total Rencana", format_rupiah(total_rencana))
    c3.metric("Total Pelaksanaan", format_rupiah(total_pelaksanaan))
    c4.metric("Total Upah", format_rupiah(total_upah))
    c5.metric("Total Selisih (hemat)", format_rupiah(total_selisih), delta=f"{(total_selisih/total_rencana*100):+.1f}%" if total_rencana > 0 else None)

st.caption("Versi Advanced — dengan perbandingan per item & fitur hapus lengkap")