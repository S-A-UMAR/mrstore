# Mr Store — Testing Guide

Comprehensive testing suite for backend validation, models, and API endpoints.

## Test Coverage

### Unit Tests
- **Player ID Validator**: Format validation, length bounds, character restrictions
- **Models**: Product, Order, SavedPlayerID creation and validation
- **Validators**: Edge cases, unicode handling, whitespace normalization

### Integration Tests  
- **API Endpoints**: Product listing, authentication, order creation
- **Authentication**: Registration, login, profile access, session management
- **Saved Player IDs**: Adding, removing, validation

### Workflow Tests
- **Guest Checkout**: Unauthenticated order flow
- **Authenticated Checkout**: Saved IDs, profile linking
- **Order Validation**: Invalid player IDs, missing fields

### Edge Case Tests
- **Whitespace Handling**: Leading/trailing spaces
- **Case Sensitivity**: Uppercase, lowercase, mixed case
- **Unicode Rejection**: Non-ASCII characters
- **Boundary Conditions**: Max length limits

## Running Tests

### Run All Tests
```bash
python manage.py test orders
```

### Run Specific Test Class
```bash
python manage.py test orders.tests.PubgPlayerIDValidatorTests
```

### Run Specific Test Method
```bash
python manage.py test orders.tests.PubgPlayerIDValidatorTests.test_valid_player_ids
```

### Run with Verbose Output
```bash
python manage.py test orders -v 2
```

### Run with Coverage Report
```bash
pip install coverage
coverage run --source='orders' manage.py test orders
coverage report
coverage html  # Creates htmlcov/index.html
```

## Test Results Interpretation

### Player ID Validation Tests
Expected behavior:
- ✅ Valid: `player123`, `PRO-GAMER-99`, `abc-123-def`
- ❌ Invalid: `player@123`, `-player`, `player--name`, `a` * 25

### API Tests
Expected status codes:
- `200 OK`: Successful GET requests
- `201 CREATED`: Successful POST creation
- `400 BAD REQUEST`: Validation errors (invalid player ID, etc.)
- `403 FORBIDDEN`: Unauthorized admin access
- `404 NOT FOUND`: Resource not found

### Authentication Tests
- Registration: Creates new user
- Login: Returns session on valid credentials
- Profile: Only accessible when authenticated

## Fixtures & Sample Data

The tests automatically create test data:
```python
# Sample Product
Product.objects.create(
    name='100 UC',
    uc_amount=100,
    price_ngn='300.00',
    price_kobo=30000,
    sku='UC-100',
    is_active=True,
)

# Sample User
User.objects.create_user(
    'testuser', 
    'test@example.com', 
    'password123'
)
```

## Continuous Integration

For CI/CD pipelines, use:
```bash
python manage.py test orders --keepdb --failfast
```

Options:
- `--keepdb`: Keep test database between runs (faster)
- `--failfast`: Stop on first failure
- `-v 2`: Verbose output

## Performance Notes

- Tests use in-memory SQLite by default (very fast)
- Full test suite typically runs in < 5 seconds
- Individual test methods run in milliseconds

## Troubleshooting

### Import Errors
Ensure Django is installed in venv and settings are configured:
```bash
python manage.py check
```

### Database Errors
Tests should use fresh database. If issues persist:
```bash
python manage.py flush
python manage.py test orders
```

### Test Failures
Check error messages for:
1. ValidationError - Player ID format issues
2. IntegrityError - Database constraint violations
3. AssertionError - Expected vs actual values

## Test Metrics

Current test suite includes:
- **11 test classes**
- **45+ test methods**
- **100% validator coverage**
- **Full API endpoint coverage**
- **End-to-end workflow tests**

## Future Test Additions

Recommended additions:
- [ ] Payment processing tests (with mocked Paystack)
- [ ] Webhook signature verification tests
- [ ] Wholesaler client integration tests
- [ ] Performance/load tests
- [ ] Email notification tests
- [ ] Rate limiting tests
- [ ] Admin dashboard API tests

## Contributing Tests

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all validators are tested
3. Test both success and failure paths
4. Add edge case tests
5. Update this documentation

Example test template:
```python
class NewFeatureTests(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        pass
    
    def test_success_case(self):
        """Test normal operation"""
        pass
    
    def test_error_case(self):
        """Test error handling"""
        pass
    
    def test_edge_case(self):
        """Test boundary conditions"""
        pass
```

## Related Documentation

- [Validation Rules](orders/validators.py)
- [API Documentation](API.md) 
- [Model Definitions](orders/models.py)
