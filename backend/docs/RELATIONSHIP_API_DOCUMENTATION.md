# Relationship System API Documentation

## Overview

The Relationship System provides a complete solution for managing data relationships in WoosCloud Storage. It supports:

- **One-to-One (1:1)** relationships
- **One-to-Many (1:N)** relationships  
- **Many-to-Many (M:N)** relationships
- **Populate** - Automatic reference resolution
- **Validation** - Reference integrity checking
- **Cascade Operations** - Automatic delete/update handling

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Relationship Types](#relationship-types)
3. [API Endpoints](#api-endpoints)
4. [Populate](#populate)
5. [Validation](#validation)
6. [Cascade Actions](#cascade-actions)
7. [Examples](#examples)
8. [Best Practices](#best-practices)

---

## Quick Start

### 1. Create a Relationship

```python
import requests

response = requests.post(
    "http://127.0.0.1:8000/api/relationships",
    headers={"X-API-Key": "your_api_key"},
    json={
        "name": "user_posts",
        "from_collection": "users",
        "to_collection": "posts",
        "from_field": "posts",
        "relation_type": "one_to_many",
        "description": "User has many posts"
    }
)

relationship_id = response.json()["id"]
```

### 2. Create Data with References

```python
# Create user with post references
response = requests.post(
    "http://127.0.0.1:8000/api/storage/create",
    headers={"X-API-Key": "your_api_key"},
    json={
        "collection": "users",
        "data": {
            "name": "John Doe",
            "posts": ["post_id_1", "post_id_2"]
        }
    }
)

user_id = response.json()["id"]
```

### 3. Populate References

```python
# Get user with populated posts
response = requests.get(
    f"http://127.0.0.1:8000/api/relationships/populate/{user_id}",
    headers={"X-API-Key": "your_api_key"},
    params={
        "collection": "users",
        "fields": ["posts"],
        "depth": 1
    }
)

data = response.json()["data"]
# data["posts"] now contains full post objects instead of IDs
```

---

## Relationship Types

### One-to-One (1:1)

**Use Case:** User has one Profile

```json
{
  "name": "user_profile",
  "from_collection": "users",
  "to_collection": "profiles",
  "from_field": "profile_id",
  "relation_type": "one_to_one"
}
```

**Data Structure:**
```json
{
  "name": "John",
  "profile_id": "profile_123"
}
```

### One-to-Many (1:N)

**Use Case:** User has many Posts

```json
{
  "name": "user_posts",
  "from_collection": "users",
  "to_collection": "posts",
  "from_field": "posts",
  "relation_type": "one_to_many"
}
```

**Data Structure:**
```json
{
  "name": "John",
  "posts": ["post_1", "post_2", "post_3"]
}
```

### Many-to-Many (M:N)

**Use Case:** Users follow Users, Posts have Tags

```json
{
  "name": "user_followers",
  "from_collection": "users",
  "to_collection": "users",
  "from_field": "following",
  "relation_type": "many_to_many"
}
```

**Data Structure:**
```json
{
  "name": "John",
  "following": ["user_2", "user_3", "user_4"]
}
```

---

## API Endpoints

### Create Relationship

**POST** `/api/relationships`

```json
{
  "name": "string",
  "from_collection": "string",
  "to_collection": "string",
  "from_field": "string",
  "relation_type": "one_to_one | one_to_many | many_to_many",
  "required": false,
  "on_delete": "none | cascade | set_null | restrict",
  "on_update": "none | cascade",
  "description": "string",
  "tags": ["string"]
}
```

### List Relationships

**GET** `/api/relationships`

**Query Parameters:**
- `from_collection` (optional) - Filter by source collection
- `to_collection` (optional) - Filter by target collection

### Get Relationship

**GET** `/api/relationships/{relationship_id}`

### Update Relationship

**PATCH** `/api/relationships/{relationship_id}`

```json
{
  "on_delete": "cascade",
  "required": true,
  "description": "Updated description"
}
```

### Delete Relationship

**DELETE** `/api/relationships/{relationship_id}`

---

## Populate

Populate automatically resolves references and replaces IDs with full objects.

### Basic Populate

**GET** `/api/relationships/populate/{document_id}`

**Query Parameters:**
- `collection` (required) - Collection name
- `fields` (required) - Fields to populate (array)
- `depth` (optional) - Nesting depth (1-3, default: 1)

### Example

**Request:**
```http
GET /api/relationships/populate/user_123?collection=users&fields=posts&depth=1
```

**Before Populate:**
```json
{
  "name": "John",
  "posts": ["post_1", "post_2"]
}
```

**After Populate:**
```json
{
  "name": "John",
  "posts": [
    {
      "id": "post_1",
      "title": "First Post",
      "content": "..."
    },
    {
      "id": "post_2",
      "title": "Second Post",
      "content": "..."
    }
  ]
}
```

### Nested Populate (depth > 1)

```http
GET /api/relationships/populate/post_123?collection=posts&fields=author,comments&depth=2
```

Will populate:
1. Post → Author (depth 1)
2. Post → Comments (depth 1)
3. Comments → Authors (depth 2)

---

## Validation

Validate reference integrity before saving data.

### Validate References

**POST** `/api/relationships/validate`

**Query Parameters:**
- `collection` (required)

**Body:**
```json
{
  "name": "John",
  "posts": ["post_1", "post_2"],
  "profile_id": "profile_123"
}
```

**Response:**
```json
{
  "total_checked": 3,
  "valid_count": 2,
  "invalid_count": 1,
  "results": [
    {
      "valid": true,
      "field": "posts",
      "collection": "posts",
      "reference_id": "post_1",
      "exists": true
    },
    {
      "valid": false,
      "field": "posts",
      "collection": "posts",
      "reference_id": "post_2",
      "exists": false,
      "error_message": "Referenced document not found"
    }
  ]
}
```

---

## Cascade Actions

Control what happens when referenced documents are deleted or updated.

### Cascade Action Types

| Action | Description |
|--------|-------------|
| `none` | Do nothing (default) |
| `cascade` | Delete/update related documents |
| `set_null` | Set reference to null |
| `restrict` | Prevent deletion if references exist |

### Examples

#### CASCADE Delete

```json
{
  "name": "user_posts",
  "on_delete": "cascade"
}
```

When User is deleted → All Posts are deleted

#### SET_NULL

```json
{
  "name": "post_author",
  "on_delete": "set_null"
}
```

When User is deleted → `author_id` in Posts becomes null

#### RESTRICT

```json
{
  "name": "user_posts",
  "on_delete": "restrict"
}
```

When User is deleted → Error if Posts exist

---

## Examples

### Example 1: Blog System

```python
# 1. Create relationships
requests.post("/api/relationships", json={
    "name": "user_posts",
    "from_collection": "users",
    "to_collection": "posts",
    "from_field": "posts",
    "relation_type": "one_to_many",
    "on_delete": "cascade"
})

requests.post("/api/relationships", json={
    "name": "post_author",
    "from_collection": "posts",
    "to_collection": "users",
    "from_field": "author_id",
    "relation_type": "one_to_one",
    "required": true
})

requests.post("/api/relationships", json={
    "name": "post_comments",
    "from_collection": "posts",
    "to_collection": "comments",
    "from_field": "comments",
    "relation_type": "one_to_many"
})

# 2. Create data
user = requests.post("/api/storage/create", json={
    "collection": "users",
    "data": {"name": "John", "email": "john@example.com"}
}).json()

post = requests.post("/api/storage/create", json={
    "collection": "posts",
    "data": {
        "title": "My Post",
        "content": "...",
        "author_id": user["id"]
    }
}).json()

# 3. Populate
result = requests.get(
    f"/api/relationships/populate/{post['id']}",
    params={
        "collection": "posts",
        "fields": ["author_id"],
        "depth": 1
    }
).json()

print(result["data"]["author_id"]["name"])  # "John"
```

### Example 2: Social Network

```python
# Users follow Users (M:N)
requests.post("/api/relationships", json={
    "name": "user_followers",
    "from_collection": "users",
    "to_collection": "users",
    "from_field": "following",
    "relation_type": "many_to_many"
})

# User follows others
requests.post("/api/storage/create", json={
    "collection": "users",
    "data": {
        "name": "Alice",
        "following": ["user_bob_id", "user_charlie_id"]
    }
})

# Populate to get full user objects
result = requests.get(
    f"/api/relationships/populate/alice_id",
    params={
        "collection": "users",
        "fields": ["following"],
        "depth": 1
    }
).json()

# result["data"]["following"] = [
#   {"name": "Bob", ...},
#   {"name": "Charlie", ...}
# ]
```

---

## Best Practices

### 1. Name Relationships Clearly

✅ **Good:**
```json
{"name": "user_posts"}
{"name": "post_author"}
{"name": "order_items"}
```

❌ **Bad:**
```json
{"name": "rel1"}
{"name": "data"}
```

### 2. Use Appropriate Cascade Actions

- **CASCADE**: Parent-child relationships (User → Posts)
- **SET_NULL**: Optional relationships (Post → Featured Image)
- **RESTRICT**: Critical relationships (Order → Payment)

### 3. Validate Before Saving

```python
# Always validate references
validation = requests.post("/api/relationships/validate", 
    params={"collection": "users"},
    json=user_data
).json()

if validation["invalid_count"] > 0:
    print("Invalid references!")
    return
```

### 4. Use Depth Wisely

- **depth=1**: Most common, good performance
- **depth=2**: Nested relationships, moderate performance
- **depth=3**: Deep nesting, slower performance

### 5. Cache Frequently Accessed Data

The system includes built-in caching:
- Relationships cached for 5 minutes
- Documents cached for 1 minute

### 6. Add Descriptions and Tags

```json
{
  "name": "user_posts",
  "description": "User has many blog posts",
  "tags": ["blog", "content", "public"]
}
```

---

## Performance Tips

1. **Batch Operations**: Validate multiple documents at once
2. **Limit Depth**: Use depth=1 when possible
3. **Use Indexes**: Create indexes on reference fields
4. **Cache Results**: Store populated data in client cache
5. **Lazy Loading**: Populate only when needed

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 | Document not found | Check document ID |
| 400 | Invalid relationship | Verify relationship configuration |
| 500 | Server error | Check server logs |
| 403 | Permission denied | Verify API key |

### Example Error Response

```json
{
  "detail": "Referenced document not found",
  "field": "author_id",
  "reference_id": "user_123"
}
```

---

## Testing

Run comprehensive tests:

```bash
# Full relationship system test
python test_relationship_system.py

# Quick populate test
python quick_test_populate.py

# Many-to-many test
python test_many_to_many.py
```

---

## Support

For issues or questions:
- GitHub: [WoosCloud Storage](https://github.com/your-repo)
- Email: support@wooscloud.com
- Docs: https://docs.wooscloud.com

---

**Version:** 1.0.0  
**Last Updated:** November 12, 2025