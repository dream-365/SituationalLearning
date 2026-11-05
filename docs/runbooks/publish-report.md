# 学习报告发布与迁移 Runbook

适用版本：situlearn 0.2.2 + SPEC-004 文档格式
最后验证：2026-11-04（本机 HTTP、真实 913-cue 样本、document/media 路由）
相关：[iPad 真机冒烟](ipad-smoke.md)、[部署配置](../../deploy/README.md)

> 旧版 `manifest.json + assets/` 发布流程已废弃。发布输入是 **document 目录**或 `.situ`；
> 公开媒体路由是 `/r/<slug>/media/...`，旧 `/r/<slug>/assets/...` 仅做 308 重定向。

## 0. 前置检查

- [ ] `document.json` 存在，且 `resources[*].href` 都指向 `media/...`
- [ ] 媒体文件存在，`resources[*].sha256` 与实际字节一致
- [ ] 25 个 `meta.labels` 键完整（build/migrate 自动填充）
- [ ] `meta.source.sha256` 或 `meta.id` 是 64 位小写 hex
- [ ] 服务端与发布端使用同一个 token；多 owner 时 token 在 `PUBLISH_TOKENS` 中
- [ ] `SITE_BASE_URL` 与 iPad/浏览器实际访问地址一致

快速自检：

```bash
uv run situlearn publish reports/demo --server https://host --dry-run
```

期望看到 `dry-run: report_key=... title=... size=... slug=...`。

---

## 1. 本地 HTTP 开发

```bash
export PUBLISH_TOKEN=dev-token
export SITE_BASE_URL=http://localhost:8000
export SITULEARN_DATA_DIR="$HOME/.cache/situlearn/web-dev"

uv run uvicorn situlearn.web.app:app --host 0.0.0.0 --port 8000
```

另一个终端：

```bash
SITULEARN_PUBLISH_TOKEN=dev-token \
  uv run situlearn publish reports/demo --server http://localhost:8000
```

验证：

```bash
curl -s -o /dev/null -w 'home=%{http_code}\n' http://localhost:8000/r/<slug>
curl -s -o /dev/null -w 'doc=%{http_code}\n'  http://localhost:8000/r/<slug>/document.json
curl -s -o /dev/null -w 'media=%{http_code}\n' http://localhost:8000/r/<slug>/media/audio/<file>
```

---

## 2. 局域网 HTTPS（iPad）

iPad 需要 HTTPS 才能安装 PWA/Service Worker。用本机局域网 IP + 本地 CA：

```bash
export PUBLISH_TOKEN="$(cat "$HOME/.cache/situlearn/lan-tls/publish_token")"
export SITE_BASE_URL="https://192.0.2.10:8443"
export SITULEARN_DATA_DIR="$HOME/.cache/situlearn/lan-web-data-20261104"

uv run uvicorn situlearn.web.app:app \
  --host 0.0.0.0 --port 8443 \
  --ssl-keyfile "$HOME/.cache/situlearn/lan-tls/server.key" \
  --ssl-certfile "$HOME/.cache/situlearn/lan-tls/server.crt"
```

发布：

```bash
SITULEARN_PUBLISH_TOKEN="$(cat "$HOME/.cache/situlearn/lan-tls/publish_token")" \
  uv run situlearn publish reports/demo --server https://192.0.2.10:8443
```

iPad 首次访问前按 [iPad 冒烟](ipad-smoke.md) 安装并信任 CA。

---

## 3. 公网 K3s

### 3.1 选择 overlay

- `deploy/k8s/overlays/prod/`：ghcr 镜像，未配置 OSS，服务回退到 PVC 本地对象存储。适合单机/试验。
- `deploy/k8s/overlays/prod-oss/`：阿里云镜像 + OSS 配置。生产推荐。

两个 overlay 的 host、镜像 tag、`SITE_BASE_URL` 都要按实际环境替换。镜像 tag 当前与 `pyproject.toml` 一致：`0.2.2`。

### 3.2 创建 Secret

`prod`（本地存储）：

```bash
kubectl create secret generic situlearn-secrets -n situlearn \
  --from-literal=PUBLISH_TOKEN="$PUBLISH_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```

`prod-oss`（OSS）：

```bash
kubectl create secret generic situlearn-secrets -n situlearn \
  --from-literal=PUBLISH_TOKEN="$PUBLISH_TOKEN" \
  --from-literal=OSS_ACCESS_KEY_ID="$OSS_ACCESS_KEY_ID" \
  --from-literal=OSS_ACCESS_KEY_SECRET="$OSS_ACCESS_KEY_SECRET" \
  --dry-run=client -o yaml | kubectl apply -f -
```

