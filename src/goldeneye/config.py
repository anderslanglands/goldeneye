from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
import tomllib


SUITE_CONFIG_NAME = "goldeneye-suite.toml"
PROJECT_CONFIG_NAME = "goldeneye.toml"
USD_FILE_SUFFIXES = frozenset({".usd", ".usda", ".usdc", ".usdz"})
DEFAULT_FLIP_THRESHOLD = 0.04
FrameValue = int | float
DEFAULT_RENDER_COMMAND = (
    "usdrender",
    "--complexity",
    "high",
    "--renderer",
    "Embree",
    "{usd_path}",
    "--outputRoot",
    "{suite_output_root}",
)
DEFAULT_RENDERER_NAME = "typhoon"


def default_renderers() -> dict[str, tuple[str, ...]]:
    return {DEFAULT_RENDERER_NAME: DEFAULT_RENDER_COMMAND}


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    name: str = "Goldeneye"
    output_root: str = "_output"
    icon_path: Path | None = None
    renderer: str = DEFAULT_RENDERER_NAME
    render_command: tuple[str, ...] = DEFAULT_RENDER_COMMAND
    renderers: dict[str, tuple[str, ...]] = field(default_factory=default_renderers)
    render_output_pattern: str = "{path}.exr"


@dataclass(frozen=True)
class SuiteConfig:
    root: Path
    name: str
    project_root: Path = Path(".")
    render_output_pattern: str = "{path}.exr"
    renderer: str = DEFAULT_RENDERER_NAME
    render_command: tuple[str, ...] = DEFAULT_RENDER_COMMAND
    renderers: dict[str, tuple[str, ...]] = field(default_factory=default_renderers)
    artifact_dir: str = "comparison"
    reference_dir: str | None = None
    reference_pattern: str = "{path}.png"
    default_flip_threshold: float | None = DEFAULT_FLIP_THRESHOLD
    missing_references: str = "allow"
    frames: dict[str, str] = field(default_factory=dict)
    skip: dict[str, str] = field(default_factory=dict)
    xfail: dict[str, str] = field(default_factory=dict)
    thresholds: dict[str, float | None] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseConfig:
    skip: str | None = None
    xfail: str | None = None
    suspect: bool = False
    expected_failure: str | None = None
    expected_failure_renderers: dict[str, str] = field(default_factory=dict)
    flip_threshold: float | None = None
    render_output: str | None = None
    renderer: str | None = None
    render_command: tuple[str, ...] | None = None
    reference: str | None = None
    frame_range: str | None = None


def find_suite_config(path: Path) -> Path | None:
    for parent in (path.parent, *path.parents):
        candidate = parent / SUITE_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


def find_project_config(path: Path) -> Path | None:
    for parent in (path, *path.parents):
        candidate = parent / PROJECT_CONFIG_NAME
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=None)
def load_project_config_for_path(path_text: str) -> ProjectConfig:
    path = Path(path_text).resolve()
    config_path = find_project_config(path if path.is_dir() else path.parent)
    if config_path is None:
        root = path if path.is_dir() else path.parent
        return ProjectConfig(root=root)

    with config_path.open("rb") as file:
        data = tomllib.load(file)

    root = config_path.parent
    goldeneye = _table(data, "goldeneye")
    render = _table(data, "render")
    _reject_legacy_render_args(render, config_path)
    renderers = _renderer_map(data, default_renderers(), config_path)
    renderer = _renderer_name(render.get("renderer", render.get("name")), DEFAULT_RENDERER_NAME, config_path)
    render_command = _resolve_configured_render_command(
        render, renderers, renderer, config_path
    )
    return ProjectConfig(
        root=root,
        name=_project_name(goldeneye.get("name"), root),
        output_root=_string(goldeneye.get("output_root"), "_output"),
        icon_path=_optional_project_path(
            goldeneye.get("icon", goldeneye.get("favicon")),
            root,
            config_path,
        ),
        renderer=renderer,
        render_command=render_command,
        renderers=renderers,
        render_output_pattern=_string(render.get("output_pattern"), "{path}.exr"),
    )


