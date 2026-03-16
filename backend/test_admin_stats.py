"""Test admin dashboard stats after fixes"""
from pymongo import MongoClient
from models.activity_log import PlatformStats

client = MongoClient('mongodb://localhost:27017')
db = client['snipx']

stats = PlatformStats.calculate_stats(db)

print("=" * 50)
print("ADMIN DASHBOARD STATS (AFTER FIX)")
print("=" * 50)
for key, val in stats.items():
    print(f"  {key}: {val}")

client.close()
