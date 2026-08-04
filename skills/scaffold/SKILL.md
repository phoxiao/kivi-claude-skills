---
name: scaffold
description: 生成标准化项目脚手架（Go+Gin+GORM / Python+FastAPI / Vue 3+TS+Element Plus / 全栈），带 CLAUDE.md、接 shared-infra 的 docker-compose、GHCR 部署流水线、集成测试骨架。当用户说「新建一个项目/开个新的 XX 项目/初始化项目/搭个脚手架/scaffold」时使用。这套模板内置了这台机器的既定约定（项目落在 side_project 下、镜像走 GHCR、API 字段 snake_case），比从零手搭少踩很多坑。往已有项目里加模块、加单个文件不用它。
argument-hint: '[go | python | vue | fullstack] <项目名>'
---

# /scaffold — 标准化项目脚手架

## Description
Generate standardized project scaffolds with CLAUDE.md, Docker setup, CI/CD, and integration test skeleton.

## Instructions

### Subcommands
- `/scaffold go <name>` — Gin + GORM + PostgreSQL project
- `/scaffold python <name>` — FastAPI + Pydantic project
- `/scaffold vue <name>` — Vue 3 + TypeScript + Element Plus + Pinia project
- `/scaffold fullstack <name>` — Go backend + Vue frontend (SocioCloud style)

### Project Location
All projects are created at: `/Volumes/BOX/WorkSpace/side_project/<name>/`

### Common Files (all templates)

Every project gets:

1. **`CLAUDE.md`** — project-specific instructions including:
   - Tech stack summary
   - Key commands (build, test, lint, deploy)
   - Data contracts (API field naming, enum conventions)
   - Deployment info (GHCR image, server, workflow)

2. **`docker-compose.yml`** — local development environment
   - Uses `shared-infra` external network for shared services
   - PostgreSQL 16, Redis 7, MinIO references (not duplicated)

3. **`.github/workflows/deploy.yml`** — CI/CD based on deploy-tools template
   - Build → Push to GHCR → SSH deploy
   - Never uses Docker Hub

4. **`tests/integration/`** — integration test skeleton
   - Database setup/teardown helpers
   - API endpoint test templates
   - Forces integration-first methodology

5. **`.env.example`** — documented environment variables

6. **`.gitignore`** — comprehensive ignore file

### Template: Go (`/scaffold go <name>`)

```
<name>/
├── CLAUDE.md
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── config/
│   │   └── config.go
│   ├── handler/
│   │   └── handler.go
│   ├── model/
│   │   └── model.go
│   ├── repository/
│   │   └── repository.go
│   └── service/
│       └── service.go
├── tests/
│   └── integration/
│       └── api_test.go
├── docker-compose.yml
├── Dockerfile
├── .github/workflows/deploy.yml
├── .env.example
├── .gitignore
├── go.mod
└── go.sum
```

### Template: Python (`/scaffold python <name>`)

```
<name>/
├── CLAUDE.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   └── services/
├── tests/
│   └── integration/
│       └── test_api.py
├── docker-compose.yml
├── Dockerfile
├── .github/workflows/deploy.yml
├── .env.example
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

### Template: Vue (`/scaffold vue <name>`)

```
<name>/
├── CLAUDE.md
├── src/
│   ├── App.vue
│   ├── main.ts
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   └── index.ts
│   ├── views/
│   ├── components/
│   ├── composables/
│   ├── api/
│   │   └── index.ts
│   ├── types/
│   │   └── index.ts
│   └── locales/
│       ├── zh-CN.json
│       └── en.json
├── tests/
│   └── integration/
├── docker-compose.yml
├── Dockerfile
├── .github/workflows/deploy.yml
├── .env.example
├── .gitignore
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Conventions
- API field names: `snake_case`
- Enum values: `UPPER_SNAKE_CASE`
- Docker image registry: GHCR (`ghcr.io/<org>/<name>`)
- Database naming: `snake_case` (tables and columns)
- Go struct tags: `json:"field_name" gorm:"column:field_name"`
- Pydantic: use `alias` for API compatibility when needed

### Rules
- Do NOT create empty placeholder files — every file should have meaningful starter content
- Do NOT duplicate shared infrastructure (PostgreSQL, Redis, MinIO) — reference via external network
- Always initialize git: `git init && git add . && git commit -m "Initial scaffold"`
- Generate a comprehensive `.gitignore` appropriate for the tech stack
