"""Reset stuck 'processing' videos back to 'uploaded' status"""
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017')
db = client['snipx']

stuck = list(db.videos.find({'status': 'processing'}))
for v in stuck:
    vid_id = str(v['_id'])
    fname = v.get('filename', '?')
    print(f"Resetting: {vid_id} - {fname} from processing -> uploaded")
    db.videos.update_one(
        {'_id': v['_id']},
        {'$set': {'status': 'uploaded', 'transcript': None}}
    )

print(f"Reset {len(stuck)} stuck video(s)")
