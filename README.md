# Goldeneye

Goldeneye is a pytest-based runner for USD render test suites. It collects USD fixture files (`.usd`, `.usda`, `.usdc`, and `.usdz`), runs them through a named renderer command, compares rendered images against references, and writes sortable HTML reports with EXR inspection support.

Renderer support is pluggable: a suite can use the default `typhoon` renderer, define additional named renderers in `goldeneye.toml`, or override the render command for a single pytest run.

## Prerequisites

- Pixi to create the suite environment and run Goldeneye.
- GitHub CLI (`gh`) only if you want Goldeneye to publish reference archives to GitHub Releases. It must be authenticated for the target repository.
- A renderer command. The Goldeneye conda package depends on `openusd-typhoon`, so the default `typhoon` renderer can run `usdrender` without extra setup.

## Quick Start

Create the `test-suite` directory and install Goldeneye:

```bash
mkdir test-suite
cd test-suite
pixi init --format pixi --channel https://conda.anaconda.org/anderslanglands --channel conda-forge
pixi add python=3.11 goldeneye
pixi run goldeneye init
```

Initialize the suite config and reference directory:

```bash
mkdir -p reference
cat > goldeneye-suite.toml <<'EOF'
[suite]
name = "test-suite"

[reference]
dir = "reference"
pattern = "{path}.exr"
missing = "fail"

[comparison]
default_flip_threshold = 0.04
EOF
```

Add renderable USD fixtures in `test-suite/`, for example `simple.usda`, and put its reference image at `reference/simple.exr`. Goldeneye accepts `.usd`, `.usda`, `.usdc`, and `.usdz` files.

Run the suite:

```bash
pixi run pytest
```

Use a dry run first when checking command expansion:

```bash
pixi run pytest --goldeneye-dry-run -s
```

## Customizing

A typical suite looks like this:

```text
test-suite/
  pixi.toml
  goldeneye.toml
  goldeneye-suite.toml
  simple.usda
  nested/case.usda
  _assets/shared.usda
  reference/simple.exr
  reference/nested/case.exr
```

A directory becomes a suite when it contains `goldeneye-suite.toml`. Goldeneye collects `.usd`, `.usda`, `.usdc`, and `.usdz` files below that directory. Use directories beginning with `_`, such as `_assets/`, for support layers and resources that should not be collected as tests.

Each fixture must be renderable by the configured renderer and must write an image where Goldeneye expects it. The default project config created by `pixi run goldeneye init` is:

```toml
[goldeneye]
output_root = "_output"

[render]
renderer = "typhoon"
output_pattern = "{suite}/{path}.exr"

[renderers.typhoon]
command = [
  "usdrender",
  "--complexity", "high",
  "--renderer", "Embree",
  "{usd_path}",
  "--outputRoot", "{run_dir}",
]
```

`output_pattern` is Goldeneye's expected render artifact path relative to the run directory. With the config above, `nested/case.usda` in suite `test-suite` is expected at `_output/run-NNNN/test-suite/nested/case.exr`. Make sure the USD render product authored by the fixture, or your renderer command, writes that path.

References are resolved by the suite config:

```toml
[reference]
dir = "reference"
pattern = "{path}.exr"
missing = "fail"
```

For `nested/case.usda`, this expects `reference/nested/case.exr`. Use `--goldeneye-reference-dir /path/to/references` to override references for a run.

Each run gets a new numbered directory under `_output/`:

```text
_output/index.html
_output/run-0001/index.html
_output/run-0001/goldeneye-report.json
_output/run-0001/run-summary.json
_output/run-0001/<rendered images>
_output/run-0001/comparison/<diff artifacts>
```

Goldeneye chooses the next run number by scanning existing `_output/run-NNNN` directories and incrementing the highest number. Use `--goldeneye-output-root=/path/to/output` to put runs somewhere else.

Define your own renderer by adding a named command and selecting it:

```toml
[render]
renderer = "local-typhoon"

[renderers.local-typhoon]
command = [
  "pixi", "run",
  "--manifest-path", "../openusd-omniverse-typhoon-osl/pixi.toml",
  "--clean-env",
  "usdrender",
  "{usd_path}",
  "--outputRoot", "{run_dir}",
]
```

Invoke a configured renderer for a run with `--renderer`:

```bash
pixi run pytest test-suite --renderer local-typhoon
```

`--renderer` selects a command from `[renderers.<name>]`; use `--render-command` only when you want to provide a one-off command directly on the command line.

Useful command template fields:

| Field              | Expands to |
| ------------------ | ---------- |
| `{project_root}`   | Absolute path to the project root Goldeneye resolved for the run. This is normally the directory containing `goldeneye.toml`. |
| `{suite_root}`     | Absolute path to the suite root, the directory containing the relevant `goldeneye-suite.toml`. |
| `{suite}`          | Suite name from `[suite].name`. |
| `{usd_path}`       | Absolute path to the USD fixture file being rendered. |
| `{usd_relpath}`    | Fixture path relative to the suite root, including the file extension, for example `nested/case.usda`. |
| `{run_dir}`        | Absolute path to the current numbered run directory, for example `_output/run-0007` after resolution. |
| `{output_dir}`     | Absolute path to the parent directory of the render output Goldeneye expects for this case. |
| `{output_path}`    | Absolute path to the render output Goldeneye expects for this case. |
| `{output_relpath}` | Expected render output path relative to `{run_dir}`, for example `test-suite/nested/case.exr`. |
| `{path}`           | Fixture path relative to the suite root with its USD file extension removed, for example `nested/case`. |
| `{stem}`           | File stem of the fixture only, for example `case` for `nested/case.usda`. |
| `{name}`           | Goldeneye case name, currently the fixture file stem. |
| `{frame}`          | Frame value for frame-expanded cases. Using this field on a case without configured frames is an error. |

For a one-off run, override the command without editing config:

```bash
pixi run pytest -k carpaint \
  --render-command 'pixi run --manifest-path ../openusd-omniverse-typhoon-osl/pixi.toml --clean-env usdrender {usd_path} --outputRoot {run_dir}'
```

That override still flows through the same render-command templating path and reports as renderer `command-line`.

Mark an intentionally failing case in `<test>.goldeneye.toml`:

```toml
[test]
expected-failure = "known renderer mismatch"
```

Expected failures can also be renderer-specific. Renderer names match the selected Goldeneye renderer, including names passed with `--renderer`:

```toml
[test.expected-failure]
local-typhoon = "known local Typhoon mismatch"
```

When using the table form, `default` or `*` sets the fallback reason for renderers that are not listed explicitly. Expected failures show status `expected-failure`, preserve the reason in `expected_failure`, preserve the original failure in `expected_failure_status`, and are counted separately from strict failures.

## Persisting References

Goldeneye can store large reference images as GitHub Release assets instead of committing them directly. The repo needs a GitHub remote, and `gh` must be authenticated with permission to create releases and upload assets.

Publish changed references:

```bash
pixi run goldeneye update-references --dry-run
pixi run goldeneye update-references
```

`update-references` creates or updates `reference-releases.json` and uploads archive assets to GitHub Releases. It does not commit by default; pass `--commit` only when you want Goldeneye to commit updated reference bookkeeping.

Download references in a fresh checkout:

```bash
pixi run goldeneye download-references
```

Use the local report viewer after a run:

```bash
pixi run goldeneye view
```
