# 学习报告发布 Runbook（发布清单）

适用版本：situlearn 0.2.2（web 发布层）
最后验证：2026-11-03，本机 macOS + 局域网 HTTPS，已验证 `/healthz` 200、报告首页 200、音频 Range 206。
相关清单：[iPad 真机冒烟](ipad-smoke.md)

本文覆盖三种发布路径，按使用频率排序：

1. **方式 A：局域网 HTTPS**（本机直接发布到 iPad，已验证；日常使用）
2. **方式 B：公网 K3s**（真正的公网 URL，需要域名、集群与镜像仓库）
3. **方式 C：本机 HTTP 开发**（只在本机浏览器验证，不用于 iPad）

---

## 0. 当前环境速查

上次发布留下并已验证可用的路径：

| 项目 | 路径 / 值 |
| --- | --- |
| 报告目录 | `reports/renaissance-p01-v1` |
| 报告标题 | 被删掉的北方文艺复兴（8 章 / 69 词条 / 77 个音频） |
| 已发布 slug | `report-ve64nmjnfqdy` |
| 本机局域网 IP | `192.0.2.10` |
| 服务数据目录 | `~/.cache/situlearn/lan-web-data-20261102` |
| 发布令牌文件 | `~/.cache/situlearn/lan-tls/publish_token` |
| TLS 证书 | `~/.cache/situlearn/lan-tls/server.crt`、`server.key`（有效期至 2027-11-02） |
| iPad 安装用 CA | `~/.cache/situlearn/lan-tls/public/situlearn-ca.crt` |

> 关键点：**只要 `SITULEARN_DATA_DIR` 指向上面那个数据目录，重复发布就会命中同一条报告，slug 和 URL 都不变。** 换数据目录会生成新 slug，旧 URL 随即失效。

---

## 1. 发布前检查清单

- [ ] 用的是 **源码目录里的 0.2.2**，不是已安装的 v0.1.3 wheel：v0.1.3 不含 `publish` 子命令。
- [ ] `uv run situlearn publish <报告目录> --server <URL> --dry-run` 通过（只校验和打包，不联网）。
- [ ] 报告目录包含 `manifest.json` 与 `assets/audio/`，且 manifest 引用的音频都存在。
- [ ] 服务进程在跑，且 `SITE_BASE_URL` 与 iPad 实际访问的地址一致。
- [ ] 发布令牌与服务端 `PUBLISH_TOKEN` 一致。

快速自检：

```bash
cd /Users/alang/Workspace/Situational-Eng-Learning
uv run situlearn --version
uv run situlearn publish reports/renaissance-p01-v1 \
  --server https://192.0.2.10:8443 --dry-run
```

期望输出形如：

```text
dry-run: report_key=... title=被删掉的北方文艺复兴 size=6668075
```

---

## 2. 方式 A：局域网 HTTPS 发布（日常路径）

iPad 需要 HTTPS 才能注册 Service Worker、添加到主屏幕并离线缓存；用 Mac 的局域网 IP + 本地 CA 即可，不必部署集群。

### 2.1 启动服务（终端 1）

```bash
cd /Users/alang/Workspace/Situational-Eng-Learning

export PUBLISH_TOKEN="$(cat "$HOME/.cache/situlearn/lan-tls/publish_token")"
export SITE_BASE_URL="https://192.0.2.10:8443"
export SITULEARN_DATA_DIR="$HOME/.cache/situlearn/lan-web-data-20261102"

uv run uvicorn situlearn.web.app:app \
  --host 0.0.0.0 \
  --port 8443 \
  --ssl-keyfile "$HOME/.cache/situlearn/lan-tls/server.key" \
  --ssl-certfile "$HOME/.cache/situlearn/lan-tls/server.crt"
```

验证服务：

```bash
curl -ksS -o /dev/null -w "healthz=%{http_code}\n" https://192.0.2.10:8443/healthz
curl -ksS -o /dev/null -w "report=%{http_code}\n" https://192.0.2.10:8443/r/report-ve64nmjnfqdy
```

- 期望：`healthz=200`、`report=200`。
- 服务必须**一直开着**；终端关闭、Mac 睡眠或换 Wi-Fi 都会让 iPad 打不开。要长时间挂着可以另开一个终端执行 `caffeinate -s`。

