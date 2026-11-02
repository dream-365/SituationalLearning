# 情景学习（SituLearn）

Turn a documentary `.srt` into an offline HTML study report: a Chinese spoken narrative, plus a vocabulary notebook with IPA, bilingual definitions, context sentences, and human pronunciation.

## Status

Working end-to-end on a 60-minute documentary sample: 8 Chinese narrative chapters, 74 terms, 73/74 human pronunciation clips, 82 offline audio files. Full build about 9 minutes; fully cached rebuild under 1 second. The report includes a bottom progress player with current/total time and remaining time.

Spec: `docs/specs/SPEC-001-subtitle-learning-report/spec.md` (Approved)
Plan: `docs/specs/SPEC-001-subtitle-learning-report/plan.md` (Approved)

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Install uv first if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the released CLI:

```bash
uv tool install --python 3.12 https://github.com/dream-365/SituationalLearning/releases/download/v0.1.1/situlearn-0.1.1-py3-none-any.whl
```

If PyPI is slow, set `HTTPS_PROXY` to your local proxy before installing.

## Environment

- `DEEPSEEK_API_KEY`
- `MIMO_API_KEY`
- Optional: `DEEPSEEK_BASE_URL`, `MIMO_BASE_URL`

## Usage

```bash
export DEEPSEEK_API_KEY=...
export MIMO_API_KEY=...
situlearn build your-documentary.en.srt --out reports/your-documentary
open reports/your-documentary/report.html
```

The build writes `report.html`, `manifest.json`, and `assets/audio/` into the output directory. The generated report is fully offline. Progress is printed to stderr as each stage runs; stage and audio caches live in `~/.cache/situlearn/` and are reused on the next build unless `--force` is passed.

## Run from source

```bash
git clone https://github.com/dream-365/SituationalLearning.git
cd SituationalLearning
uv sync --frozen
cp your-documentary.en.srt samples/
uv run situlearn build samples/your-documentary.en.srt --out reports/your-documentary
```

## Development

```bash
uv run pytest
uv run ruff check .
```
