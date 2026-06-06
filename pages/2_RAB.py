import streamlit as st
from utils.supabase_client import get_supabase
from utils.helpers import format_rupiah
from datetime import datetime
from collections import defaultdict
from io import BytesIO

# ==================== IMPORT BARU ====================
from utils.ahsp_helper import get_ahsp_for_selection
from components.hierarchical_tree import display_rab_tree

# Export (Centralized)
from utils.export_utils import export_rab_excel, export_rab_pdf

supabase = get_supabase()
project_id = st.session_state.get("current_project_id")

st.header("📋 RAB - Rencana Anggaran Biaya")

if not project_id:
    st.warning("Pilih proyek terlebih dahulu di sidebar")
    st.stop()

# ==================== AMBIL DATA ====================
all_rab_items = supabase.table("rab_items")\
    .select("*")\
    .eq("project_id", project_id)\
    .order("level").order("sort_order").execute().data

# ==================== TRUE LIVE SEARCH ====================
st.markdown("### 🔍 Live Search (Update Langsung Saat Mengetik)")

search_term = st.text_input(
    "Ketik untuk mencari...",
    placeholder="Contoh: hebel, rangka, pasangan, A.1...",
    key="rab_live_search"
)

if search_term and search_term.strip() != "":
    search_lower = search_term.lower().strip()
    
    matched_ids = set()
    for item in all_rab_items:
        if search_lower in item.get('code', '').lower() or search_lower in item.get('description', '').lower():
            matched_ids.add(item['id'])
            current = item
            while current.get('parent_id'):
                matched_ids.add(current['parent_id'])
                current = next((x for x in all_rab_items if x['id'] == current['parent_id']), None)
                if current is None:
                    break

    filtered_items = [item for item in all_rab_items if item['id'] in matched_ids]
    match_count = len([i for i in filtered_items if search_lower in i.get('code','').lower() or search_lower in i.get('description','').lower()])
    st.success(f"✅ Ditemukan **{match_count} item** yang cocok dengan **'{search_term}'**")
else:
    filtered_items = all_rab_items

st.divider()

# ==================== TAMBAH ITEM BARU (LAMA) ====================
with st.expander("➕ Tambah Item BARU", expanded=False):
    col1, col2 = st.columns([1, 2])
    with col1:
        level = st.selectbox("Level", [0, 1, 2, 3], index=0)
        parent_options = ["Tidak ada (Main Item)"] + [f"{item['code']} - {item['description'][:40]}" for item in all_rab_items if item.get('level') == level-1]
        parent_choice = st.selectbox("Parent Item", parent_options)
    with col2:
        code = st.text_input("Kode Item", value="A.1")
        description = st.text_input("Uraian Pekerjaan", value="Pekerjaan ...")
    
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        volume = st.number_input("Volume", value=1.0, step=0.01)
        unit = st.text_input("Satuan", value="m³")
    with col_b:
        unit_price = st.number_input("Harga Satuan (Rp)", value=100000, step=1000)
    with col_c:
        sort_order = st.number_input("Urutan", value=1, step=1)
    
    if st.button("💾 Simpan Item BARU", type="primary"):
        parent_id = None
        if parent_choice != "Tidak ada (Main Item)":
            parent_code = parent_choice.split(" - ")[0]
            parent = next((item for item in all_rab_items if item['code'] == parent_code), None)
            if parent:
                parent_id = parent['id']
        
        new_item = {
            "project_id": project_id, "code": code, "description": description,
            "volume": volume, "unit": unit, "unit_price": unit_price,
            "level": level, "parent_id": parent_id, "sort_order": sort_order
        }
        supabase.table("rab_items").insert(new_item).execute()
        st.success("✅ Item berhasil ditambahkan!")
        st.rerun()

st.divider()

