# Spec Quality Report

- Target: `docs/specs/SPEC-002-report-web-publishing/spec.md`
- Rubric: 1.0.0 (`acb806c85c7a357f1cdfeaea80a8dc951333aefe5b630fe8576e0e0ce7f25947`)
- Target SHA-256: `886f24b477d4ba206061bb2dd1848e060400c8d55940802c6666a3e53f5ba51e`
- Reviewer session: `review-spec-002-20261102T103200Z`

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
  - evidence `1.1 系统现状`: "情景学习目前是一个本地 CLI 工具，负责把一份英文纪录片 '.srt' 字幕变成可离线打开的学习报告。当前技术栈是 Python 3.11+、uv、LangChain + DeepSeek、Jinja2 模板与本地文件缓存；没有常驻服务、没有数据库、没有账号体系，也没有服务端渲染的 Web 前端；现有报告是本地静态 HTML。"
  - normalized: "情景学习目前是一个本地 CLI 工具,负责把一份英文纪录片 '.srt' 字幕变成可离线打开的学习报告。当前技术栈是 Python 3.11+、uv、LangChain + DeepSeek、Jinja2 模板与本地文件缓存;没有常驻服务、没有数据库、没有账号体系,也没有服务端渲染的 Web 前端;现有报告是本地静态 HTML。"
  - rationale: 1.1 同时给出模块职责、六步核心流程与完整技术栈，三个要素均可直接核实。
- **bg.failure_chain** [core, level 2] — 1.2 是否有从触发到后果的分步失败链？
  - evidence `1.2 核心技术痛点`: "失败链按发生顺序如下：  1. 在 Mac 上执行 'situlearn build'，得到一份包含 'report.html'、'manifest.json' 与 'assets/audio/' 的报告目录。 2. 用户在通勤、家务或睡前想继续学习，拿起 iPad。 3. 报告只存在于 Mac 本地文件系统，iPad 上没有入口；用户也没有尝试过拷贝整个目录。 4. 用户只能回到桌前用 Mac，或直接放弃这次学习。 5. 下一次学习仍然绑定桌面，碎片时间持续浪费；未来公开分享也始终没有起点。"
  - normalized: "失败链按发生顺序如下: 1. 在 Mac 上执行 'situlearn build',得到一份包含 'report.html'、'manifest.json' 与 'assets/audio/' 的报告目录。 2. 用户在通勤、家务或睡前想继续学习,拿起 iPad。 3. 报告只存在于 Mac 本地文件系统,iPad 上没有入口;用户也没有尝试过拷贝整个目录。 4. 用户只能回到桌前用 Mac,或直接放弃这次学习。 5. 下一次学习仍然绑定桌面,碎片时间持续浪费;未来公开分享也始终没有起点。"
  - rationale: 1.2 用编号 1–5 给出从构建完成、设备切换到放弃学习的完整因果链。
- **bg.trigger** [core, level 2] — 1.3 是否解释了为什么现在做？
  - evidence `1.3 重构/设计动机`: "三个触发点在同一时间成立，所以现在做：  1. **使用触发**：用户希望在通勤、家务、睡前离开 Mac 继续学习，当前报告没有离开桌面的路径。 2. **设备触发**：iPad 是用户日常的主设备，学习材料如果只能在 Mac 上打开，使用频率会被桌面场景限制。 3. **分发触发**：用户希望未来公开分享，而本地目录没有 URL、没有发布入口、没有下架能力，公开分享无法启动。 4. **技术触发**：内容管线已经端到端跑通，报告数据与音频资产完整；用户已有云服务器、域名与 K3s 集群，缺的是发布与播放层，不是重新做内容生成。"
  - normalized: "三个触发点在同一时间成立,所以现在做: 1. **使用触发**:用户希望在通勤、家务、睡前离开 Mac 继续学习,当前报告没有离开桌面的路径。 2. **设备触发**:iPad 是用户日常的主设备,学习材料如果只能在 Mac 上打开,使用频率会被桌面场景限制。 3. **分发触发**:用户希望未来公开分享,而本地目录没有 URL、没有发布入口、没有下架能力,公开分享无法启动。 4. **技术触发**:内容管线已经端到端跑通,报告数据与音频资产完整;用户已有云服务器、域名与 K3s 集群,缺的是发布与播放层,不是重新做内容生成。"
  - rationale: 1.3 列出使用、设备、分发与技术四个触发点，并明确“同一时间成立，所以现在做”。
- **bg.non_goals** [core, level 2] — 1.4 是否写了不做的后果与本次非目标？
  - evidence `1.4 非目标`: "不做的后果已经在 1.2 写明：学习继续绑定 Mac，iPad 主设备无法使用，公开分享没有起点。本次明确不做：  - 网页上传字幕与服务器端构建（本次不做；构建继续在 Mac 本地完成）。 - 报告汇总首页、全站搜索与分类浏览（本次不做；每条报告只有独立公开链接）。"
  - normalized: "不做的后果已经在 1.2 写明:学习继续绑定 Mac,iPad 主设备无法使用,公开分享没有起点。本次明确不做: - 网页上传字幕与服务器端构建(本次不做;构建继续在 Mac 本地完成)。 - 报告汇总首页、全站搜索与分类浏览(本次不做;每条报告只有独立公开链接)。"
  - rationale: 1.4 先复述不做的三项后果，再逐条列出本次不做的范围。

## 痛点证据 (pain_evidence)

- **bg.pain_evidence** [core, level 2] — 1.2 是否有至少一条可核实的证据（事故、度量或引述）？
  - evidence `1.2 核心技术痛点`: "证据（引述）：用户描述触发场景时说：「想离开 Mac 继续学」「我不太喜欢被绑定，在桌子前看着我的Mac iPad才是我平时的那个主要设备」「公开分享无法启动」。这三条引述分别对应失败链的第 2、3、5 步。"
  - normalized: "证据(引述):用户描述触发场景时说:「想离开 Mac 继续学」「我不太喜欢被绑定,在桌子前看着我的Mac iPad才是我平时的那个主要设备」「公开分享无法启动」。这三条引述分别对应失败链的第 2、3、5 步。"
  - evidence `1.2 核心技术痛点`: "补充证据（仓库事实）：现有 'report.html.j2' 没有 Media Session、Service Worker 或播放进度持久化代码。"
  - normalized: "补充证据(仓库事实):现有 'report.html.j2' 没有 Media Session、Service Worker 或播放进度持久化代码。"
  - rationale: 用户引述按步对应失败链，仓库事实又直接支撑第 3 步与 iPad 播放层缺口。

## 目标可验收 (goal_verifiability)

