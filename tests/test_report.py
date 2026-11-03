from __future__ import annotations

from pathlib import Path

from situlearn.knowledge import (
    AudioSource,
    AudioStatus,
    NarrativeScript,
    NarrativeSection,
    ReportManifest,
    SourceInfo,
    SourceRef,
    TermCategory,
    TermEntry,
)
from situlearn.report import assemble_report


def _manifest(
    *,
    section_count: int = 4,
    config: dict[str, object] | None = None,
) -> ReportManifest:
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=f"章节 {index}",
            start_ms=(index - 1) * 60_000,
            end_ms=index * 60_000,
            summary="这一节用来测试报告渲染。" * 8,
            spoken_text="这是用于测试的播报稿，长度足够通过校验。" * 3,
            audio_refs=[f"assets/audio/sec-{index:02d}.mp3"],
            audio_status=AudioStatus.READY,
        )
        for index in range(1, section_count + 1)
    ]
    term = TermEntry(
        term="cherub",
        ipa="/ˈtʃer.əb/",
        part_of_speech="noun",
        definition_zh="小天使，艺术史中常见的有翼天使形象。",
        definition_en="a winged angelic being",
        audio_ref="assets/audio/term-cherub.mp3",
        audio_source=AudioSource.DICTIONARY,
        context_sentence="The one with the interested cherub looking on.",
        why_it_matters="这个小天使是理解瓦萨里叙事立场的视觉线索。",
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
            cue_count=1_186,
        ),
        config=config or {"llm_model": "deepseek-flash"},
        narrative=NarrativeScript(
            title="测试报告",
            logline="这是一句话简介，用来测试整份报告能否正确渲染。",
            background="这是背景段落。" * 25,
            sections=sections,
        ),
        terms=[term],
        assets=[],
        warnings=[],
    )


def test_assemble_report_writes_offline_html(tmp_path: Path) -> None:
    path = assemble_report(_manifest(), tmp_path)

    html = path.read_text(encoding="utf-8")
    assert path.name == "report.html"
    assert "测试报告" in html
    assert "cherub" in html
    assert "assets/audio/sec-01.mp3" in html
    assert "default-src 'self'" in html


def test_assemble_report_movie_uses_plot_labels(tmp_path: Path) -> None:
    path = assemble_report(
        _manifest(section_count=6, config={"content_type": "movie"}),
        tmp_path,
    )

    html = path.read_text(encoding="utf-8")
    assert "剧情脉络" in html
    assert "电影学习报告" in html
    assert "播放全部剧情" in html
    assert "全部场景" in html
    assert "回到本场" in html
    assert "内容脉络" not in html


def test_assemble_report_legacy_manifest_defaults_to_documentary(
    tmp_path: Path,
) -> None:
    path = assemble_report(_manifest(), tmp_path)

    html = path.read_text(encoding="utf-8")
    assert "内容脉络" in html
    assert "剧情脉络" not in html
