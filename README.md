# SafeLoop Visual

**SafeLoop Visual** is a local, least-privilege MCP agent/gateway for iterative visual development with Codex.
It is intentionally narrow: it helps Codex inspect a project, make bounded edits, validate it, capture an actual render, visually judge that render, and iterate.

It is **not** the gameplay/physics QA agent. A separate SafeLoop QA project should handle behavioral tests, vehicle dynamics, collision correctness, floating objects, map integrity, performance, etc.

## Why this exists

A coding agent can easily stop at "the code compiles" even when the result looks bad. SafeLoop Visual establishes a loop:

`inspect -> checkpoint -> edit -> validate -> render -> visually judge -> prioritize -> fix -> repeat`

For Godot, the rendered frame is returned to Codex as an MCP image, so the host model can actually inspect the result.

## Security model in one minute

SafeLoop deliberately does **not** expose:

- arbitrary shell execution;
- arbitrary URL/network fetching;
- package installation;
- access outside one configured workspace;
- `.env`, credential/key files, `.git`, `.codex`, `.agents`, `AGENTS.md`, `SKILL.md`, or `.safeloop` internals;
- native executable/binary writes;
- deletion unless the human opts in outside the project;
- Godot game execution unless the human opts in outside the project.

All edits made through SafeLoop are journaled so they can be rolled back to a checkpoint.

**Important:** an MCP server cannot neutralize other tools that the MCP host itself exposes. If Codex also has native shell/write/network tools enabled, those remain Codex capabilities. Use Codex permissions/sandboxing appropriately. SafeLoop's guarantee is about **SafeLoop's own tools**, not every tool in the host.

**Also important:** running a game means executing the game's code. SafeLoop performs a defensive static scan and sanitizes environment variables before launching Godot, but this is not a perfect OS sandbox or a security proof. Runtime is disabled by default. Only enable it for projects you trust.

See [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md).

## Requirements

- Python 3.10+
- Codex or another MCP-capable host
- Godot for the Godot visual adapter

The MCP Python SDK 2.x is used.

## Install locally

Clone the repository and create a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -e .
```

Run a local diagnostic:

```bash
safeloop-visual doctor --workspace "C:\\Projects\\MyGodotGame"
```

Run the static runtime scan:

```bash
safeloop-visual scan --workspace "C:\\Projects\\MyGodotGame"
```

## Connect to Codex

Codex supports stdio MCP servers through `mcp_servers` configuration. A minimal example is in [`examples/codex-config.toml`](examples/codex-config.toml).

Example for Windows (edit paths):

```toml
[mcp_servers.safeloop_visual]
command = "C:\\Tools\\safeloop-visual\\.venv\\Scripts\\python.exe"
args = ["-m", "safeloop_visual.server", "--workspace", "C:\\Projects\\MyGodotGame"]
env = {
  SAFELOOP_ALLOW_RUNTIME = "1",
  SAFELOOP_ALLOW_DELETE = "0"
}
```

For the first connection, keep `SAFELOOP_ALLOW_RUNTIME = "0"`, run `scan_runtime_risks`, review the project, then enable runtime if you trust it and want automatic visual captures.

If Godot is not on PATH:

```toml
env = {
  SAFELOOP_GODOT_BIN = "C:\\Program Files\\Godot\\Godot_v4.x-stable_win64.exe",
  SAFELOOP_ALLOW_RUNTIME = "1"
}
```

See [`docs/CODEX_SETUP.md`](docs/CODEX_SETUP.md).

## Use it

In Codex, ask it to use the MCP prompt `visual_development_loop`, or give an equivalent instruction:

> Use SafeLoop Visual for this task. Create a checkpoint, implement the requested visual changes, validate the project, capture and inspect a real rendered frame, score it against my reference, fix the largest visible problems, and repeat until the target score or iteration limit. Do not claim gameplay/physics QA.

Recommended defaults:

- target visual score: `8.5 / 10`
- max iterations: `6`
- change only the top `1-3` visible problems per iteration

## Godot tools

SafeLoop Visual exposes, among others:

- `project_info`
- `list_project_files`
- `read_project_file`
- `search_project_text`
- `show_project_image` (generic PNG/JPEG/WebP inspection for any engine)
- `create_checkpoint`
- `write_project_file`
- `replace_project_text`
- `delete_project_file` (off by default)
- `checkpoint_diff`
- `restore_checkpoint`
- `scan_runtime_risks`
- `godot_doctor`
- `validate_godot_project`
- `capture_godot_frame` (runtime off by default)
- `show_last_render`
- `record_visual_assessment`
- MCP prompt: `visual_development_loop`

The Godot adapter uses documented command-line modes, including headless editor recovery mode for validation and Movie Maker (`--write-movie`) for capture.

## Environment switches

Security-sensitive switches are configured **outside the target project** so project code cannot simply edit a config file to grant itself more power.

| Variable | Default | Meaning |
|---|---:|---|
| `SAFELOOP_WORKSPACE` | required unless `--workspace` | only project root SafeLoop may touch |
| `SAFELOOP_ALLOW_DELETE` | `0` | allow file deletion |
| `SAFELOOP_ALLOW_ENGINE` | `1` | allow guarded Godot validation process |
| `SAFELOOP_ALLOW_RUNTIME` | `0` | allow the game scene to execute for render capture |
| `SAFELOOP_ALLOW_NETWORKED_RUNTIME` | `0` | allow runtime when common network APIs are detected |
| `SAFELOOP_ALLOW_RISKY_RUNTIME` | `0` | override critical static-scan blocks; use only for trusted code |
| `SAFELOOP_GODOT_BIN` | auto | explicit Godot executable path |
| `SAFELOOP_MAX_RUNTIME_SECONDS` | `25` | hard timeout for Godot subprocesses |
| `SAFELOOP_MAX_RENDER_FRAMES` | `120` | cap Movie Maker frames |

## Cost

SafeLoop Visual itself has no paid service and makes no OpenAI API call. When used as an MCP server inside Codex, model work consumes the normal Codex usage available to your plan. It does not add a separate SafeLoop API bill. There are no Fal.ai/Meshy/Tripo integrations in this project.

## Project status

`0.1.0` is an alpha. Godot is the first automatic runtime-capture adapter. The core filesystem/checkpoint/security layer and `show_project_image` inspection are engine-agnostic so Roblox, Unity, Unreal and web adapters can be added later without changing the security core.

## License

MIT.