- **goal.verifiable** [core, level 2] — 2.1 每个 Goal 是否都有验收方式？
  - evidence `2.1 目标`: "验收：用《文艺复兴的解放》报告执行发布，返回 '201' 与 'slug'；iPad Safari 17+ 打开该 URL，章节数、词条数与本地报告一致；'curl -I' 返回 '200' 且带 'X-Robots-Tag: noindex'。"
  - normalized: "验收:用《文艺复兴的解放》报告执行发布,返回 '201' 与 'slug';iPad Safari 17+ 打开该 URL,章节数、词条数与本地报告一致;'curl -I' 返回 '200' 且带 'X-Robots-Tag: noindex'。"
  - evidence `2.1 目标`: "验收：真机连续播放 10 分钟并锁屏，音频不中断；锁屏控制可暂停与继续；切到其它 App 30 秒后返回，播放位置连续；关闭页面再打开，进度恢复误差不超过 5 秒；主屏幕图标可启动。"
  - normalized: "验收:真机连续播放 10 分钟并锁屏,音频不中断;锁屏控制可暂停与继续;切到其它 App 30 秒后返回,播放位置连续;关闭页面再打开,进度恢复误差不超过 5 秒;主屏幕图标可启动。"
  - evidence `2.1 目标`: "验收：注入中断上传，旧 URL 仍返回 '200' 且音频完整；重复发布返回同一 'slug' 且 'replaced=true'；下架后返回 '410'；无令牌发布返回 '401'；100 MB 报告发布完成时间小于 5 分钟 [estimated]。"
  - normalized: "验收:注入中断上传,旧 URL 仍返回 '200' 且音频完整;重复发布返回同一 'slug' 且 'replaced=true';下架后返回 '410';无令牌发布返回 '401';100 MB 报告发布完成时间小于 5 分钟 [estimated]。"
  - evidence `2.1 目标`: "验收：内容对照清单 100% 通过；宽度扫描 0 处横向滚动；键盘可完成播放、暂停、章节切换与词条筛选；正文对比度不低于 4.5:1。"
  - normalized: "验收:内容对照清单 100% 通过;宽度扫描 0 处横向滚动;键盘可完成播放、暂停、章节切换与词条筛选;正文对比度不低于 4.5:1。"
  - evidence `2.1 目标`: "验收：'/healthz' 与 '/readyz' 返回 '200'；滚动更新与回滚各在 10 分钟内完成；日志可按 'request_id' 串起一次发布；备份恢复演练能在 2 小时内恢复最近一份报告 [estimated]。"
  - normalized: "验收:'/healthz' 与 '/readyz' 返回 '200';滚动更新与回滚各在 10 分钟内完成;日志可按 'request_id' 串起一次发布;备份恢复演练能在 2 小时内恢复最近一份报告 [estimated]。"
  - rationale: G1–G5 每个 Goal 都带独立的“验收：”段落，覆盖命令、真机、状态码、宽度扫描与恢复演练。
- **goal.quantified** [core, level 2] — 2.1 是否至少有一个 Goal 有数字/单位/明确阈值？
  - evidence `2.1 目标`: "100 MB 报告发布完成时间小于 5 分钟 [estimated]"
  - normalized: "100 MB 报告发布完成时间小于 5 分钟 [estimated]"
  - rationale: G3 给出 100 MB 与 5 分钟的明确数值与单位，G2、G5 另有 5 秒、10 分钟等阈值。
- **goal.count** [extended, level 2] — 2.1 Goals 是否控制在 3–6 个？
  - evidence `2.1 目标`: "**G1 - 公网发布与访问（架构/交付）**"
  - normalized: "**G1 - 公网发布与访问(架构/交付)**"
  - evidence `2.1 目标`: "**G2 - iPad 看与听（体验/可靠性）**"
  - normalized: "**G2 - iPad 看与听(体验/可靠性)**"
  - evidence `2.1 目标`: "**G3 - 发布原子性与生命周期（可靠性）**"
  - normalized: "**G3 - 发布原子性与生命周期(可靠性)**"
  - evidence `2.1 目标`: "**G4 - 前端重做与移动端可用（架构/质量）**"
  - normalized: "**G4 - 前端重做与移动端可用(架构/质量)**"
  - evidence `2.1 目标`: "**G5 - 运维与可观测（运维）**"
  - normalized: "**G5 - 运维与可观测(运维)**"
  - rationale: 共 5 个 Goal，处于 3–6 区间，且每个都带类别标签（架构/交付、体验/可靠性、可靠性、架构/质量、运维）。

## 非目标边界 (non_goal_boundary)

- **nongoal.labeled** [core, level 2] — 2.2 每条 Non-Goal 是否标了本次不做或 Deferred to Phase 2？
  - evidence `2.2 非目标`: "- **NG1 - 网页构建**：不在网页上传 '.srt' 或触发服务器构建（本次不做）。对应 1.3 的“构建留在本地”，避免把 LLM/TTS 密钥与长任务搬进公网服务。 - **NG2 - 汇总首页**：不提供报告列表、全站搜索与分类浏览（本次不做）。对应 1.4 的“每条报告一个公开链接”，保持链接不可枚举。 - **NG3 - 多用户账号**：不做注册、登录、RBAC 与团队空间（Deferred to Phase 2）。当前只有单一管理令牌，公开侧只读。 - **NG4 - 跨设备进度**：不同步 iPad 与 Mac 的播放位置（本次不做）。进度保存在当前设备的 'localStorage'，避免引入账号与服务端会话。 - **NG5 - 高级播放能力**：不做句级同步高亮、语速控制与深色模式（本次不做）。章节级高亮已覆盖“边听边看”的最小需求。 - **NG6 - 原生 App**：不开发 iOS/iPadOS 原生客户端（Deferred to Phase 2）。PWA 主屏幕入口满足“像 App 一样打开”。 - **NG7 - 音频许可清理**：不替换或重新授权公开版词条音频（本次不做）。对应 1.3 的已接受风险；上线前保留一次人工复核。 - **NG8 - 搜索引擎收录**：不提交站点地图、不开放抓取、不提供公开目录（本次不做）。所有公开页返回 'noindex'。 - **NG9 - 高可用多副本**：不做多副本、多地域与数据库主从（Deferred to Phase 2）。SQLite 与单副本 PVC 是当前规模的合理边界。"
  - normalized: "- **NG1 - 网页构建**:不在网页上传 '.srt' 或触发服务器构建(本次不做)。对应 1.3 的“构建留在本地”,避免把 LLM/TTS 密钥与长任务搬进公网服务。 - **NG2 - 汇总首页**:不提供报告列表、全站搜索与分类浏览(本次不做)。对应 1.4 的“每条报告一个公开链接”,保持链接不可枚举。 - **NG3 - 多用户账号**:不做注册、登录、RBAC 与团队空间(Deferred to Phase 2)。当前只有单一管理令牌,公开侧只读。 - **NG4 - 跨设备进度**:不同步 iPad 与 Mac 的播放位置(本次不做)。进度保存在当前设备的 'localStorage',避免引入账号与服务端会话。 - **NG5 - 高级播放能力**:不做句级同步高亮、语速控制与深色模式(本次不做)。章节级高亮已覆盖“边听边看”的最小需求。 - **NG6 - 原生 App**:不开发 iOS/iPadOS 原生客户端(Deferred to Phase 2)。PWA 主屏幕入口满足“像 App 一样打开”。 - **NG7 - 音频许可清理**:不替换或重新授权公开版词条音频(本次不做)。对应 1.3 的已接受风险;上线前保留一次人工复核。 - **NG8 - 搜索引擎收录**:不提交站点地图、不开放抓取、不提供公开目录(本次不做)。所有公开页返回 'noindex'。 - **NG9 - 高可用多副本**:不做多副本、多地域与数据库主从(Deferred to Phase 2)。SQLite 与单副本 PVC 是当前规模的合理边界。"
  - rationale: NG1–NG9 每条都以“本次不做”或“Deferred to Phase 2”收束，没有未标注的条目。
