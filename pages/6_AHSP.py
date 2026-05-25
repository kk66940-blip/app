import streamlit as st
from utils.ahsp_helper import (
    get_all_ahsp_items,
    update_unit_price,
    get_price_breakdown,
    update_all_ahsp_prices
)

st.set_page_config(page_title="Database AHSP", layout="wide")
st.header("📋 Database AHSP")
st.caption("Manajemen Analisis Harga Satuan Pekerjaan")

# ==================== UPDATE MASSAL ====================
col1, col2 = st.columns([3, 1])
with col2:
    if st.button("🔄 Update Semua Harga", type="primary", use_container_width=True):
        with st.spinner("Sedang mengupdate semua harga..."):
            count = update_all_ahsp_prices()
            st.success(f"Berhasil memperbarui {count} item AHSP!")
            st.rerun()

st.divider()

# ==================== TAMPILAN DATA ====================
items = get_all_ahsp_items()

if not items:
    st.warning("Belum ada data AHSP. Silakan tambahkan data terlebih dahulu.")
    st.stop()

st.subheader(f"Total Item: {len(items)}")

for item in items:
    with st.expander(f"**{item['code']}** - {item['description']}", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Satuan", item.get("unit", "-"))
        col2.metric("Harga Tersimpan", f"Rp {item.get('stored_unit_price', 0):,.0f}")
        col3.metric("Harga Dihitung", f"Rp {item.get('calculated_unit_price', 0):,.0f}")

        # Breakdown
        breakdown = get_price_breakdown(item['id'])
        st.caption("**Rincian Biaya:**")
        st.write(f"• Material   : Rp {breakdown.get('material_cost', 0):,.0f}")
        st.write(f"• Upah       : Rp {breakdown.get('labor_cost', 0):,.0f}")
        st.write(f"• Peralatan  : Rp {breakdown.get('equipment_cost', 0):,.0f}")

        if st.button("🔄 Update Harga Satuan Ini", key=f"update_{item['id']}"):
            if update_unit_price(item['id']):
                st.success("Harga berhasil diperbarui!")
                st.rerun()
            else:
                st.error("Gagal memperbarui harga.")
