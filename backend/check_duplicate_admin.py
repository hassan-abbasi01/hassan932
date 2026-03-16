"""
Check if admin@snipx.com exists in both users and admins collections
"""
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['snipx_video_editor']

users_collection = db['users']
admins_collection = db['admins']

print("\n" + "="*60)
print("CHECKING FOR DUPLICATE ADMIN ACCOUNTS")
print("="*60)

# Check users collection
user_admin = users_collection.find_one({"email": "admin@snipx.com"})
if user_admin:
    print("\n❌ PROBLEM FOUND:")
    print(f"   admin@snipx.com exists in USERS collection")
    print(f"   User ID: {user_admin.get('_id')}")
    print(f"   Created: {user_admin.get('created_at', 'Unknown')}")
else:
    print("\n✅ admin@snipx.com NOT in users collection (good)")

# Check admins collection
admin_admin = admins_collection.find_one({"email": "admin@snipx.com"})
if admin_admin:
    print(f"\n✅ admin@snipx.com exists in ADMINS collection (good)")
    print(f"   Admin ID: {admin_admin.get('_id')}")
    print(f"   Role: {admin_admin.get('role', 'Unknown')}")
else:
    print("\n❌ admin@snipx.com NOT in admins collection (bad)")

print("\n" + "="*60)
if user_admin and admin_admin:
    print("SOLUTION: Delete admin@snipx.com from users collection")
    print("Run: python fix_duplicate_admin.py")
elif not admin_admin:
    print("SOLUTION: Create admin@snipx.com in admins collection")
    print("Run: python init_db.py")
else:
    print("✅ Everything is correct!")
print("="*60 + "\n")

client.close()
