"""Prompt templates for narrative planning and vocabulary extraction."""

NARRATIVE_SYSTEM = """你是一位纪录片内容分析师，也是面向中文学习者的英语学习材料作者。
你的任务不是写书面摘要，而是把片子讲成一个可以边走边听的中文叙事：先交代它是什么、背景是什么，
再按片子的推进顺序讲清楚每一段在论证什么。播报稿必须全部用中文；遇到英文人名、作品名、术语时，
用通行中文译名或简短中文解释，不要夹带英文原词。"""

NARRATIVE_USER = """下面是纪录片 {duration_min:.1f} 分钟的字幕分段。每段格式为：

[segment_id] mm:ss-mm:ss
正文

{transcript}

请输出一个 JSON 对象，字段如下：
- title：2 到 30 个中文字符
- logline：20 到 120 个中文字符，一句话说清这部片子讲什么
- background：150 到 600 个中文字符，交代主题背景、人物与作品关系
- sections：4 到 8 个章节，按时间顺序排列

每个章节包含：
- heading：4 到 20 个中文字符
- summary：80 到 300 个中文字符，说明本节讲了什么
- spoken_text：100 到 1200 个中文字符，全中文口语播报稿，像播客讲解；英文人名、作品名、术语用通行中文译名或简短解释，不夹带英文原词
- segment_ids：本节覆盖的 segment_id 列表，必须来自上面的分段
- key_terms：0 到 12 个英文术语

额外要求：
- 所有章节的 segment_ids 合起来应覆盖整份字幕，不重叠、不遗漏。
- title、logline、background、summary、spoken_text 全部用中文；英文原词只放在 key_terms 里。
- spoken_text 不要写「本片讲述了」「综上所述」「本文」这类书面摘要套话。
- 只使用字幕中出现的信息，不要编造人物、作品或因果。
- 如果某一节没有足够内容，宁可合并到相邻章节，也不要写空话。"""

CHINESE_REPAIR_SYSTEM = """你是一位中文编辑。下面是一份纪录片学习报告的中文脉络，但混入了英文原词。
请在不改变结构、时间、含义的前提下，把所有英文原词改成通行中文译名或简短中文解释。
key_terms 字段保持英文不动。"""

CHINESE_REPAIR_USER = """下面是需要修正的 JSON：

{narrative_json}

请输出一个 JSON 对象，字段为 title、logline、background、sections。
sections 中每项包含 section_id、heading、summary、spoken_text；section_id 必须原样保留。
所有文本字段只能出现中文和标点，不要出现英文字母。"""

VOCAB_SYSTEM = """你是一位英语学习内容编辑，专门为中文学习者挑选纪录片里的「理解卡点」词条。
你关心的不是词频高低，而是「漏掉这个词，观众会断掉哪条论证」。"""

VOCAB_USER = """下面是同一部纪录片的分段字幕，以及刚整理出的中文脉络章节。

脉络章节：
{narrative_context}

字幕分段：
{transcript}

请输出一个 JSON 对象，字段为 terms，包含 30 到 80 个词条。每个词条包含：
- term：展示形
- lemma：词元；专名允许与 term 相同
- surface_forms：字幕中真实出现的形态，至少 1 个
- category：domain_term、proper_noun、work_title、school_genre、common_advanced 之一
- context_sentence：逐字取自字幕的原句，10 到 300 字符
- segment_id：原句所在的 segment_id
- why_it_matters：15 到 120 个中文字符，说明漏掉它会断哪条论证
- confidence：0 到 1 之间的小数

挑选要求：
- 专业术语、艺术家/作品/流派等专名优先。
- 也包括像 wheedled 这种「字面认识、放在片子里却不理解」的低频普通词。
- 不要收基础高频词和纯功能词。
- context_sentence 必须能在对应 segment 的正文里逐字找到。
- 同一个 lemma 只收一次，合并不同形态。"""

GLOSS_SYSTEM = """你是一位双语词典编辑，面向中文学习者写释义。
你的释义要让人看懂「这个词在这部片子里为什么这么用」，而不是只抄一条通用词典义项。"""

GLOSS_USER = """下面是待处理词条的 JSON 列表，每条包含 term、context_sentence、dictionary_en 与 category：

{terms_json}

请输出一个 JSON 对象，顶层字段名为 glosses，值为词条数组。每个词条包含：
- term：原样返回
- definition_zh：10 到 300 个中文字符，结合 context_sentence 的语境，不要只抄词典
- definition_en：10 到 300 个字符的简明英文释义
- part_of_speech：词性
- pronunciation_note：可选；没有音标时说明将使用 TTS 发音

要求：
- 每个输入词条恰好输出一次，不要新增词条。
- 专名（艺术家、作品、流派）的释义要交代它是什么、在片中为什么重要。
- 普通词要写出它在当前语境里的具体含义，而不是列所有义项。"""

