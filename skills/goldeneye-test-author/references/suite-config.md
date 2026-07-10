# Suite Config

A suite is collected from `.usda` files below a directory containing `goldeneye-suite.toml`.

```toml
[suite]
name = "my-suite"

[render]
output_pattern = "my-suite/{path}.exr"

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
expected-failure = true
suspect = true

[comparison]
flip_threshold = 0.025
```

Use `expected-failure = true` only for intentionally failing cases. Goldeneye reports these rows with status `expected-failure`, preserves the underlying failure status as `expected_failure_status`, and counts them separately from strict failures.
