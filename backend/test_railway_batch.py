import requests

# Your Railway URL
API_URL = "https://woosai-backend-production.up.railway.app"

print("🧪 Testing Batch Operations on Railway")
print("=" * 60)

# Login with existing user (if you have one on Railway)
email = input("Enter email: ")
password = input("Enter password: ")

login_response = requests.post(
    f"{API_URL}/api/auth/login",
    json={"email": email, "password": password}
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    print("✅ Logged in!")
    
    # Get API keys
    keys_response = requests.get(
        f"{API_URL}/api/keys/my-keys",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if keys_response.status_code == 200 and keys_response.json().get("api_keys"):
        api_key = keys_response.json()["api_keys"][0]["key"]
        
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