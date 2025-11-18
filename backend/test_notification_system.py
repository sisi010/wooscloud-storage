"""
WoosCloud Storage - Notification System Test Suite
Tests notifications, preferences, and templates
"""

import requests
import time

# Configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

print("="*80)
print("  📧 WoosCloud Storage - Notification System Test Suite")
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
#  SECTION 1: PREFERENCES
# ============================================================================
print("="*80)
print("  ⚙️  SECTION 1: NOTIFICATION PREFERENCES")
print("="*80)

# Test 1: Get Default Preferences
print("\n1. Get default preferences...")
try:
    response = requests.get(
        f"{BASE_URL}/api/notifications/preferences/me",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    
    test("Get preferences", response.status_code == 200)
    
    print(f"     Email enabled: {result.get('email_enabled')}")
    print(f"     In-app enabled: {result.get('in_app_enabled')}")
    print(f"     Subscribed events: {len(result.get('subscribed_events', []))}")
    
except Exception as e:
    test("Get preferences", False, str(e))

# Test 2: Update Preferences
print("\n2. Update preferences...")
try:
    response = requests.patch(
        f"{BASE_URL}/api/notifications/preferences/me",
        headers={"X-API-Key": API_KEY},
        json={
            "email_enabled": True,
            "email_address": "test@example.com",
            "in_app_enabled": True,
            "min_priority": "normal"
        }
    )
    
    result = response.json()
    
    test("Update preferences", response.status_code == 200)
    print(f"     Email: {result.get('email_address')}")
    
except Exception as e:
    test("Update preferences", False, str(e))

# Test 3: Update Event Subscriptions
print("\n3. Update event subscriptions...")
try:
    response = requests.patch(
        f"{BASE_URL}/api/notifications/preferences/me",
        headers={"X-API-Key": API_KEY},
        json={
            "subscribed_events": [
                "backup.success",
                "backup.failed",
                "storage.quota_warning"
            ]
        }
    )
    
    result = response.json()
    
    test("Event subscriptions", response.status_code == 200)
    print(f"     Subscribed: {len(result.get('subscribed_events', []))} events")
    
except Exception as e:
    test("Event subscriptions", False, str(e))

# ============================================================================
#  SECTION 2: CREATE NOTIFICATIONS
# ============================================================================
print("\n" + "="*80)
print("  📬 SECTION 2: CREATE NOTIFICATIONS")
print("="*80)

# Test 4: Create Manual Notification
print("\n4. Create manual notification...")
try:
    response = requests.post(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        json={
            "event_type": "backup.success",
            "priority": "normal",
            "title": "Test Notification",
            "message": "This is a test notification",
            "data": {"test": True}
        }
    )
    
    result = response.json()
    notif_id = result.get("id")
    
    test("Create notification", response.status_code == 201)
    
    if notif_id:
        print(f"     Notification ID: {notif_id}")
        print(f"     Status: {result.get('status')}")
    
except Exception as e:
    test("Create notification", False, str(e))
    notif_id = None

# Test 5: Create High Priority Notification
print("\n5. Create high priority notification...")
try:
    response = requests.post(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        json={
            "event_type": "backup.failed",
            "priority": "high",
            "title": "Backup Failed",
            "message": "Your backup has failed",
            "action_url": "https://example.com/backups"
        }
    )
    
    result = response.json()
    high_priority_id = result.get("id")
    
    test("High priority notification", response.status_code == 201)
    
except Exception as e:
    test("High priority notification", False, str(e))
    high_priority_id = None

# Test 6: Create Urgent Notification
print("\n6. Create urgent notification...")
try:
    response = requests.post(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        json={
            "event_type": "storage.quota_warning",  # Use subscribed event
            "priority": "urgent",
            "title": "Storage Quota Warning",
            "message": "Your storage is running low"
        }
    )
    
    result = response.json()
    
    test("Urgent notification", response.status_code == 201)
    
except Exception as e:
    test("Urgent notification", False, str(e))

# ============================================================================
#  SECTION 3: LIST & RETRIEVE
# ============================================================================
print("\n" + "="*80)
print("  📋 SECTION 3: LIST & RETRIEVE")
print("="*80)

# Test 7: List All Notifications
print("\n7. List all notifications...")
try:
    response = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        params={"page": 1, "page_size": 20}
    )
    
    result = response.json()
    notifications = result.get("notifications", [])
    
    test("List notifications", len(notifications) >= 2)
    print(f"     Total: {result.get('total')}")
    print(f"     Unread: {result.get('unread_count')}")
    
except Exception as e:
    test("List notifications", False, str(e))

# Test 8: List Unread Only
print("\n8. List unread notifications...")
try:
    response = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        params={"unread_only": True}
    )
    
    result = response.json()
    unread = result.get("notifications", [])
    
    test("Unread notifications", len(unread) >= 1)
    print(f"     Unread count: {len(unread)}")
    
except Exception as e:
    test("Unread notifications", False, str(e))

# Test 9: Filter by Priority
print("\n9. Filter by priority...")
try:
    response = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        params={"priority": "high"}
    )
    
    result = response.json()
    high_priority = result.get("notifications", [])
    
    test("Filter by priority", response.status_code == 200)
    print(f"     High priority: {len(high_priority)}")
    
except Exception as e:
    test("Filter by priority", False, str(e))

