#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate a static Swift lookup table (EmojiItemTable.swift) from emojis.json
and data.js, eliminating the need to bundle and parse JSON at runtime.

Emits EmojiItem and EmojiGroup instances directly (referencing the
DiscourseEmoji enum), so the picker store can use them without conversion.

Usage:
  python3 generate_emoji_items.py \
    --json ./assets/emojis.json \
    --datajs ./assets/data.js \
    --enum-file ../Sources/DiscourseAssetKit/Emoji/Generated/DiscourseEmoji.swift \
    --out ../Sources/DiscourseAssetKit/Emoji/Generated/EmojiItemTable.swift
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Reusable helpers (same logic as discourse_emojis.py / generate_emoji_lookups.py)
# ---------------------------------------------------------------------------

def _sanitize_shortcode_to_asset(shortcode_with_colons: str) -> str:
    """:grinning_face: -> emoji_grinning_face"""
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


def _swift_string_literal(s: str) -> str:
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def _make_search_blob(name: str, aliases: list[str]) -> str:
    """Replicate Swift EmojiPickerStore.makeSearchBlob + normalizeQuery."""
    parts = [name] + aliases
    parts = [p.replace("_", " ") for p in parts]
    joined = " ".join(parts)
    blob = joined.lower().strip().replace("_", " ")
    blob = re.sub(r"\s+", " ", blob)
    return blob


def _pretty_group_name(gid: str) -> str:
    """smileys_&_emotion -> Smileys & Emotion"""
    words = gid.replace("_", " ").replace("  ", " ").split(" ")
    return " ".join(w if w == "&" else (w[0].upper() + w[1:] if w else w) for w in words)


# ---------------------------------------------------------------------------
# Parse data.js for aliases (canonical -> [alias1, alias2, ...])
# ---------------------------------------------------------------------------

def _extract_js_object(text: str, export_name: str) -> str:
    pattern = rf"export\s+const\s+{re.escape(export_name)}\s*=\s*\{{"
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find 'export const {export_name}' in data.js")
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"Unbalanced braces for {export_name}")


def _js_obj_to_dict(js_body: str) -> dict:
    result: dict = {}
    lines = js_body.split("\n")
    current_key: str | None = None
    current_array: list[str] | None = None

    for line in lines:
        stripped = line.strip().rstrip(",")
        if stripped in ("{", "}", "[", "]", "};", ""):
            if stripped == "]" and current_key is not None and current_array is not None:
                result[current_key] = current_array
                current_key = None
                current_array = None
            continue
        if current_array is not None:
            if stripped.startswith("]"):
                result[current_key] = current_array
                current_key = None
                current_array = None
                continue
            m = re.match(r'^["\'](.+?)["\']', stripped)
            if m:
                current_array.append(m.group(1))
            continue
        m = re.match(r'^\s*"([^"]+)"\s*:\s*(.+)$', stripped)
        if not m:
            m = re.match(r'^\s*([\w+\-]+)\s*:\s*(.+)$', stripped)
        if not m:
            continue
        key = m.group(1)
        val_str = m.group(2).rstrip(",")
        if val_str.startswith("["):
            if val_str.endswith("]"):
                items = re.findall(r'["\']([^"\']+)["\']', val_str)
                result[key] = items
            else:
                current_key = key
                current_array = re.findall(r'["\']([^"\']+)["\']', val_str)
            continue
        vm = re.match(r'^["\'](.+?)["\']$', val_str)
        if vm:
            result[key] = vm.group(1)
        else:
            result[key] = val_str
    return result


def parse_aliases(datajs_text: str) -> dict[str, list[str]]:
    """canonical -> [alias1, alias2, ...]"""
    body = _extract_js_object(datajs_text, "aliases")
    raw = _js_obj_to_dict(body)
    result: dict[str, list[str]] = {}
    for key, val in raw.items():
        if isinstance(val, list):
            result[key] = val
        elif isinstance(val, str):
            result.setdefault(val, []).append(key)
    return result


# ---------------------------------------------------------------------------
# Asset name → enum case name conversion
# ---------------------------------------------------------------------------

