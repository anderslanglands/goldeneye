# Goldeneye Test Author

Use this skill when adding or updating Goldeneye USDA render tests, references, thresholds, fixture docs, or suspect metadata.

## Workflow

1. Find the nearest `goldeneye-suite.toml` before editing fixtures.
2. Keep support layers, geometry, textures, and other non-test assets under `_assets/`.
3. Add `.usda` fixtures under the suite section where they should appear in reports.
4. Use deterministic render products and the suite default reference pattern unless the case genuinely needs a custom `[reference].path`.
5. Add `customLayerData.doc` when expected visual behavior is not obvious from the fixture.
6. Use `[comparison].flip_threshold`, `[test].xfail`, `[test].suspect`, and `[test].expected-failure` only when they describe intended suite behavior.
7. Run `pixi run pytest <suite> --collect-only -q` before rendering.
8. Run a focused render or `--goldeneye-dry-run -s` to verify command generation.
9. Use `goldeneye update-references` only when the user intends to publish reference updates.

See `references/suite-config.md` and `references/fixture-patterns.md` for examples.
