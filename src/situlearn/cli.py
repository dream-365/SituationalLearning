"""Command-line entry point for situlearn."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from situlearn import __version__
from situlearn.knowledge import ContentType
from situlearn.migrate import MigrateError, migrate_batch, migrate_report
from situlearn.packager import PackageError, package_directory
from situlearn.pipeline import build_report
from situlearn.progress import Progress
from situlearn.publish import PublishError, publish_report_dir
from situlearn.render import RenderError, render_document
from situlearn.web.export_bundles import export_from_settings, settings_with_data_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="situlearn")
    parser.add_argument("--version", action="version", version=f"situlearn {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build", help="build a SituLearn document from an .srt file")
    build.add_argument("input", help="path to a single-language English .srt file")
    build.add_argument("--out", required=True, help="output directory")
    build.add_argument("--no-audio", action="store_true", help="skip TTS generation")
    build.add_argument(
        "--content-type",
        choices=[content_type.value for content_type in ContentType],
        default=ContentType.DOCUMENTARY.value,
        help="content type: documentary (default) or movie",
    )
    build.add_argument("--terms-min", type=int, default=None)
    build.add_argument("--terms-max", type=int, default=None)
    build.add_argument("--voice", default="冰糖")
    build.add_argument("--no-render", action="store_true", help="skip the derived index.html")
    build.add_argument("--package", action="store_true", help="also write a .situ package")
    build.add_argument("--force", action="store_true", help="ignore caches")

    publish = subparsers.add_parser("publish", help="publish a document directory or .situ")
    publish.add_argument("source", help="document directory or .situ file")
    publish.add_argument("--server", required=True, help="base URL of the web service")
    publish.add_argument("--slug", default=None, help="requested public slug")
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

    package = subparsers.add_parser("package", help="package a document directory into a .situ file")
    package.add_argument("report_dir", help="path to a document directory")
    package.add_argument("--out", required=True, help="output .situ path")
    package.add_argument("--force", action="store_true", help="overwrite an existing output")

    migrate = subparsers.add_parser(
        "migrate", help="migrate an old manifest report into a document directory"
    )
    migrate.add_argument("old_dir", help="path to an old report directory with manifest.json")
    migrate.add_argument("--out", required=True, help="output document directory")
    migrate.add_argument("--source-language", default="en")
    migrate.add_argument("--force", action="store_true")

    migrate_batch_parser = subparsers.add_parser(
        "migrate-batch", help="migrate a directory of exported old bundles"
    )
    migrate_batch_parser.add_argument("export_root", help="root of exported bundles")
    migrate_batch_parser.add_argument("--out", required=True, help="output root")
    migrate_batch_parser.add_argument("--source-language", default="en")
    migrate_batch_parser.add_argument("--force", action="store_true")

    render = subparsers.add_parser(
        "render", help="render a document directory or .situ into an HTML directory"
    )
    render.add_argument("source", help="document directory or .situ file")
    render.add_argument("--out", required=True, help="output directory (must be empty or new)")

    export_bundles = subparsers.add_parser(
        "export-bundles", help="export legacy manifest bundles for migration"
    )
    export_bundles.add_argument("--data-dir", required=True, help="web service data directory")
    export_bundles.add_argument("--out", required=True, help="export root")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "publish":
        token = os.environ.get(args.token_env, "")
        try:
            published = publish_report_dir(
                Path(args.source),
                args.server,
                token,
                slug=args.slug,
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
                f"title={published.title} size={published.size_bytes} "
                f"slug={published.slug or '-'}"
            )
        else:
            print(f"published: {published.url}")
            print(
                f"slug={published.slug} version={published.version} "
                f"replaced={published.replaced}"
            )
        return 0

    if args.command == "export-bundles":
        try:
            exported, skipped = export_from_settings(
                settings_with_data_dir(Path(args.data_dir)),
                Path(args.out),
            )
        except Exception as exc:  # noqa: BLE001 - CLI boundary
            print(f"situlearn: {exc}", file=sys.stderr)
            return 1
        print(f"exported={exported} skipped={skipped} out={args.out}")
        return 0

    if args.command == "render":
        try:
            render_info = render_document(Path(args.source), Path(args.out))
        except RenderError as exc:
            print(f"situlearn: {exc}", file=sys.stderr)
            return 1
        for warning in render_info.warnings:
            print(f"situlearn: warning: {warning}", file=sys.stderr)
        print(
            f"rendered: {render_info.html_path} sections={render_info.sections} "
            f"blocks={render_info.blocks} missing={len(render_info.missing)}"
        )
        return 0

    if args.command == "package":
        try:
            package_info = package_directory(
                Path(args.report_dir),
                Path(args.out),
                force=args.force,
            )
        except PackageError as exc:
            print(f"situlearn: {exc}", file=sys.stderr)
            return 1
        for warning in package_info.warnings:
            print(f"situlearn: warning: {warning}", file=sys.stderr)
        print(f"packaged: {package_info.path}")
        print(f"entries={len(package_info.entries)} media_bytes={package_info.media_bytes}")
        return 0

    if args.command == "migrate":
        try:
            migrate_info = migrate_report(
                Path(args.old_dir),
                Path(args.out),
                source_language=args.source_language,
                force=args.force,
            )
        except MigrateError as exc:
            print(f"situlearn: {exc}", file=sys.stderr)
            return 1
        for warning in migrate_info.warnings:
            print(f"situlearn: warning: {warning}", file=sys.stderr)
        print(
            f"migrated: {migrate_info.out_dir} sections={migrate_info.sections} "
            f"words={migrate_info.words} resources={migrate_info.resources}"
        )
        return 0

    if args.command == "migrate-batch":
        results = migrate_batch(
            Path(args.export_root),
            Path(args.out),
            source_language=args.source_language,
            force=args.force,
        )
        failures = 0
        for batch_result in results:
            if batch_result.error:
                failures += 1
                print(f"situlearn: {batch_result.report_key}: {batch_result.error}", file=sys.stderr)
            elif batch_result.info is not None:
                print(
                    f"migrated: {batch_result.report_key} sections={batch_result.info.sections} "
                    f"words={batch_result.info.words} resources={batch_result.info.resources}"
                )
        return 1 if failures else 0

    if args.command != "build":
        parser.print_help()
        return 2

    try:
        build_result = build_report(
            Path(args.input),
            Path(args.out),
            voice=args.voice,
            content_type=args.content_type,
            terms_min=args.terms_min,
            terms_max=args.terms_max,
            no_audio=args.no_audio,
            render=not args.no_render,
            package=args.package,
            force=args.force,
            progress=Progress(sys.stderr),
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports any failure to the user
        print(f"situlearn: {exc}", file=sys.stderr)
        return 1

    print(f"document: {build_result.document_path}")
    if build_result.html_path is not None:
        print(f"html:     {build_result.html_path}")
    if build_result.package_path is not None:
        print(f"package:  {build_result.package_path}")
    print(
        f"cues={build_result.cue_count} segments={build_result.segment_count} "
        f"terms={build_result.term_count} elapsed={build_result.elapsed_s:.1f}s"
    )
    if build_result.warnings:
        print("warnings: " + "; ".join(build_result.warnings), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
