---
type: changelog
status: Draft
owner: alang
depends_on: []
updated_at: 2026-11-03
---

# Changelog: SPEC-002 学习报告公网发布与 iPad 播放

## [2026-11-03] - 明确 OSS bucket 与存量报告策略

- **修改类型**: Changed
- **影响范围**: `spec.md` 的 4.2 配置项、6.2 数据迁移与兼容性
- **变更原因**: 用户确认使用部署环境指定的 OSS bucket，且不迁移已有报告
- **具体内容**: `OSS_BUCKET` 由部署环境注入；存量报告不做 PVC→OSS 迁移，升级时先下架并删除本地副本，再从 Mac 重新发布；SQLite 元数据与外链 slug 保留

## [2026-11-03] - 报告存储改为阿里云 OSS

- **修改类型**: Changed
- **影响范围**: `spec.md` 的架构图、核心模块、数据流、关键选型、4.1 存储布局、4.2 配置、4.3 数据模型、4.4 接口、4.5 时序、4.6 错误码、4.8 部署资源、5.2–5.4、6.2、6.4、7.2、7.7 与附录 A3/A9
- **变更原因**: 用户要求报告本体存入阿里云 OSS，避免 K3s 节点承担报告容量与持久化责任
- **具体内容**: 报告（`report.html`、`manifest.json`、`assets/audio/`）改为 OSS 私有 bucket 上的不可变版本前缀，SQLite 元数据保留在 1 GiB 本地 PVC；服务端使用同地域内网 endpoint 与最小权限 RAM 子账号，公开访问仍经 `/r/<slug>/...` 同源代理并透传 Range；`ReportVersion.dir_path` 改为 `object_prefix`；`/readyz` 改为检查 OSS 可达；备份改为 SQLite 每日快照到 OSS；新增 `ERR_STORAGE_UNAVAILABLE`，容量与告警口径由 PVC 改为 OSS bucket；补充 PVC→OSS 的一次性迁移步骤

## [2026-11-02] - 批准进入实施

- **修改类型**: Changed
- **影响范围**: `spec.md` 与 `tasks.md` frontmatter status；`docs/specs/README.md`
- **变更原因**: 用户审批通过，确认按 SPEC-002 的任务拆解开始实施
- **具体内容**: `spec.md` 与 `tasks.md` 状态改为 `Approved`；索引同步；执行从 T1 开始。

## [2026-11-02] - 初始起草

- **修改类型**: Added
- **影响范围**: 全文
- **变更原因**: 用户希望在 iPad 上离开 Mac 继续看和听学习报告，并为未来的公开分享建立入口；现有报告只存在于本地文件系统，没有 URL、发布、下架或后台播放能力。
- **具体内容**: 建立现状与失败链，确认公网公开、每条报告独立难猜链接、Mac 构建后发布、K3s 部署、单一管理令牌、同链接覆盖可下架、前端完全重做、章节级同步、进度记忆与 PWA；定义发布包、存储布局、数据模型、接口、错误码、前端交互、K3s 资源、NFR、上线回滚与替代方案。公开版保留现有真人音频作为用户明确接受的再分发风险，列入附录 A 复核项。
