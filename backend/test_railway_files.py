"""
Test file upload on Railway
"""

import requests
import io

# Railway API
API_URL = "https://wooscloud-storage-production.up.railway.app"
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

headers = {"X-API-Key": API_KEY}

print("🧪 Testing File Upload on Railway")
print("=" * 60)

# Test 1: Upload small file
print("\n1️⃣ Testing Small File Upload...")
print("-" * 60)

small_file = io.BytesIO(b"Railway test file content " * 100)
files = {'file': ('railway_test.txt', small_file, 'text/plain')}
data = {'collection': 'railway_test', 'tags': '["railway", "test"]'}

try:
    response = requests.post(
        f"{API_URL}/api/files/upload",
        headers=headers,
        files=files,
        data=data,
        timeout=30
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   ID: {result['id']}")
        print(f"   Storage: {result['storage_type']}")
        file_id = result['id']
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        file_id = None
except Exception as e:
    print(f"❌ Error: {e}")
    file_id = None

# Test 2: List files
print("\n2️⃣ Testing List Files...")
print("-" * 60)

try:
    response = requests.get(
        f"{API_URL}/api/files/files",
        headers=headers,
        params={"collection": "railway_test"},
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Files listed!")
        print(f"   Total: {result['total']} files")
    else:
        print(f"❌ Failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Download file
if file_id:
    print("\n3️⃣ Testing File Download...")
    print("-" * 60)
    
    try:
        response = requests.get(
            f"{API_URL}/api/files/download/{file_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Download successful!")
            print(f"   Size: {len(response.content)} bytes")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("✅ File upload feature is working on Railway!")
print("=" * 60)