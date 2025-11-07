"""
WoosCloud Storage - Comprehensive Test Suite v2.0
Tests all features: Data CRUD, Files, Search, Autocomplete
"""

from wooscloud import WoosStorage
import time

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

print("="*70)
print("  🧪 WoosCloud Storage - Comprehensive Test Suite v2.0")
print("="*70)

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

passed = 0
failed = 0

def test(name, condition, error_msg=""):
    global passed, failed
    if condition:
        print(f"✅ PASS: {name}")
        passed += 1
    else:
        print(f"❌ FAIL: {name}")
        if error_msg:
            print(f"   Error: {error_msg}")
        failed += 1

# ============================================================
#  1. DATA CRUD TESTS
# ============================================================
print("\n" + "="*70)
print("  1. DATA CRUD TESTS")
print("="*70)

# Test 1.1: Save
print("\n1.1: Save data")
try:
    data_id = storage.save("test_crud", {"name": "Test Item", "value": 100})
    test("Save data", len(data_id) > 0)
except Exception as e:
    test("Save data", False, str(e))

# Test 1.2: Find
print("\n1.2: Find data")
try:
    items = storage.find("test_crud", limit=10)
    test("Find data", len(items) > 0)
except Exception as e:
    test("Find data", False, str(e))

# Test 1.3: Get
print("\n1.3: Get by ID")
try:
    item = storage.get("test_crud", data_id)
    test("Get by ID", item is not None and item.data["name"] == "Test Item")
except Exception as e:
    test("Get by ID", False, str(e))

# Test 1.4: Update
print("\n1.4: Update data")
try:
    success = storage.update("test_crud", data_id, {"name": "Updated Item", "value": 200})
    updated = storage.get("test_crud", data_id)
    test("Update data", updated.data["name"] == "Updated Item")
except Exception as e:
    test("Update data", False, str(e))

# Test 1.5: Delete
print("\n1.5: Delete data")
try:
    success = storage.delete("test_crud", data_id)
    deleted = storage.get("test_crud", data_id)
    test("Delete data", deleted is None)
except Exception as e:
    test("Delete data", False, str(e))

# Test 1.6: Korean support
print("\n1.6: Korean data")
try:
    kr_id = storage.save("test_korean", {"이름": "테스트", "설명": "한글 테스트 😊"})
    kr_item = storage.get("test_korean", kr_id)
    test("Korean data", kr_item.data["이름"] == "테스트")
    storage.delete("test_korean", kr_id)
except Exception as e:
    test("Korean data", False, str(e))

# ============================================================
#  2. FILE UPLOAD TESTS
# ============================================================
print("\n" + "="*70)
print("  2. FILE UPLOAD TESTS")
print("="*70)

# Test 2.1: Create test file
print("\n2.1: Create test file")
try:
    with open("test_file.txt", "w", encoding="utf-8") as f:
        f.write("WoosCloud Storage Test File\n")
        f.write("한글 파일 테스트\n")
        f.write("Emoji test: 🚀✨\n")
    test("Create test file", True)
except Exception as e:
    test("Create test file", False, str(e))

# Test 2.2: Upload file
print("\n2.2: Upload file")
try:
    result = storage.files.upload(
        file_path="test_file.txt",
        collection="test_files",
        description="Test file upload",
        tags=["test", "demo"]
    )
    file_id = result["id"]
    test("Upload file", len(file_id) > 0)
except Exception as e:
    test("Upload file", False, str(e))
    file_id = None

# Test 2.3: Get file info
if file_id:
    print("\n2.3: Get file info")
    try:
        info = storage.files.get_info(file_id)
        test("Get file info", info["filename"] == "test_file.txt")
    except Exception as e:
        test("Get file info", False, str(e))

# Test 2.4: Download file
if file_id:
    print("\n2.4: Download file")
    try:
        content = storage.files.download(file_id)
        test("Download file", len(content) > 0 and b"WoosCloud" in content)
    except Exception as e:
        test("Download file", False, str(e))

# Test 2.5: List files
print("\n2.5: List files")
try:
    result = storage.files.list(collection="test_files", limit=10)
    test("List files", result["total"] > 0)
except Exception as e:
    test("List files", False, str(e))

# Test 2.6: Delete file
if file_id:
    print("\n2.6: Delete file")
    try:
        result = storage.files.delete(file_id)
        test("Delete file", result["success"] == True)
    except Exception as e:
        test("Delete file", False, str(e))

# ============================================================
#  3. SEARCH TESTS
# ============================================================
print("\n" + "="*70)
print("  3. SEARCH TESTS")
print("="*70)

