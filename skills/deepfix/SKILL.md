---
name: deepfix
description: 因果链深度调试——在改任何一行代码之前，先把「症状 → 近因 → 深层原因 → 根因」这条链走完，避免修在第一个搜到的匹配文件上。当用户报告 bug、贴报错或堆栈、说「这里不对/为什么会这样/查一下这个问题」，尤其是跨模块的数据对不上（前端拿到空数组、枚举值大小写不一致、字段名前后端不一致）时使用。也在你自己准备直接动手改代码修 bug 前主动用它——浅层修复的代价是反复返工。纯粹的语法错误、拼写错误、类型标注不匹配这类一眼定位的问题不用它。
argument-hint: '[bug 描述或报错信息]'
---

# /deepfix — 因果链深度调试

## Description
Causal-chain debugging that traces from symptoms to root cause BEFORE making any code changes. Prevents shallow fixes and wrong initial approaches.

## Instructions

### Core Rule
**DO NOT EDIT ANY FILE UNTIL STEP 3 IS COMPLETE.**

This is not a suggestion — it is a hard constraint. Steps 1 and 2 are READ-ONLY.

### Workflow

#### Step 1: Reproduce & Observe (READ-ONLY)

- Locate the failure: error message, stack trace, unexpected behavior
- Identify the failure layer: UI → API → Service → Database → Infrastructure
- Read relevant log output, console errors, test failures
- Do NOT hypothesize fixes yet

#### Step 2: Trace the Causal Chain (READ-ONLY)

Build the full chain before proposing any fix:

```
[Symptom] ← [Proximate Cause] ← [Deeper Cause] ← [Root Cause]
```

**Example:**
```
"ReviewList shows 0 items"
  ← API returns empty array
  ← Query uses status="IN_REVIEW" but data has "in_review"
  ← Frontend/backend enum convention mismatch (no shared contract)
```

**Mandatory cross-module checks:**
- Compare producer's response model vs consumer's expected model
- Check field names, types, enum values, casing conventions
- Check serialization/deserialization (JSON tags, Pydantic aliases)
- Check database schema vs ORM model vs API response

**Tech-stack specific checks:**

| Stack | What to check |
|-------|---------------|
| Go + GORM | `gorm:"column:..."` tags, `json:"..."` tags, `binding:"..."` tags, AutoMigrate vs actual DB schema |
| Python + FastAPI | Pydantic `alias`, `response_model`, `async/await` correctness, SQLAlchemy column names |
| Vue 3 + TS | Prop types vs API response shape, `.value` unwrapping, Element Plus event names (`@change` vs `@update:modelValue`) |
| Docker | Env var names consistency across `.env`, `docker-compose.yml`, and app config |

#### Step 3: Propose Fix

Present to the user:
1. **Causal chain** — the full trace from symptom to root cause
2. **Confidence** — HIGH / MEDIUM / LOW
3. **Fix scope** — which files and what changes
4. **Impact** — what else could break
5. **Regression risk** — HIGH / MEDIUM / LOW

Wait for user acknowledgment if confidence is MEDIUM or LOW.

#### Step 4: Fix & Verify

1. Apply the **minimal fix** — don't refactor surrounding code
2. If it's a contract mismatch, fix **both sides** (producer AND consumer)
3. Add or update tests that would have caught this bug
4. Run the full test suite for affected modules
5. If using dev-browser, verify the fix visually

### Arguments
- `/deepfix` — start debugging the current issue (user describes the bug)
- `/deepfix <error message>` — start from a specific error
- `/deepfix <file:line>` — start from a specific location

### Anti-Patterns (DO NOT DO)
- Fixing the first file that matches a search query
- Adding a `try/catch` to suppress an error without understanding why it occurs
- Changing types/interfaces without checking all consumers
- Fixing only one side of a producer/consumer contract mismatch
- Skipping the causal chain because "the fix is obvious"
