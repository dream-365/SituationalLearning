from __future__ import annotations

from situlearn import chains, prompts
from situlearn.content import DOCUMENTARY_PROFILE, MOVIE_PROFILE
from situlearn.knowledge import (
    AudioStatus,
    NarrativeScript,
    NarrativeSection,
    TermCandidate,
    TermCategory,
)
from situlearn.models import Segment
from situlearn.planning import PlannedNarrative, PlannedSection


class FakeRunnable:
    def __init__(self, captured: dict) -> None:
        self.captured = captured

    def invoke(self, payload):
        self.captured["payload"] = payload
        return self.captured["result"]


class FakePrompt:
    def __init__(self, captured: dict) -> None:
        self.captured = captured

    def __or__(self, other):
        return FakeRunnable(self.captured)


def _install_fake_prompt(monkeypatch, captured: dict) -> None:
    class FakeChatPromptTemplate:
        @staticmethod
        def from_messages(messages):
            captured["messages"] = messages
            return FakePrompt(captured)

    monkeypatch.setattr(chains, "ChatPromptTemplate", FakeChatPromptTemplate)
    monkeypatch.setattr(chains, "structured_output", lambda llm, schema: object())


def _segments(count: int) -> list[Segment]:
    return [
        Segment(
            segment_id=f"seg-{index:04d}",
            cue_ids=[index],
            start_ms=(index - 1) * 10_000,
            end_ms=index * 10_000,
            text=f"Line {index} for the test.",
        )
        for index in range(1, count + 1)
    ]


def _planned(count: int) -> PlannedNarrative:
    return PlannedNarrative(
        title="测试报告",
        logline="这是一句话简介。",
        background="这是背景。",
        sections=[
            PlannedSection(
                heading=f"第{index}节",
                summary="这是摘要，长度足够测试。" * 3,
                spoken_text="这是播报稿，长度足够测试。" * 3,
                segment_ids=[f"seg-{index:04d}"],
            )
            for index in range(1, count + 1)
        ],
    )


def _script(count: int, title: str = "测试报告") -> NarrativeScript:
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=f"第{index}节",
            start_ms=(index - 1) * 10_000,
            end_ms=index * 10_000,
            summary="这是摘要，长度足够测试。",
            spoken_text="这是播报稿，长度足够测试。",
            audio_status=AudioStatus.UNAVAILABLE,
        )
        for index in range(1, count + 1)
    ]
    return NarrativeScript(
        title=title,
        logline="这是一句话简介。",
        background="这是背景。",
        sections=sections,
    )


def _candidate() -> TermCandidate:
    return TermCandidate(
        term="cherub",
        lemma="cherub",
        surface_forms=["cherub"],
        category=TermCategory.PROPER_NOUN,
        cue_ids=[1],
        context_sentence="A cherub appears in the scene.",
        section_id="sec-01",
        why_it_matters="漏掉它会听不懂这场戏在讲什么。",
        confidence=0.9,
    )


def test_plan_narrative_movie_selects_movie_prompts(monkeypatch) -> None:
    captured: dict = {"result": _planned(6)}
    _install_fake_prompt(monkeypatch, captured)

    script = chains.plan_narrative(
        object(),
        _segments(6),
        profile=MOVIE_PROFILE,
        source_name="film.srt",
    )

    assert captured["messages"][0] == ("system", prompts.NARRATIVE_SYSTEM_MOVIE)
    assert captured["messages"][1][1] == prompts.NARRATIVE_USER_MOVIE
    assert captured["payload"]["source_name"] == "film.srt"
    assert len(script.sections) == 6


def test_plan_narrative_documentary_keeps_legacy_prompts(monkeypatch) -> None:
    captured: dict = {"result": _planned(4)}
    _install_fake_prompt(monkeypatch, captured)

    chains.plan_narrative(
        object(),
        _segments(4),
        profile=DOCUMENTARY_PROFILE,
        source_name="film.srt",
    )

    assert captured["messages"][0] == ("system", prompts.NARRATIVE_SYSTEM)
    assert captured["messages"][1][1] == prompts.NARRATIVE_USER
    assert "source_name" not in captured["payload"]


def test_repair_narrative_selects_movie_prompt(monkeypatch) -> None:
    script = _script(6, title="Movie 测试报告")
    patch = chains.NarrativeTextPatch(
        title="电影测试报告",
        logline="这是一句话简介。",
        background="这是背景。",
        sections=[
            chains.SectionTextPatch(
                section_id=f"sec-{index:02d}",
                heading=f"第{index}节",
                summary="这是修正后的摘要。",
                spoken_text="这是修正后的播报稿。",
            )
            for index in range(1, 7)
        ],
    )
    captured: dict = {"result": patch}
    _install_fake_prompt(monkeypatch, captured)

    chains.repair_narrative_chinese(object(), script, profile=MOVIE_PROFILE)

    assert captured["messages"][0] == ("system", prompts.CHINESE_REPAIR_SYSTEM_MOVIE)


def test_extract_terms_selects_movie_prompt(monkeypatch) -> None:
    captured: dict = {"result": object()}
    _install_fake_prompt(monkeypatch, captured)
    candidate = _candidate()
    monkeypatch.setattr(
        chains, "to_term_candidates", lambda extracted, segments, script: [candidate]
    )

    terms = chains.extract_terms(
        object(),
        _segments(6),
        _script(6),
        profile=MOVIE_PROFILE,
    )

    assert captured["messages"][0] == ("system", prompts.VOCAB_SYSTEM_MOVIE)
    assert captured["messages"][1][1] == prompts.VOCAB_USER_MOVIE
    assert terms == [candidate]
