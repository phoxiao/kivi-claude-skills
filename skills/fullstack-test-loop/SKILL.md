---
name: fullstack-test-loop
description: |
  Fully automated test-fix-retest loop for full-stack projects. Auto-detects tech stack
  (Java/Spring Boot, Go, Python, Rust, Node.js + Vue/React/Angular/Next.js/Svelte),
  runs tests in pyramid order (compile → backend unit → frontend typecheck → frontend unit →
  API E2E → browser E2E), analyzes failures with causal-chain debugging (symptom → proximate
  cause → root cause), clusters related failures, auto-fixes code, and iterates until all
  pass or max iterations reached. Also identifies missing test coverage gaps and auto-generates
  tests when none exist for a phase. Use this skill whenever the user wants to run tests,
  fix failing tests, or verify code changes haven't broken anything — including: "run tests",
  "run all tests", "make tests pass", "fix failing tests", "test loop", "fullstack test",
  "测试", "跑测试", "跑一下所有测试", "测试全挂了帮我修", "帮我修测试", or after code
  changes touching both frontend and backend (e.g., API contract changes, field naming
  migrations, new service dependencies). Proactively suggest when the user finishes
  implementing a feature that spans multiple layers, or when they mention NullPointerException
  in tests, type errors after refactoring, or cross-module contract mismatches.
---

# /fullstack-test-loop — Detect, Run, Analyze, Fix, Repeat

## Purpose

A fully automated closed-loop test runner for any full-stack project. It discovers your
tech stack, runs every applicable test layer from fast to slow, diagnoses failures by
tracing causal chains (not surface symptoms), fixes code, and re-runs until green — or
until it knows it can't fix something and needs your input.

## When This Skill Activates

- User asks to run tests or make tests pass
- User finishes a feature and wants verification
- After code changes spanning frontend + backend
- User says `/fullstack-test-loop` directly

## Subcommands

```
/fullstack-test-loop                    # Run all layers, auto-detect everything
/fullstack-test-loop backend            # Backend only (compile + unit/integration)
/fullstack-test-loop frontend           # Frontend only (typecheck + unit)
/fullstack-test-loop e2e                # E2E only (API + browser)
/fullstack-test-loop browser            # Browser E2E only (dev-browser)
/fullstack-test-loop --no-fix           # Run + analyze only, no auto-fix
/fullstack-test-loop --skip-fix         # Alias for --no-fix (run all phases, report only)
/fullstack-test-loop --max-iterations 3 # Override max iterations (default: 5)
/fullstack-test-loop --force-all        # Run all layers even if earlier ones fail
/fullstack-test-loop --scenarios <file> # Use specific test-scenarios checklist file
```

---

## Phase 0: Stack Detection

Before running anything, understand what this project contains. Read `references/stack-detection.md`
for the full detection logic.

**Quick summary:**

1. Scan project root AND common subdirectories (`backend/`, `frontend/`, `server/`, `client/`, `app/`, `web/`, `api/`, `src/`)
2. Identify backend framework from build files (pom.xml, build.gradle, go.mod, Cargo.toml, pyproject.toml, etc.)
3. Identify frontend framework from package.json dependencies (vue, react, angular, svelte, next, nuxt)
4. Identify E2E setup (shell scripts in e2e/, cypress.config.*, playwright.config.*, docker-compose.e2e.yml)
5. Check for existing test configuration (pytest.ini, vitest.config.*, jest.config.*, .mocharc.*)

Output a mental StackProfile before proceeding:

```
Stack Detection:
  Backend:   Java/Maven (Spring Boot) @ backend/
  Frontend:  Vue 3 + TypeScript @ frontend/
  E2E:       Shell script @ e2e/e2e-test.sh
  Test DB:   H2 in-memory (application-test.yml)
  Services:  docker-compose.yml (postgres, minio)

Test Coverage Gaps:
  Backend tests:      FOUND (src/test/java/ — 11 test classes)
  Frontend unit tests: MISSING — will auto-generate with Vitest
  API E2E:            FOUND (e2e/e2e-test.sh — 47 assertions)
  Browser E2E:        MISSING — will auto-generate flows from routes

Test Persistence:
  Scenario checklist:   {FOUND|MISSING} (frontend/tests/e2e/test-scenarios.md — N scenarios)
  E2E test files:       {FOUND|MISSING} (frontend/tests/e2e/ — N spec files)
  Screenshot baselines: {FOUND|MISSING} (frontend/tests/e2e/screenshots/baseline/ — N images)
```

