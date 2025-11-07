"""
Final search test
"""

from wooscloud import WoosStorage

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

print("="*60)
print("  🔍 Final Search Test")
print("="*60)

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

# Test 1: Search with fields
print("\n1. Search: 'laptop' in name and description")
results = storage.search("products", "laptop", fields=["name", "description"])
print(f"✅ Found {results['total']} results")

if results['results']:
    for item in results['results']:
        print(f"  - {item['data']['name']}: {item['data'].get('description', 'N/A')}")
else:
    print("  ❌ No results!")

# Test 2: Search without fields (all fields)
print("\n2. Search: 'gaming' in all fields")
results = storage.search("products", "gaming")
print(f"✅ Found {results['total']} results")

if results['results']:
    for item in results['results']:
        print(f"  - {item['data']['name']}")
else:
    print("  ❌ No results!")

# Test 3: Search Korean
print("\n3. Search: '노트북' in all fields")
results = storage.search("products", "노트북")
print(f"✅ Found {results['total']} results")

if results['results']:
    for item in results['results']:
        print(f"  - {item['data']['name']}")
else:
    print("  ❌ No results!")

# Test 4: Autocomplete
print("\n4. Autocomplete: 'Lap'")
suggestions = storage.autocomplete("products", "name", "Lap")
print(f"✅ Found {len(suggestions)} suggestions")
for suggestion in suggestions:
    print(f"  - {suggestion}")

# Test 5: Autocomplete Korean
print("\n5. Autocomplete: '노'")
suggestions = storage.autocomplete("products", "name", "노")
print(f"✅ Found {len(suggestions)} suggestions")
for suggestion in suggestions:
    print(f"  - {suggestion}")

print("\n" + "="*60)
print("  ✅ Search Test Completed!")
print("="*60)