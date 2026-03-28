# kivi-claude-skills

Personal Claude Code skills for deployment, debugging, testing, research, and project scaffolding.

## Installation

```bash
# Step 1: 添加仓库为 marketplace
/plugin marketplace add phoxiao/kivi-claude-skills

# Step 2: 从 marketplace 安装插件
/plugin install kivi-claude-skills@phoxiao-kivi-claude-skills
```

### Local Development

```bash
claude --plugin-dir ./path/to/kivi-claude-skills
```

## Skills

| Skill | Description |
|-------|-------------|
| `deploy` | China-server deployment workflow (Docker/GHCR/SSH) |
| `deepfix` | Causal-chain debugging: symptom → root cause before any fix |
| `testloop` | Automated test-fix-retest cycle with dev-browser |
| `fullstack-test-loop` | Full-stack auto test-fix loop (Go/Python/Rust/Node.js + Vue/React/Angular) |
| `scaffold` | Standardized project scaffolding (Go/Python/Vue/Fullstack) |
| `shipit` | One-command git commit, push, and PR |
| `prd` | Structured PRD document generation |
| `task-list` | PRD task decomposition with visual dashboard |
| `research` | Structured research documentation |
| `context-research` | AI research pipeline (HF Papers + web search + synthesis) |
| `autoresearch` | Autonomous ML experiment loop (Karpathy-inspired) |
| `i18n` | Vue 3 internationalization workflow (scan/extract/audit) |
| `hypercontext` | Spatial context awareness with ASCII architecture rendering |

## Usage

After installation, all skills are available with the `kivi-claude-skills:` prefix:

```
/kivi-claude-skills:deploy
/kivi-claude-skills:shipit
/kivi-claude-skills:deepfix
```

## License

MIT
