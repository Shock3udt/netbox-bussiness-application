#!/usr/bin/env python
"""
Local test runner for NetBox Business Application plugin.

This script provides a comprehensive test runner that developers can use
locally before pushing code to GitHub Actions.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit            # Run unit tests only
    python run_tests.py --api             # Run API tests only
    python run_tests.py --health          # Run health status tests only
    python run_tests.py --fast            # Run fast test suite (no coverage)
    python run_tests.py --coverage        # Run with coverage report
    python run_tests.py --quality         # Run code quality checks
    python run_tests.py --security        # Run security checks
    python run_tests.py --all             # Run everything (tests + quality + security)
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_banner(text, color=Colors.CYAN):
    """Print a banner with the given text."""
    print(f"\n{color}{Colors.BOLD}{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}{Colors.END}\n")

def print_step(text, color=Colors.BLUE):
    """Print a step with formatting."""
    print(f"{color}{Colors.BOLD}🔧 {text}{Colors.END}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}{Colors.BOLD}✅ {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}{Colors.BOLD}❌ {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  {text}{Colors.END}")

def run_command(command, description, check=True, capture_output=False):
    """Run a shell command with proper formatting."""
    print_step(description)
    print(f"{Colors.WHITE}Command: {command}{Colors.END}")

    start_time = time.time()

    try:
        if capture_output:
            result = subprocess.run(
                command,
                shell=True,
                check=check,
                capture_output=True,
                text=True
            )
            end_time = time.time()

            if result.returncode == 0:
                print_success(f"{description} completed in {end_time - start_time:.2f}s")
                return result.stdout
            else:
                print_error(f"{description} failed (exit code {result.returncode})")
                if result.stderr:
                    print(f"{Colors.RED}Error output:\n{result.stderr}{Colors.END}")
                return None
        else:
            result = subprocess.run(command, shell=True, check=check)
            end_time = time.time()

            if result.returncode == 0:
                print_success(f"{description} completed in {end_time - start_time:.2f}s")
                return True
            else:
                print_error(f"{description} failed (exit code {result.returncode})")
                return False

    except subprocess.CalledProcessError as e:
        end_time = time.time()
        print_error(f"{description} failed after {end_time - start_time:.2f}s")
        if not check:
            return False
        raise
    except KeyboardInterrupt:
        print_error(f"\n{description} interrupted by user")
        sys.exit(1)

def check_environment():
    """Check if the environment is set up correctly."""
    print_banner("Environment Check")

    # Check Python version
    python_version = sys.version_info
    if python_version < (3, 9):
        print_error(f"Python {python_version.major}.{python_version.minor} is not supported. Please use Python 3.9+")
        return False

    print_success(f"Python {python_version.major}.{python_version.minor}.{python_version.micro}")

    # Check if we're in the right directory
    if not Path("business_application").exists():
        print_error("business_application directory not found. Are you in the project root?")
        return False

    print_success("Project structure verified")

    # Check for Django settings
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        print_warning("DJANGO_SETTINGS_MODULE not set. Tests may fail.")
        print(f"{Colors.CYAN}Hint: Set up NetBox environment first{Colors.END}")
    else:
        print_success(f"Django settings: {os.environ['DJANGO_SETTINGS_MODULE']}")

    return True

def install_test_dependencies():
    """Install test dependencies."""
    print_banner("Installing Test Dependencies")

    dependencies = [
        "pytest",
        "pytest-django",
        "pytest-cov",
        "coverage",
        "flake8",
        "black",
        "isort",
        "mypy",
        "bandit",
        "safety"
    ]

    command = f"pip install {' '.join(dependencies)}"
    return run_command(command, "Installing test dependencies", check=False)

def run_unit_tests(with_coverage=False):
    """Run unit tests."""
    print_banner("Unit Tests")

    base_command = "python -m pytest business_application/tests/"

    if with_coverage:
        command = f"coverage run --source=business_application -m pytest business_application/tests/ -v"
    else:
        command = f"{base_command} -v"

    return run_command(command, "Running unit tests")

def run_api_tests():
    """Run API tests specifically."""
    print_banner("API Tests")

    command = "python -m pytest business_application/tests/test_api_comprehensive.py -v"
    return run_command(command, "Running API tests")

def run_health_tests():
    """Run health status tests."""
    print_banner("Health Status Tests")

    command = "python -m pytest business_application/tests/test_health_status.py -v"
    return run_command(command, "Running health status tests")

def run_alert_correlation_tests():
    """Run alert correlation tests."""
    print_banner("Alert Correlation Tests")

    command = "python -m pytest business_application/tests/test_alert_correlation.py -v"
    return run_command(command, "Running alert correlation tests")

def run_model_tests():
    """Run model tests."""
    print_banner("Model Tests")

    command = "python -m pytest business_application/tests/test_models_enhanced.py -v"
    return run_command(command, "Running model tests")

def run_serializer_tests():
    """Run serializer tests."""
    print_banner("Serializer Tests")

    command = "python -m pytest business_application/tests/test_serializers.py -v"
    return run_command(command, "Running serializer tests")

def generate_coverage_report():
    """Generate coverage report."""
    print_banner("Coverage Report")

    # Generate coverage report
    run_command("coverage report -m", "Generating coverage report", check=False)

    # Generate HTML coverage report
    html_result = run_command("coverage html", "Generating HTML coverage report", check=False)

    if html_result:
        print(f"\n{Colors.GREEN}📊 HTML coverage report generated in htmlcov/index.html{Colors.END}")

    return True

def run_code_quality_checks():
    """Run code quality checks."""
    print_banner("Code Quality Checks")

    success = True

    # Black formatting check
    if not run_command("black --check --diff business_application/", "Black formatting check", check=False):
        print_warning("Code formatting issues found. Run 'black business_application/' to fix.")
        success = False

    # isort import check
    if not run_command("isort --check-only --diff business_application/", "Import sorting check", check=False):
        print_warning("Import sorting issues found. Run 'isort business_application/' to fix.")
        success = False

    # Flake8 linting
    if not run_command("flake8 business_application/ --max-line-length=120 --exclude=migrations", "Flake8 linting", check=False):
        print_warning("Linting issues found. Check output above.")
        success = False

    # MyPy type checking
    if not run_command("mypy business_application/ --ignore-missing-imports", "Type checking", check=False):
        print_warning("Type checking issues found. Check output above.")
        success = False

    if success:
        print_success("All code quality checks passed!")

    return success

def run_security_checks():
    """Run security checks."""
    print_banner("Security Checks")

    success = True

    # Bandit security check
    if not run_command("bandit -r business_application/ -ll -x */tests/*,*/migrations/*", "Bandit security check", check=False):
        print_warning("Security issues found. Check output above.")
        success = False

    # Safety dependency check
    if not run_command("safety check", "Dependency security check", check=False):
        print_warning("Vulnerable dependencies found. Check output above.")
        success = False

    if success:
        print_success("All security checks passed!")

    return success

def run_performance_tests():
    """Run performance tests."""
    print_banner("Performance Tests")

    print_step("Running health status calculation performance test")

    performance_script = """
