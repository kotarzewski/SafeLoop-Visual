# Codex setup

SafeLoop Visual is designed to run as a local stdio MCP server.

## 1. Install SafeLoop

```bash
python -m venv .venv
pip install -e .
```

Use the virtual environment's Python executable in Codex configuration.

## 2. Configure one workspace

In Codex `config.toml`, add an MCP server entry similar to:

```toml
[mcp_servers.safeloop_visual]
command = "C:\\Tools\\safeloop-visual\\.venv\\Scripts\\python.exe"
args = ["-m", "safeloop_visual.server", "--workspace", "C:\\Projects\\MyGodotGame"]
env = { SAFELOOP_ALLOW_RUNTIME = "0", SAFELOOP_ALLOW_DELETE = "0" }
```

Use absolute paths. Do not put API keys into SafeLoop environment variables; SafeLoop does not need them.

## 3. First-run safety check

Ask Codex to call:

1. `project_info`
2. `scan_runtime_risks`
3. `godot_doctor`
4. `validate_godot_project`

Keep runtime disabled until you have reviewed the project and trust it.

## 4. Enable visual capture for a trusted game

Set:

```toml
SAFELOOP_ALLOW_RUNTIME = "1"
```

Restart the MCP server/Codex session so the immutable startup settings are reloaded.

If your own game legitimately uses networking and the scan blocks it, review every finding before setting:

```toml
SAFELOOP_ALLOW_NETWORKED_RUNTIME = "1"
```

If critical process/native-extension findings exist, do not casually bypass them. For a trusted project where you deliberately need them, `SAFELOOP_ALLOW_RISKY_RUNTIME=1` is the explicit override.

## 5. Codex permissions

SafeLoop only controls its own MCP tools. Codex may still expose its built-in shell/write/network tools depending on your configuration. Prefer a restrictive Codex permission profile and do not use sandbox-bypass/full-access modes merely to run SafeLoop.

## 6. Start a visual loop

Ask Codex to use the SafeLoop MCP prompt `visual_development_loop` with your goal, reference, target score and maximum iterations.

The final answer should state a visual score and explicitly separate visual verification from untested gameplay/physics behavior.
