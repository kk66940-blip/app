from utils.supabase_client import get_supabase
import hashlib

supabase = get_supabase()

# Password baru yang mau kamu pakai
new_password = "admin123"          # ← GANTI INI KALAU MAU PASSWORD LAIN

new_hash = hashlib.sha256(new_password.encode()).hexdigest()

# Update kedua user sekaligus
users_to_update = ["admin", "ekur"]

for username in users_to_update:
    res = supabase.table("users")\
        .update({"password": new_hash})\
        .eq("username", username)\
        .execute()
    
    if res.data:
        print(f"✅ Password untuk '{username}' berhasil diupdate!")
    else:
        print(f"❌ Gagal update '{username}'")

print(f"\n🔑 Hash yang disimpan: {new_hash}")
print(f"Password yang bisa dipakai: {new_password}")