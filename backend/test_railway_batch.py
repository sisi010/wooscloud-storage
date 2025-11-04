import requests

# Your Railway URL
API_URL = "https://wooscloud-storage-production.up.railway.app"

print("🧪 Testing Batch Operations on Railway")
print("=" * 60)

# Login with existing user (if you have one on Railway)
email = input("Enter email: ")
password = input("Enter password: ")

login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={"email": email, "password": password}
)



print(f"Login status: {login_response.status_code}")
login_data = login_response.json()
print(f"Login response: {login_data}")

if login_response.status_code == 200:
    # Handle both 'token' and 'access_token' keys
    token = login_data.get("token") or login_data.get("access_token")
    
    if not token:
        print("❌ No token in response!")
        print(f"Keys: {login_data.keys()}")
        exit(1)
    
    print("✅ Logged in!")
    
    # Get or create API key
print("\n📝 Getting API keys...")
keys_response = requests.get(
    f"{API_URL}/api/keys/my-keys",
    headers={"Authorization": f"Bearer {token}"}
)

print(f"Keys status: {keys_response.status_code}")
keys_data = keys_response.json()
print(f"Keys response: {keys_data}")

# Check if user has API keys
if keys_data.get("keys") and len(keys_data["keys"]) > 0:
    api_key = keys_data["keys"][0]["key"]
    print(f"✅ Using existing key: {api_key[:30]}...")
else:
    # Create new API key
    print("\n🔑 Creating new API key...")
    create_key_response = requests.post(
        f"{API_URL}/api/keys/generate?name=RailwayBatchTestKey",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    print(f"Create key status: {create_key_response.status_code}")
    
    if create_key_response.status_code == 201:
        key_data = create_key_response.json()
        api_key = key_data.get("api_key") or key_data.get("key")
        print(f"✅ New API key created: {api_key[:30]}...")
    else:
        print(f"❌ Failed to create key: {create_key_response.text}")
        exit(1)

if api_key:
        
        # Test batch create
        batch_response = requests.post(
            f"{API_URL}/api/batch/create",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={
                "items": [
                    {"collection": "test", "data": {"name": "User1", "value": 100}},
                    {"collection": "test", "data": {"name": "User2", "value": 200}},
                    {"collection": "test", "data": {"name": "User3", "value": 300}}
                ]
            }
        )
        
        print(f"\n🎯 Batch Status: {batch_response.status_code}")
        
        if batch_response.status_code == 201:
            result = batch_response.json()
            print(f"\n🎉🎉🎉 BATCH OPERATIONS WORKING ON RAILWAY!")
            print(f"Created: {result['created']} items")
            for item in result['items']:
                print(f"  - {item['id']}")
        else:
            print(f"Error: {batch_response.text}")
else:
    print(f"Login failed: {login_response.text}")