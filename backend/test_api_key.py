"""
Generate new API key and test batch operations
"""

import requests

API_URL = "http://127.0.0.1:8000"

print("🔑 API Key Test")
print("=" * 60)

# 1. Login
print("\n1️⃣ Logging in...")
login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={
        "email": "sisi010@naver.com",
        "password": "111111"
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit()

token = login_response.json()["access_token"]
print(f"✅ Login successful!")

# 2. Create API Key
print("\n2️⃣ Creating API key...")
api_key_response = requests.post(
    f"{API_URL}/api/keys/create",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Batch Test Key"}
)

if api_key_response.status_code != 201:
    print(f"❌ API Key creation failed: {api_key_response.text}")
    exit()

api_key = api_key_response.json()["api_key"]
print(f"✅ New API Key: {api_key}")

# 3. Test Batch Create
print("\n3️⃣ Testing batch create...")
batch_response = requests.post(
    f"{API_URL}/api/batch/create",
    headers={"X-API-Key": api_key, "Content-Type": "application/json"},
    json={
        "items": [
            {"collection": "test", "data": {"name": "User1", "age": 25}},
            {"collection": "test", "data": {"name": "User2", "age": 30}},
            {"collection": "test", "data": {"name": "User3", "age": 35}}
        ]
    }
)

print(f"Status: {batch_response.status_code}")

if batch_response.status_code == 201:
    result = batch_response.json()
    print(f"✅ Batch create successful!")
    print(f"   Created: {result['created']} items")
    print(f"   Failed: {len(result['failed'])} items")
    
    if result['items']:
        print(f"\n   Created IDs:")
        for item in result['items'][:3]:
            print(f"   - {item['id']} ({item['storage_type']})")
else:
    print(f"❌ Failed: {batch_response.text}")

print("\n" + "=" * 60)
print("✅ Test complete!")