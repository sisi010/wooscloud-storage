# WoosCloud Storage - Python Client

Simple, powerful, and scalable cloud storage for Python applications.

## 🚀 Features

- **Simple API** - Store and retrieve data with just a few lines of code
- **Type Safe** - Full type hints support
- **Fast** - Optimized for performance
- **Secure** - API key authentication
- **Free Tier** - 500MB storage + 10,000 API calls/month

## 📦 Installation
```bash
pip install wooscloud
```

## 🔑 Get Your API Key

1. Sign up at [woos-ai.com](https://woos-ai.com)
2. Create an API key from your dashboard
3. Copy your API key (starts with `wai_`)

## 🎯 Quick Start
```python
from wooscloud import WoosStorage

# Initialize with your API key
storage = WoosStorage(api_key="wai_your_api_key_here")

# Save data
data_id = storage.save("users", {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
})
print(f"Saved with ID: {data_id}")

# Find data
users = storage.find("users")
for user in users:
    print(user.data)

# Find by ID
user = storage.find_one(data_id)
print(user.data)

# Update data
storage.update(data_id, {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 31  # Updated age
})

# Delete data
storage.delete(data_id)

# Get statistics
stats = storage.stats()
print(f"Storage used: {stats.storage_used_mb} MB")
print(f"API calls: {stats.api_calls_count}")
```

## 📚 Examples

### E-commerce Product Management
```python
from wooscloud import WoosStorage

storage = WoosStorage(api_key="wai_your_api_key")

# Add products
laptop_id = storage.save("products", {
    "name": "MacBook Pro M3",
    "price": 2500000,
    "category": "laptop",
    "stock": 15
})

phone_id = storage.save("products", {
    "name": "iPhone 15 Pro",
    "price": 1550000,
    "category": "smartphone",
    "stock": 30
})

# Get all products
products = storage.find("products")
print(f"Total products: {len(products)}")

# Get product count
count = storage.count("products")
print(f"Product count: {count}")
```

### User Profile Management
```python
from wooscloud import WoosStorage

storage = WoosStorage(api_key="wai_your_api_key")

# Create user profile
user_id = storage.save("users", {
    "username": "john_doe",
    "email": "john@example.com",
    "profile": {
        "age": 30,
        "city": "Seoul",
        "interests": ["technology", "reading", "travel"]
    }
})

# Update profile
storage.update(user_id, {
    "username": "john_doe",
    "email": "john@example.com",
    "profile": {
        "age": 31,  # Birthday!
        "city": "Seoul",
        "interests": ["technology", "reading", "travel", "photography"]
    }
})
```

### Blog System
```python
from wooscloud import WoosStorage
from datetime import datetime

storage = WoosStorage(api_key="wai_your_api_key")

# Create blog post
post_id = storage.save("posts", {
    "title": "Getting Started with WoosCloud",
    "content": "WoosCloud is a simple cloud storage...",
    "author": "John Doe",
    "tags": ["cloud", "storage", "tutorial"],
    "published_at": datetime.now().isoformat()
})

# Get all posts
posts = storage.find("posts", limit=10)
for post in posts:
    print(f"Title: {post.data['title']}")
    print(f"Author: {post.data['author']}")
```

## 🔧 API Reference

### WoosStorage

Main class for interacting with WoosCloud Storage.

#### `__init__(api_key: str, base_url: str = "https://wooscloud.up.railway.app")`

Initialize WoosStorage client.

**Parameters:**
- `api_key` (str): Your WoosCloud API key
- `base_url` (str, optional): API base URL

#### `save(collection: str, data: Dict[str, Any]) -> str`

Save data to a collection.

**Parameters:**
- `collection` (str): Collection name
- `data` (dict): Data to save

**Returns:**
- str: Data ID

#### `find(collection: str, limit: int = 100, skip: int = 0) -> List[StorageData]`

Find data in a collection.

**Parameters:**
- `collection` (str): Collection name
- `limit` (int): Maximum results (1-1000)
- `skip` (int): Number to skip (pagination)

**Returns:**
- List[StorageData]: List of data objects

#### `find_one(data_id: str) -> StorageData`

Find data by ID.

**Parameters:**
- `data_id` (str): Data ID

**Returns:**
- StorageData: Data object

#### `update(data_id: str, data: Dict[str, Any]) -> bool`

Update data by ID.

**Parameters:**
- `data_id` (str): Data ID
- `data` (dict): New data

**Returns:**
- bool: True if successful

#### `delete(data_id: str) -> bool`

Delete data by ID.

**Parameters:**
- `data_id` (str): Data ID

**Returns:**
- bool: True if successful

#### `stats() -> StorageStats`

Get storage usage statistics.

**Returns:**
- StorageStats: Statistics object

#### `collections() -> List[Collection]`

List all collections.

**Returns:**
- List[Collection]: List of collections

#### `count(collection: str) -> int`

Count items in a collection.

**Parameters:**
- `collection` (str): Collection name

**Returns:**
- int: Number of items

## 🛡️ Error Handling
```python
from wooscloud import WoosStorage
from wooscloud import (
    AuthenticationError,
    QuotaExceededError,
    NotFoundError,
    ValidationError
)

storage = WoosStorage(api_key="wai_your_api_key")

try:
    data = storage.find_one("invalid_id")
except NotFoundError:
    print("Data not found")
except AuthenticationError:
    print("Invalid API key")
except QuotaExceededError:
    print("Storage quota exceeded")
except ValidationError as e:
    print(f"Validation error: {e.message}")
```

## 📊 Pricing

### FREE Plan
- **Storage:** 500 MB
- **API Calls:** 10,000/month
- **Price:** $0

### STARTER Plan
- **Storage:** 5 GB
- **API Calls:** Unlimited
- **Price:** $9/month

### PRO Plan
- **Storage:** 50 GB
- **API Calls:** Unlimited
- **Price:** $29/month

## 🔗 Links

- **Website:** [woos-ai.com](https://woos-ai.com)
- **Documentation:** [woos-ai.com/docs](https://woos-ai.com/docs)
- **API Reference:** [woos-ai.com/api](https://woos-ai.com/api)
- **GitHub:** [github.com/wooscloud](https://github.com/wooscloud)

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Support

- Email: support@woos-ai.com
- Discord: [Join our community](https://discord.gg/wooscloud)
- GitHub Issues: [Report bugs](https://github.com/wooscloud/python-client/issues)

## 🌟 Contributing

Contributions are welcome! Please read our contributing guidelines.

---

Made with ❤️ by WoosCloud Team