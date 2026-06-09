import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_rap_tree

supabase = get_supabase()

# ==================== SESSION & PROJECT ====================
project_id: Optional[int] = st.session_state.get("current_project_id")
project_name: str = st.session_state.get("selected_project_name", "")

st.header("📋 RAP - Rencana Anggaran Pelaksanaan")

if not project_id:
    st.warning("⚠️ Silakan pilih proyek terlebih dahulu di sidebar.")
    st.stop()

st.subheader(f"Proyek: {project_name}")
st.divider()

# ==================== 1. GENERATE / UPDATE RAP ====================
st.subheader("🔄 Generate RAP dari RAB")

with st.expander("Pengaturan Generate RAP", expanded=True):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        percentage = st.number_input(
            "Persentase Harga Pelaksanaan (%)",
            min_value=50,
            max_value=150,
            value=85,
            step=1,
            help="Harga pelaksanaan = Harga RAB × Persentase ini"
        )
    
    with col2:
        if st.button("🔄 Generate / Update RAP", type="primary", use_container_width=True):
            with st.status("Memproses Generate RAP...", expanded=True) as status:
                try:
                    # Ambil data RAB
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
                        status.update(label="Gagal", state="error")
                        st.stop()

                    # Hapus RAP lama (nanti bisa diubah jadi versioning)
                    supabase.table("rap_items").delete().eq("project_id", project_id).execute()

                    # Salin data RAB → RAP
                    inserted_count = 0
                    for item in rab_items:
                        unit_price = item.get("unit_price") or 0
                        execution_price = round(unit_price * percentage / 100, 2)

                        rap_data = {
                            "project_id": project_id,
                            "rab_item_id": item.get("id"),
                            "code": item.get("code", ""),
                            "description": item.get("description", ""),
                            "unit": item.get("unit", ""),
                            "volume": item.get("volume", 0),
                            "planned_price": unit_price,
                            "execution_price": execution_price,
                            "upah": 0,
                            "level": item.get("level", 0),
                            "parent_id": item.get("parent_id"),
                        }
                        supabase.table("rap_items").insert(rap_data).execute()
                        inserted_count += 1

                    status.update(label=f"✅ Berhasil! {inserted_count} item RAP dibuat.", state="complete")
                    st.success(f"RAP berhasil dibuat ulang dari RAB dengan persentase {percentage}%")
                    st.rerun()

                except Exception as e:
                    status.update(label="❌ Gagal", state="error")
                    st.error(f"Terjadi kesalahan: {str(e)}")

st.divider()

# ==================== 2. EXPORT ====================
st.subheader("📤 Export RAP")

col1, col2 = st.columns(2)

# Ambil data RAP sekali untuk export
rap_items_raw = (
    supabase.table("rap_items")
    .select("*")
    .eq("project_id", project_id)
    .order("level")
    .execute()
    .data
) if project_id else []

with col1:
    if st.button("📊 Export ke Excel (Format Profesional)", type="primary", use_container_width=True):
        if rap_items_raw:
            buffer = export_hierarchical_excel(
                rap_items_raw,
                project_name,
                "RENCANA ANGGARAN PELAKSANAAN (RAP)",
                "RAP"
            )
            st.download_button(
                "⬇️ Download Excel",
                buffer,
                f"RAP_{project_name.replace(' ', '_')}.xlsx",
                key="download_excel_rap"
            )
        else:
            st.warning("Tidak ada data RAP untuk diexport.")

with col2:
    if st.button("🖨️ Export ke PDF (Format Profesional)", type="primary", use_container_width=True):
        if rap_items_raw:
            def get_rap_total(item: Dict) -> float:
                vol = item.get("volume", 0) or 0
                price = item.get("execution_price", 0) or 0
                return vol * price

            buffer = export_hierarchical_pdf(
                items=rap_items_raw,
                project_name=project_name,
                title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
                filename_prefix="RAP",
                get_total_func=get_rap_total,
                id_key="rab_item_id",      # Penting untuk hierarchy
                parent_key="parent_id"
            )
            st.download_button(
                "⬇️ Download PDF",
                buffer,
                f"RAP_{project_name.replace(' ', '_')}.pdf",
                key="download_pdf_rap"
            )
        else:
            st.warning("Tidak ada data RAP untuk diexport.")

