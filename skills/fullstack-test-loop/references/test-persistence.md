# Test Persistence Reference

## Purpose

Avoid regenerating tests from scratch on every run. Detect existing tests, track coverage
against a scenario checklist, and only generate new tests for uncovered scenarios. Existing
tests are never deleted or modified (append-only).

---

## Algorithm: Incremental Test Update

### Step 1: Inventory Existing Tests

Scan for all test files:
- Unit tests: `frontend/tests/**/*.spec.ts` (excluding `e2e/`)
- E2E tests: `frontend/tests/e2e/**/*.spec.ts`

For each file, extract a manifest:

```json
{
  "file": "frontend/tests/e2e/dashboard.spec.ts",
  "describes": [
    {
      "name": "Dashboard Module",
      "its": [
        { "name": "DASH-01: Stat cards load", "status": "active" },
        { "name": "DASH-02: Overdue activities list", "status": "active" },
        { "name": "DASH-03: Project progress cards", "status": "skipped" }
      ]
    }
  ]
}
```

Status values:
- `active` — normal `it()` block
- `skipped` — wrapped in `it.skip()`
- `needs_review` — has `// NEEDS_HUMAN_REVIEW` comment

### Step 2: Load Scenario Checklist

Read the test-scenarios checklist (default: `frontend/tests/e2e/test-scenarios.md`,
or path specified by `--scenarios` flag).

Parse each line matching the pattern:
```
- [ ] XXXX-NN: description
- [x] XXXX-NN: description  (covered)
- [!] XXXX-NN: description  (needs review)
```

Extract: `{ id: "DASH-01", module: "Dashboard", description: "...", covered: false }`

### Step 3: Diff Coverage

For each scenario in the checklist:
1. Check if any `it()` block name contains the scenario ID (e.g., `DASH-01`)
2. Match is case-insensitive and checks for the ID anywhere in the `it` name
3. If found → scenario is covered
4. If not found → scenario is uncovered, needs generation

Build a diff report:
```
Coverage Report:
  Total scenarios:    80
  Covered:           45  (56%)
  Uncovered:         32  (40%)
  Needs review:       3  (4%)

  Uncovered by module:
    Auth:             2 scenarios (AUTH-05, AUTH-06)
    Financial:        5 scenarios (FIN-01 through FIN-05)
    ...
```

### Step 4: Generate Missing Tests Only

For each uncovered scenario:

**If the target spec file exists** (e.g., `dashboard.spec.ts` exists but is missing DASH-05):
1. Read the existing file
2. Find the last closing `})` of the outermost `describe` block
3. Insert new `it()` block(s) BEFORE that closing bracket
4. Preserve all existing code — do NOT modify or reformat existing lines

**If no file exists for that module** (e.g., no `salary.spec.ts`):
1. Create a new file with the module's `describe` wrapper
2. Add all uncovered scenarios for that module as `it()` blocks

**Test naming convention:**
- Always include the scenario ID in the `it()` name
- Format: `it('DASH-05: Empty state when no data', async () => { ... })`
- This enables the inventory step to match tests to scenarios

### Step 5: Handle Failing Existing Tests

When an existing test fails, classify the failure:

**Test infrastructure failure** (safe to fix):
- Import path changed (module moved/renamed)
- Mock setup incomplete (missing mock for new dependency)
- Test utility function signature changed
- → FIX these directly — they don't change test assertions

**Assertion failure due to interface change** (DO NOT auto-fix):
- Expected value doesn't match actual (e.g., API response shape changed)
- Component renders different structure than expected
- Store state has different shape
- → Wrap with `it.skip()` and add comment:

```typescript
// NEEDS_HUMAN_REVIEW: Interface changed — expected field 'name' but got 'display_name'
// See: src/api/project.ts:45 (response shape changed)
// Original assertion expected: { name: 'Test' }
// Actual response contains: { display_name: 'Test' }
it.skip('PROJ-01: List loads and displays projects', async () => {
  // ... original test code unchanged ...
})
```

**How to distinguish:**
1. Check `git diff` for recent changes to the production code referenced by the test
2. If production code changed → likely interface change → `it.skip()` + NEEDS_HUMAN_REVIEW
3. If production code unchanged → likely genuine bug → proceed to Phase 6 fix

---

## Append-Only Safeguard

**Critical constraint: Never delete or modify existing `it()` blocks.**

### What "append-only" means:

- Adding new `describe` blocks: ALLOWED
- Adding new `it` blocks inside existing `describe`: ALLOWED
- Adding `it.skip()` wrapper to existing test: ALLOWED (for NEEDS_HUMAN_REVIEW)
- Fixing imports at top of file: ALLOWED
- Modifying an existing `it` block's body: FORBIDDEN
- Deleting an existing `it` block: FORBIDDEN
- Changing an existing `it` block's name: FORBIDDEN
- Reordering existing blocks: FORBIDDEN

### Insertion point:

When appending to an existing file, find the insertion point:

```typescript
describe('Dashboard Module', () => {
  // ... existing tests ...

  it('DASH-04: Click project card', async () => { ... })

  // ← INSERT NEW TESTS HERE

})  // ← this is the outermost describe's closing bracket
```

### Duplicate prevention:

Before inserting a new `it()` block, check if the scenario ID already exists
in ANY `it()` name in the file. If it does, skip generation for that scenario.

---

## Coverage Marker Updates

After each run, update the test-scenarios.md checklist:

1. For each scenario that was successfully tested (test passed):
   - Change `- [ ]` to `- [x]`

2. For each scenario that was marked NEEDS_HUMAN_REVIEW:
   - Change `- [ ]` or `- [x]` to `- [!]`

3. Never change `- [x]` back to `- [ ]` unless the test file was deleted

---

## Manifest Cache

After each run, produce a JSON summary for faster future inventory:

**File:** `frontend/tests/.test-manifest.json` (gitignored, transient)

```json
{
  "generated_at": "2026-03-27T10:30:00Z",
  "unit_tests": 56,
  "e2e_tests": 15,
  "scenarios_total": 80,
  "scenarios_covered": 45,
  "scenarios_review": 3,
  "files": [
    {
      "path": "frontend/tests/e2e/dashboard.spec.ts",
      "scenarios": ["DASH-01", "DASH-02", "DASH-03", "DASH-04"],
      "last_modified": "2026-03-27T10:30:00Z"
    }
  ]
}
```

On subsequent runs:
1. Check if manifest exists and is newer than all spec files
2. If yes, use manifest instead of re-parsing all files (fast path)
3. If any spec file is newer than manifest, re-inventory that file only
