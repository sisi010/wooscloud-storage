"""
WoosCloud Storage - Advanced Examples
"""

from wooscloud import WoosStorage
from datetime import datetime
import json

def blog_example():
    """Blog system example"""
    
    print("📝 Blog System Example\n")
    
    storage = WoosStorage(
        api_key="wai_your_api_key",
        base_url="http://127.0.0.1:8000"
    )
    
    # Create blog posts
    post1_id = storage.save("blog_posts", {
        "title": "Getting Started with WoosCloud",
        "content": "WoosCloud makes it easy to store data in the cloud...",
        "author": "John Doe",
        "tags": ["tutorial", "cloud", "storage"],
        "published_at": datetime.now().isoformat(),
        "views": 0,
        "likes": 0
    })
    
    post2_id = storage.save("blog_posts", {
        "title": "10 Tips for Better Code",
        "content": "Here are 10 tips that will make you a better programmer...",
        "author": "Jane Smith",
        "tags": ["programming", "tips"],
        "published_at": datetime.now().isoformat(),
        "views": 0,
        "likes": 0
    })
    
    print(f"✅ Created 2 blog posts")
    
    # Get all posts
    posts = storage.find("blog_posts", limit=10)
    
    print(f"\n📰 Recent Posts:")
    for post in posts:
        print(f"   - {post.data['title']} by {post.data['author']}")
    
    return post1_id, post2_id

def ecommerce_example():
    """E-commerce example"""
    
    print("\n🛒 E-commerce Example\n")
    
    storage = WoosStorage(
        api_key="wai_your_api_key",
        base_url="http://127.0.0.1:8000"
    )
    
    # Add products
    products = [
        {
            "name": "Wireless Mouse",
            "price": 29900,
            "category": "accessories",
            "stock": 100,
            "rating": 4.5
        },
        {
            "name": "Mechanical Keyboard",
            "price": 89900,
            "category": "accessories",
            "stock": 50,
            "rating": 4.8
        },
        {
            "name": "USB-C Hub",
            "price": 49900,
            "category": "accessories",
            "stock": 75,
            "rating": 4.3
        }
    ]
    
    for product in products:
        storage.save("products", product)
    
    print(f"✅ Added {len(products)} products")
    
    # Get product statistics
    total_products = storage.count("products")
    print(f"\n📊 Total products: {total_products}")
    
    # List all products
    all_products = storage.find("products")
    
    print(f"\n🏷️  Product Catalog:")
    for product in all_products:
        print(f"   - {product.data['name']}: {product.data['price']:,}원")

def analytics_example():
    """Analytics tracking example"""
    
    print("\n📈 Analytics Example\n")
    
    storage = WoosStorage(
        api_key="wai_your_api_key",
        base_url="http://127.0.0.1:8000"
    )
    
    # Track page views
    events = [
        {
            "type": "page_view",
            "page": "/",
            "user_id": "user123",
            "timestamp": datetime.now().isoformat()
        },
        {
            "type": "button_click",
            "button": "signup",
            "user_id": "user123",
            "timestamp": datetime.now().isoformat()
        },
        {
            "type": "purchase",
            "product_id": "prod456",
            "amount": 99000,
            "user_id": "user123",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    for event in events:
        storage.save("analytics_events", event)
    
    print(f"✅ Tracked {len(events)} events")
    
    # Get event count
    event_count = storage.count("analytics_events")
    print(f"\n📊 Total events: {event_count}")

def main():
    """Run all examples"""
    
    print("=" * 60)
    print("WoosCloud Storage - Advanced Examples")
    print("=" * 60)
    print()
    
    # Run examples
    blog_example()
    ecommerce_example()
    analytics_example()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()