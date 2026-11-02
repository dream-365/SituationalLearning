"""PWA manifest and offline fallback for public reports."""

from __future__ import annotations

from situlearn.web.render import PublicReport

_THEME_COLOR = "#0b5f8a"
_BACKGROUND_COLOR = "#f6f3ec"


def manifest_for(report: PublicReport) -> dict[str, object]:
    short_name = report.title.strip()[:12] or "情景学习"
    return {
        "id": f"/r/{report.slug}",
        "name": report.title,
        "short_name": short_name,
        "description": report.logline,
        "lang": "zh-CN",
        "start_url": f"/r/{report.slug}",
        "scope": f"/r/{report.slug}/",
        "display": "standalone",
        "background_color": _BACKGROUND_COLOR,
        "theme_color": _THEME_COLOR,
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
        ],
    }


def offline_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="robots" content="noindex, nofollow">
  <title>离线 · 情景学习</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="page-offline">
  <main class="site-main" id="main">
    <section class="hero">
      <p class="eyebrow">情景学习</p>
      <h1>当前处于离线状态</h1>
      <p class="logline">这份报告还没有缓存到本机，或者网络暂时不可用。</p>
      <p class="background">已打开过的报告和已播放过的音频会保存在本机；恢复网络后刷新页面即可继续。</p>
    </section>
  </main>
</body>
</html>
"""
