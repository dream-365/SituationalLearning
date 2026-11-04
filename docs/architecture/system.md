---
type: architecture
status: Approved
owner: alang
depends_on: []
updated_at: 2026-11-04
---

# 情景学习 总体架构

> **部分被 SPEC-004 取代（2026-11-04 生效）**：正式产物改为 `document.json` + `media/`（可选派生 `index.html` 与 `.situ` 包）；`manifest.json` / `report.html` 不再是正式产物。报告格式、离线/在线资源解析、发布与 owner 契约以 [SPEC-004](../specs/SPEC-004-presentation-format/spec.md) 为准。本文件其余架构描述仍有效。

## 1. 系统定位

本系统面向个人与少量同类英语学习者：输入一份英文纪录片或剧情电影的 `.srt` 字幕，输出一份可离线打开、可听可看的 HTML 学习报告。构建时通过 `--content-type documentary|movie` 选择题材，默认纪录片。报告由两部分组成：

- **叙事脉络**：纪录片整理主题、背景与论证推进顺序；电影按剧情顺序做观影后复盘。两者都生成口语化讲稿与可按段播放的音频。
- **生词本**：抽取片中的理解卡点，补齐音标、中英释义、上下文原句与发音音频。选词 rationale 随题材变化：纪录片关注论证断点，电影关注台词、剧情与人物关系。

系统的边界是「字幕进、学习报告出」。它不处理视频文件，不做逐句翻译，不承担背单词进度管理。

## 2. 系统边界与运行形态

- **运行形态**：本地 CLI。用户在终端执行一次构建命令，产物写入指定目录。
- **产物形态**：一个报告目录，包含 `document.json`、`media/`，默认还生成派生的 `index.html`；`.situ` 是可选的 zip 容器。HTML 通过相对路径引用媒体，不依赖本地服务或外部网络。
- **输入**：单语英文 `.srt` 字幕，以及题材参数 `documentary` / `movie`。`.vtt`、双语字幕、多集合并属于后续阶段。
- **外部依赖**：Claude Messages API（脉络梳理与术语抽取）、免费词典接口（音标、释义、真人发音）、云端 TTS（脉络播报与词典缺失时的发音兜底）。

## 3. 组件划分

| 组件 | 职责 |
| --- | --- |
| Subtitle Parser | 把 `.srt` 解析为带时间码的 cue 列表，处理 BOM、CRLF、重叠时间码与常见格式噪声。 |
| Content Segmenter | 按时间间隔与语义边界把 cue 合并为段落，供后续阶段引用时间码。 |
| Content Profile | 把 `documentary` / `movie` 解析成提示词、章节边界、词条范围、TTS 语气、缓存后缀与展示文案。 |
| Narrative Planner | 调用 LLM，按题材把完整字幕整理成结构化章节与口语化讲稿：纪录片讲论证推进，电影讲剧情与人物关系。 |
| Vocabulary Extractor | 调用 LLM，按题材抽取理解卡点；纪录片关注术语与论证断点，电影关注台词、剧情信息与人物关系。 |
| Lexicon Enricher | 查询词典接口补齐音标、英英释义与真人发音；中文释义由 Claude 结合语境生成；词典缺失时标记 TTS 兜底。 |
| TTS Provider | 可替换的语音合成接口，默认云端实现；按章节与词条生成音频。 |
| Audio Cache | 以文本与语音参数的哈希为键缓存音频，保证重跑不重复付费。 |
| Document Compiler | 把生成数据与媒体编译成 `document.json` + `media/`；写 ID、`href`、资源哈希与标签。 |
| Resolver | 以文档位置为 base 解析 `media/...`：目录、`.situ` zip、HTTP 三种模式。 |
| Packager | 只打包 `document.json` + 被引用资源，做路径安全、限额、确定性、哈希校验。 |
| Document Renderer | 按 block 类型渲染离线 HTML；不按内容类型分支。 |
| Publisher / Web | owner 隔离发布、严格文档校验、公开投影、`/document.json` 与 `/media` 路由。 |
| CLI Orchestrator | 解析参数、编排 build/render/package/migrate/publish、管理缓存与错误。 |

## 4. 数据与隐私

- 字幕内容只发送给用户显式配置的 LLM 与 TTS 服务，不经过本系统的任何中转服务。
- API Key 从环境变量读取，不写入 `document.json`、HTML 或运行日志。
- 生成物不包含外部脚本、字体或图片链接；HTML 设置内容安全策略，禁止运行时访问网络。
- 词典音频下载后落盘；`meta.attribution` 保留词典/TTS 署名。
- 公开 `document.json` 是 canonical 文档的投影，移除 `meta.id`、`meta.source.filename` 与 `meta.source.sha256`。

## 5. 演进约束

- 新增字幕格式只扩展 Subtitle Parser，不修改下游阶段的数据契约。
- 更换 TTS 供应商只替换 TTS Provider 实现，缓存键包含供应商与音色，避免串音。
- 更换 LLM 模型不改变 document 结构；`meta.generator` 记录生成器版本。
- 报告结构遵循 `document.version`，读取端对新增可选字段保持向后兼容；破坏性变更升主版本。
- 新增内容类型只新增 ContentProfile 与默认 block 组合；文档格式与 Renderer 不改。