@lru_cache(maxsize=None)
def load_suite_config_for_path(path_text: str) -> SuiteConfig:
    path = Path(path_text).resolve()
    config_path = find_suite_config(path)
    project = load_project_config_for_path(str(path))
    if config_path is None:
        return SuiteConfig(
            project_root=project.root,
            root=path.parent,
            name=path.parent.name or "default",
            render_output_pattern=project.render_output_pattern,
            renderer=project.renderer,
            render_command=project.render_command,
            renderers=dict(project.renderers),
        )

    with config_path.open("rb") as file:
        data = tomllib.load(file)

    root = config_path.parent
    suite = _table(data, "suite")
    render = _table(data, "render")
    reference = _table(data, "reference")
    comparison = _table(data, "comparison")
    _reject_legacy_render_args(render, config_path)
    renderers = _renderer_map(data, project.renderers, config_path)
    renderer = _renderer_name(render.get("renderer", render.get("name")), project.renderer, config_path)
    render_command = _resolve_configured_render_command(
        render, renderers, renderer, config_path
    )

    name = _string(suite.get("name"), root.name or "default")
    reference_dir = _optional_string(
        reference.get("dir", suite.get("reference_dir"))
    )
    if reference_dir:
        reference_dir = str(_resolve_path(root, reference_dir))

    return SuiteConfig(
        project_root=project.root,
        root=root,
        name=name,
        render_output_pattern=_string(
            render.get("output_pattern", suite.get("render_output_pattern")),
            project.render_output_pattern,
        ),
        renderer=renderer,
        render_command=render_command,
        renderers=renderers,
        artifact_dir=_string(
            comparison.get("artifact_dir", suite.get("artifact_dir")),
            "comparison",
        ),
        reference_dir=reference_dir,
        reference_pattern=_string(
            reference.get("pattern", suite.get("reference_pattern")),
            "{path}.png",
        ),
        default_flip_threshold=_optional_float(
            comparison.get(
                "default_flip_threshold",
                suite.get("default_flip_threshold", DEFAULT_FLIP_THRESHOLD),
            )
        ),
        missing_references=_string(
            reference.get("missing", suite.get("missing_references")),
            "allow",
        ),
        frames=_frame_map(data.get("frames", {})),
        skip=_string_map(data.get("skip", {})),
        xfail=_string_map(data.get("xfail", {})),
        thresholds=_threshold_map(data.get("thresholds", {})),
    )


def load_case_config(path: Path) -> CaseConfig:
    data: dict[str, Any] = {}
    for candidate in (
        path.with_suffix(".goldeneye.toml"),
        path.with_name(path.name + ".goldeneye.toml"),
    ):
        if candidate.is_file():
            with candidate.open("rb") as file:
                data = tomllib.load(file)
            break

    test = _table(data, "test")
    render = _table(data, "render")
    reference = _table(data, "reference")
    comparison = _table(data, "comparison")
    frames = _table(data, "frames")
    _reject_legacy_render_args(render, path)
    expected_failure, expected_failure_renderers = _expected_failure_config(
        _first_present(
            test,
            data,
            "expected-failure",
            "expected_failure",
        ),
        path,
    )

    return CaseConfig(
        skip=_optional_string(test.get("skip", data.get("skip"))),
        xfail=_optional_string(test.get("xfail", data.get("xfail"))),
        suspect=_bool(test.get("suspect", data.get("suspect")), False),
        expected_failure=expected_failure,
        expected_failure_renderers=expected_failure_renderers,
        flip_threshold=_optional_float(
            comparison.get("flip_threshold", data.get("flip_threshold"))
        ),
        render_output=_optional_string(
            render.get("output", data.get("render_output"))
        ),
        renderer=_optional_renderer_name(render.get("renderer", render.get("name")), path),
        render_command=_optional_command_list(render.get("command"), path),
        reference=_optional_string(reference.get("path", data.get("reference"))),
        frame_range=_optional_string(frames.get("range", test.get("frames"))),
    )


