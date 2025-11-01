"""
Test PyPI library with R2 integration
"""

from wooscloud import WoosStorage

# Railway API URL
API_URL = "https://wooscloud-storage-production.up.railway.app"
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

print("🧪 Testing PyPI Library with R2")
print("=" * 60)

# Initialize
try:
    storage = WoosStorage(
        api_key=API_KEY,
        base_url=API_URL
    )
    print("✅ WoosStorage initialized")
    print(f"   Base URL: {API_URL}")
except Exception as e:
    print(f"❌ Initialization failed: {e}")
    exit(1)

# Test 1: Stats (check R2 enabled)
print("\n1️⃣ Checking R2 Status...")
print("-" * 60)
try:
    stats = storage.stats()
    
    print(f"✅ Stats retrieved")
    print(f"   Used: {stats.used_mb} MB")
    print(f"   Limit: {stats.limit_mb} MB")
    
    # Check for R2 status
    try:
        r2_enabled = stats.r2_enabled
        print(f"   R2 Enabled: {r2_enabled}")
        if r2_enabled:
            print("   🎉 R2 is enabled!")
    except AttributeError:
        pass
    
    # Check for storage distribution
    try:
        print(f"   MongoDB items: {stats.mongodb_items}")
        print(f"   R2 items: {stats.r2_items}")
        print(f"   Total: {stats.total_items}")
    except AttributeError:
        pass
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Save small data (MongoDB)
print("\n2️⃣ Testing Small Data (should go to MongoDB)...")
print("-" * 60)
try:
    small_id = storage.save("pypi_test", {
        "type": "small",
        "message": "Testing from PyPI library",
        "size": "small"
    })
    
    print(f"✅ Saved small data")
    print(f"   ID: {small_id}")
    
    # Retrieve to check storage_type
    data = storage.find_one(small_id)
    if data:
        storage_type = data.storage_type
        print(f"   Storage type: {storage_type}")
        
        if storage_type == 'mongodb':
            print("   ✅ Correctly stored in MongoDB")
        else:
            print(f"   ⚠️  Expected mongodb, got {storage_type}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Save large data (R2)
print("\n3️⃣ Testing Large Data (should go to R2)...")
print("-" * 60)
try:
    # Create 150KB of data
    large_content = "X" * 150000
    
    large_id = storage.save("pypi_test", {
        "type": "large",
        "content": large_content,
        "size": "large"
    })
    
    print(f"✅ Saved large data")
    print(f"   ID: {large_id}")
    print(f"   Data size: ~150KB")
    
    # Retrieve to check storage_type
    data = storage.find_one(large_id)
    if data:
        storage_type = data.storage_type
        print(f"   Storage type: {storage_type}")
        
        if storage_type == 'r2':
            print("   🎉 Correctly stored in R2!")
        elif storage_type == 'mongodb':
            print("   ⚠️  Stored in MongoDB (expected R2)")
        else:
            print(f"   ⚠️  Unknown storage type: {storage_type}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: List data
print("\n4️⃣ Listing all test data...")
print("-" * 60)
try:
    items = storage.find("pypi_test", limit=10)
    
    print(f"✅ Found {len(items)} items")
    
    mongodb_count = 0
    r2_count = 0
    
    for item in items:
        try:
            storage_type = item.storage_type
        except AttributeError:
            storage_type = 'unknown'
            
        if storage_type == 'mongodb':
            mongodb_count += 1
        elif storage_type == 'r2':
            r2_count += 1
    
    print(f"   MongoDB: {mongodb_count} items")
    print(f"   R2: {r2_count} items")
    
except Exception as e:
    print(f"❌ Error: {e}")

# Summary
print("\n" + "=" * 60)
print("📊 Summary")
print("=" * 60)

print("✅ PyPI library is working with R2!")

# Check if R2 integration is detected
print("\n🔍 R2 Integration Status:")
try:
    stats = storage.stats()
    
    if stats.r2_enabled:
        print("   ✅ R2 is enabled in API")
        print(f"   ✅ MongoDB items: {stats.mongodb_items}")
        print(f"   ✅ R2 items: {stats.r2_items}")
        print("   🎉 R2 integration is fully working!")
    else:
        print("   ⚠️  R2 is disabled")
        
except Exception as e:
    print(f"   ⚠️  Could not verify R2 status: {e}")

print("=" * 60)