# Test Generation Reference

When a test phase has no existing tests, auto-generate comprehensive test coverage.
This file provides generation strategies per framework and layer.

## Table of Contents

- [General Principles](#general-principles)
- [Backend](#backend)
  - [Java/Spring Boot](#javaspring-boot)
  - [Go](#go)
  - [Python/FastAPI/Django](#pythonfastapidjango)
  - [Rust](#rust)
- [Frontend](#frontend)
  - [Vue 3 + Vitest](#vue-3--vitest)
  - [React + Vitest/Jest](#react--vitestjest)
  - [Angular](#angular)
- [API E2E](#api-e2e)
  - [Shell-based E2E Script](#shell-based-e2e-script)
- [Browser E2E](#browser-e2e)
  - [Route-based Flow Generation](#route-based-flow-generation)

---

## General Principles

1. **Comprehensive, not smoke**: Test all public interfaces, not just one happy path
2. **Read the source first**: Scan all source files to understand the domain before generating
3. **Match project conventions**: Use the project's naming style, directory structure, import patterns
4. **Test behavior, not implementation**: Assert on outputs and side effects, not internal state
5. **Include error paths**: Invalid input, null/empty, boundary conditions, auth failures
6. **No mocks for things that are easy to set up**: Prefer in-memory DBs over mocking repositories
7. **Generated tests must compile and run**: Verify imports, types, and dependencies are correct

---

## Backend

### Java/Spring Boot

**Discovery:**
1. Scan `src/main/java/**/` for `@RestController`, `@Controller`, `@Service`, `@Repository` classes
2. For each class, extract public methods with their parameters and return types
3. Check `src/test/java/` to see if tests already exist (skip classes that have tests)

**Test directory:** `src/test/java/` mirroring the main source structure

**Dependencies (add to pom.xml if missing):**
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```

**Controller test template:**
```java
@WebMvcTest(XxxController.class)
class XxxControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private XxxService xxxService;

    @Test
    void getAll_returnsOk() throws Exception {
        when(xxxService.findAll()).thenReturn(List.of(/* sample data */));
        mockMvc.perform(get("/api/xxx"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data").isArray());
    }

    @Test
    void getById_notFound_returns404() throws Exception {
        when(xxxService.findById(999L)).thenThrow(new ResourceNotFoundException("Not found"));
        mockMvc.perform(get("/api/xxx/999"))
            .andExpect(status().isNotFound());
    }

    @Test
    void create_validInput_returns201() throws Exception {
        // POST with valid JSON body
    }

    @Test
    void create_invalidInput_returns400() throws Exception {
        // POST with missing required fields
    }
}
```

**Service test template:**
```java
@ExtendWith(MockitoExtension.class)
class XxxServiceTest {

    @Mock
    private XxxRepository xxxRepository;

    @InjectMocks
    private XxxService xxxService;

    @Test
    void findAll_returnsAllEntities() { /* ... */ }

    @Test
    void findById_exists_returnsEntity() { /* ... */ }

    @Test
    void findById_notExists_throwsException() { /* ... */ }

    @Test
    void create_validInput_savesAndReturns() { /* ... */ }

    @Test
    void create_duplicateName_throwsException() { /* ... */ }

    @Test
    void delete_exists_removesEntity() { /* ... */ }
}
```

**Coverage targets per class type:**
- Controller: all endpoints × (valid input, invalid input, not found, auth required)
- Service: all public methods × (happy path, error path, edge cases)
- Repository: only if custom queries exist (Spring Data auto-generated methods are trusted)

---

### Go

**Discovery:**
1. Scan for `func` declarations in `*.go` files (excluding `*_test.go`)
2. For each package, find exported functions and methods
3. Check for existing `*_test.go` files

**Test file:** `xxx_test.go` adjacent to `xxx.go`

**Template:**
```go
func TestXxxService_Create(t *testing.T) {
    tests := []struct {
        name    string
        input   CreateXxxInput
        wantErr bool
    }{
        {"valid input", CreateXxxInput{Name: "test"}, false},
        {"empty name", CreateXxxInput{Name: ""}, true},
        {"duplicate name", CreateXxxInput{Name: "existing"}, true},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            svc := NewXxxService(mockRepo)
            result, err := svc.Create(tt.input)
            if tt.wantErr {
                assert.Error(t, err)
            } else {
                assert.NoError(t, err)
                assert.Equal(t, tt.input.Name, result.Name)
            }
        })
    }
}
```

**Use table-driven tests** — this is Go convention.

---

### Python/FastAPI/Django

**Discovery:**
1. Scan for route decorators (`@app.get`, `@router.post`, `@api_view`)
2. Scan for service/model classes
3. Check for existing `test_*.py` or `*_test.py` files

**Test file:** `tests/test_xxx.py` or adjacent `test_xxx.py`

**FastAPI template:**
```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_get_all_xxx():
    response = client.get("/api/xxx")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_xxx_valid():
    response = client.post("/api/xxx", json={"name": "test"})
    assert response.status_code == 201

def test_create_xxx_invalid():
    response = client.post("/api/xxx", json={})
    assert response.status_code == 422  # validation error
```

---

### Rust

**Discovery:**
1. Scan for `pub fn` and `pub async fn` in `src/**/*.rs`
2. Check for existing `#[cfg(test)]` modules or `tests/` directory

**Test location:** `#[cfg(test)] mod tests` block within each source file, or `tests/` for integration tests.

**Template:**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_valid_input() {
        let result = create_xxx(ValidInput { name: "test".into() });
        assert!(result.is_ok());
    }

    #[test]
    fn test_create_empty_name_fails() {
        let result = create_xxx(ValidInput { name: "".into() });
        assert!(result.is_err());
    }
}
```

---

## Frontend

### Vue 3 + Vitest

**Setup (if Vitest not installed):**

1. Install: `npm install -D vitest @vue/test-utils jsdom`
2. Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
```
3. Add script to package.json: `"test": "vitest run"`

**Discovery:**
1. Scan `src/components/**/*.vue` for all components
2. Scan `src/composables/` or `src/hooks/` for composables
3. Scan `src/stores/` for Pinia/Vuex stores
4. Scan `src/utils/` for utility functions
5. Check for existing `*.test.ts` or `*.spec.ts` files

**Component test template:**
```typescript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import XxxComponent from '../XxxComponent.vue'

describe('XxxComponent', () => {
  it('renders without errors', () => {
    const wrapper = mount(XxxComponent, {
      props: { /* required props */ },
    })
    expect(wrapper.exists()).toBe(true)
  })

  it('displays the title prop', () => {
    const wrapper = mount(XxxComponent, {
      props: { title: 'Hello' },
    })
    expect(wrapper.text()).toContain('Hello')
  })

  it('emits event on button click', async () => {
    const wrapper = mount(XxxComponent)
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('submit')).toBeTruthy()
  })

  it('handles loading state', () => {
    const wrapper = mount(XxxComponent, {
      props: { loading: true },
    })
    expect(wrapper.find('.loading-spinner').exists()).toBe(true)
  })

  it('handles empty data', () => {
    const wrapper = mount(XxxComponent, {
      props: { items: [] },
    })
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })
})
```

**Composable test template:**
```typescript
import { describe, it, expect } from 'vitest'
import { useXxx } from '../useXxx'

describe('useXxx', () => {
  it('returns initial state', () => {
    const { data, loading, error } = useXxx()
    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBeNull()
  })
})
```

**Store test template (Pinia):**
```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useXxxStore } from '../xxxStore'

describe('XxxStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('has correct initial state', () => {
    const store = useXxxStore()
    expect(store.items).toEqual([])
  })

  it('adds item', () => {
    const store = useXxxStore()
    store.addItem({ id: 1, name: 'test' })
    expect(store.items).toHaveLength(1)
  })
})
```

**Coverage targets:**
- Components: render, props, events, slots, loading/error/empty states
- Composables: initial state, state transitions, cleanup
- Stores: initial state, all actions, all getters
- Utils: all exported functions with boundary cases

---

### React + Vitest/Jest

**Setup (if not installed):**

1. Install: `npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom`
2. Create `vitest.config.ts` with `environment: 'jsdom'`

**Component test template:**
```typescript
import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import XxxComponent from '../XxxComponent'

describe('XxxComponent', () => {
  it('renders without errors', () => {
    render(<XxxComponent />)
    expect(screen.getByRole('main')).toBeInTheDocument()
  })

  it('displays data when loaded', () => {
    render(<XxxComponent items={[{ id: 1, name: 'Test' }]} />)
    expect(screen.getByText('Test')).toBeInTheDocument()
  })

  it('calls onSubmit when form is submitted', async () => {
    const onSubmit = vi.fn()
    render(<XxxComponent onSubmit={onSubmit} />)
    await fireEvent.click(screen.getByRole('button', { name: /submit/i }))
    expect(onSubmit).toHaveBeenCalled()
  })
})
```

---

### Angular

Angular projects come with Karma/Jasmine by default. Generate `.spec.ts` files adjacent
to components.

**Component test template:**
```typescript
describe('XxxComponent', () => {
  let component: XxxComponent;
  let fixture: ComponentFixture<XxxComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [XxxComponent],
      imports: [/* required modules */],
      providers: [{ provide: XxxService, useValue: mockService }],
    }).compileComponents();

    fixture = TestBed.createComponent(XxxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

---

## API E2E

### Shell-based E2E Script

Generate `e2e/e2e-test.sh` that tests all discovered API endpoints.

**Discovery:**
1. Find all controller endpoints (URL patterns, HTTP methods, request/response shapes)
2. Determine the base URL (from docker-compose, application config, or default)
3. Identify auth requirements (login endpoint, token format)

**Script structure:**
```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8080/api/v1}"
PASS=0
FAIL=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check() {
  local description="$1"
  local expected_status="$2"
  local method="$3"
  local url="$4"
  shift 4
  local extra_args=("$@")

  TOTAL=$((TOTAL + 1))
  local response
  response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$url" \
    -H "Content-Type: application/json" \
    "${extra_args[@]}" 2>/dev/null)

  local status_code
  status_code=$(echo "$response" | tail -n1)
  local body
  body=$(echo "$response" | sed '$d')

  if [ "$status_code" = "$expected_status" ]; then
    echo -e "${GREEN}[PASS]${NC} $description (${status_code})"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}[FAIL]${NC} $description: expected ${expected_status}, got ${status_code}"
    echo "  Response: $(echo "$body" | head -c 200)"
    FAIL=$((FAIL + 1))
  fi
}

check_json_field() {
  local description="$1"
  local url="$2"
  local jq_filter="$3"
  local expected="$4"

  TOTAL=$((TOTAL + 1))
  local body
  body=$(curl -s "$BASE_URL$url" -H "Content-Type: application/json")
  local actual
  actual=$(echo "$body" | python3 -c "import sys,json; print(json.loads(sys.stdin.read())$jq_filter)" 2>/dev/null || echo "PARSE_ERROR")

  if [ "$actual" = "$expected" ]; then
    echo -e "${GREEN}[PASS]${NC} $description"
    PASS=$((PASS + 1))
  else
    echo -e "${RED}[FAIL]${NC} $description: expected '$expected', got '$actual'"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== API E2E Tests ==="
echo "Base URL: $BASE_URL"
echo ""

# --- Health Check ---
check "Health check" "200" "GET" "/actuator/health"

# --- Resource CRUD ---
# GET all
check "GET /resources" "200" "GET" "/resources"

# POST create (valid)
check "POST /resources (valid)" "201" "POST" "/resources" \
  -d '{"name":"test-item","description":"test"}'

# POST create (invalid - missing required field)
check "POST /resources (missing name)" "400" "POST" "/resources" \
  -d '{"description":"test"}'

# GET by ID
check "GET /resources/1" "200" "GET" "/resources/1"

# GET not found
check "GET /resources/99999" "404" "GET" "/resources/99999"

# PUT update
check "PUT /resources/1" "200" "PUT" "/resources/1" \
  -d '{"name":"updated","description":"updated"}'

# DELETE
check "DELETE /resources/1" "200" "DELETE" "/resources/1"

# --- Response Shape ---
check_json_field "Response has 'data' wrapper" "/resources" "['code']" "200"

# --- Summary ---
echo ""
echo "==========================="
echo "Total: $TOTAL  Pass: $PASS  Fail: $FAIL"
echo "==========================="

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
```

**Adaptation rules:**
- Replace `/resources` with actual endpoint paths from the project
- Add auth header if auth is required: `-H "Authorization: Bearer $TOKEN"`
- Match the response wrapper format to the project's actual API convention
- Use `snake_case` field names if the project uses Jackson SNAKE_CASE

**Coverage targets:**
- Every endpoint: at least one success case
- CRUD resources: create, read, update, delete + validation errors
- Auth-protected endpoints: with and without token
- Response shape: verify JSON structure matches frontend types

---

## Browser E2E

### Route-based Flow Generation

Generate browser test flows by discovering frontend routes.

**Discovery:**

For Vue Router:
```typescript
// Read router/index.ts → extract all route paths and component names
const routes = [
  { path: '/', component: 'HomeView' },
  { path: '/login', component: 'LoginView' },
  { path: '/dashboard', component: 'DashboardView' },
  { path: '/resources', component: 'ResourceListView' },
  { path: '/resources/:id', component: 'ResourceDetailView' },
]
```

For React Router / Next.js: scan pages directory or route config.

**Generated flows:**

Each flow is a sequence of dev-browser actions. Generate one flow per category:

**Flow 1: Page Accessibility**
```
For each route:
  1. Navigate to route URL
  2. client.getAISnapshot()
  3. Verify: no blank page, main content renders, no console errors
  4. Screenshot
```

**Flow 2: Authentication**
```
1. Navigate to login page
2. Fill in credentials (use test user if known, else note "needs test credentials")
3. Submit form
4. Verify: redirect to dashboard/home, user info displayed
5. Navigate to protected route → verify access
6. Logout → verify redirect to login
```

**Flow 3: Primary CRUD**
```
1. Navigate to resource list
2. Verify: table/list renders with data
3. Click "Create" / "Add"
4. Fill form fields
5. Submit → verify new item in list
6. Click item → verify detail view
7. Edit → verify changes saved
8. Delete → verify removed from list
```

**Flow 4: Error Handling**
```
1. Navigate to non-existent route → verify 404 page
2. Submit form with invalid data → verify validation messages
3. (If testable) Simulate API error → verify error state shown
```

**Flow 5: Navigation & Layout**
```
1. Verify sidebar/navbar links work
2. Verify responsive menu (if applicable)
3. Verify breadcrumbs or back navigation
4. Verify active route highlighting
```

**Implementation notes:**
- All flows use dev-browser's `client.getAISnapshot()` and `client.selectSnapshotRef()`
- Screenshot before and after each significant interaction
- Log console errors found during any flow
- If a flow requires login, do the auth flow first
- Mark flows that need test credentials as NEEDS_SETUP

---

## Naming Conventions for Generated Tests

| Layer | File Pattern | Example |
|-------|-------------|---------|
| Java Controller | `XxxControllerTest.java` | `DistrictControllerTest.java` |
| Java Service | `XxxServiceTest.java` | `EventServiceTest.java` |
| Go | `xxx_test.go` | `service_test.go` |
| Python | `test_xxx.py` | `test_districts.py` |
| Vue Component | `XxxComponent.test.ts` | `DistrictTable.test.ts` |
| Vue Composable | `useXxx.test.ts` | `useDistricts.test.ts` |
| Vue Store | `xxxStore.test.ts` | `districtStore.test.ts` |
| React Component | `XxxComponent.test.tsx` | `DistrictTable.test.tsx` |
| API E2E | `e2e/e2e-test.sh` | `e2e/e2e-test.sh` |

---

## Report Annotation

When tests are auto-generated, annotate the report:

```
Layer Results:
  Backend tests:       PASS (24/24) — AUTO-GENERATED 6 test classes
  Frontend unit tests: PASS (18/18) — AUTO-GENERATED with Vitest
  API E2E:             PASS (32/32) — AUTO-GENERATED e2e/e2e-test.sh
  Browser E2E:         PASS (5 flows) — 3 flows auto-generated from routes
```

This tells the user which tests existed before and which were created by the skill.
