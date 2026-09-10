from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from ..config import Settings
from ..errors import AdapterError, RuntimeBlockedError
from ..project import ProjectWorkspace
from ..runtime_guard import RuntimeGuard
from .base import EngineAdapter


class GodotAdapter(EngineAdapter):
    def __init__(self, settings: Settings, project: ProjectWorkspace):
        self.settings = settings
        self.project = project
        self.guard = RuntimeGuard(settings, project)

    def _binary(self) -> str:
        candidates = []
        if self.settings.godot_bin:
            candidates.append(self.settings.godot_bin)
        candidates.extend(["godot", "godot4", "godot-mono"])
        for candidate in candidates:
            expanded = str(Path(candidate).expanduser()) if any(sep in candidate for sep in ("/", "\\")) else candidate
            found = expanded if Path(expanded).is_file() else shutil.which(expanded)
            if found:
                return str(Path(found).resolve())
        raise AdapterError("Godot executable not found. Set SAFELOOP_GODOT_BIN to the Godot executable path.")

    @staticmethod
    def _safe_env() -> dict[str, str]:
        # Deliberately do not pass arbitrary environment variables/API keys to game code.
        allow = {
            "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR",
            "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL",
            "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR", "XDG_DATA_HOME", "XDG_CONFIG_HOME",
        }
        return {k: v for k, v in os.environ.items() if k in allow}

    def _run(self, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        binary = self._binary()
        try:
            return subprocess.run(
                [binary, *args],
                cwd=self.settings.workspace,
                env=self._safe_env(),
                capture_output=True,
                text=True,
                timeout=timeout or self.settings.max_runtime_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise AdapterError(f"Godot timed out after {timeout or self.settings.max_runtime_seconds}s") from exc

    @staticmethod
    def _trim(text: str, limit: int = 12_000) -> str:
        return text if len(text) <= limit else text[-limit:] + "\n... output truncated ..."

    def doctor(self) -> dict:
        binary = self._binary()
        result = self._run(["--version"], timeout=10)
        return {
            "found": result.returncode == 0,
            "binary": binary,
            "version": self._trim((result.stdout or result.stderr).strip(), 1000),
            "returncode": result.returncode,
        }

    def validate(self) -> dict:
        if not self.settings.allow_engine:
            raise RuntimeBlockedError("Engine execution is disabled by SAFELOOP_ALLOW_ENGINE=0")
        if not (self.settings.workspace / "project.godot").exists():
            raise AdapterError("This workspace is not a Godot project (project.godot missing)")
        # Recovery mode disables tool scripts, editor plugins, GDExtension and other crash-prone startup features.
        result = self._run([
            "--headless", "--editor", "--recovery-mode", "--path", str(self.settings.workspace),
            "--quit-after", "1", "--no-header",
        ])
        output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        return {
            "ok": result.returncode == 0 and "ERROR:" not in output,
            "returncode": result.returncode,
            "output": self._trim(output),
            "mode": "headless editor recovery-mode; game scene not intentionally executed",
        }

    def capture_frame(self, scene: str = "", frames: int = 30) -> tuple[Path, dict]:
        if not self.settings.allow_runtime:
            raise RuntimeBlockedError(
                "Runtime capture is disabled by default. Set SAFELOOP_ALLOW_RUNTIME=1 in the MCP host configuration "
                "only for a project you trust."
            )
        if not (self.settings.workspace / "project.godot").exists():
            raise AdapterError("This workspace is not a Godot project (project.godot missing)")
        decision = self.guard.decision()
        if not decision["allowed_by_scan"]:
            raise RuntimeBlockedError(
                "Runtime guard blocked execution: " + "; ".join(decision["blocked_reasons"]) +
                ". Review scan_runtime_risks. Overrides must be configured outside the project."
            )
        frames = max(1, min(self.settings.max_render_frames, frames))
        render_dir = self.settings.workspace / ".safeloop" / "renders" / uuid.uuid4().hex[:12]
        render_dir.mkdir(parents=True, exist_ok=True)
        output = render_dir / "capture.png"
        args = [
            "--path", str(self.settings.workspace),
            "--write-movie", str(output),
            "--fixed-fps", "30",
            "--quit-after", str(frames),
            "--no-header",
        ]
        if scene:
            # Validate that the requested scene is inside the project; pass as res:// path, never shell text.
            scene_path = self.project.policy.resolve_read(scene)
            args += ["--scene", "res://" + scene_path.relative_to(self.settings.workspace).as_posix()]
        result = self._run(args)
        pngs = sorted(render_dir.glob("*.png"), key=lambda p: p.stat().st_mtime)
        if not pngs:
            logs = self._trim((result.stdout or "") + "\n" + (result.stderr or ""))
            raise AdapterError(f"Godot produced no PNG frames. Return code={result.returncode}. Output:\n{logs}")
        image = pngs[-1]
        meta = {
            "path": str(image),
            "frames_requested": frames,
            "frames_written": len(pngs),
            "returncode": result.returncode,
            "output": self._trim((result.stdout or "") + "\n" + (result.stderr or ""), 6000),
            "guard": {"counts": decision["counts"], "important": decision["important"]},
        }
        return image, meta
