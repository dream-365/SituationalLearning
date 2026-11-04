# Spec Quality Report

- Target: `docs/specs/SPEC-003-content-type-profiles/spec.md`
- Rubric: 1.0.0 (`acb806c85c7a357f1cdfeaea80a8dc951333aefe5b630fe8576e0e0ce7f25947`)
- Target SHA-256: `f184c86262fd3f3277a33c1af7b72ab7715f2c824bda7368389a030ac856f8e6`
- Reviewer session: `spec003-review-20261103-06`

**Headline score (core): 100.0**  |  Diagnostic score (all): 100.0

> The auditor verifies evidence presence, section placement, and score arithmetic. It does not judge whether evidence is sufficient or true.

> Normalization covers full-width ASCII, NBSP, and ideographic space; it is not full Unicode NFKC.

| Dimension | Headline | Diagnostic | Weight |
|---|---:|---:|---:|
| 背景落地 | 100.0 | 100.0 | 2 |
| 痛点证据 | 100.0 | 100.0 | 3 |
| 目标可验收 | 100.0 | 100.0 | 3 |
| 非目标边界 | 100.0 | 100.0 | 2 |
| 架构自洽 | 100.0 | 100.0 | 2 |
| 详细设计完整 | 100.0 | 100.0 | 2 |
| NFR 可度量 | 100.0 | 100.0 | 2 |
| 上线可回滚 | 100.0 | 100.0 | 2 |
| 替代方案诚实 | 100.0 | 100.0 | 2 |
| 跨章自洽 | 100.0 | 100.0 | 2 |
| 证据卫生 | 100.0 | 100.0 | 3 |

## 背景落地 (background)

- **bg.current_state** [core, level 2] — 1.1 是否写清了模块职责、核心流程与当前技术栈？
  - evidence `1.1 系统现状`: "情景学习目前是一个本地 CLI 工具，负责把一份英文纪录片的 '.srt' 字幕变成可离线打开的学习报告。核心链路是：Subtitle Parser 解析字幕，Content Segmenter 合并半句 cue，Narrative Planner 生成中文脉络，Vocabulary Extractor 选出“理解卡点”词条，Lexicon Enricher 补词典与真人发音，TTS 生成章节音频与残留词条音频，Report Assembler 写出 'manifest.json' 与 'report.html'。Web 发布层把同一份 manifest 渲染成公网页面（SPEC-002），不重新生成内容。"
  - normalized: "情景学习目前是一个本地 CLI 工具,负责把一份英文纪录片的 '.srt' 字幕变成可离线打开的学习报告。核心链路是:Subtitle Parser 解析字幕,Content Segmenter 合并半句 cue,Narrative Planner 生成中文脉络,Vocabulary Extractor 选出“理解卡点”词条,Lexicon Enricher 补词典与真人发音,TTS 生成章节音频与残留词条音频,Report Assembler 写出 'manifest.json' 与 'report.html'。Web 发布层把同一份 manifest 渲染成公网页面(SPEC-002),不重新生成内容。"
  - rationale: 1.1 写明了 CLI 工具的模块职责、从字幕解析到报告生成的完整调用链，以及 manifest/report 与 Web 发布层的当前形态，足以理解现状。
- **bg.failure_chain** [core, level 2] — 1.2 是否有从触发到后果的分步失败链？
  - evidence `1.2 核心技术痛点`: "1. 用户拿到一部剧情电影的英文字幕，执行 'situlearn build'。 2. Narrative Planner 仍以“纪录片内容分析师”的身份工作，把剧情片讲成“每一段在论证什么”，而不是“谁想要什么、关系如何变化、剧情如何推进”。 3. Vocabulary Extractor 仍按“论证断点”选词，容易漏掉台词里的俚语、口语、人物关系词和潜台词关键词。 4. 报告标题、章节结构和播报稿可以生成，但读起来像一部谈论文献的纪录片，而不是一部剧情片；用户无法把报告当作“看完电影后的剧情复盘”使用。 5. 三个下游后果同时出现：剧情理解未被有效复盘；词表与观影体验脱节；用户只能继续人工整理，工具的电影场景实际不可用。"
  - normalized: "1. 用户拿到一部剧情电影的英文字幕,执行 'situlearn build'。 2. Narrative Planner 仍以“纪录片内容分析师”的身份工作,把剧情片讲成“每一段在论证什么”,而不是“谁想要什么、关系如何变化、剧情如何推进”。 3. Vocabulary Extractor 仍按“论证断点”选词,容易漏掉台词里的俚语、口语、人物关系词和潜台词关键词。 4. 报告标题、章节结构和播报稿可以生成,但读起来像一部谈论文献的纪录片,而不是一部剧情片;用户无法把报告当作“看完电影后的剧情复盘”使用。 5. 三个下游后果同时出现:剧情理解未被有效复盘;词表与观影体验脱节;用户只能继续人工整理,工具的电影场景实际不可用。"
  - rationale: 1.2 以 1–5 步编号给出从执行 build 到三个下游后果的完整失败链，触发与后果逐级对应。
- **bg.trigger** [core, level 2] — 1.3 是否解释了为什么现在做？
  - evidence `1.3 重构/设计动机`: "1. **使用触发**：用户当前已经在看剧情电影，电影字幕无法得到与纪录片同等质量的学习报告。 2. **能力触发**：现有管线已经能解析任意单语英文 SRT，分题材只需要替换提示词策略、章节约束与展示文案，不需要重做解析、词典、音频或发布链路。 3. **兼容触发**：现有纪录片产物、缓存与已发布报告必须继续可用；分型不能以破坏旧行为为代价。"
  - normalized: "1. **使用触发**:用户当前已经在看剧情电影,电影字幕无法得到与纪录片同等质量的学习报告。 2. **能力触发**:现有管线已经能解析任意单语英文 SRT,分题材只需要替换提示词策略、章节约束与展示文案,不需要重做解析、词典、音频或发布链路。 3. **兼容触发**:现有纪录片产物、缓存与已发布报告必须继续可用;分型不能以破坏旧行为为代价。"
  - rationale: 1.3 列出使用、能力与兼容三个触发点，说明当前已覆盖电影场景且改动窗口合适。
- **bg.non_goals** [core, level 2] — 1.4 是否写了不做的后果与本次非目标？
  - evidence `1.4 非目标`: "不做的后果是电影场景继续产出纪录片式报告，用户仍要人工整理。本次明确不做：  - 防剧透模式、按观看进度解锁、'spoiler_level' 字段（本次不做）。 - 'characters'、'synopsis'、人物关系图与人物专属词条分类（Deferred to Phase 2）。 - LLM 自动识别内容类型（本次不做；避免多一次调用和不可复现的分类结果）。 - 针对电影的 Segmenter 参数调优（本次不做；复用现有切分策略）。 - 同一字幕的纪录片版与电影版在服务端并存（本次不做；发布仍是“最后发布生效”）。 - 新增语言、双语字幕、多集合并与视频处理（本次不做）。"
  - normalized: "不做的后果是电影场景继续产出纪录片式报告,用户仍要人工整理。本次明确不做: - 防剧透模式、按观看进度解锁、'spoiler_level' 字段(本次不做)。 - 'characters'、'synopsis'、人物关系图与人物专属词条分类(Deferred to Phase 2)。 - LLM 自动识别内容类型(本次不做;避免多一次调用和不可复现的分类结果)。 - 针对电影的 Segmenter 参数调优(本次不做;复用现有切分策略)。 - 同一字幕的纪录片版与电影版在服务端并存(本次不做;发布仍是“最后发布生效”)。 - 新增语言、双语字幕、多集合并与视频处理(本次不做)。"
  - rationale: 1.4 先写明不做的后果，再逐条列出本次非目标，边界清晰。

