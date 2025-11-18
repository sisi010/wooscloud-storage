"""
Quick Test: Populate Functionality Only
Tests only the populate endpoint to speed up debugging
"""

import requests
import sys

# Configuration
API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

def test(name, condition, error=""):
    """Simple test helper"""
    if condition:
        print(f"  ✅ {name}")
        return True
    else:
        print(f"  ❌ {name}")
        if error:
            print(f"     Error: {error}")
        return False

print("="*80)
print("  ⚡ QUICK POPULATE TEST")
print("="*80)

# Step 1: Create a user
print("\n1. Creating test user...")
try:
    user_response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers={"X-API-Key": API_KEY},
        json={
            "collection": "quick_test_users",
            "data": {
                "name": "Quick Test User",
                "email": "quick@test.com"
            }
        }
    )
    user_id = user_response.json().get("id")
    test("User created", user_response.status_code == 201)
    print(f"     User ID: {user_id}")
except Exception as e:
    test("User created", False, str(e))
    sys.exit(1)

# Step 2: Create posts
print("\n2. Creating test posts...")
post_ids = []
try:
    for i in range(2):
        post_response = requests.post(
            f"{BASE_URL}/api/storage/create",
            headers={"X-API-Key": API_KEY},
            json={
                "collection": "quick_test_posts",
                "data": {
                    "title": f"Quick Post {i+1}",
                    "content": f"Content {i+1}",
                    "author_id": user_id
                }
            }
        )
        if post_response.status_code == 201:
            post_ids.append(post_response.json().get("id"))
    
    test("Posts created", len(post_ids) == 2)
    print(f"     Post IDs: {post_ids}")
except Exception as e:
    test("Posts created", False, str(e))
    sys.exit(1)

# Step 3: Create user with posts
print("\n3. Creating user with posts array...")
try:
    user_with_posts_response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers={"X-API-Key": API_KEY},
        json={
            "collection": "quick_test_users",
            "data": {
                "name": "User With Posts",
                "email": "withposts@test.com",
                "posts": post_ids
            }
        }
    )
    user_with_posts_id = user_with_posts_response.json().get("id")
    test("User with posts created", user_with_posts_response.status_code == 201)
    print(f"     User ID: {user_with_posts_id}")
except Exception as e:
    test("User with posts created", False, str(e))
    sys.exit(1)

# Step 4: Verify user has posts
print("\n4. Verifying user has posts array...")
try:
    verify_response = requests.get(
        f"{BASE_URL}/api/storage/read/{user_with_posts_id}",
        headers={"X-API-Key": API_KEY},
        params={"collection": "quick_test_users"}
    )
    user_data = verify_response.json().get("data", {})
    has_posts = "posts" in user_data
    posts_count = len(user_data.get("posts", []))
    
    test("User has posts array", has_posts and posts_count == 2)
    print(f"     Posts: {user_data.get('posts')}")
except Exception as e:
    test("User has posts array", False, str(e))
    sys.exit(1)

# Step 5: Create relationship
print("\n5. Creating relationship...")
try:
    rel_response = requests.post(
        f"{BASE_URL}/api/relationships",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "quick_test_user_posts",
            "from_collection": "quick_test_users",
            "to_collection": "quick_test_posts",
            "from_field": "posts",
            "relation_type": "one_to_many"
        }
    )
    rel_id = rel_response.json().get("id")
    test("Relationship created", rel_response.status_code == 201)
    print(f"     Relationship ID: {rel_id}")
except Exception as e:
    test("Relationship created", False, str(e))
    sys.exit(1)

# Step 6: TEST POPULATE!
print("\n6. Testing populate endpoint...")
try:
    populate_response = requests.get(
        f"{BASE_URL}/api/relationships/populate/{user_with_posts_id}",
        headers={"X-API-Key": API_KEY},
        params={
            "collection": "quick_test_users",
            "fields": ["posts"],
            "depth": 1
        }
    )
    
    print(f"     Status Code: {populate_response.status_code}")
    
    if populate_response.status_code == 200:
        result = populate_response.json()
        data = result.get("data", {})
        posts = data.get("posts", [])
        
        print(f"     Response: {result}")
        print(f"     Populated posts count: {len(posts) if isinstance(posts, list) else 0}")
        
        if isinstance(posts, list) and len(posts) > 0:
            print(f"     First post: {posts[0] if posts else 'None'}")
            test("Populate SUCCESS", isinstance(posts[0], dict))
        else:
            test("Populate FAILED", False, f"Posts is not populated: {posts}")
    else:
        print(f"     Error: {populate_response.json()}")
        test("Populate endpoint", False, f"Status {populate_response.status_code}")
        
except Exception as e:
    test("Populate endpoint", False, str(e))

# Cleanup
print("\n7. Cleaning up...")
try:
    # Delete users
    requests.delete(
        f"{BASE_URL}/api/storage/delete/{user_id}",
        headers={"X-API-Key": API_KEY},
        params={"collection": "quick_test_users"}
    )
    requests.delete(
        f"{BASE_URL}/api/storage/delete/{user_with_posts_id}",
        headers={"X-API-Key": API_KEY},
        params={"collection": "quick_test_users"}
    )
    
    # Delete posts
    for post_id in post_ids:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{post_id}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "quick_test_posts"}
        )
    
    # Delete relationship
    requests.delete(
        f"{BASE_URL}/api/relationships/{rel_id}",
        headers={"X-API-Key": API_KEY}
    )
    
    print("  ✅ Cleanup complete")
except Exception as e:
    print(f"  ⚠️  Cleanup error: {e}")

print("\n" + "="*80)
print("  ⚡ QUICK TEST COMPLETE")
print("="*80)