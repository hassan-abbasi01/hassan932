from pymongo import MongoClient
from bson import ObjectId
client = MongoClient('mongodb://localhost:27017')
db = client.snipx

# Check all ticket IDs
tickets = list(db.support_tickets.find({}, {'_id': 1, 'subject': 1}))
for t in tickets:
    tid = t['_id']
    print(f"ID: {tid} (type: {type(tid).__name__}) Subject: {t.get('subject')}")
    
    # Try to find it by ObjectId
    if isinstance(tid, str):
        found_str = db.support_tickets.find_one({'_id': tid})
        found_oid = db.support_tickets.find_one({'_id': ObjectId(tid)})
        print(f"  Find by str: {found_str is not None}, by ObjectId: {found_oid is not None}")
    else:
        found_str = db.support_tickets.find_one({'_id': str(tid)})
        found_oid = db.support_tickets.find_one({'_id': tid})
        print(f"  Find by str: {found_str is not None}, by ObjectId: {found_oid is not None}")