## 痛点证据 (pain_evidence)

- **bg.pain_evidence** [core, level 2] — 1.2 是否有至少一条可核实的证据（事故、度量或引述）？
  - evidence `1.2 核心技术痛点`: "证据（引述）：用户在本轮需求中明确说「至少要支持纪录片跟电影」。这不是“将来也许”的愿望，而是当前使用范围已经覆盖电影，而工具只在纪录片场景成立。  补充证据（仓库事实）：'src/situlearn/prompts.py' 的全部叙事、中文修复、选词与释义提示词都写有“纪录片/片子/片中”；'src/situlearn/tts.py' 的默认语气写死为纪录片解说；报告模板的“内容脉络”“播放本节”“章节”等文案没有任何题材分支。这些不是措辞问题，而是生成目标与验收标准的问题。"
  - normalized: "证据(引述):用户在本轮需求中明确说「至少要支持纪录片跟电影」。这不是“将来也许”的愿望,而是当前使用范围已经覆盖电影,而工具只在纪录片场景成立。 补充证据(仓库事实):'src/situlearn/prompts.py' 的全部叙事、中文修复、选词与释义提示词都写有“纪录片/片子/片中”;'src/situlearn/tts.py' 的默认语气写死为纪录片解说;报告模板的“内容脉络”“播放本节”“章节”等文案没有任何题材分支。这些不是措辞问题,而是生成目标与验收标准的问题。"
  - rationale: 1.2 给出用户原话引述与可核对的仓库事实（提示词、TTS 语气、模板文案），且直接对应失败链中的纪录片式生成。

## 目标可验收 (goal_verifiability)

- **goal.verifiable** [core, level 2] — 2.1 每个 Goal 是否都有验收方式？
  - evidence `2.1 目标`: "- **G1 - 架构：内容类型可选**：'situlearn build' 新增 '--content-type documentary\|movie'，默认 'documentary'；非法值由 CLI 拒绝。验收：CLI 帮助与参数校验测试通过；不传参数时 manifest 与报告行为与改动前一致。 - **G2 - 生成能力：电影生成策略**：电影构建使用独立的叙事、中文修复、选词与释义提示词；叙事按剧情时间顺序输出 6–12 个场景段落，允许完整剧透，选词 rationale 指向台词、剧情与人物关系。验收：提示词单元测试冻结关键要求；mock LLM 的端到端构建产出 6 段电影报告。 - **G3 - 展示：电影展示文案**：电影报告使用“剧情脉络 / 场景 / 播放本场 / 全部场景 / 回到本场 / 上一场 / 下一场”等文案；纪录片报告文案逐字不变。验收：离线 HTML、Web 报告、章节页、词表页与播放器契约测试。 - **G4 - 可靠性：向后兼容与缓存隔离**：旧 manifest 无内容类型时按纪录片渲染；纪录片缓存、提示词和 TTS 缓存键保持逐字节兼容；同一字幕的纪录片与电影构建使用不同缓存目录，不串内容。验收：旧 fixture 渲染测试、缓存目录隔离测试、'AudioCache.key(style=None)' 对照测试。 - **G5 - 可运维性：发布与文档**：README、架构文档与发布 runbook 说明内容类型用法和“同一字幕最后发布生效”的限制。验收：文档评审；'publish --dry-run' 行为不变。"
  - normalized: "- **G1 - 架构:内容类型可选**:'situlearn build' 新增 '--content-type documentary\|movie',默认 'documentary';非法值由 CLI 拒绝。验收:CLI 帮助与参数校验测试通过;不传参数时 manifest 与报告行为与改动前一致。 - **G2 - 生成能力:电影生成策略**:电影构建使用独立的叙事、中文修复、选词与释义提示词;叙事按剧情时间顺序输出 6–12 个场景段落,允许完整剧透,选词 rationale 指向台词、剧情与人物关系。验收:提示词单元测试冻结关键要求;mock LLM 的端到端构建产出 6 段电影报告。 - **G3 - 展示:电影展示文案**:电影报告使用“剧情脉络 / 场景 / 播放本场 / 全部场景 / 回到本场 / 上一场 / 下一场”等文案;纪录片报告文案逐字不变。验收:离线 HTML、Web 报告、章节页、词表页与播放器契约测试。 - **G4 - 可靠性:向后兼容与缓存隔离**:旧 manifest 无内容类型时按纪录片渲染;纪录片缓存、提示词和 TTS 缓存键保持逐字节兼容;同一字幕的纪录片与电影构建使用不同缓存目录,不串内容。验收:旧 fixture 渲染测试、缓存目录隔离测试、'AudioCache.key(style=None)' 对照测试。 - **G5 - 可运维性:发布与文档**:README、架构文档与发布 runbook 说明内容类型用法和“同一字幕最后发布生效”的限制。验收:文档评审;'publish --dry-run' 行为不变。"
  - rationale: 5 个 Goal 每个都附有验收方式，涵盖参数校验测试、提示词单测、端到端构建、渲染契约测试与文档评审。
- **goal.quantified** [core, level 2] — 2.1 是否至少有一个 Goal 有数字/单位/明确阈值？
  - evidence `2.1 目标`: "- **G2 - 生成能力：电影生成策略**：电影构建使用独立的叙事、中文修复、选词与释义提示词；叙事按剧情时间顺序输出 6–12 个场景段落，允许完整剧透，选词 rationale 指向台词、剧情与人物关系。验收：提示词单元测试冻结关键要求；mock LLM 的端到端构建产出 6 段电影报告。"
  - normalized: "- **G2 - 生成能力:电影生成策略**:电影构建使用独立的叙事、中文修复、选词与释义提示词;叙事按剧情时间顺序输出 6–12 个场景段落,允许完整剧透,选词 rationale 指向台词、剧情与人物关系。验收:提示词单元测试冻结关键要求;mock LLM 的端到端构建产出 6 段电影报告。"
  - rationale: G2 明确要求输出 6–12 个场景段落，验收中给出 6 段电影报告，具备数字与范围。
- **goal.count** [extended, level 2] — 2.1 Goals 是否控制在 3–6 个？
  - evidence `2.1 目标`: "以下 5 个 Goal 按架构、生成能力、展示、可靠性与可运维性分类："
  - normalized: "以下 5 个 Goal 按架构、生成能力、展示、可靠性与可运维性分类:"
  - rationale: 共 5 个 Goal，处于 3–6 个区间，并按架构、生成能力、展示、可靠性与可运维性分类。

## 非目标边界 (non_goal_boundary)

- **nongoal.labeled** [core, level 2] — 2.2 每条 Non-Goal 是否标了本次不做或 Deferred to Phase 2？
  - evidence `2.2 非目标`: "- **NG1 - 防剧透**：不做剧透安全模式、观看进度边界或分段解锁（本次不做）。 - **NG2 - 结构化剧情模型**：不新增人物、关系、剧情摘要字段或人物词条分类（Deferred to Phase 2）。 - **NG3 - 自动识别**：不做 '--content-type auto' 或 LLM 分类（本次不做）。内容类型由 CLI 显式指定，不由模型自动识别。 - **NG4 - 发布复合键**：不改 'report_key' 与服务端校验；同一字幕的两种题材不能同时在线（Deferred to Phase 2）。 - **NG5 - 电影专用切分**：不调整 Segmenter 的 gap、字数与时长参数（本次不做）。"
  - normalized: "- **NG1 - 防剧透**:不做剧透安全模式、观看进度边界或分段解锁(本次不做)。 - **NG2 - 结构化剧情模型**:不新增人物、关系、剧情摘要字段或人物词条分类(Deferred to Phase 2)。 - **NG3 - 自动识别**:不做 '--content-type auto' 或 LLM 分类(本次不做)。内容类型由 CLI 显式指定,不由模型自动识别。 - **NG4 - 发布复合键**:不改 'report_key' 与服务端校验;同一字幕的两种题材不能同时在线(Deferred to Phase 2)。 - **NG5 - 电影专用切分**:不调整 Segmenter 的 gap、字数与时长参数(本次不做)。"
  - rationale: 5 条 Non-Goal 均标注「本次不做」或「Deferred to Phase 2」，无遗漏。
