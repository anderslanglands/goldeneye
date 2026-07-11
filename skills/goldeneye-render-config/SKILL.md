# Goldeneye Render Config

Use this skill when customizing renderer commands, running against a local renderer checkout, adding per-test render overrides, or debugging command templating.

## Workflow

1. Prefer named `[renderers.<name>]` entries for reusable commands; select one with `[render].renderer`.
2. Use list-form commands; do not use shell strings unless the user explicitly needs shell behavior.
3. Put broad defaults in `goldeneye.toml` or `goldeneye-suite.toml`.
4. Put exceptional behavior in `<test>.goldeneye.toml`.
5. Use template fields such as `{usd_path}`, `{output_path}`, `{run_dir}`, and `{frame}`.
6. Verify with `pixi run pytest <suite> --collect-only -q`.
7. Verify command expansion with `pixi run pytest <suite> --goldeneye-dry-run -s`.

See `references/render-command-templates.md` for examples.