### 2.2 发布报告（终端 2）

```bash
cd /Users/alang/Workspace/Situational-Eng-Learning

SITULEARN_PUBLISH_TOKEN="$(cat "$HOME/.cache/situlearn/lan-tls/publish_token")" \
  uv run situlearn publish reports/renaissance-p01-v1 \
  --server https://192.0.2.10:8443
```

期望输出：

```text
published: https://192.0.2.10:8443/r/report-ve64nmjnfqdy
slug=report-ve64nmjnfqdy version=... replaced=True
```

- `replaced=True` 表示覆盖了同一份报告的旧版本，URL 不变。
- 换一份字幕构建的新报告会得到新 `report_key`，因此是新 slug。
- 发布是“先上传新版本、再原子切换”；中途失败不会破坏当前可访问的旧版本。

### 2.3 iPad 打开

Safari 打开：

```text
https://192.0.2.10:8443/r/report-ve64nmjnfqdy
```

首次使用或换 iPad 时，需要让 iPad 信任本地 CA：

1. 让 iPad 能下载 `situlearn-ca.crt`（AirDrop 最省事；或临时起一个 HTTP 服务）：
   ```bash
   python3 -m http.server 8444 \
     --directory "$HOME/.cache/situlearn/lan-tls/public"
   ```
   iPad Safari 打开 `http://192.0.2.10:8444/situlearn-ca.crt` 并安装描述文件。
2. iPad 设置 → 通用 → 关于本机 → 证书信任设置 → 打开 “SituLearn Local CA” 完全信任。
3. 重新打开报告 URL，确认没有证书警告。

完整播放验收见 [iPad 真机冒烟](ipad-smoke.md)。

### 2.4 停止服务

终端 1 按 `Ctrl+C`。

---

## 3. 方式 B：公网 K3s 发布

目标：把报告发布到 `https://<你的域名>/r/<slug>`，不再依赖 Mac 开机。

### 3.1 部署前准备

- [ ] 一个真实域名，DNS 指向 K3s 入口。
- [ ] Traefik Ingress 可用；TLS 证书（cert-manager 或已有 Secret `situlearn-tls`）。
- [ ] 可用的镜像仓库，能推送 `ghcr.io/dream-365/situlearn-web:<tag>`。
- [ ] 本机有 `kubectl` 和容器构建工具（当前 Mac 上两者都未安装）。
- [ ] 把 `deploy/k8s/overlays/prod/kustomization.yaml` 里的 `situlearn.example.com` 换成真实域名，`SITE_BASE_URL` 同步替换。

### 3.2 构建并推送镜像

```bash
docker build -t ghcr.io/dream-365/situlearn-web:0.2.2 .
docker push ghcr.io/dream-365/situlearn-web:0.2.2
```

若本机没有 Docker，可在 CI 或其他构建机上执行，再把 tag 写回 overlay。

### 3.3 创建命名空间与令牌

```bash
kubectl create namespace situlearn --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic situlearn-secrets -n situlearn \
  --from-literal=PUBLISH_TOKEN="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -
```

记下这个令牌，发布时要用同一个值。`deploy/k8s/base/secret.yaml` 里的占位值不可直接用于生产。

### 3.4 应用并等待就绪

```bash
kubectl diff -k deploy/k8s/overlays/prod
kubectl apply -k deploy/k8s/overlays/prod
kubectl rollout status deployment/situlearn -n situlearn --timeout=10m
```

### 3.5 验收服务

```bash
curl -fsS https://<你的域名>/healthz
curl -fsS https://<你的域名>/readyz
curl -fsS https://<你的域名>/metrics | head
```

### 3.6 发布报告

```bash
SITULEARN_PUBLISH_TOKEN="<上一步创建的令牌>" \
  uv run situlearn publish reports/renaissance-p01-v1 \
  --server https://<你的域名>
```

然后在 iPad 打开输出的 URL，按 [iPad 真机冒烟](ipad-smoke.md) 的 10 步走一遍。

### 3.7 回滚

- 单条报告有问题：先下架该报告（见第 5 节）。
- 整体有问题：把 `PUBLISH_ENABLED` 置为 `"false"` 并回滚镜像 tag，再重新 apply。

