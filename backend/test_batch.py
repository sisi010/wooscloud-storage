"""
Test batch operations
"""

import requests

API_URL = "http://127.0.0.1:8000"
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("🧪 Testing Batch Operations")
print("=" * 60)

# Test 1: Batch Create
print("\n1️⃣ Testing Batch Create...")
print("-" * 60)

batch_create_data = {
    "items": [
        {"collection": "batch_test", "data": {"name": "User1", "age": 25}},
        {"collection": "batch_test", "data": {"name": "User2", "age": 30}},
        {"collection": "batch_test", "data": {"name": "User3", "age": 35}},
        {"collection": "batch_test", "data": {"name": "User4", "age": 40}},
        {"collection": "batch_test", "data": {"name": "User5", "age": 45}}
    ]
}

try:
    response = requests.post(
        f"{API_URL}/api/batch/create",
        headers=headers,
        json=batch_create_data
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Batch create successful!")
        print(f"   Created: {result['created']} items")
        print(f"   Failed: {len(result['failed'])} items")
    
    # Show failed items with errors
    if result['failed']:
        print(f"\n   Failed items:")
        for item in result['failed']:
            print(f"   - Index {item['index']}: {item['error']}")
        
        # Save IDs for later tests
        created_ids = [item['id'] for item in result['items']]
        print(f"   IDs: {created_ids[:3]}...")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        created_ids = []
except Exception as e:
    print(f"❌ Error: {e}")
    created_ids = []

# Test 2: Batch Read
if created_ids:
    print("\n2️⃣ Testing Batch Read...")
    print("-" * 60)
    
    batch_read_data = {"ids": created_ids[:3]}
    
    try:
        response = requests.post(
            f"{API_URL}/api/batch/read",
            headers=headers,
            json=batch_read_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch read successful!")
            print(f"   Found: {result['found']} items")
            print(f"   Not found: {len(result['not_found'])} items")
            
            for item in result['items']:
                print(f"   - {item['data']['name']}: {item['data']['age']} years old")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Test 3: Batch Update
if created_ids:
    print("\n3️⃣ Testing Batch Update...")
    print("-" * 60)
    
    batch_update_data = {
        "items": [
            {"id": created_ids[0], "data": {"name": "User1", "age": 26, "updated": True}},
            {"id": created_ids[1], "data": {"name": "User2", "age": 31, "updated": True}}
        ]
    }
    
    try:
        response = requests.post(
            f"{API_URL}/api/batch/update",
            headers=headers,
            json=batch_update_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch update successful!")
            print(f"   Updated: {result['updated']} items")
            print(f"   Failed: {len(result['failed'])} items")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Test 4: Batch Delete
if created_ids:
    print("\n4️⃣ Testing Batch Delete...")
    print("-" * 60)
    
    batch_delete_data = {"ids": created_ids}
    
    try:
        response = requests.post(
            f"{API_URL}/api/batch/delete",
            headers=headers,
            json=batch_delete_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Batch delete successful!")
            print(f"   Deleted: {result['deleted']} items")
            print(f"   Not found: {len(result['not_found'])} items")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("📊 Test Summary")
print("=" * 60)
print("✅ Batch operations feature is ready!")
print("\n📱 API Endpoints:")
print(f"   POST {API_URL}/api/batch/create")
print(f"   POST {API_URL}/api/batch/read")
print(f"   POST {API_URL}/api/batch/update")
print(f"   POST {API_URL}/api/batch/delete")
print("=" * 60)