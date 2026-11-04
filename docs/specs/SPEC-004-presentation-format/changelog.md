# Changelog

## 2026-11-04 — 实现完成

- T0a/T0b：document 模型、strict writer / tolerant reader、JSON Schema。
- T1/T2：目录/.situ/HTTP Resolver、确定性 Packager。
- T3/T4：旧 manifest → document 迁移、派生 HTML Renderer。
- T5：build 输出 `document.json + media/ + index.html`，支持 `--no-render` / `--package`。
- T6a–T6c：publish client、owner 隔离 API/storage、document/media 公共路由、PWA link。
- T6d/T7：旧 bundle 导出、DB 迁移/引导、README/architecture/runbook 更新、移除旧 `report.py`。
- 验证：214 passed, 2 skipped；ruff/mypy 通过；真实字幕端到端 publish/render/media 通过。
- 剩余：T6d 的真实 K3s 切换与回滚演练需运维执行。

## 2026-11-04 — Approved

- 用户批准 SPEC-004，状态改为 Approved。
- SPEC-002/003 转为“部分被 SPEC-004 取代”；system.md、README、SPEC-002 §6.2 同步生效。
- 下一步：执行 T0a（严格写入模型）；实现必须按本 spec，不得擅自扩展格式。

## 2026-11-04 — 第六轮收口（最终核对处置）

- Owner 发布路径：`get_by_key(owner_id, report_key)`、owner-scoped upsert；`report_id = uuid5(owner_id:report_key)` 在写对象前确定。
- 原子发布：`report_versions(status=pending)` → 写 `canonical.json` + `document.json`（投影）+ `media/` → 单事务 ready + current_version；失败清理；启动清理 24h pending 残留。
- 版本内文件明确：`canonical.json` 私有、`document.json` 公开投影。
- slug：`requested_slug` 409/422；默认 slug 截断 ≤64；sidecar schema `{"slug","published_at"}`；目录打包用 Packager 排除 sidecar/HTML。
- 错误码/读取：missing-hash read warning；group 内 audio.script read warning；invalid-id-source 与 invalid-meta-id 拆分；新增 vocabulary/keywords/word.id/slug/migrate 错误码。
- Authoring：`words[].term` 用 casefold 唯一。
- migrate-batch：缺 `source.sha256` 报 `migrate/missing-source-sha256`。
- 取代说明改为“SPEC-004 批准后生效”，更新 updated_at 与 SPEC-002 §6.2。
- 下一步：请用户批准；批准前不写实现代码。

## 2026-11-04 — 第五轮收口（定向终审处置）

- B1+：owner 生命周期 API 隔离（GET/DELETE 按 `(owner_id, slug)`，跨 owner 404）；原子发布（先写新 prefix，单事务切换 `current_version`）；DB 迁移/引导（owners、owner_id 回填、复合唯一、report_id、旧 slug/prefix 保留）。
- B2+：发布 wire contract：multipart `archive` + `requested_slug`；目录读 `publish.json`，`.situ` 用 `--slug`；导出 `bundle.json` 带旧 slug；`migrate-batch` 输出 `publish.json`。
- M2：`document/hash-mismatch` 在 package/publish 改为拒绝；缺失 `sha256` 拒绝。
- M3：authoring 空 vocabulary 编译失败；同 section 重复/跨 section 词 warning；字段表补全。
- M7：非 narration group 的 `group.script` 拒绝，新增 `script-on-non-narration-group`。
- minors：错误码补齐（scattered/definitions/source-url/meta-id/style/authoring）；25 labels 在 §6.3/Appendix B/§4.13 一致；system.md/README/frontmatter 取代标记；`section.audio_refs` 找不到跳过；`meta.id` 的 source 定义；308 Range 说明；cover/summary/nested narration 限制。
- 下一步：请用户批准；批准前不写实现代码。

## 2026-11-04 — 第四轮修订（第三轮评审处置）

- B1：新增 4.15 完整 owner 模型：token→owner、`UNIQUE(owner_id, report_key)`、`UNIQUE(slug)`、`report_id`、owner-scoped 对象前缀、slug 保留、发布校验顺序、zip 上传信封。
- M1：公开投影同时移除 `meta.id` / `meta.source.sha256`，key 不再公开。
- M2：`resources[].sha256` 改为必填；build/compile/migrate 计算；package/publish 校验；新增 `document/missing-hash`。
- M3：authoring 增加字段表、casefold 匹配、重复/未引用词规则、narration→blocks/audio、vocabulary title/layout、meta.id 来源。
- M4：narrative 必须恰好一个 narration group；新增 `duplicate-narration-group`。
- M5：迁移补 `word.audio` 路径→资源 ID、媒体 sha256、narrative group 包装、attribution 常量、vocabulary ID 冲突、batch 校验/force。
- M6：`migrate-batch` 目录名==source.sha256、输出重叠、失败隔离、`publish.json` slug。
- M7：`group.script` 只允许 narration group；任何 group 内禁止 `audio.script`。
- M8：authoring 契约补全；见上。
- M9：SPEC-004 取代 SPEC-002/003 相关契约；已给 `system.md`、SPEC-002、SPEC-003 加取代说明；`/assets` 用 308。
- minors：labels 25 键、attribution 常量、错误码补全、`meta.id` 校验、发布信封、vocabulary ID 冲突、资源/entry 限额、enum 回退。
- 下一步：定向终审；批准前不写实现代码。

## 2026-11-04 — 第三轮修订（第二轮评审处置）

