"""Tests for server-rendered public document pages."""

from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

from web_fixtures import client, document, publish, settings

import situlearn.render
from situlearn.render import DOCUMENT_SCRIPT_CSP_HASH


def _published(tmp_path: Path, *, kind: str = "documentary"):
    test_client = client(settings(tmp_path))
    response = publish(test_client, document_dict=document(kind=kind))
    assert response.status_code == 201, response.text
    return test_client, response.json()["slug"]


def test_report_home_renders_public_content(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(f"/r/{slug}")
    assert response.status_code == 200
    html = response.text
    assert "Web Test Report" in html
    assert "内容脉络" in html
    assert "word" in html
    assert "<audio" in html
    assert "<img" in html
    assert "word-w-1" in html
    assert f"/r/{slug}/media/audio/s0.mp3" in html
    assert f"/r/{slug}/media/audio/term.mp3" in html
    assert 'src="media/' not in html
    assert "data-playlist='[\"media/" not in html


def test_movie_report_uses_plot_labels(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path, kind="movie")
    html = test_client.get(f"/r/{slug}").text
    assert "剧情脉络" in html
    assert "电影学习报告" in html
    assert "内容脉络" not in html


def test_chapter_page_renders_spoken_text(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(f"/r/{slug}/chapters/s1")
    assert response.status_code == 200
    assert "Spoken text for section 1." in response.text
    assert "Spoken text for section 0." not in response.text
    assert f"/r/{slug}/media/audio/s1.mp3" in response.text


def test_vocabulary_page_filters(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(f"/r/{slug}/vocabulary?section=s0")
    assert response.status_code == 200
    assert 'id="word-w-1"' in response.text
    assert 'data-category-filter="domain_term"' in response.text
    assert "data-word-search" in response.text
    assert f"/r/{slug}/media/audio/term.mp3" in response.text

    empty = test_client.get(f"/r/{slug}/vocabulary?section=s1")
    assert 'id="word-w-1"' not in empty.text

    missing = test_client.get(f"/r/{slug}/vocabulary?q=not-present")
    assert 'id="word-w-1"' not in missing.text


def test_unknown_report_returns_404_and_unpublished_returns_410(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    assert test_client.get("/r/unknown").status_code == 404
    assert test_client.delete(
        f"/api/v1/reports/{slug}",
        headers={"Authorization": "Bearer test-token"},
    ).status_code == 204
    assert test_client.get(f"/r/{slug}").status_code == 410


def test_media_serves_range(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(
        f"/r/{slug}/media/audio/s0.mp3",
        headers={"Range": "bytes=0-2"},
    )
    assert response.status_code == 206
    assert response.content == b"sec"
    assert response.headers["content-range"] == f"bytes 0-2/{len(b'section-0')}"
    assert response.headers["accept-ranges"] == "bytes"


def test_public_headers_and_head_request(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(f"/r/{slug}")
    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert "default-src 'self'" in response.headers["content-security-policy"]
    head = test_client.head(f"/r/{slug}")
    assert head.status_code == 200


def test_unregistered_media_path_is_rejected(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(f"/r/{slug}/media/audio/not-registered.mp3")
    assert response.status_code == 404


def test_csp_allows_document_inline_script(tmp_path: Path) -> None:
    test_client, slug = _published(tmp_path)
    response = test_client.get(f"/r/{slug}")
    csp = response.headers["content-security-policy"]
    assert f"'{DOCUMENT_SCRIPT_CSP_HASH}'" in csp

    template_path = Path(situlearn.render.__file__).parent / "templates" / "document.html.j2"
    body = re.search(r"<script>(.*?)</script>", template_path.read_text(), re.DOTALL).group(1)
    expected = "sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
    assert expected == DOCUMENT_SCRIPT_CSP_HASH
