"""Contract checks for the browser player and its templates."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "src" / "situlearn" / "web" / "static" / "player.js"
PLAYER_TEXT = PLAYER.read_text(encoding="utf-8")
BASE_TEMPLATE = (
    ROOT / "src" / "situlearn" / "web" / "templates" / "base.html.j2"
).read_text(encoding="utf-8")
REPORT_TEMPLATE = (
    ROOT / "src" / "situlearn" / "web" / "templates" / "report.html.j2"
).read_text(encoding="utf-8")
CHAPTER_TEMPLATE = (
    ROOT / "src" / "situlearn" / "web" / "templates" / "chapter.html.j2"
).read_text(encoding="utf-8")


def test_player_uses_one_audio_element_and_playlist():
    assert "new Audio()" in PLAYER_TEXT
    assert "state.playlist" in PLAYER_TEXT
    assert 'document.createElement("audio")' not in PLAYER_TEXT
    assert "loadIndex(state.index + 1)" in PLAYER_TEXT
    assert "player.hidden = false" in PLAYER_TEXT


def test_player_registers_media_session_controls():
    assert "mediaSession" in PLAYER_TEXT
    assert "MediaMetadata" in PLAYER_TEXT
    assert "setPositionState" in PLAYER_TEXT
    assert "playbackState" in PLAYER_TEXT
    for action in ("play", "pause", "previoustrack", "nexttrack", "seekto"):
        assert f'setActionHandler("{action}"' in PLAYER_TEXT


def test_player_persists_and_restores_chapter_progress():
    assert "situlearn:progress:" in PLAYER_TEXT
    assert "localStorage.setItem" in PLAYER_TEXT
    assert "localStorage.getItem" in PLAYER_TEXT
    assert "asset_index" in PLAYER_TEXT
    assert "current_time_s" in PLAYER_TEXT
    assert "data-section-id" in PLAYER_TEXT
    assert "继续上次播放" in PLAYER_TEXT
    assert "state.kind !== \"chapter\"" in PLAYER_TEXT


def test_templates_wire_player_to_sections():
    assert "/static/player.js" in BASE_TEMPLATE
    assert 'data-report-slug="{{ report.slug }}"' in BASE_TEMPLATE
    assert 'data-section-id="{{ section.section_id }}"' in REPORT_TEMPLATE
    assert 'data-section-id="{{ section.section_id }}"' in CHAPTER_TEMPLATE
    assert "data-srcs=" in REPORT_TEMPLATE


def test_player_javascript_parses():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    subprocess.run([node, "--check", str(PLAYER)], check=True)


def test_player_is_served(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", backup_dir=tmp_path / "backup")
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/static/player.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert "mediaSession" in response.text
