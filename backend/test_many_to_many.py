"""
Many-to-Many Relationship Test
Tests for M:N relationships (e.g., Users follow Users, Posts have Tags)
"""

import requests

API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
BASE_URL = "http://127.0.0.1:8000"

def test(name, condition, error=""):
    if condition:
        print(f"  ✅ {name}")
        return True
    else:
        print(f"  ❌ {name}")
        if error:
            print(f"     Error: {error}")
        return False

print("="*80)
print("  🔗 MANY-TO-MANY RELATIONSHIP TEST")
print("="*80)

# Create users
print("\n1. Creating users...")
user_ids = []
try:
    for i in range(3):
        response = requests.post(
            f"{BASE_URL}/api/storage/create",
            headers={"X-API-Key": API_KEY},
            json={
                "collection": "test_users_mn",
                "data": {
                    "name": f"User {i+1}",
                    "email": f"user{i+1}@test.com"
                }
            }
        )
        if response.status_code == 201:
            user_ids.append(response.json()["id"])
    
    test("Users created", len(user_ids) == 3)
    print(f"     User IDs: {user_ids}")
except Exception as e:
    test("Users created", False, str(e))

# Create tags
print("\n2. Creating tags...")
tag_ids = []
try:
    for i in range(4):
        response = requests.post(
            f"{BASE_URL}/api/storage/create",
            headers={"X-API-Key": API_KEY},
            json={
                "collection": "test_tags",
                "data": {
                    "name": f"Tag {i+1}",
                    "color": f"#00000{i}"
                }
            }
        )
        if response.status_code == 201:
            tag_ids.append(response.json()["id"])
    
    test("Tags created", len(tag_ids) == 4)
    print(f"     Tag IDs: {tag_ids}")
except Exception as e:
    test("Tags created", False, str(e))

# Create M:N relationship: Users follow Users
print("\n3. Creating 'Users follow Users' relationship...")
try:
    response = requests.post(
        f"{BASE_URL}/api/relationships",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "user_followers",
            "from_collection": "test_users_mn",
            "to_collection": "test_users_mn",
            "from_field": "following",
            "relation_type": "many_to_many",
            "description": "Users can follow other users"
        }
    )
    user_follow_rel_id = response.json().get("id")
    test("User follow relationship", response.status_code == 201)
    print(f"     Relationship ID: {user_follow_rel_id}")
except Exception as e:
    test("User follow relationship", False, str(e))

# Create M:N relationship: Posts have Tags
print("\n4. Creating 'Posts have Tags' relationship...")
try:
    response = requests.post(
        f"{BASE_URL}/api/relationships",
        headers={"X-API-Key": API_KEY},
        json={
            "name": "post_tags",
            "from_collection": "test_posts_mn",
            "to_collection": "test_tags",
            "from_field": "tags",
            "relation_type": "many_to_many"
        }
    )
    post_tag_rel_id = response.json().get("id")
    test("Post tags relationship", response.status_code == 201)
except Exception as e:
    test("Post tags relationship", False, str(e))

# User 1 follows User 2 and User 3
print("\n5. User 1 follows others...")
try:
    response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers={"X-API-Key": API_KEY},
        json={
            "collection": "test_users_mn",
            "data": {
                "name": "User 1 Updated",
                "email": "user1@test.com",
                "following": [user_ids[1], user_ids[2]]
            }
        }
    )
    user1_updated_id = response.json().get("id")
    test("User follows others", response.status_code == 201)
    print(f"     Following: {[user_ids[1], user_ids[2]]}")
except Exception as e:
    test("User follows others", False, str(e))

# Create post with tags
print("\n6. Creating post with tags...")
try:
    response = requests.post(
        f"{BASE_URL}/api/storage/create",
        headers={"X-API-Key": API_KEY},
        json={
            "collection": "test_posts_mn",
            "data": {
                "title": "Test Post",
                "content": "Content here",
                "tags": [tag_ids[0], tag_ids[1], tag_ids[2]]
            }
        }
    )
    post_id = response.json().get("id")
    test("Post with tags", response.status_code == 201)
    print(f"     Post ID: {post_id}")
    print(f"     Tags: {[tag_ids[0], tag_ids[1], tag_ids[2]]}")
except Exception as e:
    test("Post with tags", False, str(e))

# Populate: User with following
print("\n7. Populate user following...")
try:
    response = requests.get(
        f"{BASE_URL}/api/relationships/populate/{user1_updated_id}",
        headers={"X-API-Key": API_KEY},
        params={
            "collection": "test_users_mn",
            "fields": ["following"],
            "depth": 1
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        following = result.get("data", {}).get("following", [])
        test("Populate following", isinstance(following, list) and len(following) > 0)
        print(f"     Following count: {len(following)}")
        if following:
            print(f"     First followed user: {following[0].get('name')}")
    else:
        test("Populate following", False, f"Status {response.status_code}")
        
except Exception as e:
    test("Populate following", False, str(e))

# Populate: Post with tags
print("\n8. Populate post tags...")
try:
    response = requests.get(
        f"{BASE_URL}/api/relationships/populate/{post_id}",
        headers={"X-API-Key": API_KEY},
        params={
            "collection": "test_posts_mn",
            "fields": ["tags"],
            "depth": 1
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        tags = result.get("data", {}).get("tags", [])
        test("Populate tags", isinstance(tags, list) and len(tags) > 0)
        print(f"     Tags count: {len(tags)}")
        if tags:
            print(f"     Tag names: {[t.get('name') for t in tags]}")
    else:
        test("Populate tags", False, f"Status {response.status_code}")
        
except Exception as e:
    test("Populate tags", False, str(e))

# Cleanup
print("\n9. Cleaning up...")
try:
    # Delete users
    for uid in user_ids + [user1_updated_id]:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{uid}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "test_users_mn"}
        )
    
    # Delete tags
    for tid in tag_ids:
        requests.delete(
            f"{BASE_URL}/api/storage/delete/{tid}",
            headers={"X-API-Key": API_KEY},
            params={"collection": "test_tags"}
        )
    
    # Delete post
    requests.delete(
        f"{BASE_URL}/api/storage/delete/{post_id}",
        headers={"X-API-Key": API_KEY},
        params={"collection": "test_posts_mn"}
    )
    
    # Delete relationships
    requests.delete(
        f"{BASE_URL}/api/relationships/{user_follow_rel_id}",
        headers={"X-API-Key": API_KEY}
    )
    requests.delete(
        f"{BASE_URL}/api/relationships/{post_tag_rel_id}",
        headers={"X-API-Key": API_KEY}
    )
    
    print("  ✅ Cleanup complete")
except Exception as e:
    print(f"  ⚠️  Cleanup error: {e}")

print("\n" + "="*80)
print("  🔗 MANY-TO-MANY TEST COMPLETE")
print("="*80)