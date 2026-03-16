from pymongo import MongoClient
from datetime import datetime

client = MongoClient('mongodb://localhost:27017/')

print("\n" + "="*60)
print("DATABASE STRUCTURE CHECK")
print("="*60)

# Check both databases
for db_name in ['snipx', 'snipx_video_editor']:
    print(f"\n📁 DATABASE: {db_name}")
    print("-" * 60)
    
    db = client[db_name]
    collections = db.list_collection_names()
    
    print(f"Collections found: {', '.join(collections)}")
    
    # Check users collection
    if 'users' in collections:
        user_count = db.users.count_documents({})
        print(f"\n👥 USERS in {db_name}: {user_count}")
        
        if user_count > 0:
            print("\nUser Details:")
            for idx, user in enumerate(db.users.find({}), 1):
                fname = user.get('firstName', 'N/A')
                lname = user.get('lastName', 'N/A')
                email = user.get('email', 'N/A')
                created = user.get('created_at', 'N/A')
                print(f"  {idx}. {fname} {lname} - {email}")
    else:
        print(f"\n❌ NO 'users' collection in {db_name}")
    
    # Check admins collection
    if 'admins' in collections:
        admin_count = db.admins.count_documents({})
        print(f"\n👑 ADMINS in {db_name}: {admin_count}")
        
        if admin_count > 0:
            print("\nAdmin Details:")
            for idx, admin in enumerate(db.admins.find({}), 1):
                email = admin.get('email', 'N/A')
                role = admin.get('role', 'N/A')
                print(f"  {idx}. {email} - {role}")
    
    # Check videos collection
    if 'videos' in collections:
        video_count = db.videos.count_documents({})
        print(f"\n🎥 VIDEOS in {db_name}: {video_count}")

print("\n" + "="*60)
print("RECOMMENDATION")
print("="*60)
print("✅ PRIMARY DATABASE: snipx (backend uses this)")
print("⚠️  SECONDARY DATABASE: snipx_video_editor (unused/legacy)")
print("\nYour backend connects to 'snipx' database.")
print("The 'snipx_video_editor' is an old database that can be ignored.")
print("="*60 + "\n")
