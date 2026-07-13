from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from pathlib import Path


DEFAULT_GOLDENEYE_TOML = """[goldeneye]
name = __PROJECT_NAME__
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


DEFAULT_README_MD = """# __PROJECT_NAME__

Goldeneye test suites for __PROJECT_NAME__. The checked-in fixtures and EXR references are managed by Goldeneye.

## Prerequisites

- [Pixi](https://pixi.sh/latest/installation/) must be installed before using the repository's build, test, and viewing commands. Pixi manages the dependencies, build and execution environment.
- [GitHub CLI](https://cli.github.com/), logged in and authenticated for publishing updated reference archives to the repository.

## Quick Start

```bash
git submodule update --init --recursive
pixi run goldeneye download-references # download reference images
pixi run goldeneye build               # build web server
pixi run pytest                        # run test suites
pixi run goldeneye view                # run web server to view results
```

## Running Tests

Running tests using standard [`pytest`](https://docs.pytest.org/en/stable/).

To run all tests:
```bash
pixi run pytest
```

To run a particular section, or particular test fixture:
```bash
pixi run pytest section/subsection
pixi run pytest section/subsection/case.usda
```

To filter test runs by name use the `-k` flag:
```bash
# run all tests with "light" in the name
pixi run pytest -k light
# run all tests with "light" or "material" in the name
pixi run pytest -k 'light or material'
```

## Reference Images

### Getting reference images

Populate all reference directories after cloning or pulling a manifest update:

```bash
pixi run goldeneye download-references
```

Reference images are stored as immutable ZIP archives in GitHub Releases, with one archive per suite subsection. The committed `reference-releases.json` manifest records every archive, file, size, and SHA-256 checksum. Hydrated `reference/` directories are intentionally ignored by Git.

The command downloads only archives whose files are absent or outdated, verifies the archive and every extracted image, and records local hydration state. It refuses to overwrite locally edited references; use `--force` only when those edits should be discarded.

### Updating reference images

After adding or removing tests, adding or removing reference files, or using the report's **Update reference** action, publish the changed subsections:

```bash
pixi run goldeneye update-references
```

This command requires references hydrated from the current manifest. It creates an immutable GitHub release containing only changed subsection archives, updates `reference-releases.json`, and creates a Git commit containing the manifest and associated suite changes. Unrelated files outside suite directories are not included. Use `--dry-run --no-commit` to inspect the detected changes without publishing.

## Adding Renderers

By default, goldeneye is preconfigured with the OpenUSD Typhoon renderer. To add additional renderers, add a `[renderers.<name>]` block to `goldeneye.toml`. For example, to add Arnold:

```toml
[renderers.arnold]
command = [
    "kick", "{usd_path}",
]
```

Configured renderers can then be run by name:
```bash
pixi run pytest test-suite --renderer arnold
```

See the [goldeneye documentation](https://github.com/anderslanglands/goldeneye) for more information including the full set of tokens that can be expanded in the renderer command.
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
    project_name = default_project_name(path)
    config_text = DEFAULT_GOLDENEYE_TOML.replace(
        "__PROJECT_NAME__",
        json.dumps(project_name),
    )
    path.write_text(config_text, encoding="utf-8")
    project_root = path.parent
    update_gitignore(project_root)
    readme_path = write_default_readme(project_root, project_name)
    print(f"wrote {path}")
    if readme_path is not None:
        print(f"wrote {readme_path}")
    return 0


def default_project_name(config_path: Path) -> str:
    parent = config_path.parent
    if str(parent) in {"", "."}:
        parent = Path.cwd()
    return parent.resolve().name or "Goldeneye"


def write_default_readme(project_root: Path, project_name: str) -> Path | None:
    readme = project_root / "README.md"
    if readme.exists():
        return None
    text = DEFAULT_README_MD.replace("__PROJECT_NAME__", project_name)
    readme.write_text(text, encoding="utf-8")
    return readme


def update_gitignore(project_root: Path) -> None:
    gitignore = project_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if any(is_reference_ignore_pattern(line) for line in existing.splitlines()):
        return
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    gitignore.write_text(prefix + "reference/\n", encoding="utf-8")


def is_reference_ignore_pattern(line: str) -> bool:
    value = line.strip()
    if not value or value.startswith(("#", "!")):
        return False
    normalized = value.lstrip("/")
    return normalized in {"reference", "reference/", "reference/**"}


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
