# Testing Guide

This document describes the comprehensive testing infrastructure for the NetBox Business Application plugin.

## 🚀 Quick Start

### Local Testing

```bash
# Install test dependencies
python run_tests.py --install-deps

# Run all tests
python run_tests.py

# Run quick tests (no coverage)
python run_tests.py --fast

# Run with coverage report
python run_tests.py --coverage
```

### GitHub Actions

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests
- Daily scheduled runs
- Manual workflow dispatch

## 📊 Test Coverage

Our test suite covers:

- **API Endpoints**: Comprehensive testing of all REST API endpoints
- **Health Status Calculation**: Complex service dependency health logic
- **Alert Correlation**: Event processing and incident creation
- **Model Validation**: Database models and business logic
- **Serializer Logic**: API data serialization/deserialization
- **Performance**: Health calculation and alert processing performance
- **Security**: Code security and dependency vulnerability scanning

## 🧪 Test Types

### Unit Tests

Test individual components in isolation:

```bash
# Run all unit tests
python run_tests.py --unit

# Run specific test suites
python run_tests.py --models      # Model tests
python run_tests.py --api         # API tests
python run_tests.py --health      # Health status tests
python run_tests.py --serializers # Serializer tests
python run_tests.py --correlation # Alert correlation tests
```

### Integration Tests

Test component interactions and workflows:

```bash
# Integration tests run automatically in GitHub Actions
# They test real API workflows with a running NetBox instance
```

### Performance Tests

Test system performance under load:

```bash
python run_tests.py --performance
```

Performance thresholds:
- Health calculation: < 3.0s for 10 services
- Alert processing: < 0.5s per alert
- Database queries: < 20 per health check

## 🏗️ Test Structure

```
business_application/tests/
├── __init__.py
├── test_api_comprehensive.py    # Complete API endpoint tests
├── test_health_status.py        # Health status calculation tests
├── test_alert_correlation.py    # Alert correlation engine tests
├── test_models_enhanced.py      # Enhanced model tests
├── test_serializers.py          # Serializer validation tests
├── test_api_endpoints.py        # Legacy API tests (integration)
├── test_models.py               # Legacy model tests (basic)
├── test_filters.py              # Filter tests
└── test_views.py                # View tests
```

## 🔧 Local Development Workflow

### Before Making Changes

1. Run the full test suite:
```bash
python run_tests.py --all
```

2. Check code quality:
```bash
python run_tests.py --quality
```

### During Development

1. Run relevant tests quickly:
```bash
python run_tests.py --fast
```

2. Run specific test categories:
```bash
python run_tests.py --health  # For health status changes
python run_tests.py --api     # For API changes
```

### Before Pushing

1. Run comprehensive tests:
```bash
python run_tests.py --all
```

2. Check test coverage:
```bash
python run_tests.py --coverage
```

3. Ensure code quality:
```bash
python run_tests.py --quality --security
```

## 🚦 GitHub Actions Workflows

### CI/CD Pipeline (`.github/workflows/ci.yml`)

**Triggers**: Push, PR, Daily schedule

**What it does**:
- Tests across Python 3.10-3.12 and NetBox 4.0-4.2
- Runs comprehensive test suite with coverage
- Performs linting and code quality checks
- Runs integration tests with real NetBox instance
- Security vulnerability scanning
- Uploads coverage reports to Codecov

### Health Monitoring (`.github/workflows/health-monitoring.yml`)

**Triggers**: Every 4 hours, Manual dispatch

**What it does**:
- Validates health status calculation algorithms
- Tests service dependency health propagation
- Monitors API endpoint health
- Performance regression testing
- Creates GitHub issues on failure

### Code Quality (`.github/workflows/code-quality.yml`)

**Triggers**: Push, PR, Weekly schedule

**What it does**:
- Black code formatting check
- isort import sorting validation
- Flake8 linting
- MyPy type checking
- PyLint code analysis
- Bandit security scanning
- Code complexity analysis
- Documentation coverage check
- Dead code detection

### Release Readiness (`.github/workflows/release-readiness.yml`)

**Triggers**: Tag push, Manual dispatch

**What it does**:
- Comprehensive validation across all supported versions
- Performance benchmarking
- Security release scanning
- Compatibility matrix testing
- Release readiness report generation

## 📈 Test Metrics & Standards

### Coverage Requirements
- **Minimum**: 80% line coverage
- **Target**: 90% line coverage
- **Critical paths**: 100% coverage (health calculation, alert processing)