def _to_lower_camel(s: str) -> str:
    """
    "emoji_grinning_face" -> "emojiGrinningFace"
    "emoji_3d_cube" -> "emoji3dCube"
    """
    parts = re.split(r"[^a-zA-Z0-9]+", s.strip())
    parts = [p for p in parts if p]
    if not parts:
        return "emoji"
    first = parts[0].lower()
    rest = [p[:1].upper() + p[1:] for p in parts[1:]]
    out = first + "".join(rest)
    if re.match(r"^[0-9]", out):
        out = "_" + out
    if out in {"class", "struct", "enum", "protocol", "extension", "import"}:
        out = out + "Emoji"
    return out


# ---------------------------------------------------------------------------
# Parse enum file for valid asset names
# ---------------------------------------------------------------------------

def parse_enum_asset_names(enum_path: Path) -> dict[str, str]:
    """Extract rawValue → caseName mapping from DiscourseEmoji enum cases."""
    text = enum_path.read_text(encoding="utf-8")
    pairs = re.findall(r'case\s+(\w+)\s*=\s*"([^"]+)"', text)
    return {raw: case for case, raw in pairs}


# ---------------------------------------------------------------------------
# Group metadata
# ---------------------------------------------------------------------------

CANONICAL_GROUP_ORDER = [
    "smileys_&_emotion",
    "people_&_body",
    "animals_&_nature",
    "food_&_drink",
    "travel_&_places",
    "activities",
    "objects",
    "symbols",
    "flags",
]

# group_id -> discourse emoji asset name (used as category icon in picker)
GROUP_ICONS: dict[str, str] = {
    "smileys_&_emotion": "emoji_grinning_face",
    "people_&_body":     "emoji_waving_hand",
    "animals_&_nature":  "emoji_monkey",
    "food_&_drink":      "emoji_grapes",
    "travel_&_places":   "emoji_globe_showing_europe_africa",
    "activities":        "emoji_jack_o_lantern",
    "objects":           "emoji_glasses",
    "symbols":           "emoji_atm_sign",
    "flags":             "emoji_chequered_flag",
}

DEFAULT_ICON = "emoji_red_question_mark"


# ---------------------------------------------------------------------------
# Swift code generation
# ---------------------------------------------------------------------------

