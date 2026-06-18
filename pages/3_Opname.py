import sys
import uuid
from pathlib import Path
from io import BytesIO
from datetime import datetime
from collections import defaultdict

import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

# Path fix untuk deployment (Streamlit Cloud, dll.)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase
from components.hierarchical_tree import display_opname_tree

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")


# ==================== FUNGSI INVOICE ====================
def generate_invoice_pdf(period_id, period_label, kasbon_value):
    try:
        if not project_id:
            st.error("Project ID tidak ditemukan")
            return

        project_res = supabase.table("projects").select("*").eq("id", project_id).execute()
        project = project_res.data[0] if project_res.data else {}

        rab_items = supabase.table("rab_items")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("level").order("sort_order").execute().data

        opname_details = supabase.table("opname_details")\
            .select("rab_item_id, actual_volume")\
            .eq("period_id", period_id).execute().data

        actual_map = {d['rab_item_id']: d['actual_volume'] for d in opname_details}

        children_map = defaultdict(list)
        for item in rab_items:
            children_map[item.get('parent_id')].append(item)

        main_items = [item for item in rab_items 
                      if (item.get('level', 0) == 0 or 
                          (item.get('volume', 0) == 0 and "pekerjaan" in item.get('description', '').lower()))
                      and any(actual_map.get(child['id'], 0) > 0 for child in children_map.get(item['id'], []))]

        if not main_items:
            st.warning("Tidak ada data opname di periode ini.")
            return

        subtotal = 0
        table_data = [["No", "Uraian Pekerjaan", "Sat", "Vol", "Harga (Rp)", "Nilai (Rp)"]]
        item_no = 1

        for main_item in main_items:
            main_id = main_item['id']
            table_data.append(["", f"▶ {main_item.get('description', '')}", "", "", "", ""])

            for child in children_map.get(main_id, []):
                if actual_map.get(child['id'], 0) > 0:
                    vol = actual_map[child['id']]
                    price = child.get('unit_price', 0) or 0
                    nilai = vol * price
                    subtotal += nilai

                    table_data.append([
                        str(item_no),
                        f"    {item_no}. {child.get('description', '')}",
                        child.get('unit', ''),
                        f"{vol:,.2f}",
                        f"{price:,.0f}",
                        f"{nilai:,.0f}"
                    ])
                    item_no += 1

        table_data.append(["", "SUBTOTAL", "", "", "", f"{subtotal:,.0f}"])

        ppn_rate = project.get('ppn_rate', 11.0)
        retensi_rate = project.get('retensi_rate', 5.0)
        ppn = subtotal * (ppn_rate / 100)
        retensi = subtotal * (retensi_rate / 100)
        grand_total = subtotal + ppn - retensi - kasbon_value

        filename = f"Invoice_{project_name}_{period_label[:25]}.pdf".replace(" ", "_")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)

        styles = getSampleStyleSheet()
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9)
        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', 
                                     textColor=colors.HexColor('#0d6efd'))

        elements = []
        from utils.company import get_company_settings, build_letterhead, build_bank_footer
        _company = get_company_settings()
        build_letterhead(elements, _company, styles)
        elements.append(Paragraph("INVOICE OPNAME", title_style))
        elements.append(Paragraph(f"<b>Proyek:</b> {project_name}", normal))
        elements.append(Paragraph(f"<b>Periode:</b> {period_label}", normal))
        elements.append(Paragraph(f"<b>Tanggal:</b> {datetime.now().strftime('%d %B %Y')}", normal))
        elements.append(Spacer(1, 0.4*cm))

        t = Table(table_data, colWidths=[1*cm, 7*cm, 1.5*cm, 2*cm, 3*cm, 3*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e7f1ff')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.4*cm))

        summary_data = [
            ["Keterangan", "Jumlah (Rp)"],
            ["Subtotal Opname", f"{subtotal:,.0f}"],
            [f"PPN ({ppn_rate}%)", f"{ppn:,.0f}"],
            [f"Retensi ({retensi_rate}%)", f"- {retensi:,.0f}"],
            ["Potongan Kasbon", f"- {kasbon_value:,.0f}"],
            ["GRAND TOTAL", f"{grand_total:,.0f}"]
        ]

        summary_table = Table(summary_data, colWidths=[10*cm, 6*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4edda')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
        ]))
        elements.append(summary_table)

        elements.append(Spacer(1, 0.8*cm))
        build_bank_footer(elements, _company, styles)
        elements.append(Spacer(1, 0.6*cm))
        elements.append(Paragraph("Hormat kami,", normal))
        elements.append(Spacer(1, 1.2*cm))
        elements.append(Paragraph("_________________________", normal))
        elements.append(Paragraph("Direktur / Pengelola Proyek", normal))

        doc.build(elements)
        buffer.seek(0)

        st.download_button("⬇️ Download Invoice PDF", data=buffer, file_name=filename, 
                           mime="application/pdf", use_container_width=True)
        st.success("Invoice berhasil dibuat!")

    except Exception as e:
        st.error(f"Error membuat invoice: {str(e)}")


# ==================== UI UTAMA ====================
st.header("📝 Opname - Harga dari RAB")

if not project_id:
    st.warning("Pilih proyek di sidebar")
    st.stop()

# PERIODE
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    periods = supabase.table("opname_periods")\
        .select("id, period_no, opname_date, description, kasbon")\
        .eq("project_id", project_id).order("period_no").execute().data

    period_options = {f"Periode {p['period_no']} - {p['description']} ({p['opname_date']})": p['id'] for p in periods}

    if period_options:
        selected_period_label = st.selectbox("Pilih Periode Opname", list(period_options.keys()))
        current_period_id = period_options[selected_period_label]
    else:
        st.warning("Belum ada periode.")
        current_period_id = None

with col2:
    with st.expander("➕ Periode Baru", expanded=False):
        with st.form("new_period"):
            period_no = st.number_input("Nomor Periode", min_value=1, value=1)
            opname_date = st.date_input("Tanggal Opname", datetime.now())
            description = st.text_input("Keterangan", f"Opname Minggu ke-{period_no}")
            if st.form_submit_button("Buat Periode"):
                supabase.table("opname_periods").insert({
                    "project_id": project_id, "period_no": period_no,
                    "opname_date": str(opname_date), "description": description, "kasbon": 0
                }).execute()
                st.success("Periode berhasil dibuat!")
                st.rerun()

with col3:
    if current_period_id:
        kasbon_data = supabase.table("opname_periods").select("kasbon").eq("id", current_period_id).execute().data
        current_kasbon = kasbon_data[0]["kasbon"] if kasbon_data else 0
        kasbon = st.number_input("Kasbon (Rp)", min_value=0, value=int(current_kasbon), step=100000)
        if st.button("Simpan Kasbon", use_container_width=True):
            supabase.table("opname_periods").update({"kasbon": kasbon}).eq("id", current_period_id).execute()
            st.success("Kasbon disimpan!")

# TOMBOL AKSI
col_a, col_b, col_c = st.columns(3)
with col_a:
    if st.button("💾 Simpan Opname", type="primary", use_container_width=True):
        st.success("Data berhasil disimpan!")
with col_b:
    if st.button("🧾 Buat Invoice", type="primary", use_container_width=True):
        if current_period_id:
            generate_invoice_pdf(current_period_id, selected_period_label, kasbon)
        else:
            st.warning("Pilih periode terlebih dahulu")
with col_c:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

st.divider()

# ==================== TREE OPNAME ====================
st.subheader("Struktur Opname")

if not current_period_id:
    st.info("Pilih atau buat periode terlebih dahulu")
    st.stop()

rab_items = supabase.table("rab_items")\
    .select("*").eq("project_id", project_id).order("level").order("sort_order").execute().data

opname_details = supabase.table("opname_details")\
    .select("*").eq("period_id", current_period_id).execute().data

# ==================== DATA & HANDLER ====================
actual_map = {d['rab_item_id']: d.get('actual_volume', 0) for d in opname_details}
photo_map = {d['rab_item_id']: d.get('photo_url') for d in opname_details}

# Total opname dari periode-periode SEBELUM periode aktif (untuk hitung sisa).
# Karena opname disimpan per-periode (increment), sisa = RAB - jumlah semua
# periode sebelumnya.
prev_opname_map = {}
try:
    _all_periods = supabase.table("opname_periods").select("id, period_no").eq(
        "project_id", project_id).execute().data or []
    _cur = next((p for p in _all_periods if p["id"] == current_period_id), None)
    _cur_no = _cur["period_no"] if _cur else None
    if _cur_no is not None:
        _prev_ids = [p["id"] for p in _all_periods if (p.get("period_no") or 0) < _cur_no]
        if _prev_ids:
            _prev_rows = supabase.table("opname_details").select(
                "rab_item_id, actual_volume").in_("period_id", _prev_ids).execute().data or []
            for r in _prev_rows:
                rid = r["rab_item_id"]
                prev_opname_map[rid] = (prev_opname_map.get(rid, 0) or 0) + (r.get("actual_volume", 0) or 0)
except Exception:
    prev_opname_map = {}

def handle_save_opname(item, new_actual, uploaded_file, new_kasbon=0):
    """Callback untuk menyimpan volume + foto.

    new_kasbon diterima agar cocok dengan signature yang dipanggil komponen
    tree, tapi tidak dipakai di Opname utama (kasbon per-item hanya relevan
    untuk Opname Sub).
    """
    try:
        rab_id = item['id']
        existing = supabase.table("opname_details") \
            .select("id").eq("period_id", current_period_id).eq("rab_item_id", rab_id).execute()

        data = {
            "period_id": current_period_id,
            "rab_item_id": rab_id,
            "actual_volume": new_actual
        }

        if uploaded_file:
            file_ext = uploaded_file.name.split(".")[-1].lower()
            unique_filename = f"{uuid.uuid4()}.{file_ext}"
            file_path = f"opname/{current_period_id}/{unique_filename}"

            supabase.storage.from_("opname-photos").upload(
                path=file_path,
                file=uploaded_file.getvalue(),
                file_options={"content-type": uploaded_file.type}
            )
            public_url = supabase.storage.from_("opname-photos").get_public_url(file_path)
            data["photo_url"] = public_url

        if existing.data:
            supabase.table("opname_details").update(data) \
                .eq("period_id", current_period_id).eq("rab_item_id", rab_id).execute()
            st.success("✅ Volume + Foto berhasil diupdate!")
        else:
            supabase.table("opname_details").insert(data).execute()
            st.success("✅ Volume + Foto berhasil disimpan!")

        st.rerun()
    except Exception as e:
        st.error(f"Gagal menyimpan: {str(e)}")


# ==================== TAMPILAN HIRARKIS (Komponen Reusable) ====================
display_opname_tree(
    items=rab_items,
    actual_map=actual_map,
    on_save=handle_save_opname,
    show_photo_upload=True,
    key_prefix="opname_main",
    prev_opname_map=prev_opname_map,
)

# Tampilkan foto yang sudah ada (opsional, jika ingin ditampilkan di luar komponen)
# Bisa dikembangkan lebih lanjut jika diperlukan preview foto global.

# ==================== FITUR EDIT VOLUME (Opname Utama) ====================
st.divider()
st.subheader("✏️ Edit Volume Opname per Item")

if current_period_id:
    opname_details = supabase.table("opname_details") \
        .select("*") \
        .eq("period_id", current_period_id).execute().data
    opname_map = {d['rab_item_id']: d for d in opname_details}

    items_with_data = [item for item in rab_items if item.get('volume', 0) > 0]

    if items_with_data:
        for item in items_with_data:
            rab_id = item['id']
            detail = opname_map.get(rab_id, {})
            current_volume = detail.get("actual_volume", 0) or 0

            with st.expander(f"{item.get('code','')} - {item.get('description','')[:55]}", expanded=False):
                st.write(f"**Volume Saat Ini:** {current_volume:,.2f} {item.get('unit','')}")

                with st.form(key=f"edit_opname_{rab_id}"):
                    new_volume = st.number_input(
                        "Volume Opname Baru", 
                        min_value=0.0, 
                        value=float(current_volume), 
                        step=0.01,
                        key=f"vol_edit_{rab_id}"
                    )

                    if st.form_submit_button("💾 Simpan Perubahan Volume", type="primary"):
                        if detail:
                            supabase.table("opname_details").update({
                                "actual_volume": new_volume
                            }).eq("id", detail["id"]).execute()
                        else:
                            supabase.table("opname_details").insert({
                                "period_id": current_period_id,
                                "rab_item_id": rab_id,
                                "actual_volume": new_volume
                            }).execute()
                        
                        st.success("Volume berhasil diperbarui!")
                        st.rerun()
    else:
        st.info("Belum ada item RAB dengan volume di proyek ini.")