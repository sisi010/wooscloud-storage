# WoosCloud Storage

Simple, powerful, and scalable cloud storage service with API.

## 🎯 Features

- ☁️ Cloud database storage
- 🔑 Simple API key authentication
- 🐍 Easy-to-use Python library
- 💰 Generous free tier (500MB)
- 🚀 Fast and reliable

## 📦 Project Structure
```
wooscloud-storage/
├── backend/          # FastAPI backend
├── python-library/   # Python client library
└── frontend/         # Web interface
```

## 🚀 Quick Start

### Install Library
```bash
pip install woosailb
```

### Use Storage
```python
from woosailb import WoosStorage

storage = WoosStorage(api_key="your_api_key")

# Save data
storage.save("users", {"name": "홍길동", "age": 30})

# Find data
users = storage.find("users")
```

## 💰 Pricing

- **FREE**: 500MB storage
- **STARTER**: 5GB storage ($9/month)
- **PRO**: 50GB storage ($29/month)

## 📚 Documentation

Visit https://woos-ai.com/docs for full documentation.

## 🔗 Links

- Website: https://woos-ai.com
- Dashboard: https://woos-ai.com/storage.html
- API Docs: https://wooscloud-backend.up.railway.app/api/docs

## 📄 License

MIT License

## What's New in v1.1.0

### 🎉 Cloudflare R2 Integration
- Automatic routing: Small data (< 100KB) → MongoDB, Large data (≥ 100KB) → R2
- New `storage_type` field in responses: `'mongodb'` or `'r2'`
- Enhanced stats with R2 status and distribution

### API Updates
- `stats()` now includes `r2_enabled` and `storage_distribution`
- `find_one()` and `find()` return `storage_type` for each item
- Supports multi-cloud storage seamlessly

### Example
```python
from wooscloud import WoosStorage

storage = WoosStorage(api_key="your_api_key")

# Save data (automatically routed)
data_id = storage.save("collection", {"key": "value"})

# Get storage stats
stats = storage.stats()
print(f"R2 Enabled: {stats.r2_enabled}")
print(f"MongoDB items: {stats.mongodb_items}")
print(f"R2 items: {stats.r2_items}")

# Check where data is stored
item = storage.find_one(data_id)
print(f"Storage type: {item.storage_type}")  # 'mongodb' or 'r2'
```