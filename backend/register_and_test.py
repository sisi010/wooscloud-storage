import requests

API_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("🧪 WoosCloud Batch Operations Test")
print("=" * 60)

# 1. Login (or register if needed)
print("\n1️⃣ Logging in...")
login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={
        "email": "test@example.com",
        "password": "test1234"
    }
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print("✅ Login successful!")
else:
    print(f"❌ Login failed: {login_response.text}")
    exit()

# 2. Create API Key
print("\n2️⃣ Creating API key...")
api_key_response = requests.post(
    f"{API_URL}/api/keys/create",
    headers={"Authorization": f"Bearer {token}"},
    json={"name": "Batch Test Key"}
)

if api_key_response.status_code == 201:
    api_key = api_key_response.json()["api_key"]
    print(f"✅ API Key created: {api_key}")
else:
    print(f"❌ API Key creation failed: {api_key_response.text}")
    exit()

# 3. Test Batch Create
print("\n3️⃣ Testing Batch Create...")
print("-" * 60)

batch_response = requests.post(
    f"{API_URL}/api/batch/create",
    headers={
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    },
    json={
        "items": [
            {"collection": "users", "data": {"name": "Alice", "age": 25, "city": "Seoul"}},
            {"collection": "users", "data": {"name": "Bob", "age": 30, "city": "Busan"}},
            {"collection": "users", "data": {"name": "Charlie", "age": 35, "city": "Incheon"}},
            {"collection": "products", "data": {"name": "Laptop", "price": 1500}},
            {"collection": "products", "data": {"name": "Phone", "price": 800}}
        ]
    }
)

print(f"Status: {batch_response.status_code}")

if batch_response.status_code == 201:
    result = batch_response.json()
    print(f"\n✅ Batch create successful!")
    print(f"   Created: {result['created']} items")
    print(f"   Failed: {len(result['failed'])} items")
    
    if result['items']:
        print(f"\n📦 Created items:")
        for item in result['items']:
            print(f"   [{item['index']}] {item['collection']}")
            print(f"       ID: {item['id']}")
            print(f"       Size: {item['size']} bytes")
            print(f"       Storage: {item['storage_type']}")
        
    if result['failed']:
        print(f"\n❌ Failed items:")
        for item in result['failed']:
            print(f"   [{item['index']}] {item['collection']}: {item['error']}")
    
    # Save created IDs for later tests
    created_ids = [item['id'] for item in result['items']]
    
    # 4. Test Batch Read
    if created_ids:
        print(f"\n4️⃣ Testing Batch Read...")
        print("-" * 60)
        
        read_response = requests.post(
            f"{API_URL}/api/batch/read",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            json={"ids": created_ids[:3]}
        )
        
        if read_response.status_code == 200:
            read_result = read_response.json()
            print(f"✅ Found {read_result['found']} items")
            
            for item in read_result['items']:
                print(f"   - {item['data']}")
        else:
            print(f"❌ Read failed: {read_response.text}")
    
    # 5. Test Batch Delete
    if created_ids:
        print(f"\n5️⃣ Testing Batch Delete...")
        print("-" * 60)
        
        delete_response = requests.post(
            f"{API_URL}/api/batch/delete",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            json={"ids": created_ids}
        )
        
        if delete_response.status_code == 200:
            delete_result = delete_response.json()
            print(f"✅ Deleted {delete_result['deleted']} items")
        else:
            print(f"❌ Delete failed: {delete_response.text}")

else:
    print(f"❌ Batch create failed: {batch_response.text}")

print("\n" + "=" * 60)
print("✅ All tests complete!")
print("=" * 60)