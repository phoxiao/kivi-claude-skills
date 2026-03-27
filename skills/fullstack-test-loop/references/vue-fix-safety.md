# Vue SFC Fix Safety Rules

## The Problem

Auto-fixing `.vue` Single File Components (SFC) can break UI by modifying template structure
or styles. This has caused production regressions (e.g., dashboard layout breaking after
auto-fix modified template bindings).

**Why template/style changes are high-risk:**
1. Templates contain structural HTML that affects layout, accessibility, and data binding
2. Styles contain CSS that affects visual appearance across the entire component
3. Both interact with UI frameworks (Element Plus, Tailwind CSS) in complex, non-obvious ways
4. Both are extremely difficult to validate without visual inspection
5. A single changed class or directive can cascade through the entire page layout

---

## Rules

### ALLOWED Fixes in .vue Files

Only modifications within `<script>` or `<script setup>` blocks:

1. Reactive data declarations (`ref`, `reactive`, `computed`, `watch`)
2. Function logic (event handlers, API calls, data transforms)
3. TypeScript type annotations and interfaces
4. Import statements (adding, removing, renaming)
5. Pinia store usage patterns (`useXxxStore()`, store actions/getters)
6. Vue Router navigation calls (`router.push()`, `useRoute()`)
7. Lifecycle hook logic (`onMounted`, `onUnmounted`, `watchEffect`, etc.)
8. Variable declarations and assignments
9. Composable usage (`useToast()`, `useListFilters()`, etc.)

### FORBIDDEN Fixes in .vue Files

ANY modification to `<template>` or `<style>` blocks, including but not limited to:

1. Adding, removing, or reordering HTML elements
2. Changing CSS classes on elements (including Tailwind utility classes)
3. Modifying `v-if`, `v-show`, `v-for`, `v-model` directives
4. Changing component props passed in template (e.g., `:loading="xxx"`)
5. Changing event bindings in template (e.g., `@click="xxx"`)
6. Modifying slot content
7. Changing `<style>` rules, selectors, or scoped/module attributes
8. Adding or removing `<style>` blocks
9. Changing `<template>` root element structure

**Exception:** If a `<script>` fix renames a function/variable that is referenced in `<template>`
(e.g., renaming `handleClick` to `onClick`), the template reference must also be updated.
This is the ONLY case where template modification is allowed, and it must be a mechanical
rename only — no structural changes.

---

## When Root Cause Is in Template or Style

If causal chain analysis shows the root cause is in `<template>` or `<style>`:

1. **Document the finding clearly:**
   ```
   NEEDS_HUMAN_REVIEW:
     File: src/views/v2/CommandCenter.vue
     Block: <template> line 45
     Issue: v-for key binding uses wrong field, causing duplicate render
     Suggested fix: Change :key="item.name" to :key="item.id"
     Reason auto-fix blocked: template modification forbidden (vue-fix-safety rule)
   ```

2. **Mark as NEEDS_HUMAN_REVIEW** — do NOT attempt the fix
3. **Provide exact location** (file path, line number, block type)
4. **Provide suggested change** with before/after code
5. **Explain why** the change is needed (what test it would fix)
6. **Continue** to the next failure cluster — do not block on this

---

## SFC Block Detection

Before applying ANY fix to a `.vue` file, determine the block boundaries:

### Parsing Strategy

Use regex to find block boundaries:

```
<script[^>]*>     → script block start
</script>         → script block end

<template[^>]*>   → template block start
</template>       → template block end

<style[^>]*>      → style block start
</style>          → style block end
```

### Validation Steps

1. Parse the SFC to identify line ranges for each block
2. Determine which block(s) your proposed fix touches
3. If the fix modifies ANY line within `<template>` or `<style>` range → BLOCK the fix
4. If the fix only modifies lines within `<script>` or `<script setup>` range → ALLOW

### Edge Cases

- **Multiple `<style>` blocks**: All are forbidden (scoped and unscoped)
- **Multiple `<script>` blocks**: Both `<script>` and `<script setup>` are allowed
- **`<script>` with `lang="ts"`**: Still allowed (it's still a script block)
- **Inline styles in template** (`:style="..."`): These are in `<template>`, so FORBIDDEN
- **Dynamic classes in template** (`:class="..."`): These are in `<template>`, so FORBIDDEN
  - However, changing the logic function that computes the class (in `<script>`) IS allowed

---

## Integration with Fix Workflow

This file is referenced from Phase 6 Step 4 in SKILL.md:

```
Before fixing any .vue file:
  1. Read this file (references/vue-fix-safety.md)
  2. Parse the SFC block boundaries
  3. Check if proposed fix touches template/style
  4. If yes → NEEDS_HUMAN_REVIEW
  5. If no → proceed with fix
  6. After fix → run visual regression check (references/visual-regression.md)
```
