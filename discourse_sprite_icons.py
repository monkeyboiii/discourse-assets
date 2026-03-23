#!/usr/bin/env python3
"""
Parse a Discourse/FontAwesome-style SVG sprite and generate:
- Individual SVG files per <symbol>
- Optional PDF conversion (via cairosvg)
- Optional Xcode .xcassets image sets (template rendering intent)
- Optional Swift enum for Image("assetName")

Works with:
- Raw .svg sprite files
- Discourse fingerprinted sprite JS files (e.g. svg-1-<hash>.js)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import xml.etree.ElementTree as ET


# ----------------------------- utilities -----------------------------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_svg_block(text: str) -> str:
    """
    Extract the first <svg ...> ... </svg> block from a blob of text.
    Handles JS sprite files that embed SVG as a string with backslash escapes.
    """
    m = re.search(r"<svg\b[^>]*>.*?</svg>", text, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        raise ValueError("Could not find an <svg>...</svg> block in the input.")
    svg = m.group(0)

    # If this looks like a JS-escaped string (lots of \n and \"), unescape lightly.
    # We only unescape common sequences; we do NOT run a full unicode_escape decode
    # to avoid accidentally rewriting valid path data.
    if "\\n" in svg or "\\\"" in svg or "\\'" in svg:
        svg = (
            svg.replace("\\n", "\n")
               .replace("\\t", "\t")
               .replace('\\"', '"')
               .replace("\\'", "'")
               .replace("\\/", "/")
               .replace("\\\\", "\\")
        )
    return svg


def strip_ns(tag: str) -> str:
    # "{http://www.w3.org/2000/svg}symbol" -> "symbol"
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def to_lower_camel(s: str) -> str:
    """
    "address-book" -> "addressBook"
    "far-eye" -> "farEye"
    "3d-cube" -> "_3dCube"
    """
    parts = re.split(r"[^a-zA-Z0-9]+", s.strip())
    parts = [p for p in parts if p]
    if not parts:
        return "_icon"
    first = parts[0].lower()
    rest = [p[:1].upper() + p[1:] for p in parts[1:]]
    out = first + "".join(rest)
    if re.match(r"^[0-9]", out):
        out = "_" + out
    # Avoid a few Swift keywords that can't be used even with backticks as enum cases
    if out in {"class", "struct", "enum", "protocol", "extension", "import"}:
        out = out + "Icon"
    return out


def safe_asset_name(symbol_id: str) -> str:
    """
    Asset names can contain '-' etc. Keep them stable and readable.
    Just remove path separators and surrounding whitespace.
    """
    s = symbol_id.strip().replace("/", "_").replace("\\", "_")
    return s or "icon"


@dataclass(frozen=True)
class SymbolIcon:
    symbol_id: str
    viewbox: str
    inner_xml: str  # children content as XML string


# ----------------------------- parsing -----------------------------

def parse_symbols(svg_text: str) -> List[SymbolIcon]:
    """
    Parse the sprite SVG and return all <symbol> entries with id + viewBox + inner XML.
    """
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse SVG XML: {e}") from e

    # Find all <symbol> nodes (namespace-insensitive), deduplicate by id
    symbols: List[SymbolIcon] = []
    seen_ids: set[str] = set()
    for elem in root.iter():
        if strip_ns(elem.tag).lower() != "symbol":
            continue
        sid = elem.attrib.get("id")
        if not sid or sid in seen_ids:
            continue
        seen_ids.add(sid)
        viewbox = elem.attrib.get("viewBox") or elem.attrib.get("viewbox")
        if not viewbox:
            # Some sprites may omit; try inheriting from root viewBox if present
            viewbox = root.attrib.get("viewBox", "0 0 0 0")

        # Serialize children (not including the <symbol> tag itself)
        inner_parts: List[str] = []
        for child in list(elem):
            inner_parts.append(ET.tostring(child, encoding="unicode"))
        inner_xml = "\n".join(inner_parts).strip()

        symbols.append(SymbolIcon(symbol_id=sid, viewbox=viewbox, inner_xml=inner_xml))

    if not symbols:
        raise ValueError("No <symbol id='...'> elements found in the SVG.")
    return symbols


def build_standalone_svg(icon: SymbolIcon) -> str:
    # Minimal standalone SVG wrapper for each symbol
    # Keep viewBox and inner nodes intact.
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="{icon.viewbox}">\n'
        f"{icon.inner_xml}\n"
        "</svg>\n"
    )


# ----------------------------- outputs -----------------------------

def write_svg_files(icons: Iterable[SymbolIcon], out_dir: Path) -> Dict[str, Path]:
    """
    Write one .svg per symbol id. Returns map: symbol_id -> svg_path
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: Dict[str, Path] = {}
    for icon in icons:
        asset = safe_asset_name(icon.symbol_id)
        p = out_dir / f"{asset}.svg"
        p.write_text(build_standalone_svg(icon), encoding="utf-8")
        mapping[icon.symbol_id] = p
    return mapping


