import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
from collections import defaultdict
import sys
from pathlib import Path

# Path fix for deployment (Streamlit Cloud)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from components.hierarchical_tree import display_opname_tree
from utils.helpers import format_rupiah

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")


# ==================== FUNGSI INVOICE OPNAME SUB ====================
def generate_invoice_sub_pdf(period_id, period_label, kasbon_value, selected_child_ids=None):
    """Buat PDF Invoice Opname Sub.

    selected_child_ids : set/list id child (rab_items.id) yang akan dimasukkan ke
        invoice. Jika None, semua child dengan volume > 0 dimasukkan (perilaku lama).
    """
    try:
        project_res = supabase.table("projects").select("*").eq("id", project_id).execute()
        project = project_res.data[0] if project_res.data else {}

        rab_items = supabase.table("rab_items")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("level").order("sort_order").execute().data

        rap_items = supabase.table("rap_items")\
            .select("*")\
            .eq("project_id", project_id).execute().data

        opname_sub_details = supabase.table("opname_sub_details")\
            .select("*")\
            .eq("period_id", period_id).execute().data

        actual_map = {d['rab_item_id']: d['volume_actual'] for d in opname_sub_details}
        kasbon_item_map = {d['rab_item_id']: (d.get('kasbon_amount') or 0) for d in opname_sub_details}
        rap_price_map = {r['rab_item_id']: r.get('execution_price', 0) for r in rap_items}

        children_map = defaultdict(list)
        for item in rab_items:
            children_map[item.get('parent_id')].append(item)

        def _child_included(cid):
            """Child masuk invoice jika volume > 0 dan (tak ada filter atau terpilih)."""
            if (actual_map.get(cid, 0) or 0) <= 0:
                return False
            if selected_child_ids is None:
                return True
            return cid in selected_child_ids

        main_items = [item for item in rab_items
                      if (item.get('level', 0) == 0 or
                          (item.get('volume', 0) == 0 and "pekerjaan" in item.get('description', '').lower()))
                      and any(_child_included(child['id']) for child in children_map.get(item['id'], []))]

        if not main_items:
            st.warning("Tidak ada item terpilih untuk dibuat invoice di periode ini.")
            return

        subtotal = 0
        total_kasbon_per_item = 0
        table_data = [["No", "Uraian Pekerjaan", "Sat", "Vol", "Harga RAP (Rp)", "Nilai (Rp)", "Kasbon (Rp)"]]
        item_no = 1

        for main_item in main_items:
            main_id = main_item['id']
            table_data.append(["", f"▶ {main_item.get('description', '')}", "", "", "", "", ""])

            for child in children_map.get(main_id, []):
                if _child_included(child['id']):
                    vol = actual_map[child['id']]
                    price = rap_price_map.get(child['id'], 0)
                    nilai = vol * price
                    kasbon_item = kasbon_item_map.get(child['id'], 0)
                    subtotal += nilai
                    total_kasbon_per_item += kasbon_item

                    table_data.append([
                        str(item_no),
                        f"    {item_no}. {child.get('description', '')}",
                        child.get('unit', ''),
                        f"{vol:,.2f}",
                        f"{price:,.0f}",
                        f"{nilai:,.0f}",
                        f"{kasbon_item:,.0f}" if kasbon_item > 0 else "-"
                    ])
                    item_no += 1

        table_data.append(["", "SUBTOTAL", "", "", "", f"{subtotal:,.0f}", f"{total_kasbon_per_item:,.0f}"])

        ppn_rate = project.get('ppn_rate', 11.0)
        retensi_rate = project.get('retensi_rate', 5.0)
        ppn = subtotal * (ppn_rate / 100)
        retensi = subtotal * (retensi_rate / 100)
        grand_total = subtotal + ppn - retensi - total_kasbon_per_item - kasbon_value

        filename = f"Invoice_Sub_{project_name}_{period_label[:25]}.pdf".replace(" ", "_")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)

        styles = getSampleStyleSheet()
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9)
        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#2E7D32'))

        elements = []
        from utils.company import get_company_settings, build_letterhead, build_bank_footer
        _company = get_company_settings()
        build_letterhead(elements, _company, styles)
        elements.append(Paragraph("INVOICE OPNAME SUB (HARGA RAP)", title_style))
        elements.append(Paragraph(f"<b>Proyek:</b> {project_name}", normal))
        elements.append(Paragraph(f"<b>Periode:</b> {period_label}", normal))
        elements.append(Paragraph(f"<b>Tanggal:</b> {datetime.now().strftime('%d %B %Y')}", normal))
        elements.append(Spacer(1, 0.5*cm))

        # Kolom lebih ramping karena ada kolom Kasbon baru
        t = Table(table_data, colWidths=[0.8*cm, 6*cm, 1.3*cm, 1.8*cm, 2.8*cm, 2.8*cm, 2.5*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            # Highlight kolom kasbon per item dengan warna kuning muda
            ('BACKGROUND', (6, 1), (6, -1), colors.HexColor('#FFFDE7')),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))

        summary_data = [
            ["Keterangan", "Jumlah (Rp)"],
            ["Subtotal Opname Sub", f"{subtotal:,.0f}"],
            [f"PPN ({ppn_rate}%)", f"{ppn:,.0f}"],
            [f"Retensi ({retensi_rate}%)", f"- {retensi:,.0f}"],
            ["Potongan Kasbon per Item", f"- {total_kasbon_per_item:,.0f}"],
            ["Potongan Kasbon Sub (Global)", f"- {kasbon_value:,.0f}"],
            ["GRAND TOTAL", f"{grand_total:,.0f}"]
        ]

        summary_table = Table(summary_data, colWidths=[10*cm, 6*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Highlight baris kasbon per item dengan kuning muda
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#FFFDE7')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
        ]))
        elements.append(summary_table)

        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("Mohon transfer ke rekening kami.", normal))
        build_bank_footer(elements, _company, styles)
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Hormat kami,", normal))
        elements.append(Spacer(1, 1.5*cm))
        elements.append(Paragraph("_________________________", normal))
        elements.append(Paragraph("Direktur / Pengelola Proyek", normal))

        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            label="⬇️ Download Invoice Opname Sub PDF",
            data=buffer,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True
        )
        st.success("Invoice Opname Sub berhasil dibuat!")

    except Exception as e:
        st.error(f"Error saat membuat invoice: {str(e)}")


