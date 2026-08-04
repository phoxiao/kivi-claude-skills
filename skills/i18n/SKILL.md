---
name: i18n
description: Vue 3 项目的国际化工作流——扫描硬编码中文、抽取到 locale 文件并替换成 $t() 调用、审计各语言 key 的完整性。当用户说「国际化/i18n/做多语言/提取中文/这个页面还没翻译/locale 文件对不上/加一门语言」，或者在 Vue 项目里看到模板和 TS 里散着写死的中文需要收拢时使用。非 Vue 项目、或者只是要翻译一段文本，不用它。
argument-hint: '[scan | extract | audit]'
---

# /i18n — Vue 国际化工作流

## Description
Internationalization workflow for Vue 3 projects. Scans, extracts, and audits i18n strings.

## Instructions

### Subcommands
- `/i18n scan` — Scan for hardcoded Chinese strings in Vue/TS files
- `/i18n extract` — Extract strings to locale files and replace with `$t()` calls
- `/i18n audit` — Check key completeness across all locale files

### `/i18n scan`

1. Search for hardcoded Chinese characters in:
   - `src/**/*.vue` — template and script sections
   - `src/**/*.ts` — TypeScript files
   - Exclude: `src/locales/`, `node_modules/`, `dist/`

2. Pattern to detect Chinese: `[\u4e00-\u9fff]`

3. Output format:
   ```
   ## Hardcoded Chinese Strings Found

   ### src/views/Dashboard.vue
   - Line 15: `<h1>仪表盘</h1>` → suggested key: `dashboard.title`
   - Line 28: `placeholder="请输入搜索内容"` → suggested key: `dashboard.search_placeholder`

   ### src/components/UserCard.vue
   - Line 8: `'用户不存在'` → suggested key: `user.not_found`

   Total: 3 strings in 2 files
   ```

### `/i18n extract`

1. Run scan first to identify strings
2. For each string:
   - Generate a key following the naming convention: `page.section.description`
   - Add the key and Chinese value to `src/locales/zh-CN.json`
   - Add the key with empty string to `src/locales/en.json` (for later translation)
   - Replace the hardcoded string with `$t('key')` or `t('key')` in setup script

3. Handle different contexts:
   - Template text: `<h1>{{ $t('dashboard.title') }}</h1>`
   - Template attribute: `:placeholder="$t('dashboard.search_placeholder')"`
   - Script string: `t('user.not_found')` (requires `const { t } = useI18n()`)
   - Ensure `useI18n()` import exists in `<script setup>` if not already present

### `/i18n audit`

1. Read all locale files in `src/locales/`
2. Compare keys across all files
3. Report:
   ```
   ## i18n Audit Report

   ### Missing Keys
   - `en.json` missing: dashboard.title, user.not_found (2 keys)
   - `zh-CN.json` missing: none

   ### Empty Values
   - `en.json`: dashboard.title, dashboard.search_placeholder (2 keys)

   ### Unused Keys (not referenced in source)
   - `zh-CN.json`: old.deprecated_key

   Total keys: 45
   Coverage: zh-CN 100%, en 93%
   ```

### Key Naming Convention
- Format: `page.section.description`
- Use `snake_case` for multi-word segments
- Examples:
  - `dashboard.title` — page title
  - `dashboard.search_placeholder` — search input placeholder
  - `user.form.email_label` — form field label
  - `common.confirm` — shared across pages
  - `error.network_error` — error messages

### Default Locale
- Primary: `zh-CN`
- Secondary: `en`

### Rules
- Never delete existing keys during extract — only add new ones
- Always preserve the existing structure and ordering of locale files
- Use flat key structure with dot notation, not nested objects
- If `vue-i18n` is not installed, warn the user before proceeding
