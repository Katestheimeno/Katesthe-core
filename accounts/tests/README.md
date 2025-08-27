# Accounts App Test Suite

This directory contains comprehensive tests for the accounts app, following the same structure as the main application.

## Test Structure

```
accounts/tests/
├── factories/           # Test data factories using factory-boy
│   ├── __init__.py
│   └── _user.py        # User model factories
├── controllers/         # Tests for views/controllers
│   ├── __init__.py
│   └── test_auth.py    # Authentication controller tests
├── serializers/         # Tests for serializers
│   ├── __init__.py
│   └── test_auth.py    # Authentication serializer tests
├── models/             # Tests for models
│   ├── __init__.py
│   └── test_user.py    # User model tests
├── services/           # Tests for business logic services
│   └── __init__.py
├── selectors/          # Tests for query logic
│   └── __init__.py
├── conftest.py         # Pytest configuration and fixtures
└── README.md           # This file
```

## Test Categories

### 🏭 Factories (`factories/`)
- **UserFactory**: Creates test user instances with realistic data
- **InactiveUserFactory**: Creates inactive users
- **UnverifiedUserFactory**: Creates unverified users
- **StaffUserFactory**: Creates staff users
- **SuperUserFactory**: Creates superusers

### 🎮 Controllers (`controllers/`)
Tests for authentication views and endpoints:
- **JWT Token Creation**: Login with username/email
- **JWT Logout**: Token blacklisting
- **User Activation**: Email verification flow
- **User Profile**: CRUD operations via /me endpoint
- **Error Handling**: Invalid credentials, missing data

### 📝 Serializers (`serializers/`)
Tests for data validation and transformation:
- **CustomTokenObtainPairSerializer**: JWT token generation and validation
- **UserCreateSerializer**: User registration validation
- **UserDeleteSerializer**: Password confirmation for deletion
- **UserSerializer**: General user data serialization
- **CurrentUserSerializer**: Current user profile management

### 🗄️ Models (`models/`)
Tests for User model functionality:
- **User Creation**: Manager methods and validation
- **User Status**: Active/inactive, verified/unverified states
- **User Timestamps**: Auto-generated timestamps
- **Database Constraints**: Unique fields, indexes
- **String Representation**: Model display methods

## Running Tests

### Using Docker Compose
```bash
# Run all tests
docker compose exec web python -m pytest accounts/tests/

# Run with coverage
docker compose exec web python -m pytest accounts/tests/ --cov=accounts --cov-report=html

# Run specific test file
docker compose exec web python -m pytest accounts/tests/controllers/test_auth.py -v

# Run specific test class
docker compose exec web python -m pytest accounts/tests/controllers/test_auth.py::TestCustomJWTTokenCreateView -v

# Run specific test method
docker compose exec web python -m pytest accounts/tests/controllers/test_auth.py::TestCustomJWTTokenCreateView::test_jwt_token_creation_success -v
```

### Using Pytest Directly
```bash
# Run tests with coverage
pytest accounts/tests/ --cov=accounts --cov-report=term-missing
# to run all proejct tests
uv run pytest --ds=config.django.test --cov=. --cov-report=term-missing


# Run tests with markers
pytest accounts/tests/ -m "auth"
pytest accounts/tests/ -m "unit"
pytest accounts/tests/ -m "integration"

# Run tests in parallel
pytest accounts/tests/ -n auto

# Run tests with verbose output
pytest accounts/tests/ -v -s
```

## Test Fixtures

The `conftest.py` file provides reusable fixtures:

### User Fixtures
- `user`: Regular active user
- `inactive_user`: Inactive user
- `unverified_user`: Unverified user
- `staff_user`: Staff user
- `superuser`: Superuser

### Client Fixtures
- `api_client`: Unauthenticated API client
- `authenticated_client`: Authenticated client with regular user
- `staff_client`: Authenticated client with staff user
- `superuser_client`: Authenticated client with superuser

### Token Fixtures
- `user_tokens`: JWT tokens for regular user
- `staff_tokens`: JWT tokens for staff user

## Coverage Requirements

- **Minimum Coverage**: 80% (configured in pytest.ini)
- **Coverage Reports**: HTML, XML, and terminal output
- **Coverage Location**: `htmlcov/index.html`

## Test Data

All tests use factory-boy to generate realistic test data:
- Users are created with proper passwords
- Email addresses are normalized to lowercase
- Usernames are unique and follow naming conventions
- Timestamps are automatically generated

## Best Practices

1. **Use Factories**: Always use factories instead of creating objects manually
2. **Test Isolation**: Each test should be independent and not rely on other tests
3. **Meaningful Names**: Test method names should clearly describe what they test
4. **Assertions**: Use specific assertions that test the exact behavior
5. **Error Cases**: Always test both success and failure scenarios
6. **Coverage**: Aim for high coverage but focus on critical paths

## Adding New Tests

When adding new functionality:

1. **Create Factory**: Add factory methods in `factories/_user.py` if needed
2. **Add Fixtures**: Add reusable fixtures in `conftest.py`
3. **Write Tests**: Create tests in the appropriate directory
4. **Update Coverage**: Ensure new code is covered by tests
5. **Document**: Update this README if adding new test categories

## Debugging Tests

### Common Issues
- **Database Issues**: Use `--reuse-db` flag to reuse test database
- **Migration Issues**: Use `--nomigrations` flag to skip migrations
- **Import Issues**: Ensure all imports are correct and paths are valid

### Debug Commands
```bash
# Run single test with debug output
pytest accounts/tests/controllers/test_auth.py::TestCustomJWTTokenCreateView::test_jwt_token_creation_success -v -s

# Run tests with maximum verbosity
pytest accounts/tests/ -vvv

# Run tests and stop on first failure
pytest accounts/tests/ -x

# Run tests and show local variables on failure
pytest accounts/tests/ -l
```

## Integration with CI/CD

The test suite is designed to work with CI/CD pipelines:
- Coverage reports are generated in XML format
- Tests fail if coverage drops below 80%
- All tests can be run in Docker containers
- Exit codes are properly set for CI systems