- **nongoal.not_dumping_ground** [extended, level 2] — 2.2 非目标是否能追溯到痛点或边界？
  - evidence `2.2 非目标`: "- **NG1 - 网页构建**：不在网页上传 '.srt' 或触发服务器构建（本次不做）。对应 1.3 的“构建留在本地”，避免把 LLM/TTS 密钥与长任务搬进公网服务。 - **NG2 - 汇总首页**：不提供报告列表、全站搜索与分类浏览（本次不做）。对应 1.4 的“每条报告一个公开链接”，保持链接不可枚举。 - **NG3 - 多用户账号**：不做注册、登录、RBAC 与团队空间（Deferred to Phase 2）。当前只有单一管理令牌，公开侧只读。 - **NG4 - 跨设备进度**：不同步 iPad 与 Mac 的播放位置（本次不做）。进度保存在当前设备的 'localStorage'，避免引入账号与服务端会话。 - **NG5 - 高级播放能力**：不做句级同步高亮、语速控制与深色模式（本次不做）。章节级高亮已覆盖“边听边看”的最小需求。 - **NG6 - 原生 App**：不开发 iOS/iPadOS 原生客户端（Deferred to Phase 2）。PWA 主屏幕入口满足“像 App 一样打开”。 - **NG7 - 音频许可清理**：不替换或重新授权公开版词条音频（本次不做）。对应 1.3 的已接受风险；上线前保留一次人工复核。 - **NG8 - 搜索引擎收录**：不提交站点地图、不开放抓取、不提供公开目录（本次不做）。所有公开页返回 'noindex'。 - **NG9 - 高可用多副本**：不做多副本、多地域与数据库主从（Deferred to Phase 2）。SQLite 与单副本 PVC 是当前规模的合理边界。"
  - normalized: "- **NG1 - 网页构建**:不在网页上传 '.srt' 或触发服务器构建(本次不做)。对应 1.3 的“构建留在本地”,避免把 LLM/TTS 密钥与长任务搬进公网服务。 - **NG2 - 汇总首页**:不提供报告列表、全站搜索与分类浏览(本次不做)。对应 1.4 的“每条报告一个公开链接”,保持链接不可枚举。 - **NG3 - 多用户账号**:不做注册、登录、RBAC 与团队空间(Deferred to Phase 2)。当前只有单一管理令牌,公开侧只读。 - **NG4 - 跨设备进度**:不同步 iPad 与 Mac 的播放位置(本次不做)。进度保存在当前设备的 'localStorage',避免引入账号与服务端会话。 - **NG5 - 高级播放能力**:不做句级同步高亮、语速控制与深色模式(本次不做)。章节级高亮已覆盖“边听边看”的最小需求。 - **NG6 - 原生 App**:不开发 iOS/iPadOS 原生客户端(Deferred to Phase 2)。PWA 主屏幕入口满足“像 App 一样打开”。 - **NG7 - 音频许可清理**:不替换或重新授权公开版词条音频(本次不做)。对应 1.3 的已接受风险;上线前保留一次人工复核。 - **NG8 - 搜索引擎收录**:不提交站点地图、不开放抓取、不提供公开目录(本次不做)。所有公开页返回 'noindex'。 - **NG9 - 高可用多副本**:不做多副本、多地域与数据库主从(Deferred to Phase 2)。SQLite 与单副本 PVC 是当前规模的合理边界。"
  - rationale: 九条非目标各自附有对应 1.3/1.4 的约束或边界理由，没有无来源的垃圾桶式条目。

## 架构自洽 (architecture)

- **arch.solution_shape** [core, level 2] — 第 3 章是否有拓扑或等价的模块/数据流描述？
  - evidence `3. 架构设计与核心方案`: "'''mermaid flowchart LR     subgraph MAC["Mac 本地"]         SRT[".srt 字幕"] --> BUILD["现有构建管线<br/>parse → plan → extract → enrich → synthesize → assemble"]         BUILD --> DIR["报告目录<br/>manifest.json + assets/audio"]         DIR --> PUB["situlearn publish<br/>打包 + 计算 report_key"]     end      PUB -->\|"HTTPS + 管理令牌"\| ING["Traefik Ingress<br/>TLS 终止"]      subgraph K3S["K3s 集群"]         ING --> API["Web/API 服务<br/>FastAPI"]         API --> SSR["SSR 渲染器<br/>Jinja2 模板"]         API --> DB[("SQLite<br/>reports / versions")]         API --> STORE[("PVC<br/>不可变版本目录")]         API --> AUDIO["音频静态服务<br/>支持 Range"]         AUDIO --> STORE         SSR --> SHELL["PWA Shell<br/>manifest + service worker"]     end      IPAD["iPad Safari / 主屏幕 App"] --> ING     IPAD -->\|"页面与音频请求"\| API '''"
  - normalized: "'''mermaid flowchart LR subgraph MAC["Mac 本地"] SRT[".srt 字幕"] --> BUILD["现有构建管线<br/>parse → plan → extract → enrich → synthesize → assemble"] BUILD --> DIR["报告目录<br/>manifest.json + assets/audio"] DIR --> PUB["situlearn publish<br/>打包 + 计算 report_key"] end PUB -->\|"HTTPS + 管理令牌"\| ING["Traefik Ingress<br/>TLS 终止"] subgraph K3S["K3s 集群"] ING --> API["Web/API 服务<br/>FastAPI"] API --> SSR["SSR 渲染器<br/>Jinja2 模板"] API --> DB[("SQLite<br/>reports / versions")] API --> STORE[("PVC<br/>不可变版本目录")] API --> AUDIO["音频静态服务<br/>支持 Range"] AUDIO --> STORE SSR --> SHELL["PWA Shell<br/>manifest + service worker"] end IPAD["iPad Safari / 主屏幕 App"] --> ING IPAD -->\|"页面与音频请求"\| API '''"
  - rationale: 3.1 用 Mermaid 拓扑图给出 Mac 本地、Ingress、K3s 内 Web/API、SSR、SQLite、PVC、音频服务与 iPad 的数据流。
- **arch.topology** [extended, level 2] — 3.1 拓扑图是否让每个模块有一句职责？
  - evidence `3.1 总体架构`: "'''mermaid flowchart LR     subgraph MAC["Mac 本地"]         SRT[".srt 字幕"] --> BUILD["现有构建管线<br/>parse → plan → extract → enrich → synthesize → assemble"]         BUILD --> DIR["报告目录<br/>manifest.json + assets/audio"]         DIR --> PUB["situlearn publish<br/>打包 + 计算 report_key"]     end      PUB -->\|"HTTPS + 管理令牌"\| ING["Traefik Ingress<br/>TLS 终止"]      subgraph K3S["K3s 集群"]         ING --> API["Web/API 服务<br/>FastAPI"]         API --> SSR["SSR 渲染器<br/>Jinja2 模板"]         API --> DB[("SQLite<br/>reports / versions")]         API --> STORE[("PVC<br/>不可变版本目录")]         API --> AUDIO["音频静态服务<br/>支持 Range"]         AUDIO --> STORE         SSR --> SHELL["PWA Shell<br/>manifest + service worker"]     end      IPAD["iPad Safari / 主屏幕 App"] --> ING     IPAD -->\|"页面与音频请求"\| API '''"
  - normalized: "'''mermaid flowchart LR subgraph MAC["Mac 本地"] SRT[".srt 字幕"] --> BUILD["现有构建管线<br/>parse → plan → extract → enrich → synthesize → assemble"] BUILD --> DIR["报告目录<br/>manifest.json + assets/audio"] DIR --> PUB["situlearn publish<br/>打包 + 计算 report_key"] end PUB -->\|"HTTPS + 管理令牌"\| ING["Traefik Ingress<br/>TLS 终止"] subgraph K3S["K3s 集群"] ING --> API["Web/API 服务<br/>FastAPI"] API --> SSR["SSR 渲染器<br/>Jinja2 模板"] API --> DB[("SQLite<br/>reports / versions")] API --> STORE[("PVC<br/>不可变版本目录")] API --> AUDIO["音频静态服务<br/>支持 Range"] AUDIO --> STORE SSR --> SHELL["PWA Shell<br/>manifest + service worker"] end IPAD["iPad Safari / 主屏幕 App"] --> ING IPAD -->\|"页面与音频请求"\| API '''"
  - rationale: 拓扑图中的每个节点都带简短职责标签，3.2 又逐模块给出一句职责说明。
- **arch.change_set** [extended, level 2] — 第 3 章是否写清新增/改造/保持不变？
  - evidence `3. 架构设计与核心方案`: "- **新增**：'situlearn publish' 子命令、FastAPI Web/API 服务、SSR 页面模板、PWA Shell、SQLite 元数据、K3s/Kustomize 部署资源、发布与公开访问的监控指标。 - **改造**：CLI 增加发布入口；报告数据读取从“仅本地渲染”扩展为“本地渲染 + 服务端渲染”；总体架构文档第 2 节当前只描述本地 CLI，实施阶段同步改为“本地构建 + 公网只读 Web App”。 - **保持不变**：现有构建管线、'manifest.json' schema、音频生成与缓存、离线 'report.html' 产物、API Key 只存在本地环境变量的约束。现有本地报告仍可继续双击打开，不因本方案失效。"
  - normalized: "- **新增**:'situlearn publish' 子命令、FastAPI Web/API 服务、SSR 页面模板、PWA Shell、SQLite 元数据、K3s/Kustomize 部署资源、发布与公开访问的监控指标。 - **改造**:CLI 增加发布入口;报告数据读取从“仅本地渲染”扩展为“本地渲染 + 服务端渲染”;总体架构文档第 2 节当前只描述本地 CLI,实施阶段同步改为“本地构建 + 公网只读 Web App”。 - **保持不变**:现有构建管线、'manifest.json' schema、音频生成与缓存、离线 'report.html' 产物、API Key 只存在本地环境变量的约束。现有本地报告仍可继续双击打开,不因本方案失效。"
  - rationale: 3.5 用新增、改造、保持不变三段清单完整覆盖变更范围。
