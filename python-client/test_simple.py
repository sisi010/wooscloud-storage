from wooscloud import WoosStorage

print('🚀 Testing WoosCloud')

storage = WoosStorage(
    api_key='wai_46ESHEZmnB0Oi7ubK6yZICOz7BnaLhhQgVGDI9n_KCc',
    base_url='http://127.0.0.1:8000'
)

print('✅ Initialized')

# Save
data_id = storage.save('test', {'msg': 'Hello!'})
print(f'✅ Saved: {data_id}')

# Find
items = storage.find('test', limit=3)
print(f'✅ Found {len(items)} items')

# Stats
stats = storage.stats()
print(f'✅ Used: {stats.storage_used_mb} MB')

print('🎉 All tests passed!')