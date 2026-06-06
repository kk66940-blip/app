import streamlit as st
import sys
from pathlib import Path

# Ensure components can be imported when running on Streamlit Cloud
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from utils.export_utils import export_hierarchical_excel, export_hierarchical_pdf
from components.hierarchical_tree import display_rap_tree
from datetime import datetime

supabase = get_supabase()

project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header("📋 RAP - Rencana Anggaran Pelaksanaan")
st.subheader(f"Proyek: {project_name}")

if not project_id:
    st.warning("Pilih proyek di sidebar")
    st.stop()

st.divider()

# ==================== CREATE RAP FROM RAB (VERSI DIPERBAIKI) ====================
st.subheader("🔄 Buat RAP dari RAB")

col1, col2 = st.columns([1, 2])
with col1:
    percentage = st.number_input(
        "Persentase Harga dari RAB (%)",
        min_value=50,
        max_value=150,
        value=85,
        step=1
    )

with col2:
    st.write("")
    if st.button("🔄 Buat/Update RAP", type="primary", use_container_width=True):
        try:
            # Hapus data RAP lama
            supabase.table("rap_items").delete().eq("project_id", project_id).execute()

            # Ambil data RAB
            rab_items = supabase.table("rab_items") \
                .select("*") \
                .eq("project_id", project_id) \
                .execute().data

            inserted_count = 0
            for item in rab_items:
                rap_data = {
                    "project_id": project_id,
                    "rab_item_id": item['id'],
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

            st.success(f"✅ Berhasil membuat {inserted_count} item RAP!")
            st.rerun()   # <- ini penting agar data langsung ter-refresh

        except Exception as e:
            st.error(f"❌ Gagal membuat RAP: {str(e)}")

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

# ==================== TABEL DI HALAMAN ====================
st.subheader("📊 Daftar RAP (Hirarkis)")

rap_items = supabase.table("rap_items")\
    .select("*")\
    .eq("project_id", project_id)\
    .execute().data

if not rap_items:
    st.info("Belum ada data RAP. Buat RAP dari RAB di atas.")
    st.stop()

def build_rap_tree(items):
    """Build parent_id → children map (reused from export_utils logic)"""
    children_map = defaultdict(list)
    for item in items:
        children_map[item.get('parent_id')].append(item)
    for pid in children_map:
        children_map[pid] = sorted(children_map[pid], key=lambda x: (x.get('sort_order', 0), x.get('id', 0)))
    return children_map


def display_rap_tree(items, parent_id=None, level=0):
    """Recursive hierarchical display (consistent with RAB page)"""
    children = [item for item in items if item.get("parent_id") == parent_id]
    for item in sorted(children, key=lambda x: x.get('sort_order', 0)):
        indent = "　" * level * 2
        code = item.get('code', '')
        desc = item.get('description', '')
        
        prefix = "▶ " if level == 0 else "└─ "
        title = f"{indent}{prefix}{code} - {desc}" if code else f"{indent}{prefix}{desc}"

        vol = item.get("volume") or 0
        planned = item.get("planned_price") or 0
        exec_price = item.get("execution_price") or 0
        upah = item.get("upah") or 0

        total_rencana = vol * planned
        total_pelaksanaan = vol * exec_price
        total_upah = vol * upah

        with st.expander(title, expanded=False):
            col1, col2, col3 = st.columns(3)
            col1.metric("Volume", f"{vol:,.2f} {item.get('unit','')}")
            col2.metric("Harga Rencana", format_rupiah(planned))
            col3.metric("Harga Pelaksanaan", format_rupiah(exec_price))

            st.caption(
                f"**Total Rencana:** {format_rupiah(total_rencana)} | "
                f"**Total Pelaksanaan:** {format_rupiah(total_pelaksanaan)} | "
                f"**Total + Upah:** {format_rupiah(total_upah)}"
            )

            col_edit, col_delete = st.columns(2)
            with col_edit:
                if st.button("✏️ Edit Harga", key=f"edit_{item['id']}", use_container_width=True):
                    st.session_state.edit_rap_item = item
                    st.rerun()
            with col_delete:
                if st.button("🗑️ Hapus", key=f"del_{item['id']}", use_container_width=True):
                    st.warning("Fitur hapus akan ditambahkan nanti")

            # Recursive call for children
            display_rap_tree(items, item["id"], level + 1)

    # Edit Form (global)
    if "edit_rap_item" in st.session_state:
        item = st.session_state.edit_rap_item
        st.subheader(f"✏️ Edit Item: {item.get('code','')} - {item.get('description','')}")

        col1, col2 = st.columns(2)
        with col1:
            new_exec = st.number_input("Harga Pelaksanaan Baru (Rp)", value=float(item.get('execution_price', 0)), step=1000.0)
        with col2:
            new_upah = st.number_input("Upah Baru (Rp)", value=float(item.get('upah', 0)), step=1000.0)

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                try:
                    supabase.table("rap_items").update({
                        "execution_price": new_exec,
                        "upah": new_upah
                    }).eq("id", item['id']).execute()
                    st.success("✅ Harga berhasil diperbarui!")
                    del st.session_state.edit_rap_item
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        with col_cancel:
            if st.button("Batal", use_container_width=True):
                del st.session_state.edit_rap_item
                st.rerun()


# ==================== TAMPILAN HIRARKIS RAP (Mirip RAB) ====================
st.subheader("📊 Struktur RAP (Hirarkis)")

from components.hierarchical_tree import display_hierarchical_tree
from utils.helpers import format_rupiah

def render_rap_content(item):
    """Render konten RAP yang lebih lengkap dan rapi (mirip RAB)"""
    code = item.get('code', '')
    desc = item.get('description', '')
    vol = item.get('volume') or 0
    unit = item.get('unit', '')
    planned = item.get('planned_price') or 0
    exec_price = item.get('execution_price') or 0
    upah = item.get('upah') or 0

    total_rencana = vol * planned
    total_pelaksanaan = vol * exec_price
    total_upah = vol * upah
    
    # Hitung selisih (variance)
    variance = total_rencana - total_pelaksanaan
    variance_percent = ((planned - exec_price) / planned * 100) if planned > 0 else 0

    # === TAMPILAN UTAMA ===
    col1, col2, col3 = st.columns([2.5, 2, 2])
    
    with col1:
        st.write(f"**{code}**")
        st.caption(desc[:80] + "..." if len(desc) > 80 else desc)
    
    with col2:
        st.metric("Volume", f"{vol:,.2f} {unit}")
    
    with col3:
        st.metric("Harga Pelaksanaan", format_rupiah(exec_price))

    # Detail tambahan
    with st.expander("Lihat Detail Perhitungan", expanded=False):
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Harga Rencana (RAB)", format_rupiah(planned))
        col_b.metric("Total Rencana", format_rupiah(total_rencana))
        col_c.metric("Total Pelaksanaan", format_rupiah(total_pelaksanaan))

        st.divider()
        
        col_d, col_e = st.columns(2)
        col_d.metric("Selisih (RAB - RAP)", format_rupiah(variance))
        col_e.metric("Persentase Hemat/Boros", f"{variance_percent:.1f}%")

    # Tombol Edit
    if st.button("✏️ Edit Harga Pelaksanaan", key=f"rap_edit_{item['id']}", use_container_width=True):
        st.session_state.edit_rap_item = item
        st.rerun()


# ==================== PANGGIL KOMPONEN ====================
if rap_items:
    display_hierarchical_tree(
        items=rap_items,
        render_content=render_rap_content,
        key_prefix="rap_final"
    )
else:
    st.info("Belum ada data RAP. Silakan buat RAP dari RAB terlebih dahulu di bagian atas.")

st.divider()

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