import time
import sys
import os
import django

# Add current directory to Python path
sys.path.insert(0, '.')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'netbox.settings')
django.setup()

from business_application.models import TechnicalService, ServiceDependency
from business_application.models import ServiceType, DependencyType

# Create test services
services = []
for i in range(20):
    service = TechnicalService.objects.create(
        name=f'Perf Test Service {i}',
        service_type=ServiceType.TECHNICAL
    )
    services.append(service)

# Create dependencies
for i in range(15):
    if i < len(services) - 1:
        ServiceDependency.objects.create(
            name=f'Perf Dep {i}',
            upstream_service=services[i],
            downstream_service=services[i + 1],
            dependency_type=DependencyType.NORMAL
        )

# Test health calculation performance
start_time = time.time()
for service in services[:10]:
    health_status = service.health_status

end_time = time.time()
calculation_time = end_time - start_time

print(f"Health calculation time for 10 services: {calculation_time:.2f} seconds")
print(f"Average time per service: {calculation_time/10:.3f} seconds")

# Cleanup
for service in services:
    service.delete()

if calculation_time > 5.0:
    print("❌ Performance test failed: Too slow")
    sys.exit(1)
else:
    print("✅ Performance test passed")
"""

    with open('/tmp/performance_test.py', 'w') as f:
        f.write(performance_script)

    result = run_command("python /tmp/performance_test.py", "Health status performance test", check=False)

    # Cleanup
    if os.path.exists('/tmp/performance_test.py'):
        os.remove('/tmp/performance_test.py')

    return result

def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="NetBox Business Application Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--health", action="store_true", help="Run health status tests only")
    parser.add_argument("--models", action="store_true", help="Run model tests only")
    parser.add_argument("--serializers", action="store_true", help="Run serializer tests only")
    parser.add_argument("--correlation", action="store_true", help="Run alert correlation tests only")
    parser.add_argument("--fast", action="store_true", help="Run fast test suite (no coverage)")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage report")
    parser.add_argument("--quality", action="store_true", help="Run code quality checks only")
    parser.add_argument("--security", action="store_true", help="Run security checks only")
    parser.add_argument("--performance", action="store_true", help="Run performance tests only")
    parser.add_argument("--all", action="store_true", help="Run everything")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--no-env-check", action="store_true", help="Skip environment check")

    args = parser.parse_args()

    print_banner("NetBox Business Application Test Runner", Colors.MAGENTA)

    # Check environment
    if not args.no_env_check:
        if not check_environment():
            sys.exit(1)

    # Install dependencies if requested
    if args.install_deps:
        if not install_test_dependencies():
            print_error("Failed to install dependencies")
            sys.exit(1)

    start_time = time.time()
    success = True

    try:
        # Run specific test suites
        if args.unit or (not any([args.api, args.health, args.models, args.serializers,
                                 args.correlation, args.quality, args.security, args.performance]) and not args.all):
            success &= run_unit_tests(with_coverage=args.coverage)

        if args.api:
            success &= run_api_tests()

        if args.health:
            success &= run_health_tests()

        if args.models:
            success &= run_model_tests()

        if args.serializers:
            success &= run_serializer_tests()

        if args.correlation:
            success &= run_alert_correlation_tests()

        # Run all tests for comprehensive testing
        if args.all or (not args.fast and not any([args.unit, args.api, args.health, args.models,
                                                  args.serializers, args.correlation, args.quality,
                                                  args.security, args.performance])):
            success &= run_unit_tests(with_coverage=True)
            success &= run_api_tests()
            success &= run_health_tests()
            success &= run_model_tests()
            success &= run_serializer_tests()
            success &= run_alert_correlation_tests()

            if args.coverage or args.all:
                generate_coverage_report()

        # Code quality checks
        if args.quality or args.all:
            success &= run_code_quality_checks()

        # Security checks
        if args.security or args.all:
            success &= run_security_checks()

        # Performance tests
        if args.performance or args.all:
            success &= run_performance_tests()

        # Generate coverage report if requested
        if args.coverage and not args.all:
            generate_coverage_report()

    except KeyboardInterrupt:
        print_error("\nTest run interrupted by user")
        sys.exit(1)

    # Final summary
    end_time = time.time()
    total_time = end_time - start_time

    print_banner("Test Results Summary", Colors.MAGENTA)

    if success:
        print_success(f"All tests passed! ✨")
        print(f"{Colors.GREEN}Total time: {total_time:.2f} seconds{Colors.END}")
        print(f"\n{Colors.CYAN}🚀 Ready to push to GitHub!{Colors.END}")
    else:
        print_error(f"Some tests failed! 💥")
        print(f"{Colors.RED}Total time: {total_time:.2f} seconds{Colors.END}")
        print(f"\n{Colors.YELLOW}🔧 Please fix the issues above before pushing.{Colors.END}")

    # Usage hints
    print(f"\n{Colors.CYAN}💡 Usage hints:{Colors.END}")
    print(f"  - Run {Colors.BOLD}python run_tests.py --fast{Colors.END} for quick feedback")
    print(f"  - Run {Colors.BOLD}python run_tests.py --coverage{Colors.END} to see test coverage")
    print(f"  - Run {Colors.BOLD}python run_tests.py --quality{Colors.END} to check code quality")
    print(f"  - Run {Colors.BOLD}python run_tests.py --all{Colors.END} for comprehensive testing")

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
