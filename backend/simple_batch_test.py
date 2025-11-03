"""
Simple batch test with existing API key
"""

import requests

API_URL = "http://127.0.0.1:8000"

# Use the API key from earlier
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

print("🧪 Simple Batch Test")
print("=" * 60)

# Test 1: Single item
print("\n1️⃣ Testing with 1 item...")

response = requests.post(
    f"{API_URL}/api/batch/create",
    headers={
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "items": [
            {"collection": "test", "data": {"name": "Test User", "age": 30}}
        ]
    }
)

print(f"Status: {response.status_code}")

if response.status_code == 201:
    result = response.json()
    print(f"✅ SUCCESS!")
    print(f"   Created: {result['created']}")
    print(f"   Failed: {len(result['failed'])}")
    
    if result['items']:
        item = result['items'][0]
        print(f"   ID: {item['id']}")
        print(f"   Storage: {item['storage_type']}")
    
    print("\n🎉🎉🎉 BATCH OPERATIONS WORKING! 🎉🎉🎉")
    
elif response.status_code == 404:
    print("❌ 404 - Batch router not registered in main.py")
    print("\n💡 Check main.py has:")
    print("   app.include_router(batch_router.router, prefix='/api/batch', tags=['Batch Operations'])")
    
elif response.status_code == 401:
    print("❌ 401 - API key invalid")
    print("   Try creating a new user and API key")
    
else:
    print(f"❌ Error {response.status_code}")
    print(f"   {response.text}")

print("\n" + "=" * 60)