"""Readable refusal of a project declaration (lot 41, étape 3)."""

from __future__ import annotations


class ProjectError(ValueError):
    """An incomplete or inconsistent project declaration, or a project step that
    cannot run. Its message is meant for the engineer, never a raw traceback:
    every command catches it and prints it as `<commande> ÉCHEC : <message>`."""

    def __init__(self, message: str, problems: tuple[str, ...] = ()) -> None:
        self.problems = problems
        if problems:
            message = message + "\n" + "\n".join(f"- {p}" for p in problems)
        super().__init__(message)


__all__ = ["ProjectError"]
