# =====================================================
# utils/ahsp_helper.py
# Helper functions untuk Database AHSP Level 3
# =====================================================

from utils.supabase_client import get_supabase
from typing import Optional, List, Dict, Any

supabase = get_supabase()


def get_all_ahsp_items() -> List[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_all_ahsp_items: {e}")
        return []


def get_ahsp_item_by_id(ahsp_item_id: int) -> Optional[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select("*").eq("id", ahsp_item_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error get_ahsp_item_by_id: {e}")
        return None


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


def get_price_breakdown(ahsp_item_id: int) -> Dict[str, float]:
    try:
        response = supabase.rpc("get_ahsp_price_breakdown", {"p_ahsp_item_id": ahsp_item_id}).execute()
        return response.data[0] if response.data else {"material_cost": 0, "labor_cost": 0, "equipment_cost": 0, "total_cost": 0}
    except Exception as e:
        print(f"Error get_price_breakdown: {e}")
        return {"material_cost": 0, "labor_cost": 0, "equipment_cost": 0, "total_cost": 0}


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


def get_ahsp_by_division(division_name: str) -> List[Dict]:
    try:
        response = supabase.table("v_ahsp_items").select("*").eq("division_name", division_name).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_ahsp_by_division: {e}")
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


# =====================================================
# FUNGSI BARU untuk integrasi dengan RAB
# =====================================================

def get_ahsp_for_selection() -> List[Dict]:
    """
    Mengambil data AHSP yang siap dipilih untuk ditambahkan ke RAB.
    Hanya mengambil field yang dibutuhkan.
    """
    try:
        response = supabase.table("v_ahsp_items").select(
            "id, code, description, unit, calculated_unit_price, stored_unit_price, division_name"
        ).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error get_ahsp_for_selection: {e}")
        return []
