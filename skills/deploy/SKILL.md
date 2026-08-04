---
name: deploy
description: 中国服务器感知的部署工作流（GitHub Actions → SSH，镜像走 GHCR 不走 Docker Hub）。当用户说「部署/上线/发布/推到服务器/deploy <项目>」、要查各服务的部署状态、或者部署失败要排查时使用。尤其在出现 Docker Hub 拉取超时、GHCR 认证失败、SSH 连不上服务器这类中国网络环境特有的故障时，直接用这个 skill 的排查顺序，不要自己瞎试。本地跑 docker compose、改 CI 配置文件本身不算部署，不用它。
argument-hint: '[项目名 | status | debug <项目名>]'
---

# /deploy — 中国服务器感知部署

## Description
Deployment workflow optimized for China-hosted servers with Docker/GHCR/SSH. Handles common failure modes like Docker Hub timeouts and GHCR auth issues.

## Instructions

### Subcommands
- `/deploy <project>` — Execute deployment for a project
- `/deploy status` — Check all service statuses
- `/deploy debug <project>` — Diagnose deployment failure

### Architecture Assumptions
- Deployments run via **GitHub Actions → SSH to server**, NOT from local machine
- Docker images are hosted on **GHCR** (ghcr.io), NEVER Docker Hub
- Deploy configs live in `/Volumes/BOX/WorkSpace/side_project/deploy-tools/`
- Infrastructure: PostgreSQL 16, Redis 7, MinIO on shared-infra Docker network

### `/deploy <project>` Workflow

1. Check if the project has a `.github/workflows/deploy.yml`
2. Verify the latest commit is pushed (`git status`, compare with remote)
3. Trigger deployment: `gh workflow run deploy.yml` or push to trigger branch
4. Monitor: `gh run list --workflow=deploy.yml --limit=3`
5. If failed, automatically switch to debug mode

### `/deploy status` Workflow

1. List all projects with deploy workflows:
   ```
   find /Volumes/BOX/WorkSpace/side_project/ -name "deploy.yml" -path "*/.github/*"
   ```
2. For each project, show latest workflow run status:
   ```
   gh run list --workflow=deploy.yml --limit=1 --json status,conclusion,createdAt
   ```

### `/deploy debug <project>` — China Server Troubleshooting

**Follow this order strictly. Do NOT skip steps.**

1. **Check GitHub Actions logs first**:
   ```
   gh run list --workflow=deploy.yml --limit=1
   gh run view <run-id> --log-failed
   ```

2. **GHCR auth failure** (error: `unauthorized`, `denied`):
   - Check repository's `packages: write` permission in workflow YAML
   - Verify `GITHUB_TOKEN` or `CR_PAT` secret exists
   - Check if package visibility matches (private repo → private package)

3. **Docker Hub pull timeout** (error: `context deadline exceeded`, `TLS handshake timeout`):
   - Determine if it's a base image (`FROM node:20`) or app image
   - For base images: suggest using GHCR mirror or pre-pulled images
   - **NEVER suggest switching from GHCR to Docker Hub** — Docker Hub is unreliable from China

4. **SSH deployment timeout** (error: `ssh: connect`, `Connection timed out`):
   - Increase `command_timeout: 5m` in workflow
   - Check if server firewall allows GitHub Actions IP ranges
   - Verify SSH key is correctly set in repository secrets

5. **Container health check failure** (deployed but not running):
   - SSH to server, run `docker logs <container>` for app logs
   - Check `docker compose ps` for container status
   - Verify `.env` on server matches expected config

6. **Image tag mismatch** (deployed but wrong version):
   - Compare `.env` `IMAGE_TAG` on server vs latest GHCR tag
   - Check if `docker compose pull` was executed in deploy script

### Rules
- **NEVER** suggest switching from GHCR to Docker Hub
- **NEVER** run deployment commands locally — always through GitHub Actions
- Always check GitHub Actions logs BEFORE SSH-ing to the server
- Do NOT enter Plan Mode for deployment debugging
