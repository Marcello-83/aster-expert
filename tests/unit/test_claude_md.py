"""CLAUDE.md ne porte que les règles en vigueur (lot 48 bis, audit R10 a)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
HISTORIQUE = ROOT / "docs" / "historique" / "claude_md_avant_lot48bis.md"

# Une ancre par règle ou famille de règles qui ne doit jamais disparaître.
ANCRES = (
    "TOUTE PRODUCTION DE CE DÉPÔT EST EN FRANÇAIS",
    "jamais dans `src/`",
    "Ne jamais dépendre du Python du système",
    "Un lot, une branche",
    "--no-verify",
    "Consultation obligatoire",
    "Un précédent n'est jamais appliqué",
    "choix de l'agent",
    "Ne jamais mélanger silencieusement plusieurs versions",
    "Ne jamais annoncer un niveau supérieur",
    "Aucun accès réseau dans les tests unitaires",
    "Le critère est écrit dans le rapport **avant** l'exécution",
    "un commit Git distinct",
    "Une session par lot",
    "une seule partition",
    "aucune coordonnée en dur",
    "Arguments nommés",
    "Discrétisation explicite",
    "jamais de mémoire",
    "Une session traite un lot et un seul",
    "ASTER_EXPERT_TERMES_INTERDITS",
    "pre-push",
    "`replay_mode`",
    "`blocker_scopes`",
    "`fiche enregistrer",
    "partiel",
)


def test_claude_md_is_under_400_lines() -> None:
    assert CLAUDE.count("\n") < 400


def test_every_rule_anchor_is_still_there() -> None:
    missing = [a for a in ANCRES if a not in CLAUDE]
    assert missing == []


def test_the_history_is_kept_verbatim_elsewhere() -> None:
    text = HISTORIQUE.read_text(encoding="utf-8")
    assert (
        "**Lot 46** (`docs/essais_lot46.md`" in text and len(text.splitlines()) > 1100
    )
