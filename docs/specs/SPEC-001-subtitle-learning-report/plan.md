---
type: plan
status: Approved
owner: alang
depends_on: []
updated_at: 2026-11-02
---

# SPEC-001 实施计划

## 1. 计划范围与当前状态

- **目标**：把 SPEC-001 从 Draft 推进到 Phase 1 可运行，产出一份基于真实 srt 的离线学习报告。
- **Spec 状态**：Draft；独立质量评审 core 100.0；mdstandards phase 1 通过。
- **真实样本**：`文艺复兴解锁 The Renaissance Unchained p01 01 Gods, Myths and Oil Paintings [BV15i4y1U7uT_p1].en.srt`。
- **样本结构**：1,186 条 cue，59.7 分钟，UTF-8 无 BOM，LF 换行；62 条多行 cue；无 HTML 标签、无说话人标记；1,171 条不同文本；最大单条 73 字符。
- **关键发现**：大量 cue 在句子中间切断（首条以 `in` 结尾，下一条以 `Florence` 开头），Segmenter 必须先按标点与时间间隔合并成完整句子，再切语义段。
- **环境**：`DEEPSEEK_API_KEY` 与 `MIMO_API_KEY` 已设置；Python 3.11+、uv 与 ffmpeg 的可用性待 C0 检查。
- **TTS 调研**：已完成，结论见第 2 节。

## 2. 小米 mimo-v2.5-tts 调研结论

| 项 | 结论 |
| --- | --- |
| 接口 | `POST https://api.xiaomimimo.com/v1/chat/completions`，Chat Completions 兼容，不是 `/audio/speech` |
| 鉴权 | `api-key: $MIMO_API_KEY` 或 `Authorization: Bearer`；`tp-` Key 在部分环境用 Bearer 会 401，优先 `api-key` |
| 模型 | `mimo-v2.5-tts`（预置音色）；另有 `mimo-v2.5-tts-voiceclone` 与 `mimo-v2.5-tts-voicedesign` |
| 待合成文本 | 必须放在 `assistant` 消息；`user` 消息只放风格指令 |
| 音频参数 | `audio.voice` 与 `audio.format`；支持 `wav`、`mp3`、`pcm`、`pcm16` |
| 返回结构 | JSON；`choices[0].message.audio.data` 是 base64 音频；`transcript` 恒为 `null` |
| 预置音色 | `冰糖`（中文女）、`茉莉`（中文女）、`苏打`（中文男）、`白桦`（中文男）、`Mia`、`Chloe`、`Milo`、`Dean`（英文） |
| 上下文/输出 | 8K / 8K |
| 限流 | 100 RPM / 10M TPM |
| 语速 | 没有 `speed` 参数；用 `user` 风格指令，或本地 ffmpeg `atempo` 后处理 |
| 计费 | 官方页面写「限时免费」，未给额度、到期日或商业使用条款 |
| 连通测试 | 2026-11-02 通过：`冰糖` 音色、mp3、34,320 bytes、MPEG Layer III 64 kbps / 24 kHz / mono、`finish_reason=stop` |
| 本机工具 | `ffprobe` 当前因 whisper.cpp dylib 缺失不可用；v0.1 不依赖 ffmpeg，分块音频用章节播放列表 |
| 结论 | 可用于 v0.1；需要按 8K 上限分块、按 100 RPM 限速、默认 mp3；中英混读质量需人工试听确认 |

参考：

