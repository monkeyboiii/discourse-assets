"""Parse a Discourse/FontAwesome-style SVG sprite into individual icons."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from src.shared.naming import safe_asset_name


@dataclass(frozen=True)
class SymbolIcon:
    symbol_id: str
    viewbox: str
    inner_xml: str


def extract_svg_block(text: str) -> str:
    """Pull the first ``<svg>...</svg>`` block out of raw text.

    Handles JS-escaped sprite strings (e.g. svg-*.js) by lightly unescaping
    common sequences when the extracted block looks escaped.
    """
    m = re.search(r"<svg\b[^>]*>.*?</svg>", text, flags=re.DOTALL | re.IGNORECASE)
    if not m:
        raise ValueError("Could not find an <svg>...</svg> block in the input.")
    svg = m.group(0)

    if "\\n" in svg or '\\"' in svg or "\\'" in svg:
        svg = (
            svg.replace("\\n", "\n")
               .replace("\\t", "\t")
               .replace('\\"', '"')
               .replace("\\'", "'")
               .replace("\\/", "/")
               .replace("\\\\", "\\")
        )
    return svg


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def parse_symbols(svg_text: str) -> list[SymbolIcon]:
    """Return one ``SymbolIcon`` per unique ``<symbol id=...>`` in the sprite."""
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse SVG XML: {e}") from e

    symbols: list[SymbolIcon] = []
    seen_ids: set[str] = set()
    for elem in root.iter():
        if _strip_ns(elem.tag).lower() != "symbol":
            continue
        sid = elem.attrib.get("id")
        if not sid or sid in seen_ids:
            continue
        seen_ids.add(sid)
        viewbox = (
            elem.attrib.get("viewBox")
            or elem.attrib.get("viewbox")
            or root.attrib.get("viewBox", "0 0 0 0")
        )
        inner_xml = "\n".join(
            ET.tostring(child, encoding="unicode") for child in list(elem)
        ).strip()
        symbols.append(SymbolIcon(symbol_id=sid, viewbox=viewbox, inner_xml=inner_xml))

    if not symbols:
        raise ValueError("No <symbol id='...'> elements found in the SVG.")
    return symbols


def build_standalone_svg(icon: SymbolIcon) -> str:
    """Wrap one symbol's inner XML in a complete standalone SVG document."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="{icon.viewbox}">\n'
        f"{icon.inner_xml}\n"
        "</svg>\n"
    )


def write_svg_files(icons: list[SymbolIcon], out_dir: Path) -> dict[str, Path]:
    """Write one standalone ``.svg`` per icon. Returns symbol_id -> path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, Path] = {}
    for icon in icons:
        asset = safe_asset_name(icon.symbol_id)
        p = out_dir / f"{asset}.svg"
        p.write_text(build_standalone_svg(icon), encoding="utf-8")
        mapping[icon.symbol_id] = p
    return mapping
