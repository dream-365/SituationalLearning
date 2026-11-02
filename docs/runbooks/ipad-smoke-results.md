# iPad 真机冒烟结果

- 日期：2026-11-02
- 版本：situlearn 0.2.0
- 执行人：alang
- 设备：目标 iPad（iPadOS 17+，真机；具体型号未记录）
- 环境：本地局域网 HTTPS（`https://<local-lan-ip>:8443`），未部署 K3s
- 报告：`report-ve64nmjnfqdy`（《被删掉的北方文艺复兴》，8 章 / 69 词条 / 77 个音频）
- 对照清单：[ipad-smoke.md](ipad-smoke.md)

## 结果

| 步骤 | 结果 | 证据 |
| --- | --- | --- |
| 1 | 通过 | 服务版本 0.2.0；`/healthz` 与 `/readyz` 返回 200 |
| 2 | 通过 | `situlearn publish` 返回 `slug=report-ve64nmjnfqdy`；下架后重新发布返回同一 slug 且 `replaced=True` |
| 3 | 通过 | iPad 打开报告首页；服务端记录首页 200，标题与章节可读 |
| 4 | 通过 | iPad 播放章节；服务端记录音频 206 Range 请求 |
| 5 | 通过 | iPad 锁屏连续播放 10 分钟不中断 |
| 6 | 通过 | 锁屏界面暂停/继续/上一章/下一章均生效 |
| 7 | 通过 | 切到其它 App 30 秒后返回，播放位置连续 |
| 8 | 通过 | 关闭页面后重开，出现续播提示；恢复误差不超过 5 秒 |
| 9 | 通过 | 添加到主屏幕、独立窗口打开；断网后已缓存页面/音频可用；离线页可访问 |
| 10 | 通过 | 词条发音、章节/分类筛选、搜索、拖动进度均通过；下架后首页/音频/manifest 均 410；重新发布后首页 200、音频 206 |

## 服务端证据

- 首页、词表页、PWA manifest、`sw.js`、离线页、样式与播放器脚本均返回 200。
- 音频请求返回 206，包含 `Content-Range`。
- 公开页返回 `X-Robots-Tag: noindex, nofollow`、HSTS 与 CSP；`HEAD` 返回 200。
- 下架：`DELETE /api/v1/reports/report-ve64nmjnfqdy` 返回 204；随后首页、音频、manifest 均返回 410 `ERR_REPORT_GONE`。
- 重新发布：同一 slug 恢复，首页 200，音频 206。
- `/metrics`：`report_count 1`，`storage_bytes 7,224,662`。

## 本轮发现与修复

- **筛选交互问题**：首轮 iPad 测试发现章节/分类下拉切换后不会自动应用，必须手动点“筛选”。已新增 `static/filters.js`：下拉 `change` 立即提交，搜索输入 350ms 防抖后提交；同时保留无 JS 时的服务端筛选回退。修复后 iPad 复测通过。
- **图标 404**：iPad 首轮访问触发 `/apple-touch-icon.png` 与 `/favicon.ico` 404；已在页面头部增加 icon 与 apple-touch-icon 链接，指向现有 PWA 图标。

## 未覆盖项

- K3s 部署与 `kubectl kustomize` 真机/集群验证：按用户要求本轮跳过；部署资源已做静态校验。
- 真实公网域名与 TLS 证书：本轮使用本地局域网 CA；未验证公网 DNS/Traefik/cert-manager 链路。
- 多用户并发与带宽成本：未在公开分享场景下压测。
