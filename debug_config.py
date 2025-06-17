# debug_config.py - Debug what configuration is being loaded
import os
import sys

print("🔍 Debugging Configuration Loading...")
print(f"Current directory: {os.getcwd()}")

# Check environment variables directly
print("\n📋 Environment Variables:")
database_url_env = os.getenv('DATABASE_URL')
print(f"DATABASE_URL from env: {database_url_env}")

# Check .env file content
print("\n📁 .env file content:")
try:
    with open('.env', 'r') as f:
        content = f.read()
        print(content)
except FileNotFoundError:
    print("No .env file found")

# Try importing just the config
print("\n⚙️ Testing config import...")
try:
    from app.core.config import settings
    print(f"✅ Config loaded successfully")
    print(f"Database URL from settings: {settings.database_url}")
    print(f"Database URL repr: {repr(settings.database_url)}")
except Exception as e:
    print(f"❌ Config failed: {e}")
    import traceback
    traceback.print_exc()