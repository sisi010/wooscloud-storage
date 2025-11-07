"""
Test file upload functionality
"""

from wooscloud import WoosStorage

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "https://wooscloud-storage-production.up.railway.app"

print("="*60)
print("  📁 File Upload Test")
print("="*60)

storage = WoosStorage(api_key=API_KEY, base_url=BASE_URL)

# Test 1: Create a test file
print("\n1. Creating test file...")
with open("test_image.txt", "w", encoding="utf-8") as f:  # UTF-8 추가!
    f.write("This is a test file for WoosCloud Storage!\n")
    f.write("Testing file upload functionality.\n")
    f.write("한글 테스트도 해봅시다! 😊")

print("✅ Test file created: test_image.txt")

# Test 2: Upload file
print("\n2. Uploading file...")
try:
    result = storage.files.upload(
        file_path="test_image.txt",
        collection="test_files",
        description="Test file upload",
        tags=["test", "demo"],
        metadata={"test": True, "version": "1.2.0"}
    )
    
    file_id = result["id"]
    print(f"✅ Upload successful!")
    print(f"   File ID: {file_id}")
    print(f"   Storage: {result['storage_type']}")
    print(f"   Size: {result['size']} bytes")
    
except Exception as e:
    print(f"❌ Upload failed: {e}")
    exit(1)

# Test 3: Get file info
print("\n3. Getting file info...")
try:
    info = storage.files.get_info(file_id)
    print(f"✅ File info retrieved")
    print(f"   Filename: {info['filename']}")
    print(f"   Content-Type: {info['content_type']}")
    print(f"   Collection: {info['collection']}")
    
except Exception as e:
    print(f"❌ Get info failed: {e}")

# Test 4: List files
print("\n4. Listing files...")
try:
    result = storage.files.list(collection="test_files", limit=5)
    print(f"✅ Found {result['total']} file(s)")
    for file in result['files']:
        print(f"   - {file['filename']} ({file['size']} bytes)")
    
except Exception as e:
    print(f"❌ List failed: {e}")

# Test 5: Download file
print("\n5. Downloading file...")
try:
    content = storage.files.download(file_id)
    print(f"✅ Download successful!")
    print(f"   Downloaded {len(content)} bytes")
    print(f"   Content preview: {content[:50].decode('utf-8')}...")
    
except Exception as e:
    print(f"❌ Download failed: {e}")

# Test 6: Download to file
print("\n6. Downloading to file...")
try:
    storage.files.download(file_id, "downloaded_test.txt")
    print(f"✅ Downloaded to: downloaded_test.txt")
    
except Exception as e:
    print(f"❌ Download to file failed: {e}")

# Test 7: Delete file
print("\n7. Deleting file...")
try:
    result = storage.files.delete(file_id)
    print(f"✅ File deleted!")
    print(f"   Freed: {result['freed_bytes']} bytes")
    
except Exception as e:
    print(f"❌ Delete failed: {e}")

print("\n" + "="*60)
print("  ✅ File Upload Test Completed!")
print("="*60)