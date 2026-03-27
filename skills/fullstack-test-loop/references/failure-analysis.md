# Failure Analysis Reference

## Parsing Test Output by Framework

### JUnit 5 (Maven Surefire)

**Console output pattern:**
```
[ERROR] Tests run: 5, Failures: 1, Errors: 0, Skipped: 0, Time elapsed: 1.234 s <<< FAILURE! -- in com.example.TestClass
[ERROR] testMethod(com.example.TestClass)  Time elapsed: 0.05 s  <<< FAILURE!
org.opentest4j.AssertionFailedError: expected: <3> but was: <0>
  at com.example.TestClass.testMethod(TestClass.java:42)
```

**XML report (target/surefire-reports/TEST-*.xml):**
```xml
<testcase name="testMethod" classname="com.example.TestClass" time="0.05">
  <failure type="org.opentest4j.AssertionFailedError"
           message="expected: &lt;3&gt; but was: &lt;0&gt;">
    at com.example.TestClass.testMethod(TestClass.java:42)
  </failure>
</testcase>
```

### Go test

```
--- FAIL: TestGetUsers (0.00s)
    user_service_test.go:25: expected 3 users, got 0
FAIL
FAIL    example.com/internal/service    0.012s
```

### pytest

```
FAILED tests/test_service.py::TestUserService::test_get_users - AssertionError: assert 0 == 3
E       AssertionError: assert 0 == 3
E        +  where 0 = len([])
tests/test_service.py:42: AssertionError
```

### Vitest / Jest

```
 FAIL  src/__tests__/Component.test.ts > Component > renders correctly
AssertionError: expected '<div>Hello</div>' to contain 'Welcome'
 ❯ src/__tests__/Component.test.ts:15:25
     13|   const wrapper = mount(Component)
     14|   const html = wrapper.html()
     15|   expect(html).toContain('Welcome')
       |                         ^
```

### Shell E2E

```
[FAIL] POST /api/v1/registration: expected 201, got 400
  Response: {"code":400,"message":"name is required"}
```

### TypeScript Compiler (tsc / vue-tsc)

```
src/types/dto.ts(15,3): error TS2322: Type 'string' is not assignable to type 'number'.
src/components/Table.vue(42,5): error TS2339: Property 'districtName' does not exist on type 'District'.
```

---

## Failure Categories

Categorize each failure to determine the fix approach:

### Category 1: Compilation / Type Error
- TypeScript type mismatches
- Java compilation errors
- Missing imports / undefined symbols
- **Fix approach:** Trace the type change to its origin, fix at source

### Category 2: Test Setup / Configuration
- `Failed to load ApplicationContext` (Spring)
- `fixture not found` (pytest)
- `NullInjectorError` (Angular)
- Missing mock setup
- **Fix approach:** Fix test infrastructure, not business logic

### Category 3: Assertion Failure
- `expected X but was Y`
- `assert X == Y`
- **Fix approach:** Determine if the test or the code is wrong.
  If the code recently changed intentionally, update the test.
  If the code changed unintentionally, fix the code.

### Category 4: Runtime Exception
- NullPointerException, IndexOutOfBoundsException
- TypeError, AttributeError
- panic, unwrap failure
- **Fix approach:** Trace data flow to find where null/invalid data enters

### Category 5: Timeout / Performance
- `Timed out after 5000ms`
- `context deadline exceeded`
- **Fix approach:** Check for infinite loops, missing async awaits, DB queries without limits

### Category 6: Environment / Infrastructure
- `Connection refused`
- `ECONNREFUSED`
- `No such file or directory`
- **Fix approach:** Fix environment setup, not code

### Category 7: API Contract Mismatch
- Frontend type doesn't match API response
- Field naming convention mismatch (camelCase vs snake_case)
- Response wrapper mismatch (`{data}` vs raw)
- **Fix approach:** Align the contract — check API spec, fix the side that diverged

---

## Clustering Algorithm

Before fixing anything, cluster failures by likely root cause:

### Step 1: Group by location
```
Cluster A: 3 failures in BaseDataServiceTest
Cluster B: 2 failures in RegistrationControllerTest
Cluster C: 1 failure in frontend type check
```

### Step 2: Group by exception type within location
```
Cluster A1: 2 failures with NullPointerException in BaseDataServiceTest → same mock missing
Cluster A2: 1 failure with AssertionError in BaseDataServiceTest → different issue
```

### Step 3: Check for cross-cluster root cause
If Cluster A and Cluster B both involve the same service method or the same database entity,
they likely share a root cause. Merge them.

### Step 4: Rank by impact
Fix the cluster that affects the most tests first. This gives the best ROI per fix iteration.

---

## Causal Chain Template

For each failure cluster, fill in this template before attempting any fix:

```
FAILURE CLUSTER: [description]
  Affects: [N] tests in [module(s)]

  SYMPTOM:    [what the test output shows]
  PROXIMATE:  [the immediate code-level cause]
  ROOT CAUSE: [the underlying reason this happened]

  FIX:        [specific change to make]
  FILES:      [file paths to modify]
  RISK:       [could this fix break something else?]
```

### Example 1: Missing Mock

```
FAILURE CLUSTER: SecurityContext null in tests
  Affects: 5 tests in BaseDataServiceTest, RegistrationControllerTest

  SYMPTOM:    expected 200 but got 403 / NullPointerException on getCurrentUser()
  PROXIMATE:  SecurityContext bean returns null when no auth header is set
  ROOT CAUSE: New test class doesn't have test security configuration

  FIX:        Add @ActiveProfiles("test") and @WithMockUser to test class
  FILES:      src/test/java/.../BaseDataServiceTest.java
  RISK:       Low — only affects test setup
```

### Example 2: API Contract Change

```
FAILURE CLUSTER: Frontend type errors after API change
  Affects: 3 type errors in frontend, 2 E2E assertion failures

  SYMPTOM:    TS2339: Property 'districtName' does not exist on type 'District'
  PROXIMATE:  Frontend interface has `districtName` but API returns `district_name`
  ROOT CAUSE: Backend added snake_case serialization but frontend types weren't updated

  FIX:        Update frontend TypeScript interface to use snake_case field names
  FILES:      frontend/src/types/district.ts
  RISK:       Medium — need to update all usages of districtName in templates
```

### Example 3: Data Flow Bug

```
FAILURE CLUSTER: Aggregation returns 0
  Affects: 2 tests in AggregationServiceTest

  SYMPTOM:    expected sum 150.0000 but was 0.0000
  PROXIMATE:  AggregationService.calculate() returns 0
  ROOT CAUSE: New filter condition excludes all records when status is null

  FIX:        Handle null status in filter: treat null as "all statuses"
  FILES:      src/main/java/.../AggregationService.java:87
  RISK:       Medium — verify null handling doesn't break other callers
```
