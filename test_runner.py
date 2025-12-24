#!/usr/bin/env python3
"""
NetBox Plugin Test Runner
Provides multiple testing strategies for different scenarios
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

def print_banner(text, color="blue"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m", 
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "purple": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "end": "\033[0m"
    }
    
    border = "=" * (len(text) + 4)
    print(f"\n{colors.get(color, '')}{border}")
    print(f"  {text}")
    print(f"{border}{colors['end']}\n")

def run_cmd(cmd, description="", check=True):
    print(f"🔧 {description}")
    print(f"   $ {cmd}")
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            print(f"   ✅ Success ({elapsed:.1f}s)")
            return True
        else:
            print(f"   ❌ Failed ({elapsed:.1f}s)")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Failed ({elapsed:.1f}s): {e}")
        return False

def setup_netbox():
    """Setup minimal NetBox environment"""
    netbox_dir = "/tmp/netbox"
    
    if not os.path.exists(netbox_dir):
        print_banner("Setting up NetBox Environment", "blue")
        
        if not run_cmd(f"git clone --depth 1 --branch v4.2.7 https://github.com/netbox-community/netbox.git {netbox_dir}",
                      "Cloning NetBox"):
            return False
            
        if not run_cmd(f"pip install -r {netbox_dir}/requirements.txt",
                      "Installing NetBox dependencies"):
            return False
    
    # Install plugin dependencies
    if not run_cmd("pip install -r requirements.txt pytest pytest-django coverage",
                  "Installing plugin dependencies"):
        return False
    
    return True

def test_sqlite():
    """Run fast unit tests with SQLite"""
    print_banner("Running Unit Tests (SQLite In-Memory)", "green")
    
    if not setup_netbox():
        return False
    
    # Copy test settings
    test_settings_path = "/tmp/netbox/netbox/test_settings.py"
    if not run_cmd(f"cp business_application/test_settings.py {test_settings_path}",
                  "Copying test settings"):
        return False
    
    # Set environment
    os.environ["DJANGO_SETTINGS_MODULE"] = "test_settings"
    os.environ["PYTHONPATH"] = f"/tmp/netbox/netbox:{os.getcwd()}"
    
    # Run migrations
    if not run_cmd("cd /tmp/netbox/netbox && python manage.py migrate --settings=test_settings",
                  "Running SQLite migrations"):
        return False
    
    # Run tests
    test_cmd = f"cd /tmp/netbox/netbox && python -m pytest {os.getcwd()}/business_application/tests/ -v --tb=short"
    return run_cmd(test_cmd, "Running unit tests with SQLite")

def test_postgresql_check():
    """Check if PostgreSQL is available locally"""
    print_banner("Checking Local PostgreSQL", "yellow")
    
    # Check if PostgreSQL is running
    if not run_cmd("pg_isready -h localhost -p 5432", "Checking PostgreSQL connection", check=False):
        print("❌ PostgreSQL not available locally")
        print("💡 Options:")
        print("   1. Install PostgreSQL: sudo apt-get install postgresql")
        print("   2. Use Docker: docker run -d --name test-postgres -e POSTGRES_PASSWORD=netbox -e POSTGRES_USER=netbox -e POSTGRES_DB=netbox -p 5432:5432 postgres:13")
        print("   3. Use SQLite tests instead: python test_runner.py --sqlite")
        return False
    
    print("✅ PostgreSQL is available!")
    return True

def test_smoke():
    """Quick smoke test - just import the plugin"""
    print_banner("Running Smoke Test (Plugin Import)", "cyan")
    
    if not setup_netbox():
        return False
    
    os.environ["PYTHONPATH"] = f"/tmp/netbox/netbox:{os.getcwd()}"
    
    smoke_test = """
import sys
sys.path.append('{}')
import business_application
print(f'✅ Plugin {{business_application.__name__}} imported successfully')
config = getattr(business_application, 'config', None)
if config:
    print(f'📦 Name: {{config.name}}')
    print(f'🔢 Version: {{config.version}}') 
    print(f'📝 Description: {{config.description}}')
    print(f'⚠️  Min NetBox: {{config.min_version}}')
else:
    print('📦 Basic import successful')
""".format(os.getcwd())
    
    return run_cmd(f"cd /tmp/netbox/netbox && python -c \"{smoke_test}\"",
                  "Testing plugin import")

def main():
    parser = argparse.ArgumentParser(description="NetBox Plugin Test Runner")
    parser.add_argument("--sqlite", action="store_true", help="Run fast unit tests with SQLite")
    parser.add_argument("--postgresql", action="store_true", help="Run comprehensive tests with PostgreSQL") 
    parser.add_argument("--smoke", action="store_true", help="Run smoke test (plugin import only)")
    parser.add_argument("--check-postgres", action="store_true", help="Check if PostgreSQL is available")
    parser.add_argument("--all", action="store_true", help="Run all available tests")
    
    args = parser.parse_args()
    
    if not any([args.sqlite, args.postgresql, args.smoke, args.check_postgres, args.all]):
        print_banner("NetBox Plugin Test Runner", "purple")
        print("🧪 Available test strategies:")
        print()
        print("⚡ Fast Tests:")
        print("   --sqlite       SQLite in-memory (30 seconds, good for development)")
        print("   --smoke        Plugin import test (5 seconds, CI smoke test)")
        print()
        print("🔍 Comprehensive Tests:")
        print("   --postgresql   Full PostgreSQL tests (2-3 minutes, production-like)")
        print()
        print("🛠️  Utilities:")
        print("   --check-postgres  Check if PostgreSQL is available")
        print("   --all            Run all available tests")
        print()
        print("💡 Recommendations:")
        print("   Development:  python test_runner.py --sqlite")
        print("   CI/CD:        python test_runner.py --smoke (fast) + --postgresql (thorough)")
        print("   Pre-commit:   python test_runner.py --sqlite")
        return
    
    success = True
    
    if args.smoke or args.all:
        success &= test_smoke()
    
    if args.sqlite or args.all:
        success &= test_sqlite()
    
    if args.check_postgres:
        test_postgresql_check()
    
    if args.postgresql or args.all:
        if test_postgresql_check():
            print("🚧 PostgreSQL tests not yet implemented")
            print("💡 Use GitHub Actions for full PostgreSQL testing")
        success = False
    
    if success:
        print_banner("All Tests Passed! 🎉", "green")
        sys.exit(0)
    else:
        print_banner("Some Tests Failed 😞", "red")
        sys.exit(1)

if __name__ == "__main__":
    main()