- **nongoal.not_dumping_ground** [extended, level 2] — 2.2 非目标是否能追溯到痛点或边界？
  - evidence `2.2 非目标`: "- **NG1 - 防剧透**：不做剧透安全模式、观看进度边界或分段解锁（本次不做）。 - **NG2 - 结构化剧情模型**：不新增人物、关系、剧情摘要字段或人物词条分类（Deferred to Phase 2）。 - **NG3 - 自动识别**：不做 '--content-type auto' 或 LLM 分类（本次不做）。内容类型由 CLI 显式指定，不由模型自动识别。 - **NG4 - 发布复合键**：不改 'report_key' 与服务端校验；同一字幕的两种题材不能同时在线（Deferred to Phase 2）。 - **NG5 - 电影专用切分**：不调整 Segmenter 的 gap、字数与时长参数（本次不做）。"
  - normalized: "- **NG1 - 防剧透**:不做剧透安全模式、观看进度边界或分段解锁(本次不做)。 - **NG2 - 结构化剧情模型**:不新增人物、关系、剧情摘要字段或人物词条分类(Deferred to Phase 2)。 - **NG3 - 自动识别**:不做 '--content-type auto' 或 LLM 分类(本次不做)。内容类型由 CLI 显式指定,不由模型自动识别。 - **NG4 - 发布复合键**:不改 'report_key' 与服务端校验;同一字幕的两种题材不能同时在线(Deferred to Phase 2)。 - **NG5 - 电影专用切分**:不调整 Segmenter 的 gap、字数与时长参数(本次不做)。"
  - rationale: 每条非目标都能对应 1.3 的产品边界或 1.4 的范围约束，例如防剧透对应「看完再学」、自动识别对应「显式指定」。

## 架构自洽 (architecture)

- **arch.solution_shape** [core, level 2] — 第 3 章是否有拓扑或等价的模块/数据流描述？
  - evidence `3. 架构设计与核心方案`: "本章给出新增/改造/不变的组件拓扑与数据流：CLI 把题材交给 ContentProfile，Build Pipeline 按 profile 选择 PromptSet、缓存、章节校验与 TTS，Renderer 按 manifest 注入文案；新增 content.py 与电影提示词，改造 pipeline/chains/audio 与模板，SRT 解析、词典、真人音频与发布 API 保持不变。"
  - normalized: "本章给出新增/改造/不变的组件拓扑与数据流:CLI 把题材交给 ContentProfile,Build Pipeline 按 profile 选择 PromptSet、缓存、章节校验与 TTS,Renderer 按 manifest 注入文案;新增 content.py 与电影提示词,改造 pipeline/chains/audio 与模板,SRT 解析、词典、真人音频与发布 API 保持不变。"
  - rationale: 第 3 章开头直接给出组件拓扑与数据流：CLI→ContentProfile→Pipeline→PromptSet/缓存/TTS→Renderer，并有 3.1 图佐证。
- **arch.topology** [extended, level 2] — 3.1 拓扑图是否让每个模块有一句职责？
  - evidence `3.1 总体架构`: "'''mermaid graph TD     CLI[CLI --content-type] --> Profile[ContentProfile 解析]     Profile --> Pipeline[Build Pipeline]     Pipeline --> Narrative[Narrative Planner PromptSet]     Pipeline --> Vocab[Vocabulary / Gloss PromptSet]     Pipeline --> Cache[(Content-type 缓存命名空间)]     Pipeline --> TTS[TTS Style]     Pipeline --> Manifest[manifest.json config.content_type]     Manifest --> Offline[离线报告 labels]     Manifest --> Web[Web 报告 labels + player] '''"
  - normalized: "'''mermaid graph TD CLI[CLI --content-type] --> Profile[ContentProfile 解析] Profile --> Pipeline[Build Pipeline] Pipeline --> Narrative[Narrative Planner PromptSet] Pipeline --> Vocab[Vocabulary / Gloss PromptSet] Pipeline --> Cache[(Content-type 缓存命名空间)] Pipeline --> TTS[TTS Style] Pipeline --> Manifest[manifest.json config.content_type] Manifest --> Offline[离线报告 labels] Manifest --> Web[Web 报告 labels + player] '''"
  - evidence `3.1 总体架构`: "图中每个模块的职责：  - **CLI**：解析 '--content-type'，默认纪录片，把值交给构建管线。 - **ContentProfile**：把题材解析成提示词、边界、缓存、TTS 与文案策略。 - **Build Pipeline**：按 profile 编排生成、校验、缓存与 manifest 写入。 - **PromptSet**：为叙事、选词与释义提供题材对应的提示词模板。 - **Renderer**：从 manifest 读取题材，把 'ReportLabels' 注入离线与 Web 模板。"
  - normalized: "图中每个模块的职责: - **CLI**:解析 '--content-type',默认纪录片,把值交给构建管线。 - **ContentProfile**:把题材解析成提示词、边界、缓存、TTS 与文案策略。 - **Build Pipeline**:按 profile 编排生成、校验、缓存与 manifest 写入。 - **PromptSet**:为叙事、选词与释义提供题材对应的提示词模板。 - **Renderer**:从 manifest 读取题材,把 'ReportLabels' 注入离线与 Web 模板。"
  - rationale: 3.1 提供 mermaid 拓扑图，并逐模块给出一句职责说明。
- **arch.change_set** [extended, level 2] — 第 3 章是否写清新增/改造/保持不变？
  - evidence `3. 架构设计与核心方案`: "本章给出新增/改造/不变的组件拓扑与数据流：CLI 把题材交给 ContentProfile，Build Pipeline 按 profile 选择 PromptSet、缓存、章节校验与 TTS，Renderer 按 manifest 注入文案；新增 content.py 与电影提示词，改造 pipeline/chains/audio 与模板，SRT 解析、词典、真人音频与发布 API 保持不变。"
  - normalized: "本章给出新增/改造/不变的组件拓扑与数据流:CLI 把题材交给 ContentProfile,Build Pipeline 按 profile 选择 PromptSet、缓存、章节校验与 TTS,Renderer 按 manifest 注入文案;新增 content.py 与电影提示词,改造 pipeline/chains/audio 与模板,SRT 解析、词典、真人音频与发布 API 保持不变。"
  - rationale: 第 3 章开头直接写明新增 content.py 与电影提示词、改造 pipeline/chains/audio 与模板、其余链路保持不变。