- **arch.rationale** [extended, level 2] — 关键选型是否有理由，详细对比指向第 7 章？
  - evidence `3.4 关键选型与约束`: "- **服务端采用 Python + FastAPI + Jinja2 服务端渲染，不引入 Node 前端构建链**：现有仓库已是 Python/uv，服务端渲染首屏快、部署面小，PWA 与 Media Session 用原生 JS 即可实现。与 SPA 的对比见 7.5。"
  - normalized: "- **服务端采用 Python + FastAPI + Jinja2 服务端渲染,不引入 Node 前端构建链**:现有仓库已是 Python/uv,服务端渲染首屏快、部署面小,PWA 与 Media Session 用原生 JS 即可实现。与 SPA 的对比见 7.5。"
  - rationale: 3.4 的关键选型逐条给出理由，并用“见 7.5”等指向第 7 章的详细对比。

## 详细设计完整 (detailed_design)

- **design.contract** [core, level 2] — 第 4 章是否至少有一份数据模型或接口契约？
  - evidence `4. 详细设计`: "\| 'Report' \| 'report_key' \| string(64) \| 是 \| 字幕 sha256 十六进制；唯一；来自 'manifest.source.sha256' \|"
  - normalized: "\| 'Report' \| 'report_key' \| string(64) \| 是 \| 字幕 sha256 十六进制;唯一;来自 'manifest.source.sha256' \|"
  - evidence `4. 详细设计`: "'POST /api/v1/reports'：'multipart/form-data'，字段 'archive'（'tar.gz'，≤100 MB）、'report_key'（64 位十六进制）、'schema_version'（主版本）。请求头 'Authorization: Bearer $PUBLISH_TOKEN'。成功 '201' 首次创建，'200' 覆盖更新，响应 '{slug, url, report_id, version, replaced}'。"
  - normalized: "'POST /api/v1/reports':'multipart/form-data',字段 'archive'('tar.gz',≤100 MB)、'report_key'(64 位十六进制)、'schema_version'(主版本)。请求头 'Authorization: Bearer $PUBLISH_TOKEN'。成功 '201' 首次创建,'200' 覆盖更新,响应 '{slug, url, report_id, version, replaced}'。"
  - rationale: 第 4 章同时提供 4.3 的数据模型字段表与 4.4 的发布接口契约。
- **design.data_model** [extended, level 2] — 4.3 数据模型是否有字段类型、必填与校验？
  - evidence `4.3 数据模型与契约`: "\| 实体 \| 字段 \| 类型 \| 必填 \| 校验与说明 \| \| --- \| --- \| --- \| --- \| --- \| \| 'Report' \| 'report_id' \| string(UUID) \| 是 \| 主键；服务端生成 \| \| 'Report' \| 'report_key' \| string(64) \| 是 \| 字幕 sha256 十六进制；唯一；来自 'manifest.source.sha256' \| \| 'Report' \| 'slug' \| string(64) \| 是 \| 唯一；小写字母、数字与连字符；创建后不变 \|"
  - normalized: "\| 实体 \| 字段 \| 类型 \| 必填 \| 校验与说明 \| \| --- \| --- \| --- \| --- \| --- \| \| 'Report' \| 'report_id' \| string(UUID) \| 是 \| 主键;服务端生成 \| \| 'Report' \| 'report_key' \| string(64) \| 是 \| 字幕 sha256 十六进制;唯一;来自 'manifest.source.sha256' \| \| 'Report' \| 'slug' \| string(64) \| 是 \| 唯一;小写字母、数字与连字符;创建后不变 \|"
  - rationale: 4.3 的字段表逐列给出类型、必填与校验说明，满足三项要求。
- **design.interface** [extended, level 2] — 4.4 接口是否有请求/响应/状态码或方法签名？
  - evidence `4.4 接口与协议`: "'POST /api/v1/reports'：'multipart/form-data'，字段 'archive'（'tar.gz'，≤100 MB）、'report_key'（64 位十六进制）、'schema_version'（主版本）。请求头 'Authorization: Bearer $PUBLISH_TOKEN'。成功 '201' 首次创建，'200' 覆盖更新，响应 '{slug, url, report_id, version, replaced}'。未授权 '401'；包过大 '413'；归档非法 '400'；manifest 缺失或引用资产缺失 '422'；并发发布同一 'report_key' 返回 '409'。"
  - normalized: "'POST /api/v1/reports':'multipart/form-data',字段 'archive'('tar.gz',≤100 MB)、'report_key'(64 位十六进制)、'schema_version'(主版本)。请求头 'Authorization: Bearer $PUBLISH_TOKEN'。成功 '201' 首次创建,'200' 覆盖更新,响应 '{slug, url, report_id, version, replaced}'。未授权 '401';包过大 '413';归档非法 '400';manifest 缺失或引用资产缺失 '422';并发发布同一 'report_key' 返回 '409'。"
  - evidence `4.4 接口与协议`: "'ReportPublisher.publish(report_dir: Path, server: URL, token: str) -> PublishResult'：负责打包、上传与错误映射。"
  - normalized: "'ReportPublisher.publish(report_dir: Path, server: URL, token: str) -> PublishResult':负责打包、上传与错误映射。"
  - rationale: 4.4 同时给出 HTTP 请求、响应、状态码与内部方法签名。
- **design.sequence** [extended, level 2] — 4.5 复杂流程是否有时序图或等价分步说明？
  - evidence `4.5 核心流程与时序`: "'''mermaid sequenceDiagram     participant U as 用户     participant C as situlearn publish     participant API as Web/API 服务     participant S as Report Store     participant D as SQLite     participant B as iPad Safari      U->>C: publish report-dir --server base-url     C->>C: 读取 manifest，计算 report_key，打包 tar.gz     C->>API: POST /api/v1/reports（Bearer token）     API->>API: 校验令牌、大小、归档结构、manifest、音频引用     API->>S: 写入 staging，移动到不可变版本目录     API->>D: 事务：创建或更新 Report，切换 current_version     D-->>API: 提交成功     API-->>C: 200/201 {slug, url, replaced}     API->>S: 旧版本移入 trash，24 小时后清理     C-->>U: 输出公开 URL     B->>API: GET /r/{slug}     API->>D: 读取当前版本     API->>S: 读取 manifest     API-->>B: SSR HTML + PWA 资源     B->>API: GET /r/{slug}/assets/{path}（Range）     API-->>B: 206 Partial Content '''"
  - normalized: "'''mermaid sequenceDiagram participant U as 用户 participant C as situlearn publish participant API as Web/API 服务 participant S as Report Store participant D as SQLite participant B as iPad Safari U->>C: publish report-dir --server base-url C->>C: 读取 manifest,计算 report_key,打包 tar.gz C->>API: POST /api/v1/reports(Bearer token) API->>API: 校验令牌、大小、归档结构、manifest、音频引用 API->>S: 写入 staging,移动到不可变版本目录 API->>D: 事务:创建或更新 Report,切换 current_version D-->>API: 提交成功 API-->>C: 200/201 {slug, url, replaced} API->>S: 旧版本移入 trash,24 小时后清理 C-->>U: 输出公开 URL B->>API: GET /r/{slug} API->>D: 读取当前版本 API->>S: 读取 manifest API-->>B: SSR HTML + PWA 资源 B->>API: GET /r/{slug}/assets/{path}(Range) API-->>B: 206 Partial Content '''"
  - evidence `4.5 核心流程与时序`: "异常路径：  1. **令牌无效**：在读取请求体前返回 '401'，不写 staging，不记录请求体。 2. **上传中断或归档非法**：删除 staging，不切换版本；旧版本继续服务。 3. **manifest 或音频引用缺失**：返回 '422'，staging 清理；不创建报告。 4. **数据库事务失败**：新版本目录保留在 'staging' 或标记为 'superseded'，'current_version' 不变；返回 '500' 并记录 'request_id'。 5. **并发发布同一 'report_key'**：数据库唯一约束或行锁拦截，返回 '409'；客户端提示稍后重试。 6. **旧版本清理失败**：只记录告警，不影响公开访问；下次清理任务重试。 7. **公开请求遇到下架**：返回 '410'，不暴露历史版本。 8. **音频 Range 非法**：返回 '416' 与 'Content-Range: bytes */<size>'，前端回退到整段请求。"
  - normalized: "异常路径: 1. **令牌无效**:在读取请求体前返回 '401',不写 staging,不记录请求体。 2. **上传中断或归档非法**:删除 staging,不切换版本;旧版本继续服务。 3. **manifest 或音频引用缺失**:返回 '422',staging 清理;不创建报告。 4. **数据库事务失败**:新版本目录保留在 'staging' 或标记为 'superseded','current_version' 不变;返回 '500' 并记录 'request_id'。 5. **并发发布同一 'report_key'**:数据库唯一约束或行锁拦截,返回 '409';客户端提示稍后重试。 6. **旧版本清理失败**:只记录告警,不影响公开访问;下次清理任务重试。 7. **公开请求遇到下架**:返回 '410',不暴露历史版本。 8. **音频 Range 非法**:返回 '416' 与 'Content-Range: bytes */<size>',前端回退到整段请求。"
  - rationale: 4.5 既有完整时序图，又用八条异常路径覆盖失败分支。