`deployment.yaml` 的 OSS secret ref 是 optional 的；未配置 OSS 时使用本地对象存储。

### 3.3 应用与验收

```bash
kubectl diff -k deploy/k8s/overlays/prod-oss
kubectl apply -k deploy/k8s/overlays/prod-oss
kubectl rollout status deployment/situlearn -n situlearn --timeout=10m

curl -fsS https://<域名>/healthz
curl -fsS https://<域名>/readyz
curl -fsS https://<域名>/metrics | head
```

发布：

```bash
SITULEARN_PUBLISH_TOKEN="$PUBLISH_TOKEN" \
  uv run situlearn publish reports/demo --server https://<域名>
```

---

## 4. 旧报告迁移

### 4.1 本地旧报告

```bash
uv run situlearn migrate reports/old --out reports/migrated
uv run situlearn render reports/migrated --out reports/migrated-html
```

### 4.2 已发布旧 bundle

```bash
# 1. 从旧服务数据目录导出 manifest bundles
uv run situlearn export-bundles \
  --data-dir ~/.cache/situlearn/web-dev \
  --out exports/bundles

# 2. 批量迁移；输出 publish.json 保留旧 slug
uv run situlearn migrate-batch exports/bundles --out reports/migrated

# 3. 重新发布（目录里有 publish.json 时自动带 requested_slug）
uv run situlearn publish reports/migrated/<report_key> --server https://<域名>
```

旧报告里没有对应词卡的 `key_terms` 会被丢弃并写 warning；这是当前格式的取舍。

---

## 5. 切换与回滚

### 5.1 切换顺序

1. 停止旧发布。
2. 导出旧 bundle（4.2 第 1 步）。
3. `migrate-batch` 生成新文档。
4. 部署新服务端（仓库迁移在启动时执行：`owners`、`owner_id` 回填、复合唯一键、`document_*` 列）。
5. 重新发布迁移后的报告，`publish.json` 保留旧 slug。
6. 验证旧 URL 301/308/200（旧 `/assets` 308 到 `/media`）。

### 5.2 回滚

- 保留旧镜像 tag、DB 备份与对象存储中的旧 bundle。
- 恢复旧服务前，先把 `reports.current_version` re-pin 到迁移前版本；或直接恢复 DB 快照。
- 新文档不删除；旧服务不读取即可。
- 回滚窗口内不要清理 `situlearn-data` PVC/OSS 旧前缀。

### 5.3 上线验证

```bash
curl -fsS https://<域名>/healthz
curl -fsS https://<域名>/r/<slug>/document.json | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(d["format"], len(d["sections"]))'
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
  https://<域名>/r/<slug>/media/audio/<file>
```

公开 `document.json` 不应出现 `meta.id`、`meta.source.filename`、`meta.source.sha256`。

---

## 6. 备份与恢复

### 6.1 本地

```bash
uv run python -m situlearn.web.backup --data-dir <data> --backup-dir <backup> --keep-days 7
```

### 6.2 OSS

配置 `OSS_*` 后：

```bash
uv run python -m situlearn.web.backup --keep-days 30
```

会写 `backups/situlearn-<UTC>.sqlite3` 并清理过期备份。

### 6.3 K3s

`deploy/k8s/base/cronjob.yaml` 每天 03:17 执行。使用 `prod-oss` 时备份写 OSS；使用 `prod` 时写 `situlearn-backup` PVC 的 `/backup`。恢复时：

1. 停服务。
2. 用最新 SQLite 快照替换 `<data>/situlearn.sqlite3`（OSS 快照先下载）。
3. 确保对象存储中的报告前缀仍存在。
4. 启动服务，`/readyz` 200 后抽查 `/r/<slug>` 与 `/media`。

---

## 7. 常见问题

| 现象 | 检查 |
| --- | --- |
| `ERR_LOCAL_DOCUMENT` | 目录里没有 `document.json`；旧报告先 `migrate` |
| `ERR_LOCAL_MANIFEST` | 旧版发布客户端/旧报告；升级 CLI 或先迁移 |
| 409 slug conflict | `requested_slug` 被其他 report 占用；换 slug 或先下架 |
| 404 media | 请求的路径不在 `resources[*].href` 中 |
| `/assets/...` 308 | 预期；新路径是 `/media/...` |
| 410 | 报告已 unpublish；重新 publish 即可 |
| 503 | `/readyz` 看 data/object store 依赖 |
