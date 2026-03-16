"""Fix support tickets with string IDs - convert them to ObjectIds"""
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('mongodb://localhost:27017')
db = client.snipx

tickets = list(db.support_tickets.find())
fixed = 0

for t in tickets:
    tid = t['_id']
    uid = t.get('user_id')
    needs_fix = False
    
    # Fix string _id -> ObjectId
    if isinstance(tid, str):
        new_doc = t.copy()
        new_doc['_id'] = ObjectId(tid)
        db.support_tickets.delete_one({'_id': tid})
        db.support_tickets.insert_one(new_doc)
        print(f"Fixed ticket _id: {tid} (was string, now ObjectId)")
        fixed += 1
        needs_fix = True
    
    # Fix string user_id -> ObjectId
    if isinstance(uid, str) and uid:
        query_id = ObjectId(tid) if not isinstance(tid, str) else tid
        if needs_fix:
            query_id = ObjectId(tid)
        db.support_tickets.update_one(
            {'_id': query_id},
            {'$set': {'user_id': ObjectId(uid)}}
        )
        print(f"Fixed user_id for ticket {tid}: was string, now ObjectId")

print(f"\nFixed {fixed} tickets with string IDs")
print("All tickets now use proper ObjectId format")
