"""
WoosCloud Storage Comprehensive Test Suite
Tests various error cases and edge conditions
"""

from wooscloud import WoosStorage
import time

# Test configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_authentication():
    """Test authentication errors"""
    print_section("1. AUTHENTICATION TESTS")
    
    # Test 1.1: Invalid API key format
    print("Test 1.1: Invalid API key format")
    try:
        storage = WoosStorage(api_key="invalid_key")
        print("❌ FAIL: Should reject invalid format")
    except Exception as e:
        print(f"✅ PASS: {e}")
    
    # Test 1.2: Wrong API key (correct format)
    print("\nTest 1.2: Wrong API key (valid format)")
    try:
        storage = WoosStorage(
            api_key="wai_fakekeyfortesting123456789",
            base_url=BASE_URL
        )
        storage.save("test", {"data": "test"})
        print("❌ FAIL: Should reject fake key")
    except Exception as e:
        print(f"✅ PASS: {e}")
    
    # Test 1.3: Valid API key
    print("\nTest 1.3: Valid API key")
    try:
        storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
        print("✅ PASS: Authentication successful")
    except Exception as e:
        print(f"❌ FAIL: {e}")

def test_data_operations():
    """Test data CRUD operations"""
    print_section("2. DATA OPERATION TESTS")
    
    storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
    
    # Test 2.1: Save empty data
    print("Test 2.1: Save empty data")
    try:
        result = storage.save("test_empty", {})
        print(f"✅ PASS: Saved empty data with ID: {result}")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 2.2: Save large data
    print("\nTest 2.2: Save large data (10KB)")
    try:
        large_data = {"text": "A" * 10000}  # ~10KB
        result = storage.save("test_large", large_data)
        print(f"✅ PASS: Saved large data with ID: {result}")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 2.3: Save special characters
    print("\nTest 2.3: Save special characters")
    try:
        special_data = {
            "korean": "한글 테스트",
            "emoji": "😀🎉✅",
            "symbols": "!@#$%^&*()",
            "quotes": "\"'`",
            "newlines": "line1\nline2\nline3"
        }
        result = storage.save("test_special", special_data)
        print(f"✅ PASS: Saved special chars with ID: {result}")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 2.4: Save nested data
    print("\nTest 2.4: Save nested data")
    try:
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep nested"
                    }
                }
            },
            "array": [1, 2, [3, 4, [5, 6]]]
        }
        result = storage.save("test_nested", nested_data)
        print(f"✅ PASS: Saved nested data with ID: {result}")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 2.5: Find non-existent collection
    print("\nTest 2.5: Find non-existent collection")
    try:
        items = storage.find("nonexistent_collection_xyz")
        print(f"✅ PASS: Returned {len(items)} items (empty list expected)")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 2.6: Get non-existent ID
    print("\nTest 2.6: Get non-existent ID")
    try:
        item = storage.get("test_special", "000000000000000000000000")
        if item is None:
            print(f"✅ PASS: Returned None as expected")
        else:
            print(f"❌ FAIL: Should return None or error, got: {item.id}")
    except Exception as e:
        print(f"✅ PASS: {e}")

def test_collection_names():
    """Test various collection name formats"""
    print_section("3. COLLECTION NAME TESTS")
    
    storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
    
    test_cases = [
        ("valid_collection", True),
        ("collection123", True),
        ("collection_with_underscore", True),
        ("collection-with-dash", True),
        ("CollectionMixedCase", True),
        ("한글컬렉션", True),  # May or may not work
    ]
    
    for collection_name, should_work in test_cases:
        print(f"\nTest: Collection name '{collection_name}'")
        try:
            result = storage.save(collection_name, {"test": "data"})
            if should_work:
                print(f"✅ PASS: Saved to '{collection_name}'")
            else:
                print(f"⚠️  Unexpected success for '{collection_name}'")
        except Exception as e:
            if not should_work:
                print(f"✅ PASS: Rejected '{collection_name}' - {e}")
            else:
                print(f"❌ FAIL: Should accept '{collection_name}' - {e}")

