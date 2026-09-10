from __future__ import annotations

import argparse
import json

from .adapters import GodotAdapter
from .config import Settings
from .project import ProjectWorkspace
from .runtime_guard import RuntimeGuard
from .server import build_server


def _settings(workspace: str) -> Settings:
    return Settings.from_env(workspace)


def main() -> None:
    parser = argparse.ArgumentParser(prog="safeloop-visual")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Run stdio MCP server")
    serve.add_argument("--workspace", required=True)

    doctor = sub.add_parser("doctor", help="Inspect project and Godot availability")
    doctor.add_argument("--workspace", required=True)

    scan = sub.add_parser("scan", help="Run defensive runtime risk scan")
    scan.add_argument("--workspace", required=True)

    args = parser.parse_args()
    settings = _settings(args.workspace)
    project = ProjectWorkspace(settings)

    if args.command == "serve":
        build_server(settings).run(transport="stdio")
        return
    if args.command == "doctor":
        output = {"project": project.info()}
        if project.detect_engine() == "godot":
            try:
                output["godot"] = GodotAdapter(settings, project).doctor()
            except Exception as exc:
                output["godot"] = {"found": False, "error": str(exc)}
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return
    if args.command == "scan":
        print(json.dumps(RuntimeGuard(settings, project).decision(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
