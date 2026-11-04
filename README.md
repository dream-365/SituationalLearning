# 情景学习（SituLearn）

Turn a documentary or movie `.srt` into an offline, listenable SituLearn document: narration, images, audio, and vocabulary cards in one portable format.

## Status

The canonical artifact is a **SituLearn document**:

```text
reports/<name>/
├── document.json     # the single content truth
├── media/            # audio/images referenced by media/... hrefs
└── index.html        # derived view (optional)
```

`document.json` is JSON with ordered `sections` and typed `blocks`
(`text`, `image`, `audio`, `word`, `group`). A `.situ` file is just a zip
containing `document.json` + `media/`; the same document works offline and
online.

`manifest.json` / `report.html` are no longer produced. Older reports are
converted with `situlearn migrate`.

Specs:

- `docs/specs/SPEC-004-presentation-format/spec.md` (Approved) — document format
- `docs/specs/SPEC-003-content-type-profiles/spec.md` (content types)
- `docs/specs/SPEC-002-report-web-publishing/spec.md` (historical publishing context)

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Install uv first if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the released CLI:

```bash
uv tool install --python 3.12 https://github.com/dream-365/SituationalLearning/releases/download/v0.2.2/situlearn-0.2.2-py3-none-any.whl
```

If PyPI/GitHub is slow, set `HTTPS_PROXY` to your local proxy before installing.

## Environment

Build/CLI:

| 变量 | 默认 | 用途 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | — | 必填；叙事、术语、释义 |
| `MIMO_API_KEY` | — | 必填；TTS |
| `DEEPSEEK_MODEL` | `deepseek-flash` | LLM 模型 |
| `DEEPSEEK_BASE_URL` / `MIMO_BASE_URL` | 官方 | 自建/代理端点 |

Web 服务：

| 变量 | 默认 | 用途 |
| --- | --- | --- |
| `PUBLISH_TOKEN` | — | 单个发布令牌；映射到 `DEFAULT_OWNER_ID` |
| `PUBLISH_TOKENS` | `{}` | JSON `{token: owner_id}` 多 owner 注册表 |
| `DEFAULT_OWNER_ID` / `OWNER_NAME` | `owner-0001` / `default` | bootstrap owner |
| `SITE_BASE_URL` | `http://localhost:8000` | 公开 URL 前缀 |
| `SITULEARN_DATA_DIR` | `~/.cache/situlearn/web` | SQLite / 本地对象存储 |
| `SITULEARN_BACKUP_DIR` | `~/.cache/situlearn/backup` | 本地备份目录 |
| `SITULEARN_STAGING_DIR` | `<data>/staging` | 上传暂存 |
| `PUBLISH_ENABLED` | `true` | 关闭 POST 发布 |
| `MAX_REPORT_BYTES` / `MAX_REPORT_FILES` | 100 MiB / 2000 | 上传限额 |
| `MAX_REPORTS` | 50 | 单 owner 报告上限 |
| `PUBLISH_RATE_LIMIT` | `5/min` | 发布限流 |
| `PREVIOUS_VERSION_TTL_H` | 24 | 旧版本保留小时数 |
| `DB_BUSY_TIMEOUT_MS` / `LOG_LEVEL` | 5000 / info | SQLite / 日志 |
| `OSS_BUCKET` / `OSS_ENDPOINT` / `OSS_PREFIX` | — | 阿里云 OSS |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | — | OSS 密钥 |
| `OSS_CONNECT_TIMEOUT_MS` / `OSS_READ_CACHE_TTL_S` | 3000 / 60 | OSS 超时/缓存 |

> `PUBLIC_RATE_LIMIT`、`AUDIO_CACHE_MAX_MB`、`SENTRY_DSN` 目前在配置中保留但尚未生效；不要把它们当作已启用的控制项。

## Build

```bash
export DEEPSEEK_API_KEY=...
export MIMO_API_KEY=...
situlearn build your-documentary.en.srt --out reports/your-documentary
```

Outputs `document.json`, `media/`, and a derived `index.html`.

```bash
situlearn build your-movie.en.srt --content-type movie --out reports/your-movie
situlearn build input.srt --out reports/machine --no-render
situlearn build input.srt --out reports/demo --package
```

`--no-render` skips `index.html`; `--package` also writes `reports/demo.situ`.

Stage and audio caches live in `~/.cache/situlearn/` and are reused unless
`--force` is passed. Documentary and movie builds use separate cache namespaces.

## Render

```bash
situlearn render reports/your-documentary --out reports/your-documentary-html
situlearn render reports/your-documentary.situ --out reports/your-documentary-html
```

`--out` must be a new or empty directory. The output contains `index.html` +
`media/`; it does not copy `document.json`.

## Package

```bash
situlearn package reports/your-documentary --out reports/your-documentary.situ
```

`.situ` contains only `document.json` and the media referenced by `document.json`.

## Migrate old reports

```bash
situlearn migrate reports/old-report --out reports/migrated
situlearn migrate-batch exports/bundles --out reports/migrated
```

`migrate-batch` expects `<export-root>/<report_key>/manifest.json + assets/` and
writes `<out-root>/<report_key>/document.json + media/`；只有 bundle 带旧 slug 时才写
`publish.json`。

## Publish

```bash
export SITULEARN_PUBLISH_TOKEN=...
situlearn publish reports/your-documentary --server https://learn.example.com
situlearn publish reports/your-documentary.situ --server https://learn.example.com --slug old-slug
```

