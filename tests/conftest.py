from pathlib import Path

import pytest

from safeloop_visual.config import Settings


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "project.godot").write_text("[application]\nconfig/name=\"Test\"\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    return tmp_path


@pytest.fixture
def settings(workspace: Path) -> Settings:
    return Settings(workspace=workspace)
