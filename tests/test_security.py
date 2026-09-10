import os
from pathlib import Path

import pytest

from safeloop_visual.errors import PolicyError
from safeloop_visual.security import WorkspacePolicy


def test_allows_normal_project_file(settings, workspace):
    path = workspace / "scripts" / "player.gd"
    path.write_text("extends Node\n", encoding="utf-8")
    policy = WorkspacePolicy(settings)
    assert policy.resolve_read("scripts/player.gd") == path.resolve()


@pytest.mark.parametrize("bad", ["../outside.txt", "/etc/passwd", ".env", ".git/config", ".codex/config.toml", ".agents/x", "AGENTS.md", "SKILL.md", "private.pem", "credentials.json"])
def test_blocks_sensitive_and_escape_paths(settings, bad):
    policy = WorkspacePolicy(settings)
    with pytest.raises(PolicyError):
        policy.resolve_write(bad, 10)


def test_blocks_symlink_escape(settings, workspace, tmp_path):
    if os.name == "nt":
        pytest.skip("Symlink creation may require Windows developer/admin mode")
    outside = tmp_path.parent / "outside-safeloop-test"
    outside.mkdir(exist_ok=True)
    link = workspace / "escape"
    link.symlink_to(outside, target_is_directory=True)
    policy = WorkspacePolicy(settings)
    with pytest.raises(PolicyError):
        policy.resolve_write("escape/pwn.txt", 4)


def test_blocks_native_binary_write(settings):
    policy = WorkspacePolicy(settings)
    with pytest.raises(PolicyError):
        policy.resolve_write("addons/evil.dll", 10)


def test_blocks_symlink_even_when_target_stays_inside(settings, workspace):
    if os.name == "nt":
        pytest.skip("Symlink creation may require Windows developer/admin mode")
    target = workspace / "scripts" / "real.gd"
    target.write_text("x", encoding="utf-8")
    link = workspace / "scripts" / "link.gd"
    link.symlink_to(target)
    policy = WorkspacePolicy(settings)
    with pytest.raises(PolicyError):
        policy.resolve_read("scripts/link.gd")
