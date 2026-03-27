# Fix Strategies Reference

## Decision Tree

```
START: A test failure cluster has been identified with its causal chain.

Q1: Is the failure in TEST code (setup, mocks, assertions, fixtures)?
  YES → Go to "Test Code Fixes"
  NO  → Q2

Q2: Is it a compilation or type error?
  YES → Go to "Compilation Fixes"
  NO  → Q3

Q3: Is it a runtime behavior bug (wrong result, exception, unexpected state)?
  YES → Go to "Runtime Fixes"
  NO  → Q4

Q4: Is it an environment or configuration issue?
  YES → Go to "Config Fixes"
  NO  → Q5

Q5: Is it a cross-module contract mismatch?
  YES → Go to "Contract Fixes"
  NO  → Flag as NEEDS_HUMAN_INPUT with explanation
```

---

## Test Code Fixes

These are the safest fixes — they only change test code, not production code.

### Missing Mock Setup

**Pattern:** Test calls a service that depends on another bean, but the mock isn't configured.

```java
// Before: mock returns null by default
@MockBean private SecurityService securityService;

// After: configure mock in @BeforeEach
@BeforeEach
void setUp() {
    when(securityService.getCurrentUser()).thenReturn(testUser);
}
```

### Outdated Assertion

**Pattern:** Production code changed intentionally, but test assertion wasn't updated.

**How to tell:** Check git log for recent changes to the production code. If the change was
intentional (feature commit, not a bug), update the test.

```python
# Before: test expects old format
assert response.json()["name"] == "Test District"

# After: API now returns snake_case wrapped response
assert response.json()["data"]["name"] == "Test District"
```

### Missing Test Annotation

**Pattern:** Test class missing framework-specific annotation.

Common missing annotations:
- Spring: `@SpringBootTest`, `@ActiveProfiles("test")`, `@WithMockUser`
- JUnit: `@ExtendWith(MockitoExtension.class)`
- pytest: `@pytest.mark.asyncio`, `@pytest.fixture`

### Fixture / Test Data Issues

**Pattern:** Test data conflicts with other tests (unique constraints, shared state).

Fix: Use unique identifiers per test, or add proper cleanup in @AfterEach / teardown.

---

## Compilation Fixes

### Type Mismatch

**Pattern:** A function signature changed but callers weren't updated.

**Strategy:**
1. Find where the type was changed (git diff or git log)
2. Determine if the change was intentional
3. If intentional: update all callers to match new signature
4. If unintentional: revert the type change

### Missing Import

**Pattern:** New code references a symbol that isn't imported.

**Strategy:** Add the import. Check if the symbol moved (refactoring) or is new.

### Deleted Symbol

**Pattern:** Code references a function/class/variable that no longer exists.

**Strategy:**
1. Check git log for when it was deleted
2. Find the replacement (renamed? moved? replaced by different approach?)
3. Update the reference to use the replacement

---

## Runtime Fixes

These change production code. Apply with care.

### NullPointerException / Null Reference

**Strategy:**
1. Trace the null value backward through the call chain
2. Find where the value should have been set
3. Fix at the source — add the missing assignment or initialization
4. If the null is legitimate (optional data), add a null check at the consumer

**Do NOT:** Add null checks everywhere. Fix the root cause.

### Wrong Result (Assertion Failure on Business Logic)

**Strategy:**
1. Read the test to understand expected behavior
2. Read the production code to understand actual behavior
3. Identify the divergence point
4. Determine which is correct — the test expectation or the code
5. Fix the incorrect side

**Critical question:** Was the production code recently changed? If so, the change might
be the bug. If not, the test expectation might be wrong.

### Unhandled Exception

**Strategy:**
1. Check if the exception is from bad input (add validation) or bad state (fix state management)
2. Add appropriate error handling at the right level
3. Don't catch and swallow — handle meaningfully

---

## Config Fixes

### Database Configuration

**Pattern:** Tests fail because they can't connect to a database or the schema is wrong.

