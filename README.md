# Goldeneye

Goldeneye is a reusable pytest plugin and report viewer for USD render regression suites. It collects `.usda` fixtures under directories containing `goldeneye-suite.toml`, renders them with a configured command, compares outputs against references, and writes sortable HTML reports with EXR viewing support.

## Install In A Suite

Goldeneye is intended to be consumed as a conda package:

```toml
[dependencies]
goldeneye = "*"
```

During local development, a suite can use an editable Python dependency:

```toml
[pypi-dependencies]
goldeneye = { path = "../goldeneye", editable = true }
```

Goldeneye conda packages depend on `openusd-typhoon`, so the default command can run `usdrender` with hdEmbree.

## Minimal Suite

```text
my-suite/
  pixi.toml
  goldeneye.toml
  tests/
    goldeneye-suite.toml
    simple.usda
    reference/
      simple.exr
```

Project defaults live in `goldeneye.toml`:

```toml
[goldeneye]
output_root = "_output"

[render]
command = [
  "usdrender",
  "--complexity", "high",
  "--renderer", "Embree",
  "{usd_path}",
  "--outputRoot", "{run_dir}",
]
output_pattern = "{suite}/{path}.exr"
```

Suite config lives in `goldeneye-suite.toml`. Per-test overrides use `<test>.goldeneye.toml`. Goldeneye does not read Typhoon-era config names and does not support `[render].args`; use a complete list-form `[render].command` override instead.

Useful command template fields include `{project_root}`, `{suite_root}`, `{suite}`, `{usd_path}`, `{usd_relpath}`, `{run_dir}`, `{output_dir}`, `{output_path}`, `{output_relpath}`, `{path}`, `{stem}`, `{name}`, and `{frame}`.

Override the render command for a single pytest run with `--render-command`:

```bash
cd /home/anders/code/aousd-materials-test-suite
pixi run pytest material-fidelity -k carpaint \
  --render-command 'pixi run --manifest-path ../openusd-omniverse-typhoon-osl/pixi.toml --clean-env usdrender {usd_path} --outputRoot {run_dir}'
```

The override takes precedence over project, suite, and per-test `[render].command` values.

Mark an intentionally failing case in its per-test config:

```toml
[test]
expected-failure = true
```

When such a case hits a Goldeneye render/config/reference/compare/threshold failure, the report status is `expected-failure`, the original status is preserved as `expected_failure_status`, and the run summary counts it separately from strict failures.

## Commands

Run tests directly with pytest:

```bash
pixi run pytest tests
pixi run pytest tests -k carpaint
pixi run pytest tests --goldeneye-dry-run -s
```

Use the `goldeneye` CLI for maintenance:

```bash
pixi run goldeneye download-references
pixi run goldeneye extract-failures
pixi run goldeneye view
pixi run goldeneye update-references --dry-run
```

Optional Pixi aliases can be added by downstream suites:

```toml
[tasks]
"goldeneye:download-references" = "goldeneye download-references"
"goldeneye:update-references" = "goldeneye update-references"
"goldeneye:extract-failures" = "goldeneye extract-failures"
"goldeneye:view" = "goldeneye view"
```

## References

Reference archives are described by `reference-releases.json` and published with GitHub CLI releases. Downloading requires network access to GitHub releases. Publishing requires `gh` installed and authenticated with permissions to create releases and upload release assets.

`goldeneye update-references` does not commit by default. Pass `--commit` only when you want Goldeneye to commit updated reference bookkeeping.

## Local Development

```bash
pixi run pytest tests -q
pixi run goldeneye --help
pixi run goldeneye view --help
pixi run build-conda
```

The prebuilt EXR viewer JS/WASM files under `src/goldeneye/static/` are included in editable installs and conda packages. Rebuild them only when changing `tools/exr_wasm/`:

```bash
pixi run goldeneye build-viewer-assets
```
