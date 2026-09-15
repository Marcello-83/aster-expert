"""Errors raised while parsing a `.comm` file."""

from __future__ import annotations


class CommParseError(Exception):
    """Raised when a `.comm` file cannot be parsed as Python source at all.

    Anything the parser can make sense of past that point — an unhandled
    construct, an argument that cannot be statically resolved — is reported
    explicitly (`parse_warnings`, `dynamic`, `unresolved`), never by raising.
    This error is reserved for a genuine `SyntaxError` from `ast.parse`, or
    for the file being unreadable.
    """
