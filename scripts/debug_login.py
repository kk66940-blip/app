from utils.supabase_client import get_supabase
import hashlib

supabase = get_supabase()

print("🔍 DEBUG LOGIN - Isi Table Users")
print("=" * 50)

# Ambil semua user
res = supabase.table("users").select("*").execute()

if not res.data:
    print("❌ Table users KOSONG atau tidak ditemukan!")
else:
    for user in res.data:
        print(f"Username     : {user.get('username')}")
        print(f"Password Hash: {user.get('password')}")
        print(f"Full Name    : {user.get('full_name')}")
        print(f"Role         : {user.get('role')}")
        print("-" * 40)

# Test hash "admin123"
test_hash = hashlib.sha256("admin123".encode()).hexdigest()
print(f"\n🔑 SHA-256 dari 'admin123' = {test_hash}")
print("Cocokkan hash ini dengan hash di database kamu.")