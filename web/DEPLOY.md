# WeWrite 线上部署（P1：容器沙箱 + 并发）

单机内部体验版。LLM 走 relay（真 Claude），每任务关进一次性 Docker 容器。

## 1. 前置
- 一台专用 Linux VM（Ubuntu/Debian 系示例），装好 Docker、Python3.11、Node、nginx、git。
- 跑后端用**非 root** 账号；该账号加入 `docker` 组（或用 rootless docker）。
- 安全组只放 443（80 仅留给 certbot，22 限你自己 IP）。

## 2. 拉代码 + 后端依赖

```bash
git clone https://github.com/oaker-io/wewrite-platform.git wewrite && cd wewrite
python3 -m venv web/backend/.venv
web/backend/.venv/bin/pip install -r web/backend/requirements.txt -r requirements.txt
```

## 3. 构建任务镜像 + 专用网络 + 出站防火墙

```bash
docker build -f web/backend/docker/Dockerfile.job -t wewrite-job:latest .
docker network create wewrite-jobs
sudo bash web/backend/docker/firewall-jobs.sh wewrite-jobs
```

## 4. 后端 .env（容器模式 + relay 真 Claude）

```bash
ANTHROPIC_BASE_URL=https://relay.upthos.com
ANTHROPIC_AUTH_TOKEN=<有 Claude 权限的 relay key>
WEWRITE_MODEL=claude-sonnet-4-6
WEWRITE_RUNNER=container
WEWRITE_MAX_CONCURRENT_JOBS=3
WEWRITE_MAX_PER_USER_JOBS=1
WEWRITE_JOB_IMAGE=wewrite-job:latest
WEWRITE_JOB_NETWORK=wewrite-jobs
WEWRITE_IMAGE_PROVIDER=sub2api
WEWRITE_IMAGE_API_KEY=<生图 key>
WEWRITE_IMAGE_BASE_URL=https://relay.upthos.com
WEWRITE_IMAGE_MODEL=gpt-image-2
APP_SECRET_KEY=<Fernet key>
```

验证 relay 真 Claude（响应 model 以 claude 开头）：见 web/QUICKSTART.md 的自检 curl。

## 5. 起服务 + 自检

```bash
web/backend/.venv/bin/uvicorn app.main:app --app-dir web/backend --env-file web/backend/.env --host 127.0.0.1 --port 8000
curl -s localhost:8000/api/health   # runner=container, runner_ready=true
```

（生产用 systemd 守护；nginx 反代 + certbot TLS，参考 QUICKSTART。）

## 6. 安全冒烟（必做）

```bash
docker run --rm --network wewrite-jobs curlimages/curl -m 5 http://169.254.169.254 || echo "OK: 元数据被堵"
docker run --rm --network wewrite-jobs curlimages/curl -m 5 https://relay.upthos.com >/dev/null && echo "OK: 公网可达"
```

## 7. 已知限制 / 运维注意（P1）
- **工作区写权限**：任务容器以**宿主属主身份**运行（ContainerRunner 传 `--user $(id -u):$(id -g)`），因此跑后端的账号必须对 `WEWRITE_WORKSPACE_ROOT`（默认系统临时目录）与 `WEWRITE_ARTIFACT_ROOT` 有读写权。这样镜像内 uid 与宿主挂载目录属主一致，避免 PermissionError。
- **URL 取材降级**：任务镜像未装 Playwright/Camoufox 的浏览器二进制，`scripts/fetch_article.py` 在容器内只能用 requests 级抓取（Level 1）；抓 bot 防护强的页面会静默降级。若线上需要浏览器级抓取，在 Dockerfile.job 的 pip 安装后追加 `playwright install --with-deps chromium`（镜像会变大）。多数 distribute 任务用 source_text/source_job_id，不受影响。
- **CLI 版本**：`@anthropic-ai/claude-code` 未固定版本；如需可复现构建，改成 `npm install -g @anthropic-ai/claude-code@<版本>`。容器 rootfs 只读，CLI 运行时不会自更新。
- **状态在内存**：后端进程重启会清空账号/任务/历史（P1 内存版；P2 上 DB）。
- **构建上下文**：`docker build` 用仓库根作上下文，已加根 `.dockerignore` 排除 `web/frontend`/`node_modules` 等大目录。
