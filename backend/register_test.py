import requests

API_URL = "http://127.0.0.1:8000"

# Register new user
print("Registering new user...")
response = requests.post(
    f"{API_URL}/api/auth/register",
    json={
        "email": "test@example.com",
        "password": "test1234",
        "name": "Test User"  # username → name
    }
)

print(f"Status: {response.status_code}")
result = response.json()
print(f"Response: {result}")

if response.status_code == 201:
    print(f"\n✅ User created!")
    print(f"API Key: {result.get('api_key')}")
    
    # Test batch create
    print("\n" + "=" * 60)
    print("🧪 Testing Batch Create...")
    print("=" * 60)
    
    batch_response = requests.post(
        f"{API_URL}/api/batch/create",
        headers={
            "X-API-Key": result.get('api_key'),
            "Content-Type": "application/json"
        },
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
        batch_result = batch_response.json()
        print(f"\n✅ Batch create successful!")
        print(f"   Created: {batch_result['created']} items")
        print(f"   Failed: {len(batch_result['failed'])} items")
        
        if batch_result['items']:
            print(f"\n   Created items:")
            for item in batch_result['items']:
                print(f"   - ID: {item['id']}")
                print(f"     Collection: {item['collection']}")
                print(f"     Size: {item['size']} bytes")
                print(f"     Storage: {item['storage_type']}")
    else:
        print(f"❌ Error: {batch_response.text}")
else:
    print(f"❌ Registration failed: {result}")