"""
utils/company.py
Helper terpusat untuk data perusahaan (tabel company_settings) dan pembuatan
kop surat (letterhead) untuk dokumen PDF (invoice & SPK).

Tabel company_settings bersifat global (satu baris untuk seluruh aplikasi),
bukan per-proyek. Pola: ambil baris pertama; jika belum ada, kembalikan default.
"""

from io import BytesIO

from utils.supabase_client import get_supabase

# Default aman bila tabel belum diisi.
_DEFAULTS = {
    "company_name": "PT. Konstruksi Indonesia",
    "address": "",
    "phone": "",
    "email": "",
    "npwp": "",
    "logo_path": "",
    "footer": "",
    "bank_name": "",
    "account_number": "",
    "account_holder": "",
}


def get_company_settings() -> dict:
    """Ambil data perusahaan (baris pertama). Kembalikan default bila kosong."""
    try:
        supabase = get_supabase()
        res = supabase.table("company_settings").select("*").limit(1).execute()
        if res.data:
            # Gabungkan dengan default agar key yang null tetap ada.
            merged = {**_DEFAULTS, **{k: v for k, v in res.data[0].items() if v is not None}}
            merged["id"] = res.data[0].get("id")
            return merged
    except Exception:
        pass
    return {**_DEFAULTS, "id": None}


def save_company_settings(data: dict) -> bool:
    """Simpan data perusahaan (update bila ada baris, insert bila belum)."""
    supabase = get_supabase()
    payload = {k: data.get(k, "") for k in _DEFAULTS}
    existing = supabase.table("company_settings").select("id").limit(1).execute().data
    if existing:
        supabase.table("company_settings").update(payload).eq("id", existing[0]["id"]).execute()
    else:
        supabase.table("company_settings").insert(payload).execute()
    return True


def _try_load_logo(logo_path: str):
    """Coba muat logo dari URL untuk reportlab Image. Kembalikan Image atau None.

    Aman gagal: jika path kosong, bukan URL, atau gagal diunduh, kembalikan None
    agar PDF tetap dibuat tanpa logo (tidak merusak dokumen).
    """
    if not logo_path or not str(logo_path).startswith(("http://", "https://")):
        return None
    try:
        import urllib.request
        from reportlab.platypus import Image
        from reportlab.lib.units import cm

        with urllib.request.urlopen(logo_path, timeout=5) as resp:
            data = resp.read()
        img = Image(BytesIO(data))
        # Skala ke tinggi maksimal ~1.8cm menjaga rasio.
        max_h = 1.8 * cm
        if img.imageHeight > 0:
            ratio = img.imageWidth / img.imageHeight
            img.drawHeight = max_h
            img.drawWidth = max_h * ratio
        return img
    except Exception:
        return None


def build_letterhead(elements: list, company: dict, styles) -> None:
    """Tambahkan blok kop surat ke daftar `elements` reportlab (in-place).

    Parameters
    ----------
    elements : list   daftar flowable reportlab yang sedang dibangun.
    company  : dict   hasil get_company_settings().
    styles   : dict-like  hasil getSampleStyleSheet() atau styles kustom.
    """
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    name_style = ParagraphStyle(
        "CompanyName", parent=styles["Normal"], fontSize=14,
        fontName="Helvetica-Bold", textColor=colors.HexColor("#0d6efd"),
    )
    info_style = ParagraphStyle(
        "CompanyInfo", parent=styles["Normal"], fontSize=8.5,
        textColor=colors.HexColor("#333333"), leading=11,
    )

    # Susun baris info perusahaan
    info_lines = [f"<b>{company.get('company_name', '')}</b>"]
    if company.get("address"):
        info_lines.append(company["address"])
    contact = []
    if company.get("phone"):
        contact.append(f"Telp: {company['phone']}")
    if company.get("email"):
        contact.append(company["email"])
    if contact:
        info_lines.append(" &nbsp;|&nbsp; ".join(contact))
    if company.get("npwp"):
        info_lines.append(f"NPWP: {company['npwp']}")

    info_para = Paragraph("<br/>".join(info_lines), info_style)
    logo = _try_load_logo(company.get("logo_path", ""))

    if logo is not None:
        # Dua kolom: logo kiri, info kanan
        head_table = Table([[logo, info_para]], colWidths=[3 * cm, 14 * cm])
        head_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(head_table)
    else:
        elements.append(Paragraph(company.get("company_name", ""), name_style))
        elements.append(info_para)

    # Garis pemisah
    elements.append(Spacer(1, 0.15 * cm))
    line = Table([[""]], colWidths=[17.5 * cm], rowHeights=[2])
    line.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#0d6efd"))]))
    elements.append(line)
    elements.append(Spacer(1, 0.4 * cm))


def build_bank_footer(elements: list, company: dict, styles) -> None:
    """Tambahkan footer rekening bank (untuk invoice) bila datanya ada."""
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer

    if not company.get("bank_name") and not company.get("account_number"):
        return
    foot_style = ParagraphStyle(
        "BankFooter", parent=styles["Normal"], fontSize=8.5,
        textColor=colors.HexColor("#333333"), leading=11,
    )
    parts = ["<b>Pembayaran ditransfer ke:</b>"]
    if company.get("bank_name"):
        parts.append(f"Bank: {company['bank_name']}")
    if company.get("account_number"):
        parts.append(f"No. Rekening: {company['account_number']}")
    if company.get("account_holder"):
        parts.append(f"Atas Nama: {company['account_holder']}")
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("<br/>".join(parts), foot_style))