def generate_item_table(
    emojis_json: dict[str, list[dict]],
    canonical_to_aliases: dict[str, list[str]],
    valid_assets: dict[str, str],
) -> str:
    lines: list[str] = []
    lines.append("// AUTO-GENERATED by generate_emoji_items.py -- do not edit")
    lines.append("")
    lines.append("// swiftlint:disable file_length")
    lines.append("")
    lines.append("enum EmojiItemTable {")

    # Determine group order
    known_set = set(CANONICAL_GROUP_ORDER)
    groups_with_entries = [g for g in emojis_json.keys() if emojis_json[g]]
    ordered_known = [g for g in CANONICAL_GROUP_ORDER if g in groups_with_entries]
    ordered_unknown = sorted(g for g in groups_with_entries if g not in known_set)
    group_order = ordered_known + ordered_unknown

    # Emit groups array (using EmojiGroup directly)
    lines.append("    static let groups: [EmojiGroup] = [")
    for gid in group_order:
        display_name = _pretty_group_name(gid)
        icon_asset = GROUP_ICONS.get(gid, DEFAULT_ICON)
        icon_case = valid_assets.get(icon_asset)
        if not icon_case:
            icon_case = _to_lower_camel(icon_asset)
        lines.append(
            f"        EmojiGroup("
            f"id: {_swift_string_literal(gid)}, "
            f"displayName: {_swift_string_literal(display_name)}, "
            f"discourseIcon: .{icon_case}"
            f"),"
        )
    lines.append("    ]")
    lines.append("")

    # Emit per-group arrays as separate static lets to reduce Swift
    # compiler memory (single massive dictionary literal causes exponential
    # type-checker cost).

    total = 0
    skipped_dup = 0
    skipped_missing = 0

    # Maps group_id -> Swift property name (for the final entries dict)
    group_prop_names: list[tuple[str, str]] = []

    for gid in group_order:
        entries = emojis_json[gid]
        items: list[tuple[str, str]] = []  # (baseName, swift_line)

        seen: set[str] = set()
        for entry in entries:
            name = entry["name"]
            if name in seen:
                skipped_dup += 1
                print(f"    [SKIP] duplicate '{name}' in group '{gid}'")
                continue
            seen.add(name)
            tonable = entry.get("tonable", False)
            search_aliases = entry.get("search_aliases", [])

            asset_name = _sanitize_shortcode_to_asset(f":{name}:")
            case_name = valid_assets.get(asset_name)
            if case_name is None:
                skipped_missing += 1
                print(f"    [SKIP] no enum case for '{name}' (asset: {asset_name}) in group '{gid}'")
                continue

            extra_aliases = canonical_to_aliases.get(name, [])
            all_aliases = search_aliases + extra_aliases
            blob = _make_search_blob(name, all_aliases)

            aliases_literal = ", ".join(_swift_string_literal(a) for a in search_aliases)
            tonable_str = "true" if tonable else "false"

            swift_line = (
                f"        EmojiItem("
                f"id: {_swift_string_literal(asset_name)}, "
                f"emoji: .{case_name}, "
                f"baseName: {_swift_string_literal(name)}, "
                f"groupId: {_swift_string_literal(gid)}, "
                f"tonable: {tonable_str}, "
                f"aliases: [{aliases_literal}], "
                f"searchBlob: {_swift_string_literal(blob)}"
                f"),"
            )
            items.append((name, swift_line))
            total += 1

        # Emit a private static let for this group
        prop_name = "_" + re.sub(r"[^A-Za-z0-9]+", "_", gid).strip("_")
        group_prop_names.append((gid, prop_name))
        lines.append(f"    private static let {prop_name}: [EmojiItem] = [")
        for _, swift_line in items:
            lines.append(swift_line)
        lines.append("    ]")
        lines.append("")

    # Emit the combined entries dictionary referencing per-group lets
    lines.append("    static let entries: [String: [EmojiItem]] = [")
    for gid, prop_name in group_prop_names:
        lines.append(f"        {_swift_string_literal(gid)}: {prop_name},")
    lines.append("    ]")
    lines.append("}")
    lines.append("")

    skipped = skipped_dup + skipped_missing
    print(f"  {len(group_order)} groups, {total} entries, {skipped} skipped ({skipped_dup} duplicate, {skipped_missing} missing asset)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate static EmojiItemTable.swift from emojis.json + data.js"
    )
    ap.add_argument("--json", required=True, type=Path, help="Path to emojis.json")
    ap.add_argument("--datajs", required=True, type=Path, help="Path to data.js")
    ap.add_argument("--enum-file", required=True, type=Path, help="Path to DiscourseEmoji.swift (for asset validation)")
    ap.add_argument("--out", required=True, type=Path, help="Output Swift file path")
    args = ap.parse_args()

    print("[1/4] Loading emojis.json...")
    emojis_json = json.loads(args.json.read_text(encoding="utf-8"))
    entry_count = sum(len(v) for v in emojis_json.values())
    print(f"  {len(emojis_json)} groups, {entry_count} entries")

    print("[2/4] Parsing data.js for aliases...")
    datajs_text = args.datajs.read_text(encoding="utf-8")
    canonical_to_aliases = parse_aliases(datajs_text)
    print(f"  {len(canonical_to_aliases)} canonical entries with aliases")

    print("[3/4] Reading DiscourseEmoji enum for asset validation...")
    valid_assets = parse_enum_asset_names(args.enum_file)  # rawValue → caseName
    print(f"  {len(valid_assets)} valid asset names")

    print("[4/4] Generating EmojiItemTable.swift...")
    swift_content = generate_item_table(emojis_json, canonical_to_aliases, valid_assets)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(swift_content, encoding="utf-8")
    print(f"  Written: {args.out}")

    print("[OK] Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
