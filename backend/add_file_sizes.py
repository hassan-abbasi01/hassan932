"""
Add file_size field to all videos in database by calculating from actual files
"""
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))
db = client.snipx

videos_collection = db.videos
uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')

print("\n" + "="*60)
print("ADDING FILE SIZES TO VIDEOS")
print("="*60)

videos = list(videos_collection.find())
updated_count = 0
missing_file_count = 0
total_size = 0

for video in videos:
    video_id = str(video['_id'])
    filename = video.get('filename', '')
    
    # Check if file_size already exists
    if video.get('file_size'):
        print(f"✓ Video {video_id[:8]}... already has file_size: {video['file_size']} bytes")
        total_size += video['file_size']
        continue
    
    # Try to find the file
    video_path = video.get('video_path', '')
    if not video_path:
        video_path = os.path.join(uploads_dir, filename)
    
    if os.path.exists(video_path):
        file_size = os.path.getsize(video_path)
        
        # Update in database
        videos_collection.update_one(
            {'_id': video['_id']},
            {'$set': {'file_size': file_size}}
        )
        
        print(f"✓ Updated {video_id[:8]}... - {filename}")
        print(f"  Size: {file_size / (1024*1024):.2f} MB")
        updated_count += 1
        total_size += file_size
    else:
        print(f"✗ File not found for {video_id[:8]}... ({filename})")
        # Set file_size to 0 for missing files
        videos_collection.update_one(
            {'_id': video['_id']},
            {'$set': {'file_size': 0}}
        )
        missing_file_count += 1

print("\n" + "="*60)
print(f"✅ Updated {updated_count} videos with file sizes")
print(f"⚠️  {missing_file_count} videos with missing files (set to 0)")
print(f"📊 Total storage: {total_size / (1024*1024*1024):.2f} GB")
print("="*60 + "\n")
