#!/usr/bin/env python3
"""
Download and extract Discourse SVG sprite (<symbol> list) from a hosted forum.

Usage:
  python discourse_sprite_dump.py <url> -o sprite.svg
"""

from __future__ import annotations

import argparse
import ast
import html
import json
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin
from urllib.request import Request, urlopen


UA = "Mozilla/5.0 (compatible; discourse-sprite-dumper/1.0; +https://example.com)"


def http_get(url: str, timeout: int = 20) -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/javascript,*/*;q=0.8",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


class DiscourseSetupMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.svg_sprite_path: str | None = None
        self.base_url: str | None = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attrs_dict = dict(attrs)
        if attrs_dict.get("id") != "data-discourse-setup":
            return

        # Discourse provides these on the meta tag:
        # data-base-url="https://..."
        # data-svg-sprite-path="/svg-sprite/<host>/svg-..."
        self.base_url = attrs_dict.get("data-base-url") or self.base_url
        self.svg_sprite_path = attrs_dict.get("data-svg-sprite-path") or self.svg_sprite_path


def extract_svg_sprite_path(html_bytes: bytes) -> tuple[str | None, str | None]:
    """Return (base_url, svg_sprite_path) from the data-discourse-setup meta tag."""
    text = html_bytes.decode("utf-8", errors="replace")

    # Fast path: HTMLParser
    parser = DiscourseSetupMetaParser()
    parser.feed(text)
    if parser.svg_sprite_path:
        return parser.base_url, parser.svg_sprite_path

    # Fallback: regex search
    # Find the meta tag by id and then grab attributes.
    # This is less robust than parsing but helpful if HTML is malformed.
    meta_match = re.search(
        r"<meta[^>]+id=[\"']data-discourse-setup[\"'][^>]*>",
        text,
        flags=re.IGNORECASE,
    )
    if not meta_match:
        return None, None

    meta_tag = meta_match.group(0)
    base_match = re.search(r'data-base-url=[\'"]([^\'"]+)[\'"]', meta_tag, flags=re.I)
    svg_match = re.search(r'data-svg-sprite-path=[\'"]([^\'"]+)[\'"]', meta_tag, flags=re.I)

    base_url = base_match.group(1) if base_match else None
    svg_path = svg_match.group(1) if svg_match else None
    return base_url, svg_path


def decode_js_string_literal(lit: str) -> str:
    """
    Decode a JS string literal (including surrounding quotes) to a Python str.
    Handles common Discourse output: window.__svg_sprite = "....";
    """
    lit = lit.strip()

    # Most Discourse sprites use a double-quoted JS string; that's JSON-compatible.
    if len(lit) >= 2 and lit[0] == '"' and lit[-1] == '"':
        return json.loads(lit)

    # Sometimes it could be single-quoted. Try Python literal_eval (close enough for many cases).
    if len(lit) >= 2 and lit[0] == "'" and lit[-1] == "'":
        # ast.literal_eval will interpret escapes like \n, \t, \uXXXX, \\
        return ast.literal_eval(lit)

    raise ValueError("Unrecognized string literal quoting in sprite JS.")


def extract_svg_from_sprite_js(js_bytes: bytes) -> str:
    """
    Extract the SVG string from JS like:
      window.__svg_sprite = "....";
    """
    text = js_bytes.decode("utf-8", errors="replace")

    # Capture a JS string literal after window.__svg_sprite =
    # Supports both "..." and '...' and allows escaped characters / newlines.
    m = re.search(
        r"window\.__svg_sprite\s*=\s*(?P<lit>"
        r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')\s*;",
        text,
        flags=re.DOTALL,
    )
    if not m:
        # Some builds might omit window.__svg_sprite and export differently.
        # Show a small snippet to help debugging.
        snippet = text[:4000]
        raise ValueError(
            "Could not find `window.__svg_sprite = ...;` in JS.\n"
            f"JS starts with:\n{snippet}"
        )

    lit = m.group("lit")
    svg = decode_js_string_literal(lit)

    # In some cases the decoded string may contain HTML entities (rare, but safe to handle).
    svg = html.unescape(svg)
    return svg


def pretty_print_xml_if_possible(xml_text: str) -> str:
    # Optional pretty print. If it fails (some sprites contain quirks), return raw.
    try:
        import xml.dom.minidom as minidom

        dom = minidom.parseString(xml_text.encode("utf-8"))
        pretty = dom.toprettyxml(indent="  ")
        # Remove empty lines minidom loves to add
        pretty = "\n".join([line for line in pretty.splitlines() if line.strip()])
        return pretty
    except Exception:
        return xml_text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url", help="Base forum URL, e.g. https://forum.dirtbikechina.com")
    ap.add_argument("-o", "--out", default="discourse-sprite.xml", help="Output SVG file")
    ap.add_argument("--save-js", default=None, help="Optional path to save the downloaded sprite .js")
    ap.add_argument("--no-pretty", action="store_true", help="Do not pretty-print the SVG")
    ap.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/") + "/"

    # 1) Fetch HTML
    html_bytes = http_get(base_url, timeout=args.timeout)

    # 2) Parse meta tag
    meta_base_url, sprite_path = extract_svg_sprite_path(html_bytes)
    if not sprite_path:
        raise SystemExit(
            "Could not locate meta#data-discourse-setup with data-svg-sprite-path.\n"
            "Tip: Try fetching /latest or /categories if your homepage is customized."
        )

    effective_base = meta_base_url or base_url
    sprite_url = urljoin(effective_base.rstrip("/") + "/", sprite_path.lstrip("/"))

    # 3) Fetch sprite JS
    js_bytes = http_get(sprite_url, timeout=args.timeout)

    if args.save_js:
        with open(args.save_js, "wb") as f:
            f.write(js_bytes)

    # 4) Extract SVG from JS
    svg = extract_svg_from_sprite_js(js_bytes)

    # 5) Optionally format
    if not args.no_pretty:
        svg = pretty_print_xml_if_possible(svg)

    # 6) Write SVG
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"OK: wrote SVG sprite to {args.out}")
    print(f"Sprite JS URL: {sprite_url}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise
