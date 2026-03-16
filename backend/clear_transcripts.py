"""Clear all stale transcripts from MongoDB so they regenerate with fixed filler logic"""
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017')
db = client['snipx']

# Clear ALL transcripts - they'll be regenerated with the fixed filler word lists
result = db.videos.update_many(
    {'transcript': {'$exists': True}},
    {'$set': {'transcript': None}}
)
print(f"Cleared transcripts from {result.modified_count} video(s)")

# Also reset any stuck processing videos
stuck = db.videos.update_many(
    {'status': 'processing'},
    {'$set': {'status': 'uploaded'}}
)
print(f"Reset {stuck.modified_count} stuck video(s)")