- **arch.rationale** [extended, level 2] — 关键选型是否有理由，详细对比指向第 7 章？
  - evidence `3.4 关键选型与约束`: "采用“不可变 'ContentProfile' + 独立 'PromptSet'”的原因：题材差异集中在一处；提示词可以逐字冻结与测试；缓存、TTS 与文案共享同一策略来源；纪录片路径可以保持空后缀与 'null' 样式，兼容成本最低。与自动识别、动态模型等方案的完整对比见第 7 章。"
  - normalized: "采用“不可变 'ContentProfile' + 独立 'PromptSet'”的原因:题材差异集中在一处;提示词可以逐字冻结与测试;缓存、TTS 与文案共享同一策略来源;纪录片路径可以保持空后缀与 'null' 样式,兼容成本最低。与自动识别、动态模型等方案的完整对比见第 7 章。"
  - rationale: 3.4 说明选择不可变 ContentProfile + 独立 PromptSet 的四点理由，并明确详细对比见第 7 章。

## 详细设计完整 (detailed_design)

- **design.contract** [core, level 2] — 第 4 章是否至少有一份数据模型或接口契约？
  - evidence `4. 详细设计`: "本章给出 ContentType、ContentProfile 与 ReportLabels 的数据契约，CLI 与构建入口的接口，正常/异常流程，以及每个错误场景的处理策略。"
  - normalized: "本章给出 ContentType、ContentProfile 与 ReportLabels 的数据契约,CLI 与构建入口的接口,正常/异常流程,以及每个错误场景的处理策略。"
  - rationale: 第 4 章开头声明给出 ContentType/ContentProfile/ReportLabels 数据契约与 CLI/构建入口接口，4.3 与 4.4 落实为字段表和方法签名。
- **design.data_model** [extended, level 2] — 4.3 数据模型是否有字段类型、必填与校验？
  - evidence `4.3 数据模型与契约`: "\| 字段 \| 类型 \| 必填 \| 说明 \| \| --- \| --- \| --- \| --- \| \| 'content_type' \| 'ContentType' \| 是 \| 题材标识，只允许 'documentary' / 'movie' \| \| 'prompt_version' \| string \| 是 \| 写入缓存文件名与 manifest；本次两者均为 'v2' \| \| 'cache_suffix' \| string \| 是 \| 纪录片为空串，电影为 '-movie' \| \| 'section_min' / 'section_max' \| int \| 是 \| 纪录片 4/8，电影 6/12 \| \| 'terms_min' / 'terms_max' \| int \| 是 \| 两者均为 30/80；本次不改变词条目标 \| \| 'tts_style' \| string 或 null \| 是 \| 纪录片 'null' 表示使用 provider 默认；电影为剧情解说语气 \| \| 'labels' \| 'ReportLabels' \| 是 \| 模板文案集合；纪录片取值与现有模板逐字一致 \|"
  - normalized: "\| 字段 \| 类型 \| 必填 \| 说明 \| \| --- \| --- \| --- \| --- \| \| 'content_type' \| 'ContentType' \| 是 \| 题材标识,只允许 'documentary' / 'movie' \| \| 'prompt_version' \| string \| 是 \| 写入缓存文件名与 manifest;本次两者均为 'v2' \| \| 'cache_suffix' \| string \| 是 \| 纪录片为空串,电影为 '-movie' \| \| 'section_min' / 'section_max' \| int \| 是 \| 纪录片 4/8,电影 6/12 \| \| 'terms_min' / 'terms_max' \| int \| 是 \| 两者均为 30/80;本次不改变词条目标 \| \| 'tts_style' \| string 或 null \| 是 \| 纪录片 'null' 表示使用 provider 默认;电影为剧情解说语气 \| \| 'labels' \| 'ReportLabels' \| 是 \| 模板文案集合;纪录片取值与现有模板逐字一致 \|"
  - evidence `4.3 数据模型与契约`: "manifest 契约：'ReportManifest.config.content_type' 是可选字符串，只允许 'documentary' / 'movie'；纪录片构建不写入该键。渲染路径遇到缺失、未知或非法值时回退 'documentary'；构建路径遇到非法值时抛 'ValueError'。"
  - normalized: "manifest 契约:'ReportManifest.config.content_type' 是可选字符串,只允许 'documentary' / 'movie';纪录片构建不写入该键。渲染路径遇到缺失、未知或非法值时回退 'documentary';构建路径遇到非法值时抛 'ValueError'。"
  - rationale: 4.3 的字段表给出每个字段的类型、必填与说明，并用「只允许 documentary/movie」等约束与非法值处理体现校验。
- **design.interface** [extended, level 2] — 4.4 接口是否有请求/响应/状态码或方法签名？
  - evidence `4.4 接口与协议`: "- CLI：'situlearn build <input.srt> --out <dir> [--content-type documentary\|movie]'；默认 'documentary'；未知取值由 argparse 'choices' 拒绝，退出码 2。 - 构建入口：'build_report(input_path, out_dir, *, content_type=documentary, terms_min=None, terms_max=None, no_audio=False, force=False, cache_root=None, progress=None)'；'terms_min/max' 为 'None' 时从 profile 取默认值。 - 渲染入口：'profile_for_manifest(manifest) -> ContentProfile'；只读取 'manifest.config'，不重新判断题材。 - 错误返回：'build_report' 的未知类型抛 'ValueError'，由 CLI 边界打印错误并返回 1；渲染路径不因未知题材抛错。"
  - normalized: "- CLI:'situlearn build <input.srt> --out <dir> [--content-type documentary\|movie]';默认 'documentary';未知取值由 argparse 'choices' 拒绝,退出码 2。 - 构建入口:'build_report(input_path, out_dir, *, content_type=documentary, terms_min=None, terms_max=None, no_audio=False, force=False, cache_root=None, progress=None)';'terms_min/max' 为 'None' 时从 profile 取默认值。 - 渲染入口:'profile_for_manifest(manifest) -> ContentProfile';只读取 'manifest.config',不重新判断题材。 - 错误返回:'build_report' 的未知类型抛 'ValueError',由 CLI 边界打印错误并返回 1;渲染路径不因未知题材抛错。"
  - rationale: 4.4 给出 CLI 用法、build_report 与 profile_for_manifest 方法签名，以及 argparse/ValueError 对应的退出码与错误行为。
- **design.sequence** [extended, level 2] — 4.5 复杂流程是否有时序图或等价分步说明？
  - evidence `4.5 核心流程与时序`: "正常路径：  1. CLI 解析 '--content-type'，默认 'documentary'，传给 'build_report'。 2. 'build_report' 解析出 'ContentProfile'，据此确定词条范围与缓存目录。 3. Narrative Planner、Vocabulary Extractor、Gloss 从 'PromptSet' 取对应模板；电影叙事额外接收字幕文件名作为片名线索。 4. 章节生成后按 profile 校验数量：纪录片 4–8，电影 6–12。 5. TTS 按 profile 的语气合成；纪录片传 'None' 以保持 provider 默认和旧缓存键。 6. manifest 的 'config' 仅在非纪录片时写入 'content_type'；纪录片 manifest 字节保持兼容。 7. 离线与 Web 渲染从 'config.content_type' 取 profile；缺失或未知值回退纪录片。"
  - normalized: "正常路径: 1. CLI 解析 '--content-type',默认 'documentary',传给 'build_report'。 2. 'build_report' 解析出 'ContentProfile',据此确定词条范围与缓存目录。 3. Narrative Planner、Vocabulary Extractor、Gloss 从 'PromptSet' 取对应模板;电影叙事额外接收字幕文件名作为片名线索。 4. 章节生成后按 profile 校验数量:纪录片 4–8,电影 6–12。 5. TTS 按 profile 的语气合成;纪录片传 'None' 以保持 provider 默认和旧缓存键。 6. manifest 的 'config' 仅在非纪录片时写入 'content_type';纪录片 manifest 字节保持兼容。 7. 离线与 Web 渲染从 'config.content_type' 取 profile;缺失或未知值回退纪录片。"
  - evidence `4.5 核心流程与时序`: "异常路径：  8. 缓存中的章节数不符合当前 profile：丢弃缓存并重新生成。 9. 新生成或中文修复后的章节数仍不符合 profile：构建失败，提示实际数量与允许范围。 10. 旧 manifest 缺少或带有未知 'content_type'：按纪录片渲染，不报错、不 404。"
  - normalized: "异常路径: 8. 缓存中的章节数不符合当前 profile:丢弃缓存并重新生成。 9. 新生成或中文修复后的章节数仍不符合 profile:构建失败,提示实际数量与允许范围。 10. 旧 manifest 缺少或带有未知 'content_type':按纪录片渲染,不报错、不 404。"
  - rationale: 4.5 用编号步骤给出正常路径 1–7 与异常路径 8–10，覆盖缓存不符、章节越界与旧 manifest 回退。
