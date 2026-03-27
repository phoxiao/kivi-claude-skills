# Visual Regression Detection Reference

## Purpose

Prevent auto-fixes from breaking UI. After any source fix to a `.vue` file's `<script>` block,
capture a screenshot of the affected page and compare against a baseline. If visual regression
is detected, revert the fix immediately.

This is the last line of defense — it catches regressions that pass unit tests but break
the visual appearance (e.g., a script change that causes a computed property to return wrong
data, leaving a page blank or with missing sections).

---

## Baseline Management

### Storage Layout

```
frontend/tests/e2e/screenshots/
  baseline/          # Version-controlled baseline PNGs (git tracked)
  current/           # Current-run screenshots (gitignored, transient)
  diff/              # Diff images for debugging (gitignored, transient)
```

### Naming Convention

```
{route-path-slug}--{viewport}.png
```

Examples:
- `dashboard--desktop.png`
- `login--desktop.png`
- `projects--desktop.png`
- `projects-id--desktop.png`
- `my-work--desktop.png`
- `admin--desktop.png`

Route slug rules:
- Replace `/` with `-`
- Replace `:param` with `id`
- Remove leading `-`
- Examples: `/projects/:id` → `projects-id`, `/salary/summary` → `salary-summary`

Default viewport: `desktop` (1280x800)

### Gitignore

Add to `frontend/.gitignore`:
```
tests/e2e/screenshots/current/
tests/e2e/screenshots/diff/
tests/.test-manifest.json
```

---

## Capture Workflow

### When to Trigger

After ANY Phase 6 fix that modifies a `.vue` file's `<script>` block:

1. **Identify affected routes:**
   - Determine which `.vue` file was modified
   - Trace which view components import the modified file
     (grep for `import` statements referencing the modified file)
   - Map view components to routes (cross-reference `router/index.ts`)
   - If the modified file IS a view component, map directly to its route
   - If it's a shared component (e.g., `StatCard.vue`), identify ALL routes that use it

2. **For each affected route, capture a screenshot:**
   - Navigate to the route via dev-browser
   - If authentication required, login first (use test credentials)
   - Wait for page load completion:
     - Network idle (no pending requests)
     - No loading spinners visible
     - Main content rendered (not just skeleton)
   - Capture screenshot
   - Also capture `client.getAISnapshot()` for structural comparison

### Route-to-File Mapping (SocioCloud specific)

Common mappings to help trace affected routes:

```
src/views/v2/CommandCenter.vue    → /dashboard
src/views/v2/MyWork.vue           → /my-work
src/views/v2/LaunchFlow.vue       → /launch
src/views/v2/ProjectList.vue      → /projects
src/views/v2/ProjectWorkspace.vue → /projects/:id
src/views/v2/ReviewInbox.vue      → /review
src/views/v2/MessagesView.vue     → /messages
src/views/v2/AdminView.vue        → /admin
src/components/ui/AppShell.vue    → ALL routes (layout shell)
src/components/ui/NavRail.vue     → ALL routes (navigation)
src/components/StatCard.vue       → /dashboard
src/components/DataTable.vue      → multiple (projects, activities, salary, etc.)
src/components/StatusPill.vue     → multiple (projects, activities)
```

For components used in multiple views, check the 3 most important routes
(dashboard, projects list, activity detail) rather than all routes.

---

## Comparison Strategy

### Method 1: AI Snapshot Comparison (Primary)

Use dev-browser's `client.getAISnapshot()` before and after the fix.

Compare structurally:
- Same number of major sections/cards/tables?
- Same navigation elements visible?
- No error messages or blank sections that weren't there before?
- No "undefined" or "null" text appearing in data areas?
- No missing headings or labels?

**Pass criteria:**
- Structural content matches (same sections, same element types)
- Dynamic data differences are expected and acceptable (different numbers, dates)
- No new error states or blank areas

### Method 2: Screenshot Visual Comparison (Secondary, when baselines exist)

When baseline PNGs exist in `baseline/`:

1. Load baseline image
2. Load current screenshot
3. Compare visually:
   - Major layout areas in same position?
   - No large blank/white areas that weren't in baseline?
   - No obvious missing components?
   - Navigation and header still present?

**Threshold:**
- Minor differences in dynamic data (numbers, dates, counts) → PASS
- Major structural differences (missing sections, blank areas, error messages) → FAIL

### Decision Tree

```
Was a .vue file's <script> modified?
  NO  → Skip visual regression check
  YES → Identify affected routes
    ↓
For each affected route:
  ↓
Baseline exists?
  YES → Capture current screenshot
    ↓
    Compare current vs baseline (AI snapshot + visual)
      ↓
      Structural match?
        YES → PASS (fix is safe)
        NO  → Check nature of difference
          ↓
          Only dynamic data changed (numbers, dates)?
            YES → PASS (expected variation)
            NO  → FAIL → REVERT fix, mark NEEDS_HUMAN_REVIEW
  ↓
  NO  → Capture current as new baseline
    ↓
    Check for obvious errors (blank page, error messages, console errors)
      ↓
      Page renders normally?
        YES → Save as baseline, PASS
        NO  → FAIL → REVERT fix, mark NEEDS_HUMAN_REVIEW
```

---

## Baseline Lifecycle

### Creating Baselines

Baselines are created in two scenarios:

1. **First run (no baselines exist):**
   - During Phase 5 (browser E2E), capture screenshots of every tested route
   - Save to `baseline/` directory
   - These become the initial baselines

2. **New route added:**
   - When a test scenario references a route with no baseline
   - Capture and save automatically

### Updating Baselines

Baselines should be updated when intentional UI changes are made:

- **Automatic:** After a PASS with >5% visual difference (suggesting the UI evolved
  intentionally), log a note: "Baseline may be stale for {route}"
- **Manual:** User can run with `--update-baselines` to recapture all baselines
- **On NEEDS_HUMAN_REVIEW resolution:** After user manually fixes an issue, the next
  successful run should update the baseline for affected routes

### What Gets Committed

| Directory | Git tracked? | Purpose |
|-----------|-------------|---------|
| `baseline/` | YES | Reference snapshots for comparison |
| `current/` | NO (gitignored) | Transient screenshots from current run |
| `diff/` | NO (gitignored) | Debug images showing differences |

---

## Integration with Phase 6

In SKILL.md Phase 6 Step 5 (Validate Fix):

```
After re-running affected tests to validate a fix:

1. Check if the fix touched any .vue file's <script> block
2. If yes:
   a. Identify affected routes (see Route-to-File Mapping above)
   b. For each route:
      - Navigate via dev-browser
      - Capture screenshot and AI snapshot
      - Compare with baseline (if exists)
   c. If regression detected on ANY route:
      - REVERT the fix immediately (before marking it as failed)
      - Mark as NEEDS_HUMAN_REVIEW with:
        - Which route regressed
        - What changed visually
        - The fix that was reverted
      - Add to fix log: "Fix #N: REVERTED — visual regression on /{route}"
   d. If no regression:
      - Fix is safe, proceed to next failure cluster
      - Update baseline if needed
3. If no .vue files were touched: skip visual regression check
```
