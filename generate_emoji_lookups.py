#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parse Discourse's data.js and generate Swift lookup tables for:
  - aliases (alias -> canonical, canonical -> [aliases])
  - replacements (Unicode char -> canonical shortcode)
  - translations (emoticon text -> canonical shortcode)
  - tonableEmojis (Set of shortcodes that support skin tones)

Usage:
  python3 generate_emoji_lookups.py \
    --datajs ./assets/data.js \
    --out-dir ../App/Models/Site/Emoji/Generated
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _extract_js_object(text: str, export_name: str) -> str:
    """Extract the body of `export const <name> = { ... };` from JS source."""
    pattern = rf"export\s+const\s+{re.escape(export_name)}\s*=\s*\{{"
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find 'export const {export_name}' in data.js")
    start = m.end() - 1  # include the opening {
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"Unbalanced braces for {export_name}")


def _extract_js_array(text: str, export_name: str) -> str:
    """Extract the body of `export const <name> = [ ... ];` from JS source."""
    pattern = rf"export\s+const\s+{re.escape(export_name)}\s*=\s*\["
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find 'export const {export_name}' in data.js")
    start = m.end() - 1  # include the opening [
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"Unbalanced brackets for {export_name}")


def _js_obj_to_dict(js_body: str) -> dict:
    """Convert a JS object literal to a Python dict.

    Parses line-by-line to handle:
      - Unquoted keys (foo: ...)
      - Quoted keys with special chars (":'(": ...)
      - Single-quoted array values
      - Multi-line array values
    """
    result: dict = {}
    lines = js_body.split("\n")

    current_key: str | None = None
    current_array: list[str] | None = None

    for line in lines:
        stripped = line.strip().rstrip(",")

        # Skip braces-only lines
        if stripped in ("{", "}", "[", "]", "};", ""):
            if stripped == "]" and current_key is not None and current_array is not None:
                result[current_key] = current_array
                current_key = None
                current_array = None
            continue

        # Inside a multi-line array value
        if current_array is not None:
            if stripped.startswith("]"):
                result[current_key] = current_array
                current_key = None
                current_array = None
                continue
            # Array element: "value" or 'value'
            m = re.match(r'^["\'](.+?)["\']', stripped)
            if m:
                current_array.append(m.group(1))
            continue

        # Key-value line: either `key: value` or `"key": value`
        # Match quoted key
        m = re.match(r'^\s*"([^"]+)"\s*:\s*(.+)$', stripped)
        if not m:
            # Match bare key (unquoted, may contain +-)
            m = re.match(r'^\s*([\w+\-]+)\s*:\s*(.+)$', stripped)
        if not m:
            continue

        key = m.group(1)
        val_str = m.group(2).rstrip(",")

        # Value is an array starting on this line
        if val_str.startswith("["):
            if val_str.endswith("]"):
                # Single-line array: ["a", "b"]
                items = re.findall(r'["\']([^"\']+)["\']', val_str)
                result[key] = items
            else:
                # Multi-line array starts
                current_key = key
                current_array = re.findall(r'["\']([^"\']+)["\']', val_str)
            continue

        # Value is a string: "value" or 'value'
        vm = re.match(r'^["\'](.+?)["\']$', val_str)
        if vm:
            result[key] = vm.group(1)
        else:
            result[key] = val_str

    return result


def _js_array_to_list(js_body: str) -> list:
    """Convert a JS array literal to a Python list via JSON."""
    s = js_body
    s = s.replace("'", '"')
    s = re.sub(r",\s*\]", "]", s)
    return json.loads(s)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def parse_aliases(text: str) -> dict[str, list[str]]:
    """canonical -> [alias1, alias2, ...]"""
    body = _extract_js_object(text, "aliases")
    return _js_obj_to_dict(body)


def parse_replacements(text: str) -> dict[str, str]:
    """Unicode char -> canonical shortcode"""
    body = _extract_js_object(text, "replacements")
    return _js_obj_to_dict(body)


def parse_translations(text: str) -> dict[str, str]:
    """Emoticon text -> canonical shortcode"""
    body = _extract_js_object(text, "translations")
    return _js_obj_to_dict(body)


def parse_tonable(text: str) -> list[str]:
    """List of emoji shortcodes that support skin tones."""
    body = _extract_js_array(text, "tonableEmojis")
    return _js_array_to_list(body)


# ---------------------------------------------------------------------------
# Swift code generation
# ---------------------------------------------------------------------------

