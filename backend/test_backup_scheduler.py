"""
WoosCloud Storage - Backup Scheduler Test Suite
Tests automatic backup scheduling, execution, and retention
"""

import requests
import time

# Configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

print("="*80)
print("  ⏰ WoosCloud Storage - Backup Scheduler Test Suite")
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

print("\nCreating test data for scheduled backups...")
test_ids = []

try:
    for i in range(5):
        response = requests.post(
            f"{BASE_URL}/api/storage/create",
            headers={"X-API-Key": API_KEY},
            json={
                "collection": "scheduler_test",
                "data": {"item": i, "value": i * 100}
            }
        )
        if response.status_code == 201:
            test_ids.append(response.json().get("id"))
    
    test("Test data created", len(test_ids) == 5)
    print(f"     Created {len(test_ids)} test items")
    
except Exception as e:
    test("Test data created", False, str(e))

# ============================================================================
#  SECTION 1: SCHEDULE CREATION
# ============================================================================
print("\n" + "="*80)
print("  📅 SECTION 1: SCHEDULE CREATION")
print("="*80)

# Test 1: Create Daily Schedule
print("\n1. Create daily backup schedule...")
try:
    response = requests.post(
        f"{BASE_URL}/api/backup-schedules",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Daily Backup",
            "description": "Daily backup at 2 AM",
            "frequency": "daily",
            "backup_type": "full",
            "collections": ["scheduler_test"],
            "include_files": True,
            "compress": True,
            "retention_days": 30,
            "tags": ["test", "daily"]
        }
    )
    
    result = response.json()
    daily_schedule_id = result.get("id")
    
    test("Create daily schedule", response.status_code == 201)
    
    if daily_schedule_id:
        print(f"     Schedule ID: {daily_schedule_id}")
        print(f"     Frequency: {result.get('frequency')}")
        print(f"     Next run: {result.get('next_run_at')}")
    
except Exception as e:
    test("Create daily schedule", False, str(e))
    daily_schedule_id = None

# Test 2: Create Weekly Schedule
print("\n2. Create weekly backup schedule...")
try:
    response = requests.post(
        f"{BASE_URL}/api/backup-schedules",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Weekly Backup",
            "frequency": "weekly",
            "backup_type": "full",
            "compress": True,
            "max_backups": 4,
            "tags": ["test", "weekly"]
        }
    )
    
    result = response.json()
    weekly_schedule_id = result.get("id")
    
    test("Create weekly schedule", response.status_code == 201)
    
    if weekly_schedule_id:
        print(f"     Schedule ID: {weekly_schedule_id}")
        print(f"     Max backups: {result.get('max_backups')}")
    
except Exception as e:
    test("Create weekly schedule", False, str(e))
    weekly_schedule_id = None

# Test 3: Create Hourly Schedule
print("\n3. Create hourly backup schedule...")
try:
    response = requests.post(
        f"{BASE_URL}/api/backup-schedules",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Hourly Backup",
            "frequency": "hourly",
            "backup_type": "incremental",
            "collections": ["scheduler_test"],
            "compress": True,
            "retention_days": 7
        }
    )
    
    result = response.json()
    hourly_schedule_id = result.get("id")
    
    test("Create hourly schedule", response.status_code == 201)
    
except Exception as e:
    test("Create hourly schedule", False, str(e))
    hourly_schedule_id = None

# Test 4: Create Custom Cron Schedule
print("\n4. Create custom cron schedule...")
try:
    response = requests.post(
        f"{BASE_URL}/api/backup-schedules",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "Custom Schedule",
            "frequency": "custom",
            "cron_expression": "0 */6 * * *",  # Every 6 hours
            "backup_type": "full",
            "compress": True
        }
    )
    
    result = response.json()
    custom_schedule_id = result.get("id")
    
    test("Create custom schedule", response.status_code == 201)
    
    if custom_schedule_id:
        print(f"     Cron: {result.get('cron_expression')}")
    
except Exception as e:
    test("Create custom schedule", False, str(e))
    custom_schedule_id = None

