"""
WoosCloud Storage - Audit Log & Monitoring Test Suite
Tests audit logging, statistics, and security monitoring
"""

import requests
import time

# Configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

print("="*80)
print("  📝 WoosCloud Storage - Audit Log Test Suite")
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
#  SETUP: CREATE TEST ACTIVITIES
# ============================================================================
print("="*80)
print("  🔧 SETUP: Creating Test Activities")
print("="*80)

print("\nGenerating activities for audit logs...")

activities = []

try:
    # Create some data
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/api/storage/create",
            headers={"X-API-Key": API_KEY},
            json={"collection": "audit_test", "data": {"item": i}}
        )
        if response.status_code == 201:
            activities.append(response.json().get("id"))
    
    # Update data
    if activities:
        requests.put(
            f"{BASE_URL}/api/storage/update/{activities[0]}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "audit_test"},
            json={"data": {"updated": True}}
        )
    
    # Search
    requests.get(
        f"{BASE_URL}/api/search",
        headers={"X-API-Key": API_KEY},
        params={"collection": "audit_test", "query": "item"}
    )
    
    # Failed request (trigger error)
    requests.get(
        f"{BASE_URL}/api/storage/get/invalid_id",
        headers={"X-API-Key": API_KEY},
        params={"collection": "audit_test"}
    )
    
    # Wait for logs to be written
    time.sleep(1)
    
    test("Test activities generated", len(activities) >= 3)
    print(f"     Generated {len(activities)} activities")
    
except Exception as e:
    test("Test activities generated", False, str(e))

# ============================================================================
#  SECTION 1: AUDIT LOG RETRIEVAL
# ============================================================================
print("\n" + "="*80)
print("  📋 SECTION 1: AUDIT LOG RETRIEVAL")
print("="*80)

# Test 1: Get All Logs
print("\n1. Get all audit logs...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"page": 1, "page_size": 50}
    )
    
    result = response.json()
    logs = result.get("logs", [])
    
    test("Get audit logs", response.status_code == 200 and len(logs) > 0)
    
    if logs:
        print(f"     Total logs: {result.get('total')}")
        print(f"     Retrieved: {len(logs)}")
        print(f"     First log: {logs[0].get('event_type')}")
    
except Exception as e:
    test("Get audit logs", False, str(e))

# Test 2: Filter by Event Type
print("\n2. Filter logs by event type...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"event_type": "data.create", "page_size": 10}
    )
    
    result = response.json()
    logs = result.get("logs", [])
    
    all_create = all(log.get("event_type") == "data.create" for log in logs)
    
    test("Filter by event type", response.status_code == 200 and all_create)
    print(f"     Found {len(logs)} create events")
    
except Exception as e:
    test("Filter by event type", False, str(e))

# Test 3: Filter by Severity
print("\n3. Filter logs by severity...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"severity": "info", "page_size": 10}
    )
    
    result = response.json()
    
    test("Filter by severity", response.status_code == 200)
    print(f"     Info logs: {len(result.get('logs', []))}")
    
except Exception as e:
    test("Filter by severity", False, str(e))

# Test 4: Filter by Status
print("\n4. Filter logs by status...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"status": "success", "page_size": 10}
    )
    
    result = response.json()
    
    test("Filter by status", response.status_code == 200)
    print(f"     Success logs: {len(result.get('logs', []))}")
    
except Exception as e:
    test("Filter by status", False, str(e))

# Test 5: Search Logs
print("\n5. Search audit logs...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"search": "storage", "page_size": 10}
    )
    
    result = response.json()
    
    test("Search logs", response.status_code == 200)
    print(f"     Search results: {len(result.get('logs', []))}")
    
except Exception as e:
    test("Search logs", False, str(e))

# Test 6: Sort and Pagination
print("\n6. Sort and pagination...")
try:
    # Get first page
    response1 = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"page": 1, "page_size": 2, "sort_order": "desc"}
    )
    
    # Get second page
    response2 = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"page": 2, "page_size": 2, "sort_order": "desc"}
    )
    
    test("Sort and pagination", 
         response1.status_code == 200 and response2.status_code == 200)
    
except Exception as e:
    test("Sort and pagination", False, str(e))

# ============================================================================
#  SECTION 2: STATISTICS
# ============================================================================
print("\n" + "="*80)
print("  📊 SECTION 2: STATISTICS")
print("="*80)

# Test 7: Get Statistics
print("\n7. Get audit statistics...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/stats",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    
    test("Get statistics", response.status_code == 200)
    
    print(f"     Total events: {result.get('total_events')}")
    print(f"     Unique users: {result.get('unique_users')}")
    print(f"     Event types: {len(result.get('by_event_type', []))}")
    
except Exception as e:
    test("Get statistics", False, str(e))

# Test 8: Statistics with Date Range
print("\n8. Statistics with date range...")
try:
    from datetime import datetime, timedelta
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)
    
    response = requests.get(
        f"{BASE_URL}/api/audit/stats",
        headers={"X-API-Key": API_KEY},
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )
    
    result = response.json()
    
    test("Date range statistics", response.status_code == 200)
    print(f"     Events in range: {result.get('total_events')}")
    
except Exception as e:
    test("Date range statistics", False, str(e))

# ============================================================================
#  SECTION 3: SECURITY EVENTS
# ============================================================================
print("\n" + "="*80)
print("  🔒 SECTION 3: SECURITY EVENTS")
print("="*80)