The publish token identifies an owner. The same owner + `report_key` overwrites
the same report; different owners cannot overwrite each other. `publish.json`
next to a document directory can carry the requested slug.

Public routes:

| 路由 | 说明 |
| --- | --- |
| `/r/<slug>` | 派生报告页 |
| `/r/<slug>/chapters/{section_id}` | 单章节页 |
| `/r/<slug>/vocabulary` | 词表，支持 `section` / `category` / `q` |
| `/r/<slug>/document.json` | 公开投影；移除 `meta.id`、`meta.source.filename`、`meta.source.sha256` |
| `/r/<slug>/media/...` | 仅服务已注册资源；MIME 来自 `resources[*].mime` |
| `/r/<slug>/assets/...` | 旧路径，308 到 `/media/...` |
| `/r/<slug>/manifest.webmanifest` | PWA manifest |
| `/healthz` / `/readyz` / `/metrics` | 健康检查与指标 |
| `/offline` / `/sw.js` | 离线页 / Service Worker |

API（Bearer token）：

| 方法与路径 | 说明 |
| --- | --- |
| `POST /api/v1/reports` | multipart `archive` + 可选 `requested_slug` |
| `GET /api/v1/reports` | 当前 owner 的报告列表 |
| `GET /api/v1/reports/{slug}` | owner 内元数据；跨 owner 404 |
| `DELETE /api/v1/reports/{slug}` | owner 内下架；跨 owner 404 |

## Run the web service

```bash
export PUBLISH_TOKEN=dev-token
export SITE_BASE_URL=http://localhost:8000
export SITULEARN_DATA_DIR=~/.cache/situlearn/web-dev
uv run uvicorn situlearn.web.app:app --host 0.0.0.0 --port 8000
```

Optional multi-owner token registry:

```bash
export PUBLISH_TOKENS='{"token-a":"owner-a","token-b":"owner-b"}'
```

Then publish from another terminal:

```bash
SITULEARN_PUBLISH_TOKEN=dev-token \
  uv run situlearn publish reports/your-documentary --server http://localhost:8000
```

## K3s deployment

The deployment resources live in `deploy/k8s`.

- `overlays/prod/`：ghcr 镜像 + 本地 PVC 对象存储（不配置 OSS）。
- `overlays/prod-oss/`：阿里云镜像 + OSS，生产推荐。

Build and push an image first, then update the image tag in the chosen overlay.
The current package version is `0.2.2`.

```bash
docker build -t ghcr.io/dream-365/situlearn-web:0.2.2 .
docker push ghcr.io/dream-365/situlearn-web:0.2.2

kubectl create namespace situlearn --dry-run=client -o yaml | kubectl apply -f -
# prod-oss: include OSS keys; prod may omit them (secret refs are optional)
kubectl create secret generic situlearn-secrets -n situlearn \
  --from-literal=PUBLISH_TOKEN="$(openssl rand -hex 32)" \
  --from-literal=OSS_ACCESS_KEY_ID="$OSS_ACCESS_KEY_ID" \
  --from-literal=OSS_ACCESS_KEY_SECRET="$OSS_ACCESS_KEY_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl diff -k deploy/k8s/overlays/prod-oss
kubectl apply -k deploy/k8s/overlays/prod-oss
kubectl rollout status deployment/situlearn -n situlearn --timeout=10m
```

Backup/restore and cutover/rollback are in
[`docs/runbooks/publish-report.md`](docs/runbooks/publish-report.md).

Health checks:

```bash
curl -fsS https://learn.example.com/healthz
curl -fsS https://learn.example.com/readyz
curl -fsS https://learn.example.com/metrics | head
```

## iPad

1. Open the published URL in Safari.
2. Tap the share button and choose “添加到主屏幕” to install the report as a PWA.
3. Play a section, then lock the iPad; audio should continue and lock-screen controls should work.
4. Reopen the report to resume from the last section/position.
5. Already opened pages and played audio are cached for weak or offline networks.

## CLI reference

| 命令 | 主要参数 |
| --- | --- |
| `build <input.srt>` | `--out`（必填）、`--content-type documentary\|movie`、`--no-audio`、`--no-render`、`--package`、`--voice`、`--terms-min`、`--terms-max`、`--force` |
| `render <dir\|.situ>` | `--out`（必填，必须新目录或空目录） |
| `package <dir>` | `--out`、`--force` |
| `migrate <old-dir>` | `--out`、`--source-language`、`--force` |
| `migrate-batch <export-root>` | `--out`、`--source-language`、`--force` |
| `export-bundles` | `--data-dir`、`--out` |
| `publish <dir\|.situ>` | `--server`、`--slug`、`--dry-run`、`--token-env`（默认 `SITULEARN_PUBLISH_TOKEN`） |

`publish.json` 放在 document 目录旁时，`publish` 会自动读取 `slug`。

## Docs

- [文档索引](docs/README.md)
- [总体架构](docs/architecture/system.md)
- [发布/迁移/备份/回滚 Runbook](docs/runbooks/publish-report.md)
- [iPad 真机冒烟](docs/runbooks/ipad-smoke.md)
- [部署配置](deploy/README.md)
- [SPEC-004 文档格式](docs/specs/SPEC-004-presentation-format/spec.md)

## Development

```bash
uv sync --frozen
uv run pytest
uv run ruff check src tests
uv run mypy src/situlearn/web src/situlearn/publish.py src/situlearn/cli.py
```

Web-specific tests:

```bash
uv run pytest tests/test_web_*.py tests/test_publish.py -q
```
