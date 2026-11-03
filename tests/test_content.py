from __future__ import annotations

import pytest

from situlearn.content import (
    DOCUMENTARY_PROFILE,
    MOVIE_PROFILE,
    content_type_from_config,
    profile_for,
    profile_for_manifest,
    resolve_content_type,
    validate_narrative,
)
from situlearn.knowledge import (
    AudioSource,
    AudioStatus,
    ContentType,
    NarrativeScript,
    NarrativeSection,
    ReportManifest,
    SourceInfo,
    SourceRef,
    TermCategory,
    TermEntry,
)


def _script(section_count: int) -> NarrativeScript:
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=f"第{index}节",
            start_ms=(index - 1) * 10_000,
            end_ms=index * 10_000,
            summary="这是用于测试的摘要，长度足够。",
            spoken_text="这是用于测试的播报稿，长度足够。",
            audio_refs=[],
            audio_status=AudioStatus.UNAVAILABLE,
        )
        for index in range(1, section_count + 1)
    ]
    return NarrativeScript(
        title="测试报告",
        logline="这是用于测试的一句话简介。",
        background="这是用于测试的背景。",
        sections=sections,
    )


def _manifest(config: dict[str, object]) -> ReportManifest:
    term = TermEntry(
        term="cherub",
        part_of_speech="noun",
        definition_zh="小天使，艺术史中常见的有翼天使形象。",
        definition_en="a winged angelic being",
        audio_ref="unavailable",
        audio_source=AudioSource.UNAVAILABLE,
        context_sentence="The one with the interested cherub looking on.",
        why_it_matters="这个小天使是理解画面的视觉线索。",
        section_id="sec-01",
        category=TermCategory.PROPER_NOUN,
        sources=[SourceRef(name="Wiktionary", url="https://example.com/cherub")],
    )
    return ReportManifest(
        schema_version="1.0.0",
        source=SourceInfo(
            filename="sample.srt",
            sha256="0" * 64,
            duration_ms=240_000,
            cue_count=4,
        ),
        config=config,
        narrative=_script(4),
        terms=[term],
    )


def test_default_profile_is_documentary() -> None:
    assert resolve_content_type() is ContentType.DOCUMENTARY
    assert profile_for() is DOCUMENTARY_PROFILE
    assert profile_for("movie") is MOVIE_PROFILE


def test_invalid_content_type_raises() -> None:
    with pytest.raises(ValueError):
        resolve_content_type("podcast")


def test_content_type_from_config_falls_back_to_documentary() -> None:
    assert content_type_from_config({}) is ContentType.DOCUMENTARY
    assert content_type_from_config({"content_type": "movie"}) is ContentType.MOVIE
    assert content_type_from_config({"content_type": "unknown"}) is ContentType.DOCUMENTARY


def test_profile_for_manifest_uses_config() -> None:
    assert profile_for_manifest(_manifest({})) is DOCUMENTARY_PROFILE
    assert profile_for_manifest(_manifest({"content_type": "movie"})) is MOVIE_PROFILE


def test_profiles_carry_bounds_and_cache_suffixes() -> None:
    assert DOCUMENTARY_PROFILE.cache_suffix == ""
    assert (DOCUMENTARY_PROFILE.section_min, DOCUMENTARY_PROFILE.section_max) == (4, 8)
    assert MOVIE_PROFILE.cache_suffix == "-movie"
    assert (MOVIE_PROFILE.section_min, MOVIE_PROFILE.section_max) == (6, 12)


def test_documentary_labels_keep_existing_copy() -> None:
    labels = DOCUMENTARY_PROFILE.labels
    assert labels.report_eyebrow == "情景学习 · 字幕学习报告"
    assert labels.narrative_heading == "内容脉络"
    assert labels.play_section == "播放本节"
    assert labels.all_sections == "全部章节"
    assert labels.previous_section == "上一章"
    assert labels.progress_narrative == "叙事脉络"
    assert labels.progress_section_audio == "章节音频"


def test_movie_labels_use_plot_copy() -> None:
    labels = MOVIE_PROFILE.labels
    assert labels.report_eyebrow == "情景学习 · 电影学习报告"
    assert labels.narrative_heading == "剧情脉络"
    assert labels.play_section == "播放本场"
    assert labels.all_sections == "全部场景"
    assert labels.previous_section == "上一场"
    assert labels.progress_narrative == "剧情脉络"
    assert labels.progress_section_audio == "场景音频"


def test_validate_narrative_enforces_profile_bounds() -> None:
    validate_narrative(_script(4), DOCUMENTARY_PROFILE)
    validate_narrative(_script(8), DOCUMENTARY_PROFILE)
    validate_narrative(_script(6), MOVIE_PROFILE)
    validate_narrative(_script(12), MOVIE_PROFILE)

    with pytest.raises(ValueError):
        validate_narrative(_script(9), DOCUMENTARY_PROFILE)
    with pytest.raises(ValueError):
        validate_narrative(_script(4), MOVIE_PROFILE)