**Common fixes:**
- Add or fix `application-test.yml` / `application-test.properties`
- Set `spring.jpa.hibernate.ddl-auto=create-drop` for test profile
- Ensure H2 compatibility mode matches production DB (e.g., `MODE=PostgreSQL`)
- Fix Flyway migration path for test environment

### Missing Environment Variable

**Pattern:** Code reads an env var that isn't set in test environment.

**Fix:** Add the variable to:
- `application-test.yml` (Spring)
- `.env.test` (Node.js)
- `conftest.py` fixtures (Python)
- Test configuration class

### Port / URL Configuration

**Pattern:** Test tries to reach a service at wrong URL/port.

**Fix:** Check and align:
- docker-compose port mappings
- application config for test profile
- E2E test script base URL

---

## Contract Fixes

### Field Naming Mismatch

**Pattern:** Backend uses `snake_case`, frontend uses `camelCase`.

**Strategy:**
1. Check the project convention (API spec, CLAUDE.md settings)
2. If convention says snake_case: fix the frontend TypeScript types
3. If convention says camelCase: fix the backend serialization config
4. Update all affected interfaces and usages

### Response Shape Mismatch

**Pattern:** Frontend expects `response.data.items` but API returns `response.items`.

**Strategy:**
1. Check API interceptors (Axios interceptors, fetch wrappers)
2. Check if the wrapper `{code, message, data}` is applied consistently
3. Fix the side that diverges from the API spec

### Enum Value Mismatch

**Pattern:** Backend enum has new/changed values that frontend doesn't know about.

**Strategy:**
1. Find the source of truth (usually backend)
2. Update the frontend enum/type definition to match
3. Handle any UI display logic for new values

---

## Fix Constraints

These rules apply to ALL fixes:

1. **Minimal diff**: Change the fewest files and lines possible. One root cause = one fix.

2. **No drive-by refactoring**: If you see messy code adjacent to the fix, leave it alone.
   The goal is passing tests, not code beauty.

3. **No new features**: Don't add error handling, logging, or validation that wasn't there
   before, unless it's the direct cause of the failure.

4. **Verify immediately**: After each fix, re-run only the affected tests to confirm the fix
   works before moving to the next failure.

5. **Three strikes rule**: If the same failure persists after 3 fix attempts, stop trying
   and flag it as BLOCKED. Explain what you tried and what you think is going on.

6. **Regression guard**: If a fix causes NEW test failures, immediately revert it.
   The original failure is better than a regression.

7. **Ask when uncertain**: If you're not sure whether to change the test or the production
   code, flag it as NEEDS_HUMAN_INPUT with context about both options.

---

## Vue SFC Safety Rules

When fixing ANY `.vue` file, read `references/vue-fix-safety.md` first.

**Summary:** Only modify code within `<script>` or `<script setup>` blocks. Modifications to
`<template>` and `<style>` blocks are FORBIDDEN. If the root cause is in template/style,
mark as `NEEDS_HUMAN_REVIEW` with the exact location and suggested change.

**After any `.vue` script fix:** Run the visual regression check (see `references/visual-regression.md`).
If visual regression is detected, revert the fix immediately.

---

## Fix Logging

Track every fix attempt for the final report:

```
Fix #1 (iteration 1):
  Cluster: SecurityContext null in 5 tests
  Change: Added @ActiveProfiles("test") to EventServiceTest
  File: backend/src/test/java/.../EventServiceTest.java
  Result: 5 tests now pass ✓

Fix #2 (iteration 1):
  Cluster: Type mismatch in frontend
  Change: Updated District interface field names to snake_case
  File: frontend/src/types/district.ts
  Result: 3 type errors resolved ✓

Fix #3 (iteration 2):
  Cluster: AggregationService returns 0
  Change: Handle null status in filter condition
  File: backend/src/main/java/.../AggregationService.java:87
  Result: FAILED — test still fails, different error now

Fix #3b (iteration 2):
  Cluster: AggregationService returns 0
  Change: Also initialize default status in constructor
  File: backend/src/main/java/.../AggregationService.java:23
  Result: 2 tests now pass ✓
```
