import pytest

from safeloop_visual.config import Settings
from safeloop_visual.errors import SafeLoopError


def test_env_defaults_are_restrictive(monkeypatch, workspace):
    monkeypatch.setenv("SAFELOOP_WORKSPACE", str(workspace))
    for key in ["SAFELOOP_ALLOW_DELETE", "SAFELOOP_ALLOW_RUNTIME", "SAFELOOP_ALLOW_NETWORKED_RUNTIME", "SAFELOOP_ALLOW_RISKY_RUNTIME"]:
        monkeypatch.delenv(key, raising=False)
    settings = Settings.from_env()
    assert settings.allow_delete is False
    assert settings.allow_runtime is False
    assert settings.allow_networked_runtime is False
    assert settings.allow_risky_runtime is False


def test_workspace_required(monkeypatch):
    monkeypatch.delenv("SAFELOOP_WORKSPACE", raising=False)
    with pytest.raises(SafeLoopError):
        Settings.from_env()
