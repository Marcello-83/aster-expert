"""AsterExpert: traceable Code_Aster corpus, catalogue and validation tooling.

This package never imports ``code_aster``. Access to the catalogue and to the
solver goes through subprocesses launched with the Aster interpreter, see
``docs/architecture.md`` (ADR-002).
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