- **design.errors** [extended, level 2] — 4.6 每个错误码是否有触发场景与处理策略？
  - evidence `4.6 异常处理与错误码`: "\| 错误码 \| 触发场景 \| 处理策略 \| \| --- \| --- \| --- \| \| 'ERR_PUBLISH_UNAUTHORIZED' \| 缺失、错误或过期令牌 \| 返回 '401'；记录 'request_id' 与哈希 IP；不读取请求体 \| \| 'ERR_PUBLISH_DISABLED' \| 'PUBLISH_ENABLED=false' \| 返回 '503'；公开读取继续服务 \| \| 'ERR_PUBLISH_PAYLOAD_TOO_LARGE' \| 归档超过 100 MB 或文件数超过 2,000 \| 返回 '413'；客户端提示压缩或拆分 \| \| 'ERR_PUBLISH_INVALID_ARCHIVE' \| 非 gzip、路径越界、符号链接、绝对路径 \| 返回 '400'；清理 staging；客户端提示重新打包 \| \| 'ERR_PUBLISH_MANIFEST_INVALID' \| 'manifest.json' 缺失、无法解析或字段不全 \| 返回 '422'；不创建报告；返回首个字段错误 \| \| 'ERR_PUBLISH_SCHEMA_UNSUPPORTED' \| 'schema_version' 主版本不是 '1' \| 返回 '422'；提示升级/降级客户端 \| \| 'ERR_PUBLISH_ASSET_MISSING' \| 引用的音频文件不存在或大小为 0 \| 返回 '422'；列出前 10 个缺失路径 \| \| 'ERR_PUBLISH_CONFLICT' \| 同一 'report_key' 并发发布 \| 返回 '409'；客户端指数退避重试最多 3 次 \| \| 'ERR_PUBLISH_STORAGE_FULL' \| PVC 剩余空间低于 10% \| 返回 '507'；触发容量告警；公开读取继续 \| \| 'ERR_PUBLISH_DB_BUSY' \| SQLite 写锁超过 5 秒 \| 返回 '503'；客户端重试；记录 'request_id' \| \| 'ERR_REPORT_NOT_FOUND' \| slug 不存在 \| 返回 '404'；不区分从未存在与已删除（下架使用 '410'） \| \| 'ERR_REPORT_GONE' \| 报告已下架 \| 返回 '410'；页面提示报告已下架 \| \| 'ERR_RATE_LIMITED' \| 超过发布或公开请求频率 \| 返回 '429'；带 'Retry-After' \| \| 'ERR_AUDIO_RANGE_INVALID' \| 'Range' 格式错误或越界 \| 返回 '416'；带 'Content-Range: bytes */<size>' \| \| 'ERR_ASSET_PATH_INVALID' \| 公开资源路径含 '..' 或非法字符 \| 返回 '400'；不读取文件系统 \|"
  - normalized: "\| 错误码 \| 触发场景 \| 处理策略 \| \| --- \| --- \| --- \| \| 'ERR_PUBLISH_UNAUTHORIZED' \| 缺失、错误或过期令牌 \| 返回 '401';记录 'request_id' 与哈希 IP;不读取请求体 \| \| 'ERR_PUBLISH_DISABLED' \| 'PUBLISH_ENABLED=false' \| 返回 '503';公开读取继续服务 \| \| 'ERR_PUBLISH_PAYLOAD_TOO_LARGE' \| 归档超过 100 MB 或文件数超过 2,000 \| 返回 '413';客户端提示压缩或拆分 \| \| 'ERR_PUBLISH_INVALID_ARCHIVE' \| 非 gzip、路径越界、符号链接、绝对路径 \| 返回 '400';清理 staging;客户端提示重新打包 \| \| 'ERR_PUBLISH_MANIFEST_INVALID' \| 'manifest.json' 缺失、无法解析或字段不全 \| 返回 '422';不创建报告;返回首个字段错误 \| \| 'ERR_PUBLISH_SCHEMA_UNSUPPORTED' \| 'schema_version' 主版本不是 '1' \| 返回 '422';提示升级/降级客户端 \| \| 'ERR_PUBLISH_ASSET_MISSING' \| 引用的音频文件不存在或大小为 0 \| 返回 '422';列出前 10 个缺失路径 \| \| 'ERR_PUBLISH_CONFLICT' \| 同一 'report_key' 并发发布 \| 返回 '409';客户端指数退避重试最多 3 次 \| \| 'ERR_PUBLISH_STORAGE_FULL' \| PVC 剩余空间低于 10% \| 返回 '507';触发容量告警;公开读取继续 \| \| 'ERR_PUBLISH_DB_BUSY' \| SQLite 写锁超过 5 秒 \| 返回 '503';客户端重试;记录 'request_id' \| \| 'ERR_REPORT_NOT_FOUND' \| slug 不存在 \| 返回 '404';不区分从未存在与已删除(下架使用 '410') \| \| 'ERR_REPORT_GONE' \| 报告已下架 \| 返回 '410';页面提示报告已下架 \| \| 'ERR_RATE_LIMITED' \| 超过发布或公开请求频率 \| 返回 '429';带 'Retry-After' \| \| 'ERR_AUDIO_RANGE_INVALID' \| 'Range' 格式错误或越界 \| 返回 '416';带 'Content-Range: bytes */<size>' \| \| 'ERR_ASSET_PATH_INVALID' \| 公开资源路径含 '..' 或非法字符 \| 返回 '400';不读取文件系统 \|"
  - rationale: 4.6 的错误码表逐行给出触发场景与处理策略，覆盖发布、报告、限流与音频异常。

## NFR 可度量 (nfr)

