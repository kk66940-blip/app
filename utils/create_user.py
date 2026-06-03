from utils.supabase_client import get_supabase

supabase = get_supabase()

data = {
    "username": "admin",
    "password": "admin123",      # GANTI INI SESUKA KAMU
    "full_name": "Administrator",
    "role": "admin"
}

res = supabase.table("users").insert(data).execute()

if res.data:
    print("✅ User berhasil dibuat!")
    print("Username :", data["username"])
    print("Password :", data["password"])
else:
    print("❌ Gagal membuat user")