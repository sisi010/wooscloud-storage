"""
Test batch operations on Railway
"""

import requests

# Railway URL
API_URL = "https://woosai-backend-production.up.railway.app"

print("🧪 Testing Batch Operations on Railway")
print("=" * 60)

# 1. Register new user
print("\n1️⃣ Registering user...")
register_response = requests.post(
    f"{API_URL}/api/auth/register",
    json={
        "email": "batch_test@example.com",
        "password": "test1234",
        "name": "Batch Tester"
    }
)

if register_response.status_code == 201:
    print("✅ User registered!")
else:
    print(f"⚠️  Registration response: {register_response.status_code}")
    # User might already exist, continue

# 2. Login
print("\n2️⃣ Logging in...")
login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={
        "email": "batch_test@example.com",
        "password": "test1234"
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.text}")
    exit()

token = login_response.json()["access_token"]
print("✅ Login successful!")

# 3. Get or create API key
print("\n3️⃣ Getting API key...")

# Try to list existing keys first
list_response = requests.get(
    f"{API_URL}/api/keys",
    headers={"Authorization": f"Bearer {token}"}
)

api_key = None

if list_response.status_code == 200:
    keys = list_response.json().get("api_keys", [])
    if keys:
        api_key = keys[0]["key"]
        print(f"✅ Using existing API key")

if not api_key:
    # Create new key
    create_response = requests.post(
        f"{API_URL}/api/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Batch Test Key"}
    )
    
    if create_response.status_code in [200, 201]:
        api_key = create_response.json()["api_key"]
        print(f"✅ Created new API key")
    else:
        print(f"❌ Failed to create key: {create_response.text}")
        exit()

print(f"   Key: {api_key[:20]}...")

# 4. Test Batch Create
print("\n4️⃣ Testing Batch Create...")
print("-" * 60)

batch_response = requests.post(
    f"{API_URL}/api/batch/create",
    headers={
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    },
    json={
        "items": [
            {"collection": "users", "data": {"name": "Alice", "age": 25}},
            {"collection": "users", "data": {"name": "Bob", "age": 30}},
            {"collection": "users", "data": {"name": "Charlie", "age": 35}},
        ]
    }
)

print(f"Status: {batch_response.status_code}")

if batch_response.status_code == 201:
    result = batch_response.json()
    print(f"\n✅ SUCCESS!")
    print(f"   Created: {result['created']} items")
    print(f"   Failed: {len(result['failed'])} items")
    
    for item in result['items']:
        print(f"   - {item['id']} ({item['storage_type']})")
        
    print("\n🎉 Batch operations are working perfectly!")
    
else:
    print(f"❌ Failed: {batch_response.text}")

print("\n" + "=" * 60)