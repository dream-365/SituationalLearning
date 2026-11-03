---
type: tasks
status: In Progress
owner: alang
depends_on: []
spec: ./spec.md
spec_sha256: "f184c86262fd3f3277a33c1af7b72ab7715f2c824bda7368389a030ac856f8e6"
updated_at: 2026-11-03
---

# 情景学习 字幕学习报告内容类型分型 执行拆解

| ID | 任务 | 覆盖 | 依赖 | 写入 | 完成标准 | 验证 |
|---|---|---|---|---|---|---|
| T1 | 新增 `ContentType`、`ContentProfile` 与 `ReportLabels` 注册表 | G1 | — | src/situlearn/knowledge.py, src/situlearn/content.py | 两类 profile 可解析；旧 manifest 缺失类型时回退纪录片 | python -m pytest tests/test_content.py |
| T2 | 新增电影提示词与 `PromptSet` 选择 | G2 | T1 | src/situlearn/prompts.py | 纪录片常量逐字不变；电影模板含剧透、潜台词、剧情与台词选词要求 | python -m pytest tests/test_prompts.py |
| T3 | 链路与音频按 profile 选择提示词和语气 | G2 | T2 | src/situlearn/chains.py, src/situlearn/gloss.py, src/situlearn/audio.py | 电影叙事/修复/选词/释义使用电影模板；style 进入音频缓存键 | python -m pytest tests/test_chains.py tests/test_audio.py |
| T4 | CLI 新增 `--content-type` 并传入构建 | G1 | T1 | src/situlearn/cli.py | documentary 为默认值、movie 可选、非法值被 argparse 拒绝 | python -m pytest tests/test_pipeline.py -k movie |
| T5 | 缓存隔离、章节校验与 manifest 内容类型 | G4 | T3, T4 | src/situlearn/pipeline.py | 纪录片缓存路径不变；电影使用 -movie 目录；仅电影 manifest 写 content_type | python -m pytest tests/test_pipeline.py -k cache |
| T6 | 离线报告注入题材文案 | G3 | T1 | src/situlearn/report.py, src/situlearn/templates/report.html.j2 | 电影 HTML 出现剧情脉络/场景/回到本场；纪录片文案不变 | python -m pytest tests/test_report.py |
| T7 | Web 报告、章节页、词表与播放器注入题材文案 | G3 | T1 | src/situlearn/web/render.py, src/situlearn/web/templates/, src/situlearn/web/static/player.js | 电影 Web 页面与播放器使用电影文案；纪录片契约测试通过 | python -m pytest tests/test_web_render.py tests/test_web_player_contract.py |
| T8 | 更新 README、架构与发布说明 | G5 | T5, T6, T7 | README.md, docs/architecture/system.md, docs/runbooks/publish-report.md, docs/specs/README.md | 文档说明 --content-type 用法与同一字幕最后发布生效 | python -m pytest |
