#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bundle Discourse emoji images into an Xcode Asset Catalog so you can render
emojis locally by *name* (shortcode) without fetching from the network.

Input: emojis.json from Discourse's /emojis.json endpoint.
  Structure: { "group_name": [{ "name", "url", "tonable", "group", "search_aliases" }, ...], ... }

Output:
  <out>/Emoji.xcassets/
    Contents.json
    emoji_smiley.imageset/
      Contents.json
      emoji_smiley.png

Asset naming rule (deterministic, no mapping file needed):
  shortcode "smiley" -> asset name "emoji_smiley"
  runtime usage: Image("emoji_smiley")

Example:
  python3 discourse_emojis.py \
    --json ./assets/emojis.json \
    --out ./assets/emojis \
    --base-url https://forum.dirtbikechina.com \
    --download --incremental
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sanitize_shortcode_to_asset(shortcode_with_colons: str) -> str:
    """
    ":grinning_face:" -> "emoji_grinning_face"
    Keep A-Za-z0-9_ only; everything else -> "_"
    """
    sc = shortcode_with_colons.strip(":")
    if sc == '+1':
        sc = "plus_one"
    elif sc == '-1':
        sc = "minus_one"
    sc = re.sub(r"[^A-Za-z0-9_]+", "_", sc)
    sc = re.sub(r"_+", "_", sc).strip("_")
    if not sc:
        sc = "unknown"
    return f"emoji_{sc}"


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


def _ext_from_url(url: str, default: str = ".png") -> str:
    path = urlparse(url).path
    _, ext = os.path.splitext(path)
    ext = (ext or default).lower()
    return ext


def _download(url: str, dst: Path) -> None:
    scheme, netloc, path, query, fragment = urlsplit(url)

    try:
        netloc = netloc.encode('idna').decode('ascii')
    except UnicodeError:
        pass

    path = quote(path, safe='/')
    query = quote(query, safe='=&?')
    fragment = quote(fragment, safe='')

    url = urlunsplit((scheme, netloc, path, query, fragment))
    dst.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (emoji-bundler)"})
    with urlopen(req, timeout=30) as resp:
        dst.write_bytes(resp.read())


def _create_xcassets_root(xcassets: Path, incremental: bool = False) -> None:
    if xcassets.exists() and not incremental:
        shutil.rmtree(xcassets)
    xcassets.mkdir(parents=True, exist_ok=True)
    _write_json(xcassets / "Contents.json", {"info": {"author": "xcode", "version": 1}})


def _create_imageset(xcassets: Path, asset_name: str, filename: str) -> Path:
    imageset = xcassets / f"{asset_name}.imageset"
    imageset.mkdir(parents=True, exist_ok=True)

    contents = {
        "images": [
            {"idiom": "universal", "filename": filename, "scale": "1x"},
            {"idiom": "universal", "scale": "2x"},
            {"idiom": "universal", "scale": "3x"},
        ],
        "info": {"author": "xcode", "version": 1},
    }
    _write_json(imageset / "Contents.json", contents)
    return imageset


def write_swift_enum(asset_names: list[str], swift_path: Path, enum_name: str = "EmojiAsset") -> None:
    """
    Generate a Swift enum mapping case names -> asset string.
    """
    lines: list[str] = []
    lines.append("import SwiftUI\n")
    lines.append(f"enum {enum_name}: String, CaseIterable {{")
    for asset_name in sorted(asset_names):
        case_name = _to_lower_camel(asset_name)
        lines.append(f'    case {case_name} = "{asset_name}"')
    lines.append("}")
    lines.append("")
    lines.append(f"extension {enum_name} {{")
    lines.append("    var image: Image { Image(self.rawValue) }")
    lines.append("}")
    lines.append("")

    swift_path.parent.mkdir(parents=True, exist_ok=True)
    swift_path.write_text("\n".join(lines), encoding="utf-8")