- **nfr.measurable** [core, level 2] — 第 5 章每条 NFR 是否有数字、单位或验收方式？
  - evidence `5. 非功能性需求`: "- **页面首字节**：已发布报告首页在 2C2G 节点上的 TTFB 小于 300 ms [estimated]；验收：用 100 次请求取 P95。"
  - normalized: "- **页面首字节**:已发布报告首页在 2C2G 节点上的 TTFB 小于 300 ms [estimated];验收:用 100 次请求取 P95。"
  - evidence `5. 非功能性需求`: "- **进程恢复**：Pod 重启后 60 秒内恢复公开访问；验收：'kubectl delete pod' 后连续请求，记录恢复时间。"
  - normalized: "- **进程恢复**:Pod 重启后 60 秒内恢复公开访问;验收:'kubectl delete pod' 后连续请求,记录恢复时间。"
  - evidence `5. 非功能性需求`: "- **告警阈值**：5xx 比例连续 5 分钟大于 1%、发布失败连续 3 次、PVC 使用率大于 80%、Pod 重启次数 1 小时内大于 2 次；验收：用测试流量触发阈值并在告警通道看到记录。"
  - normalized: "- **告警阈值**:5xx 比例连续 5 分钟大于 1%、发布失败连续 3 次、PVC 使用率大于 80%、Pod 重启次数 1 小时内大于 2 次;验收:用测试流量触发阈值并在告警通道看到记录。"
  - evidence `5. 非功能性需求`: "- **限流**：发布 5 次/分钟/令牌，公开 120 次/分钟/IP；客户端 IP 只信任 Ingress 注入的 'X-Forwarded-For'，取最右侧由可信代理追加的地址；超限返回 '429' 与 'Retry-After'；验收：压测触发 429，等待后恢复。"
  - normalized: "- **限流**:发布 5 次/分钟/令牌,公开 120 次/分钟/IP;客户端 IP 只信任 Ingress 注入的 'X-Forwarded-For',取最右侧由可信代理追加的地址;超限返回 '429' 与 'Retry-After';验收:压测触发 429,等待后恢复。"
  - evidence `5. 非功能性需求`: "- **可访问性**：主要触控目标 ≥44×44 px；正文对比度 ≥4.5:1；播放与筛选可用键盘完成；验收：键盘走查与对比度工具检查。"
  - normalized: "- **可访问性**:主要触控目标 ≥44×44 px;正文对比度 ≥4.5:1;播放与筛选可用键盘完成;验收:键盘走查与对比度工具检查。"
  - rationale: 5.1–5.5 的每条 NFR 都带数字、单位或明确的“验收：”方式。
- **nfr.coverage** [core, level 2] — 第 5 章是否覆盖性能、可靠性、可观测性、安全，或说明不适用？
  - evidence `5. 非功能性需求`: "- **页面首字节**：已发布报告首页在 2C2G 节点上的 TTFB 小于 300 ms [estimated]；验收：用 100 次请求取 P95。"
  - normalized: "- **页面首字节**:已发布报告首页在 2C2G 节点上的 TTFB 小于 300 ms [estimated];验收:用 100 次请求取 P95。"
  - evidence `5. 非功能性需求`: "- **发布原子性**：任何发布失败都不能改变 'current_version'；验收：注入上传中断、校验失败、数据库失败三种故障，旧 URL 均返回 '200' 且音频完整。"
  - normalized: "- **发布原子性**:任何发布失败都不能改变 'current_version';验收:注入上传中断、校验失败、数据库失败三种故障,旧 URL 均返回 '200' 且音频完整。"
  - evidence `5. 非功能性需求`: "- **结构化日志**：JSON Lines，至少包含 'timestamp'、'level'、'request_id'、'route'、'method'、'status'、'duration_ms'、'slug'、'error_code'；不记录令牌、请求体与字幕原文。验收：抽一次发布与一次播放，日志字段齐全。"
  - normalized: "- **结构化日志**:JSON Lines,至少包含 'timestamp'、'level'、'request_id'、'route'、'method'、'status'、'duration_ms'、'slug'、'error_code';不记录令牌、请求体与字幕原文。验收:抽一次发布与一次播放,日志字段齐全。"
  - evidence `5. 非功能性需求`: "- **传输安全**：Ingress 强制 HTTPS，TLS 1.2+，HSTS 一年；HTTP 自动跳转 HTTPS；验收：'curl' 检查协议与响应头。"
  - normalized: "- **传输安全**:Ingress 强制 HTTPS,TLS 1.2+,HSTS 一年;HTTP 自动跳转 HTTPS;验收:'curl' 检查协议与响应头。"
  - rationale: 第 5 章分节覆盖性能、可靠性、可观测性与安全，并额外覆盖兼容性与可访问性。
- **nfr.honesty** [core, level 2] — 未实测的指标是否标了 [estimated] 或 未实现？
  - evidence `5. 非功能性需求`: "- **页面首字节**：已发布报告首页在 2C2G 节点上的 TTFB 小于 300 ms [estimated]；验收：用 100 次请求取 P95。"
  - normalized: "- **页面首字节**:已发布报告首页在 2C2G 节点上的 TTFB 小于 300 ms [estimated];验收:用 100 次请求取 P95。"
  - evidence `5. 非功能性需求`: "- **数据持久性**：报告与 SQLite 位于 PVC；每日备份，RPO 24 小时、RTO 2 小时 [estimated]；验收：从备份恢复一份报告并在临时命名空间打开。"
  - normalized: "- **数据持久性**:报告与 SQLite 位于 PVC;每日备份,RPO 24 小时、RTO 2 小时 [estimated];验收:从备份恢复一份报告并在临时命名空间打开。"
  - rationale: 尚未实测的延迟、并发、资源、RPO/RTO 等指标均带 [estimated]，没有写成已达成。

## 上线可回滚 (rollout)

- **rollout.release** [core, level 2] — 6.1 是否有发布策略与灰度节奏？
  - evidence `6.1 发布与灰度`: "本方案是新增公网服务，没有历史生产流量；发布以“访问范围逐步扩大”代替流量灰度：  - **Phase 1 - 本地联调**：在 Mac 上以本地进程运行 Web/API，使用局域网地址让 iPad 打开；验证 SSR、音频 Range、Media Session 与进度记忆。通过标准：G2、G4 的验收项在真机通过。 - **Phase 2 - K3s 单用户**：构建镜像并部署到 K3s，配置域名与 TLS；只由 alang 使用公开链接访问 48 小时。通过标准：G1、G3、G5 的验收项通过，5xx 为 0。"
  - normalized: "本方案是新增公网服务,没有历史生产流量;发布以“访问范围逐步扩大”代替流量灰度: - **Phase 1 - 本地联调**:在 Mac 上以本地进程运行 Web/API,使用局域网地址让 iPad 打开;验证 SSR、音频 Range、Media Session 与进度记忆。通过标准:G2、G4 的验收项在真机通过。 - **Phase 2 - K3s 单用户**:构建镜像并部署到 K3s,配置域名与 TLS;只由 alang 使用公开链接访问 48 小时。通过标准:G1、G3、G5 的验收项通过,5xx 为 0。"
  - rationale: 6.1 用四阶段访问范围扩大代替流量灰度，并给每阶段通过标准与观察时长。
- **rollout.migration** [core, level 2] — 6.2 是否有迁移/兼容方案，或说明无需迁移？
  - evidence `6.2 数据迁移与兼容性`: "- **存量数据**：服务端是新建，没有历史数据库需要迁移；现有本地报告目录不需要转换，首次 'situlearn publish' 即完成导入。"
  - normalized: "- **存量数据**:服务端是新建,没有历史数据库需要迁移;现有本地报告目录不需要转换,首次 'situlearn publish' 即完成导入。"
  - evidence `6.2 数据迁移与兼容性`: "- **manifest 兼容**：服务端接受 'schema_version' 主版本 '1'，对新增可选字段保持忽略；主版本变化时拒绝发布并提示升级客户端。现有 'manifest.json' 不新增必填字段。"
  - normalized: "- **manifest 兼容**:服务端接受 'schema_version' 主版本 '1',对新增可选字段保持忽略;主版本变化时拒绝发布并提示升级客户端。现有 'manifest.json' 不新增必填字段。"
  - rationale: 6.2 明确说明无需迁移历史数据库，并给出 manifest、slug、数据库与缓存的兼容策略。
