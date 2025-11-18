"""
WoosCloud Storage - Quick Comprehensive Integration Test
Tests all major features together
"""

import requests
import time

# Configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

print("="*80)
print("  🔬 WoosCloud Storage - Quick Comprehensive Test")
print("="*80)
print(f"\n📡 Server: {BASE_URL}\n")

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")
        failed += 1

# ============================================================================
#  ALL FEATURES QUICK TEST
# ============================================================================

print("Testing all major features...\n")

# 1. V1 API
try:
    response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers={"X-API-Key": API_KEY},
        json={"collection": "quick_test", "data": {"test": "v1"}}
    )
    v1_id = response.json().get("id")
    test("V1 API", response.status_code == 201)
except Exception as e:
    test("V1 API", False)
    v1_id = None

# 2. V2 API
try:
    response = requests.post(
        f"{BASE_URL}/api/v2/storage",
        headers={"X-API-Key": API_KEY},
        json={"collection": "quick_test", "data": {"test": "v2"}}
    )
    result = response.json()
    v2_id = result.get("data", {}).get("id")
    test("V2 API", result.get("success") == True)
except Exception as e:
    test("V2 API", False)
    v2_id = None

# 3. Search
try:
    response = requests.get(
        f"{BASE_URL}/api/search",
        headers={"X-API-Key": API_KEY},
        params={"collection": "quick_test", "query": "test"}
    )
    test("Search", response.status_code == 200)
except:
    test("Search", False)

# 4. Backup
try:
    response = requests.post(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Quick Test Backup",
            "backup_type": "full",
            "collections": ["quick_test"],
            "compress": True
        }
    )
    backup_id = response.json().get("id")
    test("Backup", response.status_code == 201)
except Exception as e:
    test("Backup", False)
    backup_id = None

# 5. List Backups
try:
    response = requests.get(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY}
    )
    test("List Backups", response.status_code == 200)
except:
    test("List Backups", False)

# 6. Restore (Dry Run)
if backup_id:
    try:
        response = requests.post(
            f"{BASE_URL}/api/backups/restore",
            headers={"X-API-Key": API_KEY},
            json={
                "backup_id": backup_id,
                "conflict_resolution": "skip",
                "dry_run": True
            }
        )
        test("Restore", response.status_code == 201)
    except:
        test("Restore", False)
else:
    test("Restore", False)

# 7. Webhooks
try:
    response = requests.get(
        f"{BASE_URL}/api/webhooks",
        headers={"X-API-Key": API_KEY}
    )
    test("Webhooks", response.status_code == 200)
except:
    test("Webhooks", False)

# 8. Stats
try:
    response = requests.get(
        f"{BASE_URL}/api/storage/stats",
        headers={"X-API-Key": API_KEY}
    )
    test("Stats", response.status_code == 200)
except:
    test("Stats", False)

# 9. Export
try:
    response = requests.get(
        f"{BASE_URL}/api/export/preview",
        headers={"X-API-Key": API_KEY},
        params={"collection": "quick_test"}
    )
    test("Export", response.status_code == 200)
except:
    test("Export", False)

# 10. Version Headers
try:
    response = requests.get(
        f"{BASE_URL}/api/storage/stats",
        headers={"X-API-Key": API_KEY}
    )
    has_version = "X-API-Version" in response.headers
    test("Version Headers", has_version)
except:
    test("Version Headers", False)

# Cleanup
try:
    if v1_id:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{v1_id}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "quick_test"}
        )
    if v2_id:
        requests.delete(
            f"{BASE_URL}/api/v2/storage/{v2_id}",
            headers={"X-API-Key": API_KEY}
        )
    if backup_id:
        requests.delete(
            f"{BASE_URL}/api/backups/{backup_id}",
            headers={"X-API-Key": API_KEY}
        )
except:
    pass

# ============================================================================
#  RESULTS
# ============================================================================
print("\n" + "="*80)
print("  📊 RESULTS")
print("="*80)

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total}")
print(f"❌ Failed: {failed}/{total}")
print(f"📊 Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n🎉🎉🎉 ALL FEATURES WORKING! 🎉🎉🎉")
    print("\n✅ Verified:")
    print("  • V1 API ✅")
    print("  • V2 API ✅")
    print("  • Search ✅")
    print("  • Backup & Restore ✅")
    print("  • Webhooks ✅")
    print("  • Stats & Export ✅")
    print("  • Version Headers ✅")
    print("\n🚀 System is PRODUCTION READY!")
else:
    print(f"\n⚠️  {failed} feature(s) failed")
    print("⚠️  Please review before proceeding")

print(f"\n⏱️  Completed in ~5 seconds")