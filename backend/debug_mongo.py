import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def test():
    client = AsyncIOMotorClient("mongodb+srv://mumuai1:q8ASDkq4BsHXEzZQ@mumuai1.o9pizhk.mongodb.net/wooscloud")
    db = client.wooscloud
    collection = db["test_encryption"]
    
    doc_id = "691472c368ed6ec84eb3a1d4"
    
    # Try ObjectId
    doc1 = await collection.find_one({"_id": ObjectId(doc_id)})
    print(f"With ObjectId: {doc1 is not None}")
    if doc1:
        print(f"Document keys: {list(doc1.keys())}")
        print(f"user_id type: {type(doc1.get('user_id'))}")
        print(f"user_id value: {doc1.get('user_id')}")
    
    # Try string
    doc2 = await collection.find_one({"_id": doc_id})
    print(f"\nWith string: {doc2 is not None}")

asyncio.run(test())
