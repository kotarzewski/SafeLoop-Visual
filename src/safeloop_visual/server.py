from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ContentBlock, ImageContent, TextContent

from . import __version__
from .adapters import GodotAdapter
from .config import Settings
from .project import ProjectWorkspace
from .prompts import visual_loop_prompt
from .runtime_guard import RuntimeGuard


SERVER_INSTRUCTIONS = """SafeLoop Visual exposes least-privilege project editing and visual inspection tools.
Use it for iterative visual development: inspect -> checkpoint -> edit -> validate -> render -> visually judge -> fix.
It deliberately exposes no arbitrary shell and no arbitrary network tool.
Do not claim gameplay/physics QA: that is intentionally a separate agent.
Runtime execution is disabled by default and must be opted into by the human outside the project.
"""


def _image_blocks(image_path: Path, metadata: dict, mime_type: str = "image/png") -> list[ContentBlock]:
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return [
        TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False, indent=2)),
        ImageContent(type="image", data=data, mime_type=mime_type),
    ]


def build_server(settings: Settings) -> MCPServer:
    project = ProjectWorkspace(settings)
    godot = GodotAdapter(settings, project)
    guard = RuntimeGuard(settings, project)
    mcp = MCPServer(
        "safeloop-visual",
        title="SafeLoop Visual",
        description="Local least-privilege visual development loop for Codex.",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )

    @mcp.tool()
    def project_info() -> dict:
        """Inspect workspace type, security switches, and active checkpoint."""
        return project.info()

    @mcp.tool()
    def list_project_files(pattern: str = "**/*", limit: int = 250) -> list[str]:
        """List visible project files. Secret/config/agent metadata paths are hidden."""
        return project.list_files(pattern, limit)

    @mcp.tool()
    def read_project_file(path: str, start_line: int = 1, end_line: int = 400) -> str:
        """Read UTF-8 project text within the configured workspace."""
        return project.read_file(path, start_line, end_line)

    @mcp.tool()
    def search_project_text(query: str, pattern: str = "**/*", case_sensitive: bool = False, max_results: int = 50) -> list[dict]:
        """Search text inside visible project source/config files."""
        return project.search_text(query, pattern, case_sensitive, max_results)


    @mcp.tool(structured_output=False)
    def show_project_image(path: str) -> list[ContentBlock]:
        """Return a PNG/JPEG/WebP image from the workspace for visual inspection. Useful for any engine."""
        image = project.policy.resolve_read(path)
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(image.suffix.lower())
        if mime is None:
            raise ValueError("Only PNG, JPEG and WebP project images are supported")
        return _image_blocks(image, {"path": path, "source": "project image"}, mime)

    @mcp.tool()
    def create_checkpoint(label: str = "") -> dict:
        """Start a transactional checkpoint. Future SafeLoop mutations record original file contents."""
        return project.journal.create(label)

    @mcp.tool()
    def write_project_file(path: str, content: str, reason: str = "") -> dict:
        """Create or replace a UTF-8 project file subject to SafeLoop path/size policy."""
        return project.write_file(path, content, reason)

    @mcp.tool()
    def replace_project_text(path: str, old: str, new: str, expected_replacements: int = 1, reason: str = "") -> dict:
        """Perform an exact non-ambiguous text replacement in a project file."""
        return project.replace_text(path, old, new, expected_replacements, reason)

    @mcp.tool()
    def delete_project_file(path: str, reason: str = "") -> dict:
        """Delete one file only when deletion was explicitly enabled outside the project."""
        return project.delete_file(path, reason)

    @mcp.tool()
    def checkpoint_diff(checkpoint_id: str = "") -> str:
        """Show a bounded unified diff of mutations recorded since a checkpoint."""
        cid = checkpoint_id or project.journal.active_id()
        if not cid:
            return "No active checkpoint."
        return project.journal.diff(cid)

    @mcp.tool()
    def restore_checkpoint(checkpoint_id: str) -> dict:
        """Undo SafeLoop-recorded mutations back to a checkpoint."""
        return project.journal.restore(checkpoint_id)

    @mcp.tool()
    def scan_runtime_risks() -> dict:
        """Statically scan Godot scripts/native files before any runtime execution."""
        return guard.decision()

    @mcp.tool()
    def godot_doctor() -> dict:
        """Locate Godot and report its version. Does not run the game."""
        return godot.doctor()

    @mcp.tool()
    def validate_godot_project() -> dict:
        """Start Godot headless editor in recovery mode for a basic project validation; does not intentionally run the main game scene."""
        return godot.validate()

    @mcp.tool(structured_output=False)
    def capture_godot_frame(scene: str = "", frames: int = 30) -> list[ContentBlock]:
        """Run a trusted Godot project briefly and return the newest rendered PNG as an MCP image. Disabled by default."""
        image, metadata = godot.capture_frame(scene=scene, frames=frames)
        return _image_blocks(image, metadata)

    @mcp.tool(structured_output=False)
    def show_last_render() -> list[ContentBlock]:
        """Return the latest PNG created by SafeLoop without running the project again."""
        render_root = settings.workspace / ".safeloop" / "renders"
        images = list(render_root.glob("**/*.png")) if render_root.exists() else []
        if not images:
            return [TextContent(type="text", text="No SafeLoop render exists yet.")]
        image = max(images, key=lambda p: p.stat().st_mtime)
        return _image_blocks(image, {"path": str(image), "source": "last SafeLoop render"})

    @mcp.tool()
    def record_visual_assessment(score: float, summary: str, issues: list[str], iteration: int = 1) -> dict:
        """Persist the host model's visual assessment for auditability. This tool does not generate the score itself."""
        score = max(0.0, min(10.0, float(score)))
        iteration = max(1, min(100, int(iteration)))
        state_dir = settings.workspace / ".safeloop"
        state_dir.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "iteration": iteration,
            "score": score,
            "summary": summary[:1500],
            "issues": [str(x)[:500] for x in issues[:20]],
        }
        with (state_dir / "visual_assessments.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    @mcp.prompt()
    def visual_development_loop(goal: str, reference_description: str = "", target_score: float = 8.5, max_iterations: int = 6) -> str:
        """Prompt for the complete SafeLoop Visual inspect/edit/render/judge loop."""
        return visual_loop_prompt(goal, reference_description, target_score, max_iterations)

    return mcp


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SafeLoop Visual MCP server")
    parser.add_argument("--workspace", help="Project workspace. Overrides SAFELOOP_WORKSPACE.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    settings = Settings.from_env(args.workspace)
    build_server(settings).run(transport="stdio")


if __name__ == "__main__":
    main()
