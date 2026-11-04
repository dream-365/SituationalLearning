from __future__ import annotations

import copy

import pytest
from pydantic import ValidationError

from situlearn.document import (
    REQUIRED_LABELS,
    Document,
    DocumentValidationError,
    check_document,
    document_schema,
    parse_document,
    raise_for_errors,
)


def _labels() -> dict[str, str]:
    return {key: f"label-{key}" for key in REQUIRED_LABELS}


def _document() -> dict:
    return {
        "format": "situlearn.document",
        "version": 1,
        "meta": {
            "id": "0" * 64,
            "title": "测试文档",
            "language": "zh-CN",
            "source": {
                "filename": "sample.srt",
                "sha256": "0" * 64,
                "language": "en",
                "duration_ms": 10_000,
                "cue_count": 4,
            },
            "labels": _labels(),
            "attribution": ["dictionary"],
        },
        "resources": {
            "aud-1": {
                "type": "audio",
                "mime": "audio/mpeg",
                "href": "media/audio/a.mp3",
                "sha256": "1" * 64,
                "source": "tts",
            },
            "img-1": {
                "type": "image",
                "mime": "image/jpeg",
                "href": "media/images/a.jpg",
                "sha256": "2" * 64,
            },
        },
        "sections": [
            {
                "id": "s1",
                "role": "narrative",
                "title": "第一节",
                "time": {"start_ms": 0, "end_ms": 10_000},
                "keywords": [{"word_id": "w-1"}],
                "blocks": [
                    {
                        "type": "group",
                        "role": "narration",
                        "script": "播报稿",
                        "blocks": [
                            {"type": "image", "resource": "img-1"},
                            {"type": "text", "text": "描述性文字"},
                            {"type": "audio", "resource": "aud-1"},
                        ],
                    }
                ],
            },
            {
                "id": "vocabulary",
                "role": "vocabulary",
                "title": "生词本",
                "layout": "grid",
                "blocks": [
                    {
                        "id": "w-1",
                        "type": "word",
                        "term": "epistemology",
                        "definitions": {"zh": "认识论", "en": "theory of knowledge"},
                        "section_id": "s1",
                        "audio": "aud-1",
                        "image": "img-1",
                        "sources": [{"name": "Wiktionary", "url": "https://example.com"}],
                    }
                ],
            },
        ],
    }


def _parse(data: dict, mode: str = "write"):
    return parse_document(data, mode=mode)


def test_valid_document_parses_without_issues() -> None:
    document, issues = _parse(_document())
    assert document.meta.title == "测试文档"
    assert document.meta.source is not None
    assert document.meta.source.language == "en"
    assert issues == []


def test_unknown_fields_are_ignored() -> None:
    data = _document()
    data["future_field"] = {"x": 1}
    data["sections"][0]["future_field"] = 1
    document, issues = _parse(data)
    assert document.meta.title == "测试文档"
    assert issues == []


def test_text_uses_markup_and_style() -> None:
    data = _document()
    group = data["sections"][0]["blocks"][0]
    group["blocks"][1] = {"type": "text", "text": "标题", "markup": "plain", "style": "heading"}
    document, _ = _parse(data)
    assert document.sections[0].blocks[0].blocks[1].style.value == "heading"


def test_word_only_allowed_in_vocabulary() -> None:
    data = _document()
    word = copy.deepcopy(data["sections"][1]["blocks"][0])
    data["sections"][0]["blocks"][0]["blocks"].append(word)
    with pytest.raises(ValidationError):
        _parse(data)


def test_narrative_requires_exactly_one_narration_group() -> None:
    data = _document()
    data["sections"][0]["blocks"] = []
    with pytest.raises(ValidationError):
        _parse(data)

    data = _document()
    data["sections"][0]["blocks"].append(copy.deepcopy(data["sections"][0]["blocks"][0]))
    with pytest.raises(ValidationError):
        _parse(data)


