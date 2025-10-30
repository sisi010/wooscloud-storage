"""
MongoDB database connection
Using motor (async MongoDB driver)
"""
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from typing import Optional

# Global database client
mongodb_client: Optional[AsyncIOMotorClient] = None
database = None

async def connect_db():
    """Connect to MongoDB"""
    global mongodb_client, database
    
    try:
        mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
        database = mongodb_client[settings.DATABASE_NAME]
        
        # Test connection
        await mongodb_client.admin.command('ping')
        print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")
        
        # Create indexes for better performance
        await create_indexes()
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise

async def close_db():
    """Close MongoDB connection"""
    global mongodb_client
    
    if mongodb_client:
        mongodb_client.close()
        print("❌ MongoDB connection closed")

async def get_database():
    """Get database instance"""
    return database

async def create_indexes():
    """Create database indexes for better performance"""
    
    # Users collection indexes
    await database.users.create_index("email", unique=True)
    
    # API Keys collection indexes
    await database.api_keys.create_index("key", unique=True)
    await database.api_keys.create_index("user_id")
    
    # Storage data collection indexes
    await database.storage_data.create_index([("user_id", 1), ("collection", 1)])
    await database.storage_data.create_index("user_id")
    
    # Metadata collection indexes (for Phase 2+)
    await database.metadata.create_index("data_id", unique=True)
    await database.metadata.create_index("user_id")
    
    print("✅ Database indexes created")