# ==================== TAMBAH ITEM DARI AHSP (FITUR BARU) ====================
with st.expander("➕ Tambah Item dari Database AHSP", expanded=False):
    st.caption("Pilih item dari database AHSP. Harga akan otomatis terisi dari perhitungan terbaru.")

    ahsp_items = get_ahsp_for_selection()

    if not ahsp_items:
        st.warning("Belum ada data di Database AHSP. Silakan isi dulu di halaman Database AHSP.")
    else:
        # Format pilihan
        ahsp_options = {
            f"{item['code']} - {item['description'][:65]} ({item.get('unit', '-')})": item 
            for item in ahsp_items
        }

        selected_label = st.selectbox(
            "Pilih Item AHSP",
            options=list(ahsp_options.keys()),
            key="ahsp_select_rab"
        )

        selected_ahsp = ahsp_options[selected_label]

        # Preview
        col1, col2, col3 = st.columns(3)
        col1.metric("Kode", selected_ahsp['code'])
        col2.metric("Satuan", selected_ahsp.get('unit', '-'))
        col3.metric("Harga dari AHSP", f"Rp {selected_ahsp.get('calculated_unit_price', 0):,.0f}")

        st.divider()

        # Form input
        with st.form("form_add_from_ahsp"):
            col_a, col_b = st.columns(2)
            with col_a:
                level = st.selectbox("Level", [0, 1, 2, 3], index=0, key="ahsp_level")
                volume = st.number_input("Volume", value=1.0, step=0.01, key="ahsp_volume")
            with col_b:
                sort_order = st.number_input("Urutan", value=1, step=1, key="ahsp_sort")
                parent_options = ["Tidak ada (Main Item)"] + [
                    f"{item['code']} - {item['description'][:40]}" 
                    for item in all_rab_items if item.get('level') == level - 1
                ]
                parent_choice = st.selectbox("Parent Item", parent_options, key="ahsp_parent")

            if st.form_submit_button("💾 Simpan ke RAB dari AHSP", type="primary", use_container_width=True):
                try:
                    parent_id = None
                    if parent_choice != "Tidak ada (Main Item)":
                        parent_code = parent_choice.split(" - ")[0]
                        parent = next((item for item in all_rab_items if item['code'] == parent_code), None)
                        if parent:
                            parent_id = parent['id']

                    new_item = {
                        "project_id": project_id,
                        "code": selected_ahsp['code'],
                        "description": selected_ahsp['description'],
                        "volume": volume,
                        "unit": selected_ahsp.get('unit', ''),
                        "unit_price": selected_ahsp.get('calculated_unit_price', 0) or selected_ahsp.get('stored_unit_price', 0),
                        "level": level,
                        "parent_id": parent_id,
                        "sort_order": sort_order
                    }

                    supabase.table("rab_items").insert(new_item).execute()
                    st.success(f"✅ Item dari AHSP berhasil ditambahkan: {selected_ahsp['code']}")
                    st.rerun()

                except Exception as e:
                    st.error(f"Gagal menyimpan: {str(e)}")

st.divider()

# ==================== STRUKTUR RAB ====================
st.subheader("Struktur RAB")

# ==================== TAMPILAN HIRARKIS (Menggunakan Komponen Reusable) ====================
st.subheader("Struktur RAB")

def handle_rab_edit(item):
    st.session_state.edit_item = item
    st.rerun()

def handle_rab_delete(item):
    st.session_state.delete_item = item
    st.rerun()

if filtered_items:
    display_rab_tree(
        items=filtered_items,
        on_edit=handle_rab_edit,
        on_delete=handle_rab_delete,
        search_term=search_term,
        key_prefix="rab_page"
    )
else:
    if search_term:
        st.warning(f"Tidak ada item yang cocok dengan **'{search_term}'**")
    else:
        st.info("Belum ada data RAB.")