---

## 4. 方式 C：本机 HTTP 开发

只用于本机浏览器调试；iPad 与 PWA 离线能力不适用。

```bash
export PUBLISH_TOKEN=dev-token
export SITE_BASE_URL=http://localhost:8000
export SITULEARN_DATA_DIR="$HOME/.cache/situlearn/web-dev"

uv run uvicorn situlearn.web.app:app --host 0.0.0.0 --port 8000
```

另一个终端：

```bash
SITULEARN_PUBLISH_TOKEN=dev-token \
  uv run situlearn publish reports/renaissance-p01-v1 \
  --server http://localhost:8000
```

---

## 5. 发布后验收清单

- [ ] `/healthz`、`/readyz` 返回 200。
- [ ] 公开首页 200，章节数与词条数与本地报告一致。
- [ ] 音频请求返回 **206**，带 `Content-Range`：
      `curl -s -o /dev/null -w "%{http_code}\n" -r 0-99 https://<base>/r/<slug>/assets/audio/sec-01-01.mp3`
- [ ] 重复发布同一报告：返回同一 slug，且 `replaced=True`，不新增报告。
- [ ] iPad 冒烟 10 步通过（锁屏播放、切 App、续播、主屏幕、离线）。
- [ ] 需要下架时，公开 URL 返回 410。

### 下架报告

```bash
curl -sS -X DELETE \
  -H "Authorization: Bearer $(cat "$HOME/.cache/situlearn/lan-tls/publish_token")" \
  -o /dev/null -w "%{http_code}\n" \
  https://192.0.2.10:8443/api/v1/reports/report-ve64nmjnfqdy
```

期望 204；随后首页、音频、manifest 均返回 410。重新发布可恢复同一 slug。

### 查看服务端状态

```bash
curl -ksS https://192.0.2.10:8443/metrics | head
```

关注 `publish_total`、`report_count`、`storage_bytes`。

---

## 6. 常见问题

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| `situlearn: invalid choice: 'publish'` | 用的是已安装的 v0.1.3 wheel | 在源码目录用 `uv run situlearn ...`；v0.2.0 wheel 发布后再装 |
| `401 ERR_PUBLISH_UNAUTHORIZED` | 发布令牌与服务端 `PUBLISH_TOKEN` 不一致 | 两边都从同一个令牌文件读取 |
| `413` | 报告超过 `MAX_REPORT_BYTES`（默认 100 MiB） | 检查是否误打包了无关大文件 |
| `422` / `ERR_LOCAL_ASSET` | manifest 引用的音频缺失或为空 | 重新构建报告，或补齐 `assets/audio/` |
| 发布后 URL 变了 | `SITULEARN_DATA_DIR` 与上次不同 | 指回原来的数据目录，如 `lan-web-data-20261102` |
| iPad 打不开 | 服务没开、Mac 睡眠、换 Wi-Fi 导致 IP 变化、防火墙拦截 8443 | `curl -k` 自测；确认 IP；必要时改证书 SAN |
| Safari 证书警告 | iPad 未信任本地 CA | 重新安装 `situlearn-ca.crt` 并开启完全信任 |
| 端口被占用 | 上次的 uvicorn 未退出 | `lsof -nP -iTCP:8443 -sTCP:LISTEN` 后结束进程 |
| 锁屏后音乐停 | 未用 HTTPS / 未通过 Safari 播放 / 系统限制 | 确认 URL 是 `https://`，按冒烟清单第 5 步复测 |

---

## 7. 一页版清单（可打印）

```text
[ ] 终端 1：启动 uvicorn（SITULEARN_DATA_DIR=lan-web-data-20261102，8443，TLS）
[ ] curl /healthz -> 200
[ ] 终端 2：situlearn publish reports/renaissance-p01-v1 --server https://192.0.2.10:8443
[ ] 输出 slug=report-ve64nmjnfqdy，replaced=True
[ ] curl 公开首页 -> 200
[ ] curl Range 音频 -> 206
[ ] iPad Safari 打开 URL，播放一章
[ ] （每次正式使用）按 ipad-smoke.md 走 10 步
[ ] 用完 Ctrl+C 停服务
```
