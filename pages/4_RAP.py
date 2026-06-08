import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Ensure components can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_rap_tree

supabase = get_supabase()

# ==================== PROJECT GUARD ====================
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name")

st.header("📋 RAP - Rencana Anggaran Pelaksanaan")

if not project_id:
    st.warning("⚠️ Silakan pilih proyek terlebih dahulu di sidebar.")
    st.info("Gunakan dropdown **📂 Pilih Proyek** di sidebar kiri.")
    st.stop()

st.subheader(f"Proyek: {project_name}")

st.divider()

# ==================== BUAT RAP DARI RAB ====================
st.subheader("🔄 Buat / Update RAP dari RAB")

col1, col2 = st.columns([1, 2])
with col1:
    percentage = st.number_input(
        "Persentase Harga Pelaksanaan dari RAB (%)",
        min_value=50,
        max_value=150,
        value=85,
        step=1,
        help="Harga Pelaksanaan = Harga RAB × Persentase ini"
    )

with col2:
    if st.button("🔄 Buat / Update RAP", type="primary", use_container_width=True):
        
        status = st.status("Memproses pembuatan RAP...", expanded=True)
        
        try:
            with status:
                # STEP 1: Ambil data RAB
                st.write("1️⃣ Mengambil data RAB...")
                
                rab_items = supabase.table("rab_items") \
                    .select("*") \
                    .eq("project_id", project_id) \
                    .order("level") \
                    .execute().data

                if not rab_items:
                    st.error("❌ Tidak ada data RAB untuk proyek ini.")
                    st.info("Silakan buat data RAB terlebih dahulu di halaman RAB.")
                    st.stop()

                st.write(f"✅ Ditemukan {len(rab_items)} item RAB.")

                # STEP 2: Hapus data RAP lama
                st.write("2️⃣ Menghapus data RAP lama...")
                supabase.table("rap_items").delete().eq("project_id", project_id).execute()
                st.write("✅ Data RAP lama berhasil dihapus.")

                # STEP 3: Salin data RAP (Hierarchy mengikuti RAB)
                st.write("3️⃣ Menyalin data dari RAB ke RAP...")
                
                inserted_count = 0
                
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
                    inserted_count += 1

                st.write(f"✅ Berhasil menyalin {inserted_count} item RAP.")

                status.update(label="✅ RAP berhasil dibuat!", state="complete")
                st.success(f"🎉 Berhasil membuat {inserted_count} item RAP!")
                st.balloons()
                st.rerun()

        except Exception as e:
            status.update(label="❌ Gagal membuat RAP", state="error")
            st.error(f"❌ Terjadi kesalahan: {str(e)}")
            with st.expander("Detail Error"):
                import traceback
                st.code(traceback.format_exc())

st.divider()

# ==================== EXPORT RAP ====================
st.subheader("📤 Export RAP")

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Export ke Excel (Format Profesional)", type="primary", use_container_width=True):
        try:
            rap_items = supabase.table("rap_items") \
                .select("*") \
                .eq("project_id", project_id) \
                .execute().data

            if not rap_items:
                st.warning("Tidak ada data RAP untuk diekspor.")
                st.stop()

            buffer = export_hierarchical_excel(
                items=rap_items,
                project_name=project_name,
                title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
                filename_prefix="RAP"
            )

            filename = f"RAP_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                label="⬇️ Download Excel RAP",
                data=buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.success("✅ Export Excel berhasil!")

        except Exception as e:
            st.error(f"❌ Error saat export Excel: {str(e)}")

with col2:
    if st.button("🖨️ Export ke PDF", type="primary", use_container_width=True):
        try:
            rap_items = supabase.table("rap_items") \
                .select("*") \
                .eq("project_id", project_id) \
                .execute().data

            if not rap_items:
                st.warning("Tidak ada data RAP untuk diekspor.")
                st.stop()

            buffer = export_hierarchical_pdf(
                items=rap_items,
                project_name=project_name,
                title="RENCANA ANGGARAN PELAKSANAAN (RAP)",
                filename_prefix="RAP"
            )

            filename = f"RAP_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="⬇️ Download PDF RAP",
                data=buffer,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )
            st.success("✅ Export PDF berhasil!")

        except Exception as e:
            st.error(f"❌ Error saat export PDF: {str(e)}")

