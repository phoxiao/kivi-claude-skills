---
name: testloop
description: 用 dev-browser 跑自主的「测试 → 诊断 → 修复 → 复验」循环，专测浏览器里的用户流程（导航、列表分页与空态、表单校验与提交、弹窗、登录态与路由守卫），每轮抓 console 报错和接口报错，最多三轮。当用户说「测一下这个页面/点一遍看有没有问题/这个流程走不通/testloop <url>」时使用。禁止改用 Playwright。要跑的是完整测试金字塔（编译、后端单测、前端类型检查、API 端到端）时用 fullstack-test-loop，那个覆盖面更大；这个只管浏览器里点得到的部分。
argument-hint: '[<url> | all] [--focus=<区域>]'
---

# /testloop — 自主 Dev-Browser 测试循环

## Description
Automated test-fix-retest cycle using dev-browser. Systematically tests user flows, diagnoses issues, fixes them, and re-verifies.

## Instructions

### Core Rule
**ALWAYS use dev-browser. NEVER use Playwright directly.**

### Subcommands
- `/testloop <url>` — test a specific page
- `/testloop all` — discover all routes from router file and test each
- `/testloop <url> --focus=<area>` — test a specific area (forms, lists, navigation, etc.)

### Per-Round Workflow (max 3 rounds)

#### 1. Observe
- Open URL with dev-browser
- Set up listeners for console errors and API errors
- Take AI snapshot: `client.getAISnapshot()`
- Screenshot the initial state

#### 2. Interact
Test these user flows in order:
1. **Navigation** — links, menu items, breadcrumbs
2. **Lists/Tables** — data loading, pagination, empty states
3. **Forms** — input, validation, submission, error display
4. **Modals/Dialogs** — open, interact, close
5. **Auth flows** — login state, protected routes, redirects

For each interaction:
```javascript
// Use selectSnapshotRef to interact with elements
const ref = await client.selectSnapshotRef('button text or description');
await ref.click();
// Re-snapshot after interaction
const snapshot = await client.getAISnapshot();
```

#### 3. Diagnose & Fix
- For each issue found, trace to source code using `/deepfix` methodology
- Apply fix
- Log the issue and fix for the round summary

#### 4. Retest
- Reload the page
- Re-run the same interactions
- Verify fixes and check for regressions
- If new issues found, start next round (max 3 rounds)

### Route Discovery (`/testloop all`)

1. Find the router file:
   - Vue: `src/router/index.ts` or `src/router/index.js`
   - React: `src/routes.tsx` or `src/App.tsx`
2. Extract all route paths
3. Test each route sequentially
4. Generate summary report

### Dev-Browser Rules
- Use `client.getAISnapshot()` for page state, NOT DOM parsing
- Use `client.selectSnapshotRef()` for element interaction
- In `page.evaluate()`, do NOT use TypeScript type annotations — it's plain JavaScript
- Always screenshot before and after significant interactions
- Wait for network idle after navigation

### Output Format

After testing, produce a summary:
```
## Test Results — <url>
### Round 1
- [PASS] Navigation: all links working
- [FAIL] Form: email validation not triggered → Fixed in src/components/LoginForm.vue:42
- [FAIL] API: 401 on /api/users → Fixed in src/middleware/auth.ts:15

### Round 2 (retest)
- [PASS] Form: email validation working
- [PASS] API: auth middleware fixed
- [FAIL] List: empty state not shown → Fixed in src/views/UserList.vue:28

### Round 3 (retest)
- [PASS] All previous fixes verified
- No new issues found

Total: 5 tests, 5 passed, 0 failed
Rounds: 3
```
