# Security model

SafeLoop Visual follows least privilege and explicit opt-in for high-impact capabilities.

## Trust boundaries

There are three separate actors:

1. **MCP host/model (for example Codex)** — decides which SafeLoop tools to call.
2. **SafeLoop Visual** — validates paths/operations and performs bounded project actions.
3. **Target project/runtime** — potentially untrusted code that may execute when a game is launched.

SafeLoop constrains actor 2. It cannot remove capabilities independently provided to actor 1 by the host, and it cannot prove actor 3 harmless.

## Filesystem controls

Every user/model path is interpreted relative to one immutable workspace root established when the server starts.

Rejected:

- absolute paths;
- `..` or symlink escapes after path resolution;
- `.git`, `.safeloop`, `.codex`, `.agents`, `.ssh`, cloud credential directories;
- common secret/key filenames and extensions;
- executable/native binary writes;
- oversized reads/writes.

The security switches come from the MCP process environment/CLI, not a project-editable config file.

## Mutation journal

A checkpoint does not clone the whole game. Instead, on the first SafeLoop mutation of each file after a checkpoint, SafeLoop stores that file's original state in `.safeloop/checkpoints/...`.

This permits rollback of SafeLoop-made file writes, replacements, creations, and opt-in deletions while avoiding huge copies of project asset directories.

It is not a replacement for Git. Use Git as the durable source-control layer.

## No raw shell

SafeLoop exposes no `shell(command)` or equivalent tool. The Godot adapter launches only a Godot executable with arguments built by SafeLoop using `subprocess.run(..., shell=False)`.

The game process receives a reduced environment instead of every environment variable from the MCP server, lowering the risk of project code reading API keys from environment variables.

## Runtime guard

Runtime execution is disabled by default. Before Godot Movie Maker capture, SafeLoop scans project source for common high-risk capabilities such as:

- `OS.execute` / process creation;
- shell opening;
- .NET process launch;
- common HTTP/socket APIs;
- native extensions/binaries;
- dynamic file access (warning).

Critical/network detections block runtime unless the human explicitly opts in through environment switches outside the project.

This scanner is intentionally conservative but **not complete**. Static regex checks cannot prove arbitrary code safe, and a game engine itself is a large native application. For hostile/untrusted repositories, run the entire workflow inside a disposable VM/container or OS sandbox rather than relying on this scanner.

## Host-side Codex permissions

SafeLoop's lack of shell/network tools does not disable Codex's own shell/network capabilities. For the strongest separation, configure Codex permissions so native tools have only the access you intend, and avoid full-access / sandbox-bypass modes for this workflow.

## Threats explicitly out of scope in v0.1

- exploits in Godot itself;
- malicious compiler/importer vulnerabilities;
- complete semantic detection of malicious game scripts;
- hostile native extensions when the user explicitly overrides the block;
- host tools outside SafeLoop;
- physical/device isolation.
