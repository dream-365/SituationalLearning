# Tasks — SPEC-004 轻量文档格式

状态：SPEC-004 已批准；T0a–T7 实现完成。T6d 的真实集群切换/回滚演练待运维执行。复选框保留为原始拆分清单，未逐项回填；完成状态以 changelog 为准。

## 依赖顺序

```text
T0a strict writer/models
 ├── T0b tolerant reader + JSON Schema
 ├── T1 Resolver
 ├── T2 Packager
 ├── T3 Migrator
 └── T4 Renderer
        └── T5 Build 管线
              ├── T6a Publish client + export
              ├── T6b Server owner/API/media/validation
              ├── T6c Web viewer/parity
              └── T6d Cutover/rollback
                    └── T7 文档与清理
```

## T0a — 严格写入模型（已完成）

- [ ] `Document` / `Meta` / `Resource` / `Section` / `TextBlock` / `ImageBlock` / `AudioBlock` / `WordBlock` / `GroupBlock`。
- [ ] 严格校验：`format`、`version=1`、必填字段、ID 规则、唯一性、资源类型匹配、`href` 必须 `media/` 且唯一、MIME、时间顺序（重叠 warning）、`word` 只在 vocabulary、`group` 深度、限额（resources 9,999）。
- [ ] `word.id` / `word.section_id` 必填；`keywords` 只含 `word_id`，同 section。
- [ ] narrative section **恰好一个** narration group；不得有第二个；顶层不得散落旁白原语；cover/summary 禁止 narration；嵌套 group 禁止 narration role。
- [ ] 任何 group 内禁止 `audio.script`；`group.script` 只在 narration group；非 narration group 带 script → 拒绝。
- [ ] `resources[].sha256` 必填；package/publish 缺失或不匹配拒绝。
- [ ] `meta.id` / `report_key`：有 source 等于 `source.sha256`；无 source 显式提供；不随机生成；两者都有时必须相等；格式 64-hex。
- [ ] 错误码覆盖 scattered-narration、script-on-non-narration、invalid-definitions、invalid-source-url、invalid-meta-id。
- [ ] `meta.labels` 写入端必填集合：19 个现有键 + `vocabulary_heading` + 5 个分类键。
- [ ] 测试：合法/非法样例、重复 ID/href、错误资源类型、`href` 违规、word/section 不一致、narration group 数量、group.script、缺失哈希、无随机 ID。

验收：真实样本通过严格写入；非法样例给出明确错误码。

## T0b — 宽容读取 + JSON Schema（已完成）

- [ ] 未知 block / 损坏 block / 未知 role / 未知 word.kind / 未知 resource.source 跳过/回退 + warning。
- [ ] 资源缺失/类型不匹配/哈希缺失或不匹配 → warning + 占位。
- [ ] `version != 1` 拒绝；未知字段忽略；labels 缺键回退。
- [ ] 错误码方向表：write / read / package / publish / compile。
- [ ] 导出 `document.schema.json`（与 Pydantic 同源）。
- [ ] 测试：unknown/malformed block、enum 回退、缺失资源、哈希、版本拒绝、schema。

验收：损坏文档仍能渲染已知部分；schema 可用于 LLM structured output。

## T1 — Resolver（已完成）

- [ ] `resolve(base, href)`：仅 `media/` 相对路径；目录、zip、HTTP 三种 base。
- [ ] RFC 3986 规则：无 scheme/netloc/query/fragment/`..`/`.`/空段/反斜杠/百分号分隔符；NFC。
- [ ] 安全：路径穿越、符号链接、大小写冲突、重复 entry。
- [ ] 测试：同一文档在目录、zip、HTTP 下解析一致；违规路径拒绝。

验收：真实样本 84/84 资源在目录与 `.situ` 下可解析；HTTP 下 84/84 返回 200。

## T2 — Packager（已完成）

- [ ] 只打包 `document.json` + `resources[*].href`；其他文件跳过并 warning。
- [ ] 路径硬化：绝对路径、`..`、反斜杠、盘符、NUL、symlink、重复 entry、大小写冲突。
- [ ] 限额：entries、单 entry 解压大小、总解压大小、压缩比。
- [ ] 确定性：排序、固定时间戳、固定压缩策略。
- [ ] **只校验哈希，不改写 `document.json`**；build/compile/migrate 写入 `sha256`。
- [ ] CLI：`situlearn package <dir> --out <file.situ>`。
- [ ] 测试：roundtrip、未引用文件、非法路径、确定性、缺失/不匹配哈希。

验收：真实样本打包成功；包内 84/84 资源存在；同一输入两次打包字节一致；包内文档与源逐字节一致。

## T3 — Migrator（已完成）

