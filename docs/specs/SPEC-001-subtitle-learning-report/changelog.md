---
type: changelog
status: Draft
owner: alang
depends_on: []
updated_at: 2026-11-02
---

# Changelog: SPEC-001 情景学习

## [2026-11-02] - 项目更名为情景学习

- **修改类型**: Changed
- **影响范围**: 项目名、Python 包名、CLI、README、Spec 标题
- **变更原因**: 用户认为 `sublearn` 名称不合适，项目定名「情景学习」
- **具体内容**: 显示名改为「情景学习」；Python 包与 CLI 改为 `situlearn`；Spec 标题改为「情景学习 字幕脉络与生词语音化 技术方案」；缓存与报告产物不变。

## [2026-11-02] - 真人音频失败结果增加 TTL 缓存

- **修改类型**: Changed
- **影响范围**: 4.2 配置；5.2 可靠性
- **变更原因**: 未命中词条每次重跑都重新请求，拖慢全缓存重跑
- **具体内容**: 未命中结果写入 1 小时 TTL 负缓存；TTL 过期后重试；已成功词条继续跳过网络请求。

## [2026-11-02] - 外部请求限流与重试

- **修改类型**: Changed
- **影响范围**: 4.2 配置；5.2 可靠性
- **变更原因**: 真人音频源在并发下会返回 429/5xx，需要控制并发与频率
- **具体内容**: Oxford/Youdao 每源不超过 8 req/s，词典不超过 5 req/s，TTS 不超过 90 RPM；429/5xx 按 `Retry-After` 或指数退避重试最多 3 次；真人音频并发 2、词典 4、TTS 串行；临时失败不写入成功缓存。

## [2026-11-02] - 报告增加播放进度条

- **修改类型**: Added
- **影响范围**: 3.2 Report Assembler；4.4 接口；5.5 可访问性
- **变更原因**: 用户需要知道音频还剩多少
- **具体内容**: 报告底部增加全局播放器，显示进度条、当前/总时长与剩余时间；支持播放/暂停、拖动跳转与跨章节连续播放；进度条支持键盘操作。

## [2026-11-02] - 真人音频优先 Oxford/Youdao

- **修改类型**: Changed
- **影响范围**: 2.1 G4；3.4 关键选型；4.3 `TermEntry`；4.4 接口；5.4 安全；7.4 / 7.7；附录 A7/A8
- **变更原因**: 用户要求词条必须拿到真人音频；`dictionaryapi.dev` 媒体服务器 502，Oxford/Youdao 可用
- **具体内容**: 增加 Oxford/Youdao 真人音频源与四级回退（整词、词元、别名、多词关键词）；G4 改为 ≥95% 真人音频；TTS 仅用于残留词条与脉络章节；新增 `pronunciation_note` 与音频来源署名；实测覆盖 67/69，Oxford 28 + Youdao 39，残留 `Renascita`、`Saint Donasian`。

## [2026-11-02] - 播报稿改为全中文

- **修改类型**: Changed
- **影响范围**: 2.1 G2；4.2 `narrative_language` / `prompt_version`；4.3 `NarrativeSection.spoken_text`；附录 A7
- **变更原因**: 用户反馈中英夹杂的播报稿理解吃力，要求全部用中文
- **具体内容**: `spoken_text`、`summary`、`background`、`title`、`logline` 改为全中文；英文人名、作品名、术语用通行中文译名或简短解释，不夹带英文原词；英文原词只保留在 `key_terms`；提示词版本升到 `v2`，旧脉络缓存作废。

## [2026-11-02] - 放宽 why_it_matters 下限

- **修改类型**: Changed
- **影响范围**: 4.3 `TermCandidate.why_it_matters`；`TermEntry.why_it_matters`
- **变更原因**: 真实样本抽词出现两条 19 字的高质量解释，被 20 字下限误判，导致整批结构化输出解析失败；报告需要展示「为什么它是卡点」
- **具体内容**: `why_it_matters` 下限从 20 字调整为 15 字；`TermEntry` 增加同名必填字段，由候选词条带入；提示词与 Pydantic 模型同步。

## [2026-11-02] - 批准进入实施

- **修改类型**: Changed
- **影响范围**: `spec.md` 与 `plan.md` 的 frontmatter status；`docs/specs/README.md`
- **变更原因**: 用户确认 U1–U7；独立质量评审 core 100.0；mdstandards phase 1 通过
- **具体内容**: `spec.md` 与 `plan.md` 状态改为 `Approved`；输入源、DeepSeek 模型、TTS 音色与使用边界已确认，进入 M1 实施。

## [2026-11-02] - S1：根据 SRT 与 TTS 调研回写

- **修改类型**: Changed
- **影响范围**: 1.2 痛点证据；1.4 非目标；2.1 G2；3.2 模块职责；3.4 关键选型；4.2 配置；4.3 数据模型；4.4 接口；4.6 错误码；5.2 可靠性；6.3 冒烟；7.4 / 7.7；附录 A
- **变更原因**: 真实 srt 实测发现 cue 在半句处切断；小米 `mimo-v2.5-tts` 调研确认请求形态、8K 上限、100 RPM 与无 speed 参数；用户确认 `deepseek-flash`、`冰糖` 与仅个人使用
- **具体内容**: 补入真实样本统计与句子级合并要求；默认模型改 `deepseek-flash`；默认音色改 `冰糖`；新增 `narrative_language`、`tts_model`、`tts_base_url`、`tts_api_key_env`、`tts_chunk_chars`、`tts_rpm_limit`；章节音频改为 `audio_refs` 数组与 `audio_status`；TTS 协议细化为 Chat Completions 形态与 base64 返回；新增 TTS 分块与无效响应处理；关闭 U1–U5，新增 A7 中英混读音质。

