#!/usr/bin/env python3
"""
Django Database Connection Debugger
Comprehensive debugging script for NetBox plugin database connectivity issues
"""

import os
import sys
import traceback


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def debug_environment():
    print_section("🌍 ENVIRONMENT VARIABLES")
    
    env_vars = [
        'DJANGO_SETTINGS_MODULE',
        'PYTHONPATH', 
        'DATABASE_URL',
        'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, '<NOT SET>')
        if 'password' in var.lower():
            display_value = '*' * len(value) if value != '<NOT SET>' else value
        else:
            display_value = value
        print(f"  {var}: {display_value}")


def debug_python_path():
    print_section("🐍 PYTHON PATH & MODULES")
    
    print("Python sys.path:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    
    print("\nTrying to import Django...")
    try:
        import django
        print(f"✅ Django imported successfully: {django.__version__}")
    except ImportError as e:
        print(f"❌ Django import failed: {e}")
        return False
        
    print("\nTrying to import NetBox...")
    try:
        import netbox
        print(f"✅ NetBox imported successfully: {netbox.__version__}")
    except ImportError as e:
        print(f"❌ NetBox import failed: {e}")
        return False
        
    return True


def debug_django_settings():
    print_section("⚙️ DJANGO SETTINGS")
    
    try:
        import django
        from django.conf import settings
        
        # Setup Django
        print("Setting up Django...")
        django.setup()
        print("✅ Django setup successful")
        
        # Check database configuration
        print(f"\nDjango settings module: {settings.SETTINGS_MODULE}")
        
        if hasattr(settings, 'DATABASES'):
            print("\nDATABASE configuration:")
            db_config = settings.DATABASES.get('default', {})
            
            for key, value in db_config.items():
                if key.upper() == 'PASSWORD':
                    display_value = '*' * len(str(value)) if value else '<EMPTY>'
                else:
                    display_value = value
                print(f"  {key}: {display_value}")
        else:
            print("❌ No DATABASES configuration found!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Django settings error: {e}")
        traceback.print_exc()
        return False


def debug_database_connection():
    print_section("🔌 DATABASE CONNECTION")
    
    try:
        from django.db import connection
        from django.db.utils import OperationalError
        
        print("Testing Django database connection...")
        
        # Get connection parameters
        conn_params = connection.get_connection_params()
        print("\nConnection parameters being used:")
        for key, value in conn_params.items():
            if 'password' in key.lower():
                display_value = '*' * len(str(value)) if value else '<EMPTY>'
            else:
                display_value = value
            print(f"  {key}: {display_value}")
        
        # Test connection
        print("\nAttempting to connect...")
        connection.ensure_connection()
        print("✅ Django database connection successful!")
        
        # Test a simple query
        print("\nTesting simple query...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            result = cursor.fetchone()[0]
            print(f"✅ Query successful: {result}")
            
        return True
        
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        
        # Additional debugging for password issues
        if "fe_sendauth: no password supplied" in str(e):
            print("\n🔍 DEBUGGING PASSWORD ISSUE:")
            try:
                from django.conf import settings
                db_config = settings.DATABASES.get('default', {})
                password = db_config.get('PASSWORD')
                
                print(f"  Password from settings: {'SET' if password else 'NOT SET'}")
                print(f"  Password length: {len(password) if password else 0}")
                print(f"  Password type: {type(password)}")
                
                # Check if password is being passed to connection
                conn_params = connection.get_connection_params()
                conn_password = conn_params.get('password')
                print(f"  Password in connection params: {'SET' if conn_password else 'NOT SET'}")
                
            except Exception as debug_e:
                print(f"  Error during password debugging: {debug_e}")
                
        return False
        
    except Exception as e:
        print(f"❌ Unexpected database error: {e}")
        traceback.print_exc()
        return False


def debug_netbox_plugin():
    print_section("🔌 NETBOX PLUGIN")
    
    try:
        print("Testing NetBox plugin import...")
        sys.path.insert(0, os.environ.get('GITHUB_WORKSPACE', '.'))
        
        import business_application
        print(f"✅ Plugin imported: {business_application.__name__}")
        
        if hasattr(business_application, 'config'):
            config = business_application.config
            print(f"  Name: {config.name}")
            print(f"  Version: {config.version}")
            print(f"  Min NetBox: {config.min_version}")
            
        return True
        
    except Exception as e:
        print(f"❌ Plugin import failed: {e}")
        traceback.print_exc()
        return False


def main():
    print("🔍 Django Database Connection Debugger")
    print("=====================================")
    
    success = True
    
    # Debug environment
    debug_environment()
    
    # Debug Python imports
    if not debug_python_path():
        success = False
    
    # Debug Django settings  
    if not debug_django_settings():
        success = False
    
    # Debug database connection
    if not debug_database_connection():
        success = False
        
    # Debug plugin
    if not debug_netbox_plugin():
        success = False
    
    print_section("📊 SUMMARY")
    if success:
        print("🎉 All checks passed!")
        sys.exit(0)
    else:
        print("❌ Some checks failed. See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
