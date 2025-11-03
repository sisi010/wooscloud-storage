import requests

API_URL = "http://127.0.0.1:8000"

print("=" * 60)
print("🧪 Final Batch Operations Test")
print("=" * 60)

# 1. Register
print("\n1️⃣ Registering user...")
reg_response = requests.post(
    f"{API_URL}/api/auth/register",
    json={
        "email": "final_test@test.com",
        "password": "test1234",
        "name": "Final Tester"
    }
)
print(f"Status: {reg_response.status_code}")

# 2. Login
print("\n2️⃣ Logging in...")
login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={
        "email": "final_test@test.com",
        "password": "test1234"
    }
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print(f"✅ Login successful!")
    
    # 3. Create API key
    print("\n3️⃣ Creating API key...")
    key_response = requests.post(
        f"{API_URL}/api/keys/generate?name=FinalTestKey",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if key_response.status_code == 201:
        key_data = key_response.json()
        print(f"Key response: {key_data}")  # 디버깅
        api_key = key_data.get("api_key") or key_data.get("key")
        print(f"✅ API Key created: {api_key}")
        
        # 4. Test batch create
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
                    {"collection": "users", "data": {"name": "Charlie", "age": 35}}
                ]
            }
        )
        
        print(f"Status: {batch_response.status_code}")
        
        if batch_response.status_code == 201:
            result = batch_response.json()
            print(f"\n🎉🎉🎉 BATCH OPERATIONS WORKING!")
            print(f"Created: {result['created']} items")
            print(f"Failed: {len(result['failed'])} items")
            
            for item in result['items']:
                print(f"  - {item['id']} ({item['storage_type']})")
        else:
            print(f"❌ Error: {batch_response.text}")
    else:
        print(f"❌ Key creation failed: {key_response.text}")
else:
    print(f"❌ Login failed: {login_response.text}")

print("\n" + "=" * 60)