# ==================== UI UTAMA ====================
st.header("📝 Opname Sub - Harga dari RAP")

if not project_id:
    st.warning("Pilih proyek di sidebar")
    st.stop()

# ==================== PERIODE + KASBON ====================
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    periods = supabase.table("opname_periods")\
        .select("id, period_no, opname_date, description, kasbon_sub")\
        .eq("project_id", project_id)\
        .order("period_no").execute().data

    period_options = {f"Periode {p['period_no']} - {p['description']} ({p['opname_date']})": p['id'] for p in periods}

    if period_options:
        selected_label = st.selectbox("Pilih Periode Opname Sub", list(period_options.keys()))
        current_period_id = period_options[selected_label]
    else:
        st.warning("Belum ada periode. Buat dulu di menu Opname utama.")
        current_period_id = None

with col2:
    with st.expander("➕ Periode Baru", expanded=False):
        with st.form("new_period_sub"):
            period_no = st.number_input("Nomor Periode", min_value=1, value=1)
            opname_date = st.date_input("Tanggal Opname", datetime.now())
            description = st.text_input("Keterangan", f"Opname Sub Minggu ke-{period_no}")

            if st.form_submit_button("Buat Periode"):
                supabase.table("opname_periods").insert({
                    "project_id": project_id,
                    "period_no": period_no,
                    "opname_date": str(opname_date),
                    "description": description,
                    "kasbon_sub": 0
                }).execute()
                st.success("Periode berhasil dibuat!")
                st.rerun()

with col3:
    if current_period_id:
        kasbon_data = supabase.table("opname_periods").select("kasbon_sub").eq("id", current_period_id).execute().data
        current_kasbon = kasbon_data[0]["kasbon_sub"] if kasbon_data else 0

        kasbon = st.number_input("Kasbon Sub (Rp)", min_value=0, value=int(current_kasbon), step=100000)
        if st.button("Simpan Kasbon Sub", use_container_width=True):
            supabase.table("opname_periods").update({"kasbon_sub": kasbon}).eq("id", current_period_id).execute()
            st.success("Kasbon Sub disimpan!")

# ==================== TOMBOL AKSI ====================
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("💾 Simpan Opname Sub", type="primary", use_container_width=True):
        st.success("Data Opname Sub berhasil disimpan!")
with col_b:
    if st.button("🧾 Buat Invoice Sub", type="primary", use_container_width=True):
        if current_period_id:
            st.session_state.show_invoice_sub_picker = True
        else:
            st.warning("Pilih periode terlebih dahulu")
with col_c:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.divider()

# ==================== TREE OPNAME SUB ====================
st.subheader("Struktur Opname Sub (Harga RAP)")

if not current_period_id:
    st.info("Pilih atau buat periode terlebih dahulu")
    st.stop()

# Data
rab_items = supabase.table("rab_items")\
    .select("*")\
    .eq("project_id", project_id)\
    .order("level").order("sort_order").execute().data

rap_items = supabase.table("rap_items")\
    .select("*")\
    .eq("project_id", project_id).execute().data

opname_sub_details = supabase.table("opname_sub_details")\
    .select("*")\
    .eq("period_id", current_period_id).execute().data