- **rollout.smoke** [core, level 2] — 6.3 是否有冒烟清单与观察指标？
  - evidence `6.3 上线验证与冒烟`: "1. 'GET /healthz' 与 'GET /readyz' 均返回 '200'。 2. 用《文艺复兴的解放》报告执行 'situlearn publish'，返回 '201' 与公开 URL；重复发布返回同一 'slug' 且 'replaced=true'。"
  - normalized: "1. 'GET /healthz' 与 'GET /readyz' 均返回 '200'。 2. 用《文艺复兴的解放》报告执行 'situlearn publish',返回 '201' 与公开 URL;重复发布返回同一 'slug' 且 'replaced=true'。"
  - evidence `6.3 上线验证与冒烟`: "观察指标：'publish_success_rate'、'http_5xx_rate'、'http_request_duration_seconds{p95}'、'audio_206_rate'、'storage_bytes'、'report_count'、Pod 重启次数。"
  - normalized: "观察指标:'publish_success_rate'、'http_5xx_rate'、'http_request_duration_seconds{p95}'、'audio_206_rate'、'storage_bytes'、'report_count'、Pod 重启次数。"
  - rationale: 6.3 提供十步冒烟清单，并单列发布、5xx、P95、音频 206、存储与重启等观察指标。
- **rollout.rollback_trigger** [core, level 2] — 6.4 回滚触发条件是否是可观测数字？
  - evidence `6.4 回滚与熔断`: "- 公开服务 5xx 比例连续 5 分钟大于 1%。 - P95 页面响应连续 5 分钟大于 2 秒。 - PVC 使用率超过 90%，或存储写入失败。"
  - normalized: "- 公开服务 5xx 比例连续 5 分钟大于 1%。 - P95 页面响应连续 5 分钟大于 2 秒。 - PVC 使用率超过 90%,或存储写入失败。"
  - rationale: 回滚条件包含 5xx 比例、P95 延迟与 PVC 使用率等可观测数字。
- **rollout.rollback_steps** [core, level 2] — 6.4 回滚步骤是否可执行？
  - evidence `6.4 回滚与熔断`: "1. 将 'PUBLISH_ENABLED' 置为 'false' 并滚动更新，停止新的发布；公开读取继续服务。 2. 执行 'kubectl rollout undo deployment/situlearn -n situlearn'，回到上一个通过冒烟的镜像 tag。 3. 如果问题来自错误发布，查 'PublishEvent' 与 'ReportVersion'，把 'current_version' 指回上一版本；旧版本在 24 小时内仍保留，超过窗口则从备份恢复。"
  - normalized: "1. 将 'PUBLISH_ENABLED' 置为 'false' 并滚动更新,停止新的发布;公开读取继续服务。 2. 执行 'kubectl rollout undo deployment/situlearn -n situlearn',回到上一个通过冒烟的镜像 tag。 3. 如果问题来自错误发布,查 'PublishEvent' 与 'ReportVersion',把 'current_version' 指回上一版本;旧版本在 24 小时内仍保留,超过窗口则从备份恢复。"
  - rationale: 回滚步骤给出开关、kubectl 命令、版本指针回退与备份恢复路径，可直接执行。

## 替代方案诚实 (alternatives)

- **alts.status_quo** [core, level 2] — 第 7 章是否有 Status Quo 及其成本/风险？
  - evidence `7. 替代方案与权衡`: "- **成本与风险**：学习继续绑定桌面；iPad 主设备无法使用；公开分享没有入口；锁屏与切后台播放没有保障。达到阈值的信号已经出现：用户明确表示 iPad 是日常主设备，且公开分享无法启动。 - **结论**：不满足 G1 与 G2，淘汰。"
  - normalized: "- **成本与风险**:学习继续绑定桌面;iPad 主设备无法使用;公开分享没有入口;锁屏与切后台播放没有保障。达到阈值的信号已经出现:用户明确表示 iPad 是日常主设备,且公开分享无法启动。 - **结论**:不满足 G1 与 G2,淘汰。"
  - rationale: 7.1 明确给出 Status Quo 的成本、风险、阈值信号与淘汰结论。
- **alts.rejected** [core, level 2] — 第 7 章是否至少有一个被否决方案，且淘汰原因对应当前约束？
  - evidence `7. 替代方案与权衡`: "- **思路**：在 Mac 或家用服务器上起 Web 服务，通过 Tailscale 或内网穿透让 iPad 访问。 - **优点**：不暴露公网；部署简单；复用现有设备。 - **淘汰原因**：用户明确要求公网公开分享；私有网络无法让外部学习者访问；家庭网络与 Mac 休眠会直接影响可用性。"
  - normalized: "- **思路**:在 Mac 或家用服务器上起 Web 服务,通过 Tailscale 或内网穿透让 iPad 访问。 - **优点**:不暴露公网;部署简单;复用现有设备。 - **淘汰原因**:用户明确要求公网公开分享;私有网络无法让外部学习者访问;家庭网络与 Mac 休眠会直接影响可用性。"
  - rationale: 方案 B 的淘汰原因逐条对应用户要公网分享、外部访问与可用性约束。
- **alts.matrix** [core, level 2] — 第 7 章是否有与约束对应的权衡矩阵？
  - evidence `7. 替代方案与权衡`: "\| 维度 \| Status Quo \| 方案 A 静态托管 \| 方案 B 私有网络 \| 方案 C 网页构建 \| 方案 D SPA \| 方案 E 原生 App \| 当前选型 \| \| --- \| --- \| --- \| --- \| --- \| --- \| --- \| --- \| \| 离开 Mac 可访问 \| 否 \| 是 \| 是（仅私有网络） \| 是 \| 是 \| 是 \| **是** \| \| 公网公开分享 \| 否 \| 是 \| 否 \| 是 \| 是 \| 是 \| **是** \|"
  - normalized: "\| 维度 \| Status Quo \| 方案 A 静态托管 \| 方案 B 私有网络 \| 方案 C 网页构建 \| 方案 D SPA \| 方案 E 原生 App \| 当前选型 \| \| --- \| --- \| --- \| --- \| --- \| --- \| --- \| --- \| \| 离开 Mac 可访问 \| 否 \| 是 \| 是(仅私有网络) \| 是 \| 是 \| 是 \| **是** \| \| 公网公开分享 \| 否 \| 是 \| 否 \| 是 \| 是 \| 是 \| **是** \|"
  - rationale: 7.7 的矩阵维度直接对应离开 Mac、公网分享、令牌下架、后台播放、运维成本与密钥暴露等约束。
- **alts.consistency** [core, level 2] — 第 7 章结论是否与 Goals、架构选型一致？
  - evidence `7. 替代方案与权衡`: "矩阵结论与第 2 章一致：G1 要求公网发布与访问，排除 Status Quo 与方案 B；G3 要求令牌、原子覆盖与下架，排除方案 A；G2 要求 iPad 后台播放，方案 E 最强但成本过高，PWA 组合在本次范围内足够；方案 C 把密钥与付费构建搬到公网，风险与成本不匹配；方案 D 引入不必要的前端构建链。当前选型与 Goals、3.4 的关键选型一致。"
  - normalized: "矩阵结论与第 2 章一致:G1 要求公网发布与访问,排除 Status Quo 与方案 B;G3 要求令牌、原子覆盖与下架,排除方案 A;G2 要求 iPad 后台播放,方案 E 最强但成本过高,PWA 组合在本次范围内足够;方案 C 把密钥与付费构建搬到公网,风险与成本不匹配;方案 D 引入不必要的前端构建链。当前选型与 Goals、3.4 的关键选型一致。"
  - rationale: 7.7 的结论逐项引用 G1/G2/G3 与 3.4 的关键选型，未与 Goals 或架构矛盾。

## 跨章自洽 (cross_consistency)

