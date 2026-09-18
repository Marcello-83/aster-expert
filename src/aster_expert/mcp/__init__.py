"""MCP server exposing existing aster_expert capabilities as tools (lot 8).

A wrapper package: no ranking, chunking, catalogue-extraction, or validation
logic lives here. `aster_expert.mcp.tools` composes existing modules;
`aster_expert.mcp.server` registers them as MCP tools; `aster_expert.mcp.
logging` journals every call; `aster_expert.mcp.models` carries the response
envelopes that make the validation level travel with each answer.
"""