def test_narration_group_rejects_audio_script() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["blocks"][2]["script"] = "重复文稿"
    with pytest.raises(ValidationError):
        _parse(data)


def test_group_script_only_on_narration() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["role"] = "visual"
    with pytest.raises(ValidationError):
        _parse(data)


def test_nested_narration_group_rejected() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["blocks"].append(
        {
            "type": "group",
            "role": "narration",
            "script": "嵌套",
            "blocks": [{"type": "text", "text": "嵌套"}],
        }
    )
    with pytest.raises(ValidationError):
        _parse(data)


def test_keyword_must_match_word_section() -> None:
    data = _document()
    data["sections"][1]["blocks"][0]["section_id"] = "s1"
    data["sections"][0]["keywords"] = [{"word_id": "w-missing"}]
    with pytest.raises(ValidationError):
        _parse(data)

    data = _document()
    data["sections"][0]["keywords"] = [{"word_id": "w-1"}]
    data["sections"][1]["blocks"][0]["section_id"] = "s2"
    with pytest.raises(ValidationError):
        _parse(data)


def test_word_section_id_must_resolve_to_narrative() -> None:
    data = _document()
    data["sections"][1]["blocks"][0]["section_id"] = "missing"
    with pytest.raises(ValidationError):
        _parse(data)


def test_duplicate_ids_rejected() -> None:
    data = _document()
    data["sections"][0]["id"] = "vocabulary"
    with pytest.raises(ValidationError):
        _parse(data)

    data = _document()
    data["sections"][1]["blocks"][0]["id"] = "w-1"
    data["sections"][0]["keywords"] = []
    data["sections"][0]["blocks"][0]["blocks"].append(
        {"id": "w-1", "type": "text", "text": "重复 id"}
    )
    with pytest.raises(ValidationError):
        _parse(data)


def test_href_must_be_media_and_unique() -> None:
    data = _document()
    data["resources"]["aud-1"]["href"] = "assets/audio/a.mp3"
    with pytest.raises(ValidationError):
        _parse(data)

    data = _document()
    data["resources"]["img-1"]["href"] = data["resources"]["aud-1"]["href"]
    with pytest.raises(ValidationError):
        _parse(data)


def test_href_traversal_rejected() -> None:
    data = _document()
    data["resources"]["aud-1"]["href"] = "media/../secret.mp3"
    with pytest.raises(ValidationError):
        _parse(data)


def test_resource_sha256_required() -> None:
    data = _document()
    del data["resources"]["aud-1"]["sha256"]
    with pytest.raises(ValidationError):
        _parse(data)


def test_resource_type_must_match_reference() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["blocks"][0] = {"type": "image", "resource": "aud-1"}
    with pytest.raises(ValidationError):
        _parse(data)


def test_meta_id_must_equal_source_sha256() -> None:
    data = _document()
    data["meta"]["id"] = "3" * 64
    with pytest.raises(ValidationError):
        _parse(data)


def test_missing_labels_are_write_errors() -> None:
    data = _document()
    data["meta"]["labels"] = {"section_unit": "章节"}
    document, issues = _parse(data)
    assert document.meta.title == "测试文档"
    errors = [issue for issue in issues if issue.severity == "error"]
    assert any(issue.code == "document/missing-label" for issue in errors)
    with pytest.raises(DocumentValidationError):
        raise_for_errors(issues)


def test_missing_id_and_source_is_write_error() -> None:
    data = _document()
    del data["meta"]["id"]
    del data["meta"]["source"]["sha256"]
    _, issues = _parse(data)
    assert any(issue.code == "document/invalid-id-source" for issue in issues)


