from __future__ import annotations

import hashlib

import pytest

from situlearn import prompts
from situlearn.knowledge import ContentType

DOCUMENTARY_HASHES = {
    "NARRATIVE_SYSTEM": "76fa87890d30fd8d9dd7d8c9ec9911f67a5b774d8aff3467f0eeb09960ccd7f3",
    "NARRATIVE_USER": "cdef49dc0b653f3684a88e187a05c62a040430dce96598bc7d0b2ae5a0069b38",
    "CHINESE_REPAIR_SYSTEM": "e893b2498630149c9c239f5015d8f29156887ebb00f2fcf7b64a3bf5fa173466",
    "CHINESE_REPAIR_USER": "b6187f0878fbebf0bd1cd276b55f7cb035e240f1cc3545319719baa35655dbd5",
    "VOCAB_SYSTEM": "4aebca3206353b2b9363f7c9ad98783a84791fa71bdf02555d41ff6a7f01f66d",
    "VOCAB_USER": "482bf25a2b1d801d4e6f7806277b94531614d16d548016813187c2e867feb2e0",
    "GLOSS_SYSTEM": "60249031d1438933309955d96dd289946330015dfd466b24ba82a623ccc85e65",
    "GLOSS_USER": "1fbea0ce785b09f690c2664950a22dc867005b3d674ec9df1f9edb9960dd904a",
}


def test_documentary_prompts_are_frozen() -> None:
    for name, expected in DOCUMENTARY_HASHES.items():
        actual = hashlib.sha256(getattr(prompts, name).encode("utf-8")).hexdigest()
        assert actual == expected, name


def test_prompts_for_selects_documentary_by_default() -> None:
    prompt_set = prompts.prompts_for(ContentType.DOCUMENTARY)
    assert prompt_set.narrative_system == prompts.NARRATIVE_SYSTEM
    assert prompt_set.vocab_system == prompts.VOCAB_SYSTEM
    assert prompt_set.gloss_user == prompts.GLOSS_USER


def test_prompts_for_movie_uses_movie_templates() -> None:
    prompt_set = prompts.prompts_for(ContentType.MOVIE)
    assert prompt_set.narrative_system == prompts.NARRATIVE_SYSTEM_MOVIE
    assert prompt_set.vocab_system == prompts.VOCAB_SYSTEM_MOVIE
    assert prompt_set.gloss_user == prompts.GLOSS_USER_MOVIE


def test_movie_narrative_prompt_covers_plot_requirements() -> None:
    prompt = prompts.NARRATIVE_USER_MOVIE
    assert "{source_name}" in prompt
    assert "完整剧透" in prompt
    assert "潜台词" in prompt
    assert "人物" in prompt
    assert "剧情" in prompt
    assert "6 到 12 个场景段落" in prompt
    assert "不要写成影评" in prompt
    assert "本片讲述了" in prompt


def test_movie_vocab_prompt_reframes_why_it_matters() -> None:
    prompt = prompts.VOCAB_USER_MOVIE
    assert "台词" in prompt
    assert "人物关系" in prompt
    assert "断掉哪条论证" not in prompt


def test_prompts_for_rejects_unknown_type() -> None:
    with pytest.raises(ValueError):
        prompts.prompts_for("podcast")