- B1：publish token 为信任边界；`report_key` 按 owner 隔离；服务端不重算 source sha；公开投影移除 `source.filename`/`source.sha256`。
- B2：迁移强制创建固定 `vocabulary` section（`id: vocabulary`、`role: vocabulary`、`layout: grid`）。
- B3：authoring 投影增加 `sections[].terms`；Compiler 按首个 section 填 `word.section_id`。
- M1/M2：`word.id` 必填；`keywords` 只含 `word_id`；`word.section_id` 必须解析且与 keyword 同 section。
- M3：build/compile 写入 `sha256`；package/publish 只校验，不改写文档。
- M4：服务端安装前 strict validation + MIME 白名单 + `nosniff`。
- M5：迁移表修正（无 `lemma`、`unavailable` 跳过、labels/attribution 来自代码常量、重叠 warning）。
- M6：`migrate-batch` 导出/输出布局与失败隔离。
- M7：narration group 只允许 `group.script`。
- M8：authoring schema 完整契约。
- M9：SPEC-004 取代 SPEC-002/003 相关契约；`/assets` 301 到 `/media/`；T7 更新 system.md 与索引。
- m1–m8：错误码方向表、labels 写入集合、entry 限额、enum 回退、公开投影、render 输出约束、ID/href 唯一、移除随机 `meta.id`。
- 下一步：第三次独立评审；批准前不写实现代码。

## 2026-11-04 — 外部评审修订（全部采纳）

- 两份独立评审（工程/架构、产品/格式）的发现全部处理；详见 spec 附录 E。
- 5 个 release blockers：`meta.id`/`report_key`、`word.section_id`、build 默认 `index.html`、`render` 目录输出、导出/migrate-batch 与回滚 re-pin。
- 格式决策：`section.role`；`word` 只在 vocabulary；`keywords` 用 `{term, word_id}`；多元素旁白强制 `group`；移除 `hero` 与保留 block；19 个 labels 全量映射；`meta.language` 与 `source.language` 拆分；LLM 内容投影 authoring schema；v1 只允许 `media/` 相对 href、绝对 URL Deferred。
- 精度项：strict writer / tolerant reader 分开；资源类型匹配；RFC 3986 href；zip 硬化与限额；字段级迁移表（禁止 `text_sha256`）；确定性打包；所有字符串转义；公开 `meta.source.filename` 裁剪；服务端校验 `report_key`。
- `tasks.md` 重排：T0a/T0b、T6a–T6d，补 export/rollback/serving/limits。
- 下一步：第二次独立评审；批准前不写实现代码。

## 2026-11-04 — 外部评审中

- 用户要求先让外部声音评审设计文档，暂缓实现。
- spec 状态从 Approved 改为 Draft（评审中）。
- T0 实现已从 worktree 撤回；草稿保留在 `/tmp/situlearn-document-t0-draft.py`，不在仓库。
- 评审材料使用 `spec.md` 原文；评审完成后更新 spec 并重新批准。

## 2026-11-04 — Approved

- 用户批准 SPEC-004，状态改为 Approved。
- 下一步：拆 tasks、进入实现；implementation 必须按本 spec 执行。

## 2026-11-04 — 规格收尾

- 关闭附录 C 全部开放项：`version=1`、`media/` 仅推荐、`labels` 可选、`definitions` 语言键对象、`group.role` 可选、绝对 `href` 读取端可显式允许、legacy Web 读取不保留、`report_key` 优先级、`resources[].source`。
- 确定章节默认策略：叙事 section 只放 `keywords`，完整 `word` 块集中在生词本。
- 确定 `audio_status` / `warnings` 不进入文档：可用性由 `audio_refs` 推导，warnings 只进日志。
- 更新发布/迁移/回滚：Web 只接受新文档，旧 bundle 必须先 `migrate` 再重新发布；迁移先于服务切换。
- 更新附录 D：真实样本发现的 3 个缺口全部关闭。

## 2026-11-04 — 真实样本验证

- 用 913 条 cue / 58.7 分钟的真实纪录片字幕验证格式：7 个叙事章节、77 个词条、84 个音频。
- 转换结果：8 个 section、77 个 `word` 块、84 个资源；`document.json` 122,666 bytes，`.situ` 5,607,474 bytes。
- 包内文档逐字节一致，84/84 资源在包内与 HTTP 下均可解析，无重复 `word` 块。
- 记录 3 个待决策缺口：资源来源 `audio_source` 的归宿、章节内联词卡 vs `keywords`、`audio_status`/`warnings` 是否保留。
- 按 `CLAUDE.md` 的军规，spec 获批前不写实现代码；验证脚本为一次性原型，未进入仓库。

## 2026-11-04 — Draft（彻底替换版）

- 推翻上一版“manifest + 展示 JSON”的增量方案，改为轻量文档格式 `situlearn.document`。
- 明确 `document.json` 是唯一内容真相；`.situ` 只是同一份 JSON + 媒体的 zip 容器。
- 资源只使用相对 `href`：包内相对 zip 根解析，在线相对文档 URL 解析；同一份 JSON 不改即可两用。
- 文档结构为 `meta` / `resources` / `sections[] → blocks[]`。
- 元素只定义 `text`、`image`、`audio`、`word` 四个原语，加可选 `group` 容器。
- `word` 块自包含；不做词条注册表。
- `manifest.json` / `report.html` 不再是正式产物：`build` 产出文档与媒体，`package` 打 `.situ`，`render` 生成派生 HTML，`migrate` 迁移旧报告。
- `situlearn publish` 上传文档与媒体；Web viewer 读取同一份文档。
- 记录 EPUB 3.3、RWPM、IIIF、H5P、OPF、deck-spec、MulmoScript、OpenMAIC、Portable Text、Editor.js、Podcasting 2.0、WebVTT、openZIM 的调研结论与许可证提示。
