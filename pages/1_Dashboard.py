import streamlit as st
from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from datetime import datetime
from collections import defaultdict

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header(f"📈 Dashboard - {project_name}")
st.caption(f"Update: {datetime.now().strftime('%d %B %Y %H:%M')}")

if not project_id:
    st.warning("Pilih proyek di sidebar")
    st.stop()

# ==================== AMBIL DATA ====================
rab_items = supabase.table("rab_items")\
    .select("id, parent_id, level, code, description, volume, unit_price")\
    .eq("project_id", project_id)\
    .order("level").order("sort_order").execute().data

# Hitung total RAB hanya dari item leaf (tidak punya child)
# supaya konsisten dengan export Excel & PDF
children_map = defaultdict(list)
for item in rab_items:
    children_map[item.get('parent_id')].append(item)

total_rab = sum(
    (item.get('volume') or 0) * (item.get('unit_price') or 0)
    for item in rab_items
    if len(children_map.get(item.get('id'), [])) == 0
)

# Opname Utama (RAB)
opname_details = supabase.table("opname_details")\
    .select("rab_item_id, actual_volume")\
    .execute().data

opname_map = {d['rab_item_id']: d['actual_volume'] for d in opname_details}

total_opname = sum(
    opname_map.get(item.get('id'), 0) * (item.get('unit_price', 0) or 0)
    for item in rab_items
)

# Opname Sub (RAP)
rap_items = supabase.table("rap_items")\
    .select("rab_item_id, execution_price")\
    .eq("project_id", project_id).execute().data

rap_price_map = {r['rab_item_id']: r.get('execution_price', 0) for r in rap_items}

opname_sub_details = supabase.table("opname_sub_details")\
    .select("rab_item_id, volume_actual")\
    .execute().data

opname_sub_map = {d['rab_item_id']: d['volume_actual'] for d in opname_sub_details}

total_opname_sub = sum(
    opname_sub_map.get(item.get('id'), 0) * rap_price_map.get(item.get('id'), 0)
    for item in rab_items
)

sisa_penagihan = total_rab - total_opname
selisih_opname = total_opname - total_opname_sub

# Jumlah Periode
period_count = supabase.table("opname_periods")\
    .select("id", count="exact")\
    .eq("project_id", project_id).execute().count or 0

# ==================== BAGIAN 1: RAB & OPNAME ====================
st.subheader("💰 Ringkasan RAB & Opname")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**Total RAB**")
    st.markdown(f"<div style='font-size:22px; font-weight:bold; color:#0d6efd;'>{format_rupiah(total_rab)}</div>", unsafe_allow_html=True)

with col2:
    progress = (total_opname / total_rab * 100) if total_rab > 0 else 0
    st.markdown("**Total Opname (RAB)**")
    st.markdown(f"<div style='font-size:22px; font-weight:bold;'>{format_rupiah(total_opname)}</div>", unsafe_allow_html=True)
    st.caption(f"📈 {progress:.1f}% dari RAB")

with col3:
    st.markdown("**Sisa Penagihan**")
    st.markdown(f"<div style='font-size:22px; font-weight:bold; color:#dc3545;'>{format_rupiah(sisa_penagihan)}</div>", unsafe_allow_html=True)

with col4:
    st.markdown("**Jumlah Periode**")
    st.markdown(f"<div style='font-size:22px; font-weight:bold;'>{period_count} Periode</div>", unsafe_allow_html=True)

st.divider()

# ==================== BAGIAN 2: OPNAME vs OPNAME SUB ====================
st.subheader("📊 Perbandingan Opname & Opname Sub")

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.metric("Total Opname (RAB)", format_rupiah(total_opname))

with col_b:
    st.metric("Total Opname Sub (RAP)", format_rupiah(total_opname_sub))

with col_c:
    selisih = total_opname - total_opname_sub
    
    if selisih > 0:
        delta_text = "📈 Opname lebih besar"
        delta_color = "normal"
    elif selisih < 0:
        delta_text = "📉 Opname Sub lebih besar"
        delta_color = "inverse"
    else:
        delta_text = "Sama"
        delta_color = "off"
    
    st.metric(
        label="Selisih (Opname - Opname Sub)", 
        value=format_rupiah(selisih),
        delta=delta_text,
        delta_color=delta_color
    )

st.divider()

# ==================== PROGRESS HIRARKIS PER PEKERJAAN UTAMA ====================
st.subheader("📋 Progress Pekerjaan Utama (Hirarkis)")

children_map = defaultdict(list)
for item in rab_items:
    children_map[item.get('parent_id')].append(item)

main_items = [item for item in rab_items if item.get('level', 0) == 0]

if main_items:
    for main in main_items:
        main_id = main['id']
        main_desc = main.get('description', '')

        # Ambil semua item di bawah main item ini (termasuk main itu sendiri)
        all_related_items = [main] + children_map.get(main_id, [])

        # ==================== NILAI RENCANA (Total dari semua sub item) ====================
        rencana_total = 0
        for item in all_related_items:
            rencana_total += (item.get('volume') or 0) * (item.get('unit_price') or 0)

        # ==================== NILAI REALISASI (Total dari data Opname) ====================
        realisasi_total = 0
        for item in all_related_items:
            actual_vol = opname_map.get(item['id'], 0)
            realisasi_total += actual_vol * (item.get('unit_price') or 0)

        # ==================== PROGRESS ====================
        progress_main = (realisasi_total / rencana_total * 100) if rencana_total > 0 else 0

        with st.expander(f"▶ {main.get('code','')} - {main_desc}", expanded=False):
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Nilai Rencana", format_rupiah(rencana_total))
            col_b.metric("Nilai Realisasi", format_rupiah(realisasi_total))
            col_c.metric("Progress", f"{progress_main:.1f}%")

            # Tampilkan detail sub pekerjaan
            if children_map.get(main_id):
                st.caption("**Sub Pekerjaan:**")
                for child in children_map.get(main_id, []):
                    c_vol = child.get('volume', 0) or 0
                    c_price = child.get('unit_price', 0) or 0
                    c_actual = opname_map.get(child['id'], 0)
                    c_real = c_actual * c_price
                    c_prog = (c_actual / c_vol * 100) if c_vol > 0 else 0

                    st.write(
                        f"• {child.get('description','')} → "
                        f"**{c_prog:.1f}%** "
                        f"({format_rupiah(c_real)} / {format_rupiah(c_vol * c_price)})"
                    )
else:
    st.info("Belum ada Main Item di RAB.")


st.divider()

# ==================== RINGKASAN PENGELUARAN ====================
st.subheader("💰 Ringkasan Pengeluaran")

try:
    expenses = supabase.table("project_expenses") \
        .select("category, amount") \
        .eq("project_id", project_id) \
        .execute().data

    if expenses:
        expense_summary = defaultdict(float)
        total_expense = 0

        for exp in expenses:
            expense_summary[exp["category"]] += exp.get("amount", 0)
            total_expense += exp.get("amount", 0)

        # Total Pengeluaran
        st.metric("Total Pengeluaran", format_rupiah(total_expense))

        # Ringkasan per Kategori
        st.markdown("**Per Kategori:**")
        cols = st.columns(len(expense_summary))
        for idx, (category, amount) in enumerate(expense_summary.items()):
            with cols[idx]:
                st.metric(category, format_rupiah(amount))
    else:
        st.info("Belum ada data pengeluaran untuk proyek ini.")

except Exception as e:
    st.error(f"Gagal memuat data pengeluaran: {e}")

