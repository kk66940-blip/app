def format_rupiah(value):
    if value is None:
        value = 0
    return f"Rp {float(value):,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_rupiah(text):
    if not text:
        return 0.0
    text = text.replace("Rp", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(text)
    except:
        return 0.0

def next_rab_code(all_items, parent_id, level):
    """Hasilkan kode RAB berikutnya secara otomatis.

    Skema:
      - Main item (parent_id None): A.1, A.2, A.3, ... (huruf 'A' tetap, angka naik)
      - Sub item: kode induk + '.' + nomor urut berikutnya di dalam induk itu
        (mis. induk A.1 -> A.1.1, A.1.2; induk A.1.1 -> A.1.1.1, ...)

    Parameters
    ----------
    all_items : list[dict]  semua rab_items proyek (punya 'code','parent_id','id').
    parent_id : int | None  id induk; None untuk main item.
    level     : int         level item (untuk fallback).

    Mengembalikan string kode. Aman bila data kosong.
    """
    def _last_number(code):
        """Ambil angka terakhir dari kode seperti 'A.1.2' -> 2; gagal -> 0."""
        if not code:
            return 0
        tail = str(code).strip().split(".")[-1]
        try:
            return int(tail)
        except (ValueError, TypeError):
            return 0

    if parent_id is None:
        # Main item: cari kode main (parent_id None) dengan prefix 'A.'
        mains = [it for it in all_items if it.get("parent_id") is None]
        max_n = 0
        for it in mains:
            code = str(it.get("code", "") or "")
            # hanya hitung yang berpola 'A.<angka>'
            if code.upper().startswith("A.") and code.count(".") == 1:
                max_n = max(max_n, _last_number(code))
        return f"A.{max_n + 1}"

    # Sub item: temukan kode induk, lalu cari nomor terbesar di antara saudara
    parent = next((it for it in all_items if it.get("id") == parent_id), None)
    parent_code = str(parent.get("code", "")).strip() if parent else ""

    siblings = [it for it in all_items if it.get("parent_id") == parent_id]
    max_n = 0
    for sib in siblings:
        max_n = max(max_n, _last_number(sib.get("code", "")))

    if parent_code:
        return f"{parent_code}.{max_n + 1}"
    # Fallback bila induk tak punya kode: pakai level
    return f"{max_n + 1}"
