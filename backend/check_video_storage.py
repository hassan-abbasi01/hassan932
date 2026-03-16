from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client.snipx

print("\n" + "="*60)
print("VIDEO STORAGE CHECK")
print("="*60)

videos = list(db.videos.find({}).limit(5))

print(f"\nTotal videos in database: {db.videos.count_documents({})}")

if videos:
    print(f"\nSample of first 5 videos:")
    for idx, video in enumerate(videos, 1):
        title = video.get('title', 'N/A')
        filename = video.get('filename', 'N/A')
        file_size = video.get('file_size', None)
        duration = video.get('duration', None)
        
        print(f"\n{idx}. {title}")
        print(f"   Filename: {filename}")
        print(f"   File Size: {file_size} bytes" if file_size else f"   File Size: NOT SET ❌")
        print(f"   Duration: {duration}s" if duration else f"   Duration: NOT SET")

# Check how many videos have file_size
videos_with_size = db.videos.count_documents({'file_size': {'$exists': True, '$ne': None}})
videos_without_size = db.videos.count_documents({'$or': [
    {'file_size': {'$exists': False}},
    {'file_size': None}
]})

print(f"\n{'='*60}")
print(f"Videos WITH file_size: {videos_with_size}")
print(f"Videos WITHOUT file_size: {videos_without_size}")
print(f"{'='*60}\n")

if videos_without_size > 0:
    print("⚠️  ISSUE: Videos don't have file_size saved!")
    print("   This is why Total Storage shows 0B")
    print("\n💡 SOLUTION:")
    print("   - When uploading new videos, save file_size")
    print("   - For existing videos, calculate from file system")
else:
    print("✅ All videos have file_size data")
