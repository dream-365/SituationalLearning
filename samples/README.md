# Samples

Put local `.srt` files here. Subtitle files are gitignored and must not be committed.

Expected input: a single-language English `.srt` file, UTF-8 (with or without BOM).

Example:

```bash
cp ~/Downloads/your-documentary.en.srt samples/
uv run situlearn build samples/your-documentary.en.srt --out reports/your-documentary
```