def test_overlapping_time_is_warning() -> None:
    data = _document()
    data["sections"][0]["time"] = {"start_ms": 0, "end_ms": 10_000}
    data["sections"].insert(
        1,
        {
            "id": "s2",
            "role": "narrative",
            "title": "第二节",
            "time": {"start_ms": 9_000, "end_ms": 20_000},
            "blocks": [
                {
                    "type": "group",
                    "role": "narration",
                    "script": "讲稿",
                    "blocks": [{"type": "text", "text": "文字"}],
                }
            ],
        },
    )
    _, issues = _parse(data)
    assert any(issue.code == "document/overlapping-time" for issue in issues)
    warnings = [issue for issue in issues if issue.code == "document/overlapping-time"]
    assert all(issue.severity == "warning" for issue in warnings)


def test_sections_must_be_ordered_by_start() -> None:
    data = _document()
    data["sections"].insert(
        1,
        {
            "id": "s0",
            "role": "narrative",
            "title": "第零节",
            "time": {"start_ms": -1, "end_ms": 1},
            "blocks": [
                {
                    "type": "group",
                    "role": "narration",
                    "script": "讲稿",
                    "blocks": [{"type": "text", "text": "文字"}],
                }
            ],
        },
    )
    with pytest.raises(ValidationError):
        _parse(data)


def test_group_depth_limit() -> None:
    data = _document()
    block: dict = {"type": "text", "text": "深层"}
    for _ in range(4):
        block = {"type": "group", "role": "visual", "blocks": [block]}
    data["sections"][0]["blocks"][0]["blocks"].append(block)
    with pytest.raises(ValidationError):
        _parse(data)


def test_unknown_block_dropped_on_read_and_rejected_on_write() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["blocks"].append({"type": "quote", "text": "引用"})
    document, issues = _parse(data, mode="read")
    assert any(issue.code == "document/unknown-block-type" for issue in issues)
    assert len(document.sections[0].blocks[0].blocks) == 3
    with pytest.raises(ValidationError):
        _parse(data, mode="write")


def test_vocabulary_section_rules() -> None:
    data = _document()
    data["sections"][1]["id"] = "vocab"
    with pytest.raises(ValidationError):
        _parse(data)

    data = _document()
    data["sections"][1]["blocks"].append({"type": "text", "text": "不允许"})
    with pytest.raises(ValidationError):
        _parse(data)


def test_cover_section_rejects_narration_group() -> None:
    data = _document()
    data["sections"].append(
        {
            "id": "cover",
            "role": "cover",
            "title": "封面",
            "blocks": [
                {
                    "type": "group",
                    "role": "narration",
                    "script": "讲稿",
                    "blocks": [{"type": "text", "text": "文字"}],
                }
            ],
        }
    )
    with pytest.raises(ValidationError):
        _parse(data)


def test_definitions_must_be_bcp47_and_not_blank() -> None:
    data = _document()
    data["sections"][1]["blocks"][0]["definitions"] = {"zh_CN": "认识论"}
    with pytest.raises(ValidationError):
        _parse(data)

    data = _document()
    data["sections"][1]["blocks"][0]["definitions"] = {"zh": "  "}
    with pytest.raises(ValidationError):
        _parse(data)


def test_roundtrip_json() -> None:
    document, _ = _parse(_document())
    restored = Document.model_validate_json(document.to_json())
    assert restored == document
    assert "subtitle" not in document.to_json()


def test_schema_shape() -> None:
    schema = document_schema()
    assert schema["title"] == "Document"
    assert "GroupBlock" in schema["$defs"]
    assert "WordBlock" in schema["$defs"]
    assert schema["$schema"].endswith("2020-12/schema")


def test_required_labels_has_25_keys() -> None:
    assert len(REQUIRED_LABELS) == 25


def test_check_document_returns_no_errors_for_valid_document() -> None:
    document, _ = _parse(_document())
    assert check_document(document, mode="write") == []


def test_malformed_known_block_dropped_on_read() -> None:
    data = _document()
    group = data["sections"][0]["blocks"][0]
    group["blocks"].append({"type": "text"})
    document, issues = _parse(data, mode="read")
    assert any(issue.code == "document/malformed-block" for issue in issues)
    assert len(document.sections[0].blocks[0].blocks) == 3


