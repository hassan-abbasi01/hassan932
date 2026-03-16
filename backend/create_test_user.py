"""
Create a test user in the database
"""
from pymongo import MongoClient
import bcrypt
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['snipx']

users_collection = db['users']

print("\n" + "="*60)
print("CREATING TEST USER")
print("="*60)

# Check if test user already exists
existing_user = users_collection.find_one({"email": "test@example.com"})

if existing_user:
    print("\n✅ Test user already exists:")
    print(f"   Email: test@example.com")
    print(f"   Name: {existing_user.get('first_name', '')} {existing_user.get('last_name', '')}")
else:
    # Create test user
    user_password = "password123"
    password_hash = bcrypt.hashpw(user_password.encode('utf-8'), bcrypt.gensalt())
    
    user_data = {
        "email": "test@example.com",
        "password_hash": password_hash.decode('utf-8'),
        "first_name": "Test",
        "last_name": "User",
        "created_at": datetime.utcnow(),
        "is_active": True,
        "email_verified": True
    }
    
    result = users_collection.insert_one(user_data)
    
    print("\n✅ Test user created successfully!")
    print(f"   Email: test@example.com")
    print(f"   Password: password123")
    print(f"   User ID: {result.inserted_id}")

print("="*60 + "\n")