def lookup_case_value(mapping: dict[str, Any], path: Path, suite_root: Path) -> Any:
    rel = path.relative_to(suite_root).as_posix()
    for key in (rel, path.name, path.stem):
        if key in mapping:
            return mapping[key]
    return None


def format_pattern(
    pattern: str,
    path: Path,
    suite: SuiteConfig,
    frame: FrameValue | None = None,
) -> str:
    if frame is None and "{frame" in pattern:
        raise ValueError(
            f"pattern {pattern!r} uses {{frame}} but no frame is configured"
        )
    try:
        try:
            relative_path = path.relative_to(suite.root).with_suffix("").as_posix()
        except ValueError:
            relative_path = path.stem
        return pattern.format(
            stem=path.stem,
            name=path.name,
            path=relative_path,
            suffix=path.suffix,
            suite=suite.name,
            frame=frame,
        )
    except ValueError as exc:
        raise ValueError(f"invalid format pattern {pattern!r}: {exc}") from exc


def parse_frame_spec(spec: str) -> tuple[FrameValue, ...]:
    frames: list[FrameValue] = []
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            continue
        range_part, separator, stride_part = part.partition("x")
        if separator and not stride_part.strip():
            raise ValueError(f"frame range {part!r} has an empty stride")

        if ":" not in range_part:
            if separator:
                raise ValueError(f"single frame {part!r} cannot have a stride")
            frames.append(_parse_frame_value(range_part))
            continue

        start_text, end_text = range_part.split(":", 1)
        start = _parse_frame_value(start_text)
        end = _parse_frame_value(end_text)
        if separator:
            step = _parse_frame_value(stride_part)
            if step == 0:
                raise ValueError(f"frame range {part!r} has a zero stride")
        else:
            step = 1 if end >= start else -1

        if (end - start) * step < 0:
            raise ValueError(f"frame range {part!r} stride does not reach the end")

        current = start
        epsilon = 1e-9
        if step > 0:
            while current <= end + epsilon:
                frames.append(_normalize_frame_value(current))
                current += step
        else:
            while current >= end - epsilon:
                frames.append(_normalize_frame_value(current))
                current += step

    if not frames:
        raise ValueError("frame range is empty")
    return tuple(frames)


def _resolve_path(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def _string(value: Any, default: str) -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise TypeError(f"expected string, got {type(value).__name__}")
    return value


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"expected string, got {type(value).__name__}")
    return value


def _default_project_name(root: Path) -> str:
    return root.name or "Goldeneye"


def _project_name(value: Any, root: Path) -> str:
    name = _string(value, _default_project_name(root)).strip()
    if not name:
        raise ValueError(f"{root / PROJECT_CONFIG_NAME}: [goldeneye].name must not be empty")
    return name


def _optional_project_path(value: Any, root: Path, config_path: Path) -> Path | None:
    text = _optional_string(value)
    if text is None:
        return None
    if not text.strip():
        raise ValueError(f"{config_path}: [goldeneye].icon must not be empty")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"{config_path}: [goldeneye].icon does not exist: {path}")
    return path


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    raise TypeError(f"expected number, got {type(value).__name__}")


def _first_present(primary: dict[str, Any], fallback: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in primary:
            return primary[key]
    for key in keys:
        if key in fallback:
            return fallback[key]
    return None


def _bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise TypeError(f"expected bool, got {type(value).__name__}")


def _expected_failure_config(
    value: Any, config_path: Path
) -> tuple[str | None, dict[str, str]]:
    if value is None:
        return None, {}
    if isinstance(value, str):
        return _expected_failure_reason(value, config_path), {}
    if not isinstance(value, dict):
        raise TypeError(f"expected string or renderer table, got {type(value).__name__}")

    default: str | None = None
    renderers: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(item, str):
            raise TypeError(
                f"expected expected-failure value for renderer {key!r} to be string"
            )
        renderer = str(key).strip()
        if not renderer:
            raise ValueError(f"{config_path}: expected-failure renderer name must not be empty")
        reason = _expected_failure_reason(item, config_path)
        if renderer in {"default", "*"}:
            default = reason
        else:
            renderers[renderer] = reason
    return default, renderers


def _expected_failure_reason(value: str, config_path: Path) -> str:
    if not value.strip():
        raise ValueError(f"{config_path}: expected-failure reason must not be empty")
    return value


def _parse_frame_value(value: str) -> FrameValue:
    text = value.strip()
    if not text:
        raise ValueError("empty frame value")
    return _normalize_frame_value(float(text))


def _normalize_frame_value(value: float) -> FrameValue:
    if float(value).is_integer():
        return int(value)
    return value


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"expected list, got {type(value).__name__}")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"expected string list item, got {type(item).__name__}")
        result.append(item)
    return result


