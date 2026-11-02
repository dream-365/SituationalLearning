from __future__ import annotations

from io import StringIO

from situlearn.progress import Progress


def test_progress_is_silent_without_stream() -> None:
    progress = Progress()
    progress.stage("解析字幕：10 条")
    progress.counter("章节音频", 1, 2)
    progress.finish()


def test_progress_writes_stages_and_counters() -> None:
    out = StringIO()
    progress = Progress(out)

    progress.stage("解析字幕：10 条")
    progress.counter("章节音频", 2, 8)
    progress.finish()
    progress.stage("完成")

    lines = out.getvalue().splitlines()
    assert lines[0].endswith("解析字幕：10 条")
    assert "章节音频 2/8" in lines[1]
    assert lines[2].endswith("完成")


def test_stage_after_counter_starts_on_a_new_line() -> None:
    out = StringIO()
    progress = Progress(out)

    progress.counter("词条音频", 3, 8)
    progress.stage("生成报告")

    lines = out.getvalue().splitlines()
    assert "词条音频 3/8" in lines[0]
    assert lines[1].endswith("生成报告")