- [ ] `migrate(old_dir, out_dir)`，按 spec 4.13 字段级映射。
- [ ] **创建且只创建一个 `vocabulary` section**：`id: vocabulary`、`role: vocabulary`、`layout: grid`、title 取 `labels.vocabulary_heading`，追加在 narrative 之后。
- [ ] 每个旧 section → `role: narrative` + 恰好一个 narration group（text + audio blocks + group.script）。
- [ ] `word.audio`：`assets/audio/...` → `media/audio/...` 查找资源 ID；`unavailable`/找不到跳过 + warning。
- [ ] `section.audio_refs` 同样做路径→资源 ID 查找；找不到/`unavailable` 跳过 + warning。
- [ ] `word.section_id`：旧 `TermEntry.section_id`；无效则第一个 narrative + warning。
- [ ] `key_terms` → `keywords`：`casefold()` 精确匹配且同 section；匹配不到丢弃 + warning。
- [ ] 媒体文件计算 `sha256`；**不映射** `assets[].text_sha256`；`config.*` 丢弃并记日志。
- [ ] labels（19 + `vocabulary_heading` + 分类）来自 `ContentProfile` / `CATEGORY_LABELS`；attribution 固定三元组；`meta.language=zh-CN`、`source.language=en`、`kind=documentary` 默认。
- [ ] 固定 ID/排序；省略 `created_at`；重叠时间 warning；`vocabulary` ID 冲突时旧 section 重命名 + warning；幂等。
- [ ] `migrate-batch`：目录名 == `manifest.source.sha256`；缺失/不匹配报 `migrate/missing-source-sha256`；输出 `<out-root>/<report_key>/document.json + media/ + publish.json`；重复 key 报错；失败隔离；`--force` 覆盖。
- [ ] 测试：fixture manifest（提交到 tests）+ 真实样本；期望 8 section / 77 word / 84 resource；重复迁移字节一致；输入不被修改。

验收：真实样本迁移出 8 个 section、77 个 `word` 块、84 个资源；严格校验通过；`word.section_id` 可筛选；重复迁移结果一致；包内文档逐字节一致。

## T4 — Renderer（已完成）

- [ ] 按 block 类型分派；不读 `content_type`。
- [ ] Section role：narrative/vocabulary/cover/summary；narration group；keywords 按 `word_id` 跳转。
- [ ] 多音频块按文档顺序组成 section 播放列表；`group.script` 只显示一次；group 内 `audio.script` 被拒绝；独立 audio 块可用 `audio.script`。
- [ ] 所有文档字符串转义；markdown 清洗；`sources[].url` 仅 http/https + `rel=noopener`。
- [ ] labels/category/attribution 渲染；缺失资源占位；未知/损坏 block 跳过。
- [ ] `render <dir|.situ> --out <output-dir>`：输出目录必须不存在或为空、不得在输入内部；只含 `index.html` + `media/`。
- [ ] 测试：每种 block、播放列表、关键词跳转、转义/XSS、缺资源、离线无外部请求、输出目录约束。

验收：真实样本渲染出 8 个 section、77 张词卡、84 个播放器；离线无网络请求；无 `content_type` 分支。

## T5 — Build 管线（已完成）

- [ ] 输出 `document.json` + `media/`；默认 `index.html`，`--no-render` 关闭。
- [ ] `--package` 产出 `.situ`（不含 HTML）。
- [ ] ContentProfile 映射：section 数、narration group、terms/keywords、vocabulary、`meta.kind`、19 labels + `vocabulary_heading` + 分类、attribution、TTS 语气。
- [ ] Authoring 投影（`authoring_version: 1`）字段表与 Compiler 规则：`sections[].terms`、`casefold` 匹配、`words[].term` casefold 唯一、重复 term 拒绝、未引用 word 丢弃 + warning、空 vocabulary 编译失败、同 section 重复/跨 section 丢弃 warning、`narration.text/script` → blocks/audio、`vocabulary` title/layout、`meta.id=source.sha256`。
- [ ] `meta.labels` 25 键（19 + `vocabulary_heading` + 5 分类）。
- [ ] build/compile 写入资源 `sha256`；不随机生成 `meta.id`。
- [ ] 保留 LLM/TTS/cache 语义；`authoring_version` 进入缓存键。
- [ ] 测试：纪录片、电影、缓存命中、`--no-render`、`--package`、authoring 校验、无旧产物。

验收：真实纪录片与一部电影构建成功；文档严格校验通过；产物为 `document.json` + `media/` + `index.html`（可选 `.situ`）。

## T6a — Publish client + export（已完成）

- [ ] `publish <dir|.situ>` 上传 zip（根 `document.json` + `media/`）；不传 `index.html`。
- [ ] 发布请求 multipart：`archive` + 可选 `requested_slug`；目录读取 `publish.json` 的 slug；`.situ` 用 `--slug`。
- [ ] 目录打包复用 Packager：只含 `document.json` + 注册 href；排除 `publish.json`/`index.html`/`preview.html`。
- [ ] sidecar schema：`{"slug": "...", "published_at": "..."}`；导出 `bundle.json` / 迁移输出 `publish.json` 同 schema。
- [ ] 旧 bundle 导出工具/接口：`<export-root>/<report_key>/manifest.json + assets/... + bundle.json`（含旧 slug）。
- [ ] 报告键从 `meta.source.sha256` / `meta.id` 取，二者都无则拒绝。
- [ ] 测试：dry-run、上传、导出、旧格式拒绝、slug 保留/冲突 409/非法 422。

