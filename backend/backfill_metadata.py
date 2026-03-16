"""Backfill missing video metadata (file_size, duration) for existing videos"""
import os
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['snipx']

videos = list(db.videos.find({}))
print(f"Total videos in DB: {len(videos)}")

fixed_size = 0
fixed_duration = 0
fixed_file_size = 0

for video in videos:
    updates = {}
    vid = video['_id']
    filepath = video.get('filepath', '')
    
    # Fix missing 'size' field from actual file
    size = video.get('size', 0) or 0
    file_size = video.get('file_size', 0) or 0
    
    if size == 0 and file_size == 0 and filepath and os.path.exists(filepath):
        actual_size = os.path.getsize(filepath)
        updates['size'] = actual_size
        updates['file_size'] = actual_size
        fixed_size += 1
    elif size > 0 and file_size == 0:
        updates['file_size'] = size
        fixed_file_size += 1
    elif file_size > 0 and size == 0:
        updates['size'] = file_size
        fixed_size += 1
    
    # Fix missing duration from metadata
    metadata = video.get('metadata', {})
    duration = metadata.get('duration') if isinstance(metadata, dict) else None
    
    if not duration and filepath and os.path.exists(filepath):
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(filepath, audio=False)
            dur = clip.duration
            clip.close()
            if dur and dur > 0:
                if not isinstance(metadata, dict):
                    metadata = {}
                metadata['duration'] = dur
                updates['metadata'] = metadata
                fixed_duration += 1
                print(f"  Fixed duration for {video.get('filename')}: {dur:.1f}s")
        except Exception as e:
            pass  # Skip if can't read
    
    if updates:
        db.videos.update_one({'_id': vid}, {'$set': updates})

print(f"\nFixed {fixed_size} videos with missing size")
print(f"Fixed {fixed_file_size} videos with missing file_size")
print(f"Fixed {fixed_duration} videos with missing duration")
print("Done!")
client.close()