st.divider()

# ==================== DAFTAR ITEM RAP ====================
# ==================== TAMPILAN DATA ====================
st.subheader("📊 Daftar Item RAP")

rap_items = supabase.table("rap_items") \
    .select("*") \
    .eq("project_id", project_id) \
    .order("level") \
    .execute().data

if not rap_items:
    st.info("Belum ada data RAP untuk proyek ini.")
    st.stop()

search = st.text_input("🔍 Cari berdasarkan kode atau uraian", placeholder="Contoh: plafon, dinding...").strip().lower()

filtered = rap_items
if search:
    filtered = [
        item for item in rap_items 
        if search in str(item.get('description', '')).lower() 
        or search in str(item.get('code', '')).lower()
    ]

# ==================== FUNGSI TAMPILAN HIERARCHY RAP (VERSI DIPERBAIKI) ====================
def show_rap_hierarchy(items):
    # Buat mapping: rab_item_id -> rap_item
    id_map = {item.get('rab_item_id'): item for item in items if item.get('rab_item_id')}
    
    # Cari parent_id yang valid (hanya yang ada di data RAP)
    def get_children(parent_rab_id):
        return [item for item in items if item.get('parent_id') == parent_rab_id]

    def render_node(item, level=0):
        indent = "　" * (level * 2)
        desc = item.get('description', '')
        vol = item.get('volume', 0) or 0
        planned = item.get('planned_price', 0) or 0
        exec_price = item.get('execution_price', 0) or 0
        total_exec = vol * exec_price
        unit = item.get('unit', '')

        with st.expander(f"{indent}{desc}", expanded=(level <= 1)):
            col1, col2, col3 = st.columns(3)
            col1.metric("Volume", f"{vol:,.2f} {unit}")
            col2.metric("Harga Rencana", f"Rp {planned:,.0f}")
            col3.metric("Harga Pelaksanaan", f"Rp {exec_price:,.0f}")

            st.caption(f"**Total Pelaksanaan:** Rp {total_exec:,.0f}")

            # Cari child berdasarkan parent_id (yang asli dari RAB)
            children = get_children(item.get('rab_item_id'))
            for child in children:
                render_node(child, level + 1)

    # Ambil root items (parent_id kosong / None)
    root_items = [item for item in items if not item.get('parent_id')]
    
    for root in root_items:
        render_node(root)

# ==================== FORM EDIT HARGA ====================
if "edit_rap_item" in st.session_state:
    item = st.session_state.edit_rap_item
    
    st.divider()
    st.subheader(f"✏️ Edit Harga: {item.get('code','')} - {item.get('description','')}")
    
    col1, col2 = st.columns(2)
    with col1:
        new_exec = st.number_input(
            "Harga Pelaksanaan Baru (Rp)", 
            value=float(item.get('execution_price', 0)), 
            step=1000.0,
            key="new_exec_price"
        )
    with col2:
        new_upah = st.number_input(
            "Upah Baru (Rp)", 
            value=float(item.get('upah', 0)), 
            step=1000.0,
            key="new_upah_price"
        )

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True, key="save_rap_edit"):
            try:
                supabase.table("rap_items").update({
                    "execution_price": new_exec,
                    "upah": new_upah
                }).eq("id", item['id']).execute()
                st.success("✅ Harga berhasil diperbarui!")
                del st.session_state.edit_rap_item
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal menyimpan: {str(e)}")
    with col_cancel:
        if st.button("Batal", use_container_width=True, key="cancel_rap_edit"):
            del st.session_state.edit_rap_item
            st.rerun()