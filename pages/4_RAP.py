import streamlit as st
import sys
from pathlib import Path

# Ensure components can be imported when running on Streamlit Cloud
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from datetime import datetime

# Import komponen tree (dipindah ke atas agar lebih bersih)
from components.hierarchical_tree import display_rap_tree

supabase = get_supabase()

# ==================== PROJECT & SESSION GUARD ====================
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name")

st.header("📋 RAP - Rencana Anggaran Pelaksanaan")

if not project_id:
    st.warning("⚠️ Silakan pilih proyek terlebih dahulu di sidebar.")
    st.info("Gunakan dropdown **📂 Pilih Proyek** di sidebar kiri untuk memilih proyek aktif.")
    st.stop()

st.subheader(f"Proyek: {project_name}")

st.divider()

# ==================== BUAT RAP DARI RAB (VERSI AMAN & PROFESIONAL) ====================
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
                # === STEP 1: Ambil data RAB (diurutkan berdasarkan level) ===
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

                st.write(f"✅ Ditemukan {len(rab_items)} item RAB (termasuk multi-level).")

                # === STEP 2: Hapus data RAP lama ===
                st.write("2️⃣ Menghapus data RAP lama...")
                supabase.table("rap_items").delete().eq("project_id", project_id).execute()
                st.write("✅ Data RAP lama berhasil dihapus.")

# === STEP 3: Salin data RAP (Hierarchy mengikuti RAB asli) ===
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
        "parent_id": item.get('parent_id')   # Langsung pakai parent_id asli dari RAB
    }

    supabase.table("rap_items").insert(rap_data).execute()
    inserted_count += 1

st.write(f"✅ Berhasil menyalin {inserted_count} item RAP.")

                    supabase.table("rap_items").insert(rap_data).execute()
                    inserted_count += 1

                st.write(f"✅ Berhasil menyalin {inserted_count} item RAP.")

                status.update(label="✅ RAP berhasil dibuat!", state="complete")
                
                st.success(f"🎉 Berhasil membuat {inserted_count} item RAP!")
                st.caption(f"Persentase yang digunakan: {percentage}%")
                st.balloons()
                st.rerun()

        except Exception as e:
            status.update(label="❌ Gagal membuat RAP", state="error")
            st.error(f"❌ Terjadi kesalahan saat membuat RAP: {str(e)}")
            st.info("Silakan coba lagi. Jika masih error, hubungi developer.")
            
            with st.expander("Detail teknis (untuk developer)"):
                import traceback
                st.code(traceback.format_exc())
st.divider()

# ==================== EXPORT RAP (Menggunakan Centralized Utils) ====================
st.subheader("📤 Export RAP")

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Export ke Excel (Format Profesional)", type="primary", use_container_width=True):
        try:
            rap_items = supabase.table("rap_items")\
                .select("*")\
                .eq("project_id", project_id)\
                .execute().data

            if not rap_items:
                st.warning("Tidak ada data RAP untuk diekspor.")
                st.stop()

            # Gunakan fungsi terpusat (jauh lebih bersih & konsisten)
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
            st.success("✅ Export Excel berhasil menggunakan format standar profesional!")

        except Exception as e:
            st.error(f"❌ Error saat export Excel: {str(e)}")

with col2:
    if st.button("🖨️ Export ke PDF", type="primary", use_container_width=True):
        try:
            rap_items = supabase.table("rap_items")\
                .select("*")\
                .eq("project_id", project_id)\
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

# ==================== LOAD DATA RAP (DENGAN ERROR HANDLING) ====================
st.subheader("📊 Daftar Item RAP")

try:
    rap_items = supabase.table("rap_items") \
        .select("*") \
        .eq("project_id", project_id) \
        .order("level") \
        .execute().data
except Exception as e:
    st.error(f"❌ Gagal mengambil data RAP dari database: {str(e)}")
    st.info("Coba refresh halaman atau hubungi administrator.")
    st.stop()

if not rap_items:
    st.info("Belum ada data RAP untuk proyek ini.")
    st.markdown("Silakan klik tombol **🔄 Buat/Update RAP** di bagian atas untuk membuat data RAP dari RAB.")
    st.stop()

# ==================== SEARCH ====================
search_term = st.text_input(
    "🔍 Cari berdasarkan kode atau deskripsi",
    placeholder="Contoh: plafon, dinding, cat...",
    key="rap_search"
).strip().lower()

# Filter items berdasarkan search (jika ada)
if search_term:
    filtered_items = [
        item for item in rap_items 
        if search_term in str(item.get('code', '')).lower() 
        or search_term in str(item.get('description', '')).lower()
    ]
    if not filtered_items:
        st.warning(f"Tidak ditemukan item yang mengandung kata **'{search_term}'**.")
else:
    filtered_items = rap_items

# ==================== TAMPILKAN TREE MENGGUNAKAN KOMPONEN PROFESIONAL ====================
def handle_edit_price(item):
    """Callback untuk edit harga via komponen"""
    st.session_state.edit_rap_item = item
    st.rerun()

if not filtered_items:
    st.info("Tidak ada item RAP yang ditampilkan.")
else:
    try:
        display_rap_tree(
            items=filtered_items,
            search_term=search_term,
            key_prefix="rap_main"
        )
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan saat menampilkan daftar RAP: {str(e)}")
        st.info("Coba refresh halaman atau hubungi developer.")
        with st.expander("Detail Error (untuk developer)"):
            import traceback
            st.code(traceback.format_exc())

# ==================== FORM EDIT HARGA (Global) ====================
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

# ==================== RINGKASAN ====================
st.subheader("📈 Ringkasan RAP")

total_rencana = sum((item.get('volume') or 0) * (item.get('planned_price') or 0) for item in rap_items)
total_pelaksanaan = sum((item.get('volume') or 0) * (item.get('execution_price') or 0) for item in rap_items)
total_upah = sum((item.get('volume') or 0) * (item.get('upah') or 0) for item in rap_items)
total_biaya = total_pelaksanaan
total_variance = total_rencana - total_biaya

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Rencana (RAB)", format_rupiah(total_rencana))
with col2:
    st.metric("Total Pelaksanaan (RAP)", format_rupiah(total_pelaksanaan))
with col3:
    st.metric("Total Upah (Info)", format_rupiah(total_upah))
with col4:
    delta_color = "inverse" if total_variance < 0 else "normal"
    st.metric("Total Biaya RAP", format_rupiah(total_biaya),
              delta=format_rupiah(total_variance),
              delta_color=delta_color)

st.caption(f"Update: {datetime.now().strftime('%d %B %Y %H:%M')}")

