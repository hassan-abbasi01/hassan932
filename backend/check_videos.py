from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))
db = client.snipx

# Check videos
videos = list(db.videos.find())
print(f"Total videos in DB: {len(videos)}")
for v in videos:
    print(f"  - ID: {v.get('_id')}")
    print(f"    Filename: {v.get('filename')}")
    print(f"    User ID: {v.get('user_id')}")
    print(f"    Status: {v.get('status')}")
    print()

# Check users
users = list(db.users.find())
print(f"\nTotal users in DB: {len(users)}")
for u in users:
    print(f"  - ID: {u.get('_id')}")
    print(f"    Email: {u.get('email')}")
