"""Static accessibility and responsive-style checks for the public pages."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "src" / "situlearn" / "web" / "static" / "styles.css").read_text(
    encoding="utf-8"
)
BASE_TEMPLATE = (
    ROOT / "src" / "situlearn" / "web" / "templates" / "base.html.j2"
).read_text(encoding="utf-8")
VOCAB_TEMPLATE = (
    ROOT / "src" / "situlearn" / "web" / "templates" / "vocabulary.html.j2"
).read_text(encoding="utf-8")
FILTERS_JS = (
    ROOT / "src" / "situlearn" / "web" / "static" / "filters.js"
).read_text(encoding="utf-8")


def _color(name: str) -> str:
    match = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", CSS)
    assert match, f"missing CSS color token --{name}"
    return match.group(1)


def _luminance(value: str) -> float:
    channels = [int(value[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    bright, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def test_stylesheet_is_mobile_safe_and_touch_friendly():
    assert "* {\n  box-sizing: border-box;" in CSS
    assert "min-height: 44px" in CSS
    assert "min-width: 44px" in CSS
    assert "@media (max-width: 480px)" in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert ":focus-visible" in CSS
    assert "env(safe-area-inset-bottom)" in CSS
    assert "overflow-wrap: anywhere" in CSS


def test_text_and_button_contrast_meets_wcag_aa():
    assert _contrast(_color("ink"), _color("bg")) >= 4.5
    assert _contrast(_color("muted"), _color("bg")) >= 4.5
    assert _contrast(_color("accent"), _color("surface")) >= 4.5
    assert _contrast(_color("accent-ink"), _color("accent")) >= 4.5


def test_templates_have_accessibility_metadata_and_labels():
    assert 'lang="zh-CN"' in BASE_TEMPLATE
    assert 'name="viewport"' in BASE_TEMPLATE
    assert 'name="robots"' in BASE_TEMPLATE
    assert 'class="skip-link"' in BASE_TEMPLATE
    assert 'aria-label="报告导航"' in BASE_TEMPLATE
    assert 'aria-label="播放 ' in VOCAB_TEMPLATE
    assert "/static/filters.js" in VOCAB_TEMPLATE


def test_filters_apply_on_change_and_search():
    assert "HTMLSelectElement" in FILTERS_JS
    assert "requestSubmit" in FILTERS_JS
    assert 'addEventListener("change"' in FILTERS_JS
    assert 'addEventListener("input"' in FILTERS_JS
    assert "setTimeout(submitFilters, 350)" in FILTERS_JS


def test_static_stylesheet_is_served(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", backup_dir=tmp_path / "backup")
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "--accent" in response.text
