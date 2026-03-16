"""
Quick check for admin@snipx.com in both collections
"""
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['snipx_video_editor']

users_collection = db['users']
admins_collection = db['admins']

print("\n" + "="*60)
print("CHECKING admin@snipx.com")
print("="*60)

user_admin = users_collection.find_one({"email": "admin@snipx.com"})
admin_admin = admins_collection.find_one({"email": "admin@snipx.com"})

print(f"\nIn USERS collection: {'YES ❌' if user_admin else 'NO ✅'}")
print(f"In ADMINS collection: {'YES ✅' if admin_admin else 'NO ❌'}")

if user_admin:
    print(f"\n❌ PROBLEM: admin@snipx.com found in USERS collection!")
    print(f"   ID: {user_admin.get('_id')}")
    print(f"   Name: {user_admin.get('firstName')} {user_admin.get('lastName')}")

if admin_admin:
    print(f"\n✅ GOOD: admin@snipx.com found in ADMINS collection")
    print(f"   ID: {admin_admin.get('_id')}")
    print(f"   Name: {admin_admin.get('name')}")
    print(f"   Role: {admin_admin.get('role')}")

print("="*60 + "\n")

client.close()
