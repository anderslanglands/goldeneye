# Fixture Patterns

Keep shared scene data in `_assets/` and sublayer it from individual tests. Author fixtures so each test has one predictable render product path relative to the suite, for example `nodes/math/case.exr`.

Add a short `customLayerData.doc` when the expected pixels depend on a subtle MaterialX/USD behavior, packed non-RGB output, or an intentionally unusual renderer state.
