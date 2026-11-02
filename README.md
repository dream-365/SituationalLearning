# 情景学习（SituLearn）

Turn a documentary `.srt` into an offline HTML study report: a Chinese spoken narrative, plus a vocabulary notebook with IPA, bilingual definitions, context sentences, and human pronunciation.

## Status

Working end-to-end on a 60-minute documentary sample: 8 Chinese narrative chapters, 74 terms, 73/74 human pronunciation clips, 82 offline audio files. Full build about 9 minutes; fully cached rebuild under 1 second. The report includes a bottom progress player with current/total time and remaining time.

Spec: `docs/specs/SPEC-001-subtitle-learning-report/spec.md` (Approved)
Plan: `docs/specs/SPEC-001-subtitle-learning-report/plan.md` (Approved)

## Setup

```bash
uv sync --frozen
cp your-documentary.en.srt samples/
uv run situlearn build samples/your-documentary.en.srt --out reports/your-documentary
```

If PyPI is slow, export your local proxy before syncing:

```bash
HTTPS_PROXY=http://127.0.0.1:1087 uv sync --frozen
```

## Environment

- `DEEPSEEK_API_KEY`
- `MIMO_API_KEY`
- Optional: `DEEPSEEK_BASE_URL`, `MIMO_BASE_URL`

## Development

```bash
uv run pytest
uv run ruff check .
```
