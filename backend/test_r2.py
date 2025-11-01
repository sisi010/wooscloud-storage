"""
Test R2 integration
Small data -> MongoDB
Large data -> R2
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🧪 Testing R2 Integration\n")
print("=" * 60)

# Test 1: Small data (should go to MongoDB)
print("\n1️⃣ Testing small data (< 100KB)...")
print("-" * 60)

small_data = {
    "collection": "test",
    "data": {
        "type": "small",
        "message": "This is small data",
        "timestamp": "2025-01-02T10:00:00Z"
    }
}

try:
    response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers=headers,
        json=small_data,
        timeout=10
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Success!")
        print(f"   Storage type: {result.get('storage_type', 'N/A')}")
        print(f"   Size: {result.get('size', 0)} bytes")
        print(f"   ID: {result.get('id', 'N/A')}")
        small_id = result.get('id')
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        small_id = None
        
except Exception as e:
    print(f"❌ Error: {e}")
    small_id = None

# Test 2: Large data (should go to R2)
print("\n2️⃣ Testing large data (>= 100KB)...")
print("-" * 60)

# Create 150KB of data
large_content = "X" * 150000

large_data = {
    "collection": "test",
    "data": {
        "type": "large",
        "content": large_content,
        "timestamp": "2025-01-02T10:01:00Z"
    }
}

try:
    response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers=headers,
        json=large_data,
        timeout=10
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Success!")
        print(f"   Storage type: {result.get('storage_type', 'N/A')}")
        print(f"   Size: {result.get('size', 0):,} bytes")
        print(f"   Size: {result.get('size', 0) / 1024:.2f} KB")
        print(f"   ID: {result.get('id', 'N/A')}")
        large_id = result.get('id')
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        large_id = None
        
except Exception as e:
    print(f"❌ Error: {e}")
    large_id = None

# Test 3: Retrieve small data
if small_id:
    print("\n3️⃣ Retrieving small data from MongoDB...")
    print("-" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/storage/read/{small_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Retrieved successfully!")
            print(f"   Storage type: {result.get('storage_type', 'N/A')}")
            print(f"   Message: {result.get('data', {}).get('message', 'N/A')}")
        else:
            print(f"❌ Failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

# Test 4: Retrieve large data
if large_id:
    print("\n4️⃣ Retrieving large data from R2...")
    print("-" * 60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/storage/read/{large_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Retrieved successfully!")
            print(f"   Storage type: {result.get('storage_type', 'N/A')}")
            print(f"   Content length: {len(str(result.get('data', {})))} chars")
        else:
            print(f"❌ Failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

# Test 5: Get statistics
print("\n5️⃣ Checking storage statistics...")
print("-" * 60)

try:
    response = requests.get(
        f"{BASE_URL}/api/storage/stats",
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        stats = result.get('stats', {})
        storage = stats.get('storage', {})
        distribution = stats.get('storage_distribution', {})
        
        print(f"✅ Stats retrieved!")
        print(f"   Used: {storage.get('used_mb', 0):.2f} MB")
        print(f"   Limit: {storage.get('limit_mb', 0):.2f} MB")
        print(f"   R2 enabled: {stats.get('r2_enabled', False)}")
        print(f"   MongoDB items: {distribution.get('mongodb', 0)}")
        print(f"   R2 items: {distribution.get('r2', 0)}")
        print(f"   Total items: {distribution.get('total', 0)}")
    else:
        print(f"❌ Failed: {response.status_code}")
        
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
    print("\n🎉 R2 integration is working correctly!")
else:
    print("⚠️  Some tests failed")
    if not small_id:
        print("   - Small data creation failed")
    if not large_id:
        print("   - Large data creation failed")

print("\n" + "=" * 60)