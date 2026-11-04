"""Content-type profiles: prompt, cache, label, and bound policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from situlearn.knowledge import ContentType, NarrativeScript, ReportManifest

CATEGORY_LABELS = {
    "domain_term": "领域术语",
    "proper_noun": "专名",
    "work_title": "作品名",
    "school_genre": "流派/时期",
    "common_advanced": "低频普通词",
}


@dataclass(frozen=True)
class ReportLabels:
    """User-visible copy that changes with the content type."""

    report_eyebrow: str
    web_eyebrow: str
    narrative_heading: str
    narrative_lead: str
    play_all: str
    play_section: str
    no_audio: str
    expand_script: str
    section_unit: str
    section_counter_unit: str
    this_section: str
    key_terms_heading: str
    vocab_lead: str
    all_sections: str
    back_to_section: str
    previous_section: str
    next_section: str
    progress_narrative: str
    progress_section_audio: str


@dataclass(frozen=True)
class ContentProfile:
    """Generation and presentation policy for one content type."""

    content_type: ContentType
    prompt_version: str
    cache_suffix: str
    section_min: int
    section_max: int
    terms_min: int
    terms_max: int
    tts_style: str | None
    labels: ReportLabels


DOCUMENTARY_PROFILE = ContentProfile(
    content_type=ContentType.DOCUMENTARY,
    prompt_version="v2",
    cache_suffix="",
    section_min=4,
    section_max=8,
    terms_min=30,
    terms_max=80,
    tts_style=None,
    labels=ReportLabels(
        report_eyebrow="情景学习 · 字幕学习报告",
        web_eyebrow="情景学习报告",
        narrative_heading="内容脉络",
        narrative_lead="先听一遍片子怎么走，再回头对着下面的生词本看。",
        play_all="播放全部脉络",
        play_section="播放本节",
        no_audio="暂无音频",
        expand_script="展开播报稿",
        section_unit="章节",
        section_counter_unit="章",
        this_section="本节",
        key_terms_heading="本节关键词",
        vocab_lead="专业术语和专名优先，也可以按章节筛选，回到它出现的语境。",
        all_sections="全部章节",
        back_to_section="回到本节",
        previous_section="上一章",
        next_section="下一章",
        progress_narrative="叙事脉络",
        progress_section_audio="章节音频",
    ),
)

MOVIE_PROFILE = ContentProfile(
    content_type=ContentType.MOVIE,
    prompt_version="v2",
    cache_suffix="-movie",
    section_min=6,
    section_max=12,
    terms_min=30,
    terms_max=80,
    tts_style="用自然、清晰、适合电影剧情解说的语气，语速适中，人物与情节讲得连贯。",
    labels=ReportLabels(
        report_eyebrow="情景学习 · 电影学习报告",
        web_eyebrow="情景学习 · 电影报告",
        narrative_heading="剧情脉络",
        narrative_lead="先听一遍剧情和人物怎么走，再回头对着下面的生词本看。",
        play_all="播放全部剧情",
        play_section="播放本场",
        no_audio="暂无音频",
        expand_script="展开播报稿",
        section_unit="场景",
        section_counter_unit="场",
        this_section="本场",
        key_terms_heading="本场关键词",
        vocab_lead="台词里的关键词和专名优先，也可以按场景筛选，回到它出现的语境。",
        all_sections="全部场景",
        back_to_section="回到本场",
        previous_section="上一场",
        next_section="下一场",
        progress_narrative="剧情脉络",
        progress_section_audio="场景音频",
    ),
)

CONTENT_PROFILES: Mapping[ContentType, ContentProfile] = MappingProxyType(
    {
        ContentType.DOCUMENTARY: DOCUMENTARY_PROFILE,
        ContentType.MOVIE: MOVIE_PROFILE,
    }
)


def resolve_content_type(value: ContentType | str | None = None) -> ContentType:
    """Resolve build-time input strictly; ``None`` means documentary."""

    if value is None:
        return ContentType.DOCUMENTARY
    if isinstance(value, ContentType):
        return value
    return ContentType(value)


def profile_for(value: ContentType | str | None = None) -> ContentProfile:
    return CONTENT_PROFILES[resolve_content_type(value)]


def content_type_from_config(config: Mapping[str, object]) -> ContentType:
    """Read the type from a manifest, falling back for old/foreign manifests."""

    raw = config.get("content_type")
    if isinstance(raw, str):
        try:
            return ContentType(raw)
        except ValueError:
            pass
    return ContentType.DOCUMENTARY


def profile_for_manifest(manifest: ReportManifest) -> ContentProfile:
    return CONTENT_PROFILES[content_type_from_config(manifest.config)]


def validate_narrative(script: NarrativeScript, profile: ContentProfile) -> None:
    count = len(script.sections)
    if not profile.section_min <= count <= profile.section_max:
        raise ValueError(
            f"narrative sections={count} outside "
            f"{profile.section_min}-{profile.section_max} for "
            f"{profile.content_type.value}"
        )
