#!/usr/bin/env python
"""
Local NetBox testing environment setup script.

This script sets up a local NetBox installation for plugin testing.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description, check=True):
    """Run a command with error handling."""
    print(f"🔧 {description}")
    print(f"   Command: {command}")

    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {description} completed")
            return True
        else:
            print(f"   ❌ {description} failed")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} failed: {e}")
        return False

def setup_netbox_testing():
    """Set up NetBox for local plugin testing."""

    print("="*60)
    print("  NetBox Plugin Testing Environment Setup")
    print("="*60)

    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Not in a virtual environment. Consider using venv or conda.")

    # Create netbox directory for testing
    netbox_dir = Path("./netbox-testing")

    if netbox_dir.exists():
        print(f"📁 NetBox testing directory already exists at {netbox_dir}")
        response = input("Remove existing directory and reinstall? (y/N): ")
        if response.lower() == 'y':
            shutil.rmtree(netbox_dir)
        else:
            print("Using existing NetBox installation...")
            return netbox_dir

    # Clone NetBox
    print("\n📥 Cloning NetBox...")
    if not run_command(
        f"git clone --depth 1 --branch v3.7 https://github.com/netbox-community/netbox.git {netbox_dir}",
        "Cloning NetBox v3.7"
    ):
        return None

    # Install NetBox requirements
    print("\n📦 Installing NetBox requirements...")
    if not run_command(
        f"pip install -r {netbox_dir}/requirements.txt",
        "Installing NetBox dependencies"
    ):
        return None

    # Install NetBox in development mode
    print("\n🔧 Installing NetBox in development mode...")
    if not run_command(
        f"pip install -e {netbox_dir}/",
        "Installing NetBox"
    ):
        return None

    # Install additional testing dependencies
    print("\n📦 Installing testing dependencies...")
    test_deps = [
        "pytest", "pytest-django", "pytest-cov", "coverage",
        "factory-boy", "requests", "django-extensions"
    ]

    for dep in test_deps:
        run_command(f"pip install {dep}", f"Installing {dep}", check=False)

    return netbox_dir

def setup_netbox_config(netbox_dir):
    """Set up NetBox configuration for testing."""

    print("\n⚙️  Setting up NetBox configuration...")

    config_dir = netbox_dir / "netbox" / "netbox"
    config_file = config_dir / "configuration.py"

    # Copy example configuration
    example_config = config_dir / "configuration_example.py"
    if not run_command(
        f"cp {example_config} {config_file}",
        "Copying configuration example"
    ):
        return False

    # Create test configuration
    test_config = """
# Test configuration for NetBox plugin development

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'testing-secret-key-do-not-use-in-production-abcdefghijklmnopqrstuvwxyz0123456789'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Redis (using fakeredis for testing)
REDIS = {
    'tasks': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 0,
        'CONNECTION_CLASS': 'fakeredis.FakeConnection',
    },
    'caching': {
        'HOST': 'localhost',
        'PORT': 6379,
        'PASSWORD': '',
        'DATABASE': 1,
        'CONNECTION_CLASS': 'fakeredis.FakeConnection',
    }
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'business_application': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Plugin configuration
PLUGINS = ['business_application']

PLUGINS_CONFIG = {
    'business_application': {
        'enable_health_monitoring': True,
        'alert_correlation_window': 30,
        'max_incident_age_days': 30,
    }
}

# Testing settings
USE_TZ = True
TIME_ZONE = 'UTC'

# Media files (for testing)
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Static files (for testing)
STATIC_ROOT = BASE_DIR / 'static'
STATIC_URL = '/static/'
"""

    # Write test configuration
    with open(config_file, 'w') as f:
        f.write(test_config)

    print("   ✅ NetBox configuration created")
    return True

def setup_environment_variables(netbox_dir):
    """Set up environment variables for testing."""

    print("\n🌍 Setting up environment variables...")

    # Create environment setup script
    env_script = Path("./setup_test_env.sh")

    env_content = f"""#!/bin/bash
# NetBox Plugin Testing Environment Setup

export DJANGO_SETTINGS_MODULE="netbox.settings"
export PYTHONPATH="{netbox_dir.absolute()}/netbox:$PWD:$PYTHONPATH"

echo "🔧 NetBox testing environment configured!"
echo "📁 NetBox path: {netbox_dir.absolute()}"
echo "🐍 Python path: $PYTHONPATH"
echo "⚙️  Django settings: $DJANGO_SETTINGS_MODULE"
echo ""
echo "✅ Run tests with: python run_tests.py"
echo "✅ Or use: source setup_test_env.sh && python run_tests.py"
"""

    with open(env_script, 'w') as f:
        f.write(env_content)

    os.chmod(env_script, 0o755)

    print("   ✅ Environment setup script created: ./setup_test_env.sh")

    # Set environment variables for current session
    os.environ['DJANGO_SETTINGS_MODULE'] = 'netbox.settings'
    os.environ['PYTHONPATH'] = f"{netbox_dir.absolute()}/netbox:{os.getcwd()}:{os.environ.get('PYTHONPATH', '')}"

    return True

def run_initial_setup(netbox_dir):
    """Run initial Django setup commands."""

    print("\n🔄 Running initial Django setup...")

    netbox_manage = netbox_dir / "netbox" / "manage.py"

    # Run migrations
    if not run_command(
        f"cd {netbox_dir}/netbox && python manage.py migrate",
        "Running database migrations"
    ):
        print("   ⚠️  Migrations failed, but this might be OK for testing")

    # Collect static files
    if not run_command(
        f"cd {netbox_dir}/netbox && python manage.py collectstatic --noinput",
        "Collecting static files"
    ):
        print("   ⚠️  Static file collection failed, but this might be OK for testing")

    return True

def install_fakeredis():
    """Install fakeredis for testing without Redis server."""
    print("\n📦 Installing fakeredis for testing...")
    return run_command("pip install fakeredis", "Installing fakeredis", check=False)

def main():
    """Main setup function."""

    try:
        # Install fakeredis first
        install_fakeredis()

        # Set up NetBox
        netbox_dir = setup_netbox_testing()
        if not netbox_dir:
            print("❌ Failed to set up NetBox")
            return False

        # Configure NetBox
        if not setup_netbox_config(netbox_dir):
            print("❌ Failed to configure NetBox")
            return False

        # Set up environment
        if not setup_environment_variables(netbox_dir):
            print("❌ Failed to set up environment")
            return False

        # Run initial setup
        run_initial_setup(netbox_dir)

        print("\n" + "="*60)
        print("🎉 NetBox testing environment setup complete!")
        print("="*60)

        print("\n📋 Next steps:")
        print("1. Run: source setup_test_env.sh")
        print("2. Then: python run_tests.py --fast")
        print("\nOr run directly:")
        print(f"   cd {netbox_dir}/netbox && python manage.py test ../../business_application/tests/")

        return True

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
