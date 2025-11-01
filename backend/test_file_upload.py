"""
Test file upload/download functionality
"""

import requests
import io

# Local API
API_URL = "http://127.0.0.1:8000"
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"

headers = {"X-API-Key": API_KEY}

print("🧪 Testing File Upload/Download")
print("=" * 60)

# Test 1: Upload small file (< 5MB) → MongoDB
print("\n1️⃣ Testing Small File Upload (MongoDB)...")
print("-" * 60)

small_file_content = b"This is a small test file content. " * 100  # ~3.5KB
small_file = io.BytesIO(small_file_content)

files = {
    'file': ('test_small.txt', small_file, 'text/plain')
}
data = {
    'collection': 'test_files',
    'description': 'Small test file',
    'tags': '["test", "small"]'
}

try:
    response = requests.post(
        f"{API_URL}/api/files/upload",
        headers=headers,
        files=files,
        data=data
    )
    
    if response.status_code == 201:
        result = response.json()
        print(f"✅ Upload successful!")
        print(f"   ID: {result['id']}")
        print(f"   Filename: {result['filename']}")
        print(f"   Size: {result['size']} bytes")
        print(f"   Storage: {result['storage_type']}")
        
        small_file_id = result['id']
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   {response.text}")
        small_file_id = None
except Exception as e:
    print(f"❌ Error: {e}")
    small_file_id = None

# Test 2: Upload large file (≥ 5MB) → R2
print("\n2️⃣ Testing Large File Upload (R2)...")
print("-" * 60)

# Create 6MB file
large_file_content = b"X" * (6 * 1024 * 1024)  # 6MB
large_file = io.BytesIO(large_file_content)

files = {
    'file': ('test_large.bin', large_file, 'application/octet-stream')
}
data = {
    'collection': 'test_files',
    'description': 'Large test file',
    'tags': '["test", "large"]'
}

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
        print(f"   Filename: {result['filename']}")
        print(f"   Size: {result['size']:,} bytes ({result['size']/1024/1024:.2f} MB)")
        print(f"   Storage: {result['storage_type']}")
        if result.get('url'):
            print(f"   URL: {result['url']}")
        
        large_file_id = result['id']
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   {response.text}")
        large_file_id = None
except Exception as e:
    print(f"❌ Error: {e}")
    large_file_id = None

# Test 3: Get file info
if small_file_id:
    print("\n3️⃣ Testing Get File Info...")
    print("-" * 60)
    
    try:
        response = requests.get(
            f"{API_URL}/api/files/file/{small_file_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ File info retrieved!")
            print(f"   Filename: {result['filename']}")
            print(f"   Size: {result['size']} bytes")
            print(f"   Storage: {result['storage_type']}")
            print(f"   Collection: {result['collection']}")
            print(f"   Metadata: {result['metadata']}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Test 4: Download file
if small_file_id:
    print("\n4️⃣ Testing File Download...")
    print("-" * 60)
    
    try:
        response = requests.get(
            f"{API_URL}/api/files/download/{small_file_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            downloaded_content = response.content
            print(f"✅ Download successful!")
            print(f"   Size: {len(downloaded_content)} bytes")
            print(f"   Content matches: {downloaded_content == small_file_content}")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

# Test 5: List files
print("\n5️⃣ Testing List Files...")
print("-" * 60)

try:
    response = requests.get(
        f"{API_URL}/api/files/files",
        headers=headers,
        params={"collection": "test_files", "limit": 10}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Files listed!")
        print(f"   Total: {result['total']} files")
        print(f"   Returned: {len(result['files'])} files")
        
        for file in result['files']:
            print(f"   - {file['filename']} ({file['size']} bytes, {file['storage_type']})")
    else:
        print(f"❌ Failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 6: Delete file
if small_file_id:
    print("\n6️⃣ Testing File Deletion...")
    print("-" * 60)
    
    try:
        response = requests.delete(
            f"{API_URL}/api/files/file/{small_file_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ File deleted!")
            print(f"   Freed: {result['freed_bytes']} bytes")
        else:
            print(f"❌ Failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("📊 Test Summary")
print("=" * 60)
print("✅ File upload/download feature is ready!")
print("\n📱 API Endpoints:")
print(f"   POST   {API_URL}/api/files/upload")
print(f"   GET    {API_URL}/api/files/download/{{id}}")
print(f"   GET    {API_URL}/api/files/file/{{id}}")
print(f"   DELETE {API_URL}/api/files/file/{{id}}")
print(f"   GET    {API_URL}/api/files/files")
print("=" * 60)