from __future__ import annotations

import pytest

from situlearn.cli import build_parser


def test_build_content_type_defaults_to_documentary() -> None:
    args = build_parser().parse_args(["build", "input.srt", "--out", "out"])

    assert args.content_type == "documentary"


def test_build_accepts_movie_content_type() -> None:
    args = build_parser().parse_args(
        ["build", "input.srt", "--out", "out", "--content-type", "movie"]
    )

    assert args.content_type == "movie"


def test_build_rejects_unknown_content_type() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(
            ["build", "input.srt", "--out", "out", "--content-type", "podcast"]
        )

    assert exc.value.code == 2
