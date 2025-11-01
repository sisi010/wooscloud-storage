"""
Test Railway deployment with R2
"""

import requests

# Railway URL
RAILWAY_URL = "https://wooscloud-storage-production.up.railway.app"
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🧪 Testing Railway Deployment")
print("=" * 60)
print(f"URL: {RAILWAY_URL}\n")

# Test 1: Health Check
print("1️⃣ Health Check...")
print("-" * 60)
try:
    response = requests.get(f"{RAILWAY_URL}/health", timeout=10)
    print(f"✅ Status: {response.status_code}")
    result = response.json()
    print(f"   Database: {result.get('database', 'unknown')}")
    print(f"   Environment: {result.get('environment', 'unknown')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Stats (check R2 enabled)
print("\n2️⃣ Checking R2 Status...")
print("-" * 60)
try:
    response = requests.get(
        f"{RAILWAY_URL}/api/storage/stats",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        stats = result.get('stats', {})
        
        r2_enabled = stats.get('r2_enabled', False)
        print(f"✅ R2 Enabled: {r2_enabled}")
        
        storage = stats.get('storage', {})
        print(f"   Used: {storage.get('used_mb', 0)} MB")
        print(f"   Limit: {storage.get('limit_mb', 0)} MB")
        
        distribution = stats.get('storage_distribution', {})
        print(f"   MongoDB items: {distribution.get('mongodb', 0)}")
        print(f"   R2 items: {distribution.get('r2', 0)}")
        
        if r2_enabled:
            print("   🎉 R2 is enabled on Railway!")
        else:
            print("   ⚠️  R2 is disabled")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Create small data (MongoDB)
print("\n3️⃣ Testing Small Data (MongoDB)...")
print("-" * 60)
small_data = {
    "collection": "railway_test",
    "data": {
        "type": "small",
        "message": "Testing from Railway",
        "timestamp": "2025-01-02T12:00:00Z"
    }
}

try:
    response = requests.post(
        f"{RAILWAY_URL}/api/storage/create",
        headers=headers,
        json=small_data,
        timeout=10
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Created!")
        print(f"   Storage type: {result.get('storage_type', 'unknown')}")
        print(f"   Size: {result.get('size', 0)} bytes")
        print(f"   ID: {result.get('id', 'N/A')}")
        small_id = result.get('id')
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   {response.text}")
        small_id = None
        
except Exception as e:
    print(f"❌ Error: {e}")
    small_id = None

# Test 4: Create large data (R2)
print("\n4️⃣ Testing Large Data (R2)...")
print("-" * 60)
large_data = {
    "collection": "railway_test",
    "data": {
        "type": "large",
        "content": "X" * 150000,
        "timestamp": "2025-01-02T12:01:00Z"
    }
}

try:
    response = requests.post(
        f"{RAILWAY_URL}/api/storage/create",
        headers=headers,
        json=large_data,
        timeout=10
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Created!")
        print(f"   Storage type: {result.get('storage_type', 'unknown')}")
        print(f"   Size: {result.get('size', 0):,} bytes")
        print(f"   Size: {result.get('size', 0) / 1024:.2f} KB")
        print(f"   ID: {result.get('id', 'N/A')}")
        
        if result.get('storage_type') == 'r2':
            print("   🎉 Data stored in R2!")
        else:
            print("   ⚠️  Data stored in MongoDB")
            
        large_id = result.get('id')
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"   {response.text}")
        large_id = None
        
except Exception as e:
    print(f"❌ Error: {e}")
    large_id = None

# Test 5: Retrieve large data from R2
if large_id:
    print("\n5️⃣ Retrieving Large Data from R2...")
    print("-" * 60)
    try:
        response = requests.get(
            f"{RAILWAY_URL}/api/storage/read/{large_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Retrieved successfully!")
            print(f"   Storage type: {result.get('storage_type', 'unknown')}")
            print(f"   Content length: {len(str(result.get('data', {})))} chars")
            
            if result.get('storage_type') == 'r2':
                print("   🎉 Retrieved from R2!")
        else:
            print(f"❌ Status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

# Summary
print("\n" + "=" * 60)
print("📊 Test Summary")
print("=" * 60)

if small_id and large_id:
    print("✅ All tests passed!")
    print(f"   Small data ID: {small_id}")
    print(f"   Large data ID: {large_id}")
    print("\n🎉 WoosCloud Storage is working on Railway!")
    print(f"\n📱 API Docs: {RAILWAY_URL}/api/docs")
else:
    print("⚠️  Some tests failed")

print("=" * 60)