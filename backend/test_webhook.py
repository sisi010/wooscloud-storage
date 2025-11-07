"""
Test webhook functionality
"""

from wooscloud import WoosStorage
import time

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

print("="*60)
print("  🔔 Webhook Test")
print("="*60)

# Your webhook.site URL
webhook_url = "https://webhook.site/0697bb6d-d610-466f-aa2d-5d9a7241d897"

# Test 1: Create webhook
print("\n1. Creating webhook...")
try:
    webhook = storage.webhooks.create(
        url=webhook_url,
        events=["data.created", "file.uploaded"],
        description="Test webhook"
    )
    
    webhook_id = webhook["id"]
    secret = webhook["secret"]
    
    print(f"✅ Webhook created!")
    print(f"   ID: {webhook_id}")
    print(f"   Secret: {secret[:20]}...")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2: List webhooks
print("\n2. Listing webhooks...")
webhooks = storage.webhooks.list()
print(f"✅ Found {len(webhooks)} webhook(s)")
for wh in webhooks:
    print(f"   - {wh['url']}")

# Test 3: Test webhook
print("\n3. Testing webhook...")
result = storage.webhooks.test(webhook_id)
if result['success']:
    print(f"✅ Webhook works! ({result.get('response_time_ms', 0)}ms)")
else:
    print(f"⚠️  {result['message']}")

# Test 4: Trigger event by creating data
print("\n4. Creating data to trigger webhook...")
data_id = storage.save("webhook_test", {"message": "Hello Webhook!", "timestamp": "now"})
print(f"✅ Data created: {data_id}")
print(f"   📡 Check webhook.site for the event!")

time.sleep(2)  # Wait for webhook delivery

# Test 5: Get logs
print("\n5. Getting webhook logs...")
try:
    logs = storage.webhooks.get_logs(webhook_id, limit=5)
    print(f"✅ Found {len(logs)} log(s)")
    for log in logs:
        status = "✅" if log['success'] else "❌"
        print(f"   {status} {log['event']} - Status: {log['status_code']}")
except Exception as e:
    print(f"⚠️  Could not get logs: {e}")

# Test 6: Delete webhook
print("\n6. Deleting webhook...")
storage.webhooks.delete(webhook_id)
print("✅ Webhook deleted")

print("\n" + "="*60)
print("  ✅ Webhook Test Completed!")
print("="*60)
print(f"\n📡 View all events at: {webhook_url}")