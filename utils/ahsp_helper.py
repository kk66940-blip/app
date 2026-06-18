# =====================================================
# utils/ahsp_helper.py
# Helper functions untuk Database AHSP Level 3 (Full Version)
# =====================================================

from utils.supabase_client import get_supabase
from typing import Optional, List, Dict, Any

supabase = get_supabase()


# ==================== AHSP ITEMS ====================
def get_all_ahsp_items() -> List[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_all_ahsp_items: {e}")
        return []

def get_ahsp_for_selection() -> List[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select(
            "id, code, description, unit, calculated_unit_price, stored_unit_price, division_name"
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_ahsp_for_selection: {e}")
        return []

def search_ahsp_items(search_term: str) -> List[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select("*").or_(
            f"code.ilike.%{search_term}%,description.ilike.%{search_term}%"
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error search_ahsp_items: {e}")
        return []

def get_ahsp_by_division(division_name: str) -> List[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select("*").eq("division_name", division_name).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_ahsp_by_division: {e}")
        return []


# ==================== RESOURCES ====================
def get_all_resources() -> List[Dict]:
    """Ambil semua resource (Material, Upah, Peralatan)"""
    try:
        response = supabase.table("ahsp_resources").select("*").order("resource_type").order("name").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_all_resources: {e}")
        return []

def get_resources_by_type(resource_type: str) -> List[Dict]:
    try:
        response = supabase.table("ahsp_resources").select("*").eq("resource_type", resource_type).order("name").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_resources_by_type: {e}")
        return []

def add_resource(code: str, name: str, resource_type: str, unit: str, current_price: float) -> bool:
    try:
        supabase.table("ahsp_resources").insert({
            "code": code,
            "name": name,
            "resource_type": resource_type,
            "unit": unit,
            "current_price": current_price
        }).execute()
        return True
    except Exception as e:
        print(f"Error add_resource: {e}")
        return False


# ==================== ITEM RESOURCES (KOMPOSISI) ====================
def get_item_composition(ahsp_item_id: int) -> List[Dict]:
    """Ambil komposisi resource dari satu item AHSP"""
    try:
        response = supabase.table("ahsp_item_resources") \
            .select("id, resource_id, coefficient, ahsp_resources(name, unit, resource_type, current_price)") \
            .eq("ahsp_item_id", ahsp_item_id).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_item_composition: {e}")
        return []

def save_item_composition(ahsp_item_id: int, compositions: List[Dict]) -> bool:
    """
    Simpan komposisi baru untuk item AHSP.
    compositions = [{"resource_id": 1, "coefficient": 0.5}, ...]
    """
    try:
        # Hapus komposisi lama
        supabase.table("ahsp_item_resources").delete().eq("ahsp_item_id", ahsp_item_id).execute()
        
        # Insert komposisi baru
        if compositions:
            data = [{"ahsp_item_id": ahsp_item_id, **comp} for comp in compositions]
            supabase.table("ahsp_item_resources").insert(data).execute()
        
        # Update harga setelah komposisi berubah
        supabase.rpc("update_ahsp_unit_price", {"p_ahsp_item_id": ahsp_item_id}).execute()
        return True
    except Exception as e:
        print(f"Error save_item_composition: {e}")
        return False


# ==================== UPDATE HARGA ====================
def calculate_unit_price(ahsp_item_id: int) -> float:
    try:
        response = supabase.rpc("calculate_ahsp_unit_price", {"p_ahsp_item_id": ahsp_item_id}).execute()
        return float(response.data) if response.data else 0.0
    except Exception as e:
        print(f"Error calculate_unit_price: {e}")
        return 0.0

def update_unit_price(ahsp_item_id: int) -> bool:
    try:
        supabase.rpc("update_ahsp_unit_price", {"p_ahsp_item_id": ahsp_item_id}).execute()
        return True
    except Exception as e:
        print(f"Error update_unit_price: {e}")
        return False

def update_all_ahsp_prices() -> int:
    try:
        items = get_all_ahsp_items()
        updated_count = 0
        for item in items:
            if update_unit_price(item["id"]):
                updated_count += 1
        return updated_count
    except Exception as e:
        print(f"Error update_all_ahsp_prices: {e}")
        return 0

def get_price_breakdown(ahsp_item_id: int) -> Dict[str, float]:
    try:
        response = supabase.rpc("get_ahsp_price_breakdown", {"p_ahsp_item_id": ahsp_item_id}).execute()
        return response.data[0] if response.data else {"material_cost": 0, "labor_cost": 0, "equipment_cost": 0, "total_cost": 0}
    except Exception as e:
        print(f"Error get_price_breakdown: {e}")
        return {"material_cost": 0, "labor_cost": 0, "equipment_cost": 0, "total_cost": 0}


# ==================== EXPLODE AHSP -> ITEM RAB + CHILD ====================
def explode_ahsp_to_rab(ahsp_item: Dict, kubikasi: float) -> Dict:
    """Pecah satu item AHSP menjadi struktur induk + child untuk RAB.

    - Induk: volume 0, harga 0 (nilainya = penjumlahan child, hindari dobel-hitung).
    - Tiap resource 'material' -> child: volume = koefisien * kubikasi,
      harga satuan = current_price resource.
    - Semua 'labor' + 'equipment' -> digabung 1 child "Jasa (Upah & Alat)":
      volume = 1, harga = Σ(koefisien * current_price) * kubikasi.

    Mengembalikan dict:
      { "parent": {description, unit, ...}, "children": [ {description, unit, volume, unit_price, resource_type}, ... ] }

    Aman: bila item tak punya komposisi, children = [] (pemanggil bisa menangani).
    """
    ahsp_id = ahsp_item.get("id")
    comp = get_item_composition(ahsp_id) if ahsp_id else []

    children = []
    jasa_total_per_unit = 0.0  # Σ(koef * harga) untuk labor+equipment, per 1 unit induk

    for c in comp:
        res = c.get("ahsp_resources") or {}
        rtype = res.get("resource_type")
        coeff = float(c.get("coefficient") or 0)
        price = float(res.get("current_price") or 0)
        name = res.get("name", "")
        unit = res.get("unit", "")

        if rtype == "material":
            children.append({
                "description": name,
                "unit": unit,
                "volume": round(coeff * kubikasi, 4),
                "unit_price": price,
                "resource_type": "material",
            })
        else:  # labor / equipment -> dikumpulkan jadi Jasa
            jasa_total_per_unit += coeff * price

    if jasa_total_per_unit > 0:
        children.append({
            "description": "Jasa (Upah & Alat)",
            "unit": "ls",
            "volume": 1.0,
            "unit_price": round(jasa_total_per_unit * kubikasi, 2),
            "resource_type": "jasa",
        })

    parent = {
        "description": ahsp_item.get("description", ""),
        "unit": ahsp_item.get("unit", ""),
        "volume": 0,        # induk tidak bernilai sendiri
        "unit_price": 0,    # nilai = penjumlahan child
    }
    return {"parent": parent, "children": children}
