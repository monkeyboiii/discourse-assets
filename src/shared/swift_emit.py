"""Swift source emission helpers."""

from __future__ import annotations


def swift_string_literal(s: str) -> str:
    """Produce a Swift string literal, escaping as needed."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def chunk_pairs(items: list, chunk_size: int = 500) -> list[list]:
    """Split a sorted list into fixed-size chunks.

    Used to keep Swift dictionary literals small enough that the type-checker
    doesn't blow up on huge single-expression maps.
    """
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]