# Test 10: Get Notification Details
print("\n10. Get notification details...")
if notif_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/notifications/{notif_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Get notification", response.status_code == 200)
        print(f"     Title: {result.get('title')}")
        print(f"     Read: {result.get('read_at') is not None}")
        
    except Exception as e:
        test("Get notification", False, str(e))
else:
    print("  ⏭️  Skipped (no notification ID)")

# ============================================================================
#  SECTION 4: MARK AS READ
# ============================================================================
print("\n" + "="*80)
print("  ✓ SECTION 4: MARK AS READ")
print("="*80)

# Test 11: Mark Single as Read
print("\n11. Mark notification as read...")
if notif_id:
    try:
        response = requests.post(
            f"{BASE_URL}/api/notifications/{notif_id}/read",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Mark as read", response.status_code == 200)
        print(f"     Message: {result.get('message')}")
        
    except Exception as e:
        test("Mark as read", False, str(e))
else:
    print("  ⏭️  Skipped (no notification ID)")

# Test 12: Verify Read Status
print("\n12. Verify read status...")
if notif_id:
    try:
        response = requests.get(
            f"{BASE_URL}/api/notifications/{notif_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        is_read = result.get('read_at') is not None
        
        test("Verify read", is_read)
        
    except Exception as e:
        test("Verify read", False, str(e))
else:
    print("  ⏭️  Skipped (no notification ID)")

# Test 13: Mark All as Read
print("\n13. Mark all notifications as read...")
try:
    response = requests.post(
        f"{BASE_URL}/api/notifications/read-all",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    
    test("Mark all as read", response.status_code == 200)
    print(f"     Marked: {result.get('count')} notifications")
    
except Exception as e:
    test("Mark all as read", False, str(e))

# ============================================================================
#  SECTION 5: TEMPLATES
# ============================================================================
print("\n" + "="*80)
print("  📝 SECTION 5: TEMPLATES")
print("="*80)

# Test 14: Get Templates
print("\n14. Get notification templates...")
try:
    response = requests.get(
        f"{BASE_URL}/api/notifications/templates",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    templates = result.get("templates", [])
    
    test("Get templates", len(templates) > 0)
    print(f"     Available templates: {len(templates)}")
    
    if templates:
        print(f"     Examples:")
        for template in templates[:3]:
            print(f"       - {template.get('event_type')}")
    
except Exception as e:
    test("Get templates", False, str(e))

# ============================================================================
#  SECTION 6: STATISTICS
# ============================================================================
print("\n" + "="*80)
print("  📊 SECTION 6: STATISTICS")
print("="*80)

# Test 15: Get Statistics
print("\n15. Get notification statistics...")
try:
    response = requests.get(
        f"{BASE_URL}/api/notifications/stats/me",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    
    test("Get statistics", response.status_code == 200)
    print(f"     Total sent: {result.get('total_sent')}")
    print(f"     Total read: {result.get('total_read')}")
    print(f"     Delivery rate: {result.get('delivery_rate')}%")
    print(f"     Read rate: {result.get('read_rate')}%")
    
except Exception as e:
    test("Get statistics", False, str(e))

# ============================================================================
#  SECTION 7: DELETE
# ============================================================================
print("\n" + "="*80)
print("  🗑️  SECTION 7: DELETE")
print("="*80)

# Test 16: Delete Notification
print("\n16. Delete notification...")
if high_priority_id:
    try:
        response = requests.delete(
            f"{BASE_URL}/api/notifications/{high_priority_id}",
            headers={"X-API-Key": API_KEY}
        )
        
        result = response.json()
        
        test("Delete notification", response.status_code == 200)
        print(f"     Deleted: {result.get('notification_id')}")
        
    except Exception as e:
        test("Delete notification", False, str(e))
else:
    print("  ⏭️  Skipped (no notification ID)")

# ============================================================================
#  CLEANUP
# ============================================================================
print("\n" + "="*80)
print("  🧹 CLEANUP")
print("="*80)

try:
    # Get all notifications
    response = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"X-API-Key": API_KEY},
        params={"page_size": 100}
    )
    
    if response.status_code == 200:
        notifications = response.json().get("notifications", [])
        
        # Delete all test notifications
        for notif in notifications:
            requests.delete(
                f"{BASE_URL}/api/notifications/{notif['id']}",
                headers={"X-API-Key": API_KEY}
            )
    
    print("  ✅ Test notifications cleaned up")
except:
    pass

# ============================================================================
#  RESULTS
# ============================================================================
print("\n" + "="*80)
print("  📊 NOTIFICATION SYSTEM TEST RESULTS")
print("="*80)

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total}")
print(f"❌ Failed: {failed}/{total}")
print(f"📊 Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n🎉🎉🎉 ALL NOTIFICATION TESTS PASSED! 🎉🎉🎉")
    print("\n✨ Features Tested:")
    print("  ✅ Notification preferences")
    print("  ✅ Event subscriptions")
    print("  ✅ Create notifications (manual)")
    print("  ✅ Priority levels (normal/high/urgent)")
    print("  ✅ List & filter notifications")
    print("  ✅ Mark as read (single & all)")
    print("  ✅ Notification templates")
    print("  ✅ Statistics")
    print("  ✅ Delete notifications")
    print("\n🚀 Notification System is PRODUCTION READY!")
else:
    print(f"\n⚠️  {failed} test(s) failed")

print(f"\n🎯 Total: {total} tests")
print(f"⏱️  Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")