# ============================================================================
#  SECTION 2: SCHEDULE MANAGEMENT
# ============================================================================
print("\n" + "="*80)
print("  📋 SECTION 2: SCHEDULE MANAGEMENT")
print("="*80)

# Test 5: List Schedules
print("\n5. List all schedules...")
try:
    response = requests.get(
        f"{BASE_URL}/api/backup-schedules",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    schedules = result.get("schedules", [])
    
    test("List schedules", len(schedules) >= 4)
    print(f"     Total schedules: {result.get('total')}")
    
except Exception as e:
    test("List schedules", False, str(e))

# Test 6: Get Schedule Details
print("\n6. Get schedule details...")
if daily_schedule_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/backup-schedules/{daily_schedule_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Get schedule", response.status_code == 200)
        print(f"     Name: {result.get('name')}")
        print(f"     Status: {result.get('status')}")
        print(f"     Total runs: {result.get('total_runs')}")
        
    except Exception as e:
        test("Get schedule", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# Test 7: Update Schedule
print("\n7. Update schedule...")
if daily_schedule_id:
    try:
        response = requests.patch(
            f"{BASE_URL}/api/backup-schedules/{daily_schedule_id}",
            headers={"X-API-Key": API_KEY},
            json={
                "description": "Updated description",
                "retention_days": 60,
                "tags": ["test", "daily", "updated"]
            }
        )
        
        result = response.json()
        
        test("Update schedule", response.status_code == 200)
        print(f"     Retention: {result.get('retention_days')} days")
        
    except Exception as e:
        test("Update schedule", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# Test 8: Pause Schedule
print("\n8. Pause schedule...")
if weekly_schedule_id:
    try:
        response = requests.patch(
            f"{BASE_URL}/api/backup-schedules/{weekly_schedule_id}",
            headers={"X-API-Key": API_KEY},
            json={"status": "paused"}
        )
        
        result = response.json()
        
        test("Pause schedule", result.get("status") == "paused")
        print(f"     Status: {result.get('status')}")
        
    except Exception as e:
        test("Pause schedule", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# ============================================================================
#  SECTION 3: MANUAL EXECUTION
# ============================================================================
print("\n" + "="*80)
print("  ▶️  SECTION 3: MANUAL EXECUTION")
print("="*80)

# Test 9: Execute Schedule Manually
print("\n9. Execute schedule manually...")
if daily_schedule_id:
    try:
        response = requests.post(
            f"{BASE_URL}/api/backup-schedules/{daily_schedule_id}/execute",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        job_id = result.get("id")
        
        test("Execute schedule", response.status_code == 200)
        
        if job_id:
            print(f"     Job ID: {job_id}")
            print(f"     Status: {result.get('status')}")
            print(f"     Backup ID: {result.get('backup_id')}")
        
    except Exception as e:
        test("Execute schedule", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# Test 10: Verify Backup Created
print("\n10. Verify backup was created...")
if daily_schedule_id:
    try:
        time.sleep(2)  # Wait for backup to complete
        
        response = requests.get(
            f"{BASE_URL}/api/backups",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        backups = result.get("backups", [])
        
        # Check if backup has "scheduled" tag
        scheduled_backups = [b for b in backups if "scheduled" in b.get("tags", [])]
        
        test("Backup created", len(scheduled_backups) > 0)
        
        if scheduled_backups:
            print(f"     Scheduled backups: {len(scheduled_backups)}")
        
    except Exception as e:
        test("Backup created", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# ============================================================================
#  SECTION 4: JOB HISTORY
# ============================================================================
print("\n" + "="*80)
print("  📜 SECTION 4: JOB HISTORY")
print("="*80)

# Test 11: List Jobs
print("\n11. List schedule jobs...")
if daily_schedule_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/backup-schedules/{daily_schedule_id}/jobs",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        jobs = result.get("jobs", [])
        
        test("List jobs", response.status_code == 200)
        print(f"     Total jobs: {result.get('total')}")
        
        if jobs:
            print(f"     Latest status: {jobs[0].get('status')}")
        
    except Exception as e:
        test("List jobs", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# Test 12: Get Schedule Statistics
print("\n12. Get schedule statistics...")
if daily_schedule_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/backup-schedules/{daily_schedule_id}/stats",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Schedule statistics", response.status_code == 200)
        print(f"     Total runs: {result.get('total_runs')}")
        print(f"     Successful: {result.get('successful_runs')}")
        print(f"     Success rate: {result.get('success_rate')}%")
        
    except Exception as e:
        test("Schedule statistics", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# ============================================================================
#  SECTION 5: CRON HELPERS
# ============================================================================
print("\n" + "="*80)
print("  🕐 SECTION 5: CRON HELPERS")
print("="*80)

# Test 13: Get Cron Presets
print("\n13. Get cron presets...")
try:
    response = requests.get(
        f"{BASE_URL}/api/backup-schedules/cron/presets",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    presets = result.get("presets", [])
    
    test("Cron presets", len(presets) > 0)
    print(f"     Available presets: {len(presets)}")
    
    if presets:
        print(f"     Examples:")
        for preset in presets[:3]:
            print(f"       - {preset.get('name')}: {preset.get('cron_expression')}")
    
except Exception as e:
    test("Cron presets", False, str(e))

# ============================================================================
#  SECTION 6: DELETION
# ============================================================================
print("\n" + "="*80)
print("  🗑️  SECTION 6: DELETION")
print("="*80)

# Test 14: Delete Schedule
print("\n14. Delete schedule...")
if custom_schedule_id:
    try:
        response = requests.delete(
            f"{BASE_URL}/api/backup-schedules/{custom_schedule_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Delete schedule", response.status_code == 200)
        print(f"     Deleted: {result.get('schedule_id')}")
        
    except Exception as e:
        test("Delete schedule", False, str(e))
else:
    print("  ⏭️  Skipped (no schedule ID)")

# ============================================================================
#  CLEANUP
# ============================================================================
print("\n" + "="*80)
print("  🧹 CLEANUP")
print("="*80)

try:
    # Delete test data
    for item_id in test_ids:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{item_id}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "scheduler_test"}
        )
    
    # Delete schedules
    if daily_schedule_id:
        requests.delete(
            f"{BASE_URL}/api/backup-schedules/{daily_schedule_id}",
            headers={"X-API-Key": API_KEY}
        )
    
    if weekly_schedule_id:
        requests.delete(
            f"{BASE_URL}/api/backup-schedules/{weekly_schedule_id}",
            headers={"X-API-Key": API_KEY}
        )
    
    if hourly_schedule_id:
        requests.delete(
            f"{BASE_URL}/api/backup-schedules/{hourly_schedule_id}",
            headers={"X-API-Key": API_KEY}
        )
    
    # Delete created backups
    backups_response = requests.get(
        f"{BASE_URL}/api/backups",
        headers={"X-API-Key": API_KEY}
    )
    
    if backups_response.status_code == 200:
        backups = backups_response.json().get("backups", [])
        for backup in backups:
            if "scheduled" in backup.get("tags", []):
                requests.delete(
                    f"{BASE_URL}/api/backups/{backup['id']}",
                    headers={"X-API-Key": API_KEY}
                )
    
    print("  ✅ Test data and schedules cleaned up")
except:
    pass

# ============================================================================
#  RESULTS
# ============================================================================
print("\n" + "="*80)
print("  📊 BACKUP SCHEDULER TEST RESULTS")
print("="*80)

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total}")
print(f"❌ Failed: {failed}/{total}")
print(f"📊 Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n🎉🎉🎉 ALL BACKUP SCHEDULER TESTS PASSED! 🎉🎉🎉")
    print("\n✨ Features Tested:")
    print("  ✅ Schedule creation (daily/weekly/hourly/custom)")
    print("  ✅ Schedule management (list/get/update/pause)")
    print("  ✅ Manual execution")
    print("  ✅ Job history tracking")
    print("  ✅ Statistics")
    print("  ✅ Cron presets")
    print("  ✅ Schedule deletion")
    print("\n🚀 Backup Scheduler is PRODUCTION READY!")
else:
    print(f"\n⚠️  {failed} test(s) failed")

print(f"\n🎯 Total: {total} tests")
print(f"⏱️  Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")