If detection is ambiguous (e.g., multiple backends), briefly note what was found and pick
the most likely primary stack. If truly unclear, ask the user.

**Test Coverage Gap Analysis:** For each phase, check whether tests/scripts exist. If a phase
has NO tests, flag it as a gap and prepare for auto-generation in that phase. Read
`references/test-generation.md` for generation templates per framework.

---

## Phase 1: Compilation Check (Fast Fail)

The cheapest way to catch errors. If it doesn't compile, nothing else matters.

**Run in order:**

1. **Backend compile** — see `references/backend-frameworks.md` for per-framework commands
   - Java/Maven: `mvn compile -q -f <path>/pom.xml`
   - Java/Gradle: `cd <path> && ./gradlew compileJava -q`
   - Go: `cd <path> && go build ./...`
   - Rust: `cd <path> && cargo check`
   - Python: `cd <path> && python -m py_compile <changed_files>` (or skip — Python is interpreted)

2. **Frontend typecheck** — see `references/frontend-frameworks.md`
   - Vue + TypeScript: `cd <path> && npx vue-tsc -b --noEmit` (or `npx vue-tsc --noEmit`)
   - React + TypeScript: `cd <path> && npx tsc --noEmit`
   - Angular: `cd <path> && npx ng build --configuration=development`
   - No TypeScript: skip this step

**On failure:** Go directly to Phase 6 (Fix), then re-run Phase 1. Do not proceed to Phase 2
until compilation passes (unless `--force-all`).

---

## Phase 2: Backend Tests

Run the backend's test suite. Read `references/backend-frameworks.md` for framework-specific
commands, output parsing, and common failure patterns.

**First: Check if backend tests exist.**

Scan the standard test directories for the detected framework:
- Java: `src/test/java/` or `<module>/src/test/java/`
- Go: `*_test.go` files alongside source
- Rust: `#[cfg(test)]` modules or `tests/` directory
- Python: `tests/`, `test_*.py`, `*_test.py`

**If NO backend tests exist → Auto-generate.** Read `references/test-generation.md` § Backend.

1. Discover all public service classes, controllers/handlers, and repository interfaces
2. Generate one test class per service/controller with tests covering:
   - All public methods with happy-path and key error-path cases
   - Boundary conditions (null inputs, empty collections, invalid IDs)
   - For controllers: request/response shape, status codes, validation errors
3. Place generated tests in the standard test directory for the framework
4. Run the generated tests immediately — failures in generated tests need fixing too

**Commands by framework:**

| Framework | Run All | Run Single Class | Verbose |
|-----------|---------|-------------------|---------|
| Maven | `mvn test` | `mvn test -Dtest=ClassName` | `mvn test -X` |
| Gradle | `./gradlew test` | `./gradlew test --tests ClassName` | `./gradlew test --info` |
| Go | `go test ./...` | `go test ./path/to/package -run TestName` | `go test -v ./...` |
| Rust | `cargo test` | `cargo test test_name` | `cargo test -- --nocapture` |
| Python | `pytest` | `pytest path/to/test.py::TestClass` | `pytest -v` |

**On failure:** Capture full output, proceed to Phase 6 (Analyze & Fix).

**On >20 failures in a single run:** Stop and report — this is likely a systemic issue
(wrong config, missing dependency, broken migration), not individual test bugs.

---

## Phase 3: Frontend Unit Tests

**First: Check if a test framework and tests exist.**

**Detection:**
- Check package.json for `vitest`, `jest`, `@angular/cli`, `karma` in devDependencies
- Check for config files: `vitest.config.*`, `jest.config.*`, `.mocharc.*`
- Check package.json scripts for `"test"` entry
- Check for test files: `**/*.test.{ts,tsx,js}`, `**/*.spec.{ts,tsx,js}`, `**/__tests__/**`

**If test framework exists AND tests exist → Run them:**

| Framework | Command |
|-----------|---------|
| Vitest | `npx vitest run` |
| Jest | `npx jest` |
| Angular | `npx ng test --watch=false --browsers=ChromeHeadless` |
| Karma | `npx karma start --single-run` |

**If NO test framework OR NO test files → Auto-generate.** Read `references/test-generation.md` § Frontend.

1. Install the appropriate test framework if missing (Vitest for Vue/Svelte/React-Vite, Jest for CRA/Next):
   - `npm install -D vitest @vue/test-utils jsdom` (Vue)
   - `npm install -D vitest @testing-library/react jsdom` (React-Vite)
   - Create a minimal vitest/jest config file
