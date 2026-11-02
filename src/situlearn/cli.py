"""Command-line entry point for situlearn."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from situlearn import __version__
from situlearn.pipeline import build_report
from situlearn.progress import Progress
from situlearn.publish import PublishError, publish_report_dir


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

    publish = subparsers.add_parser("publish", help="publish a built report")
    publish.add_argument("report_dir", help="path to a report directory")
    publish.add_argument("--server", required=True, help="base URL of the web service")
    publish.add_argument(
        "--token-env",
        default="SITULEARN_PUBLISH_TOKEN",
        help="environment variable holding the publish token",
    )
    publish.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and package locally without uploading",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "publish":
        token = os.environ.get(args.token_env, "")
        try:
            published = publish_report_dir(
                Path(args.report_dir),
                args.server,
                token,
                dry_run=args.dry_run,
            )
        except PublishError as exc:
            print(f"situlearn: {exc}", file=sys.stderr)
            return exc.exit_code
        except Exception as exc:  # noqa: BLE001 - CLI boundary reports any failure
            print(f"situlearn: {exc}", file=sys.stderr)
            return 1
        if published.dry_run:
            print(
                f"dry-run: report_key={published.report_key} "
                f"title={published.title} size={published.size_bytes}"
            )
        else:
            print(f"published: {published.url}")
            print(
                f"slug={published.slug} version={published.version} "
                f"replaced={published.replaced}"
            )
        return 0

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
            progress=Progress(sys.stderr),
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
