"""
Test search functionality
"""

from wooscloud import WoosStorage

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

print("="*60)
print("  🔍 Search Test")
print("="*60)

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

# Test 1: Create test data
print("\n1. Creating test data...")
products = [
    {"name": "Laptop HP", "description": "High performance laptop", "price": 1500},
    {"name": "Laptop Dell", "description": "Business laptop with SSD", "price": 1200},
    {"name": "Laptop Asus", "description": "Gaming laptop with RTX", "price": 2000},
    {"name": "Mouse Logitech", "description": "Wireless mouse", "price": 50},
    {"name": "Keyboard Mechanical", "description": "RGB gaming keyboard", "price": 150},
]

for product in products:
    storage.save("products", product)

print(f"✅ Created {len(products)} products")

# Test 2: Search all fields
print("\n2. Search: 'laptop'")
results = storage.search("products", "laptop")
print(f"✅ Found {results['total']} results")
for item in results['results']:
    print(f"   - {item['data']['name']}")

# Test 3: Search specific fields
print("\n3. Search: 'gaming' in name and description")
results = storage.search(
    collection="products",
    query="gaming",
    fields=["name", "description"]
)
print(f"✅ Found {results['total']} results")
for item in results['results']:
    print(f"   - {item['data']['name']}: {item['data']['description']}")

# Test 4: Search Korean
print("\n4. Creating Korean data...")
storage.save("products", {"name": "노트북 삼성", "description": "한국산 노트북"})
storage.save("products", {"name": "키보드 한글", "description": "한글 자판"})

results = storage.search("products", "노트북")
print(f"✅ Found {results['total']} results")
for item in results['results']:
    print(f"   - {item['data']['name']}")

# Test 5: Autocomplete
print("\n5. Autocomplete: 'Lap'")
suggestions = storage.autocomplete(
    collection="products",
    field="name",
    prefix="Lap"
)
print(f"✅ Found {len(suggestions)} suggestions")
for suggestion in suggestions:
    print(f"   - {suggestion}")

# Test 6: Autocomplete Korean
print("\n6. Autocomplete: '노'")
suggestions = storage.autocomplete(
    collection="products",
    field="name",
    prefix="노"
)
print(f"✅ Found {len(suggestions)} suggestions")
for suggestion in suggestions:
    print(f"   - {suggestion}")

print("\n" + "="*60)
print("  ✅ Search Test Completed!")
print("="*60)