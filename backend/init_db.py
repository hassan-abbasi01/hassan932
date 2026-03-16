"""
Initialize MongoDB database with default admin account
"""
from pymongo import MongoClient
import bcrypt
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['snipx']

admins_collection = db['admins']

print("\n" + "="*60)
print("INITIALIZING ADMIN ACCOUNT")
print("="*60)

# Check if admin already exists
existing_admin = admins_collection.find_one({"email": "admin@snipx.com"})

if existing_admin:
    print("\n✅ Admin account already exists:")
    print(f"   Email: admin@snipx.com")
    print(f"   Role: {existing_admin.get('role', 'super_admin')}")
    print(f"   Active: {existing_admin.get('is_active', True)}")
else:
    # Create admin account
    admin_password = "admin123"
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt())
    
    admin_data = {
        "email": "admin@snipx.com",
        "password_hash": password_hash.decode('utf-8'),
        "role": "super_admin",
        "name": "System Administrator",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "permissions": {
            "manage_users": True,
            "view_analytics": True,
            "manage_content": True,
            "manage_settings": True
        }
    }
    
    result = admins_collection.insert_one(admin_data)
    
    print("\n✅ Admin account created successfully!")
    print(f"   Email: admin@snipx.com")
    print(f"   Password: admin123")
    print(f"   Role: super_admin")
    print(f"   Admin ID: {result.inserted_id}")
    print("\n⚠️  IMPORTANT: Change the default password after first login!")

print("="*60 + "\n")

client.close()