# Setup test data
print("\n3.0: Setup search test data")
search_items = [
    {"name": "Gaming Laptop", "description": "High-end gaming machine", "price": 2000},
    {"name": "Office Laptop", "description": "Business productivity", "price": 1000},
    {"name": "Gaming Mouse", "description": "RGB gaming mouse", "price": 50},
    {"name": "노트북 삼성", "description": "한국산 노트북", "price": 1500},
]

for item in search_items:
    storage.save("search_test", item)
print("✅ Created search test data")

# Test 3.1: Search with fields
print("\n3.1: Search 'gaming' in name and description")
try:
    results = storage.search("search_test", "gaming", fields=["name", "description"])
    test("Search with fields", results["total"] >= 2)
except Exception as e:
    test("Search with fields", False, str(e))

# Test 3.2: Search all fields
print("\n3.2: Search 'laptop' in all fields")
try:
    results = storage.search("search_test", "laptop")
    test("Search all fields", results["total"] >= 2)
except Exception as e:
    test("Search all fields", False, str(e))

# Test 3.3: Search Korean
print("\n3.3: Search '노트북'")
try:
    results = storage.search("search_test", "노트북")
    test("Search Korean", results["total"] >= 1)
except Exception as e:
    test("Search Korean", False, str(e))

# Test 3.4: Case insensitive search
print("\n3.4: Search 'LAPTOP' (uppercase)")
try:
    results = storage.search("search_test", "LAPTOP", fields=["name", "description"])
    test("Case insensitive", results["total"] >= 2)
except Exception as e:
    test("Case insensitive", False, str(e))

# ============================================================
#  4. AUTOCOMPLETE TESTS
# ============================================================
print("\n" + "="*70)
print("  4. AUTOCOMPLETE TESTS")
print("="*70)

# Test 4.1: Autocomplete English
print("\n4.1: Autocomplete 'Gam'")
try:
    suggestions = storage.autocomplete("search_test", "name", "Gam")
    test("Autocomplete English", len(suggestions) >= 2)
except Exception as e:
    test("Autocomplete English", False, str(e))

# Test 4.2: Autocomplete Korean
print("\n4.2: Autocomplete '노'")
try:
    suggestions = storage.autocomplete("search_test", "name", "노")
    test("Autocomplete Korean", len(suggestions) >= 1)
except Exception as e:
    test("Autocomplete Korean", False, str(e))

# Test 4.3: Case insensitive autocomplete
print("\n4.3: Autocomplete 'gam' (lowercase)")
try:
    suggestions = storage.autocomplete("search_test", "name", "gam")
    test("Autocomplete case insensitive", len(suggestions) >= 2)
except Exception as e:
    test("Autocomplete case insensitive", False, str(e))

# ============================================================
#  5. STATISTICS TESTS
# ============================================================
print("\n" + "="*70)
print("  5. STATISTICS TESTS")
print("="*70)

print("\n5.1: Get storage stats")
try:
    stats = storage.stats()
    test("Get stats", stats.plan in ["free", "starter", "pro"])
    print(f"   Plan: {stats.plan}")
    print(f"   Storage: {stats.storage_used_mb:.2f} MB / {stats.storage_limit_mb:.0f} MB")
    print(f"   API Calls: {stats.api_calls_count}")
except Exception as e:
    test("Get stats", False, str(e))

# ============================================================
#  6. COLLECTIONS TESTS
# ============================================================
print("\n" + "="*70)
print("  6. COLLECTIONS TESTS")
print("="*70)

print("\n6.1: List collections")
try:
    collections = storage.collections()
    test("List collections", len(collections) > 0)
    print(f"   Total collections: {len(collections)}")
except Exception as e:
    test("List collections", False, str(e))

print("\n6.2: Count items in collection")
try:
    count = storage.count("search_test")
    test("Count items", count >= 4)
    print(f"   Items in 'search_test': {count}")
except Exception as e:
    test("Count items", False, str(e))

# ============================================================
#  FINAL RESULTS
# ============================================================
print("\n" + "="*70)
print("  📊 TEST RESULTS")
print("="*70)

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total}")
print(f"❌ Failed: {failed}/{total}")
print(f"📊 Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n🎉🎉🎉 ALL TESTS PASSED! 🎉🎉🎉")
else:
    print(f"\n⚠️  {failed} test(s) failed. Please review.")

print("\n" + "="*70)
print("  ✅ Comprehensive Test Suite Completed!")
print("="*70)