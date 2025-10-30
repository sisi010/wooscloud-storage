"""
WoosCloud Storage - Quick Start Example
Run this example to test your WoosCloud setup
"""

from wooscloud import WoosStorage
from wooscloud.exceptions import WoosCloudError

def main():
    """Quick start example"""
    
    # ============================================
    # STEP 1: Initialize
    # ============================================
    print("🚀 WoosCloud Storage Quick Start\n")
    
    # Replace with your actual API key
    API_KEY = "wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc"
    
    # For local development
    storage = WoosStorage(api_key=API_KEY, base_url="http://127.0.0.1:8000")
    
    # For production
    # storage = WoosStorage(api_key=API_KEY)
    
    print("✅ Connected to WoosCloud\n")
    
    # ============================================
    # STEP 2: Save Data
    # ============================================
    print("📝 Saving data...")
    
    try:
        # Save a product
        product_id = storage.save("products", {
            "name": "MacBook Pro M3",
            "price": 2500000,
            "category": "laptop",
            "brand": "Apple",
            "specs": {
                "cpu": "M3 Pro",
                "ram": "18GB",
                "storage": "512GB SSD"
            }
        })
        
        print(f"✅ Product saved! ID: {product_id}\n")
        
        # Save a user
        user_id = storage.save("users", {
            "name": "홍길동",
            "email": "hong@example.com",
            "age": 30,
            "interests": ["기술", "독서", "여행"]
        })
        
        print(f"✅ User saved! ID: {user_id}\n")
        
    except WoosCloudError as e:
        print(f"❌ Error saving data: {e.message}\n")
        return
    
    # ============================================
    # STEP 3: Find Data
    # ============================================
    print("🔍 Finding data...")
    
    try:
        # Find all products
        products = storage.find("products", limit=10)
        
        print(f"✅ Found {len(products)} products:\n")
        
        for product in products:
            print(f"   📦 {product.data.get('name')}")
            print(f"      Price: {product.data.get('price'):,}원")
            print(f"      Brand: {product.data.get('brand')}")
            print()
        
    except WoosCloudError as e:
        print(f"❌ Error finding data: {e.message}\n")
    
    # ============================================
    # STEP 4: Find One
    # ============================================
    print("🔍 Finding specific data...")
    
    try:
        product = storage.find_one(product_id)
        
        print(f"✅ Found product:\n")
        print(f"   Name: {product.data.get('name')}")
        print(f"   Price: {product.data.get('price'):,}원")
        print(f"   Category: {product.data.get('category')}")
        print()
        
    except WoosCloudError as e:
        print(f"❌ Error: {e.message}\n")
    
    # ============================================
    # STEP 5: Update Data
    # ============================================
    print("✏️  Updating data...")
    
    try:
        storage.update(product_id, {
            "name": "MacBook Pro M3",
            "price": 2300000,  # Discounted!
            "category": "laptop",
            "brand": "Apple",
            "specs": {
                "cpu": "M3 Pro",
                "ram": "18GB",
                "storage": "512GB SSD"
            },
            "discount": "8% OFF!"
        })
        
        print("✅ Product updated!\n")
        
    except WoosCloudError as e:
        print(f"❌ Error updating: {e.message}\n")
    
    # ============================================
    # STEP 6: Collections
    # ============================================
    print("📁 Listing collections...")
    
    try:
        collections = storage.collections()
        
        print(f"✅ Found {len(collections)} collections:\n")
        
        for col in collections:
            print(f"   📁 {col.name}")
            print(f"      Items: {col.count}")
            print(f"      Size: {col.size_kb} KB")
            print()
        
    except WoosCloudError as e:
        print(f"❌ Error: {e.message}\n")
    
    # ============================================
    # STEP 7: Statistics
    # ============================================
    print("📊 Getting statistics...")
    
    try:
        stats = storage.stats()
        
        print("✅ Storage Statistics:\n")
        print(f"   Storage:")
        print(f"      Used: {stats.storage_used_mb:.2f} MB")
        print(f"      Limit: {stats.storage_limit_mb:.2f} MB")
        print(f"      Usage: {stats.storage_percent:.2f}%")
        print()
        print(f"   API Calls:")
        print(f"      Count: {stats.api_calls_count}")
        print(f"      Limit: {stats.api_calls_limit}")
        print(f"      Remaining: {stats.api_calls_remaining}")
        print()
        print(f"   Plan: {stats.plan.upper()}")
        print()
        
    except WoosCloudError as e:
        print(f"❌ Error: {e.message}\n")
    
    # ============================================
    # STEP 8: Count
    # ============================================
    print("🔢 Counting items...")
    
    try:
        product_count = storage.count("products")
        user_count = storage.count("users")
        
        print(f"✅ Item counts:\n")
        print(f"   Products: {product_count}")
        print(f"   Users: {user_count}")
        print()
        
    except WoosCloudError as e:
        print(f"❌ Error: {e.message}\n")
    
    # ============================================
    # STEP 9: Delete (Optional)
    # ============================================
    print("🗑️  Cleanup (optional)...")
    
    # Uncomment to delete test data
    # try:
    #     storage.delete(product_id)
    #     storage.delete(user_id)
    #     print("✅ Test data deleted\n")
    # except WoosCloudError as e:
    #     print(f"❌ Error deleting: {e.message}\n")
    
    # ============================================
    # Done!
    # ============================================
    print("=" * 50)
    print("🎉 Quick start complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("1. Replace API_KEY with your actual key")
    print("2. Change base_url for production")
    print("3. Start building your application!")
    print()

if __name__ == "__main__":
    main()