def _swift_string_literal(s: str) -> str:
    """Produce a Swift string literal, escaping as needed."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def generate_alias_table(aliases: dict[str, list[str]]) -> str:
    """Generate EmojiAliasTable.swift content."""
    lines: list[str] = []
    lines.append("// AUTO-GENERATED by generate_emoji_lookups.py -- do not edit")
    lines.append("")
    lines.append("// swiftlint:disable file_length")
    lines.append("")
    lines.append("enum EmojiAliasTable {")

    # alias -> canonical (inverted map, deduplicated — first canonical wins)
    lines.append("    /// Alias name -> canonical name")
    lines.append("    static let aliases: [String: String] = [")
    inverted: dict[str, str] = {}
    for canonical, alias_list in sorted(aliases.items()):
        for alias in alias_list:
            if alias not in inverted:
                inverted[alias] = canonical
    for alias, canonical in sorted(inverted.items()):
        lines.append(f"        {_swift_string_literal(alias)}: {_swift_string_literal(canonical)},")
    lines.append("    ]")
    lines.append("")

    # canonical -> [aliases]
    lines.append("    /// Canonical name -> alias names (for search augmentation)")
    lines.append("    static let canonicalToAliases: [String: [String]] = [")
    for canonical in sorted(aliases.keys()):
        alias_list = aliases[canonical]
        items = ", ".join(_swift_string_literal(a) for a in sorted(alias_list))
        lines.append(f"        {_swift_string_literal(canonical)}: [{items}],")
    lines.append("    ]")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_replacement_table(replacements: dict[str, str], translations: dict[str, str]) -> str:
    """Generate EmojiReplacementTable.swift content."""
    lines: list[str] = []
    lines.append("// AUTO-GENERATED by generate_emoji_lookups.py -- do not edit")
    lines.append("")
    lines.append("// swiftlint:disable file_length")
    lines.append("")
    lines.append("enum EmojiReplacementTable {")

    # Unicode -> shortcode
    lines.append("    /// Unicode emoji character -> canonical shortcode")
    lines.append("    static let unicodeToShortcode: [String: String] = [")
    for char, shortcode in sorted(replacements.items(), key=lambda x: x[1]):
        lines.append(f"        {_swift_string_literal(char)}: {_swift_string_literal(shortcode)},")
    lines.append("    ]")
    lines.append("")

    # Emoticon -> shortcode
    lines.append("    /// Emoticon text -> canonical shortcode")
    lines.append("    static let emoticonToShortcode: [String: String] = [")
    for emoticon, shortcode in sorted(translations.items(), key=lambda x: x[1]):
        lines.append(f"        {_swift_string_literal(emoticon)}: {_swift_string_literal(shortcode)},")
    lines.append("    ]")

    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_tone_table(tonable: list[str]) -> str:
    """Generate EmojiToneTable.swift content."""
    lines: list[str] = []
    lines.append("// AUTO-GENERATED by generate_emoji_lookups.py -- do not edit")
    lines.append("")
    lines.append("enum EmojiToneTable {")
    lines.append("    /// Emoji shortcodes that support skin tones")
    lines.append("    static let tonableEmojis: Set<String> = [")
    for name in sorted(set(tonable)):
        lines.append(f"        {_swift_string_literal(name)},")
    lines.append("    ]")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Swift emoji lookup tables from Discourse data.js")
    ap.add_argument("--datajs", required=True, type=Path, help="Path to data.js")
    ap.add_argument("--out-dir", required=True, type=Path, help="Output directory for generated Swift files")
    ap.add_argument("--phase", choices=["1", "2", "3", "all"], default="all",
                    help="Which phase to generate (default: all)")
    args = ap.parse_args()

    text = args.datajs.read_text(encoding="utf-8")
    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    phase = args.phase

    if phase in ("1", "all"):
        print("[Phase 1] Parsing aliases...")
        aliases = parse_aliases(text)
        total_aliases = sum(len(v) for v in aliases.values())
        print(f"  Found {len(aliases)} canonical entries with {total_aliases} total aliases")

        alias_swift = generate_alias_table(aliases)
        alias_path = out_dir / "EmojiAliasTable.swift"
        alias_path.write_text(alias_swift, encoding="utf-8")
        print(f"  Written: {alias_path}")

    if phase in ("2", "all"):
        print("[Phase 2] Parsing replacements and translations...")
        replacements = parse_replacements(text)
        translations = parse_translations(text)
        print(f"  Found {len(replacements)} Unicode replacements, {len(translations)} emoticon translations")

        replacement_swift = generate_replacement_table(replacements, translations)
        replacement_path = out_dir / "EmojiReplacementTable.swift"
        replacement_path.write_text(replacement_swift, encoding="utf-8")
        print(f"  Written: {replacement_path}")

    if phase in ("3", "all"):
        print("[Phase 3] Parsing tonable emojis...")
        tonable = parse_tonable(text)
        print(f"  Found {len(tonable)} tonable emojis")

        tone_swift = generate_tone_table(tonable)
        tone_path = out_dir / "EmojiToneTable.swift"
        tone_path.write_text(tone_swift, encoding="utf-8")
        print(f"  Written: {tone_path}")

    print("[OK] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
