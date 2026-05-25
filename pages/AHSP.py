import streamlit as st
from utils.ahsp_helper import (
    get_all_ahsp_items,
    update_unit_price,
    get_price_breakdown,
    update_all_ahsp_prices
)

st.header("📋 Database AHSP")

# Tampilkan semua item
items = get_all_ahsp_items()

for item in items:
    with st.expander(f"{item['code']} - {item['description']}"):
        st.write(f"**Divisi:** {item.get('division_name', '-')}")
        st.write(f"**Satuan:** {item['unit']}")
        
        col1, col2 = st.columns(2)
        col1.metric("Harga Tersimpan", f"Rp {item['stored_unit_price']:,.0f}")
        col2.metric("Harga Dihitung", f"Rp {item['calculated_unit_price']:,.0f}")
        
        if st.button("Update Harga", key=f"btn_{item['id']}"):
            if update_unit_price(item['id']):
                st.success("Harga berhasil diperbarui!")
                st.rerun()

# Tombol Update Massal
if st.button("🔄 Update Semua Harga AHSP"):
    count = update_all_ahsp_prices()
    st.success(f"Berhasil update {count} item AHSP!")
