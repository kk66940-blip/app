import streamlit as st
from utils.supabase_client import get_supabase
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")
project_name = st.session_state.get("selected_project_name", "Proyek")

st.header("📝 SPK - Surat Perintah Kerja")
st.subheader(f"Proyek: {project_name}")

if not project_id:
    st.warning("Pilih proyek di sidebar terlebih dahulu")
    st.stop()

def generate_spk_pdf(spk_data, rap_items_list):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=9)
        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=16, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d6efd'))
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold')
        elements = []
        elements.append(Paragraph("SURAT PERINTAH KERJA (SPK)", title_style))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(f"<b>Nomor SPK:</b> {spk_data['spk_no']}", normal))
        elements.append(Paragraph(f"<b>Tanggal:</b> {spk_data['spk_date']}", normal))
        elements.append(Paragraph(f"<b>Tenggat Waktu:</b> {spk_data['deadline_date']}", normal))
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(f"<b>Penerima:</b> {spk_data['recipient_name']}", normal))
        if spk_data.get('recipient_contact'):
            elements.append(Paragraph(f"<b>Kontak:</b> {spk_data['recipient_contact']}", normal))
        elements.append(Spacer(1, 0.4*cm))
        table_data = [["No", "Uraian Pekerjaan", "Vol", "Harga (Rp)", "Total (Rp)"]]
        for idx, item in enumerate(rap_items_list, 1):
            table_data.append([str(idx), item.get('description', '')[:50], f"{item.get('volume_target', 0):,.2f}", f"{item.get('unit_price', 0):,.0f}", f"{item.get('total_value', 0):,.0f}"])
        t = Table(table_data, colWidths=[1*cm, 8*cm, 2*cm, 3*cm, 3*cm])
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')), ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 8), ('GRID', (0, 0), (-1, -1), 0.5, colors.grey), ('ALIGN', (2, 0), (-1, -1), 'RIGHT')]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))
        if spk_data.get('special_terms'):
            elements.append(Paragraph("<b>Syarat & Ketentuan:</b>", subtitle_style))
            elements.append(Paragraph(spk_data['special_terms'], normal))
            elements.append(Spacer(1, 0.3*cm))
        if spk_data.get('notes'):
            elements.append(Paragraph("<b>Catatan:</b>", subtitle_style))
            elements.append(Paragraph(spk_data['notes'], normal))
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("Hormat kami,", normal))
        elements.append(Spacer(1, 1.5*cm))
        elements.append(Paragraph("_________________________", normal))
        elements.append(Paragraph("Pemberi Perintah Kerja", normal))
        doc.build(elements)
        buffer.seek(0)
        st.download_button(label="⬇️ Download SPK PDF", data=buffer, file_name=f"{spk_data['spk_no']}.pdf", mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.error(f"Gagal membuat PDF: {str(e)}")

tab1, tab2 = st.tabs(["➕ Buat SPK Baru", "📋 Daftar SPK"])

with tab1:
    st.subheader("Buat SPK Baru")

    all_rap = supabase.table("rap_items") \
        .select("id, code, description, execution_price, unit, volume, parent_id") \
        .eq("project_id", project_id) \
        .execute().data

    sorted_rap = sorted(all_rap, key=lambda x: x.get('id', 0)) if all_rap else []

    main_items = [item for item in sorted_rap 
                  if (item.get('volume') == 0 or item.get('volume') is None) 
                  and "pekerjaan" in item.get('description', '').lower()]

    if main_items:
        main_options = {f"{item['
