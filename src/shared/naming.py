"""Swift case-name helpers shared by emoji and icon generators."""

from __future__ import annotations

import re


SWIFT_KEYWORDS = {
    "associatedtype", "class", "deinit", "enum", "extension", "func",
    "import", "init", "inout", "let", "operator", "precedencegroup",
    "protocol", "struct", "subscript", "typealias", "var",
    "break", "case", "continue", "default", "defer", "do", "else",
    "fallthrough", "for", "guard", "if", "in", "repeat", "return",
    "switch", "where", "while",
    "as", "catch", "false", "is", "nil", "rethrows", "self", "super",
    "throw", "throws", "true", "try",
}

# Keywords that can't be used as enum case names even with backticks.
# These get a suffix appended instead.
CONFLICT_KEYWORDS = {"class", "struct", "enum", "protocol", "extension", "import"}


def to_lower_camel(s: str) -> str:
    """``"address-book"`` -> ``"addressBook"``; ``"3d-cube"`` -> ``"_3dCube"``.

    Returns an empty string if ``s`` has no alphanumeric content — callers
    provide their own fallback.
    """
    parts = re.split(r"[^a-zA-Z0-9]+", s.strip())
    parts = [p for p in parts if p]
    if not parts:
        return ""
    first = parts[0].lower()
    rest = [p[:1].upper() + p[1:] for p in parts[1:]]
    out = first + "".join(rest)
    if re.match(r"^[0-9]", out):
        out = "_" + out
    return out


def emoji_case_name(asset_name: str) -> str:
    """``"emoji_grinning_face"`` -> ``"emojiGrinningFace"``."""
    out = to_lower_camel(asset_name) or "emoji"
    if out in CONFLICT_KEYWORDS:
        out += "Emoji"
    return out


def safe_asset_name(symbol_id: str) -> str:
    """Sanitize a symbol id for use as an xcassets asset name / filename."""
    s = symbol_id.strip().replace("/", "_").replace("\\", "_")
    return s or "icon"


def icon_case_name(symbol_id: str) -> str:
    """``"address-book"`` -> ``"addressBook"``; backticks Swift keywords."""
    out = to_lower_camel(symbol_id) or "_icon"
    if out in CONFLICT_KEYWORDS:
        out += "Icon"
    if out in SWIFT_KEYWORDS:
        out = f"`{out}`"
    return out