# ==================== EDIT FORM ====================
if "edit_item" in st.session_state:
    item = st.session_state.edit_item
    st.subheader(f"✏️ Edit Item: {item['code']}")
    
    with st.form("edit_rab_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_code = st.text_input("Kode", value=item.get('code', ''))
            new_desc = st.text_input("Uraian Pekerjaan", value=item.get('description', ''))
            new_level = st.selectbox("Level", [0,1,2,3], index=item.get('level', 0))
        with col2:
            new_volume = st.number_input("Volume", value=float(item.get('volume', 0)), step=0.01)
            new_unit = st.text_input("Satuan", value=item.get('unit', ''))
            new_price = st.number_input("Harga Satuan (Rp)", value=float(item.get('unit_price', 0)), step=1000)

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.form_submit_button("💾 Simpan Perubahan", type="primary", use_container_width=True):
                try:
                    supabase.table("rab_items").update({
                        "code": new_code,
                        "description": new_desc,
                        "level": new_level,
                        "volume": new_volume,
                        "unit": new_unit,
                        "unit_price": new_price,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", item['id']).execute()
                    
                    st.success("✅ Item berhasil diperbarui!")
                    del st.session_state.edit_item
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col_btn2:
            if st.form_submit_button("Batal", use_container_width=True):
                del st.session_state.edit_item
                st.rerun()

st.divider()

# ==================== EXPORT (Centralized via utils/export_utils.py) ====================


def export_rab_pdf_hierarchical(rab_items, project_name):
    """Export RAB ke PDF dengan tampilan rapih multi-level hierarchy (matching Excel quality)"""
    if not rab_items:
        st.warning("Tidak ada data RAB untuk diekspor.")
        return

    children_map = build_tree(rab_items)

    all_ids = {item['id'] for item in rab_items}
    root_items = [item for item in rab_items if item.get('parent_id') is None or item.get('parent_id') not in all_ids]
    root_items = sorted(root_items, key=lambda x: (x.get('sort_order', 0), x.get('id', 0)))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=1.2*cm, leftMargin=1.2*cm,
                            topMargin=1.2*cm, bottomMargin=1.2*cm)

    styles = getSampleStyleSheet()
    normal = ParagraphStyle('Normal', parent=styles['Normal'], fontSize=8, leading=10)
    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor('#0d6efd'))
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white, leading=11)
    subtotal_style = ParagraphStyle('Subtotal', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold', leading=10)
    grand_style = ParagraphStyle('Grand', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', leading=11)

    elements = []
    elements.append(Paragraph("RENCANA ANGGARAN BIAYA (RAB)", title_style))
    elements.append(Paragraph(f"<b>Proyek:</b> {project_name}", normal))
    elements.append(Paragraph(f"<b>Tanggal:</b> {datetime.now().strftime('%d %B %Y')}", normal))
    elements.append(Spacer(1, 0.25*cm))

    table_data = [["No", "Uraian Pekerjaan", "Sat", "Vol", "Harga (Rp)", "Jumlah (Rp)"]]
    
    # Track row indices for styling
    header_row_indices = []      # rows that are section headers (green)
    subtotal_row_indices = []    # rows that are SUBTOTAL (yellow)
    grand_total_row_index = None

    grand_total = 0
    current_row = 1  # start after header row (row 0)

    def add_to_pdf(node, path, children_map):
        nonlocal grand_total, current_row
        node_id = node['id']
        children = children_map.get(node_id, [])
        has_children = len(children) > 0
        current_no = ".".join(map(str, path))

        if has_children:
            # Header row (will be styled green)
            header_row_indices.append(current_row)
            table_data.append(["", Paragraph(f"▶ {node.get('description', '')}", header_style), "", "", "", ""])
            current_row += 1
            
            sub_total = 0
            for idx, child in enumerate(children, 1):
                new_path = path + [idx]
                child_total = add_to_pdf(child, new_path, children_map)
                sub_total += child_total
            
            # Subtotal row
            subtotal_row_indices.append(current_row)
            table_data.append([
                "", 
                Paragraph("<b>SUBTOTAL</b>", subtotal_style), 
                "", "", "", 
                Paragraph(f"<b>{sub_total:,.0f}</b>", subtotal_style)
            ])
            current_row += 1
            return sub_total
        else:
            vol = node.get('volume', 0) or 0
            price = node.get('unit_price', 0) or 0
            total = vol * price
            grand_total += total

            table_data.append([
                current_no,
                Paragraph(f"    {node.get('description', '')}", normal),
                node.get('unit', ''),
                f"{vol:,.2f}",
                f"{price:,.0f}",
                f"{total:,.0f}"
            ])
            current_row += 1
            return total

    for idx, root in enumerate(root_items, 1):
        add_to_pdf(root, [idx], children_map)

    # Grand Total
    grand_total_row_index = current_row
    table_data.append([
        "", 
        Paragraph("<b>GRAND TOTAL</b>", grand_style), 
        "", "", "", 
        Paragraph(f"<b>{grand_total:,.0f}</b>", grand_style)
    ])

    # Column widths (balanced for readability)
    col_widths = [1.0*cm, 8.0*cm, 1.1*cm, 1.7*cm, 2.6*cm, 2.8*cm]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Build dynamic style commands
    style_commands = [
        # Header row (blue)
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0, 1), (-1, -1), 7.5),
        ('ALIGN', (3, 1), (3, -1), 'RIGHT'),  # Vol
        ('ALIGN', (4, 1), (5, -1), 'RIGHT'),  # Harga & Jumlah
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]

    # Green background for all header rows (▶ section headers)
    for row_idx in header_row_indices:
        style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#28a745')))
        style_commands.append(('TEXTCOLOR', (0, row_idx), (-1, row_idx), colors.white))
        style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

    # Yellow background + bold for SUBTOTAL rows
    for row_idx in subtotal_row_indices:
        style_commands.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#fff3cd')))
        style_commands.append(('FONTNAME', (0, row_idx), (-1, row_idx), 'Helvetica-Bold'))

    # Green background for GRAND TOTAL
    if grand_total_row_index:
        style_commands.append(('BACKGROUND', (0, grand_total_row_index), (-1, grand_total_row_index), colors.HexColor('#d4edda')))
        style_commands.append(('FONTNAME', (0, grand_total_row_index), (-1, grand_total_row_index), 'Helvetica-Bold'))
        style_commands.append(('FONTSIZE', (0, grand_total_row_index), (-1, grand_total_row_index), 9))

    t.setStyle(TableStyle(style_commands))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)

    filename = f"RAB_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    st.download_button(
        label="⬇️ Download PDF (Rapih & Multi-Level)",
        data=buffer,
        file_name=filename,
        mime="application/pdf",
        use_container_width=True
    )
    st.success("✅ Export PDF sudah lebih rapih dengan warna header hijau, subtotal kuning, dan formatting profesional!")


