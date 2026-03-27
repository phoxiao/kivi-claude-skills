# Frontend Frameworks Reference

## Vue 3 + TypeScript

### Type Checking

```bash
# Standard typecheck
npx vue-tsc --noEmit

# Build mode (faster, uses project references)
npx vue-tsc -b --noEmit

# Check specific files (not commonly used)
npx vue-tsc --noEmit --project tsconfig.app.json
```

Note: `vue-tsc` wraps `tsc` with Vue SFC support. It understands `.vue` files.

### Common Type Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `TS2307: Cannot find module './Component.vue'` | Missing shims or volar config | Check `env.d.ts` has vue module declaration |
| `TS2339: Property 'x' does not exist on type` | Missing prop/field in interface | Update TypeScript interface to match API |
| `TS2345: Argument of type 'X' is not assignable to 'Y'` | Type mismatch | Fix the type at source (API response type or component prop) |
| `TS18048: 'x' is possibly 'undefined'` | Optional chaining needed | Add `?.` or null check |
| `TS7006: Parameter 'x' implicitly has an 'any' type` | Missing type annotation | Add explicit type |

### Unit Testing with Vitest

```bash
# Run all tests
npx vitest run

# Watch mode (not for CI)
npx vitest

# Run specific file
npx vitest run src/components/__tests__/MyComponent.test.ts

# With coverage
npx vitest run --coverage
```

### Vitest Output Parsing

```
 FAIL  src/components/__tests__/MyComponent.test.ts > MyComponent > renders correctly
AssertionError: expected '<div>Hello</div>' to contain 'Welcome'
 ❯ src/components/__tests__/MyComponent.test.ts:15:25
```

---

## React + TypeScript

### Type Checking

```bash
# Standard typecheck
npx tsc --noEmit

# With specific config
npx tsc --noEmit --project tsconfig.json
```

### Common Type Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `TS2786: 'Component' cannot be used as a JSX component` | Return type mismatch | Ensure component returns `JSX.Element` or `React.ReactNode` |
| `TS2322: Type 'X' is not assignable to type 'IntrinsicAttributes & Props'` | Wrong prop types | Fix prop interface |
| `TS2305: Module '"react"' has no exported member` | Wrong React version types | Update `@types/react` |

### Unit Testing

React projects typically use Jest or Vitest with `@testing-library/react`:

```bash
# Jest (Create React App)
npx react-scripts test --watchAll=false

# Vitest
npx vitest run

# Jest standalone
npx jest
```

---

## Angular

### Type Checking / Build

```bash
# Build (includes typecheck)
npx ng build --configuration=development

# Type check only (Angular 16+)
npx ng build --configuration=development --no-emit
```

### Unit Testing

```bash
# Run all tests (Karma + Jasmine by default)
npx ng test --watch=false --browsers=ChromeHeadless

# Specific file
npx ng test --include=**/my-component.spec.ts

# With coverage
npx ng test --code-coverage --watch=false --browsers=ChromeHeadless
```

### Common Angular Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `NullInjectorError: No provider for X` | Missing import in TestBed | Add provider or import module in TestBed.configureTestingModule |
| `Template parse errors` | Template binding error | Fix template syntax |
| `NG0100: ExpressionChangedAfterItHasBeenChecked` | Change detection issue | Use ChangeDetectorRef or restructure |

---

## Svelte

### Type Checking

```bash
# Svelte check
npx svelte-check

# With specific tsconfig
npx svelte-check --tsconfig ./tsconfig.json
```

### Unit Testing

```bash
# Vitest (most common for Svelte)
npx vitest run

# With Svelte Testing Library
npx vitest run
```

---

## Next.js

### Type Checking

```bash
# Uses tsc under the hood
npx tsc --noEmit

# Or Next.js built-in
npx next lint  # lint only
npx next build  # full build with typecheck
```

### Unit Testing

```bash
# Jest (default for Next.js)
npx jest

# Vitest
npx vitest run
```

---

## Nuxt

### Type Checking

```bash
# Nuxt typecheck
npx nuxi typecheck

# Or vue-tsc
npx vue-tsc --noEmit
```

### Unit Testing

```bash
# Vitest (recommended for Nuxt 3)
npx vitest run
```

---

## When No Test Framework Is Found

If `package.json` has no test framework in devDependencies and no test config files exist:

1. **Auto-generate**: Install the appropriate test framework and generate comprehensive tests
2. See `references/test-generation.md` § Frontend for framework selection and generation templates
3. **Still run type checking** if TypeScript is present — this catches many issues before tests
4. **Still run browser E2E** in Phase 5 — this validates the frontend visually

### Framework Selection Guide

| Frontend Framework | Recommended Test Framework | Install Command |
|---|---|---|
| Vue 3 (Vite) | Vitest + @vue/test-utils | `npm i -D vitest @vue/test-utils @vitejs/plugin-vue jsdom` |
| React (Vite) | Vitest + @testing-library/react | `npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom` |
| React (CRA) | Jest (built-in) | Already included |
| Angular | Karma + Jasmine (built-in) | Already included via `ng test` |
| Next.js | Jest + @testing-library/react | `npm i -D jest @testing-library/react @testing-library/jest-dom` |
| Nuxt 3 | Vitest + @vue/test-utils | `npm i -D vitest @vue/test-utils @nuxt/test-utils jsdom` |
| Svelte | Vitest + @testing-library/svelte | `npm i -D vitest @testing-library/svelte jsdom` |
