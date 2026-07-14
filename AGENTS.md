# Agent Instructions

## Project Overview

Goldeneye is a pytest plugin and CLI for running USD render test suites. It collects `.usd`, `.usda`, `.usdc`, and `.usdz` fixtures below `goldeneye-suite.toml`, renders them with a configured named renderer, compares outputs against references, and writes HTML reports under `_output/run-NNNN`.

## Common Commands

- Initialize a downstream suite config with `pixi run goldeneye init`.
- Run Goldeneye's tests with `pixi run pytest tests -q`.
- Build the conda package with `pixi run build-conda`.
- Rebuild the EXR viewer assets only when changing `tools/exr_wasm/`: `pixi run goldeneye build-viewer-assets`.

## Suite Setup Guidance

For a new suite, document or create this sequence from the project root:

```bash
pixi init --format pixi --channel https://conda.anaconda.org/anderslanglands --channel conda-forge
pixi add python=3.11 goldeneye
pixi run goldeneye init
mkdir -p test-suite/reference
```

If the suite directory is named `test-suite`, plain `pixi run pytest` from the project root discovers it automatically. Pass an explicit suite path for other directory names.

Use named renderers in `goldeneye.toml`. Keep render output patterns suite-relative, and pass `{suite_output_root}` to renderers that resolve USD product names against an output root:

```toml
[render]
renderer = "typhoon"
output_pattern = "{path}.exr"

[renderers.typhoon]
command = ["usdrender", "--complexity", "high", "--renderer", "Embree", "{usd_path}", "--outputRoot", "{suite_output_root}"]
```

## Generated Files

Do not commit generated run output, conda build output, Pixi environments, pytest caches, or generated egg-info metadata. `_output/`, `_conda-channel/`, `.pixi/`, `.pytest_cache/`, and `*.egg-info/` are ignored.

## References

Reference images can be published with `pixi run goldeneye update-references` and restored with `pixi run goldeneye download-references`. Both operations require an authenticated GitHub CLI and a repository remote that can host GitHub Releases.