def _load_emoji_json(json_path: Path) -> list[dict[str, str]]:
    """Load emojis.json and return a flat list of {shortcode_with_colons, src}."""
    with open(json_path, encoding="utf-8") as f:
        emoji_data = json.load(f)

    items: list[dict[str, str]] = []
    for group_entries in emoji_data.values():
        for entry in group_entries:
            name = entry["name"]
            url = entry["url"]
            items.append({"shortcode_with_colons": f":{name}:", "src": url})
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True, type=Path, help="Path to emojis.json (from Discourse /emojis.json endpoint)")
    ap.add_argument("--out", required=True, type=Path, help="Output directory (will be created)")
    ap.add_argument("--base-url", default="", help="Base URL to resolve relative src (e.g. https://forum.dirtbikechina.com)")
    ap.add_argument("--download", action="store_true", help="Download images into the asset catalog")
    ap.add_argument("--allow-non-png", action="store_true", help="Allow non-png/jpg/jpeg/pdf assets (default: skip)")
    ap.add_argument("--duplicates", choices=["skip", "suffix", "error"], default="skip",
                    help="What to do if the same shortcode appears multiple times")
    ap.add_argument("--emit-report", action="store_true",
                    help="Emit a small report JSON (shortcode -> assetName, url) for debugging")
    ap.add_argument("--swift", default="", help="If set, path to generate a Swift enum file (e.g. Sources/Emojis.swift)")
    ap.add_argument("--enum-name", default="EmojiAsset", help="Swift enum name when using --swift")
    ap.add_argument("--incremental", action="store_true",
                    help="Incremental mode: keep existing assets, only download missing/new emojis")
    args = ap.parse_args()

    items = _load_emoji_json(args.json)

    if not items:
        print("[ERR] No emoji entries found in JSON.", file=sys.stderr)
        return 2

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    xcassets = out_dir / "DiscourseEmojis.xcassets"
    _create_xcassets_root(xcassets, incremental=args.incremental)

    base_url = args.base_url.strip()

    # Track uniqueness by shortcode (name), since that's what you'll use at runtime.
    seen_shortcodes: set[str] = set()
    used_asset_names: set[str] = set()

    report: list[dict[str, str]] = []
    downloaded = 0
    skipped = 0
    kept = 0

    for it in items:
        sc_with = it["shortcode_with_colons"]   # ":smiley:"
        sc_key = sc_with.strip(":")             # "smiley"
        src = it["src"]
        url = urljoin(base_url, src) if base_url else src

        if sc_key in seen_shortcodes:
            msg = f"[WARN] Duplicate shortcode '{sc_with}' encountered: {url}"
            if args.duplicates == "skip":
                print(msg + " (skipping duplicate)")
                skipped += 1
                continue
            if args.duplicates == "error":
                print("[ERR] " + msg, file=sys.stderr)
                return 3
            # suffix: continue but ensure asset name stays unique
        else:
            seen_shortcodes.add(sc_key)

        base_asset = _sanitize_shortcode_to_asset(sc_with)
        asset_name = base_asset

        if asset_name in used_asset_names:
            if args.duplicates == "suffix":
                k = 2
                while f"{base_asset}__{k}" in used_asset_names:
                    k += 1
                asset_name = f"{base_asset}__{k}"
            else:
                # duplicates=skip covers most; this is just extra safety
                print(f"[WARN] Asset name collision for '{sc_with}' -> {asset_name} (skipping)", file=sys.stderr)
                skipped += 1
                continue

        used_asset_names.add(asset_name)

        ext = _ext_from_url(url, default=".png")
        allowed = ext in {".png", ".jpg", ".jpeg", ".pdf"}
        if not allowed and not args.allow_non_png:
            print(f"[WARN] Skipping {sc_with} because extension '{ext}' may not work in Xcode imagesets: {url}")
            skipped += 1
            continue

        filename = f"{asset_name}{ext}"  # deterministic and collision-free
        imageset = _create_imageset(xcassets, asset_name, filename)
        image_path = imageset / filename

        if args.download:
            if args.incremental and image_path.exists() and image_path.stat().st_size > 0:
                kept += 1
            else:
                try:
                    _download(url, image_path)
                    downloaded += 1
                except Exception as ex:
                    print(f"[WARN] Download failed for {sc_with} from {url}: {ex}", file=sys.stderr)
                    skipped += 1
                    # remove imageset so your asset catalog stays clean
                    shutil.rmtree(imageset, ignore_errors=True)
                    used_asset_names.discard(asset_name)
                    continue

        if args.emit_report:
            report.append({
                "shortcodeWithColons": sc_with,
                "shortcode": sc_key,
                "assetName": asset_name,
                "url": url,
                "filename": filename,
            })

    if args.emit_report:
        _write_json(out_dir / "emoji_assets_report.json", report)

    if args.swift:
        swift_path = Path(args.swift).expanduser().resolve()
        write_swift_enum(list(used_asset_names), swift_path, enum_name=args.enum_name)

    print(f"[OK] Found emojis in JSON: {len(items)}")
    print(f"[OK] Assets created: {len(used_asset_names)}")
    if args.download:
        if args.incremental:
            print(f"[OK] Already present (kept): {kept}")
            print(f"[OK] Newly downloaded: {downloaded}")
        else:
            print(f"[OK] Downloaded: {downloaded}")
    else:
        print("[NOTE] Images were NOT downloaded (use --download).")
    print(f"[OK] Skipped: {skipped}")
    print(f"[OK] Xcode asset catalog: {xcassets}")
    if args.emit_report:
        print(f"[OK] Report: {out_dir / 'emoji_assets_report.json'}")
    if args.swift:
        print(f"[OK] Swift enum: {swift_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