def test_unknown_section_role_skipped_on_read() -> None:
    data = _document()
    data["sections"].append(
        {
            "id": "x",
            "role": "appendix",
            "title": "附录",
            "blocks": [{"type": "text", "text": "x"}],
        }
    )
    document, issues = _parse(data, mode="read")
    assert any(issue.code == "document/unknown-role" for issue in issues)
    assert all(section.id != "x" for section in document.sections)


def test_unknown_word_kind_falls_back_on_read() -> None:
    data = _document()
    data["sections"][1]["blocks"][0]["kind"] = "idiom"
    document, issues = _parse(data, mode="read")
    assert document.sections[1].blocks[0].kind.value == "word"
    assert any(issue.code == "document/unknown-word-kind" for issue in issues)


def test_unknown_resource_source_removed_on_read() -> None:
    data = _document()
    data["resources"]["aud-1"]["source"] = "radio"
    document, issues = _parse(data, mode="read")
    assert document.resources["aud-1"].source is None
    assert any(issue.code == "document/unknown-source" for issue in issues)


def test_missing_resource_gets_placeholder_on_read() -> None:
    data = _document()
    del data["resources"]["img-1"]
    document, issues = _parse(data, mode="read")
    image = document.sections[0].blocks[0].blocks[0]
    assert image.resource.startswith("ph-")
    assert any(issue.code == "document/unresolved-resource" for issue in issues)


def test_resource_type_mismatch_gets_placeholder_on_read() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["blocks"][0] = {"type": "image", "resource": "aud-1"}
    document, issues = _parse(data, mode="read")
    image = document.sections[0].blocks[0].blocks[0]
    assert image.resource.startswith("ph-")
    assert any(issue.code == "document/resource-type-mismatch" for issue in issues)


def test_missing_hash_read_warns_and_parses() -> None:
    data = _document()
    del data["resources"]["aud-1"]["sha256"]
    document, issues = _parse(data, mode="read")
    assert document.resources["aud-1"].sha256 == "0" * 64
    assert any(issue.code == "document/missing-hash" for issue in issues)


def test_version_and_format_rejected_with_codes() -> None:
    data = _document()
    data["version"] = 2
    with pytest.raises(DocumentValidationError) as exc:
        _parse(data, mode="read")
    assert exc.value.issues[0].code == "document/unsupported-version"

    data = _document()
    data["format"] = "other"
    with pytest.raises(DocumentValidationError) as exc:
        _parse(data, mode="read")
    assert exc.value.issues[0].code == "document/unknown-format"


def test_malformed_document_read_raises_with_code() -> None:
    data = _document()
    del data["sections"]
    with pytest.raises(DocumentValidationError) as exc:
        _parse(data, mode="read")
    assert any(issue.code == "document/malformed-document" for issue in exc.value.issues)


def test_dangling_keyword_read_dropped() -> None:
    data = _document()
    data["sections"][0]["keywords"] = [{"word_id": "w-missing"}]
    document, issues = _parse(data, mode="read")
    assert document.sections[0].keywords == []
    assert any(issue.code == "document/dangling-keyword" for issue in issues)


def test_word_section_id_repaired_on_read() -> None:
    data = _document()
    data["sections"][1]["blocks"][0]["section_id"] = "missing"
    document, issues = _parse(data, mode="read")
    assert document.sections[1].blocks[0].section_id == "s1"
    assert any(issue.code == "document/invalid-word-section" for issue in issues)


def test_audio_script_in_group_read_removed() -> None:
    data = _document()
    data["sections"][0]["blocks"][0]["blocks"][2]["script"] = "重复"
    document, issues = _parse(data, mode="read")
    audio = document.sections[0].blocks[0].blocks[2]
    assert audio.script is None
    assert any(issue.code == "document/audio-script-in-group" for issue in issues)


def test_schema_file_matches_model() -> None:
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "src/situlearn/schemas/document.schema.json"
    assert json.loads(path.read_text(encoding="utf-8")) == document_schema()