- **design.errors** [extended, level 2] — 4.6 每个错误码是否有触发场景与处理策略？
  - evidence `4.6 异常处理与错误码`: "\| 场景 \| 处理策略 \| \| --- \| --- \| \| CLI 传入未知 '--content-type' \| argparse 'choices' 拒绝，退出码 2 \| \| 'build_report' 收到未知类型 \| 'ValueError'，由 CLI 边界打印错误并返回 1 \| \| 缓存中的章节数不符合当前 profile \| 丢弃缓存并重新生成 \| \| 新生成的章节数不符合 profile \| 构建失败并提示实际数量与允许范围 \| \| 旧 manifest 缺少 'content_type' \| 按纪录片渲染，不报错 \| \| manifest 的 'content_type' 未知 \| 按纪录片渲染，不 404 \| \| 电影少于 6 段（短片） \| 构建失败；调整 profile 下限即可，不改 schema \|"
  - normalized: "\| 场景 \| 处理策略 \| \| --- \| --- \| \| CLI 传入未知 '--content-type' \| argparse 'choices' 拒绝,退出码 2 \| \| 'build_report' 收到未知类型 \| 'ValueError',由 CLI 边界打印错误并返回 1 \| \| 缓存中的章节数不符合当前 profile \| 丢弃缓存并重新生成 \| \| 新生成的章节数不符合 profile \| 构建失败并提示实际数量与允许范围 \| \| 旧 manifest 缺少 'content_type' \| 按纪录片渲染,不报错 \| \| manifest 的 'content_type' 未知 \| 按纪录片渲染,不 404 \| \| 电影少于 6 段(短片) \| 构建失败;调整 profile 下限即可,不改 schema \|"
  - rationale: 4.6 的表格为每个错误场景列出触发条件与处理策略，包含 CLI 校验、构建失败、缓存丢弃与旧 manifest 回退。

## NFR 可度量 (nfr)

- **nfr.measurable** [core, level 2] — 第 5 章每条 NFR 是否有数字、单位或验收方式？
  - evidence `5. 非功能性需求`: "本章覆盖兼容性（5.1）、性能与资源（5.2）、可靠性与可复现性（5.3）、安全与隐私（5.4）与可观测性（5.5）；未实测指标标 [estimated]，例如构建耗时增量小于 1%、单题材缓存命中率与改动前相同。"
  - normalized: "本章覆盖兼容性(5.1)、性能与资源(5.2)、可靠性与可复现性(5.3)、安全与隐私(5.4)与可观测性(5.5);未实测指标标 [estimated],例如构建耗时增量小于 1%、单题材缓存命中率与改动前相同。"
  - rationale: 第 5 章声明覆盖五类 NFR，并以 <1%、缓存命中率等数字/验收标准约束；5.1–5.5 每条均附验收方式。
- **nfr.coverage** [core, level 2] — 第 5 章是否覆盖性能、可靠性、可观测性、安全，或说明不适用？
  - evidence `5. 非功能性需求`: "本章覆盖兼容性（5.1）、性能与资源（5.2）、可靠性与可复现性（5.3）、安全与隐私（5.4）与可观测性（5.5）；未实测指标标 [estimated]，例如构建耗时增量小于 1%、单题材缓存命中率与改动前相同。"
  - normalized: "本章覆盖兼容性(5.1)、性能与资源(5.2)、可靠性与可复现性(5.3)、安全与隐私(5.4)与可观测性(5.5);未实测指标标 [estimated],例如构建耗时增量小于 1%、单题材缓存命中率与改动前相同。"
  - rationale: 第 5 章开头明确覆盖兼容性、性能与资源、可靠性与可复现性、安全与隐私、可观测性五类。
- **nfr.honesty** [core, level 2] — 未实测的指标是否标了 [estimated] 或 未实现？
  - evidence `5. 非功能性需求`: "本章覆盖兼容性（5.1）、性能与资源（5.2）、可靠性与可复现性（5.3）、安全与隐私（5.4）与可观测性（5.5）；未实测指标标 [estimated]，例如构建耗时增量小于 1%、单题材缓存命中率与改动前相同。"
  - normalized: "本章覆盖兼容性(5.1)、性能与资源(5.2)、可靠性与可复现性(5.3)、安全与隐私(5.4)与可观测性(5.5);未实测指标标 [estimated],例如构建耗时增量小于 1%、单题材缓存命中率与改动前相同。"
  - rationale: 第 5 章开头明确未实测指标标 [estimated]，并给出构建耗时增量与缓存命中率两个示例。

## 上线可回滚 (rollout)

- **rollout.release** [core, level 2] — 6.1 是否有发布策略与灰度节奏？
  - evidence `6.1 发布与灰度`: "- 单机 CLI 工具，按版本发布；无服务端部署变更。因为没有常驻流量，不设置金丝雀或百分比灰度，灰度等价于“先在个人样本上构建并检查，再升级本地工具”。 - 旧的已发布报告继续由服务端按纪录片渲染；新构建的电影报告需要更新后的 CLI 构建并重新发布。"
  - normalized: "- 单机 CLI 工具,按版本发布;无服务端部署变更。因为没有常驻流量,不设置金丝雀或百分比灰度,灰度等价于“先在个人样本上构建并检查,再升级本地工具”。 - 旧的已发布报告继续由服务端按纪录片渲染;新构建的电影报告需要更新后的 CLI 构建并重新发布。"
  - rationale: 6.1 说明按版本发布、无服务端部署变更，并解释因无常驻流量而以个人样本构建代替金丝雀/百分比灰度。
- **rollout.migration** [core, level 2] — 6.2 是否有迁移/兼容方案，或说明无需迁移？
  - evidence `6.2 数据迁移与兼容性`: "- 不迁移旧 manifest；'config.content_type' 缺失即纪录片。 - 不清理旧缓存；纪录片缓存路径不变，继续命中。 - 不升级 'schema_version'。"
  - normalized: "- 不迁移旧 manifest;'config.content_type' 缺失即纪录片。 - 不清理旧缓存;纪录片缓存路径不变,继续命中。 - 不升级 'schema_version'。"
  - rationale: 6.2 明确不迁移旧 manifest、不清理旧缓存、不升级 schema_version，并说明缺失 content_type 即纪录片。
