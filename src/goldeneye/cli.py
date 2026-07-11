from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path


DEFAULT_GOLDENEYE_TOML = """[goldeneye]
output_root = "_output"

[render]
renderer = "typhoon"
output_pattern = "{path}.exr"

[renderers.typhoon]
command = [
  "usdrender",
  "--complexity", "high",
  "--renderer", "Embree",
  "{usd_path}",
  "--outputRoot", "{suite_output_root}",
]
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="goldeneye")
    subparsers = parser.add_subparsers(dest="command", required=True)

    commands: dict[str, Callable[[list[str]], int]] = {
        "init": _init,
        "download-references": _download_references,
        "update-references": _update_references,
        "extract-failures": _extract_failures,
        "view": _view,
        "regenerate-html": _regenerate_html,
        "regenerate-comparisons": _regenerate_comparisons,
        "build-viewer-assets": _build_viewer_assets,
    }
    for name in commands:
        subparsers.add_parser(name, add_help=False)

    args, remainder = parser.parse_known_args(argv)
    return commands[args.command](remainder)


def _init(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="goldeneye init")
    parser.add_argument(
        "path",
        nargs="?",
        default="goldeneye.toml",
        help="Config path to create. Defaults to goldeneye.toml in the current directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing config file.",
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if path.exists() and not args.force:
        parser.exit(1, f"error: {path} already exists; pass --force to overwrite\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_GOLDENEYE_TOML, encoding="utf-8")
    print(f"wrote {path}")
    return 0


def _download_references(argv: list[str]) -> int:
    from .reference_archives import main as reference_main

    return reference_main(["download", *argv])


def _update_references(argv: list[str]) -> int:
    from .reference_archives import main as reference_main

    return reference_main(["update", *argv])


def _extract_failures(argv: list[str]) -> int:
    from .extract_failures import main as extract_main

    return extract_main(argv)


def _view(argv: list[str]) -> int:
    from .view_server import main as view_main

    return view_main(argv)


def _regenerate_html(argv: list[str]) -> int:
    from .report_html import main as report_main

    return report_main(argv)


def _regenerate_comparisons(argv: list[str]) -> int:
    from .regenerate_comparisons import main as regenerate_main

    return regenerate_main(argv)


def _build_viewer_assets(argv: list[str]) -> int:
    if argv:
        parser = argparse.ArgumentParser(prog="goldeneye build-viewer-assets")
        parser.parse_args(argv)
    from .build_exr_wasm import main as build_main

    return build_main()


if __name__ == "__main__":
    raise SystemExit(main())
