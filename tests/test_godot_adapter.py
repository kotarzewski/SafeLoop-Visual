from __future__ import annotations

import os
from pathlib import Path

import pytest

from safeloop_visual.adapters.godot import GodotAdapter
from safeloop_visual.config import Settings
from safeloop_visual.errors import RuntimeBlockedError
from safeloop_visual.project import ProjectWorkspace


def make_fake_godot(tmp_path: Path) -> Path:
    fake = tmp_path / "fake-godot"
    fake.write_text(
        """#!/usr/bin/env python3
import os
import pathlib
import sys

if os.environ.get('SAFELOOP_TEST_SECRET'):
    print('secret leaked', file=sys.stderr)
    raise SystemExit(91)

args = sys.argv[1:]
if '--version' in args:
    print('4.6.fake')
    raise SystemExit(0)
if '--write-movie' in args:
    idx = args.index('--write-movie')
    requested = pathlib.Path(args[idx + 1])
    requested.parent.mkdir(parents=True, exist_ok=True)
    out = requested.with_name(requested.stem + '00000029.png')
    out.write_bytes(b'fake-png')
    print('captured')
    raise SystemExit(0)
print('validated')
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    return fake


def test_doctor_sanitizes_environment(workspace, tmp_path, monkeypatch):
    fake = make_fake_godot(tmp_path)
    monkeypatch.setenv("SAFELOOP_TEST_SECRET", "must-not-leak")
    settings = Settings(workspace=workspace, godot_bin=str(fake))
    adapter = GodotAdapter(settings, ProjectWorkspace(settings))
    result = adapter.doctor()
    assert result["found"] is True
    assert result["version"] == "4.6.fake"


def test_validate_uses_fixed_godot_process(workspace, tmp_path):
    fake = make_fake_godot(tmp_path)
    settings = Settings(workspace=workspace, godot_bin=str(fake), allow_engine=True)
    adapter = GodotAdapter(settings, ProjectWorkspace(settings))
    result = adapter.validate()
    assert result["ok"] is True
    assert "recovery-mode" in result["mode"]


def test_runtime_disabled_by_default(workspace, tmp_path):
    fake = make_fake_godot(tmp_path)
    settings = Settings(workspace=workspace, godot_bin=str(fake), allow_runtime=False)
    adapter = GodotAdapter(settings, ProjectWorkspace(settings))
    with pytest.raises(RuntimeBlockedError):
        adapter.capture_frame()


def test_capture_returns_generated_png(workspace, tmp_path):
    fake = make_fake_godot(tmp_path)
    settings = Settings(workspace=workspace, godot_bin=str(fake), allow_runtime=True)
    adapter = GodotAdapter(settings, ProjectWorkspace(settings))
    image, meta = adapter.capture_frame(frames=30)
    assert image.exists()
    assert image.read_bytes() == b"fake-png"
    assert meta["frames_requested"] == 30
    assert meta["returncode"] == 0


def test_capture_refuses_network_code_without_opt_in(workspace, tmp_path):
    fake = make_fake_godot(tmp_path)
    (workspace / "scripts" / "net.gd").write_text("extends Node\nvar h = HTTPRequest.new()\n", encoding="utf-8")
    settings = Settings(workspace=workspace, godot_bin=str(fake), allow_runtime=True)
    adapter = GodotAdapter(settings, ProjectWorkspace(settings))
    with pytest.raises(RuntimeBlockedError):
        adapter.capture_frame()