actual_map = {d['rab_item_id']: d['volume_actual'] for d in opname_sub_details}
kasbon_map = {d['rab_item_id']: (d.get('kasbon_amount') or 0) for d in opname_sub_details}
rap_price_map = {r['rab_item_id']: r.get('execution_price', 0) for r in rap_items}

# ==================== PANEL PEMILIHAN ITEM INVOICE ====================
# Fallback aman: kasbon didefinisikan di col3 hanya bila ada periode; pastikan ada.
try:
    kasbon
except NameError:
    kasbon = 0
if st.session_state.get("show_invoice_sub_picker"):
    _children_map = defaultdict(list)
    for _it in rab_items:
        _children_map[_it.get('parent_id')].append(_it)

    # Item utama yang punya minimal satu child dengan volume > 0
    _mains = [it for it in rab_items
              if (it.get('level', 0) == 0 or
                  (it.get('volume', 0) == 0 and "pekerjaan" in it.get('description', '').lower()))
              and any((actual_map.get(c['id'], 0) or 0) > 0 for c in _children_map.get(it['id'], []))]

    # Kumpulan id child yang berhak masuk (volume > 0)
    _eligible = [
        (m, [c for c in _children_map.get(m['id'], []) if (actual_map.get(c['id'], 0) or 0) > 0])
        for m in _mains
    ]

    with st.container(border=True):
        st.markdown("### 🧾 Pilih item untuk Invoice Sub")
        if not _eligible:
            st.warning("Tidak ada item dengan volume opname di periode ini.")
            if st.button("Tutup", key="inv_close_empty"):
                st.session_state.show_invoice_sub_picker = False
                st.rerun()
            st.stop()

        # Inisialisasi default: semua tercentang
        all_child_ids = [c['id'] for _, kids in _eligible for c in kids]
        if "inv_sub_sel" not in st.session_state:
            st.session_state.inv_sub_sel = set(all_child_ids)

        bcol1, bcol2, _ = st.columns([1, 1, 3])
        if bcol1.button("✅ Pilih Semua", key="inv_all", use_container_width=True):
            st.session_state.inv_sub_sel = set(all_child_ids)
            st.rerun()
        if bcol2.button("⬜ Kosongkan", key="inv_none", use_container_width=True):
            st.session_state.inv_sub_sel = set()
            st.rerun()

        sel = st.session_state.inv_sub_sel

        for main, kids in _eligible:
            kid_ids = [c['id'] for c in kids]
            all_on = all(cid in sel for cid in kid_ids)
            # Checkbox induk: mengubahnya men-set/clear semua child
            main_checked = st.checkbox(
                f"**▶ {main.get('description', '')}**",
                value=all_on, key=f"inv_main_{main['id']}",
            )
            if main_checked and not all_on:
                sel.update(kid_ids); st.rerun()
            elif not main_checked and all_on:
                sel.difference_update(kid_ids); st.rerun()

            # Child di dalam expander
            with st.expander(f"Detail ({len(kids)} item)", expanded=False):
                for c in kids:
                    cid = c['id']
                    vol = actual_map.get(cid, 0) or 0
                    price = rap_price_map.get(cid, 0) or 0
                    nilai = vol * price
                    child_on = st.checkbox(
                        f"{c.get('description', '')} — {vol:,.2f} {c.get('unit','')} × "
                        f"{format_rupiah(price)} = {format_rupiah(nilai)}",
                        value=(cid in sel), key=f"inv_child_{cid}",
                    )
                    if child_on:
                        sel.add(cid)
                    else:
                        sel.discard(cid)

        st.divider()
        n_sel = len(sel)
        total_sel = sum((actual_map.get(cid, 0) or 0) * (rap_price_map.get(cid, 0) or 0) for cid in sel)
        st.caption(f"**{n_sel} item terpilih** — Subtotal: {format_rupiah(total_sel)}")

        gcol1, gcol2 = st.columns([1, 1])
        with gcol1:
            if st.button("📄 Generate PDF", type="primary", use_container_width=True, key="inv_gen"):
                if n_sel == 0:
                    st.warning("Pilih minimal satu item.")
                else:
                    generate_invoice_sub_pdf(current_period_id, selected_label, kasbon, set(sel))
        with gcol2:
            if st.button("Batal", use_container_width=True, key="inv_cancel"):
                st.session_state.show_invoice_sub_picker = False
                st.rerun()



def handle_save_opname_sub(item, new_actual, uploaded_file, new_kasbon=0):
    """Callback untuk Opname Sub — simpan volume + kasbon per item"""
    try:
        supabase.table("opname_sub_details").upsert({
            "period_id": current_period_id,
            "rab_item_id": item['id'],
            "volume_actual": new_actual,
            "kasbon_amount": new_kasbon
        }).execute()
        st.success("✅ Volume & Kasbon Sub berhasil disimpan!")
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")