- **rollout.smoke** [core, level 2] — 6.3 是否有冒烟清单与观察指标？
  - evidence `6.3 上线验证与冒烟`: "- 纪录片回归：用《文艺复兴的解放》样本构建，确认进度仍为“叙事脉络 / 章节音频”、缓存目录无 '-movie'、manifest 无 'content_type'、报告文案不变。 - 电影冒烟：用一部本地电影 SRT 构建 '--content-type movie'，人工检查 6–12 段、剧情顺序、剧透完整性、选词与文案。 - 自动化：'uv run pytest'、'uv run ruff check src tests'；新增内容类型、提示词、链路、缓存隔离与渲染测试。 - 观察指标：纪录片回归失败数 = 0；电影样本章节数在 6–12；电影 HTML 中“内容脉络”出现次数 = 0；同一字幕双题材构建产生 2 个缓存目录（'<sha16>' 与 '<sha16>-movie'）。"
  - normalized: "- 纪录片回归:用《文艺复兴的解放》样本构建,确认进度仍为“叙事脉络 / 章节音频”、缓存目录无 '-movie'、manifest 无 'content_type'、报告文案不变。 - 电影冒烟:用一部本地电影 SRT 构建 '--content-type movie',人工检查 6–12 段、剧情顺序、剧透完整性、选词与文案。 - 自动化:'uv run pytest'、'uv run ruff check src tests';新增内容类型、提示词、链路、缓存隔离与渲染测试。 - 观察指标:纪录片回归失败数 = 0;电影样本章节数在 6–12;电影 HTML 中“内容脉络”出现次数 = 0;同一字幕双题材构建产生 2 个缓存目录('<sha16>' 与 '<sha16>-movie')。"
  - rationale: 6.3 给出纪录片回归与电影冒烟步骤、自动化命令，以及失败数、章节数、关键词次数和缓存目录数等观察指标。
- **rollout.rollback_trigger** [core, level 2] — 6.4 回滚触发条件是否是可观测数字？
  - evidence `6.4 回滚与熔断`: "- **触发条件（任一满足）**：纪录片回归用例失败数 > 0；电影构建连续 3 次出现章节数越界；已发布报告 5xx 比例连续 5 分钟 > 1%；同一字幕缓存目录出现非预期的第三种后缀。"
  - normalized: "- **触发条件(任一满足)**:纪录片回归用例失败数 > 0;电影构建连续 3 次出现章节数越界;已发布报告 5xx 比例连续 5 分钟 > 1%;同一字幕缓存目录出现非预期的第三种后缀。"
  - rationale: 6.4 的触发条件均为可观测数字：回归失败数 > 0、连续 3 次越界、5xx 连续 5 分钟 > 1% 等。
- **rollout.rollback_steps** [core, level 2] — 6.4 回滚步骤是否可执行？
  - evidence `6.4 回滚与熔断`: "- **回滚步骤**：   1. 切回内容类型改动前的稳定提交：'git checkout 3d06eca'，执行 'uv sync'。   2. 重新安装本地 CLI：'uv tool install --force --python 3.12 .'。   3. 移走或删除 '~/.cache/situlearn/<sha16>-movie' 目录，避免旧版本误读电影缓存。   4. 用回滚后的 CLI 重新构建并发布受影响的报告目录（如需要），确认旧报告 URL 与离线 HTML 仍可打开。"
  - normalized: "- **回滚步骤**: 1. 切回内容类型改动前的稳定提交:'git checkout 3d06eca',执行 'uv sync'。 2. 重新安装本地 CLI:'uv tool install --force --python 3.12 .'。 3. 移走或删除 '~/.cache/situlearn/<sha16>-movie' 目录,避免旧版本误读电影缓存。 4. 用回滚后的 CLI 重新构建并发布受影响的报告目录(如需要),确认旧报告 URL 与离线 HTML 仍可打开。"
  - rationale: 6.4 给出 4 步可执行回滚步骤，包含 git checkout、uv sync、uv tool install 与缓存目录清理。

## 替代方案诚实 (alternatives)

- **alts.status_quo** [core, level 2] — 第 7 章是否有 Status Quo 及其成本/风险？
  - evidence `7. 替代方案与权衡`: "本章先评估 Status Quo（只支持纪录片）的成本与风险，再评估自动识别与动态 Pydantic 模型两个被否决方案，最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径；方案 B 因结果不可复现被淘汰；方案 C 因动态模型复杂度高被淘汰；矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D：显式 ContentProfile + 独立 PromptSet，与第 2 章 Goals 和第 3 章架构选型一致。"
  - normalized: "本章先评估 Status Quo(只支持纪录片)的成本与风险,再评估自动识别与动态 Pydantic 模型两个被否决方案,最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径;方案 B 因结果不可复现被淘汰;方案 C 因动态模型复杂度高被淘汰;矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D:显式 ContentProfile + 独立 PromptSet,与第 2 章 Goals 和第 3 章架构选型一致。"
  - rationale: 第 7 章开头评估 Status Quo（只支持纪录片）并明确其成本是电影报告继续使用纪录片口径。
- **alts.rejected** [core, level 2] — 第 7 章是否至少有一个被否决方案，且淘汰原因对应当前约束？
  - evidence `7. 替代方案与权衡`: "本章先评估 Status Quo（只支持纪录片）的成本与风险，再评估自动识别与动态 Pydantic 模型两个被否决方案，最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径；方案 B 因结果不可复现被淘汰；方案 C 因动态模型复杂度高被淘汰；矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D：显式 ContentProfile + 独立 PromptSet，与第 2 章 Goals 和第 3 章架构选型一致。"
  - normalized: "本章先评估 Status Quo(只支持纪录片)的成本与风险,再评估自动识别与动态 Pydantic 模型两个被否决方案,最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径;方案 B 因结果不可复现被淘汰;方案 C 因动态模型复杂度高被淘汰;矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D:显式 ContentProfile + 独立 PromptSet,与第 2 章 Goals 和第 3 章架构选型一致。"
  - rationale: 第 7 章开头说明方案 B 因结果不可复现、方案 C 因动态模型复杂度高被淘汰，原因对应当前可复现性与实现复杂度约束。
- **alts.matrix** [core, level 2] — 第 7 章是否有与约束对应的权衡矩阵？
  - evidence `7. 替代方案与权衡`: "本章先评估 Status Quo（只支持纪录片）的成本与风险，再评估自动识别与动态 Pydantic 模型两个被否决方案，最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径；方案 B 因结果不可复现被淘汰；方案 C 因动态模型复杂度高被淘汰；矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D：显式 ContentProfile + 独立 PromptSet，与第 2 章 Goals 和第 3 章架构选型一致。"
  - normalized: "本章先评估 Status Quo(只支持纪录片)的成本与风险,再评估自动识别与动态 Pydantic 模型两个被否决方案,最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径;方案 B 因结果不可复现被淘汰;方案 C 因动态模型复杂度高被淘汰;矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D:显式 ContentProfile + 独立 PromptSet,与第 2 章 Goals 和第 3 章架构选型一致。"
  - rationale: 第 7 章开头说明用权衡矩阵对比方案，维度为电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度，均对应当前约束。
- **alts.consistency** [core, level 2] — 第 7 章结论是否与 Goals、架构选型一致？
  - evidence `7. 替代方案与权衡`: "本章先评估 Status Quo（只支持纪录片）的成本与风险，再评估自动识别与动态 Pydantic 模型两个被否决方案，最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径；方案 B 因结果不可复现被淘汰；方案 C 因动态模型复杂度高被淘汰；矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D：显式 ContentProfile + 独立 PromptSet，与第 2 章 Goals 和第 3 章架构选型一致。"
  - normalized: "本章先评估 Status Quo(只支持纪录片)的成本与风险,再评估自动识别与动态 Pydantic 模型两个被否决方案,最后用权衡矩阵对比显式 ContentProfile 方案。Status Quo 的成本是电影报告继续使用纪录片口径;方案 B 因结果不可复现被淘汰;方案 C 因动态模型复杂度高被淘汰;矩阵维度是电影可用性、可复现性、实现复杂度、旧行为兼容与阶段契合度。最终选择方案 D:显式 ContentProfile + 独立 PromptSet,与第 2 章 Goals 和第 3 章架构选型一致。"
  - rationale: 第 7 章结论明确最终选择方案 D，并声明与第 2 章 Goals 和第 3 章架构选型一致。

