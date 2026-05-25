import streamlit as st
from utils.ahsp_helper import (
    get_all_ahsp_items,
    update_unit_price,
    get_price_breakdown,
    update_all_ahsp_prices,
    search_ahsp_items,
    get_ahsp_by_division
)
from utils.helpers import format_rupiah
from datetime import datetime

st.set_page_config(page_title="Database AHSP", layout="wide")
st.header("📋 Database AHSP - Analisis Harga Satuan Pekerjaan")
st.caption("Level 3 • Harga Satuan berdasarkan komposisi Material + Upah + Peralatan")

# ==================== UPDATE MASSAL ====================
col1, col2, col3 = st.columns([2, 1, 1])
with col2:
    if st.button("🔄 Update Semua Harga", type="primary", use_container_width=True):
        with st.spinner("Sedang memperbarui semua harga AHSP..."):
            count = update_all_ahsp_prices()
            st.success(f"✅ Berhasil memperbarui **{count}** item AHSP!")
            st.rerun()

with col3:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

st.divider()

# ==================== FILTER & SEARCH ====================
col_f1, col_f2 = st.columns([2, 1])

with col_f1:
    search_term = st.text_input(
        "🔍 Cari AHSP (kode / uraian)",
        placeholder="Contoh: A.1, beton, pasangan bata...",
        key="ahsp_search"
    )

with col_f2:
    # Ambil daftar divisi unik
    all_items_temp = get_all_ahsp_items()
    divisions = sorted(list(set([item.get('division_name', 'Lainnya') for item in all_items_temp if item.get('division_name')])))
    selected_division = st.selectbox(
        "Filter Divisi",
        options=["Semua Divisi"] + divisions,
        index=0
    )

st.divider()

# ==================== AMBIL DATA ====================
if search_term and search_term.strip():
    items = search_ahsp_items(search_term.strip())
    st.info(f"Menampilkan hasil pencarian untuk: **{search_term}**")
elif selected_division != "Semua Divisi":
    items = get_ahsp_by_division(selected_division)
else:
    items = get_all_ahsp_items()

if not items:
    st.warning("Tidak ada data AHSP yang ditemukan.")
    st.stop()

st.subheader(f"Total Item Ditampilkan: **{len(items)}**")

# ==================== TAMPILAN DATA ====================
for item in items:
    with st.expander(f"**{item['code']}** — {item['description']}", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Satuan", item.get("unit", "-"))
        with col2:
            st.metric("Harga Tersimpan", format_rupiah(item.get('stored_unit_price', 0)))
        with col3:
            st.metric("Harga Dihitung", format_rupiah(item.get('calculated_unit_price', 0)))
        with col4:
            diff = (item.get('calculated_unit_price', 0) or 0) - (item.get('stored_unit_price', 0) or 0)
            st.metric("Selisih", format_rupiah(diff), delta_color="inverse" if diff < 0 else "normal")

        # Breakdown Biaya
        breakdown = get_price_breakdown(item['id'])
        
        st.markdown("**Rincian Biaya:**")
        bcol1, bcol2, bcol3 = st.columns(3)
        bcol1.metric("Material", format_rupiah(breakdown.get('material_cost', 0)))
        bcol2.metric("Upah", format_rupiah(breakdown.get('labor_cost', 0)))
        bcol3.metric("Peralatan", format_rupiah(breakdown.get('equipment_cost', 0)))

        st.caption(f"Total dari komposisi: **{format_rupiah(breakdown.get('total_cost', 0))}**")

        # Tombol Update per item
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            if st.button("🔄 Update Harga Ini", key=f"update_{item['id']}", use_container_width=True):
                if update_unit_price(item['id']):
                    st.success("Harga berhasil diperbarui!")
                    st.rerun()
                else:
                    st.error("Gagal memperbarui harga.")

st.divider()

# ==================== INFO ====================
st.caption(f"Update terakhir: {datetime.now().strftime('%d %B %Y %H:%M')} | AHSP Level 3 - Harga dinamis berdasarkan resource")
