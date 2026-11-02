from __future__ import annotations

from io import StringIO
from pathlib import Path

from situlearn import pipeline
from situlearn.knowledge import (
    AudioSource,
    AudioStatus,
    NarrativeScript,
    NarrativeSection,
    SourceRef,
    TermCandidate,
    TermCategory,
    TermEntry,
)
from situlearn.progress import Progress


def _script() -> NarrativeScript:
    headings = ["第一章节", "第二章节", "第三章节", "第四章节"]
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=headings[index - 1],
            start_ms=(index - 1) * 15_000,
            end_ms=index * 15_000,
            summary="这是本节摘要，用来测试报告。" * 7,
            spoken_text="这是播报稿，用来测试报告。" * 4,
            audio_refs=[],
            audio_status=AudioStatus.UNAVAILABLE,
        )
        for index in range(1, 5)
    ]
    return NarrativeScript(
        title="测试报告",
        logline="这是一句话简介，用来测试整份报告能否正确渲染。",
        background="这是背景。" * 30,
        sections=sections,
    )


def _candidate() -> TermCandidate:
    return TermCandidate(
        term="cherub",
        lemma="cherub",
        surface_forms=["cherub"],
        category=TermCategory.PROPER_NOUN,
        cue_ids=[1],
        context_sentence="The one with the interested cherub looking on.",
        section_id="sec-01",
        why_it_matters="这个小天使是理解瓦萨里叙事立场的视觉线索。",
        confidence=0.95,
    )


def _entry() -> TermEntry:
    return TermEntry(
        term="cherub",
        ipa="/ˈtʃer.əb/",
        part_of_speech="noun",
        definition_zh="小天使，艺术史中常见的有翼天使形象。",
        definition_en="a winged angelic being",
        audio_ref="unavailable",
        audio_source=AudioSource.UNAVAILABLE,
        context_sentence="The one with the interested cherub looking on.",
        why_it_matters="这个小天使是理解瓦萨里叙事立场的视觉线索。",
        section_id="sec-01",
        category=TermCategory.PROPER_NOUN,
        sources=[SourceRef(name="Wiktionary", url="https://example.com/cherub")],
    )


def test_build_report_no_audio(tmp_path: Path, monkeypatch) -> None:
    srt = tmp_path / "sample.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:15,000\nThe one with the interested cherub.\n\n"
        "2\n00:00:15,000 --> 00:00:30,000\nA second cue for testing.\n\n"
        "3\n00:00:30,000 --> 00:00:45,000\nA third cue for testing.\n\n"
        "4\n00:00:45,000 --> 00:01:00,000\nA fourth cue for testing.\n",
        encoding="utf-8",
    )

    script = _script()
    candidate = _candidate()
    entry = _entry()

    monkeypatch.setattr(pipeline, "make_chat_model", lambda: object())
    monkeypatch.setattr(pipeline, "plan_narrative", lambda llm, segments: script)
    monkeypatch.setattr(
        pipeline, "extract_terms", lambda llm, segments, narrative: [candidate]
    )
    monkeypatch.setattr(pipeline, "_lookup_dictionary", lambda terms: {})
    monkeypatch.setattr(
        pipeline, "gloss_terms", lambda llm, terms, dictionary: [entry]
    )

    progress_out = StringIO()
    result = pipeline.build_report(
        srt,
        tmp_path / "out",
        no_audio=True,
        cache_root=tmp_path / ".cache",
        progress=Progress(progress_out),
    )

    messages = progress_out.getvalue()
    assert "解析字幕：4 条" in messages
    assert "内容切分：1 个片段" in messages
    assert "--no-audio" in messages
    assert result.report_path.exists()
    assert result.manifest_path.exists()
    assert result.cue_count == 4
    assert result.term_count == 1
    assert "audio_disabled" in result.warnings
    assert "测试报告" in result.report_path.read_text(encoding="utf-8")
