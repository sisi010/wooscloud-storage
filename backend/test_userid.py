"""
Check user_id through API
"""

from wooscloud import WoosStorage
import requests

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

print("="*60)
print("  User ID & Data Check")
print("="*60)

# 1. Get user info from stats
print("\n1. Getting user info from stats...")
stats = storage.stats()
print(f"Plan: {stats.plan}")

# 2. Find products
print("\n2. Finding products...")
items = storage.find("products", limit=5)
print(f"Found {len(items)} products")

for item in items:
    print(f"\n- {item.data.get('name')}")
    print(f"  ID: {item.id}")
    print(f"  Collection: {item.collection}")

# 3. Try manual API call with different approach
print("\n3. Testing search without user_id filter...")

# Get raw response to see what's happening
response = requests.get(
    f"{BASE_URL}/api/storage/list",
    params={"collection": "products", "limit": 5},
    headers={"X-API-Key": API_KEY}
)

print(f"\nStatus: {response.status_code}")
data = response.json()
print(f"Total: {data.get('total')}")

if data.get('data'):
    print(f"\nFirst item structure:")
    print(data['data'][0])

print("\n" + "="*60)