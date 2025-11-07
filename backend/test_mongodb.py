"""
Direct MongoDB query test
"""

from pymongo import MongoClient
from bson import ObjectId

# MongoDB 연결
client = MongoClient("mongodb+srv://wooscloud:wooscloud2024@wooscloud.wabpr.mongodb.net/?retryWrites=true&w=majority&appName=wooscloud")
db = client.wooscloud

print("="*60)
print("  MongoDB Direct Query Test")
print("="*60)

# 쿼리 실행
user_id = ObjectId("6901f4fbc345305a0f62f740")

query = {
    "collection": "products",
    "user_id": user_id,
    "$or": [
        {"data.name": {"$regex": "laptop", "$options": "i"}},
        {"data.description": {"$regex": "laptop", "$options": "i"}}
    ]
}

print(f"\nQuery: {query}")

results = list(db.storage_data.find(query).limit(10))
print(f"\n✅ Found {len(results)} results")

if results:
    print("\nFirst result:")
    print(results[0])
else:
    print("\n⚠️  No results found!")
    print("\nChecking all products...")
    all_products = list(db.storage_data.find({"collection": "products"}).limit(10))
    
    print(f"\nTotal products in DB: {len(all_products)}")
    
    for p in all_products:
        name = p.get('data', {}).get('name', 'N/A')
        pid = p.get('user_id')
        print(f"- {name}")
        print(f"  user_id: {pid}")
        print(f"  Match: {pid == user_id}")
        print()

print("="*60)