# ==================== TOMBOL EXPORT ====================
project_name = st.session_state.get("selected_project_name", "Proyek")

col1, col2 = st.columns(2)
with col1:
    if st.button("📊 Export ke Excel (Format Profesional)", type="primary", use_container_width=True):
        try:
            buffer = export_rab_excel(all_rab_items, project_name)
            filename = f"RAB_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(
                label="⬇️ Download Excel RAB",
                data=buffer,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error export Excel: {e}")

with col2:
    if st.button("🖨️ Export ke PDF", type="primary", use_container_width=True):
        try:
            buffer = export_rab_pdf(all_rab_items, project_name)
            filename = f"RAB_{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            st.download_button(
                label="⬇️ Download PDF RAB",
                data=buffer,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error export PDF: {e}")


# ==================== IMPORT RAB DARI EXCEL ====================
st.divider()
st.subheader("📥 Import RAB dari Excel")

with st.expander("📋 Petunjuk Format Excel yang Didukung", expanded=False):
    st.markdown("""
    **Kolom yang wajib ada:**
    - `Level` → 0 = Main Item, 1 = Sub Item, 2 = Detail, dst.
    - `Uraian Pekerjaan`
    - `Satuan`
    - `Volume`
    - `Harga Satuan`

    **Kolom opsional:**
    - `Kode`

    **Contoh:**
    | Level | Kode   | Uraian Pekerjaan              | Satuan | Volume | Harga Satuan |
    |-------|--------|-------------------------------|--------|--------|--------------|
    | 0     | A.1    | Pekerjaan Struktur            | -      | 0      | 0            |
    | 1     | A.1.1  | Beton Bertulang               | m³     | 120    | 1.250.000    |
    | 2     | A.1.1.1| Beton K-300                   | m³     | 85     | 1.350.000    |
    """)

uploaded_file = st.file_uploader(
    "Pilih file Excel (.xlsx)", 
    type=["xlsx"], 
    key="import_rab_excel"
)