### Performance Standards
- Health status calculation: < 3 seconds for 10 services
- Alert processing: < 500ms per alert
- API response time: < 2 seconds
- Database queries: Optimized (< 20 queries per health check)

### Code Quality Standards
- **Black**: Enforced code formatting
- **isort**: Sorted imports
- **Flake8**: PEP 8 compliance (max line length: 120)
- **MyPy**: Type checking with minimal errors
- **PyLint**: Score ≥ 8.0/10
- **Bandit**: No high/medium security issues

## 🐛 Debugging Test Failures

### Local Test Failures

1. **Environment Issues**:
```bash
# Check Django settings
echo $DJANGO_SETTINGS_MODULE

# Verify NetBox installation
python -c "import netbox; print(netbox.__version__)"
```

2. **Database Issues**:
```bash
# Run migrations
python manage.py migrate

# Check database connection
python manage.py dbshell --command="SELECT 1;"
```

3. **Import Issues**:
```bash
# Check plugin installation
python -c "from business_application.models import TechnicalService"
```

### GitHub Actions Failures

1. **Check the workflow logs** for detailed error messages
2. **Review the test summary** in the GitHub Actions UI
3. **Download artifacts** for detailed reports (coverage, quality, security)
4. **Run the same test locally** to reproduce the issue

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Import errors | Check `PYTHONPATH` and plugin installation |
| Database errors | Ensure PostgreSQL/Redis are running |
| Timeout errors | Check test performance and database queries |
| Coverage drops | Add tests for new code |
| Quality failures | Run `black`, `isort`, fix linting issues |
| Security issues | Update dependencies, fix code issues |

## 🔄 Continuous Improvement

### Adding New Tests

1. **Create test file** in appropriate category
2. **Follow naming convention**: `test_<component>.py`
3. **Inherit from base test case** for common setup
4. **Add to local test runner** if needed
5. **Verify in GitHub Actions**

### Performance Monitoring

- Monitor test execution times in GitHub Actions
- Add performance tests for new features
- Set up alerting for performance regressions
- Regular performance baseline updates

### Test Data Management

- Use factories for test data creation
- Clean up test data in tearDown methods
- Use database transactions for isolation
- Mock external dependencies

## 📚 Testing Best Practices

### Writing Good Tests

1. **Descriptive names**: `test_health_status_down_when_incident_active`
2. **Single responsibility**: One assertion per test when possible
3. **Good coverage**: Test happy path, edge cases, and error conditions
4. **Independent**: Tests should not depend on each other
5. **Fast**: Mock external dependencies, use minimal test data

### Test Organization

```python
class ComponentTestCase(BaseTestCase):
    """Test component functionality"""

    def setUp(self):
        """Set up test data"""
        super().setUp()
        # Component-specific setup

    def test_happy_path(self):
        """Test normal operation"""
        pass

    def test_edge_case(self):
        """Test edge conditions"""
        pass

    def test_error_handling(self):
        """Test error conditions"""
        pass
```

### Performance Testing

```python
def test_performance_requirement(self):
    """Test meets performance requirements"""
    start_time = time.time()

    # Execute operation
    result = expensive_operation()

    end_time = time.time()
    execution_time = end_time - start_time

    self.assertLess(execution_time, 1.0, "Operation too slow")
    self.assertIsNotNone(result)
```

## 🎯 Test Automation Strategy

### Pre-commit Hooks (Recommended)

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]
EOF

# Install the git hook
pre-commit install
```

### IDE Integration

#### VS Code
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["business_application/tests"],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black"
}
```

#### PyCharm
- Enable pytest as test runner
- Configure Black as external tool
- Enable Flake8 inspections

## 📊 Monitoring & Reporting

### Test Metrics Dashboard

GitHub Actions provides:
- Test execution time trends
- Coverage reports and trends
- Code quality metrics over time
- Security scan results
- Performance benchmarks

### Alerting

Automatic alerts are created for:
- Health monitoring failures
- Security vulnerabilities
- Performance regressions
- Coverage drops below threshold

### Reports

Available reports:
- **Coverage Report**: Line and branch coverage
- **Quality Report**: Code quality metrics and issues
- **Security Report**: Vulnerability scan results
- **Performance Report**: Benchmark results and trends
- **Release Readiness**: Comprehensive pre-release validation

---

## 🤝 Contributing to Tests

When contributing new features:

1. **Add comprehensive tests** covering new functionality
2. **Update existing tests** if behavior changes
3. **Ensure performance standards** are met
4. **Add documentation** for new test patterns
5. **Run full test suite** before submitting PR

For questions about testing, check existing test patterns or open a GitHub issue.

**Happy Testing! 🧪✨**