2. Discover all components, composables/hooks, stores, and utility modules
3. Generate comprehensive test files covering:
   - Component rendering (mount, props, slots, events)
   - Store/state logic (actions, getters, mutations)
   - Composables/hooks (input/output, reactivity, edge cases)
   - Utility functions (pure logic, boundary conditions)
4. Place tests adjacent to source files (`Component.test.ts` next to `Component.vue`)
5. Run the generated tests and enter Phase 6 if any fail

---

## Phase 4: API E2E Tests

These test the running application's API endpoints. They require services to be up.

**First: Check if E2E tests exist.**

Scan for: `e2e/*.sh`, `e2e/*.py`, `cypress.config.*`, `playwright.config.*`,
`docker-compose.e2e.yml`, package.json `"test:e2e"` script, `*.postman_collection.json`.

**If NO E2E tests exist → Auto-generate.** Read `references/test-generation.md` § API E2E.

1. Discover all API endpoints by scanning:
   - Backend controller/handler annotations (`@GetMapping`, `@PostMapping`, `router.GET`, etc.)
   - OpenAPI/Swagger spec if present (`openapi.yaml`, `swagger.json`)
   - Existing frontend API call sites (axios/fetch calls)
2. Generate a shell-based E2E test script (`e2e/e2e-test.sh`) covering:
   - Health check endpoint
   - All CRUD operations per resource (create, read, update, delete)
   - Authentication flow (login, access protected endpoint, logout)
   - Error cases (invalid input → 400, missing auth → 401, not found → 404)
   - Response shape validation (check JSON structure matches expected contract)
3. Make the script executable and configurable via `BASE_URL` parameter

**Pre-check: Are services running?**

1. Check if the backend is already accessible (curl health endpoint)
2. If not, check for docker-compose.yml or docker-compose.e2e.yml
3. If docker-compose exists, start services: `docker compose up -d` and wait for health
4. If no docker-compose, check if there's a dev start script, and note that services need
   to be running manually

**Run E2E tests:**

See `references/e2e-frameworks.md` for details.

- Shell scripts: `bash e2e/e2e-test.sh [BASE_URL]`
- Docker E2E: `docker compose -f docker-compose.e2e.yml up --abort-on-container-exit`
- Cypress: `npx cypress run`
- Custom scripts: detect from package.json `"test:e2e"` or `"e2e"` scripts

**On failure:** Capture output, parse PASS/FAIL counts, proceed to Phase 6.

---

## Phase 5: Browser E2E (Final Gate)

