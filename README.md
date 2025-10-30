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