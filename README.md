# 情景学习（SituLearn）

Turn a documentary `.srt` into an offline HTML study report: a Chinese spoken narrative, plus a vocabulary notebook with IPA, bilingual definitions, context sentences, and human pronunciation.

## Status

Working end-to-end on a 60-minute documentary sample: 8 Chinese narrative chapters, 74 terms, 73/74 human pronunciation clips, 82 offline audio files. Full build about 9 minutes; fully cached rebuild under 1 second. The report includes a bottom progress player with current/total time and remaining time.

The new web layer publishes a built report to a public, unguessable URL so it can be opened and listened to on an iPad. It adds server-side rendering, background playback with Media Session, per-device progress memory, and a PWA home-screen entry.

Specs:

- `docs/specs/SPEC-001-subtitle-learning-report/spec.md` (Approved)
- `docs/specs/SPEC-002-report-web-publishing/spec.md` (Approved)
- `docs/specs/SPEC-002-report-web-publishing/tasks.md` (In Progress)

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). Install uv first if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the released CLI:

```bash
uv tool install --python 3.12 https://github.com/dream-365/SituationalLearning/releases/download/v0.1.3/situlearn-0.1.3-py3-none-any.whl
```

If PyPI is slow, set `HTTPS_PROXY` to your local proxy before installing.

The published wheel currently tracks v0.1.3. The web publishing layer and the `publish` subcommand are available from source and will ship in the v0.2.0 release.

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

## Publish to the web

The step-by-step publishing checklist (local LAN HTTPS, public K3s, verification, and rollback) is in [`docs/runbooks/publish-report.md`](docs/runbooks/publish-report.md).

The web service serves public, unguessable report URLs. Build stays local; only the finished report is uploaded.

```bash
export SITULEARN_PUBLISH_TOKEN=...
situlearn publish reports/your-documentary --server https://learn.example.com
```

The command prints the `slug` and public URL. Publishing the same subtitle again replaces the same URL:

```bash
situlearn publish reports/your-documentary --server https://learn.example.com
```

Use `--dry-run` to validate and package without uploading:

```bash
situlearn publish reports/your-documentary --server https://learn.example.com --dry-run
```

Run the service locally for development:

```bash
export PUBLISH_TOKEN=dev-token
export SITE_BASE_URL=http://localhost:8000
export SITULEARN_DATA_DIR=~/.cache/situlearn/web-dev
uv run uvicorn situlearn.web.app:app --host 0.0.0.0 --port 8000
```

Then publish from another terminal:

```bash
SITULEARN_PUBLISH_TOKEN=dev-token \
  uv run situlearn publish reports/your-documentary --server http://localhost:8000
```

## K3s deployment

The deployment resources live in `deploy/k8s`. Build and push an image first, then update the image tag in `deploy/k8s/overlays/prod/kustomization.yaml`.

```bash
docker build -t ghcr.io/dream-365/situlearn-web:0.2.2 .
docker push ghcr.io/dream-365/situlearn-web:0.2.2

kubectl create namespace situlearn --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic situlearn-secrets -n situlearn \
  --from-literal=PUBLISH_TOKEN="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl diff -k deploy/k8s/overlays/prod
kubectl apply -k deploy/k8s/overlays/prod
kubectl rollout status deployment/situlearn -n situlearn --timeout=10m
```

The overlay uses a placeholder host (`situlearn.example.com`). Replace it and the TLS secret with your domain and certificate before applying. The data and backup PVCs are 20 GiB each; adjust them in `deploy/k8s/base/pvc-*.yaml` if needed.

Health checks:

```bash
curl -fsS https://learn.example.com/healthz
curl -fsS https://learn.example.com/readyz
curl -fsS https://learn.example.com/metrics | head
```

## iPad

1. Open the published URL in Safari.
2. Tap the share button and choose “添加到主屏幕” to install the report as a PWA.
3. Play a chapter, then lock the iPad; audio should continue and the lock-screen controls should work.
4. Reopen the report to resume from the last chapter and position.
5. Already opened pages and played audio are cached for weak or offline networks.

The full real-device checklist is in `docs/runbooks/ipad-smoke.md`.

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
uv run mypy src/situlearn/web src/situlearn/publish.py src/situlearn/cli.py
```

Web-specific tests:

```bash
uv run pytest tests/test_web_*.py tests/test_publish.py tests/test_deploy_manifests.py -q
```
