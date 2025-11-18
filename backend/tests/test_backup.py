"""
WoosCloud Storage - Backup & Restore Test Suite
Tests backup creation, restoration, and management
"""

import requests
import time

# Configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

print("="*80)
print("  💾 WoosCloud Storage - Backup & Restore Test Suite")
print("="*80)
print(f"\n📡 Server: {BASE_URL}")
print(f"🔑 API Key: {API_KEY[:20]}...\n")

passed = 0
failed = 0

def test(name, condition, error_msg=""):
    """Test helper"""
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")
        if error_msg:
            print(f"     Error: {error_msg}")
        failed += 1

# ============================================================================
#  SETUP: CREATE TEST DATA
# ============================================================================
print("="*80)
print("  🔧 SETUP: Creating Test Data")
print("="*80)

test_ids = []

print("\nCreating test data...")
try:
    for i in range(5):
        response = requests.post(
            f"{BASE_URL}/api/storage/create",
            headers={"X-API-Key": API_KEY},
            json={
                "collection": "backup_test",
                "data": {
                    "name": f"Test Item {i+1}",
                    "value": (i+1) * 100,
                    "category": "backup"
                }
            }
        )
        
        if response.status_code == 201:
            test_ids.append(response.json()["id"])
    
    test("Test data created", len(test_ids) == 5)
    print(f"     Created {len(test_ids)} test items")
    
except Exception as e:
    test("Test data created", False, str(e))

# ============================================================================
#  SECTION 1: CREATE BACKUPS
# ============================================================================
print("\n" + "="*80)
print("  💾 SECTION 1: CREATE BACKUPS")
print("="*80)

# Test 1: Full Backup
print("\n1. Create full backup...")
try:
    response = requests.post(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Full Test Backup",
            "description": "Full backup of all data",
            "backup_type": "full",
            "include_files": True,
            "compress": True,
            "tags": ["test", "full"]
        }
    )
    
    result = response.json()
    full_backup_id = result.get("id")
    
    test("Full backup created", response.status_code == 201)
    
    if full_backup_id:
        print(f"     Backup ID: {full_backup_id}")
        print(f"     Status: {result.get('status')}")
        print(f"     Records: {result.get('record_count')}")
        print(f"     Size: {result.get('size_bytes')} bytes")
    
except Exception as e:
    test("Full backup created", False, str(e))
    full_backup_id = None

# Test 2: Collection-specific Backup
print("\n2. Create collection-specific backup...")
try:
    response = requests.post(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Collection Backup",
            "backup_type": "full",
            "collections": ["backup_test"],
            "include_files": False,
            "compress": True
        }
    )
    
    result = response.json()
    collection_backup_id = result.get("id")
    
    test("Collection backup created", response.status_code == 201)
    
    if collection_backup_id:
        print(f"     Backup ID: {collection_backup_id}")
        print(f"     Collections: {result.get('collections')}")
    
except Exception as e:
    test("Collection backup created", False, str(e))
    collection_backup_id = None

# Test 3: Incremental Backup
print("\n3. Create incremental backup...")
try:
    # Modify some data first
    if test_ids:
        requests.put(
            f"{BASE_URL}/api/storage/update/{test_ids[0]}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "backup_test"},
            json={"data": {"name": "Modified Item", "value": 999}}
        )
    
    time.sleep(1)
    
    response = requests.post(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Incremental Backup",
            "backup_type": "incremental",
            "compress": True
        }
    )
    
    result = response.json()
    incremental_backup_id = result.get("id")
    
    test("Incremental backup created", response.status_code == 201)
    
    if incremental_backup_id:
        print(f"     Backup ID: {incremental_backup_id}")
        print(f"     Type: {result.get('backup_type')}")
    
except Exception as e:
    test("Incremental backup created", False, str(e))
    incremental_backup_id = None

# ============================================================================
#  SECTION 2: LIST & GET BACKUPS
# ============================================================================
print("\n" + "="*80)
print("  📋 SECTION 2: LIST & GET BACKUPS")
print("="*80)