- [MiMo TTS API 参考](https://mimo.mi.com/docs/zh-CN/api/audio/tts)
- [MiMo 模型列表](https://mimo.mi.com/docs/zh-CN/quick-start/summary/model)
- [MiMo TTS 使用指南](https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/audio/speech-synthesis-v2.5)

### 2.1 DeepSeek 连通与结构化输出

- `deepseek-flash` 最小请求验证通过，返回 `model=deepseek-flash`。
- 模型元数据：`DeepSeek-V4.1-Flash`，上下文 1,048,576 tokens，最大输出 393,216 tokens，effort 默认 `high`。
- `with_structured_output` 默认 tool_choice 在 thinking mode 下返回 400：`Thinking mode does not support this tool_choice`。
- 改用 `method="json_mode"` 后，嵌套 Pydantic 模型解析成功。
- 实现约束：所有 LLM Chain 统一走 JSON mode + Pydantic 校验，`max_tokens` 设为 64,000。32,000 在 2 小时 40 分钟电影字幕上会被 thinking tokens 吃满（实测 reasoning 28,456 + 截断输出），导致 JSON 解析失败；模型最大输出为 393,216，64,000 留足余量。

## 3. 里程碑

| 里程碑 | 目标 | 预计 | 出口条件 |
| --- | --- | --- | --- |
| M0 决策与批准 | 用户确认关键选择，Spec 转 Approved | 0.5 天 | U1–U7 完成 |
| M1 骨架与连通 | 仓库骨架、uv、三个外部服务连通 | 1–2 天 | C1–C5 通过冒烟 |
| M2 主链路 | 解析、分段、脉络、抽词、词典 | 2–3 天 | C6–C8 在真实 srt 上产出 manifest |
| M3 语音与报告 | TTS、音频拼接、HTML、缓存 | 2–3 天 | C9–C12 产物可离线播放 |
| M4 真实样本验收 | 跑通真实 srt，人工评审 | 1–2 天 | G2–G5 通过 |
| M5 稳定与分享准备 | 错误处理、文档、冒烟、Phase 2 清单 | 1–2 天 | 冒烟清单全过 |

总工期约 7–12 人日 [estimated]，不含用户决策等待。

## 4. 任务清单

### 4.1 需要你确认或提供的任务（Owner: alang）

| ID | 任务 | 需要的决定或产出 | 阻塞 |
| --- | --- | --- | --- |
| U1 | 批准 Spec | 把 `spec.md` 从 `Draft` 改为 `Approved` | 全部编码 |
| U2 | 确认 DeepSeek 模型 | 已确认 `deepseek-flash`；是否改用 `deepseek-reasoner` | C5 |
| U3 | 确认 TTS 音色 | 默认 `冰糖`（中文女声）；备选 `白桦`（中文男声） | C9 |
| U4 | 确认 TTS 条款 | 接受「限时免费、无到期日、个人学习用途」 | C9 |
| U5 | 确认字幕版权边界 | 仅个人使用，还是允许分享报告 | M5 |
| U6 | 确认样本入库方式 | 建议 srt 放本地 `samples/` 并 gitignore，不提交到仓库 | C1 |
| U7 | 确认输出目录 | 默认 `reports/<srt-basename>/` | C11 |
| U8 | 验收真实样本报告 | 5 项脉络检查与 20 词抽检 | M4 |

### 4.2 实施任务（Owner: Claude）

| ID | 阶段 | 任务 | 验收 |
| --- | --- | --- | --- |
| C0 | M1 | 环境检查：`python3 --version`、`uv --version`、三个服务连通 | 版本满足；联网测试通过 |
| S1 | M0 | 根据 TTS 调研回写 Spec：请求形态、8K 分块、`audio_refs`、ffmpeg 可选 | Spec 更新并重跑质量评审 |
| C1 | M1 | 仓库骨架：pyproject、uv.lock、src、tests、templates、.gitignore | `uv sync --frozen` 成功 |
| C2 | M1 | SRT parser：编码回退、BOM/CRLF、多行 cue、半句 cue | 真实 srt 解析出 1,186 条 cue |
| C3 | M1 | Content segmenter：按标点与时间间隔合并句子再切段 | 首条 `in` 与下一条 `Florence` 合并为一个语义单元 |
| C4 | M1 | LangChain pipeline 骨架：LCEL、阶段缓存、run.log | 空实现跑通管线 |
| C5 | M1 | DeepSeek 接入：`ChatDeepSeek`、结构化输出、重试 | 一次真实调用返回合法 Pydantic 对象 |
| C6 | M2 | Narrative planner：4–8 章、中文口语、英文术语保留 | 真实 srt 产出 4–8 章中文讲稿 |
| C7 | M2 | Vocabulary extractor：30–80 词、分类、上下文、why_it_matters | 真实 srt 产出候选词表 |
| C8 | M2 | Lexicon enricher：词典、音标、中英释义、音频、署名 | 20 词抽检字段完整 |
| C9 | M3 | Xiaomi TTS adapter：assistant 文本、mp3、base64、8K 分块、100 RPM 限速 | 中英混读测试音频可播 |
| C10 | M3 | 音频分块与播放：每章可多段音频，HTML 播放器按序播放；缺失降级；v0.1 不依赖 ffmpeg | 每章音频可连续播放 |
| C11 | M3 | Report assembler：离线 HTML、章节播放、词条卡、筛选、页脚署名 | 断网可播 |
| C12 | M3 | Manifest 与缓存：schema_version、幂等、断点恢复 | 重跑 0 付费调用 |
| C13 | M4 | 测试：parser/segmenter/manifest 单测与 mock 集成 | CI 通过 |
| C14 | M4 | 真实样本跑通并产出指标 | 报告与指标摘要 |
| C15 | M4 | 按人工评审修复 | G2–G5 通过 |
| C16 | M5 | README、环境变量、用法、故障排查 | 新环境按文档可跑通 |

## 5. 关键路径

`U1 → S1 → C1 → C2 → C3 → C4 → C5 → C6/C7 → C8/C9 → C10/C11 → C14 → U8 → C15 → C16`

C2/C3 可以在等待 U2–U7 时先做，但按规范，Spec 未批准前不写生产代码；C0 的连通测试可以提前做。

## 6. 决策门

| 门 | 条件 | 不通过时 |
| --- | --- | --- |
| G0 | U1 批准 Spec | 不进入编码 |
| G1 | TTS 中英混读音频可接受 | 换 `白桦` 或调整风格指令 |
| G2 | 脉络 5 项检查至少 4 项通过 | 调提示词或换 `deepseek-reasoner` |
| G3 | 20 词抽检至少 80% 是关键卡点 | 调选词提示或调整分类权重 |
| G4 | 至少 95% 词条有音频，全部章节有音频 | 检查 TTS 限流、分块与兜底 |
| G5 | 断网可播放 | 修 HTML、CSP 与相对路径 |

## 7. 风险

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 中文音色读英文术语不自然 | 中英混读质量 | 先用 `冰糖` 与 `白桦` 各测一段；必要时在文本中加英文发音提示 |
| TTS 8K 上限 | 长章节合成失败 | 按句子分块，每块不超过 3,500 字符，合成后拼接 |
| TTS 无 speed 参数 | 无法直接调速 | v0.1 固定 1.0；需要时再引入 ffmpeg `atempo` |
| 本机 ffmpeg/ffprobe 不可用 | 影响音频拼接与变速 | v0.1 不依赖 ffmpeg；多段音频按章节播放；需要时修 Homebrew `ffmpeg-full` |
| TTS 100 RPM | 80 词加 8 章接近上限 | 串行或小并发加退避；词条音频缓存 |
| dictionaryapi.dev 媒体 502 | 真人发音下载失败 | 已实测 502；v0.1 按设计转 TTS 兜底，词典文本与音标仍可用 |
| dictionaryapi.dev 不可达 | 音标与真人发音缺失 | 换 Wiktionary API 或本地词典包；TTS 兜底 |
| DeepSeek 结构化输出不稳 | 解析失败 | Pydantic 校验加重试；必要时 JSON mode |
| 字幕版权与 TTS 条款 | 分享受限 | U4/U5 先确认；个人使用优先 |
| 免费期结束 | 成本上升 | 备选 TTS 加预算上限；接口已抽象 |

## 8. Phase 1 完成定义

- 真实 srt 在 15 分钟内生成报告 [estimated]。
- 脉络 4–8 章，中文口语，英文术语保留，音频 6–15 分钟。
- 词表 30–80 条，20 词抽检至少 80% 是关键卡点，字段完整率 100%。
- 至少 95% 词条有音频，全部章节有音频，断网可播。
- 重跑 `llm_calls=0`、`tts_calls=0`，重建小于 5 秒。
- 产物无密钥；页脚有词典与 TTS 署名。

## 9. 当前需要你做的

- U1–U7 已确认；剩余 **U8**：M4 时验收真实样本报告。
- S1 完成后，Spec 与 plan 转 `Approved`，进入 M1。

## 10. 已确认事项（2026-11-02）

- U1：批准，先做 S1 再开工。
- U2：DeepSeek 模型用 `deepseek-flash`；已用最小请求验证可用。
- U3：TTS 默认音色 `冰糖`。
- U4/U5：仅个人使用；接受小米 TTS 限时免费条款。
- U6：srt 不入库，放本地 `samples/` 并 gitignore。
- U7：输出目录 `reports/<srt-basename>/`。
- 连通验证：小米 TTS 返回 34,320 bytes MP3；DeepSeek 返回 `model=deepseek-flash`。

## 11. 当前进度（2026-11-02）

- C0 环境检查：完成；Python 3.12、uv 0.11.6、词典与 DeepSeek 可达。
- C1 骨架：完成；`uv sync --frozen` 成功。
- C2 SRT parser：完成；真实样本 1,186 条 cue。
- C3 Segmenter：完成；真实样本 90 个语义段。
- C5 DeepSeek：完成；`deepseek-flash` + JSON mode。
- C6 Narrative：真实样本 8 章，91.8 秒。
- C7 Vocabulary：真实样本 69 词，94.3 秒；分类分布合理。
- C8 Dictionary/Gloss：完成；真人音频 73/74（Oxford/Youdao）。
- C9 TTS adapter：完成，连通测试通过，仅残留词条与章节使用。
- C10/C11/C12：完成，真实音频与播放器已生成。
- C13 测试：20 passed，ruff 全绿。
- C14 真实样本：完成，结果见第 12 节。
- C15/C16：待用户验收与文档收尾。

## 12. 真实样本验收结果（2026-11-02）

- 输入：`samples/renaissance-unchained-p01.en.srt`。
- 全量首次构建：约 9 分钟（3 次 DeepSeek 调用 + 真人音频解析 + TTS）[estimated]。
- 修复/部分缓存运行：24.4 秒；全缓存重跑：0.1 秒（墙钟 0.95 秒）。
- 规模：1,186 cue → 90 个语义段 → 8 章 → 74 个词条。
- 播报稿：全中文，英文原词 0；英文只保留在 `key_terms` 与生词卡。
- 音频：82 个 MP3（8 章 + 74 词），清单与文件一一对应，缺失 0。
- 真人音频：73/74（Oxford 33 + Youdao 40），仅 `Renascita` 用 TTS；27 个多词词条播放关键词真人音并标注。
- 播放器：进度条、当前/总时长、剩余时间、跨章节连续播放。
- 报告：`reports/renaissance-p01/report.html`；旧版备份在 `reports/renaissance-p01-v1/`。
- 质量：20 个单测通过，ruff 全绿；外部闸门 phase 1 exit 0。