def try_convert_svgs_to_pdf(svg_paths: Dict[str, Path], pdf_dir: Path) -> Dict[str, Path]:
    """
    Convert SVGs to PDFs using cairosvg if installed.
    Returns map: symbol_id -> pdf_path
    """
    # Help cairocffi find Homebrew's cairo on macOS
    if sys.platform == "darwin":
        import subprocess as _sp
        _brew = _sp.run(["brew", "--prefix", "cairo"], capture_output=True, text=True)
        if _brew.returncode == 0 and _brew.stdout.strip():
            _lib = os.path.join(_brew.stdout.strip(), "lib")
            _existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
            if _lib not in _existing:
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{_lib}:{_existing}" if _existing else _lib

    try:
        import cairosvg  # type: ignore
    except Exception:
        raise RuntimeError(
            "PDF conversion requested but cairosvg is not installed.\n"
            "Install it with: pip install cairosvg\n"
            "Or run without --pdf."
        )

    pdf_dir.mkdir(parents=True, exist_ok=True)
    out: Dict[str, Path] = {}
    for sid, svg_path in svg_paths.items():
        pdf_path = pdf_dir / (svg_path.stem + ".pdf")
        svg_bytes = svg_path.read_bytes()
        cairosvg.svg2pdf(bytestring=svg_bytes, write_to=str(pdf_path))
        out[sid] = pdf_path
    return out


def write_xcassets(
    symbol_to_file: Dict[str, Path],
    xcassets_dir: Path,
    template: bool = True,
) -> None:
    """
    Create an Xcode asset catalog with one imageset per symbol.
    The file for each imageset is copied into the imageset folder.

    Note: Works best with PDF (vector) assets. SVG may work depending on Xcode version,
    but PDF is the most reliable path for iOS.
    """
    xcassets_dir.mkdir(parents=True, exist_ok=True)
    # Root Contents.json (optional but harmless)
    root_contents = {"info": {"author": "xcode", "version": 1}}
    (xcassets_dir / "Contents.json").write_text(json.dumps(root_contents, indent=2), encoding="utf-8")

    for sid, src in symbol_to_file.items():
        asset_name = safe_asset_name(sid)
        imageset_dir = xcassets_dir / f"{asset_name}.imageset"
        imageset_dir.mkdir(parents=True, exist_ok=True)

        dst_filename = src.name
        dst = imageset_dir / dst_filename
        dst.write_bytes(src.read_bytes())

        contents: Dict[str, object] = {
            "images": [
                {
                    "filename": dst_filename,
                    "idiom": "universal",
                }
            ],
            "info": {"author": "xcode", "version": 1},
        }
        if template:
            contents["properties"] = {"template-rendering-intent": "template"}

        (imageset_dir / "Contents.json").write_text(json.dumps(contents, indent=2), encoding="utf-8")


_SWIFT_KEYWORDS = {
    "associatedtype", "class", "deinit", "enum", "extension", "func",
    "import", "init", "inout", "let", "operator", "precedencegroup",
    "protocol", "struct", "subscript", "typealias", "var",
    "break", "case", "continue", "default", "defer", "do", "else",
    "fallthrough", "for", "guard", "if", "in", "repeat", "return",
    "switch", "where", "while",
    "as", "catch", "false", "is", "nil", "rethrows", "self", "super",
    "throw", "throws", "true", "try",
}