## [2026-11-02] - 开发环境固定为 uv

- **修改类型**: Changed
- **影响范围**: 3.4 关键选型；3.5 工程基线；4.7 开发环境与依赖管理；5.5 兼容性；6.1 发布；6.3 冒烟；附录 A5
- **变更原因**: 用户指定 Python 包管理使用 uv
- **具体内容**: 增加 uv 依赖管理约定：`pyproject.toml` 声明、`uv.lock` 锁定、`uv sync --frozen` 安装、`uv run` 执行；干净环境安装纳入发布冒烟；LangChain 与 DeepSeek 客户端版本以 `uv.lock` 为准。

## [2026-11-02] - 模型固定为 DeepSeek

- **修改类型**: Changed
- **影响范围**: 3.1 架构图；3.2 模块职责；3.4 关键选型；3.5 新增清单；4.2 配置；4.3 manifest config；4.4 接口；4.6 错误码；6.3 冒烟；7.6 / 7.7；附录 A
- **变更原因**: 用户明确模型固定为 DeepSeek，替换此前的 Claude / Anthropic 选型
- **具体内容**: LLM 调用改为 `langchain-deepseek` 的 `ChatDeepSeek`；默认模型 `deepseek-chat`，可切 `deepseek-reasoner`；移除 Claude 专属的 1M 上下文与自适应思考表述，改为按实际字幕规模与 DeepSeek 上下文配置；结构化输出以 Pydantic 校验兜底；被否决方案改为「直接调用 DeepSeek SDK」；新增 `llm_provider`、`llm_base_url`、`llm_api_key_env` 配置与 DeepSeek 模型版本未决项。

## [2026-11-02] - 指定 LangChain 为编排框架

- **修改类型**: Changed
- **影响范围**: 1.4 非目标；3.1 总体架构；3.2 模块职责；3.3 数据流；3.4 关键选型；3.5 新增清单；4.2 配置；4.3 manifest config；4.4 接口；4.5 时序；5.3 可观测性；6.3 冒烟；7.6 / 7.7；附录 A
- **变更原因**: 用户明确指定 LangChain 作为框架，这是架构级约束
- **具体内容**: 整条构建管线以 LCEL `Runnable` 为骨架，Narrative Planner 与 Vocabulary Extractor 改为 LangChain Chain + `ChatAnthropic`，字幕解析、词典、TTS 与渲染封装为自定义 `Runnable`；补充 `llm_framework`、`langchain_version`、`prompt_version` 配置；新增「直接使用 Anthropic SDK」的被否决方案与矩阵行；明确不引入 LangGraph/LangServe；把 LangChain 版本锁定列为未决项。

## [2026-11-02] - 落实术语样本、TTS 供应商与发音署名

- **修改类型**: Changed
- **影响范围**: 1.2 核心技术痛点；2.1 G3；3.4 关键选型；4.2 配置；4.3 数据模型；4.4 外部协议；5.4 安全、隐私与合规；7.4 / 7.6；附录 A
- **变更原因**: 用户补充《文艺复兴的解放》的具体词例，确认 TTS 供应商为小米 `mimo-v2.5-tts`（限时免费），并选择「词典真人发音 + 署名」方案
- **具体内容**: 在痛点证据中加入 `Renaissance`、`cherub`、`wheedled` 三个词例；G3 纳入低频普通词；默认 TTS 改为小米 `mimo-v2.5-tts` 并标注定价风险；明确页脚署名与 `manifest.json` 的 `sources` 要求；附录 A 关闭原 A1/A2/A3，保留定价风险、跨报告词库、双语字幕、多集四项。

## [2026-11-02] - 补强 NFR 验收与目标追溯

- **修改类型**: Changed
- **影响范围**: 2.1 目标；5.1–5.5 非功能性需求
- **变更原因**: 独立评审指出部分 NFR 缺少明确验收方式；同时为每个 Goal 补上到后续章节的对应关系
- **具体内容**: 为性能、可靠性、可观测性、安全、兼容性五类 NFR 逐条补充数字阈值或验收方法；在 2.1 后新增 Goal 到设计章节的追溯表。输入源仍为单语英文 `.srt`。

## [2026-11-02] - 初始起草

- **修改类型**: Added
- **影响范围**: 全文
- **变更原因**: 把「情景式英语学习」想法落成可评审的技术方案，作为后续实现的唯一依据
- **具体内容**: 建立背景与失败链、目标与非目标、架构与数据流、详细数据模型与错误码、可度量 NFR、分阶段上线与回滚方案，以及包含 Status Quo 和被否决方案的权衡矩阵。输入源按用户补充明确为单语英文 `.srt`，其他字幕格式列为 Deferred to Phase 2。
