from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['snipx']

print('=== USERS IN DATABASE ===\n')
users = list(db.users.find({}, {'email': 1, 'firstName': 1, 'lastName': 1, 'created_at': 1}))

for i, user in enumerate(users, 1):
    print(f"{i}. Email: {user.get('email', 'N/A')}")
    print(f"   Name: {user.get('firstName', 'N/A')} {user.get('lastName', 'N/A')}")
    print(f"   Created: {user.get('created_at', 'N/A')}")
    print(f"   ID: {user['_id']}")
    print()

print(f"Total users: {len(users)}")
