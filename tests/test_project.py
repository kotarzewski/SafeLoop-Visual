import pytest

from safeloop_visual.config import Settings
from safeloop_visual.errors import PolicyError
from safeloop_visual.project import ProjectWorkspace


def test_detects_godot(settings):
    project = ProjectWorkspace(settings)
    assert project.detect_engine() == "godot"


def test_write_replace_and_read(settings, workspace):
    project = ProjectWorkspace(settings)
    out = project.write_file("scripts/a.gd", "extends Node\nvar x = 1\n", "test")
    assert out["checkpoint_id"]
    result = project.replace_text("scripts/a.gd", "var x = 1", "var x = 2", 1)
    assert result["replacements"] == 1
    assert "var x = 2" in project.read_file("scripts/a.gd")


def test_refuses_ambiguous_replace(settings, workspace):
    (workspace / "scripts" / "a.gd").write_text("x\nx\n", encoding="utf-8")
    project = ProjectWorkspace(settings)
    with pytest.raises(PolicyError):
        project.replace_text("scripts/a.gd", "x", "y", 1)


def test_delete_disabled_by_default(settings, workspace):
    path = workspace / "scripts" / "a.gd"
    path.write_text("x", encoding="utf-8")
    project = ProjectWorkspace(settings)
    with pytest.raises(PolicyError):
        project.delete_file("scripts/a.gd")


def test_delete_opt_in(workspace):
    path = workspace / "scripts" / "a.gd"
    path.write_text("x", encoding="utf-8")
    project = ProjectWorkspace(Settings(workspace=workspace, allow_delete=True))
    result = project.delete_file("scripts/a.gd")
    assert result["deleted"] is True
    assert not path.exists()