st.divider()

# ==================== 3. TAMPILAN DATA RAP ====================
st.subheader("📊 Daftar Item RAP")

# Ambil ulang data RAP (bisa berubah setelah generate)
rap_items = (
    supabase.table("rap_items")
    .select("*")
    .eq("project_id", project_id)
    .order("level")
    .execute()
    .data
)

if not rap_items:
    st.info("Belum ada data RAP. Silakan generate terlebih dahulu.")
    st.stop()

# Search
search_term = st.text_input(
    "🔍 Cari item RAP",
    placeholder="Ketik kode atau uraian...",
    key="rap_search"
).strip().lower()

# ==================== EDIT FORM ====================
if "edit_rap_item" in st.session_state and st.session_state.edit_rap_item:
    edit_item = st.session_state.edit_rap_item
    
    with st.form(key="edit_rap_price_form"):
        st.subheader(f"✏️ Edit Harga Pelaksanaan")
        st.write(f"**Item:** {edit_item.get('code', '')} - {edit_item.get('description', '')}")
        
        new_execution_price = st.number_input(
            "Harga Pelaksanaan Baru (Rp)",
            min_value=0.0,
            value=float(edit_item.get("execution_price", 0)),
            step=1000.0,
            format="%.2f"
        )
        
        col_save, col_cancel = st.columns(2)
        with col_save:
            submitted = st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("❌ Batal", use_container_width=True)
        
        if submitted:
            try:
                supabase.table("rap_items").update({
                    "execution_price": new_execution_price
                }).eq("id", edit_item["id"]).execute()
                
                st.success("Harga pelaksanaan berhasil diperbarui!")
                del st.session_state.edit_rap_item
                st.rerun()
            except Exception as e:
                st.error(f"Gagal menyimpan: {str(e)}")
        
        if cancelled:
            del st.session_state.edit_rap_item
            st.rerun()

# ==================== TAMPILAN HIERARKI MENGGUNAKAN KOMPONEN ====================
def handle_rap_edit(item: Dict[str, Any]):
    """Callback untuk tombol edit di tree"""
    st.session_state.edit_rap_item = item
    st.rerun()

# Gunakan komponen reusable
display_rap_tree(
    items=rap_items,
    on_edit_price=handle_rap_edit,
    search_term=search_term,
    key_prefix="rap"
)

# ==================== RINGKASAN TOTAL + PERBANDINGAN RAB vs RAP ====================
if rap_items:
    st.divider()
    st.subheader("📈 Ringkasan Total RAP & Perbandingan")

    # Hitung total RAP
    total_volume = sum((item.get("volume", 0) or 0) for item in rap_items)
    total_planned = sum((item.get("volume", 0) or 0) * (item.get("planned_price", 0) or 0) for item in rap_items)
    total_execution = sum((item.get("volume", 0) or 0) * (item.get("execution_price", 0) or 0) for item in rap_items)
    total_upah = sum((item.get("upah", 0) or 0) for item in rap_items)

    # Ambil total RAB untuk perbandingan
    rab_total = 0
    try:
        rab_items_for_total = (
            supabase.table("rab_items")
            .select("volume, unit_price")
            .eq("project_id", project_id)
            .execute()
            .data
        )
        rab_total = sum((item.get("volume", 0) or 0) * (item.get("unit_price", 0) or 0) for item in rab_items_for_total)
    except:
        rab_total = 0

    # Tampilkan metrik
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Volume", f"{total_volume:,.2f}")
    col2.metric("Total Harga Rencana (RAB)", format_rupiah(total_planned))
    col3.metric("Total Harga Pelaksanaan (RAP)", format_rupiah(total_execution))
    col4.metric("Selisih (RAP - RAB)", format_rupiah(total_execution - rab_total))

    # Persentase
    if rab_total > 0:
        diff_pct = ((total_execution - rab_total) / rab_total) * 100
        st.caption(f"**Persentase selisih terhadap RAB:** {diff_pct:+.2f}%")

    if total_upah > 0:
        st.metric("Total Upah", format_rupiah(total_upah))

st.caption("Catatan: Fitur versioning RAP dan historis akan ditambahkan di versi berikutnya.")