if uploaded_file:
    try:
        import pandas as pd
        
        # Baca file Excel, gunakan baris ke-4 sebagai header (header=3 karena 0-indexed)
        df = pd.read_excel(uploaded_file, header=3)
        
        # Normalisasi nama kolom (lebih fleksibel)
        df.columns = [str(c).strip().lower().replace("(", "").replace(")", "").replace("rp", "").strip() for c in df.columns]
        
        # Mapping kolom yang fleksibel
        column_mapping = {}
        for col in df.columns:
            if col in ['level', 'lvl']:
                column_mapping[col] = 'level'
            elif col in ['uraian pekerjaan', 'uraian', 'deskripsi', 'description', 'pekerjaan']:
                column_mapping[col] = 'description'
            elif col in ['satuan', 'unit', 'sat']:
                column_mapping[col] = 'unit'
            elif col in ['volume', 'vol']:
                column_mapping[col] = 'volume'
            elif col in ['harga satuan', 'harga', 'unit price', 'hargasatuan']:
                column_mapping[col] = 'unit_price'
            elif col in ['kode', 'code', 'kd']:
                column_mapping[col] = 'code'
        
        df = df.rename(columns=column_mapping)
        
        required_cols = ['level', 'description', 'unit', 'volume', 'unit_price']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            st.error(f"Kolom yang wajib tidak ditemukan: {missing}")
            st.info(f"Kolom yang terbaca: {list(df.columns)}")
            st.stop()
        
        st.success(f"✅ Berhasil membaca **{len(df)} baris** data dari Excel.")
        
        # Preview
        with st.expander("Lihat Preview Data (10 baris pertama)", expanded=True):
            st.dataframe(df.head(10), use_container_width=True)
        
        # Pilihan Mode Import
        import_mode = st.radio(
            "Pilih Mode Import:",
            options=[
                "➕ Tambah Data Baru (Append)",
                "🔄 Ganti Semua Data (Replace All)"
            ],
            index=0,
            horizontal=True
        )

        if st.button("🚀 Mulai Import", type="primary", use_container_width=True):
            try:
                # === MODE REPLACE ALL ===
                if import_mode == "🔄 Ganti Semua Data (Replace All)":
                    try:
                        existing_rab = supabase.table("rab_items") \
                            .select("id") \
                            .eq("project_id", project_id) \
                            .execute().data
                        rab_ids = [item['id'] for item in existing_rab]

                        if rab_ids:
                            supabase.table("opname_details").delete().in_("rab_item_id", rab_ids).execute()
                            supabase.table("opname_sub_details").delete().in_("rab_item_id", rab_ids).execute()
                            supabase.table("rap_items").delete().in_("rab_item_id", rab_ids).execute()

                        supabase.table("rab_items").delete().eq("project_id", project_id).execute()
                        st.info("✅ Data RAB lama beserta RAP & Opname terkait berhasil dihapus.")
                    except Exception as delete_error:
                        st.error(f"Gagal menghapus data lama: {str(delete_error)}")
                        st.stop()

                # === PROSES IMPORT (berlaku untuk kedua mode) ===
                inserted = 0
                parent_stack = {}

                for idx, row in df.iterrows():
                    level = int(row.get('level', 0))
                    code = str(row.get('code', '')).strip() if 'code' in row else ''
                    description = str(row.get('description', '')).strip()
                    unit = str(row.get('unit', '')).strip()
                    volume = float(row.get('volume', 0) or 0)
                    unit_price = float(row.get('unit_price', 0) or 0)

                    if not description:
                        continue

                    parent_id = parent_stack.get(level - 1) if level > 0 else None

                    new_item = {
                        "project_id": project_id,
                        "level": level,
                        "code": code,
                        "description": description,
                        "unit": unit,
                        "volume": volume,
                        "unit_price": unit_price,
                        "parent_id": parent_id,
                        "sort_order": idx + 1
                    }

                    res = supabase.table("rab_items").insert(new_item).execute()
                    new_id = res.data[0]['id']
                    parent_stack[level] = new_id

                    keys_to_remove = [k for k in parent_stack if k > level]
                    for k in keys_to_remove:
                        del parent_stack[k]

                    inserted += 1

                st.success(f"✅ Berhasil import **{inserted} item** RAB!")
                st.balloons()
                st.rerun()

            except Exception as e:
                st.error(f"Gagal melakukan import: {str(e)}")
                    
    except Exception as e:
        st.error(f"Gagal membaca file Excel: {str(e)}")
