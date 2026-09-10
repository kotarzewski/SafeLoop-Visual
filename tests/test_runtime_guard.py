from safeloop_visual.config import Settings
from safeloop_visual.project import ProjectWorkspace
from safeloop_visual.runtime_guard import RuntimeGuard


def test_clean_project_allowed_by_scan(settings, workspace):
    (workspace / "scripts" / "safe.gd").write_text("extends Node\nvar x = 1\n", encoding="utf-8")
    decision = RuntimeGuard(settings, ProjectWorkspace(settings)).decision()
    assert decision["allowed_by_scan"] is True


def test_os_execute_blocks_runtime(settings, workspace):
    (workspace / "scripts" / "bad.gd").write_text('extends Node\nfunc x():\n    OS.execute("cmd", [])\n', encoding="utf-8")
    decision = RuntimeGuard(settings, ProjectWorkspace(settings)).decision()
    assert decision["allowed_by_scan"] is False
    assert decision["counts"]["critical"] == 1


def test_network_blocks_by_default(settings, workspace):
    (workspace / "scripts" / "net.gd").write_text("extends Node\nvar h = HTTPRequest.new()\n", encoding="utf-8")
    decision = RuntimeGuard(settings, ProjectWorkspace(settings)).decision()
    assert decision["allowed_by_scan"] is False
    assert decision["counts"]["network"] >= 1


def test_network_can_be_human_opted_in(workspace):
    (workspace / "scripts" / "net.gd").write_text("extends Node\nvar h = HTTPRequest.new()\n", encoding="utf-8")
    settings = Settings(workspace=workspace, allow_networked_runtime=True)
    decision = RuntimeGuard(settings, ProjectWorkspace(settings)).decision()
    assert decision["allowed_by_scan"] is True


def test_native_extension_blocks(settings, workspace):
    (workspace / "addons").mkdir()
    (workspace / "addons" / "plugin.gdextension").write_text("[configuration]\n", encoding="utf-8")
    decision = RuntimeGuard(settings, ProjectWorkspace(settings)).decision()
    assert decision["allowed_by_scan"] is False
    assert decision["counts"]["critical"] >= 1


def test_literal_res_fileaccess_not_flagged(settings, workspace):
    (workspace / "scripts" / "file.gd").write_text('extends Node\nvar f = FileAccess.open("res://a.txt", FileAccess.READ)\n', encoding="utf-8")
    decision = RuntimeGuard(settings, ProjectWorkspace(settings)).decision()
    assert decision["counts"]["warning"] == 0