def _swift_case(name: str) -> str:
    """Backtick-escape Swift reserved keywords used as enum case names."""
    return f"`{name}`" if name in _SWIFT_KEYWORDS else name


def write_swift_enum(symbol_ids: List[str], swift_path: Path, enum_name: str = "IconAsset") -> None:
    """
    Generate a Swift enum mapping case names -> asset string.
    """
    lines: List[str] = []
    lines.append("// AUTO-GENERATED by discourse_sprite_icons.py -- do not edit\n")
    lines.append("// swiftlint:disable file_length\n")
    lines.append("import SwiftUI\n")
    lines.append("/// ref: https://github.com/discourse/discourse/blob/main/lib/svg_sprite.rb")
    lines.append(f"public enum {enum_name}: String, CaseIterable, Sendable {{")
    for sid in sorted(symbol_ids):
        case_name = to_lower_camel(safe_asset_name(sid))
        asset_name = safe_asset_name(sid)
        lines.append(f'    case {_swift_case(case_name)} = "{asset_name}"')
    lines.append("}")
    lines.append("")
    lines.append(f"extension {enum_name} {{")
    lines.append("    public var image: Image { Image(self.rawValue, bundle: .module) }")
    lines.append("}")
    lines.append("")

    swift_path.parent.mkdir(parents=True, exist_ok=True)
    swift_path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------- main -----------------------------

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Split Discourse SVG sprite into per-icon assets and optional xcassets.")
    ap.add_argument("--input", "-i", required=True, help="Path to sprite file (.svg or Discourse svg-*.js)")
    ap.add_argument("--out", "-o", required=True, help="Output directory for generated files")
    ap.add_argument("--svg-dir", default="svgs", help="Subdir under --out for standalone SVGs")
    ap.add_argument("--pdf", action="store_true", help="Also convert each SVG to PDF (requires cairosvg)")
    ap.add_argument("--pdf-dir", default="pdfs", help="Subdir under --out for PDFs (when --pdf enabled)")
    ap.add_argument("--xcassets", default="", help="If set, path to generate an .xcassets catalog at this location")
    ap.add_argument("--swift", default="", help="If set, path to generate a Swift enum file (e.g. Sources/Icons.swift)")
    ap.add_argument("--enum-name", default="IconAsset", help="Swift enum name when using --swift")
    ap.add_argument("--filter", default="", help="Regex to include only symbol ids matching this pattern")
    args = ap.parse_args(argv)

    in_path = Path(args.input).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    text = read_text(in_path)
    svg_block = extract_svg_block(text)
    icons = parse_symbols(svg_block)

    if args.filter:
        rx = re.compile(args.filter)
        icons = [ic for ic in icons if rx.search(ic.symbol_id)]
        if not icons:
            print("Filter removed all icons; nothing to do.", file=sys.stderr)
            return 2

    svg_dir = out_root / args.svg_dir
    symbol_to_svg = write_svg_files(icons, svg_dir)

    symbol_to_asset_file: Dict[str, Path] = symbol_to_svg

    if args.pdf:
        pdf_dir = out_root / args.pdf_dir
        symbol_to_pdf = try_convert_svgs_to_pdf(symbol_to_svg, pdf_dir)
        symbol_to_asset_file = symbol_to_pdf  # prefer PDFs for xcassets

    if args.xcassets:
        xcassets_dir = Path(args.xcassets).expanduser().resolve()
        write_xcassets(symbol_to_asset_file, xcassets_dir, template=True)

    if args.swift:
        swift_path = Path(args.swift).expanduser().resolve()
        write_swift_enum([ic.symbol_id for ic in icons], swift_path, enum_name=args.enum_name)

    # Manifest for debugging / bookkeeping
    manifest = {
        "input": str(in_path),
        "count": len(icons),
        "icons": [
            {
                "id": ic.symbol_id,
                "viewBox": ic.viewbox,
                "svg": str(symbol_to_svg[ic.symbol_id]),
                "assetFile": str(symbol_to_asset_file[ic.symbol_id]),
            }
            for ic in icons
        ],
    }
    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Done. Generated {len(icons)} icons under: {out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
