from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any
import tomllib


SUITE_CONFIG_NAME = "goldeneye-suite.toml"
PROJECT_CONFIG_NAME = "goldeneye.toml"
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
    "{run_dir}",
)


@dataclass(frozen=True)
class ProjectConfig:
    root: Path
    output_root: str = "_output"
    render_command: tuple[str, ...] = DEFAULT_RENDER_COMMAND
    render_output_pattern: str = "{path}.exr"


@dataclass(frozen=True)
class SuiteConfig:
    root: Path
    name: str
    project_root: Path = Path(".")
    render_output_pattern: str = "{path}.exr"
    render_command: tuple[str, ...] = DEFAULT_RENDER_COMMAND
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
    expected_failure: bool = False
    flip_threshold: float | None = None
    render_output: str | None = None
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
    return ProjectConfig(
        root=root,
        output_root=_string(goldeneye.get("output_root"), "_output"),
        render_command=_command_list(
            render.get("command"), DEFAULT_RENDER_COMMAND, config_path
        ),
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
            render_command=project.render_command,
        )

    with config_path.open("rb") as file:
        data = tomllib.load(file)

    root = config_path.parent
    suite = _table(data, "suite")
    render = _table(data, "render")
    reference = _table(data, "reference")
    comparison = _table(data, "comparison")
    _reject_legacy_render_args(render, config_path)

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
        render_command=_command_list(
            render.get("command"), project.render_command, config_path
        ),
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

    return CaseConfig(
        skip=_optional_string(test.get("skip", data.get("skip"))),
        xfail=_optional_string(test.get("xfail", data.get("xfail"))),
        suspect=_bool(test.get("suspect", data.get("suspect")), False),
        expected_failure=_bool(
            _first_present(
                test,
                data,
                "expected-failure",
                "expected_failure",
            ),
            False,
        ),
        flip_threshold=_optional_float(
            comparison.get("flip_threshold", data.get("flip_threshold"))
        ),
        render_output=_optional_string(
            render.get("output", data.get("render_output"))
        ),
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


def _command_list(
    value: Any, default: tuple[str, ...], config_path: Path
) -> tuple[str, ...]:
    if value is None:
        return default
    try:
        command = tuple(_string_list(value))
    except TypeError as exc:
        raise TypeError(f"{config_path}: [render].command must be a list of strings") from exc
    if not command:
        raise ValueError(f"{config_path}: [render].command must not be empty")
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