- **x.goals_trace** [core, level 2] — 后续章节是否逐条回应 Goals？
  - evidence `全文`: "\| Goal \| 主要落点 \| \| --- \| --- \| \| G1 \| 3.1 总体架构；4.4 接口与协议；4.8 K3s 部署资源；6.3 冒烟 \| \| G2 \| 3.2 模块职责；4.7 前端页面与交互；5.5 兼容性与可访问性；6.3 冒烟 \| \| G3 \| 4.1 发布包与存储布局；4.3 数据模型与契约；4.5 核心流程与时序；4.6 错误码 \| \| G4 \| 4.7 前端页面与交互；5.5 兼容性与可访问性；6.3 内容对照 \| \| G5 \| 4.8 K3s 部署资源；5.3 可观测性；6.1 发布与灰度；6.4 回滚与熔断 \|"
  - normalized: "\| Goal \| 主要落点 \| \| --- \| --- \| \| G1 \| 3.1 总体架构;4.4 接口与协议;4.8 K3s 部署资源;6.3 冒烟 \| \| G2 \| 3.2 模块职责;4.7 前端页面与交互;5.5 兼容性与可访问性;6.3 冒烟 \| \| G3 \| 4.1 发布包与存储布局;4.3 数据模型与契约;4.5 核心流程与时序;4.6 错误码 \| \| G4 \| 4.7 前端页面与交互;5.5 兼容性与可访问性;6.3 内容对照 \| \| G5 \| 4.8 K3s 部署资源;5.3 可观测性;6.1 发布与灰度;6.4 回滚与熔断 \|"
  - rationale: 2.1 的映射表把 G1–G5 逐一指到架构、详细设计、NFR、上线与回滚章节。
- **x.nfr_arch** [core, level 2] — NFR 与架构、选型是否一致？
  - evidence `全文`: "- **部署到现有 K3s，使用原生 YAML/Kustomize，单副本 + PVC + SQLite**：用户已有集群与域名；报告访问是低并发只读，单副本足以支撑个人与小范围分享。多副本会引入 SQLite 写冲突与共享存储复杂度，留到 Phase 2。"
  - normalized: "- **部署到现有 K3s,使用原生 YAML/Kustomize,单副本 + PVC + SQLite**:用户已有集群与域名;报告访问是低并发只读,单副本足以支撑个人与小范围分享。多副本会引入 SQLite 写冲突与共享存储复杂度,留到 Phase 2。"
  - evidence `全文`: "- **数据持久性**：报告与 SQLite 位于 PVC；每日备份，RPO 24 小时、RTO 2 小时 [estimated]；验收：从备份恢复一份报告并在临时命名空间打开。"
  - normalized: "- **数据持久性**:报告与 SQLite 位于 PVC;每日备份,RPO 24 小时、RTO 2 小时 [estimated];验收:从备份恢复一份报告并在临时命名空间打开。"
  - evidence `全文`: "- **并发**：单副本支持 50 个并发音频流与 200 个每分钟页面请求而不出现 5xx [estimated]；验收：用 'hey' 或 'wrk' 压测 5 分钟，5xx 为 0。"
  - normalized: "- **并发**:单副本支持 50 个并发音频流与 200 个每分钟页面请求而不出现 5xx [estimated];验收:用 'hey' 或 'wrk' 压测 5 分钟,5xx 为 0。"
  - rationale: 单副本、PVC、SQLite 的架构选型与 5.1 并发、5.2 持久性指标相互对应，没有容量矛盾。
- **x.rollback_release** [core, level 2] — 回滚与发布策略是否一致？
  - evidence `全文`: "每个阶段使用不可变镜像 tag；K3s 部署使用 'kubectl apply -k'，发布前执行 'kubectl diff -k'，发布后等待 'rollout status'。"
  - normalized: "每个阶段使用不可变镜像 tag;K3s 部署使用 'kubectl apply -k',发布前执行 'kubectl diff -k',发布后等待 'rollout status'。"
  - evidence `全文`: "1. 将 'PUBLISH_ENABLED' 置为 'false' 并滚动更新，停止新的发布；公开读取继续服务。 2. 执行 'kubectl rollout undo deployment/situlearn -n situlearn'，回到上一个通过冒烟的镜像 tag。"
  - normalized: "1. 将 'PUBLISH_ENABLED' 置为 'false' 并滚动更新,停止新的发布;公开读取继续服务。 2. 执行 'kubectl rollout undo deployment/situlearn -n situlearn',回到上一个通过冒烟的镜像 tag。"
  - rationale: 6.4 的 rollout undo 与 6.1 的不可变镜像 tag、kubectl apply -k 流程一致。

## 证据卫生 (evidence_hygiene)

- **x.no_placeholders** [core, level 2] — 是否没有把 无 / ... / 待补充 / TBD 当作实质回答？
  - evidence `全文`: "\| 'SENTRY_DSN' \| 空 \| 可选错误上报；为空时只写本地日志 \|"
  - normalized: "\| 'SENTRY_DSN' \| 空 \| 可选错误上报;为空时只写本地日志 \|"
  - evidence `全文`: "**A1 - 域名与 TLS 细节**：用户已有域名与 K3s 集群，但具体 host、DNS 解析方式、Traefik 与 cert-manager 的现状未在本 Spec 固定；由 Kustomize overlay 的 'SITE_HOST' 注入，部署前确认证书签发路径。责任人是 alang。"
  - normalized: "**A1 - 域名与 TLS 细节**:用户已有域名与 K3s 集群,但具体 host、DNS 解析方式、Traefik 与 cert-manager 的现状未在本 Spec 固定;由 Kustomize overlay 的 'SITE_HOST' 注入,部署前确认证书签发路径。责任人是 alang。"
  - rationale: 全文未出现 TBD、待补充或省略号式占位；配置中的“空”是带说明的可选默认值，附录 A 的未决项均给出责任人、处理方式与阶段。
- **x.no_code** [core, level 2] — 是否没有堆砌实现代码、测试日志或偶发报错？
  - evidence `全文`: "新前端是服务端渲染的多页应用，共享同一套模板与播放器脚本；不使用前端框架，交互由原生 JavaScript 完成。"
  - normalized: "新前端是服务端渲染的多页应用,共享同一套模板与播放器脚本;不使用前端框架,交互由原生 JavaScript 完成。"
  - rationale: 正文以表格、Mermaid 图与设计性文字为主，没有实现代码块、测试日志或偶发报错堆栈。
- **x.numbers_sourced** [core, level 2] — 关键数字是否有出处，或标了 [estimated]？
  - evidence `全文`: "README 记录的真实样本结果为：60 分钟纪录片、8 个中文叙事章节、74 个词条、73/74 真人发音、82 个离线音频文件；完整构建约 9 分钟，全缓存重建小于 1 秒。"
  - normalized: "README 记录的真实样本结果为:60 分钟纪录片、8 个中文叙事章节、74 个词条、73/74 真人发音、82 个离线音频文件;完整构建约 9 分钟,全缓存重建小于 1 秒。"
  - evidence `全文`: "- **发布耗时**：100 MB 报告在同城网络下 5 分钟内完成 [estimated]；验收：发布真实报告并记录客户端耗时。"
  - normalized: "- **发布耗时**:100 MB 报告在同城网络下 5 分钟内完成 [estimated];验收:发布真实报告并记录客户端耗时。"
  - rationale: 样本指标注明来自 README，未实测的性能与容量数字普遍标有 [estimated]。
- **x.no_fabricated_refs** [core, level 2] — 是否没有捏造 SPEC 引用、depends_on 目标或 M<N>？
  - evidence `全文`: "depends_on:   - docs/architecture/system.md   - docs/specs/SPEC-001-subtitle-learning-report/spec.md"
  - normalized: "depends_on: - docs/architecture/system.md - docs/specs/SPEC-001-subtitle-learning-report/spec.md"
  - evidence `全文`: "- **Existing Build Pipeline**：保留 SPEC-001 的解析、规划、抽取、富化、合成与组装职责，本方案不改内容生成逻辑。"
  - normalized: "- **Existing Build Pipeline**:保留 SPEC-001 的解析、规划、抽取、富化、合成与组装职责,本方案不改内容生成逻辑。"
  - rationale: depends_on 只有 architecture/system.md 与 SPEC-001，且正文有对应引用；全文未出现 M<N> 形式。

## Audit failures

None.
