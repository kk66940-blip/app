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


# ==================== KALKULATOR VOLUME (BOQ) ====================
# Jenis perhitungan volume yang didukung untuk input dimensi RAB.
VOLUME_CALC_TYPES = {
    "volume": {"label": "Volume (P×L×T)", "fields": ["panjang", "lebar", "tinggi"], "unit_hint": "m³"},
    "luas":   {"label": "Luas (P×L)",     "fields": ["panjang", "lebar"],           "unit_hint": "m²"},
    "panjang":{"label": "Panjang (m')",   "fields": ["panjang"],                    "unit_hint": "m'"},
    "besi":   {"label": "Besi (panjang × kg/m)", "fields": ["panjang", "berat_per_m"], "unit_hint": "kg"},
    "unit":   {"label": "Jumlah/Unit",    "fields": ["jumlah"],                     "unit_hint": "bh"},
}


def calc_segment_result(calc_type: str, seg: dict) -> float:
    """Hitung hasil satu segmen berdasarkan jenis perhitungan.

    seg berisi key seperti panjang/lebar/tinggi/berat_per_m/jumlah (angka).
    'jumlah' (multiplier) berlaku untuk semua tipe; default 1 bila tak ada.
    """
    def g(k):
        try:
            return float(seg.get(k) or 0)
        except (ValueError, TypeError):
            return 0.0

    mult = g("jumlah") if seg.get("jumlah") not in (None, "") else 1.0
    if mult == 0:
        mult = 1.0

    if calc_type == "volume":
        base = g("panjang") * g("lebar") * g("tinggi")
    elif calc_type == "luas":
        base = g("panjang") * g("lebar")
    elif calc_type == "panjang":
        base = g("panjang")
    elif calc_type == "besi":
        base = g("panjang") * g("berat_per_m")
    elif calc_type == "unit":
        # untuk unit, 'jumlah' ADALAH nilainya, bukan multiplier
        return g("jumlah")
    else:
        base = 0.0
    return base * mult


def calc_total_volume(segments: list) -> float:
    """Jumlahkan hasil semua segmen. Tiap segmen punya 'tipe' & dimensinya."""
    if not segments:
        return 0.0
    total = 0.0
    for seg in segments:
        total += calc_segment_result(seg.get("tipe", "volume"), seg)
    return round(total, 4)


# ==================== BOBOT PEKERJAAN (%) ====================
def compute_rab_weights(items: list) -> dict:
    """Hitung bobot tiap item RAB = (nilai item / grand total) * 100.

    Nilai item = volume * unit_price. Grand total = jumlah nilai SEMUA item
    yang punya nilai (umumnya item daun/detail; item grup biasanya volume 0).

    Mengembalikan dict {item_id: bobot_persen}. Bila grand total 0 -> semua 0.
    """
    def _val(it):
        return (it.get("volume", 0) or 0) * (it.get("unit_price", 0) or 0)

    grand = sum(_val(it) for it in items)
    if grand <= 0:
        return {it.get("id"): 0.0 for it in items}
    return {it.get("id"): (_val(it) / grand * 100.0) for it in items}