Phase 5 runs independently of Phases 2-4. It is ONLY blocked by Phase 1 failure
(if the app doesn't compile, browser testing is meaningless). Unit test failures
(Phase 3) do NOT block browser E2E — they test different concerns.

When `browser` subcommand is used, skip Phases 1-4 entirely.
When `--force-all` is used, all phases run regardless of prior failures.

**Use dev-browser — never Playwright directly.**

**First: Check if browser test flows are defined.**

If no browser test plan exists (no prior testloop runs, no cypress specs, no defined flows):

→ **Auto-generate browser test flows** from route discovery. Read `references/test-generation.md` § Browser E2E.

1. Discover all frontend routes from:
   - Vue Router config (`router/index.ts`)
   - React Router config, Next.js pages/app directory
   - Angular routing modules
2. For each route, generate a test flow:
   - Navigate to the route
   - Verify the page renders without errors
   - Interact with primary interactive elements (forms, buttons, links)
   - Verify data loads (tables, lists, cards are not empty)
3. Generate additional flows for:
   - Authentication (login → protected page → logout)
   - CRUD operations on the primary resource
   - Error handling (invalid input, network errors)

**Execute flows using dev-browser:**

1. **Open** the app URL with dev-browser
2. **Snapshot** the page: `client.getAISnapshot()`
3. **Test critical flows** in order:
   - Navigation: links, menus, routing
   - Data display: tables, lists, cards load correctly
   - Forms: input, validation, submission
   - Error states: handle 401/403/404/500 gracefully
4. **Screenshot** before and after significant interactions
5. **Log** any console errors or failed network requests

**Determining the app URL:**
- Check docker-compose for frontend port mapping (commonly 5173, 3000, 8080)
- Check vite.config.* or package.json dev script for port
- Default: `http://localhost:5173` (Vite) or `http://localhost:3000` (CRA/Next)

**On failure:** Screenshot the issue, trace to source code, apply fix, re-run this phase.

---

## Phase 6: Analyze & Fix

This is the core intelligence of the skill. It runs whenever any phase reports failures.

### Step 1: Parse Failures

Extract structured data from test output. See `references/failure-analysis.md` for
per-framework parsing patterns.

For each failure, extract:
- **Test name** (class + method)
- **Error type** (compilation, assertion, exception, timeout)
- **Error message** (the specific assertion or exception)
- **Stack trace** (file path + line number)
- **Category** (test setup, business logic, API contract, config, data)

### Step 2: Cluster by Root Cause

Many test failures share a single root cause. Before fixing anything:

1. Group failures that share the same deepest stack frame
2. Group by error category (e.g., all NullPointerException in the same service)
3. If >3 tests fail in the same module, that module is likely the root cause

### Step 3: Causal Chain Analysis

For EACH cluster, trace the full chain. This is critical — never fix surface symptoms.

```
SYMPTOM:     5 tests fail with "expected 200 but got 403"
PROXIMATE:   SecurityContext.getCurrentUser() returns null in test environment
ROOT CAUSE:  New test class missing @ActiveProfiles("test") annotation
FIX:         Add @ActiveProfiles("test") to the test class
```

Read `references/fix-strategies.md` for the fix decision tree.

### Step 3.5: Vue SFC Fix Boundary

**Before fixing any `.vue` file**, read `references/vue-fix-safety.md`.
- Only `<script>` / `<script setup>` modifications are allowed
- `<template>` and `<style>` changes are FORBIDDEN → mark as `NEEDS_HUMAN_REVIEW`
- After any `.vue` script fix, run visual regression check (`references/visual-regression.md`)

### Step 4: Apply Fixes

Priority: fix the root cause that resolves the most failures first.

**Decision tree:**

```
Is the failure in TEST code (setup, mocks, assertions)?
  → Fix test code (mock setup, fixture update, assertion correction)

Is it a COMPILATION / TYPE error?
  → Fix the source type/signature, trace which change broke the contract

Is it a RUNTIME behavior bug (wrong result, NPE, 500 error)?
  → Read data flow: producer → consumer. Apply minimal fix at root cause.

Is it ENVIRONMENT / CONFIG (DB connection, missing env var, wrong port)?
  → Fix test config (application-test.yml, .env.test, docker-compose)

None of the above?
  → Flag as NEEDS_HUMAN_INPUT, explain what you found
```

**Constraints:**
- Minimal diff — fewest files, fewest lines changed
- Never refactor while fixing tests (separate concerns)
- After 3 failed attempts to fix the same failure, stop and explain the situation

### Step 5: Validate Fix

After fixing, re-run ONLY the affected test layer (not the full pyramid) to quickly
verify the fix works. If it passes, continue to the next failure cluster. If it fails,
try a different approach or escalate.

**Visual Regression Check:** If the fix touched any `.vue` file's `<script>` block,
read `references/visual-regression.md` and run the visual regression workflow.
If regression detected, revert the fix before marking it as failed.

---

## Test Persistence

Before generating any test (Phase 3 or Phase 5), read `references/test-persistence.md`.

Key rules:
1. Check if tests already exist before generating
2. Only append new scenarios, never modify/delete existing tests
3. Use scenario IDs from test-scenarios.md to track coverage (e.g., `DASH-01`, `AUTH-03`)
4. Existing test failures due to interface changes → `it.skip()` + `NEEDS_HUMAN_REVIEW`
5. Update test-scenarios.md coverage markers after each run: `[ ]` → `[x]`

---

## Loop Control

```
iteration = 0
max_iterations = 5  (or user override)
blocked_failures = []

LOOP:
  iteration += 1

  IF subcommand == "browser":
    Run Phase 5 only
  ELIF subcommand == "backend":
    Run Phase 1 (backend compile) + Phase 2
  ELIF subcommand == "frontend":
    Run Phase 1 (frontend typecheck) + Phase 3
  ELIF subcommand == "e2e":
    Run Phase 4 + Phase 5
  ELSE:
    Run Phase 1 (compile)
    IF Phase 1 fails AND NOT --force-all:
      Run Phase 6, continue loop

    Run Phase 2 (backend) — blocked only by backend compile failure
    Run Phase 3 (frontend unit) — blocked only by frontend typecheck failure
    Run Phase 4 (API E2E) — blocked only by backend compile failure
    Run Phase 5 (browser E2E) — blocked only by frontend typecheck failure

    Note: Phases 2-5 are INDEPENDENT of each other.
    Phase 3 failure does NOT block Phase 5.

  IF all pass:
    → Print SUCCESS report, exit loop

  IF iteration >= max_iterations:
    → Print TIMEOUT report with remaining failures, exit loop

  IF a failure persists unchanged across 3 consecutive iterations:
    → Add to blocked_failures, skip it in future iterations

  IF a fix introduces NEW failures (regression):
    → Revert the fix, add original failure to blocked_failures

  IF any single phase has >20 failures:
    → Stop that phase, report as SYSTEMIC issue

  ELSE:
    → Run Phase 6 (Analyze & Fix), then continue loop
```

---

## Output Report

At the end of the loop (success or timeout), produce this report:

```
TEST LOOP REPORT
════════════════════════════════════════════
Stack:      Java/Maven + Vue 3/TypeScript
Iterations: 3/5
Status:     DONE ✓

Layer Results:
  Backend compile:     PASS
  Backend tests:       PASS (11/11) — fixed 2 in iteration 1
  Frontend typecheck:  PASS — fixed 1 in iteration 2
  Frontend unit tests: PASS (24/24) — AUTO-GENERATED with Vitest
  API E2E:             PASS (47/47)
  Browser E2E:         PASS (5 flows verified) — 2 flows auto-generated

Fixes Applied:
  1. fix(test): add @ActiveProfiles("test") to EventServiceTest
  2. fix(service): null check in AggregationService.calculate()
  3. fix(frontend): update DistrictDTO type to match API snake_case

Blocked: (none)
════════════════════════════════════════════
```

Status values:
- **DONE** — all applicable tests pass
- **DONE_WITH_CONCERNS** — tests pass but some were skipped or had warnings
- **BLOCKED** — some failures could not be auto-fixed (listed in Blocked section)
- **TIMEOUT** — max iterations reached with remaining failures

---

## Cross-Module Contract Checking

When failures span both frontend and backend, check these common contract issues:

1. **Field naming**: Backend returns `district_name` but frontend expects `districtName`?
   Check serialization config (Jackson, Gson) and TypeScript interfaces.

2. **Response shape**: API wraps in `{code, message, data}` but frontend reads raw response?
   Check Axios interceptors and API response types.

3. **Numeric precision**: Backend sends `"123.4567"` (string) but frontend parses as number?
   Check DTO types and JSON parsing.

4. **Date formats**: Backend sends ISO 8601 but frontend expects timestamp?
   Check serialization and dayjs/moment config.

5. **Query parameter binding**: Frontend sends `group_id` but backend controller uses
   `@RequestParam Long groupId` without explicit name? Jackson SNAKE_CASE does NOT affect
   `@RequestParam` — Spring binds from the literal HTTP parameter name. Verify all
   `@RequestParam` have explicit `value = "snake_case"` when the API convention is snake_case.

5. **Enum values**: Backend enum changes but frontend still uses old values?
   Check both enum definitions.

---

## Reference Files

These provide framework-specific details. Read them when you need the specifics:

| File | When to read |
|------|-------------|
| `references/stack-detection.md` | Phase 0 — need detection logic for an unfamiliar project structure |
| `references/backend-frameworks.md` | Phases 1-2 — need compile/test commands or failure parsing for a specific backend |
| `references/frontend-frameworks.md` | Phases 1, 3 — need typecheck/test commands for a specific frontend |
| `references/e2e-frameworks.md` | Phase 4 — need to run or parse E2E test output |
| `references/failure-analysis.md` | Phase 6 Step 1 — need to parse test output from a specific framework |
| `references/fix-strategies.md` | Phase 6 Step 4 — need guidance on fix patterns for specific failure types |
| `references/vue-fix-safety.md` | Phase 6 Step 3.5 — Vue SFC fix boundary rules (script only, no template/style) |
| `references/visual-regression.md` | Phase 6 Step 5 — screenshot comparison after .vue fixes |
| `references/test-persistence.md` | Phases 3, 5 — incremental test generation, append-only updates |
| `references/test-generation.md` | Phases 2-5 — need to auto-generate tests when none exist for a phase |

---

## Important Notes

- **dev-browser for browser testing**: Always use dev-browser, never Playwright directly.
  Use `client.getAISnapshot()` for page state, `client.selectSnapshotRef()` for interaction.
  In `page.evaluate()`, use plain JavaScript (no TypeScript annotations).

- **Debugging protocol**: Never fix the first match. Always trace: symptom → proximate cause
  → root cause. For cross-module bugs, check the data contract between producer and consumer.

- **Minimal changes**: Each fix should be the smallest change that resolves the failure.
  Do not refactor, add comments, or clean up adjacent code during test fixes.

- **Service lifecycle**: If the skill starts Docker services for E2E tests, it should also
  offer to stop them when done (but not force-stop — the user might want them running).