## 跨章自洽 (cross_consistency)

- **x.goals_trace** [core, level 2] — 后续章节是否逐条回应 Goals？
  - evidence `全文`: "- CLI：'situlearn build <input.srt> --out <dir> [--content-type documentary\|movie]'；默认 'documentary'；未知取值由 argparse 'choices' 拒绝，退出码 2。 - 构建入口：'build_report(input_path, out_dir, *, content_type=documentary, terms_min=None, terms_max=None, no_audio=False, force=False, cache_root=None, progress=None)'；'terms_min/max' 为 'None' 时从 profile 取默认值。"
  - normalized: "- CLI:'situlearn build <input.srt> --out <dir> [--content-type documentary\|movie]';默认 'documentary';未知取值由 argparse 'choices' 拒绝,退出码 2。 - 构建入口:'build_report(input_path, out_dir, *, content_type=documentary, terms_min=None, terms_max=None, no_audio=False, force=False, cache_root=None, progress=None)';'terms_min/max' 为 'None' 时从 profile 取默认值。"
  - evidence `全文`: "- 缓存目录：'<cache_root>/<字幕 sha256 前 16 位><cache_suffix>'。纪录片后缀为空，路径与现状一致；电影为 '<sha16>-movie'。 - LLM 阶段文件仍为 'narrative-<prompt_version>.json'、'terms-<prompt_version>.json'、'gloss-<prompt_version>.json'；目录级隔离同时保护未版本化的 'dictionary.json' 与 'human_audio.json'。"
  - normalized: "- 缓存目录:'<cache_root>/<字幕 sha256 前 16 位><cache_suffix>'。纪录片后缀为空,路径与现状一致;电影为 '<sha16>-movie'。 - LLM 阶段文件仍为 'narrative-<prompt_version>.json'、'terms-<prompt_version>.json'、'gloss-<prompt_version>.json';目录级隔离同时保护未版本化的 'dictionary.json' 与 'human_audio.json'。"
  - evidence `全文`: "- 'README.md'：补充 '--content-type' 用法、电影示例、缓存隔离与同字幕发布覆盖限制。 - 'docs/architecture/system.md'：加入 Content Profile 组件与纪录片/电影的目标差异。 - 'docs/runbooks/publish-report.md'：说明同一字幕双题材“最后发布生效”。 - 'docs/specs/README.md'：登记 SPEC-003 及其 tasks 链接。"
  - normalized: "- 'README.md':补充 '--content-type' 用法、电影示例、缓存隔离与同字幕发布覆盖限制。 - 'docs/architecture/system.md':加入 Content Profile 组件与纪录片/电影的目标差异。 - 'docs/runbooks/publish-report.md':说明同一字幕双题材“最后发布生效”。 - 'docs/specs/README.md':登记 SPEC-003 及其 tasks 链接。"
  - rationale: 每个 Goal 都能在后续章节找到落点：G1→4.4、G2→4.7、G3→4.2、G4→4.8、G5→6.5。
- **x.nfr_arch** [core, level 2] — NFR 与架构、选型是否一致？
  - evidence `全文`: "- 分型不新增 LLM 调用轮次；同一字幕的构建耗时增量应小于 1%（仅多一次 profile 解析）[estimated]。验收：全缓存重建耗时与改动前基线相差小于 1 秒。 - 缓存隔离使同一字幕的两种题材不能互相复用 LLM 产物，这是正确性取舍；单个题材内部的缓存命中率应与改动前相同 [estimated]。验收：同一题材连续构建两次，第二次的叙事、术语与释义阶段均显示缓存命中。"
  - normalized: "- 分型不新增 LLM 调用轮次;同一字幕的构建耗时增量应小于 1%(仅多一次 profile 解析)[estimated]。验收:全缓存重建耗时与改动前基线相差小于 1 秒。 - 缓存隔离使同一字幕的两种题材不能互相复用 LLM 产物,这是正确性取舍;单个题材内部的缓存命中率应与改动前相同 [estimated]。验收:同一题材连续构建两次,第二次的叙事、术语与释义阶段均显示缓存命中。"
  - evidence `全文`: "- 纪录片提示词常量、manifest 'config' 字段顺序、缓存路径、TTS 缓存键与报告文案保持逐字节兼容。验收：改动前后的纪录片 manifest 与离线 HTML 对比无差异（时间戳除外）。"
  - normalized: "- 纪录片提示词常量、manifest 'config' 字段顺序、缓存路径、TTS 缓存键与报告文案保持逐字节兼容。验收:改动前后的纪录片 manifest 与离线 HTML 对比无差异(时间戳除外)。"
  - rationale: NFR 与架构一致：5.2 不新增 LLM 轮次对应 3.4 的 profile 选择，5.1 兼容性对应 3.5 的不变清单。
- **x.rollback_release** [core, level 2] — 回滚与发布策略是否一致？
  - evidence `全文`: "- **触发条件（任一满足）**：纪录片回归用例失败数 > 0；电影构建连续 3 次出现章节数越界；已发布报告 5xx 比例连续 5 分钟 > 1%；同一字幕缓存目录出现非预期的第三种后缀。 - **回滚步骤**：   1. 切回内容类型改动前的稳定提交：'git checkout 3d06eca'，执行 'uv sync'。   2. 重新安装本地 CLI：'uv tool install --force --python 3.12 .'。   3. 移走或删除 '~/.cache/situlearn/<sha16>-movie' 目录，避免旧版本误读电影缓存。   4. 用回滚后的 CLI 重新构建并发布受影响的报告目录（如需要），确认旧报告 URL 与离线 HTML 仍可打开。"
  - normalized: "- **触发条件(任一满足)**:纪录片回归用例失败数 > 0;电影构建连续 3 次出现章节数越界;已发布报告 5xx 比例连续 5 分钟 > 1%;同一字幕缓存目录出现非预期的第三种后缀。 - **回滚步骤**: 1. 切回内容类型改动前的稳定提交:'git checkout 3d06eca',执行 'uv sync'。 2. 重新安装本地 CLI:'uv tool install --force --python 3.12 .'。 3. 移走或删除 '~/.cache/situlearn/<sha16>-movie' 目录,避免旧版本误读电影缓存。 4. 用回滚后的 CLI 重新构建并发布受影响的报告目录(如需要),确认旧报告 URL 与离线 HTML 仍可打开。"
  - evidence `全文`: "- 单机 CLI 工具，按版本发布；无服务端部署变更。因为没有常驻流量，不设置金丝雀或百分比灰度，灰度等价于“先在个人样本上构建并检查，再升级本地工具”。 - 旧的已发布报告继续由服务端按纪录片渲染；新构建的电影报告需要更新后的 CLI 构建并重新发布。"
  - normalized: "- 单机 CLI 工具,按版本发布;无服务端部署变更。因为没有常驻流量,不设置金丝雀或百分比灰度,灰度等价于“先在个人样本上构建并检查,再升级本地工具”。 - 旧的已发布报告继续由服务端按纪录片渲染;新构建的电影报告需要更新后的 CLI 构建并重新发布。"
  - rationale: 6.4 的回滚步骤与 6.1 的按版本发布、无常驻服务一致；回滚通过切回稳定提交并重装 CLI 完成。

