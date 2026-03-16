"""Debug admin dashboard stats issues"""
from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient('mongodb://localhost:27017')
db = client['snipx']

print("=" * 60)
print("ADMIN DASHBOARD DEBUG")
print("=" * 60)

# 1. Total users
total_users = db.users.count_documents({})
print(f"\n1. Total users: {total_users}")

# 2. Total videos
total_videos = db.videos.count_documents({})
print(f"2. Total videos: {total_videos}")

# 3. Check video fields - what fields exist?
sample_video = db.videos.find_one()
if sample_video:
    print(f"\n3. Sample video fields: {list(sample_video.keys())}")
    print(f"   filename: {sample_video.get('filename')}")
    print(f"   uploaded_at: {sample_video.get('uploaded_at')} (type: {type(sample_video.get('uploaded_at')).__name__})")
    print(f"   created_at: {sample_video.get('created_at')} (type: {type(sample_video.get('created_at')).__name__})")
    print(f"   file_size: {sample_video.get('file_size')} (type: {type(sample_video.get('file_size')).__name__})")
    print(f"   duration: {sample_video.get('duration')} (type: {type(sample_video.get('duration')).__name__})")
    print(f"   enhanced: {sample_video.get('enhanced')} (type: {type(sample_video.get('enhanced')).__name__})")
    print(f"   status: {sample_video.get('status')}")
else:
    print("3. NO VIDEOS FOUND!")

# 4. Check uploaded_at field across videos
today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
print(f"\n4. Today start (UTC): {today_start}")

# Count with uploaded_at
count_uploaded_at = db.videos.count_documents({'uploaded_at': {'$gte': today_start}})
print(f"   Videos with uploaded_at >= today: {count_uploaded_at}")

# Count with created_at
count_created_at = db.videos.count_documents({'created_at': {'$gte': today_start}})
print(f"   Videos with created_at >= today: {count_created_at}")

# Check how many videos have uploaded_at vs created_at
has_uploaded_at = db.videos.count_documents({'uploaded_at': {'$exists': True}})
has_created_at = db.videos.count_documents({'created_at': {'$exists': True}})
print(f"   Videos with 'uploaded_at' field: {has_uploaded_at}")
print(f"   Videos with 'created_at' field: {has_created_at}")

# 5. Check enhanced field
has_enhanced_true = db.videos.count_documents({'enhanced': True})
has_enhanced_field = db.videos.count_documents({'enhanced': {'$exists': True}})
print(f"\n5. Videos with enhanced=True: {has_enhanced_true}")
print(f"   Videos with 'enhanced' field: {has_enhanced_field}")

# Check if status is used instead
has_status_completed = db.videos.count_documents({'status': 'completed'})
has_status_enhanced = db.videos.count_documents({'status': 'enhanced'})
print(f"   Videos with status='completed': {has_status_completed}")
print(f"   Videos with status='enhanced': {has_status_enhanced}")

# 6. Check duration field
has_duration = db.videos.count_documents({'duration': {'$exists': True, '$gt': 0}})
has_duration_field = db.videos.count_documents({'duration': {'$exists': True}})
print(f"\n6. Videos with duration > 0: {has_duration}")
print(f"   Videos with 'duration' field: {has_duration_field}")

# Sample durations
durations = list(db.videos.find({'duration': {'$exists': True}}, {'duration': 1, 'filename': 1}).limit(5))
for d in durations:
    print(f"   - {d.get('filename')}: duration={d.get('duration')}")

# 7. Active users today - check activity_logs
total_logs = db.activity_logs.count_documents({})
print(f"\n7. Total activity logs: {total_logs}")
logs_today = db.activity_logs.count_documents({'timestamp': {'$gte': today_start}})
print(f"   Logs today: {logs_today}")

# Check if there's a last_active field on users
sample_user = db.users.find_one()
if sample_user:
    print(f"\n8. Sample user fields: {list(sample_user.keys())}")
    print(f"   last_active: {sample_user.get('last_active')}")
    print(f"   last_login: {sample_user.get('last_login')}")

# 9. Check file_size across all videos
pipeline = [{'$group': {'_id': None, 'total': {'$sum': '$file_size'}}}]
storage = list(db.videos.aggregate(pipeline))
print(f"\n9. Total storage: {storage}")

# Check videos with 0 or null file_size
zero_size = db.videos.count_documents({'$or': [{'file_size': 0}, {'file_size': None}, {'file_size': {'$exists': False}}]})
print(f"   Videos with 0/null/missing file_size: {zero_size}")

# 10. Show 3 most recent videos
print(f"\n10. Most recent videos:")
recent = list(db.videos.find({}).sort([('_id', -1)]).limit(3))
for v in recent:
    print(f"   - {v.get('filename')}: status={v.get('status')}, enhanced={v.get('enhanced')}, "
          f"uploaded_at={v.get('uploaded_at')}, created_at={v.get('created_at')}, "
          f"duration={v.get('duration')}, file_size={v.get('file_size')}, user_id={v.get('user_id')}")

# 11. Check what the admin videos endpoint returns
print(f"\n11. Admin videos listing check:")
admin_videos = list(db.videos.find({}).sort([('_id', -1)]).limit(5))
for v in admin_videos:
    print(f"   ID={v['_id']}, user_id={v.get('user_id')} (type={type(v.get('user_id')).__name__})")

client.close()
