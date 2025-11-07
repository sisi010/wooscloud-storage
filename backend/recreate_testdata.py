"""
Re-create test data with current API key
"""

from wooscloud import WoosStorage

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

print("="*60)
print("  Creating Test Data")
print("="*60)

# Delete old products (optional)
print("\n1. Checking existing products...")
items = storage.find("products", limit=50)
print(f"Found {len(items)} existing products")

# Create new test data
print("\n2. Creating new test data...")
products = [
    {"name": "Laptop HP", "description": "High performance laptop", "price": 1500},
    {"name": "Laptop Dell", "description": "Business laptop with SSD", "price": 1200},
    {"name": "Laptop Asus", "description": "Gaming laptop with RTX", "price": 2000},
    {"name": "Mouse Logitech", "description": "Wireless mouse", "price": 50},
    {"name": "Keyboard Mechanical", "description": "RGB gaming keyboard", "price": 150},
    {"name": "노트북 삼성", "description": "한국산 노트북", "price": 1800},
    {"name": "키보드 한글", "description": "한글 자판", "price": 80},
]

for product in products:
    storage.save("products", product)
    print(f"✅ Created: {product['name']}")

print("\n3. Testing search...")
results = storage.search("products", "laptop", fields=["name", "description"])
print(f"Search results: {results['total']} found")

for item in results['results']:
    print(f"  - {item['data']['name']}")

print("\n" + "="*60)