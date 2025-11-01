"""
Test environment variables
"""

from app.config import settings

print("=" * 60)
print("Environment Variables Test")
print("=" * 60)
print(f"R2_ENABLED: {settings.R2_ENABLED}")
print(f"R2_ENABLED type: {type(settings.R2_ENABLED)}")
print(f"R2_ACCOUNT_ID: {settings.R2_ACCOUNT_ID}")
print(f"R2_ACCESS_KEY: {settings.R2_ACCESS_KEY[:10] if settings.R2_ACCESS_KEY else 'None'}...")
print(f"R2_SECRET_KEY: {settings.R2_SECRET_KEY[:10] if settings.R2_SECRET_KEY else 'None'}...")
print(f"R2_BUCKET_NAME: {settings.R2_BUCKET_NAME}")
print("=" * 60)