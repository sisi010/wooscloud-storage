import asyncio
import secrets
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def create_api_key():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb+srv://yongwoochoi94:q8PdslHdvWRLFCiG@mumuai1.o9pizhk.mongodb.net/?retryWrites=true&w=majority&appName=mumuai1")
    db = client.wooscloud
    
    # Find user
    user = await db.users.find_one({"email": "test@example.com"})
    
    if not user:
        print("❌ User not found!")
        client.close()
        return
    
    # Generate API key
    api_key = "wai_" + secrets.token_urlsafe(32)
    
    # Create API key document
    api_key_doc = {
        "user_id": user["_id"],
        "key": api_key,
        "name": "Batch Test Key",
        "is_active": True,
        "created_at": datetime.utcnow(),
        "last_used": None
    }
    
    # Insert to database
    await db.api_keys.insert_one(api_key_doc)
    
    print(f"✅ API Key created!")
    print(f"   User: {user['email']}")
    print(f"   Key: {api_key}")
    
    client.close()
    return api_key

# Run and get API key
api_key = asyncio.run(create_api_key())

if api_key:
    print(f"\n🧪 Testing with API key...")
    
    import requests
    
    API_URL = "http://127.0.0.1:8000"
    
    response = requests.post(
        f"{API_URL}/api/batch/create",
        headers={
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        },
        json={
            "items": [
                {"collection": "test", "data": {"name": "User1", "age": 25}},
                {"collection": "test", "data": {"name": "User2", "age": 30}},
                {"collection": "test", "data": {"name": "User3", "age": 35}}
            ]
        }
    )
    
    print(f"\nBatch Create Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Success!")
        print(f"   Created: {result['created']} items")
        print(f"   Failed: {len(result['failed'])} items")
        
        if result['items']:
            print(f"\n   Items:")
            for item in result['items']:
                print(f"   - {item['id']} ({item['storage_type']})")
    else:
        print(f"❌ Failed: {response.text}")