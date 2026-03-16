"""
List all users and admins to debug login issue
"""
from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['snipx']

users_collection = db['users']
admins_collection = db['admins']

print("\n" + "="*60)
print("ALL USERS IN DATABASE")
print("="*60)

users = list(users_collection.find({}, {"_id": 1, "email": 1, "firstName": 1, "lastName": 1}))
if users:
    for user in users:
        print(f"  - {user.get('email')} (ID: {user.get('_id')})")
        print(f"    Name: {user.get('firstName')} {user.get('lastName')}")
else:
    print("  (No users found)")

print("\n" + "="*60)
print("ALL ADMINS IN DATABASE")
print("="*60)

admins = list(admins_collection.find({}, {"_id": 1, "email": 1, "role": 1, "name": 1}))
if admins:
    for admin in admins:
        print(f"  - {admin.get('email')} (ID: {admin.get('_id')})")
        print(f"    Name: {admin.get('name')}, Role: {admin.get('role')}")
else:
    print("  (No admins found)")

print("\n" + "="*60)
print("SPECIFIC CHECK: admin@snipx.com")
print("="*60)

user_admin = users_collection.find_one({"email": "admin@snipx.com"})
admin_admin = admins_collection.find_one({"email": "admin@snipx.com"})

print(f"  In users collection: {'YES ❌' if user_admin else 'NO ✅'}")
print(f"  In admins collection: {'YES ✅' if admin_admin else 'NO ❌'}")

if user_admin and admin_admin:
    print("\n❌ DUPLICATE FOUND - Deleting from users...")
    users_collection.delete_one({"email": "admin@snipx.com"})
    print("✅ Deleted admin@snipx.com from users collection")

print("="*60 + "\n")

client.close()
