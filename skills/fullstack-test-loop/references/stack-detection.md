# Stack Detection Reference

## Detection Strategy

Scan the project root and common subdirectories to build a StackProfile. Check these
directories: `.`, `backend/`, `frontend/`, `server/`, `client/`, `app/`, `web/`, `api/`,
`src/`, `services/`.

## Backend Detection

| Marker File | Framework | Build Tool | Test Command |
|-------------|-----------|------------|--------------|
| `pom.xml` | Java (check for spring-boot-starter) | Maven | `mvn test` |
| `build.gradle` or `build.gradle.kts` | Java/Kotlin | Gradle | `./gradlew test` |
| `go.mod` | Go | go | `go test ./...` |
| `Cargo.toml` | Rust | Cargo | `cargo test` |
| `pyproject.toml` | Python (check for django/flask/fastapi) | pip/poetry | `pytest` |
| `requirements.txt` | Python | pip | `pytest` |
| `Gemfile` | Ruby (check for rails) | Bundler | `bundle exec rspec` |
| `mix.exs` | Elixir | Mix | `mix test` |
| `composer.json` | PHP (check for laravel/symfony) | Composer | `./vendor/bin/phpunit` |
| `Package.swift` | Swift | SPM | `swift test` |
| `*.csproj` or `*.sln` | C#/.NET | dotnet | `dotnet test` |

### Maven Wrapper Detection

If `mvnw` or `mvnw.cmd` exists, use `./mvnw` instead of `mvn`. Same for Gradle: use
`./gradlew` if the wrapper exists.

### Spring Boot Detection

In a Maven project, check if pom.xml contains `spring-boot-starter`. This tells you:
- Test profile: look for `application-test.yml` or `application-test.properties`
- Test database: check for H2, HSQLDB in test scope dependencies
- Security testing: check for `spring-security-test` dependency

### Python Framework Detection

```
pyproject.toml contains "django" → Django (manage.py test or pytest)
pyproject.toml contains "fastapi" → FastAPI (pytest with httpx)
pyproject.toml contains "flask" → Flask (pytest)
requirements.txt contains "pytest" → pytest available
```

## Frontend Detection

Read `package.json` (or `frontend/package.json`, etc.) and check dependencies:

| Dependency Key | Framework | TypeCheck Command |
|----------------|-----------|-------------------|
| `vue` | Vue | `vue-tsc --noEmit` or `vue-tsc -b` |
| `react` or `react-dom` | React | `tsc --noEmit` |
| `@angular/core` | Angular | `ng build` |
| `svelte` | Svelte | `svelte-check` |
| `next` | Next.js (React) | `tsc --noEmit` |
| `nuxt` | Nuxt (Vue) | `nuxi typecheck` |
| `solid-js` | Solid | `tsc --noEmit` |

### Frontend Test Framework Detection

Check `devDependencies` in package.json:

| Dependency | Test Runner | Command |
|------------|-------------|---------|
| `vitest` | Vitest | `npx vitest run` |
| `jest` | Jest | `npx jest` |
| `@testing-library/*` | (works with vitest/jest) | (check which runner) |
| `cypress` | Cypress | `npx cypress run` |
| `@playwright/test` | Playwright | `npx playwright test` |
| `karma` | Karma | `npx karma start --single-run` |

Also check package.json `scripts` for:
- `"test"` → run with `npm test`
- `"test:unit"` → unit tests
- `"test:e2e"` → E2E tests

## E2E Detection

| Pattern | Type | Runner |
|---------|------|--------|
| `e2e/*.sh` or `test/*.sh` | Shell API tests | `bash <script>` |
| `cypress.config.*` | Cypress | `npx cypress run` |
| `playwright.config.*` | Playwright | `npx playwright test` |
| `docker-compose.e2e.yml` | Docker E2E | `docker compose -f docker-compose.e2e.yml` |
| `*.http` or `*.rest` | HTTP files | IDE-dependent (informational only) |
| `k6.js` or `*.k6.js` | k6 load testing | `k6 run <script>` |

## Monorepo Patterns

If the root has these, it's a monorepo:

| Pattern | Tool |
|---------|------|
| `pnpm-workspace.yaml` | pnpm workspaces |
| `lerna.json` | Lerna |
| `nx.json` | Nx |
| `turbo.json` | Turborepo |
| Root package.json with `"workspaces"` | npm/yarn workspaces |

For monorepos, scan each workspace package for its own test setup.

## Test Database Detection

| Marker | Database |
|--------|----------|
| H2 in test dependencies (pom.xml/build.gradle) | H2 in-memory |
| `application-test.yml` with `hsqldb` | HSQLDB |
| `conftest.py` with SQLite | SQLite test DB |
| `docker-compose.test.yml` with postgres | Testcontainers/Docker PostgreSQL |
| `testcontainers` in dependencies | Testcontainers (dynamic) |

## Output Format

After detection, mentally construct:

```
StackProfile:
  project_root: /path/to/project
  backend:
    framework: spring-boot
    build_tool: maven (wrapper: true)
    path: backend/
    test_command: ./mvnw test
    test_config: backend/src/test/resources/application-test.yml
    test_db: h2-inmemory
  frontend:
    framework: vue3
    typescript: true
    path: frontend/
    typecheck_command: npx vue-tsc --noEmit
    test_framework: none
    test_command: null
  e2e:
    type: shell-script
    path: e2e/e2e-test.sh
    requires_services: true
    docker_compose: docker-compose.yml
  services:
    - postgres (port 5432)
    - minio (port 9000)
```
