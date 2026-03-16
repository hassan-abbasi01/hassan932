from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')
db = client.snipx

print("\n" + "="*60)
print("ACTIVE USERS ANALYSIS")
print("="*60)

today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

# Get all activity logs from today
all_logs_today = list(db.activity_logs.find({
    'timestamp': {'$gte': today_start}
}))

print(f"\nTotal activity logs today: {len(all_logs_today)}")

# Categorize by user_type
user_type_counts = {}
for log in all_logs_today:
    ut = log.get('user_type', 'unknown')
    user_type_counts[ut] = user_type_counts.get(ut, 0) + 1

print(f"\nActivity by type:")
for ut, count in user_type_counts.items():
    print(f"  - {ut}: {count} activities")

# Get unique user IDs for 'user' type only
unique_users = db.activity_logs.distinct('user_id', {
    'timestamp': {'$gte': today_start},
    'user_type': 'user'
})

unique_admins = db.activity_logs.distinct('user_id', {
    'timestamp': {'$gte': today_start},
    'user_type': 'admin'
})

print(f"\n" + "="*60)
print(f"DASHBOARD SHOWS: {len(unique_users)} Active Users Today")
print("="*60)

print(f"\nUnique regular users active: {len(unique_users)}")
if unique_users:
    print("User IDs:")
    for uid in unique_users:
        user = db.users.find_one({'_id': uid})
        if user:
            name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
            email = user.get('email', 'N/A')
            print(f"  - {name or 'No name'} ({email})")

print(f"\nUnique admins active: {len(unique_admins)}")
if unique_admins:
    print("Admin IDs:")
    for aid in unique_admins:
        admin = db.admins.find_one({'_id': aid})
        if admin:
            print(f"  - {admin.get('email', 'N/A')}")

print(f"\n💡 ANSWER TO YOUR QUESTION:")
print(f"   '{len(unique_users)} Active User(s) Today' refers to:")
print(f"   - Regular USERS (not admins)")
print(f"   - Who performed any action logged in activity_logs")
print(f"   - With user_type='user'")
print(f"   - Since midnight today")
print(f"\n   Admin logins ARE NOT counted in this number!")
print(f"   Admins are tracked separately.")
print("="*60 + "\n")
