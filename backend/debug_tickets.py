from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017')
db = client.snipx
tickets = list(db.support_tickets.find().sort('created_at', -1).limit(3))
print("Recent tickets:")
for t in tickets:
    print(f"  ID: {t['_id']}")
    print(f"  Subject: {t['subject']}")
    print(f"  user_id type: {type(t.get('user_id'))}")
    print(f"  user_id value: {t.get('user_id')}")
    print(f"  responses: {len(t.get('responses', []))}")
    print()
