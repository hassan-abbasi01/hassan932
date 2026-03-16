from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')
db = client.snipx

print("\n" + "="*60)
print("ACTIVE USERS TODAY EXPLANATION")
print("="*60)

today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

print(f"\nToday started at: {today_start}")
print(f"Current time: {datetime.utcnow()}")

# Check activity logs
print("\n📊 CHECKING ACTIVITY LOGS...")

# Get all logins today
all_logins_today = list(db.activity_logs.find({
    'timestamp': {'$gte': today_start},
    'action': {'$in': ['login', 'admin_login']}
}))

print(f"\nTotal logins today: {len(all_logins_today)}")

# Count by type
user_logins = [log for log in all_logins_today if log.get('user_type') == 'user']
admin_logins = [log for log in all_logins_today if log.get('user_type') == 'admin']

print(f"\n👤 USER logins: {len(user_logins)}")
for log in user_logins:
    user_id = log.get('user_id', 'N/A')
    action = log.get('action', 'N/A')
    time = log.get('timestamp', 'N/A')
    print(f"   - {user_id} at {time}")

print(f"\n👑 ADMIN logins: {len(admin_logins)}")
for log in admin_logins:
    admin_id = log.get('user_id', 'N/A')
    action = log.get('action', 'N/A')
    time = log.get('timestamp', 'N/A')
    print(f"   - {admin_id} at {time}")

# Get unique user IDs (excluding admins)
unique_users = db.activity_logs.distinct('user_id', {
    'timestamp': {'$gte': today_start},
    'user_type': 'user'
})

print(f"\n" + "="*60)
print(f"DASHBOARD SHOWS: {len(unique_users)} Active Users Today")
print("="*60)
print("\n💡 EXPLANATION:")
print("   - Active Users = UNIQUE regular users who logged in today")
print("   - Does NOT count admin logins")
print("   - Only counts user_type='user'")
print("   - If you see 1, it means 1 regular user logged in today")
print("   - Admin logins are tracked separately")
print("\n" + "="*60 + "\n")
