---
type: tasks
status: In Progress
owner: alang
depends_on: []
spec: ./spec.md
spec_sha256: "79396c2a28d0cdebb77d0a8f51f5386f0fcba5c1de587ca3c890f2ebfa066dfd"
updated_at: 2026-11-03
---

# 学习报告公网发布与 iPad 播放 执行拆解

| ID | 任务 | 覆盖 | 依赖 | 写入 | 完成标准 | 验证 |
|---|---|---|---|---|---|---|
| T1 | 搭起 FastAPI 服务骨架、配置与健康检查 | G5 | — | pyproject.toml, uv.lock, src/situlearn/web/app.py, src/situlearn/web/config.py, src/situlearn/web/observability.py, tests/test_web_health.py | 本地启动后 /healthz 与 /readyz 均返回 200；日志为 JSON Lines 且含 request_id；配置从环境变量读取 | bash -c 'uv run pytest tests/test_web_health.py -q' |
| T2 | 实现 OSS 不可变版本存储与 SQLite 原子切换 | G3 | T1 | src/situlearn/web/storage.py, src/situlearn/web/repository.py, tests/test_web_storage.py | 报告写入 OSS `object_prefix`；上传中断、校验失败、OSS 写入失败、事务失败四种注入下 current_version 不变且旧版本可读；同一 report_key 重复提交不新增报告 | bash -c 'uv run pytest tests/test_web_storage.py -q' |
| T3 | 实现发布/下架 API 与令牌认证 | G3 | T2 | src/situlearn/web/api.py, src/situlearn/web/auth.py, tests/test_web_publish_api.py | 无令牌 401；合法发布 201；重复发布 200 且 replaced=true；下架 204 后公开状态为 unpublished；超限 413；缺资产 422 | bash -c 'uv run pytest tests/test_web_publish_api.py -q' |
| T4 | 实现 situlearn publish 打包、dry-run 与上传 | G1 | T3 | src/situlearn/publish.py, src/situlearn/cli.py, tests/test_publish.py | --dry-run 不发起网络请求且校验通过；真实发布输出 slug 与 URL；同一报告重复发布返回同一 slug | bash -c 'uv run pytest tests/test_publish.py -q' |
| T5 | 实现服务端渲染的报告首页、章节页与词表页 | G4 | T2 | src/situlearn/web/render.py, src/situlearn/web/templates/, tests/test_web_render.py | 三页渲染全部 sections 与 terms；公开 HTML 不含 config、source.filename、report_id、版本号 | bash -c 'uv run pytest tests/test_web_render.py -q' |
| T6 | 补齐响应式样式、触控尺寸与可访问性 | G4 | T5 | src/situlearn/web/static/styles.css, tests/test_web_accessibility.py | 320/375/768/1024/1366 px 无横向滚动；主要触控目标 ≥44×44 px；正文对比度 ≥4.5:1；宽度扫描结果记录在测试报告中 | bash -c 'uv run pytest tests/test_web_accessibility.py -q' |
| T7 | 实现播放器、Media Session 与进度记忆 | G2 | T5 | src/situlearn/web/static/player.js, tests/test_web_player_contract.py | 单例 audio 按章节播放；注册 play/pause/previoustrack/nexttrack/seekto；进度写入 situlearn:progress:<slug> | bash -c 'uv run pytest tests/test_web_player_contract.py -q' |
| T8 | 实现 PWA 清单、Service Worker 与离线页 | G2 | T7 | src/situlearn/web/pwa.py, src/situlearn/web/static/sw.js, src/situlearn/web/static/icons/, tests/test_web_pwa.py | 每报告 manifest 的 start_url=/r/{slug}、scope=/r/{slug}/；sw.js 预缓存外壳并缓存音频；离线页可访问 | bash -c 'uv run pytest tests/test_web_pwa.py -q' |
| T9 | 构建容器镜像与 K3s/Kustomize 部署资源 | G5 | T1, T3, T5 | Dockerfile, .dockerignore, deploy/k8s/, tests/test_deploy_manifests.py | kubectl kustomize 输出含 Deployment、Service、Ingress、SQLite 小 PVC、ConfigMap、Secret（含 OSS 凭据）、CronJob 与允许 OSS 出口的 NetworkPolicy；探针、资源限制与 OSS 配置齐全 | bash -c 'kubectl kustomize deploy/k8s/overlays/prod > /tmp/situlearn.yaml && uv run pytest tests/test_deploy_manifests.py -q' |
| T10 | 增加指标端点与备份脚本 | G5 | T1 | src/situlearn/web/metrics.py, src/situlearn/web/backup.py, tests/test_web_metrics.py | /metrics 返回 publish_total、storage_bytes、report_count、oss_request_errors_total；备份脚本生成 SQLite 一致性快照并上传到 OSS `backups/` | bash -c 'uv run pytest tests/test_web_metrics.py -q' |
| T11 | 写本地端到端测试覆盖发布、播放与下架 | G1 | T4, T5, T7, T8 | tests/test_web_e2e.py | 本地发布样例后首页 200；Range 音频 206；下架后 410；重复发布不新增报告 | bash -c 'uv run pytest tests/test_web_e2e.py -q' |
| T12 | 编写 iPad 真机冒烟与锁屏播放 runbook | G2 | T8, T9 | docs/runbooks/ipad-smoke.md | runbook 含 10 步，覆盖锁屏 10 分钟、切 App、PWA 离线、进度恢复；每步有预期结果与失败判据 | docs/runbooks/ipad-smoke.md |
| T13 | 更新 README 的发布、部署与 iPad 使用说明 | G1 | T4, T9, T12 | README.md | README 含 situlearn publish、K3s 部署与 iPad 主屏幕使用三节，命令可直接复制执行 | bash -c 'grep -q "situlearn publish" README.md' |
