import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check():
    client = AsyncIOMotorClient("mongodb+srv://yongwoochoi94:q8PdslHdvWRLFCiG@mumuai1.o9pizhk.mongodb.net/?retryWrites=true&w=majority&appName=mumuai1")
    db = client.wooscloud
    
    # Find user
    user = await db.users.find_one({"email": "final_test@test.com"})
    
    if user:
        print(f"✅ User found: {user['_id']}")
        
        # Find API keys
        keys = await db.api_keys.find({"user_id": user["_id"]}).to_list(100)
        print(f"\n🔑 API Keys: {len(keys)}")
        
        for key in keys:
            print(f"  - {key['key'][:30]}...")
            print(f"    user_id: {key['user_id']}")
            print(f"    user_id type: {type(key['user_id'])}")
            print(f"    is_active: {key.get('is_active', True)}")
    else:
        print("❌ User not found!")
    
    client.close()

asyncio.run(check())