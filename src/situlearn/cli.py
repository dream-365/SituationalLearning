"""Command-line entry point for situlearn."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from situlearn import __version__
from situlearn.pipeline import build_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="situlearn")
    parser.add_argument("--version", action="version", version=f"situlearn {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build", help="build a study report from an .srt file")
    build.add_argument("input", help="path to a single-language English .srt file")
    build.add_argument("--out", required=True, help="output directory")
    build.add_argument("--no-audio", action="store_true", help="skip TTS generation")
    build.add_argument("--terms-min", type=int, default=30)
    build.add_argument("--terms-max", type=int, default=80)
    build.add_argument("--voice", default="冰糖")
    build.add_argument("--force", action="store_true", help="ignore caches")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "build":
        parser.print_help()
        return 2

    try:
        result = build_report(
            Path(args.input),
            Path(args.out),
            voice=args.voice,
            terms_min=args.terms_min,
            terms_max=args.terms_max,
            no_audio=args.no_audio,
            force=args.force,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports any failure to the user
        print(f"situlearn: {exc}", file=sys.stderr)
        return 1

    print(f"report:   {result.report_path}")
    print(f"manifest: {result.manifest_path}")
    print(
        f"cues={result.cue_count} segments={result.segment_count} "
        f"terms={result.term_count} elapsed={result.elapsed_s:.1f}s"
    )
    if result.warnings:
        print("warnings: " + "; ".join(result.warnings), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
