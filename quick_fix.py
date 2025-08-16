#!/usr/bin/env python
"""
Quick fix for NetBox plugin testing errors.
This script will set up the minimal environment needed for testing.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_cmd(cmd, description):
    """Run command with feedback."""
    print(f"🔧 {description}")
    print(f"   {cmd}")
    result = os.system(cmd)
    if result == 0:
        print(f"   ✅ Success")
        return True
    else:
        print(f"   ❌ Failed")
        return False

def main():
    print("🚀 Quick Fix for NetBox Plugin Testing")
    print("=" * 50)

    # Step 1: Install NetBox
    print("\n📦 Step 1: Installing NetBox...")
    if not run_cmd("pip install 'netbox>=3.6,<4.0'", "Installing NetBox"):
        print("⚠️  NetBox installation failed. Trying alternative...")
        if not run_cmd("pip install git+https://github.com/netbox-community/netbox.git@v3.7", "Installing NetBox from GitHub"):
            print("❌ Could not install NetBox. Please install manually.")
            return False

    # Step 2: Install testing dependencies
    print("\n📦 Step 2: Installing testing dependencies...")
    deps = ["pytest", "pytest-django", "fakeredis", "factory-boy"]
    run_cmd(f"pip install {' '.join(deps)}", "Installing test dependencies")

    # Step 3: Create minimal configuration
    print("\n⚙️  Step 3: Creating minimal NetBox configuration...")

    config_content = '''"""
Minimal NetBox configuration for plugin testing.
"""

# Minimal required settings
SECRET_KEY = 'testing-secret-key-change-in-production-' + 'x' * 50
DEBUG = True
ALLOWED_HOSTS = ['*']

# Database (SQLite for testing)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',  # In-memory database for testing
    }
}

# Redis (using fakeredis)
REDIS = {
    'tasks': {
        'CONNECTION_CLASS': 'fakeredis.FakeConnection',
        'HOST': 'localhost',
        'PORT': 6379,
        'DATABASE': 0,
    },
    'caching': {
        'CONNECTION_CLASS': 'fakeredis.FakeConnection',
        'HOST': 'localhost',
        'PORT': 6379,
        'DATABASE': 1,
    }
}

# Plugin configuration
PLUGINS = ['business_application']
PLUGINS_CONFIG = {
    'business_application': {}
}

# Minimal required settings
USE_TZ = True
TIME_ZONE = 'UTC'
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
'''

    # Write minimal configuration
    config_file = Path("netbox_test_config.py")
    with open(config_file, 'w') as f:
        f.write(config_content)

    print(f"   ✅ Created {config_file}")

    # Step 4: Set environment variables
    print("\n🌍 Step 4: Setting up environment...")

    # Create environment setup script
    env_script = '''#!/bin/bash
# Quick fix environment setup

export DJANGO_SETTINGS_MODULE="netbox_test_config"
export PYTHONPATH="$PWD:$PYTHONPATH"

echo "✅ Environment set up for testing!"
echo "Now run: python run_tests.py --fast"
'''

    with open("quick_env.sh", 'w') as f:
        f.write(env_script)
    os.chmod("quick_env.sh", 0o755)

    print("   ✅ Created quick_env.sh")

    # Step 5: Test the setup
    print("\n🧪 Step 5: Testing the setup...")

    os.environ['DJANGO_SETTINGS_MODULE'] = 'netbox_test_config'
    os.environ['PYTHONPATH'] = f"{os.getcwd()}:{os.environ.get('PYTHONPATH', '')}"

    try:
        import django
        django.setup()
        print("   ✅ Django setup successful")

        # Try importing our plugin
        from business_application.models import TechnicalService
        print("   ✅ Plugin import successful")

        print("\n🎉 Quick fix completed successfully!")
        print("\nNow run:")
        print("   source quick_env.sh")
        print("   python run_tests.py --fast")

        return True

    except Exception as e:
        print(f"   ❌ Setup test failed: {e}")
        print("\n💡 Try running:")
        print("   source quick_env.sh")
        print("   python -c 'import django; django.setup(); print(\"OK\")'")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Quick fix had issues. You may need to run: python setup_local_testing.py")
    sys.exit(0 if success else 1)
