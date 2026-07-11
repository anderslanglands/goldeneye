# Suite Config

A suite is collected from `.usd`, `.usda`, `.usdc`, and `.usdz` files below a directory containing `goldeneye-suite.toml`. Render product paths should be relative to the suite output root, so `surfaces/case.usda` normally writes `surfaces/case.exr`, not `my-suite/surfaces/case.exr`; Goldeneye places that under `_output/run-NNNN/<suite>/`.

```toml
[suite]
name = "my-suite"

[render]
output_pattern = "{path}.exr"

[reference]
dir = "reference"
pattern = "{path}.exr"
missing = "fail"

[comparison]
default_flip_threshold = 0.015
```

Per-test config lives next to a fixture as `<test>.goldeneye.toml`.

```toml
[test]
expected-failure = "known renderer mismatch"
suspect = true

[comparison]
flip_threshold = 0.025
```

Use `expected-failure = "reason"` only for intentionally failing cases. Goldeneye reports these rows with status `expected-failure`, preserves the reason in `expected_failure`, preserves the underlying failure status as `expected_failure_status`, and counts them separately from strict failures.
