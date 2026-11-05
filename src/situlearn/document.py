"""SituLearn document format: models, strict/tolerant parsing, and JSON Schema.

The document is the single content truth. A ``.situ`` package is only a zip
container holding ``document.json`` plus the files referenced by relative
``media/...`` hrefs; the same document works when served over HTTP.

See ``docs/specs/SPEC-004-presentation-format/spec.md``.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections.abc import Iterator, Mapping
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from situlearn.knowledge import SourceRef

FORMAT = "situlearn.document"
VERSION = 1

ALLOWED_AUDIO_MIME = frozenset(
    {
        "audio/aac",
        "audio/mp4",
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
    }
)
ALLOWED_IMAGE_MIME = frozenset(
    {
        "image/avif",
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
RESOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
HREF_PATTERN = re.compile(r"^media/[A-Za-z0-9._/-]+$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
BCP47_PATTERN = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})*$")
_SHA256_FIELD = r"^[0-9a-f]{64}$"

BLOCK_TYPES = frozenset({"text", "image", "audio", "word", "group"})
SECTION_ROLES = frozenset({"narrative", "vocabulary", "cover", "summary"})
MAX_SECTIONS = 200
MAX_BLOCKS = 10_000
MAX_RESOURCES = 9_999
MAX_GROUP_DEPTH = 3

REQUIRED_LABELS = frozenset(
    {
        "report_eyebrow",
        "web_eyebrow",
        "narrative_heading",
        "narrative_lead",
        "play_all",
        "play_section",
        "no_audio",
        "expand_script",
        "section_unit",
        "section_counter_unit",
        "this_section",
        "key_terms_heading",
        "vocab_lead",
        "all_sections",
        "back_to_section",
        "previous_section",
        "next_section",
        "progress_narrative",
        "progress_section_audio",
        "vocabulary_heading",
        "category.domain_term",
        "category.proper_noun",
        "category.work_title",
        "category.school_genre",
        "category.common_advanced",
    }
)

Remoteness = Literal["write", "read"]


class ResourceType(StrEnum):
    AUDIO = "audio"
    IMAGE = "image"


class ResourceSource(StrEnum):
    TTS = "tts"
    DICTIONARY = "dictionary"
    GENERATED = "generated"


class SectionRole(StrEnum):
    NARRATIVE = "narrative"
    VOCABULARY = "vocabulary"
    COVER = "cover"
    SUMMARY = "summary"


class WordKind(StrEnum):
    WORD = "word"
    PHRASE = "phrase"
    SENTENCE = "sentence"


class TextStyle(StrEnum):
    BODY = "body"
    HEADING = "heading"
    CAPTION = "caption"
    QUOTE = "quote"


class TextMarkup(StrEnum):
    PLAIN = "plain"
    MARKDOWN = "markdown"


class Layout(StrEnum):
    STACK = "stack"
    ROW = "row"
    GRID = "grid"


class GroupRole(StrEnum):
    NARRATION = "narration"
    VISUAL = "visual"
    MIXED = "mixed"


class DocumentIssue(BaseModel):
    """A validation problem. Write paths treat errors as fatal; read paths warn."""

    severity: Literal["error", "warning"]
    code: str
    message: str
    path: str = ""


class DocumentValidationError(ValueError):
    """Raised when a document has errors the caller asked to be fatal."""

    def __init__(self, issues: list[DocumentIssue]) -> None:
        self.issues = issues
        detail = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(detail)


def href_issue(href: str) -> str | None:
    """Return a human-readable problem for an unsafe resource href."""

    if not href:
        return "href must not be empty"
    if "\\" in href:
        return "href must use '/' separators"
    if unicodedata.normalize("NFC", href) != href:
        return "href must be NFC-normalized"
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        return "href must be a relative path without scheme/query/fragment"
    if not HREF_PATTERN.fullmatch(href):
        return "href must match ^media/[A-Za-z0-9._/-]+$"
    parts = PurePosixPath(href).parts
    if any(part in {"", ".", ".."} for part in parts):
        return "href must not contain empty, '.' or '..' segments"
    return None


def check_id(value: str, *, kind: str = "id") -> str:
    if not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{kind} must match [A-Za-z0-9._-] and be 1-64 chars")
    return value


class TimeRange(BaseModel):
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def _ordered(self) -> TimeRange:
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be less than end_ms")
        return self


class Resource(BaseModel):
    type: ResourceType
    mime: str = Field(min_length=1)
    href: str = Field(min_length=1)
    duration_ms: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    sha256: str = Field(pattern=_SHA256_FIELD)
    source: ResourceSource | None = None
    alt: str | None = None
    credit: str | None = None

    @field_validator("href")
    @classmethod
    def _safe_href(cls, value: str) -> str:
        issue = href_issue(value)
        if issue:
            raise ValueError(issue)
        return value


class Generator(BaseModel):
    name: str = Field(min_length=1)
    version: str | None = None


class SourceMeta(BaseModel):
    filename: str | None = None
    sha256: str | None = Field(default=None, pattern=_SHA256_FIELD)
    language: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    cue_count: int | None = Field(default=None, ge=1)


class Meta(BaseModel):
    id: str | None = Field(default=None, pattern=_SHA256_FIELD)
    title: str = Field(min_length=1)
    language: str = Field(min_length=1)
    subtitle: str | None = None
    description: str | None = None
    kind: str | None = None
    created_at: str | None = None
    generator: Generator | None = None
    source: SourceMeta | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    attribution: list[str] | None = None
    extensions: dict[str, Any] | None = None


class _BlockBase(BaseModel):
    id: str | None = Field(default=None, min_length=1)
    layout: Layout | None = None


class TextBlock(_BlockBase):
    type: Literal["text"]
    text: str = Field(min_length=1)
    markup: TextMarkup = TextMarkup.PLAIN
    style: TextStyle = TextStyle.BODY
    lang: str | None = None
    speaker: str | None = None


class ImageBlock(_BlockBase):
    type: Literal["image"]
    resource: str = Field(min_length=1)
    alt: str | None = None


class AudioBlock(_BlockBase):
    type: Literal["audio"]
    resource: str = Field(min_length=1)
    script: str | None = None
    label: str | None = None


class WordBlock(_BlockBase):
    type: Literal["word"]
    id: str = Field(min_length=1)
    term: str = Field(min_length=1)
    kind: WordKind = WordKind.WORD
    lemma: str | None = None
    ipa: str | None = None
    pronunciation_note: str | None = None
    part_of_speech: str | None = None
    definitions: dict[str, str] = Field(min_length=1)
    context: str | None = None
    note: str | None = None
    category: str | None = None
    section_id: str = Field(min_length=1)
    audio: str | None = None
    image: str | None = None
    sources: list[SourceRef] | None = None
    tags: list[str] | None = None

    @field_validator("definitions")
    @classmethod
    def _definitions_not_blank(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("definitions must not be empty")
        for language, text in value.items():
            if not BCP47_PATTERN.fullmatch(language):
                raise ValueError(f"definitions key is not BCP-47: {language!r}")
            if not text.strip():
                raise ValueError("definitions must not contain blank text")
        return value


class Keyword(BaseModel):
    word_id: str = Field(min_length=1)


class GroupBlock(_BlockBase):
    type: Literal["group"]
    layout: Layout = Layout.STACK
    role: GroupRole | None = None
    script: str | None = None
    blocks: list[Block] = Field(min_length=1)

    @model_validator(mode="after")
    def _script_and_narration(self) -> GroupBlock:
        if self.script is not None and self.role is not GroupRole.NARRATION:
            raise ValueError("group.script is only allowed on role='narration'")
        for child in self.blocks:
            if isinstance(child, AudioBlock) and child.script:
                raise ValueError("audio.script is not allowed inside a group")
            if isinstance(child, GroupBlock) and child.role is GroupRole.NARRATION:
                raise ValueError("nested groups must not use role='narration'")
        return self


Block = Annotated[
    TextBlock | ImageBlock | AudioBlock | WordBlock | GroupBlock,
    Field(discriminator="type"),
]
GroupBlock.model_rebuild()


class Section(BaseModel):
    id: str = Field(min_length=1)
    role: SectionRole
    title: str = Field(min_length=1)
    subtitle: str | None = None
    time: TimeRange | None = None
    layout: Layout | None = None
    keywords: list[Keyword] = Field(default_factory=list)
    blocks: list[Block] = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        return check_id(value, kind="section id")

    @model_validator(mode="after")
    def _role_rules(self) -> Section:
        has_word = any(isinstance(block, WordBlock) for block in iter_blocks(self.blocks))
        if has_word and self.role is not SectionRole.VOCABULARY:
            raise ValueError("word blocks are only allowed in role='vocabulary'")
        if self.role is SectionRole.VOCABULARY:
            if self.id != "vocabulary":
                raise ValueError("vocabulary section id must be 'vocabulary'")
            if self.time is not None or self.keywords:
                raise ValueError("vocabulary section must not have time or keywords")
            if any(not isinstance(block, WordBlock) for block in self.blocks):
                raise ValueError("vocabulary section may only contain word blocks")
        elif self.role is SectionRole.NARRATIVE:
            if self.time is None:
                raise ValueError("narrative section must have a time range")
            if any(isinstance(block, (TextBlock, ImageBlock, AudioBlock)) for block in self.blocks):
                raise ValueError("narrative section must wrap narration primitives in a group")
            narration = [
                block
                for block in self.blocks
                if isinstance(block, GroupBlock) and block.role is GroupRole.NARRATION
            ]
            if len(narration) != 1:
                raise ValueError("narrative section must have exactly one narration group")
        else:
            if self.time is not None or self.keywords:
                raise ValueError(f"{self.role.value} section must not have time or keywords")
            if any(
                isinstance(block, GroupBlock) and block.role is GroupRole.NARRATION
                for block in self.blocks
            ):
                raise ValueError(f"{self.role.value} section must not contain a narration group")
        return self


def iter_blocks(blocks: list[Block]) -> Iterator[Block]:
    for block in blocks:
        yield block
        if isinstance(block, GroupBlock):
            yield from iter_blocks(block.blocks)


def _group_depth(block: Block) -> int:
    if not isinstance(block, GroupBlock):
        return 0
    return 1 + max((_group_depth(child) for child in block.blocks), default=0)


def _refs(block: Block) -> Iterator[tuple[str, str]]:
    if isinstance(block, (ImageBlock, AudioBlock)):
        yield block.resource, "resource"
    elif isinstance(block, WordBlock):
        if block.audio:
            yield block.audio, "audio"
        if block.image:
            yield block.image, "image"


class Document(BaseModel):
    format: Literal["situlearn.document"]
    version: Literal[1]
    meta: Meta
    resources: dict[str, Resource] = Field(default_factory=dict)
    sections: list[Section] = Field(min_length=1)
    extensions: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _structure(self) -> Document:
        if len(self.sections) > MAX_SECTIONS:
            raise ValueError(f"sections exceed {MAX_SECTIONS}")
        if len(self.resources) > MAX_RESOURCES:
            raise ValueError(f"resources exceed {MAX_RESOURCES}")

        section_ids: set[str] = set()
        block_ids: set[str] = set()
        word_ids: set[str] = set()
        word_by_id: dict[str, WordBlock] = {}
        keyword_checks: list[tuple[Section, Keyword]] = []
        vocabulary_count = 0
        block_count = 0
        last_start: int | None = None
        hrefs: set[str] = set()

        for resource_id, resource in self.resources.items():
            if not RESOURCE_ID_PATTERN.fullmatch(resource_id):
                raise ValueError(f"invalid resource id: {resource_id!r}")
            if resource.href in hrefs:
                raise ValueError(f"duplicate resource href: {resource.href!r}")
            hrefs.add(resource.href)
            allowed = (
                ALLOWED_AUDIO_MIME if resource.type is ResourceType.AUDIO else ALLOWED_IMAGE_MIME
            )
            if resource.mime not in allowed:
                raise ValueError(f"unsupported mime for {resource_id}: {resource.mime!r}")

        for section in self.sections:
            if section.id in section_ids:
                raise ValueError(f"duplicate section id: {section.id}")
            section_ids.add(section.id)
            if section.role is SectionRole.VOCABULARY:
                vocabulary_count += 1
            if section.time is not None:
                if last_start is not None and section.time.start_ms < last_start:
                    raise ValueError("timed sections must be ordered by start_ms")
                last_start = section.time.start_ms
            keyword_checks.extend((section, keyword) for keyword in section.keywords)

            for block in iter_blocks(section.blocks):
                block_count += 1
                if block.id:
                    if block.id in block_ids:
                        raise ValueError(f"duplicate block id: {block.id}")
                    block_ids.add(block.id)
                if isinstance(block, WordBlock):
                    if block.id in word_ids:
                        raise ValueError(f"duplicate word id: {block.id}")
                    word_ids.add(block.id)
                    word_by_id[block.id] = block
                if isinstance(block, GroupBlock) and _group_depth(block) > MAX_GROUP_DEPTH:
                    raise ValueError(f"group nesting exceeds {MAX_GROUP_DEPTH}")
                for reference, field in _refs(block):
                    if reference not in self.resources:
                        raise ValueError(f"missing resource {reference!r} for {block.type}.{field}")
                    resource = self.resources[reference]
                    if isinstance(block, ImageBlock):
                        expected = ResourceType.IMAGE
                    elif isinstance(block, AudioBlock):
                        expected = ResourceType.AUDIO
                    else:
                        expected = ResourceType.AUDIO if field == "audio" else ResourceType.IMAGE
                    if resource.type is not expected:
                        raise ValueError(
                            f"resource {reference!r} has type {resource.type.value}, "
                            f"expected {expected.value}"
                        )

        if block_count > MAX_BLOCKS:
            raise ValueError(f"blocks exceed {MAX_BLOCKS}")
        if vocabulary_count > 1:
            raise ValueError("document must have at most one vocabulary section")
        if word_ids and vocabulary_count == 0:
            raise ValueError("word blocks require a vocabulary section")

        for section, keyword in keyword_checks:
            word = word_by_id.get(keyword.word_id)
            if word is None:
                raise ValueError(f"keyword references missing word: {keyword.word_id}")
            if word.section_id != section.id:
                raise ValueError(
                    f"keyword {keyword.word_id} belongs to {word.section_id}, not {section.id}"
                )

        for word in word_by_id.values():
            if word.section_id not in section_ids:
                raise ValueError(f"word {word.id} references missing section {word.section_id}")
            target = next(section for section in self.sections if section.id == word.section_id)
            if target.role is not SectionRole.NARRATIVE:
                raise ValueError(f"word {word.id} section_id must reference a narrative section")

        if (
            self.meta.id
            and self.meta.source
            and self.meta.source.sha256
            and self.meta.id != self.meta.source.sha256
        ):
            raise ValueError("meta.id must equal meta.source.sha256 when both exist")
        return self

    def to_json(self) -> str:
        return self.model_dump_json(exclude_none=True, indent=2) + "\n"

    @classmethod
    def from_json(cls, data: str | bytes) -> Document:
        document, _ = parse_document(data, mode="read")
        return document


def check_document(
    document: Document,
    *,
    mode: Remoteness = "write",
) -> list[DocumentIssue]:
    """Policy checks not expressible in the structural model."""

    issues: list[DocumentIssue] = []
    severity: Literal["error", "warning"] = "error" if mode == "write" else "warning"

    if mode == "write":
        missing_labels = sorted(REQUIRED_LABELS - set(document.meta.labels))
        for key in missing_labels:
            issues.append(
                DocumentIssue(
                    severity="error",
                    code="document/missing-label",
                    message=f"missing required label: {key}",
                    path="meta.labels",
                )
            )

    has_source_sha = bool(document.meta.source and document.meta.source.sha256)
    if not has_source_sha and not document.meta.id:
        issues.append(
            DocumentIssue(
                severity=severity,
                code="document/invalid-id-source",
                message="document needs meta.source.sha256 or meta.id",
                path="meta",
            )
        )

    last_start: int | None = None
    last_end: int | None = None
    for section in document.sections:
        if section.time is None:
            continue
        if last_start is not None and section.time.start_ms < last_start:
            issues.append(
                DocumentIssue(
                    severity="error",
                    code="document/time-out-of-order",
                    message=f"section {section.id} starts before the previous section",
                    path=f"sections[{section.id}].time",
                )
            )
        if last_end is not None and section.time.start_ms < last_end:
            issues.append(
                DocumentIssue(
                    severity="warning",
                    code="document/overlapping-time",
                    message=f"section {section.id} overlaps the previous section",
                    path=f"sections[{section.id}].time",
                )
            )
        last_start = section.time.start_ms
        last_end = section.time.end_ms

    return issues


MISSING_SHA256 = "0" * 64
_BLOCK_MODELS: dict[str, type[BaseModel]] = {
    "text": TextBlock,
    "image": ImageBlock,
    "audio": AudioBlock,
    "word": WordBlock,
}


def _warn(issues: list[DocumentIssue], code: str, message: str, path: str = "") -> None:
    issues.append(DocumentIssue(severity="warning", code=code, message=message, path=path))


def _iter_raw_blocks(blocks: list[Any]) -> Iterator[dict[str, Any]]:
    for block in blocks:
        if not isinstance(block, dict):
            continue
        yield block
        if block.get("type") == "group" and isinstance(block.get("blocks"), list):
            yield from _iter_raw_blocks(block["blocks"])


def _normalize_block(
    block: dict[str, Any],
    issues: list[DocumentIssue],
    path: str,
) -> dict[str, Any] | None:
    kind = block.get("type")
    if kind not in BLOCK_TYPES:
        _warn(issues, "document/unknown-block-type", f"unknown block type {kind!r}; skipped", path)
        return None

    block = dict(block)
    layout = block.get("layout")
    if layout is not None and layout not in {"stack", "row", "grid"}:
        block.pop("layout", None)
        _warn(issues, "document/unknown-layout", f"unknown layout {layout!r}; ignored", path)

    if kind == "text":
        if block.get("style") not in {None, "body", "heading", "caption", "quote"}:
            block["style"] = "body"
            _warn(issues, "document/unknown-style", "unknown text style; fallback body", path)
        if block.get("markup") not in {None, "plain", "markdown"}:
            block["markup"] = "plain"
            _warn(issues, "document/unknown-style", "unknown markup; fallback plain", path)
    elif kind == "word":
        if block.get("kind") not in {None, "word", "phrase", "sentence"}:
            block["kind"] = "word"
            _warn(
                issues,
                "document/unknown-word-kind",
                "unknown word kind; fallback word",
                path,
            )
    elif kind == "group":
        role = block.get("role")
        if role is not None and role not in {"narration", "visual", "mixed"}:
            block.pop("role", None)
            _warn(issues, "document/unknown-role", f"unknown group role {role!r}; ignored", path)
        if block.get("script") is not None and block.get("role") != "narration":
            block.pop("script", None)
            _warn(
                issues,
                "document/script-on-non-narration-group",
                "group.script on non-narration group; ignored",
                path,
            )
        children = block.get("blocks")
        if not isinstance(children, list):
            _warn(issues, "document/malformed-block", "group blocks must be a list; skipped", path)
            return None
        normalized: list[dict[str, Any]] = []
        for index, child in enumerate(children):
            if not isinstance(child, dict):
                _warn(issues, "document/malformed-block", "block is not an object; skipped", path)
                continue
            child = dict(child)
            if child.get("type") == "audio" and child.get("script"):
                child.pop("script", None)
                _warn(
                    issues,
                    "document/audio-script-in-group",
                    "audio.script inside group; ignored",
                    f"{path}.blocks[{index}]",
                )
            if child.get("type") == "group" and child.get("role") == "narration":
                child["role"] = "visual"
                _warn(
                    issues,
                    "document/nested-narration-group",
                    "nested narration group; role reset to visual",
                    f"{path}.blocks[{index}]",
                )
            result = _normalize_block(child, issues, f"{path}.blocks[{index}]")
            if result is not None:
                normalized.append(result)
        if not normalized:
            _warn(issues, "document/empty-group", "group has no known blocks; skipped", path)
            return None
        block["blocks"] = normalized

    model = GroupBlock if kind == "group" else _BLOCK_MODELS[kind]
    try:
        model.model_validate(block)
    except ValidationError as exc:
        _warn(issues, "document/malformed-block", f"malformed {kind} block; skipped: {exc}", path)
        return None
    return block


def _tolerant_blocks(
    blocks: list[Any],
    issues: list[DocumentIssue],
    path: str,
) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            _warn(issues, "document/malformed-block", "block is not an object; skipped", path)
            continue
        result = _normalize_block(block, issues, f"{path}[{index}]")
        if result is not None:
            kept.append(result)
    return kept


def _placeholder_resource(
    resources: dict[str, Any],
    expected: str,
    issues: list[DocumentIssue],
    message: str,
    code: str,
    path: str,
) -> str:
    index = 1
    while f"ph-{index}" in resources:
        index += 1
    resource_id = f"ph-{index}"
    resources[resource_id] = {
        "type": expected,
        "mime": "audio/mpeg" if expected == "audio" else "image/png",
        "href": f"media/missing/{resource_id}",
        "sha256": MISSING_SHA256,
        "alt": "missing resource",
    }
    _warn(issues, code, message, path)
    return resource_id


def _resolve_refs(raw: dict[str, Any], issues: list[DocumentIssue]) -> None:
    resources = raw.setdefault("resources", {})
    if not isinstance(resources, dict):
        resources = {}
        raw["resources"] = resources

    for section in raw.get("sections", []):
        if not isinstance(section, dict):
            continue
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            continue
        for block in _iter_raw_blocks(blocks):
            kind = block.get("type")
            pairs: list[tuple[str, str]] = []
            if kind == "image":
                pairs.append(("resource", "image"))
            elif kind == "audio":
                pairs.append(("resource", "audio"))
            elif kind == "word":
                if block.get("audio"):
                    pairs.append(("audio", "audio"))
                if block.get("image"):
                    pairs.append(("image", "image"))
            for field, expected in pairs:
                reference = block.get(field)
                resource = resources.get(reference)
                if not isinstance(resource, dict):
                    block[field] = _placeholder_resource(
                        resources,
                        expected,
                        issues,
                        f"missing resource {reference!r}",
                        "document/unresolved-resource",
                        f"block.{field}",
                    )
                elif resource.get("type") != expected:
                    block[field] = _placeholder_resource(
                        resources,
                        expected,
                        issues,
                        f"resource {reference!r} has wrong type; placeholder used",
                        "document/resource-type-mismatch",
                        f"block.{field}",
                    )


def _fix_section_shapes(raw: dict[str, Any], issues: list[DocumentIssue]) -> None:
    sections = raw.get("sections")
    if not isinstance(sections, list):
        return
    kept_sections: list[Any] = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            kept_sections.append(section)
            continue
        role = section.get("role")
        blocks = section.get("blocks")
        if not isinstance(blocks, list):
            continue
        kept: list[Any] = []
        narration_groups = 0
        for block in blocks:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            is_narration = kind == "group" and block.get("role") == "narration"
            if role == "vocabulary":
                if kind != "word":
                    _warn(
                        issues,
                        "document/invalid-vocabulary-content",
                        "non-word block in vocabulary section; skipped",
                        f"sections[{index}]",
                    )
                    continue
            elif role == "narrative":
                if kind in {"text", "image", "audio", "word"}:
                    _warn(
                        issues,
                        "document/scattered-narration",
                        "top-level primitive in narrative section; skipped",
                        f"sections[{index}]",
                    )
                    continue
                if is_narration:
                    narration_groups += 1
                    if narration_groups > 1:
                        _warn(
                            issues,
                            "document/duplicate-narration-group",
                            "extra narration group; skipped",
                            f"sections[{index}]",
                        )
                        continue
            else:
                if kind == "word" or is_narration:
                    _warn(
                        issues,
                        "document/narration-in-cover",
                        "word/narration block in cover/summary; skipped",
                        f"sections[{index}]",
                    )
                    continue
            kept.append(block)
        if role == "narrative" and narration_groups == 0:
            _warn(
                issues,
                "document/missing-narration-group",
                "narrative section has no narration group; skipped",
                f"sections[{index}]",
            )
            continue
        if not kept:
            _warn(
                issues,
                "document/empty-section",
                "section has no known blocks; skipped",
                f"sections[{index}]",
            )
            continue
        section = dict(section)
        section["blocks"] = kept
        kept_sections.append(section)
    raw["sections"] = kept_sections


def _fix_word_sections(raw: dict[str, Any], issues: list[DocumentIssue]) -> None:
    sections = raw.get("sections")
    if not isinstance(sections, list):
        return
    narrative_ids = [
        section["id"]
        for section in sections
        if isinstance(section, dict)
        and section.get("role") == "narrative"
        and isinstance(section.get("id"), str)
    ]

    word_by_id: dict[str, dict[str, Any]] = {}
    kept_sections: list[Any] = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict) or section.get("role") != "vocabulary":
            kept_sections.append(section)
            continue
        kept: list[Any] = []
        for block in section.get("blocks", []):
            if not isinstance(block, dict) or block.get("type") != "word":
                continue
            word_id = block.get("id")
            if not isinstance(word_id, str) or not word_id:
                _warn(
                    issues,
                    "document/missing-word-id",
                    "word block has no id; skipped",
                    f"sections[{index}]",
                )
                continue
            if block.get("section_id") not in narrative_ids:
                if not narrative_ids:
                    _warn(
                        issues,
                        "document/invalid-word-section",
                        "word has no narrative section; skipped",
                        f"sections[{index}]",
                    )
                    continue
                block = dict(block)
                block["section_id"] = narrative_ids[0]
                _warn(
                    issues,
                    "document/invalid-word-section",
                    "word section_id repaired to first narrative section",
                    f"sections[{index}]",
                )
            word_by_id[word_id] = block
            kept.append(block)
        if not kept:
            _warn(
                issues,
                "document/empty-section",
                "vocabulary section has no words; skipped",
                f"sections[{index}]",
            )
            continue
        section = dict(section)
        section["blocks"] = kept
        kept_sections.append(section)
    raw["sections"] = kept_sections

    for section in kept_sections:
        if not isinstance(section, dict) or section.get("role") != "narrative":
            continue
        keywords = section.get("keywords")
        if not isinstance(keywords, list):
            continue
        kept_keywords: list[Any] = []
        for keyword in keywords:
            word_id = keyword.get("word_id") if isinstance(keyword, dict) else None
            word = word_by_id.get(word_id) if isinstance(word_id, str) else None
            if word is None:
                _warn(
                    issues,
                    "document/dangling-keyword",
                    f"keyword {word_id!r} has no word; skipped",
                    f"sections[{section.get('id')}]",
                )
                continue
            if word.get("section_id") != section.get("id"):
                _warn(
                    issues,
                    "document/cross-section-keyword",
                    "keyword belongs to another section; skipped",
                    f"sections[{section.get('id')}]",
                )
                continue
            kept_keywords.append(keyword)
        section["keywords"] = kept_keywords


def _tolerant_prepare(raw: Mapping[str, Any], issues: list[DocumentIssue]) -> dict[str, Any]:
    result = copy.deepcopy(dict(raw))

    resources = result.get("resources")
    if not isinstance(resources, dict):
        resources = {}
        result["resources"] = resources
    for resource_id in list(resources):
        resource = resources[resource_id]
        if not isinstance(resource, dict):
            resources.pop(resource_id)
            _warn(issues, "document/malformed-block", "resource is not an object; skipped")
            continue
        if resource.get("type") not in {"audio", "image"}:
            resources.pop(resource_id)
            _warn(issues, "document/malformed-block", f"resource {resource_id!r} has no type")
            continue
        source = resource.get("source")
        if source is not None and source not in {"tts", "dictionary", "generated"}:
            resource.pop("source", None)
            _warn(issues, "document/unknown-source", "unknown resource source; ignored")
        sha256 = resource.get("sha256")
        if not isinstance(sha256, str) or not SHA256_PATTERN.fullmatch(sha256):
            resource["sha256"] = MISSING_SHA256
            _warn(issues, "document/missing-hash", f"resource {resource_id!r} has no hash")
        href = resource.get("href")
        if isinstance(href, str) and href_issue(href):
            resources.pop(resource_id)
            _warn(issues, "document/invalid-href", f"resource {resource_id!r} href invalid")

    sections = result.get("sections")
    if not isinstance(sections, list):
        return result
    normalized_sections: list[Any] = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            _warn(issues, "document/malformed-block", "section is not an object; skipped")
            continue
        role = section.get("role")
        if role not in SECTION_ROLES:
            _warn(issues, "document/unknown-role", f"unknown section role {role!r}; skipped")
            continue
        section = dict(section)
        blocks = section.get("blocks")
        if isinstance(blocks, list):
            section["blocks"] = _tolerant_blocks(blocks, issues, f"sections[{index}].blocks")
        normalized_sections.append(section)
    result["sections"] = normalized_sections

    _fix_section_shapes(result, issues)
    _resolve_refs(result, issues)
    _fix_word_sections(result, issues)
    return result


def _load_raw(data: str | bytes | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(data, (str, bytes)):
        value = json.loads(data)
    else:
        value = dict(data)
    if not isinstance(value, dict):
        raise TypeError("document must be a JSON object")
    return value


def _check_envelope(raw: Mapping[str, Any], issues: list[DocumentIssue]) -> None:
    if raw.get("format") != FORMAT:
        issues.append(
            DocumentIssue(
                severity="error",
                code="document/unknown-format",
                message=f"format must be {FORMAT!r}",
                path="format",
            )
        )
        raise DocumentValidationError(issues)
    if raw.get("version") != VERSION:
        issues.append(
            DocumentIssue(
                severity="error",
                code="document/unsupported-version",
                message=f"version must be {VERSION}",
                path="version",
            )
        )
        raise DocumentValidationError(issues)


def parse_document(
    data: str | bytes | Mapping[str, Any],
    *,
    mode: Remoteness = "read",
) -> tuple[Document, list[DocumentIssue]]:
    issues: list[DocumentIssue] = []
    raw = _load_raw(data)
    _check_envelope(raw, issues)
    if mode == "read":
        raw = _tolerant_prepare(raw, issues)
        try:
            document = Document.model_validate(raw)
        except ValidationError as exc:
            issues.append(
                DocumentIssue(
                    severity="error",
                    code="document/malformed-document",
                    message=f"document is not structurally valid: {exc}",
                )
            )
            raise DocumentValidationError(issues) from exc
    else:
        document = Document.model_validate(raw)
    issues.extend(check_document(document, mode=mode))
    return document, issues


def raise_for_errors(issues: list[DocumentIssue]) -> None:
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise DocumentValidationError(errors)


def load_document(
    path: Path,
    *,
    mode: Remoteness = "read",
) -> tuple[Document, list[DocumentIssue]]:
    return parse_document(path.read_text(encoding="utf-8"), mode=mode)


def save_document(document: Document, path: Path) -> None:
    path.write_text(document.to_json(), encoding="utf-8")


def document_schema() -> dict[str, Any]:
    schema = Document.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return schema


__all__ = [
    "ALLOWED_AUDIO_MIME",
    "ALLOWED_IMAGE_MIME",
    "BCP47_PATTERN",
    "BLOCK_TYPES",
    "FORMAT",
    "HREF_PATTERN",
    "MAX_BLOCKS",
    "MAX_GROUP_DEPTH",
    "MAX_RESOURCES",
    "MAX_SECTIONS",
    "REQUIRED_LABELS",
    "VERSION",
    "AudioBlock",
    "Block",
    "Document",
    "DocumentIssue",
    "DocumentValidationError",
    "Generator",
    "GroupBlock",
    "GroupRole",
    "ImageBlock",
    "Keyword",
    "Layout",
    "Meta",
    "Resource",
    "ResourceSource",
    "ResourceType",
    "Section",
    "SectionRole",
    "SourceMeta",
    "TextBlock",
    "TextMarkup",
    "TextStyle",
    "TimeRange",
    "WordBlock",
    "WordKind",
    "check_document",
    "document_schema",
    "href_issue",
    "iter_blocks",
    "load_document",
    "parse_document",
    "raise_for_errors",
    "save_document",
]