## 证据卫生 (evidence_hygiene)

- **x.no_placeholders** [core, level 2] — 是否没有把 无 / ... / 待补充 / TBD 当作实质回答？
  - evidence `全文`: "- 电影章节下限 6 是否对短片过严；先用 6–12，真实样本不足时只调 profile。 - 电影词条范围是否应高于 30–80；本次沿用，profile 已为后续调整留口。 - 同一字幕双题材并存是否需要服务端复合 'report_key'；本次标为 Deferred to Phase 2。 - 是否需要 '--title' 显式片名；本次先用字幕文件名作线索，效果不足再补。"
  - normalized: "- 电影章节下限 6 是否对短片过严;先用 6–12,真实样本不足时只调 profile。 - 电影词条范围是否应高于 30–80;本次沿用,profile 已为后续调整留口。 - 同一字幕双题材并存是否需要服务端复合 'report_key';本次标为 Deferred to Phase 2。 - 是否需要 '--title' 显式片名;本次先用字幕文件名作线索,效果不足再补。"
  - evidence `全文`: "- 不迁移旧 manifest；'config.content_type' 缺失即纪录片。 - 不清理旧缓存；纪录片缓存路径不变，继续命中。 - 不升级 'schema_version'。"
  - normalized: "- 不迁移旧 manifest;'config.content_type' 缺失即纪录片。 - 不清理旧缓存;纪录片缓存路径不变,继续命中。 - 不升级 'schema_version'。"
  - rationale: 全文未发现以 无/.../待补充/TBD 充当实质回答；附录未决问题每项都给出本次决定，标为 Deferred 的也有明确归属。
- **x.no_code** [core, level 2] — 是否没有堆砌实现代码、测试日志或偶发报错？
  - evidence `全文`: "'''mermaid graph TD     CLI[CLI --content-type] --> Profile[ContentProfile 解析]     Profile --> Pipeline[Build Pipeline]     Pipeline --> Narrative[Narrative Planner PromptSet]     Pipeline --> Vocab[Vocabulary / Gloss PromptSet]     Pipeline --> Cache[(Content-type 缓存命名空间)]     Pipeline --> TTS[TTS Style]     Pipeline --> Manifest[manifest.json config.content_type]     Manifest --> Offline[离线报告 labels]     Manifest --> Web[Web 报告 labels + player] '''"
  - normalized: "'''mermaid graph TD CLI[CLI --content-type] --> Profile[ContentProfile 解析] Profile --> Pipeline[Build Pipeline] Pipeline --> Narrative[Narrative Planner PromptSet] Pipeline --> Vocab[Vocabulary / Gloss PromptSet] Pipeline --> Cache[(Content-type 缓存命名空间)] Pipeline --> TTS[TTS Style] Pipeline --> Manifest[manifest.json config.content_type] Manifest --> Offline[离线报告 labels] Manifest --> Web[Web 报告 labels + player] '''"
  - evidence `全文`: "- CLI：'situlearn build <input.srt> --out <dir> [--content-type documentary\|movie]'；默认 'documentary'；未知取值由 argparse 'choices' 拒绝，退出码 2。 - 构建入口：'build_report(input_path, out_dir, *, content_type=documentary, terms_min=None, terms_max=None, no_audio=False, force=False, cache_root=None, progress=None)'；'terms_min/max' 为 'None' 时从 profile 取默认值。 - 渲染入口：'profile_for_manifest(manifest) -> ContentProfile'；只读取 'manifest.config'，不重新判断题材。 - 错误返回：'build_report' 的未知类型抛 'ValueError'，由 CLI 边界打印错误并返回 1；渲染路径不因未知题材抛错。"
  - normalized: "- CLI:'situlearn build <input.srt> --out <dir> [--content-type documentary\|movie]';默认 'documentary';未知取值由 argparse 'choices' 拒绝,退出码 2。 - 构建入口:'build_report(input_path, out_dir, *, content_type=documentary, terms_min=None, terms_max=None, no_audio=False, force=False, cache_root=None, progress=None)';'terms_min/max' 为 'None' 时从 profile 取默认值。 - 渲染入口:'profile_for_manifest(manifest) -> ContentProfile';只读取 'manifest.config',不重新判断题材。 - 错误返回:'build_report' 的未知类型抛 'ValueError',由 CLI 边界打印错误并返回 1;渲染路径不因未知题材抛错。"
  - rationale: 全文只有 mermaid 架构图、内联标识符和方法签名，没有实现代码块、测试日志或偶发报错堆砌。
- **x.numbers_sourced** [core, level 2] — 关键数字是否有出处，或标了 [estimated]？
  - evidence `全文`: "- 分型不新增 LLM 调用轮次；同一字幕的构建耗时增量应小于 1%（仅多一次 profile 解析）[estimated]。验收：全缓存重建耗时与改动前基线相差小于 1 秒。 - 缓存隔离使同一字幕的两种题材不能互相复用 LLM 产物，这是正确性取舍；单个题材内部的缓存命中率应与改动前相同 [estimated]。验收：同一题材连续构建两次，第二次的叙事、术语与释义阶段均显示缓存命中。"
  - normalized: "- 分型不新增 LLM 调用轮次;同一字幕的构建耗时增量应小于 1%(仅多一次 profile 解析)[estimated]。验收:全缓存重建耗时与改动前基线相差小于 1 秒。 - 缓存隔离使同一字幕的两种题材不能互相复用 LLM 产物,这是正确性取舍;单个题材内部的缓存命中率应与改动前相同 [estimated]。验收:同一题材连续构建两次,第二次的叙事、术语与释义阶段均显示缓存命中。"
  - evidence `全文`: "- 观察指标：纪录片回归失败数 = 0；电影样本章节数在 6–12；电影 HTML 中“内容脉络”出现次数 = 0；同一字幕双题材构建产生 2 个缓存目录（'<sha16>' 与 '<sha16>-movie'）。"
  - normalized: "- 观察指标:纪录片回归失败数 = 0;电影样本章节数在 6–12;电影 HTML 中“内容脉络”出现次数 = 0;同一字幕双题材构建产生 2 个缓存目录('<sha16>' 与 '<sha16>-movie')。"
  - rationale: 关键实测类数字均标 [estimated]（如构建耗时增量 <1%、缓存命中率），其余数字是设计阈值或验收指标，不冒充实测结果。
- **x.no_fabricated_refs** [core, level 2] — 是否没有捏造 SPEC 引用、depends_on 目标或 M<N>？
  - evidence `全文`: "depends_on:   - docs/architecture/system.md   - docs/specs/SPEC-001-subtitle-learning-report/spec.md updated_at: 2026-11-03"
  - normalized: "depends_on: - docs/architecture/system.md - docs/specs/SPEC-001-subtitle-learning-report/spec.md updated_at: 2026-11-03"
  - evidence `全文`: "\| 关联资源 \| [总体架构](../../architecture/system.md)；SPEC-001 字幕脉络与生词语音化；本地样本《文艺复兴的解放》 \|"
  - normalized: "\| 关联资源 \| [总体架构](../../architecture/system.md);SPEC-001 字幕脉络与生词语音化;本地样本《文艺复兴的解放》 \|"
  - rationale: 引用均指向仓库内可核实的架构文档、SPEC-001 路径与文件/提交，未出现 M<N> 或无法核实的依赖目标。

## Audit failures

None.
