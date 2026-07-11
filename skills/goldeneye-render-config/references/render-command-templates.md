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
  "--outputRoot", "{run_dir}",
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
  "--outputRoot", "{run_dir}",
]
```

Use `{frame}` only for frame-expanded tests. Goldeneye reports a config error if a command uses `{frame}` on a non-frame case.