# ==================== TAMPILAN HIRARKIS ====================
display_opname_tree(
    items=rab_items,
    actual_map=actual_map,
    rap_price_map=rap_price_map,
    kasbon_map=kasbon_map,
    on_save=handle_save_opname_sub,
    show_photo_upload=False,
    show_kasbon=True,
    key_prefix="opname_sub"
)

st.divider()

# ==================== RINGKASAN ====================
total_nilai = sum(
    (actual_map.get(item['id'], 0) * rap_price_map.get(item['id'], 0))
    for item in rab_items
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Opname Sub Periode Ini", f"Rp {total_nilai:,.0f}")

# Hitung total kasbon per item dari opname_sub_details
_kasbon_per_item_total = sum(
    (d.get('kasbon_amount') or 0)
    for d in supabase.table("opname_sub_details")
        .select("kasbon_amount")
        .eq("period_id", current_period_id).execute().data
)
col2.metric("Total Kasbon per Item", f"Rp {_kasbon_per_item_total:,.0f}")
col3.metric("Total Kasbon Sub (Global)", f"Rp {kasbon:,.0f}")
col4.metric("Net Setelah Semua Kasbon", f"Rp {total_nilai - _kasbon_per_item_total - kasbon:,.0f}")

# ==================== EDIT LANGSUNG + KASBON PER ITEM (TANPA TOMBOL EDIT TERPISAH) ====================
st.divider()
st.subheader("✏️ Edit Volume & Kasbon per Item (Langsung)")

if current_period_id:
    opname_details = supabase.table("opname_sub_details") \
        .select("*") \
        .eq("period_id", current_period_id).execute().data
    opname_map = {d['rab_item_id']: d for d in opname_details}

    # Tampilkan SEMUA item RAB yang punya volume (bisa langsung edit/create)
    items_with_record = [
        item for item in rab_items 
        if item.get('volume', 0) > 0
    ]

    if items_with_record:
        for item in items_with_record:
            rab_id = item['id']
            detail = opname_map.get(rab_id, {})
            current_kasbon = detail.get("kasbon_amount", 0) or 0
            volume_actual = detail.get("volume_actual", 0) or 0
            rap_price = rap_price_map.get(rab_id, 0)
            nilai_opname = volume_actual * rap_price

            with st.expander(f"{item.get('code','')} - {item.get('description','')[:55]}", expanded=False):
                st.write(f"**Volume Opname:** {volume_actual:,.2f} {item.get('unit','')}")
                st.write(f"**Nilai Opname:** {format_rupiah(nilai_opname)}")

                # Edit form
                with st.form(key=f"edit_form_{rab_id}"):
                    new_volume = st.number_input(
                        "Volume Opname Baru", 
                        min_value=0.0, 
                        value=float(volume_actual), 
                        step=0.01,
                        key=f"vol_{rab_id}"
                    )
                    new_kasbon = st.number_input(
                        "Kasbonan (Rp)", 
                        min_value=0.0, 
                        value=float(current_kasbon), 
                        step=50000.0,
                        key=f"kasbon_{rab_id}"
                    )

                    submitted = st.form_submit_button("💾 Simpan Perubahan", type="primary")

                    if submitted:
                        if detail:
                            supabase.table("opname_sub_details").update({
                                "volume_actual": new_volume,
                                "kasbon_amount": new_kasbon
                            }).eq("id", detail["id"]).execute()
                        else:
                            supabase.table("opname_sub_details").insert({
                                "period_id": current_period_id,
                                "rab_item_id": rab_id,
                                "volume_actual": new_volume,
                                "kasbon_amount": new_kasbon
                            }).execute()
                        
                        st.success("Data berhasil diperbarui!")
                        st.rerun()

        # Ringkasan Total Kasbon
        total_kasbon_per_item = sum(d.get("kasbon_amount", 0) or 0 for d in opname_details)
        st.metric("Total Kasbon per Item (Periode Ini)", format_rupiah(total_kasbon_per_item))

        if st.button("📋 Lihat Laporan Kasbon Detail"):
            st.write("### Daftar Kasbon per Item")
            kasbon_list = []
            for item in rab_items:
                d = opname_map.get(item['id'], {})
                k = d.get("kasbon_amount", 0) or 0
                if k > 0:
                    kasbon_list.append({
                        "Kode": item.get("code", ""),
                        "Uraian": item.get("description", ""),
                        "Kasbon (Rp)": k
                    })
            
            if kasbon_list:
                import pandas as pd
                df = pd.DataFrame(kasbon_list)
                st.dataframe(df, use_container_width=True)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Laporan Kasbon (CSV)", 
                    csv, 
                    f"Kasbon_OpnameSub_Periode_{current_period_id}.csv"
                )
            else:
                st.info("Belum ada kasbon yang diinput.")
    else:
        st.info("Belum ada item RAB dengan volume di proyek ini.")