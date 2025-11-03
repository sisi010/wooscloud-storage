import requests

API_URL = "https://wooscloud-storage-production.up.railway.app"

print("🚀 Registering user on Railway...")
print("=" * 60)

response = requests.post(
    f"{API_URL}/api/auth/register",
    json={
        "email": "railway@wooscloud.com",
        "password": "Railway123!",
        "name": "Railway Tester"
    }
)

print(f"Status: {response.status_code}")

if response.status_code == 201:
    print("\n✅ Registration successful!")
    print("\n📝 Login Credentials:")
    print("   Email: railway@wooscloud.com")
    print("   Password: Railway123!")
    
    print("\n🎯 Now run: python test_railway_batch.py")
    print("   And use these credentials!")
    
else:
    print(f"Response: {response.json()}")

print("=" * 60)