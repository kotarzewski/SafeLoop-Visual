from safeloop_visual.project import ProjectWorkspace


def test_restore_existing_file(settings, workspace):
    path = workspace / "scripts" / "a.gd"
    path.write_text("before\n", encoding="utf-8")
    project = ProjectWorkspace(settings)
    cp = project.journal.create("before change")["checkpoint_id"]
    project.write_file("scripts/a.gd", "after\n")
    assert path.read_text(encoding="utf-8") == "after\n"
    restored = project.journal.restore(cp)
    assert "scripts/a.gd" in restored["restored"]
    assert path.read_text(encoding="utf-8") == "before\n"


def test_restore_removes_created_file(settings, workspace):
    project = ProjectWorkspace(settings)
    cp = project.journal.create("before create")["checkpoint_id"]
    project.write_file("scripts/new.gd", "new\n")
    assert (workspace / "scripts" / "new.gd").exists()
    restored = project.journal.restore(cp)
    assert "scripts/new.gd" in restored["removed_created_files"]
    assert not (workspace / "scripts" / "new.gd").exists()


def test_diff_contains_change(settings, workspace):
    path = workspace / "scripts" / "a.gd"
    path.write_text("before\n", encoding="utf-8")
    project = ProjectWorkspace(settings)
    cp = project.journal.create()["checkpoint_id"]
    project.write_file("scripts/a.gd", "after\n")
    diff = project.journal.diff(cp)
    assert "-before" in diff
    assert "+after" in diff


def test_restore_rejects_tampered_sensitive_path(settings, workspace):
    import json
    import pytest
    from safeloop_visual.errors import PolicyError

    project = ProjectWorkspace(settings)
    cp = project.journal.create()["checkpoint_id"]
    manifest_path = workspace / ".safeloop" / "checkpoints" / cp / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["entries"][".git/config"] = {"existed": False, "kind": "file"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(PolicyError):
        project.journal.restore(cp)
