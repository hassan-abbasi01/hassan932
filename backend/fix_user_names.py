from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['snipx']

# Update users with missing names
db.users.update_one(
    {'email': '221053@students.au.edu.pk'}, 
    {'$set': {'firstName': 'Student', 'lastName': 'User'}}
)

db.users.update_one(
    {'email': 'hd2107862@gmail.com'}, 
    {'$set': {'firstName': 'Demo', 'lastName': 'Account'}}
)

db.users.update_one(
    {'email': 'demo@snipx.com'}, 
    {'$set': {'firstName': 'Demo', 'lastName': 'User'}}
)

print('✓ Updated user names')

# List all users now
print('\n=== UPDATED USERS ===\n')
users = list(db.users.find({}, {'email': 1, 'firstName': 1, 'lastName': 1}))

for i, user in enumerate(users, 1):
    print(f"{i}. {user.get('firstName', 'N/A')} {user.get('lastName', 'N/A')} - {user.get('email')}")

print(f"\n✅ All {len(users)} users ready to view in admin dashboard!")
