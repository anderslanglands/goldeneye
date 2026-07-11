# Agent Instructions

## Project Overview

Goldeneye is a pytest plugin and CLI for running USD render test suites. It collects `.usd`, `.usda`, `.usdc`, and `.usdz` fixtures below `goldeneye-suite.toml`, renders them with a configured named renderer, compares outputs against references, and writes HTML reports under `_output/run-NNNN`.

## Common Commands

- Initialize a downstream suite config with `pixi run goldeneye init`.
- Run Goldeneye's tests with `pixi run pytest tests -q`.
- Build the conda package with `pixi run build-conda`.
- Rebuild the EXR viewer assets only when changing `tools/exr_wasm/`: `pixi run goldeneye build-viewer-assets`.

## Suite Setup Guidance

For a new suite, document or create this sequence:

```bash
pixi init --format pixi --channel https://conda.anaconda.org/anderslanglands --channel conda-forge
pixi add python=3.11 goldeneye
pixi run goldeneye init
```

Use named renderers in `goldeneye.toml`:

```toml
[render]
renderer = "typhoon"
output_pattern = "{suite}/{path}.exr"

[renderers.typhoon]
command = ["usdrender", "--complexity", "high", "--renderer", "Embree", "{usd_path}", "--outputRoot", "{run_dir}"]
```

## Generated Files

Do not commit generated run output, conda build output, Pixi environments, pytest caches, or generated egg-info metadata. `_output/`, `_conda-channel/`, `.pixi/`, `.pytest_cache/`, and `*.egg-info/` are ignored.

## References

Reference images can be published with `pixi run goldeneye update-references` and restored with `pixi run goldeneye download-references`. Publishing requires an authenticated GitHub CLI and a repository remote that can host GitHub Releases.
