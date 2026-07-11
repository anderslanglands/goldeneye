# Render Command Templates

Default Typhoon/OpenUSD command:

```toml
[render]
renderer = "typhoon"

[renderers.typhoon]
command = [
  "usdrender",
  "--complexity", "high",
  "--renderer", "Embree",
  "{usd_path}",
  "--outputRoot", "{suite_output_root}",
]
```

Local renderer checkout example:

```toml
[render]
renderer = "local-typhoon"

[renderers.local-typhoon]
command = [
  "pixi", "run",
  "--manifest-path", "/home/anders/code/openusd-omniverse/pixi.toml",
  "--clean-env",
  "usdrender",
  "--complexity", "high",
  "--renderer", "Embree",
  "{usd_path}",
  "--outputRoot", "{suite_output_root}",
]
```

With the default `output_pattern = "{path}.exr"`, `{output_relpath}` expands to a suite-relative product such as `nodes/math/case.exr`; `{suite_output_root}` points at the per-suite directory under the numbered run. Use `{frame}` only for frame-expanded tests. Goldeneye reports a config error if a command uses `{frame}` on a non-frame case.
