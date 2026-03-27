# Backend Frameworks Reference

## Java / Maven (Spring Boot)

### Commands

```bash
# Compile only
mvn compile -q -f backend/pom.xml
# or with wrapper
./mvnw compile -q -f backend/pom.xml

# Run all tests
mvn test -f backend/pom.xml

# Run specific test class
mvn test -Dtest=BaseDataServiceTest -f backend/pom.xml

# Run specific test method
mvn test -Dtest=BaseDataServiceTest#testGetDistricts -f backend/pom.xml

# Verbose output
mvn test -X -f backend/pom.xml
```

### Output Parsing

Maven Surefire output format:
```
[INFO] Tests run: 5, Failures: 1, Errors: 0, Skipped: 0

[ERROR] testGetDistricts(com.example.service.BaseDataServiceTest)
  Time elapsed: 0.043 s  <<< FAILURE!
  org.opentest4j.AssertionFailedError: expected: <3> but was: <0>
    at com.example.service.BaseDataServiceTest.testGetDistricts(BaseDataServiceTest.java:42)
```

Extract:
- Test class: `com.example.service.BaseDataServiceTest`
- Test method: `testGetDistricts`
- Error type: `AssertionFailedError` (assertion) or exception name
- Message: `expected: <3> but was: <0>`
- File + line: `BaseDataServiceTest.java:42`

### Common Failure Patterns

| Pattern | Root Cause | Fix |
|---------|-----------|-----|
| `Failed to load ApplicationContext` | Missing bean, wrong config, circular dependency | Check @Configuration, @Bean, component scan |
| `NullPointerException` in service | Missing @MockBean or @InjectMocks setup | Add mock setup in @BeforeEach |
| `expected 200 but got 403` | Security config not relaxed for test | Add @WithMockUser or dev-mode token |
| `Table "X" not found` | H2 dialect mismatch or missing Flyway migration | Check application-test.yml ddl-auto setting |
| `DataIntegrityViolationException` | Unique constraint in test data | Use unique IDs in test fixtures |
| `No qualifying bean of type` | Missing @MockBean for dependency | Add @MockBean annotation |
| `Connection refused` | Test trying to reach external service | Mock the external dependency |

### Surefire Report Location

After `mvn test`, XML reports are at:
`target/surefire-reports/TEST-<ClassName>.xml`

These contain structured test results parseable for detailed failure analysis.

---

## Java / Gradle

### Commands

```bash
# Compile
./gradlew compileJava -q

# Run all tests
./gradlew test

# Run specific test class
./gradlew test --tests "com.example.service.BaseDataServiceTest"

# Run specific test method
./gradlew test --tests "com.example.service.BaseDataServiceTest.testGetDistricts"

# Verbose
./gradlew test --info
```

### Output Parsing

Gradle test reports are at: `build/reports/tests/test/index.html`
XML reports at: `build/test-results/test/TEST-<ClassName>.xml`

Same JUnit 5 format as Maven Surefire.

---

## Go

### Commands

```bash
# Build check
go build ./...

# Run all tests
go test ./...

# Run specific package
go test ./internal/service/...

# Run specific test
go test ./internal/service -run TestGetUsers

# Verbose
go test -v ./...

# With race detection
go test -race ./...

# With coverage
go test -cover ./...
```

### Output Parsing

```
--- FAIL: TestGetUsers (0.00s)
    user_service_test.go:25: expected 3 users, got 0
FAIL
FAIL    example.com/internal/service    0.012s
```

Extract:
- Test name: `TestGetUsers`
- File + line: `user_service_test.go:25`
- Message: `expected 3 users, got 0`
- Package: `example.com/internal/service`

### Common Failure Patterns

| Pattern | Root Cause | Fix |
|---------|-----------|-----|
| `undefined: FunctionName` | Missing import or unexported function | Check package visibility, imports |
| `connection refused` | Database/service not running | Use test doubles or testcontainers |
| `context deadline exceeded` | Test timeout | Increase timeout or fix slow operation |
| `race detected` | Data race | Add proper synchronization (mutex, channel) |

---

## Rust

### Commands

```bash
# Check (faster than build)
cargo check

# Run all tests
cargo test

# Run specific test
cargo test test_name

# Verbose (show println! output)
cargo test -- --nocapture

# Run tests in specific module
cargo test module_name::
```

### Output Parsing

```
test result: FAILED. 4 passed; 1 failed; 0 ignored

failures:
---- service::tests::test_get_users stdout ----
thread 'service::tests::test_get_users' panicked at 'assertion failed: (left == right)
  left: 0
  right: 3', src/service.rs:142:9
```

---

## Python / pytest

### Commands

```bash
# Run all tests
pytest
# or
python -m pytest

# Run specific file
pytest tests/test_service.py

# Run specific class
pytest tests/test_service.py::TestUserService

# Run specific test
pytest tests/test_service.py::TestUserService::test_get_users

# Verbose
pytest -v

# With coverage
pytest --cov=src

# Stop on first failure
pytest -x
```

### Output Parsing

```
FAILED tests/test_service.py::TestUserService::test_get_users - AssertionError: assert 0 == 3
```

Extract:
- File: `tests/test_service.py`
- Class: `TestUserService`
- Method: `test_get_users`
- Error: `AssertionError`
- Message: `assert 0 == 3`

### Common Failure Patterns

| Pattern | Root Cause | Fix |
|---------|-----------|-----|
| `ModuleNotFoundError` | Missing dependency or wrong PYTHONPATH | pip install or fix imports |
| `fixture 'db' not found` | Missing conftest.py fixture | Add fixture or conftest |
| `IntegrityError` | Database constraint violation | Fix test data or use factory |
| `ConnectionRefusedError` | External service not mocked | Add pytest-mock or responses library |

---

## Ruby / RSpec

### Commands

```bash
# Run all tests
bundle exec rspec

# Run specific file
bundle exec rspec spec/services/user_service_spec.rb

# Run specific example
bundle exec rspec spec/services/user_service_spec.rb:25

# Verbose
bundle exec rspec --format documentation
```

---

## .NET / dotnet

### Commands

```bash
# Build
dotnet build

# Run all tests
dotnet test

# Run specific project
dotnet test tests/MyProject.Tests

# Verbose
dotnet test --verbosity detailed
```
