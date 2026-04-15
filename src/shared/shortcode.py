"""Shortcode -> asset name sanitizer.

Mirror of ``DiscourseEmoji.sanitizeShortcodeToAssetName`` in
``Sources/DiscourseAssetKit/Emoji/Emoji+Init.swift``. The Python and Swift
implementations must stay in lockstep — edit both or neither.
"""

import re


def sanitize_shortcode_to_asset(shortcode_with_colons: str) -> str:
    sc = shortcode_with_colons.strip(":")
    if sc == "+1":
        sc = "plus_one"
    elif sc == "-1":
        sc = "minus_one"
    sc = re.sub(r"[^A-Za-z0-9_]+", "_", sc)
    sc = re.sub(r"_+", "_", sc).strip("_")
    if not sc:
        sc = "unknown"
    return f"emoji_{sc}"
