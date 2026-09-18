"""Errors raised while serving an MCP tool call (lot 8).

Subclasses `mcp.server.mcpserver.exceptions.ToolError` deliberately: an
anticipated failure here (unknown profile, missing prerequisite index,
invalid keyword path, missing work root) must reach the calling session as
an `is_error=True` result carrying this exact message, never the generic
"Error executing tool <name>" the SDK substitutes for an unanticipated crash
(CLAUDE.md, "ne jamais neutraliser une alarme sans en expliquer la cause").
A genuinely unexpected failure (a real bug) is deliberately left
unenveloped: the SDK wraps it as `UnexpectedToolError` on its own, which is
exactly the loud failure this project requires (see `aster_expert.mcp.tools`
module docstring).
"""

from __future__ import annotations

from mcp.server.mcpserver.exceptions import ToolError


class McpToolError(ToolError):
    """Raised when this project's MCP layer cannot serve a tool call as requested."""