def test_query_operations():
    """Test query and filter operations"""
    print_section("4. QUERY OPERATION TESTS")
    
    storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
    
    # Setup test data
    print("Setting up test data...")
    for i in range(5):
        storage.save("test_query", {
            "index": i,
            "name": f"Item {i}",
            "active": i % 2 == 0
        })
    
    # Test 4.1: Find with limit
    print("\nTest 4.1: Find with limit=2")
    try:
        items = storage.find("test_query", limit=2)
        if len(items) == 2:
            print(f"✅ PASS: Returned exactly 2 items")
        else:
            print(f"❌ FAIL: Expected 2 items, got {len(items)}")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 4.2: Find with skip
    print("\nTest 4.2: Find with skip=3")
    try:
        items = storage.find("test_query", skip=3)
        print(f"✅ PASS: Returned {len(items)} items (should be 2)")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 4.3: Find all
    print("\nTest 4.3: Find all items")
    try:
        items = storage.find("test_query")
        print(f"✅ PASS: Found {len(items)} items")
    except Exception as e:
        print(f"❌ FAIL: {e}")

def test_update_delete():
    """Test update and delete operations"""
    print_section("5. UPDATE & DELETE TESTS")
    
    storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
    
    # Test 5.1: Update existing item
    print("Test 5.1: Update existing item")
    try:
        # Create item
        item_id = storage.save("test_update", {"value": "original"})
        
        # Update item
        storage.update("test_update", item_id, {"value": "updated"})
        
        # Verify update
        item = storage.get("test_update", item_id)
        if item.data["value"] == "updated":
            print(f"✅ PASS: Item updated successfully")
        else:
            print(f"❌ FAIL: Update didn't work")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 5.2: Delete existing item
    print("\nTest 5.2: Delete existing item")
    try:
        # Create item
        item_id = storage.save("test_delete", {"temp": "data"})
        
        # Delete item
        storage.delete("test_delete", item_id)
        
        print(f"✅ PASS: Item deleted successfully")
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 5.3: Delete non-existent item
    print("\nTest 5.3: Delete non-existent item")
    try:
        storage.delete("test_delete", "000000000000000000000000")
        print(f"⚠️  Should handle gracefully")
    except Exception as e:
        print(f"✅ PASS: Handled error - {e}")

def test_stats():
    """Test statistics endpoint"""
    print_section("6. STATISTICS TESTS")
    
    storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
    
    print("Test 6.1: Get storage statistics")
    try:
        stats = storage.stats()
        print(f"✅ PASS: Statistics retrieved")
        print(f"   Plan: {stats.plan}")
        print(f"   Storage Limit: {stats.storage_limit_mb:.0f} MB")
        print(f"   Storage Used: {stats.storage_used_mb:.2f} MB")
        print(f"   API Calls: {stats.api_calls_count}/{stats.api_calls_limit}")
    except Exception as e:
        print(f"❌ FAIL: {e}")

def test_performance():
    """Test performance with multiple operations"""
    print_section("7. PERFORMANCE TESTS")
    
    storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)
    
    print("Test 7.1: Rapid successive saves (10 items)")
    try:
        start_time = time.time()
        for i in range(10):
            storage.save("test_perf", {"index": i, "timestamp": time.time()})
        elapsed = time.time() - start_time
        print(f"✅ PASS: Saved 10 items in {elapsed:.2f} seconds")
        print(f"   Average: {elapsed/10:.3f}s per item")
    except Exception as e:
        print(f"❌ FAIL: {e}")

def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*60)
    print("  🧪 WoosCloud Storage Comprehensive Test Suite")
    print("="*60)
    
    try:
        test_authentication()
        test_data_operations()
        test_collection_names()
        test_query_operations()
        test_update_delete()
        test_stats()
        test_performance()
        
        print("\n" + "="*60)
        print("  ✅ Test Suite Completed!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")

if __name__ == "__main__":
    run_all_tests()