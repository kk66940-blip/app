from utils.supabase_client import get_supabase

supabase = get_supabase()

print("🔍 DEBUG STRUKTUR TABLE USERS")
print("=" * 60)

# Ambil 1 baris untuk melihat kolom apa saja yang ada
res = supabase.table("users").select("*").limit(1).execute()

if res.data:
    user = res.data[0]
    print("✅ Kolom yang ada di table users:")
    for key in user.keys():
        print(f"   • {key} → {user[key]}")
else:
    print("❌ Table users kosong atau tidak bisa diakses!")

print("\n" + "=" * 60)
print("Kirimkan output ini ke saya supaya saya tahu nama kolom password yang benar.")