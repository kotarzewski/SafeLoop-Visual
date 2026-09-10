from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import SafeLoopError


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SafeLoopError(f"{name} must be an integer") from exc
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class Settings:
    workspace: Path
    allow_delete: bool = False
    allow_engine: bool = True
    allow_runtime: bool = False
    allow_networked_runtime: bool = False
    allow_risky_runtime: bool = False
    godot_bin: str | None = None
    max_read_bytes: int = 8_000_000
    max_write_bytes: int = 2_000_000
    max_runtime_seconds: int = 25
    max_render_frames: int = 120

    @classmethod
    def from_env(cls, workspace_override: str | None = None) -> "Settings":
        raw_workspace = workspace_override or os.environ.get("SAFELOOP_WORKSPACE")
        if not raw_workspace:
            raise SafeLoopError(
                "Workspace is required. Pass --workspace or set SAFELOOP_WORKSPACE."
            )
        workspace = Path(raw_workspace).expanduser().resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise SafeLoopError(f"Workspace does not exist or is not a directory: {workspace}")
        return cls(
            workspace=workspace,
            allow_delete=_env_bool("SAFELOOP_ALLOW_DELETE", False),
            allow_engine=_env_bool("SAFELOOP_ALLOW_ENGINE", True),
            allow_runtime=_env_bool("SAFELOOP_ALLOW_RUNTIME", False),
            allow_networked_runtime=_env_bool("SAFELOOP_ALLOW_NETWORKED_RUNTIME", False),
            allow_risky_runtime=_env_bool("SAFELOOP_ALLOW_RISKY_RUNTIME", False),
            godot_bin=os.environ.get("SAFELOOP_GODOT_BIN") or None,
            max_read_bytes=_env_int("SAFELOOP_MAX_READ_BYTES", 8_000_000, 1_024, 20_000_000),
            max_write_bytes=_env_int("SAFELOOP_MAX_WRITE_BYTES", 2_000_000, 1_024, 20_000_000),
            max_runtime_seconds=_env_int("SAFELOOP_MAX_RUNTIME_SECONDS", 25, 1, 180),
            max_render_frames=_env_int("SAFELOOP_MAX_RENDER_FRAMES", 120, 1, 600),
        )
