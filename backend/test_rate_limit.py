"""
Test Rate Limiting functionality
"""

from wooscloud import WoosStorage
import time

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

print("="*70)
print("  ⏱️  Rate Limiting Test")
print("="*70)

# Test 1: Get rate limit info
print("\n1. Getting rate limit info...")
try:
    import requests
    response = requests.get(
        f"{BASE_URL}/api/storage/rate-limit",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        info = response.json()
        print(f"✅ Rate limit info retrieved")
        print(f"   Plan: {info['plan']}")
        
        hourly = info['limits']['hourly']
        print(f"\n   Hourly limit:")
        if hourly['limit'] == -1:
            print(f"     Unlimited")
        else:
            print(f"     Limit: {hourly['limit']}")
            print(f"     Used: {hourly['used']}")
            print(f"     Remaining: {hourly['remaining']}")
        
        monthly = info['limits']['monthly']
        print(f"\n   Monthly limit:")
        if monthly['limit'] == -1:
            print(f"     Unlimited")
        else:
            print(f"     Limit: {monthly['limit']}")
            print(f"     Used: {monthly['used']}")
            print(f"     Remaining: {monthly['remaining']}")
    else:
        print(f"⚠️  Status: {response.status_code}")
        
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 2: Check rate limit headers
print("\n2. Checking rate limit headers...")
try:
    response = requests.get(
        f"{BASE_URL}/api/storage/stats",
        headers={"X-API-Key": API_KEY}
    )
    
    if 'X-RateLimit-Limit' in response.headers:
        print(f"✅ Rate limit headers present")
        print(f"   X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit')}")
        print(f"   X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining')}")
        print(f"   X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset')}")
    else:
        print(f"⚠️  No rate limit headers found")
        
except Exception as e:
    print(f"❌ Failed: {e}")

# Test 3: Rapid requests
print("\n3. Testing rapid requests (10 requests)...")
start_time = time.time()
success_count = 0
rate_limited = False

for i in range(10):
    try:
        storage.save("rate_test", {"index": i, "timestamp": time.time()})
        success_count += 1
        print(f"   Request {i+1}: ✅")
    except Exception as e:
        if "429" in str(e) or "Rate limit" in str(e):
            print(f"   Request {i+1}: ⚠️  Rate limited!")
            rate_limited = True
            break
        else:
            print(f"   Request {i+1}: ❌ {e}")
    
    time.sleep(0.1)  # Small delay

elapsed = time.time() - start_time

print(f"\n   Summary:")
print(f"     Successful: {success_count}/10")
print(f"     Time: {elapsed:.2f}s")
print(f"     Rate limited: {'Yes' if rate_limited else 'No'}")

# Test 4: Get updated rate limit info
print("\n4. Getting updated rate limit info...")
try:
    response = requests.get(
        f"{BASE_URL}/api/storage/rate-limit",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        info = response.json()
        hourly = info['limits']['hourly']
        
        if hourly['limit'] == -1:
            print(f"✅ Hourly: Unlimited (used: {hourly['used']})")
        else:
            print(f"✅ Hourly: {hourly['used']}/{hourly['limit']} ({hourly['remaining']} remaining)")
    
except Exception as e:
    print(f"❌ Failed: {e}")

print("\n" + "="*70)
print("  ✅ Rate Limiting Test Completed!")
print("="*70)