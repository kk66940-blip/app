"""
scripts/check_users_table.py
Utilitas debug: lihat nama kolom tabel users.
Jalankan: python scripts/check_users_table.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.supabase_client import get_supabase


def main():
    supabase = get_supabase()
    res = supabase.table("users").select("*").limit(1).execute()
    if res.data:
        print("Kolom pada tabel users:")
        for key in res.data[0].keys():
            print(f"  • {key}")
    else:
        print("❌ Tabel users kosong atau tidak bisa diakses.")


if __name__ == "__main__":
    main()
