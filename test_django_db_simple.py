#!/usr/bin/env python3
"""
Simple Django Database Connection Test
Focuses specifically on the Django database connection issue
"""

import os
import sys
import traceback

# Set up environment
os.environ['DJANGO_SETTINGS_MODULE'] = 'netbox.settings'
sys.path.insert(0, '/tmp/netbox/netbox')

def test_django_connection():
    print("🔍 Simple Django Database Connection Test")
    print("=" * 50)
    
    try:
        print("1. Importing Django...")
        import django
        print(f"✅ Django {django.VERSION} imported")
        
        print("\n2. Setting up Django...")
        django.setup()
        print("✅ Django setup completed")
        
        print("\n3. Loading settings...")
        from django.conf import settings
        print("✅ Settings loaded")
        
        print("\n4. Checking database configuration...")
        db_config = settings.DATABASES['default']
        print(f"   Engine: {db_config.get('ENGINE')}")
        print(f"   Name: {db_config.get('NAME')}")
        print(f"   User: {db_config.get('USER')}")
        print(f"   Host: {db_config.get('HOST')}")
        print(f"   Port: {db_config.get('PORT')}")
        password = db_config.get('PASSWORD')
        print(f"   Password: {'SET (' + str(len(password)) + ' chars)' if password else 'NOT SET'}")
        
        print("\n5. Getting Django connection...")
        from django.db import connection
        print("✅ Connection object created")
        
        print("\n6. Getting connection parameters...")
        conn_params = connection.get_connection_params()
        print("   Connection parameters:")
        for key, value in sorted(conn_params.items()):
            if 'password' in key.lower():
                display = f"SET ({len(str(value))} chars)" if value else "NOT SET"
            else:
                display = str(value)
            print(f"     {key}: {display}")
        
        print("\n7. Testing database connection...")
        connection.ensure_connection()
        print("✅ Database connection successful!")
        
        print("\n8. Testing simple query...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            result = cursor.fetchone()[0]
            print(f"✅ Query successful: {result}")
            
        print("\n🎉 ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n📊 Full traceback:")
        traceback.print_exc()
        
        # Additional debugging for password issues
        if "fe_sendauth: no password supplied" in str(e):
            print("\n🔍 PASSWORD DEBUGGING:")
            try:
                from django.conf import settings
                db_config = settings.DATABASES['default']
                password = db_config.get('PASSWORD')
                print(f"   Settings password: {'SET' if password else 'NOT SET'}")
                print(f"   Password value: {repr(password)}")
                print(f"   Password type: {type(password)}")
                
                from django.db import connection
                conn_params = connection.get_connection_params()
                conn_password = conn_params.get('password')
                print(f"   Connection password: {'SET' if conn_password else 'NOT SET'}")
                print(f"   Connection password value: {repr(conn_password)}")
                print(f"   Connection password type: {type(conn_password)}")
                
                # Check if they're the same
                if password == conn_password:
                    print("   ✅ Passwords match between settings and connection")
                else:
                    print("   ❌ PASSWORD MISMATCH!")
                    print(f"      Settings: {repr(password)}")
                    print(f"      Connection: {repr(conn_password)}")
                    
            except Exception as debug_e:
                print(f"   Error during password debugging: {debug_e}")
                
        return False

if __name__ == "__main__":
    success = test_django_connection()
    sys.exit(0 if success else 1)
