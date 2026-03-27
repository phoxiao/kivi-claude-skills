# E2E Test Frameworks Reference

## Shell-Based API Tests

Common in projects that use curl/httpie to test REST APIs.

### Detection

Look for:
- `e2e/*.sh`, `test/*.sh`, `tests/*.sh`
- Scripts containing `curl` commands with API endpoints
- Scripts that check HTTP status codes

### Running

```bash
# Typical invocation
bash e2e/e2e-test.sh

# With custom base URL
bash e2e/e2e-test.sh http://localhost:8080/api/v1

# Make executable first if needed
chmod +x e2e/e2e-test.sh
```

### Output Parsing

Shell E2E scripts typically output colored PASS/FAIL results:

```
[PASS] Health check: 200 OK
[FAIL] POST /registration: expected 201, got 400
  Response: {"code":400,"message":"Validation error: name is required"}
[PASS] GET /districts: returned 5 items
```

Extract:
- Status: PASS or FAIL
- Endpoint: HTTP method + path
- Expected vs actual: status code or response body
- Error detail: response body on failure

### Common Failure Patterns

| Pattern | Cause | Fix |
|---------|-------|-----|
| `Connection refused` | Backend not running | Start services first |
| `401 Unauthorized` | Missing or expired auth token | Check test token format |
| `404 Not Found` | Endpoint URL changed | Update test URL or route |
| `500 Internal Server Error` | Backend bug | Check backend logs |
| `Timeout` | Slow response or hung service | Check service health, increase timeout |
| JSON parse error | Response format changed | Update test assertion |

### Service Readiness

Before running shell E2E tests, ensure services are up:

```bash
# Wait for backend health endpoint
for i in $(seq 1 30); do
  curl -sf http://localhost:8080/actuator/health && break
  sleep 2
done

# Wait for frontend dev server
for i in $(seq 1 30); do
  curl -sf http://localhost:5173 && break
  sleep 2
done
```

---

## Docker Compose E2E

### Detection

Look for:
- `docker-compose.e2e.yml` or `docker-compose.test.yml`
- These typically define isolated instances with different ports

### Running

```bash
# Start E2E environment
docker compose -f docker-compose.e2e.yml up -d

# Wait for health checks
docker compose -f docker-compose.e2e.yml ps  # check all services are "healthy"

# Run E2E tests against isolated environment
bash e2e/e2e-test.sh http://localhost:18080/api/v1

# Tear down
docker compose -f docker-compose.e2e.yml down -v
```

### Full Lifecycle

```bash
# One-shot: start, wait, test, stop
docker compose -f docker-compose.e2e.yml up --abort-on-container-exit --exit-code-from e2e-runner
```

This works if the e2e test is defined as a service in docker-compose.e2e.yml.

---

## Cypress

### Detection

Look for: `cypress.config.ts`, `cypress.config.js`, `cypress/` directory

### Running

```bash
# Headless (CI mode)
npx cypress run

# Specific spec file
npx cypress run --spec "cypress/e2e/login.cy.ts"

# With specific browser
npx cypress run --browser chrome

# Interactive (not for automated loop)
npx cypress open
```

### Output Parsing

```
  Running:  login.cy.ts
    Login Flow
      ✓ should display login form (234ms)
      ✗ should login with valid credentials (1523ms)
        AssertionError: Timed out retrying: expected '[data-cy=dashboard]' to exist
```

### Common Failures

| Pattern | Cause | Fix |
|---------|-------|-----|
| `Timed out retrying` | Element not found in time | Check selector, increase timeout, or fix rendering |
| `cy.visit() failed: 404` | Wrong URL or route missing | Fix URL or add route |
| `CORS error` | Cross-origin request blocked | Configure proxy or CORS |

---

## HTTP Files (.http / .rest)

### Detection

Look for: `*.http`, `*.rest` files (used by VS Code REST Client, IntelliJ HTTP Client)

### Note

These are not directly runnable from CLI in most cases. They serve as documentation
and manual testing aids. If found, note them in the StackProfile but don't try to
execute them automatically.

For IntelliJ HTTP Client CLI:
```bash
# If ijhttp is available
ijhttp --env-file http-client.env.json requests.http
```

---

## k6 Load Tests

### Detection

Look for: `k6.js`, `*.k6.js`, `k6/` directory, or `import http from 'k6/http'` in JS files

### Running

```bash
# Run load test
k6 run e2e/load-test.k6.js

# With specific VUs and duration
k6 run --vus 10 --duration 30s e2e/load-test.k6.js
```

Note: Load tests are expensive and slow. Only include in the test loop if the user
explicitly requests it or if the test file is specifically named in the scope.

---

## Postman / Newman

### Detection

Look for: `*.postman_collection.json`, `newman/` directory

### Running

```bash
# Run with Newman
npx newman run collection.json --environment env.json
```

---

## Service Startup Patterns

When E2E tests need running services, use this detection order:

1. **Already running?** Try `curl -sf http://localhost:<port>/health` or similar
2. **Docker Compose?** `docker compose up -d` and wait for health checks
3. **Start scripts?** Check package.json for `"start"`, `"dev"`, `"serve"` scripts
4. **Manual?** Tell the user: "E2E tests require running services. Please start them and re-run."

### Port Detection

Check these sources for port numbers:
- `docker-compose.yml` port mappings
- `application.yml` / `application.properties` for `server.port`
- `vite.config.*` for frontend dev server port
- `.env` files for PORT variables
- package.json scripts for `--port` flags
