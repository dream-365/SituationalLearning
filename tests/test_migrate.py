from __future__ import annotations

import json
from pathlib import Path

import pytest

from situlearn.cli import main
from situlearn.document import Document
from situlearn.knowledge import (
    AudioAsset,
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
from situlearn.migrate import MigrateError, migrate_batch, migrate_report


def _manifest() -> ReportManifest:
    sections = []
    for index in range(1, 5):
        sections.append(
            NarrativeSection(
                section_id=f"sec-0{index}",
                heading=f"第{index}节",
                start_ms=(index - 1) * 1000,
                end_ms=index * 1000,
                summary=f"这是第{index}节摘要，长度足够。",
                spoken_text=f"这是第{index}节播报稿，长度足够。",
                audio_refs=[f"assets/audio/sec-0{index}.mp3"],
                audio_status=AudioStatus.READY,
                key_terms=["alpha"] if index == 1 else (["beta"] if index == 2 else []),
            )
        )
    terms = [
        TermEntry(
            term="alpha",
            ipa="/ˈælfə/",
            part_of_speech="noun",
            definition_zh="第一个测试词条的释义。",
            definition_en="the first test term",
            audio_ref="assets/audio/term-alpha.mp3",
            audio_source=AudioSource.DICTIONARY,
            context_sentence="This is the alpha sentence.",
            why_it_matters="这是理解第一段论证推进的关键线索。",
            section_id="sec-01",
            category=TermCategory.DOMAIN_TERM,
            sources=[SourceRef(name="Wiktionary", url="https://example.com/alpha")],
        ),
        TermEntry(
            term="beta",
            part_of_speech="noun",
            definition_zh="第二个测试词条的释义。",
            definition_en="the second test term",
            audio_ref="assets/audio/term-beta.mp3",
            audio_source=AudioSource.TTS,
            context_sentence="This is the beta sentence.",
            why_it_matters="这是理解第二段人物关系的关键线索。",
            section_id="sec-02",
            category=TermCategory.PROPER_NOUN,
            sources=[SourceRef(name="Wiktionary", url="https://example.com/beta")],
        ),
    ]
    assets = [
        AudioAsset(
            asset_id=f"a-{index}",
            path=f"assets/audio/sec-0{index}.mp3",
            duration_ms=1000,
            text_sha256="0" * 64,
            source=AudioSource.TTS,
        )
        for index in range(1, 5)
    ] + [
        AudioAsset(
            asset_id="a-alpha",
            path="assets/audio/term-alpha.mp3",
            duration_ms=500,
            text_sha256="1" * 64,
            source=AudioSource.DICTIONARY,
        ),
        AudioAsset(
            asset_id="a-beta",
            path="assets/audio/term-beta.mp3",
            duration_ms=500,
            text_sha256="2" * 64,
            source=AudioSource.TTS,
        ),
    ]
    return ReportManifest(
        schema_version="1.0.0",
        source=SourceInfo(
            filename="sample.srt",
            sha256="a" * 64,
            duration_ms=4000,
            cue_count=8,
        ),
        config={"content_type": "documentary"},
        narrative=NarrativeScript(
            title="迁移测试",
            logline="一句测试简介。",
            background="这是用于迁移测试的背景说明。",
            sections=sections,
        ),
        terms=terms,
        assets=assets,
        warnings=[],
    )


def _make_old(tmp_path: Path) -> Path:
    old = tmp_path / "old"
    old.mkdir()
    manifest = _manifest()
    (old / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    for asset in manifest.assets:
        path = old / asset.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"bytes-{asset.path}".encode())
    return old


def _rewrite_manifest(old: Path, mutate) -> None:
    data = json.loads((old / "manifest.json").read_text(encoding="utf-8"))
    mutate(data)
    (old / "manifest.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def test_migrate_report_builds_document(tmp_path: Path) -> None:
    old = _make_old(tmp_path)
    out = tmp_path / "new"
    info = migrate_report(old, out)
    document = Document.model_validate_json((out / "document.json").read_text(encoding="utf-8"))

    assert info.sections == 5
    assert info.words == 2
    assert info.resources == 6
    assert [section.role.value for section in document.sections] == [
        "narrative",
        "narrative",
        "narrative",
        "narrative",
        "vocabulary",
    ]
    vocabulary = document.sections[-1]
    assert len(vocabulary.blocks) == 2
    alpha = vocabulary.blocks[0]
    assert alpha.term == "alpha"
    assert alpha.section_id == "sec-01"
    assert alpha.audio is not None
    assert alpha.audio in document.resources
    assert document.sections[0].keywords[0].word_id == alpha.id
    assert document.sections[0].blocks[0].script == "这是第1节播报稿，长度足够。"
    assert document.meta.labels["vocabulary_heading"] == "生词本"
    assert "category.domain_term" in document.meta.labels
    assert document.meta.source is not None
    assert document.meta.source.language == "en"
    assert document.meta.id == "a" * 64
    assert not (out / "publish.json").exists()

    for resource in document.resources.values():
        path = out / resource.href
        assert path.is_file()
        assert __import__("hashlib").sha256(path.read_bytes()).hexdigest() == resource.sha256


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    old = _make_old(tmp_path)
    migrate_report(old, tmp_path / "a")
    migrate_report(old, tmp_path / "b")
    assert (tmp_path / "a" / "document.json").read_bytes() == (
        tmp_path / "b" / "document.json"
    ).read_bytes()


def test_migrate_skips_unavailable_term_audio(tmp_path: Path) -> None:
    old = _make_old(tmp_path)
    _rewrite_manifest(
        old,
        lambda data: data["terms"][0].__setitem__("audio_ref", "unavailable"),
    )
    out = tmp_path / "new"
    migrate_report(old, out)
    document = Document.model_validate_json((out / "document.json").read_text(encoding="utf-8"))
    alpha = document.sections[-1].blocks[0]
    assert alpha.term == "alpha"
    assert alpha.audio is None


def test_migrate_drops_unmatched_keyword(tmp_path: Path) -> None:
    old = _make_old(tmp_path)

    def add_keyword(data: dict) -> None:
        data["narrative"]["sections"][0]["key_terms"].append("gamma")

    _rewrite_manifest(old, add_keyword)
    info = migrate_report(old, tmp_path / "new")
    assert any("gamma" in warning for warning in info.warnings)


def test_migrate_renames_legacy_vocabulary_section(tmp_path: Path) -> None:
    old = _make_old(tmp_path)

    def rename(data: dict) -> None:
        data["narrative"]["sections"][0]["section_id"] = "vocabulary"
        for term in data["terms"]:
            if term["section_id"] == "sec-01":
                term["section_id"] = "vocabulary"

    _rewrite_manifest(old, rename)
    out = tmp_path / "new"
    migrate_report(old, out)
    document = Document.model_validate_json((out / "document.json").read_text(encoding="utf-8"))
    assert document.sections[-1].id == "vocabulary"
    assert document.sections[-1].role.value == "vocabulary"
    assert document.sections[0].id == "vocabulary-legacy-1"


def test_migrate_rejects_duplicate_section_ids(tmp_path: Path) -> None:
    old = _make_old(tmp_path)

    def duplicate(data: dict) -> None:
        data["narrative"]["sections"][1]["section_id"] = data["narrative"]["sections"][0][
            "section_id"
        ]

    _rewrite_manifest(old, duplicate)
    with pytest.raises(MigrateError) as exc:
        migrate_report(old, tmp_path / "new")
    assert exc.value.code == "document/duplicate-id"


def test_migrate_batch_reads_export_layout(tmp_path: Path) -> None:
    old = _make_old(tmp_path)
    report_key = "a" * 64
    export = tmp_path / "export" / report_key
    export.parent.mkdir()
    export.mkdir()
    (export / "manifest.json").write_bytes((old / "manifest.json").read_bytes())
    for asset in _manifest().assets:
        path = export / asset.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((old / asset.path).read_bytes())
    (export / "bundle.json").write_text(
        json.dumps({"slug": "old-slug", "published_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )

    results = migrate_batch(tmp_path / "export", tmp_path / "out")
    assert len(results) == 1
    assert results[0].error is None
    assert results[0].info is not None
    publish = tmp_path / "out" / report_key / "publish.json"
    assert json.loads(publish.read_text(encoding="utf-8"))["slug"] == "old-slug"


def test_migrate_batch_reports_key_mismatch(tmp_path: Path) -> None:
    old = _make_old(tmp_path)
    export = tmp_path / "export" / "wrong-key"
    export.mkdir(parents=True)
    (export / "manifest.json").write_bytes((old / "manifest.json").read_bytes())
    for asset in _manifest().assets:
        path = export / asset.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((old / asset.path).read_bytes())

    results = migrate_batch(tmp_path / "export", tmp_path / "out")
    assert results[0].error is not None
    assert "missing-source-sha256" in results[0].error or "does not match" in results[0].error


def test_cli_migrate(tmp_path: Path) -> None:
    old = _make_old(tmp_path)
    out = tmp_path / "new"
    assert main(["migrate", str(old), "--out", str(out)]) == 0
    assert (out / "document.json").is_file()