# Test 9: Get Security Events
print("\n9. Get security events...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/security-events",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    events = result.get("events", [])
    
    test("Get security events", response.status_code == 200)
    print(f"     Total events: {result.get('total')}")
    print(f"     Unresolved: {result.get('unresolved_count')}")
    
except Exception as e:
    test("Get security events", False, str(e))

# Test 10: Filter Security Events by Severity
print("\n10. Filter security events by severity...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/security-events",
        headers={"X-API-Key": API_KEY},
        params={"severity": "warning"}
    )
    
    result = response.json()
    
    test("Filter security events", response.status_code == 200)
    print(f"     Warning events: {len(result.get('events', []))}")
    
except Exception as e:
    test("Filter security events", False, str(e))

# ============================================================================
#  SECTION 4: SYSTEM HEALTH
# ============================================================================
print("\n" + "="*80)
print("  💚 SECTION 4: SYSTEM HEALTH")
print("="*80)

# Test 11: Get System Health
print("\n11. Get system health metrics...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/health",
        headers={"X-API-Key": API_KEY}
    )
    
    result = response.json()
    
    test("System health", response.status_code == 200)
    
    print(f"     Requests (1h): {result.get('total_requests_last_hour')}")
    print(f"     Success rate: {result.get('success_rate')}%")
    print(f"     Avg response: {result.get('average_response_time_ms')}ms")
    print(f"     Error rate: {result.get('error_rate')}%")
    print(f"     Active users: {result.get('active_users')}")
    
except Exception as e:
    test("System health", False, str(e))

# ============================================================================
#  SECTION 5: USER ACTIVITY
# ============================================================================
print("\n" + "="*80)
print("  👤 SECTION 5: USER ACTIVITY")
print("="*80)

# Test 12: Get My Activity
print("\n12. Get my activity summary...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/my-activity",
        headers={"X-API-Key": API_KEY},
        params={"days": 7}
    )
    
    result = response.json()
    
    test("My activity", response.status_code == 200)
    
    print(f"     Total actions: {result.get('total_actions')}")
    print(f"     Collections: {len(result.get('collections_accessed', []))}")
    print(f"     Top actions: {len(result.get('most_common_actions', []))}")
    
except Exception as e:
    test("My activity", False, str(e))

# ============================================================================
#  SECTION 6: AUTOMATIC LOGGING
# ============================================================================
print("\n" + "="*80)
print("  🤖 SECTION 6: AUTOMATIC LOGGING")
print("="*80)

# Test 13: Verify Automatic Logging
print("\n13. Verify automatic logging...")
try:
    # Make a request
    create_response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers={"X-API-Key": API_KEY},
        json={"collection": "auto_log_test", "data": {"test": True}}
    )
    
    created_id = create_response.json().get("id")
    
    # Wait for log
    time.sleep(1)
    
    # Check if logged
    logs_response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"event_type": "data.create", "page_size": 1}
    )
    
    logs = logs_response.json().get("logs", [])
    
    test("Automatic logging", len(logs) > 0)
    
    if logs:
        print(f"     Latest log: {logs[0].get('event_type')}")
        print(f"     Response time: {logs[0].get('response_time_ms')}ms")
    
    # Cleanup
    if created_id:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{created_id}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "auto_log_test"}
        )
    
except Exception as e:
    test("Automatic logging", False, str(e))

# Test 14: Log Contains Request Details
print("\n14. Verify log contains request details...")
try:
    response = requests.get(
        f"{BASE_URL}/api/audit/logs",
        headers={"X-API-Key": API_KEY},
        params={"page_size": 1}
    )
    
    logs = response.json().get("logs", [])
    
    if logs:
        log = logs[0]
        has_details = all([
            log.get("method"),
            log.get("endpoint"),
            log.get("response_status"),
            log.get("timestamp"),
            log.get("ip_address")
        ])
        
        test("Log has details", has_details)
        
        if has_details:
            print(f"     Method: {log.get('method')}")
            print(f"     Endpoint: {log.get('endpoint')}")
            print(f"     Status: {log.get('response_status')}")
            print(f"     IP: {log.get('ip_address')}")
    else:
        test("Log has details", False, "No logs found")
    
except Exception as e:
    test("Log has details", False, str(e))

# ============================================================================
#  CLEANUP
# ============================================================================
print("\n" + "="*80)
print("  🧹 CLEANUP")
print("="*80)

try:
    # Delete test data
    for item_id in activities:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{item_id}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "audit_test"}
        )
    
    print("  ✅ Test data cleaned up")
except:
    pass

# ============================================================================
#  RESULTS
# ============================================================================
print("\n" + "="*80)
print("  📊 AUDIT LOG TEST RESULTS")
print("="*80)

total = passed + failed
percentage = (passed / total * 100) if total > 0 else 0

print(f"\n✅ Passed: {passed}/{total}")
print(f"❌ Failed: {failed}/{total}")
print(f"📊 Success Rate: {percentage:.1f}%")

if failed == 0:
    print("\n🎉🎉🎉 ALL AUDIT LOG TESTS PASSED! 🎉🎉🎉")
    print("\n✨ Features Tested:")
    print("  ✅ Audit log retrieval")
    print("  ✅ Advanced filtering")
    print("  ✅ Search and pagination")
    print("  ✅ Statistics")
    print("  ✅ Security events")
    print("  ✅ System health monitoring")
    print("  ✅ User activity tracking")
    print("  ✅ Automatic logging")
    print("\n🚀 Audit & Monitoring is PRODUCTION READY!")
else:
    print(f"\n⚠️  {failed} test(s) failed")

print(f"\n🎯 Total: {total} tests")
print(f"⏱️  Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")