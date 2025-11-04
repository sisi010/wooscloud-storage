import requests
import time

API_URL = "https://wooscloud-storage-production.up.railway.app"

print("🧪 Testing Batch Operations on Railway")
print("=" * 60)

# Get credentials
email = input("Enter email: ")
password = input("Enter password: ")

# Login
login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={"email": email, "password": password}
)

print(f"Login status: {login_response.status_code}")

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print("✅ Logged in!")
    
    # Always create a fresh API key
    print("\n🔑 Creating fresh API key...")
    create_key_response = requests.post(
        f"{API_URL}/api/keys/generate?name=BatchTest_{int(time.time())}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Create key status: {create_key_response.status_code}")
    
    if create_key_response.status_code == 201:
        key_data = create_key_response.json()
        api_key = key_data.get("api_key") or key_data.get("key")
        print(f"✅ API Key created: {api_key[:40]}...")
        
        # Test batch create immediately
        print("\n🎯 Testing Batch Create...")
        print("-" * 60)
        
        batch_response = requests.post(
            f"{API_URL}/api/batch/create",
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            },
            json={
                "items": [
                    {"collection": "test", "data": {"name": "User1", "value": 100}},
                    {"collection": "test", "data": {"name": "User2", "value": 200}},
                    {"collection": "test", "data": {"name": "User3", "value": 300}}
                ]
            }
        )
        
        print(f"Batch Status: {batch_response.status_code}")
        
        if batch_response.status_code == 201:
            result = batch_response.json()
            print(f"\n🎉🎉🎉 BATCH OPERATIONS WORKING ON RAILWAY!")
            print(f"Created: {result['created']} items")
            print(f"Failed: {len(result.get('failed', []))} items")
            
            if result.get('items'):
                print("\nCreated items:")
                for item in result['items']:
                    print(f"  - {item['id']} ({item.get('storage_type', 'unknown')})")
        else:
            print(f"❌ Error: {batch_response.text}")
    else:
        print(f"❌ Create key failed: {create_key_response.text}")
else:
    print(f"Login failed: {login_response.text}")

print("\n" + "=" * 60)