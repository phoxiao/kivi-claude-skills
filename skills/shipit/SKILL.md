---
name: shipit
description: 一条命令走完 git 提交、推送、必要时开 PR——按 Conventional Commits 格式（英文 type + 中文 subject），按文件名逐个暂存不用 git add -A，自动拦截 .env / 密钥这类敏感文件。当用户说「提交一下/推上去/发出去/shipit/commit 并 push」时使用。关键是**不要反问「要提交吗」也不要进 Plan Mode**——用户说 shipit 就是已经决定发了。只想看看改了什么、或者只要 commit 不要 push 时，不用它。
---

# /shipit — Git 提交推送一体化

## Description
One-command git commit, push, and optional PR creation. No questions asked — when the user says `/shipit`, they want to ship.

## Instructions

### Core Principle
**User invoked `/shipit` = intent to publish. Do NOT ask "should I commit?". Do NOT enter Plan Mode. Do NOT do a full code review.**

### Workflow

1. **Assess scope** (parallel):
   - `git status` — see all changes (never use `-uall`)
   - `git diff --stat` — understand change scope
   - `git log --oneline -5` — match existing commit style

2. **Safety checks**:
   - Exclude sensitive files: `.env`, `credentials.*`, `*.key`, `.DS_Store`, `node_modules/`
   - If sensitive files are staged, warn the user and remove them from staging
   - Never use `git add -A` or `git add .` — always stage files by name

3. **Stage files**:
   - Stage all modified/new files by explicit filename
   - Group related files logically

4. **Generate commit message** (Git Zen / Conventional Commits 风格):
   - 格式: `<type>(<scope>): <subject>`
   - type 使用英文 (`feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `style`)
   - scope 可选，标识影响模块
   - subject 使用中文，祈使语气，不超过 50 字符，不加句号
   - 需要时添加 body：空一行后用中文解释 **为什么**（不是怎么做），每行不超过 72 字符
   - 每个 commit 只做一件事（atomic commits）
   - Do NOT include `Co-Authored-By` lines
   - Use HEREDOC format:
     ```
     git commit -m "$(cat <<'EOF'
     <type>(<scope>): <中文 subject>

     <可选中文 body — 解释为什么>
     EOF
     )"
     ```
   - 示例:
     - `feat(auth): 添加微信 OAuth 登录`
     - `fix(api): 修复分页查询返回重复数据`
     - `docs: 添加项目需求文档和原型设计`
     - `refactor(db): 抽取连接池配置为共享模块`

5. **Push**:
   - `git push -u origin HEAD`
   - If push fails due to upstream changes, `git pull --rebase` then retry

6. **PR creation** (only when user says `/shipit pr`):
   - `gh pr create` with:
     - Short title (< 70 chars)
     - Body with `## Summary` (bullet points) + `## Test plan`
     - Footer: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

### Arguments
- `/shipit` — commit and push current changes
- `/shipit pr` — commit, push, and create PR
- `/shipit pr <base>` — create PR against specific base branch

### Rules
- **Never** force push (`--force`, `--force-with-lease`)
- **Never** amend existing commits
- **Never** skip hooks (`--no-verify`)
- **Never** enter Plan Mode
- **Never** ask confirmation before committing (the `/shipit` invocation IS the confirmation)
- **Never** include `Co-Authored-By` or other AI attribution lines in commit messages
- If there are no changes to commit, say so and stop