def _optional_command_list(value: Any, config_path: Path) -> tuple[str, ...] | None:
    if value is None:
        return None
    return _command_list(value, (), config_path)


def _optional_renderer_name(value: Any, config_path: Path) -> str | None:
    if value is None:
        return None
    return _renderer_name(value, "", config_path)


def _renderer_name(value: Any, default: str, config_path: Path) -> str:
    renderer = _string(value, default).strip()
    if not renderer:
        raise ValueError(f"{config_path}: renderer name must not be empty")
    return renderer


def _renderer_map(
    data: dict[str, Any],
    inherited: dict[str, tuple[str, ...]],
    config_path: Path,
) -> dict[str, tuple[str, ...]]:
    renderers = dict(inherited)
    table = _table(data, "renderers")
    for name, value in table.items():
        renderer_name = _renderer_name(str(name), "", config_path)
        if not isinstance(value, dict):
            raise TypeError(
                f"{config_path}: [renderers.{renderer_name}] must be a table"
            )
        renderers[renderer_name] = _command_list(
            value.get("command"),
            (),
            config_path,
            label=f"[renderers.{renderer_name}].command",
        )
    return renderers


def _resolve_configured_render_command(
    render: dict[str, Any],
    renderers: dict[str, tuple[str, ...]],
    renderer: str,
    config_path: Path,
) -> tuple[str, ...]:
    if "command" in render:
        command = _command_list(render.get("command"), (), config_path)
        renderers[renderer] = command
        return command
    try:
        return renderers[renderer]
    except KeyError as exc:
        raise ValueError(
            f"{config_path}: [render].renderer {renderer!r} does not match a configured renderer"
        ) from exc


def _command_list(
    value: Any,
    default: tuple[str, ...],
    config_path: Path,
    *,
    label: str = "[render].command",
) -> tuple[str, ...]:
    if value is None:
        return default
    try:
        command = tuple(_string_list(value))
    except TypeError as exc:
        raise TypeError(f"{config_path}: {label} must be a list of strings") from exc
    if not command:
        raise ValueError(f"{config_path}: {label} must not be empty")
    return command


def _reject_legacy_render_args(render: dict[str, Any], config_path: Path) -> None:
    if "args" in render:
        raise ValueError(
            f"{config_path}: [render].args is not supported by Goldeneye; "
            "use [render].command instead"
        )


def _string_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError(f"expected table, got {type(value).__name__}")
    result: dict[str, str] = {}
    for key, item in value.items():
        if item is True:
            result[str(key)] = "marked in suite config"
        elif isinstance(item, str):
            result[str(key)] = item
        else:
            raise TypeError(
                f"expected skip/xfail value for {key!r} to be string or true"
            )
    return result


def _frame_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError(f"expected table, got {type(value).__name__}")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(item, str):
            raise TypeError(f"expected frame range value for {key!r} to be string")
        result[str(key)] = item
    return result


def _threshold_map(value: Any) -> dict[str, float | None]:
    if not isinstance(value, dict):
        raise TypeError(f"expected table, got {type(value).__name__}")
    result: dict[str, float | None] = {}
    for key, item in value.items():
        result[str(key)] = _optional_float(item)
    return result