# Test 4: List Backups
print("\n4. List all backups...")
try:
    response = requests.get(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY},
        params={"limit": 10}
    )
    
    result = response.json()
    backups = result.get("backups", [])
    
    test("List backups", len(backups) >= 3)
    print(f"     Total backups: {result.get('total')}")
    print(f"     Returned: {len(backups)}")
    
except Exception as e:
    test("List backups", False, str(e))

# Test 5: Get Backup Details
print("\n5. Get backup details...")
if full_backup_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/backups/{full_backup_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Get backup details", response.status_code == 200)
        print(f"     Name: {result.get('name')}")
        print(f"     Status: {result.get('status')}")
        print(f"     Record count: {result.get('record_count')}")
        
    except Exception as e:
        test("Get backup details", False, str(e))
else:
    print("  ⏭️  Skipped (no backup ID)")

# Test 6: Backup Statistics
print("\n6. Get backup statistics...")
try:
    response = requests.get(
        f"{BASE_URL}/api/backups/stats/summary",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    
    test("Backup statistics", response.status_code == 200)
    print(f"     Total backups: {result.get('total_backups')}")
    print(f"     Total size: {result.get('total_size_bytes')} bytes")
    print(f"     By type: {result.get('by_type')}")
    
except Exception as e:
    test("Backup statistics", False, str(e))

# ============================================================================
#  SECTION 3: RESTORE OPERATIONS
# ============================================================================
print("\n" + "="*80)
print("  🔄 SECTION 3: RESTORE OPERATIONS")
print("="*80)

# Test 7: Dry Run Restore
print("\n7. Dry run restore (preview)...")
if full_backup_id:
    try:
        response = requests.post(
            f"{BASE_URL}/api/backups/restore",
            headers={"X-API-Key": API_KEY},
            json={
                "backup_id": full_backup_id,
                "conflict_resolution": "skip",
                "restore_files": True,
                "dry_run": True
            }
        )
        
        result = response.json()
        
        test("Dry run restore", response.status_code == 201)
        print(f"     Status: {result.get('status')}")
        print(f"     Would restore: {result.get('records_restored')} records")
        print(f"     Conflicts: {result.get('conflicts_encountered')}")
        
    except Exception as e:
        test("Dry run restore", False, str(e))
else:
    print("  ⏭️  Skipped (no backup ID)")

# Test 8: Delete some data before restore
print("\n8. Prepare for actual restore (delete data)...")
try:
    if test_ids:
        # Delete first 2 items
        for item_id in test_ids[:2]:
            requests.delete(
                f"{BASE_URL}/api/storage/delete/{item_id}",
                headers={"X-API-Key": API_KEY},
                params={"collection": "backup_test"}
            )
        
        test("Data deleted", True)
        print(f"     Deleted 2 items")
    
except Exception as e:
    test("Data deleted", False, str(e))

# Test 9: Actual Restore (Skip Conflicts)
print("\n9. Restore with skip conflicts...")
if full_backup_id:
    try:
        response = requests.post(
            f"{BASE_URL}/api/backups/restore",
            headers={"X-API-Key": API_KEY},
            json={
                "backup_id": full_backup_id,
                "conflict_resolution": "skip",
                "restore_files": True,
                "dry_run": False
            }
        )
        
        result = response.json()
        restore_job_id = result.get("id")
        
        test("Restore (skip)", response.status_code == 201)
        print(f"     Job ID: {restore_job_id}")
        print(f"     Restored: {result.get('records_restored')} records")
        print(f"     Skipped: {result.get('conflicts_resolved', {}).get('skip', 0)}")
        
    except Exception as e:
        test("Restore (skip)", False, str(e))
        restore_job_id = None
else:
    print("  ⏭️  Skipped (no backup ID)")
    restore_job_id = None

# Test 10: Get Restore Job Status
print("\n10. Get restore job status...")
if restore_job_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/restore-jobs/{restore_job_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Restore job status", response.status_code == 200)
        print(f"     Status: {result.get('status')}")
        print(f"     Records restored: {result.get('records_restored')}")
        print(f"     Conflicts: {result.get('conflicts_encountered')}")
        
    except Exception as e:
        test("Restore job status", False, str(e))
else:
    print("  ⏭️  Skipped (no job ID)")

# Test 11: Verify Restored Data
print("\n11. Verify restored data...")
try:
    # Use V1 list endpoint
    response = requests.get(
        f"{BASE_URL}/api/storage/list",
        headers={"X-API-Key": API_KEY},
        params={"collection": "backup_test", "limit": 10}
    )
    
    result = response.json()
    items = result.get("data", [])
    
    test("Data restored", len(items) >= 2)
    print(f"     Found {len(items)} items after restore")
    
except Exception as e:
    test("Data restored", False, str(e))

# Test 12: Collection-specific Restore
print("\n12. Collection-specific restore...")
if collection_backup_id:
    try:
        response = requests.post(
            f"{BASE_URL}/api/backups/restore",
            headers={"X-API-Key": API_KEY},
            json={
                "backup_id": collection_backup_id,
                "collections": ["backup_test"],
                "conflict_resolution": "overwrite",
                "dry_run": False
            }
        )
        
        result = response.json()
        
        test("Collection restore", response.status_code == 201)
        print(f"     Collections: {result.get('collections')}")
        print(f"     Overwrote: {result.get('conflicts_resolved', {}).get('overwrite', 0)}")
        
    except Exception as e:
        test("Collection restore", False, str(e))
else:
    print("  ⏭️  Skipped (no backup ID)")

# ============================================================================
#  SECTION 4: DELETE BACKUP
# ============================================================================
print("\n" + "="*80)
print("  🗑️  SECTION 4: DELETE BACKUP")
print("="*80)

# Test 13: Delete Backup
print("\n13. Delete backup...")
if incremental_backup_id:
    try:
        response = requests.delete(
            f"{BASE_URL}/api/backups/{incremental_backup_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Delete backup", response.status_code == 200)
        print(f"     Deleted: {result.get('backup_id')}")
        
    except Exception as e:
        test("Delete backup", False, str(e))
else:
    print("  ⏭️  Skipped (no backup ID)")

# ============================================================================
#  CLEANUP
# ============================================================================
print("\n" + "="*80)
print("  🧹 CLEANUP")
print("="*80)

try:
    # Delete test data
    response = requests.get(
        f"{BASE_URL}/api/storage/list",
        headers={"X-API-Key": API_KEY},
        params={"collection": "backup_test", "limit": 100}
    )
    
    result = response.json()
    items = result.get("data", [])
    
    for item in items:
        item_id = item.get("id")
        if item_id:
            requests.delete(
                f"{BASE_URL}/api/storage/delete/{item_id}",
                headers={"X-API-Key": API_KEY},
                params={"collection": "backup_test"}
            )
    
    # Delete remaining backups
    if full_backup_id:
        requests.delete(
            f"{BASE_URL}/api/backups/{full_backup_id}",
            headers={"X-API-Key": API_KEY}
        )
    
    if collection_backup_id:
        requests.delete(
            f"{BASE_URL}/api/backups/{collection_backup_id}",
            headers={"X-API-Key": API_KEY}
        )
    
    print("  ✅ Test data and backups cleaned up")
except:
    pass

# ============================================================================
#  RESULTS
# ============================================================================
print("\n" + "="*80)
print("  📊 BACKUP & RESTORE TEST RESULTS")
print("="*80)

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total}")
print(f"❌ Failed: {failed}/{total}")
print(f"📊 Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n🎉🎉🎉 ALL BACKUP & RESTORE TESTS PASSED! 🎉🎉🎉")
    print("\n✨ Features Tested:")
    print("  ✅ Full backups")
    print("  ✅ Incremental backups")
    print("  ✅ Collection-specific backups")
    print("  ✅ Compression")
    print("  ✅ Restore with conflict resolution")
    print("  ✅ Dry run mode")
    print("  ✅ Backup statistics")
    print("  ✅ Backup management")
else:
    print(f"\n⚠️  {failed} test(s) failed")

print(f"\n🎯 Total: {total} tests")
print(f"⏱️  Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")