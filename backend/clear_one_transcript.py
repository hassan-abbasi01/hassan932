from pymongo import MongoClient
from bson import ObjectId

db = MongoClient('mongodb://localhost:27017')['snipx']
r = db.videos.update_one(
    {'_id': ObjectId('69b122c28d31ea387682a062')},
    {'$unset': {'transcript': 1}}
)
print("Cleared transcript, matched:", r.matched_count, "modified:", r.modified_count)
