"""
Helpers for the first / middle / last name split.

The DB and every downstream consumer (PDF reports, notifications, audit
log, JWT display name, the "Hi, {name}" greeting) still work off a single
`full_name` string, so registration/update endpoints collect the three
parts and combine them here into that one stored column instead of
threading first/middle/last through the entire codebase.
"""


def split_name(full_name: str) -> tuple[str, str | None, str]:
    """The reverse of combine_name() - used once, for the seed admin, since
    it's created directly from a single SEED_ADMIN_NAME env var rather than
    already-split fields."""
    tokens = (full_name or "").split()
    if not tokens:
        return "", None, ""
    if len(tokens) == 1:
        return tokens[0], None, tokens[0]
    return tokens[0], (" ".join(tokens[1:-1]) or None), tokens[-1]


def combine_name(first_name: str, middle_name: str | None, last_name: str) -> str:
    """
    Join name parts into a single display name.

    A middle name/initial is inserted as-is (so both "A." and "Alolor"
    are handled the same way - we don't try to guess which one the person
    typed and force a period onto it).
    """
    parts = [first_name.strip()]
    if middle_name and middle_name.strip():
        parts.append(middle_name.strip())
    parts.append(last_name.strip())
    return " ".join(p for p in parts if p)