## T6b — Server owner / API / media / validation（已完成）

- [ ] **Owner 模型**：token→`owner_id`；`reports` 表 `UNIQUE(owner_id, report_key)`、`UNIQUE(slug)`；`report_id = uuid5(NAMESPACE_URL, owner_id:report_key)`；对象前缀 `owners/<owner_id>/reports/<report_id>/<version>/`。
- [ ] **发布路径 owner 隔离**：`get_by_key(owner_id, report_key)`、owner-scoped upsert；禁止全局 key 查询。
- [ ] **生命周期 API owner 隔离**：`GET/DELETE /api/v1/reports/{slug}` 校验 `report.owner_id == token.owner_id`；跨 owner 404；repository 用 `(owner_id, slug)`。
- [ ] **DB 迁移/引导**：创建 `owners`；回填 bootstrap owner；`reports` 重建复合唯一；生成 `report_id`；旧 slug/object_prefix 保留；启动前执行，失败拒绝启动。
- [ ] **原子发布**：先解析 `report_id`；插入 `report_versions(status=pending)`；写 `canonical.json` + `document.json`（投影）+ `media/`；单事务标记 ready + upsert reports + 切 `current_version`；失败删 prefix/pending；启动清理 24h pending 残留。
- [ ] **版本内文件**：`canonical.json` 私有、`document.json` 公开投影；公开路由不服务 canonical。
- [ ] **slug**：`requested_slug` 空闲使用、同 report 复用、其他 report 409、非法 422；默认 slug 截断 ≤64。
- [ ] 只接受新文档；旧 manifest 端点移除；API 主版本升级。
- [ ] 安装前 strict validation：schema、`version=1`、ID/引用、`href`、资源类型/MIME 白名单、限额、`resources.sha256` 校验。
- [ ] `document/hash-mismatch` 在 package/publish 为拒绝；缺失 `sha256` 拒绝。
- [ ] 公开投影：移除 `meta.id` / `meta.source.filename` / `meta.source.sha256`；canonical 文档保留在服务端。
- [ ] 路由 `/r/<slug>/document.json`、`/r/<slug>/media/...`；只服务已注册 href。
- [ ] `Content-Type` 取自 `resources.mime`；只允许 audio/image + JSON；`nosniff`。
- [ ] `requested_slug`：空闲使用；同 owner/report 复用；其他 owner 占用 409。
- [ ] 旧 `/assets/...` 308 到 `/media/...`；迁移窗口内旧路径 alias 保留 Range。
- [ ] 测试：跨 owner 覆盖/读取/删除、slug 冲突、MIME/XSS、路径、公开投影、媒体哈希、旧 URL 308、原子发布失败回滚。

## T6c — Web viewer / parity（已完成）

- [ ] 读取新文档；按 block 渲染；不保留 legacy manifest 读取。
- [ ] 保留 `/r/<slug>`、`/chapters/<id>`、`/vocabulary`（section/category 筛选）。
- [ ] 分类标签、attribution、词→section 筛选、关键词跳转与旧行为一致。
- [ ] 公开文档不含 `meta.id` / source provenance；迁移报告保持旧 slug。
- [ ] 测试：页面/章节/词表契约、筛选、移动端/播放器。

## T6d — Cutover / rollback（实现完成，演练待运维）

- [ ] 导出全部旧 bundle → `migrate-batch` → 部署新服务 → 切换 CLI。
- [ ] DB schema migration/bootstrap 演练：owners、owner_id 回填、复合唯一、report_id、旧 slug/prefix。
- [ ] 回滚演练：恢复旧服务 + DB 快照/re-pin `current_version`；旧 bundle 可读。
- [ ] 验证 SPEC-002/003/system.md 的取代说明已生效；`/assets` 308 与 slug 稳定。
- [ ] 记录演练结果与回滚窗口。

## T7 — 文档与清理（已完成）

- [ ] `README.md`：命令、产物、“发哪个文件”、owner/token。
- [ ] `docs/architecture/system.md`：Document/Container/Resolver/strict-toleration；产品产物。
- [ ] `docs/runbooks/publish-report.md`：token/owner、导出、迁移、切换、回滚、308、slug。
- [ ] 移除或标记废弃：旧 manifest/report 代码路径、双读路径、旧 fixture。
- [ ] 更新 `docs/specs/README.md` 任务链接与 SPEC-002/003 状态说明。

## 横切验收

- [ ] 真实样本：`document.json` 约 120 KB、`.situ` 约 5.3 MB；84/84 资源离线与在线可用。
- [ ] 安全：zip slip、href 穿越、非法 MIME、脚本注入、密钥泄露、跨 owner 覆盖、缺失/篡改哈希测试通过。
- [ ] 性能：文档解析 < 50 ms；媒体按需加载；`.situ` 随机访问不整包解压。
- [ ] 可观测性：构建/迁移/渲染/发布日志包含 section/block/resource 数量、validation、projection 裁剪项。
