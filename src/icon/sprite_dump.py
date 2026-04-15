"""Download Discourse's SVG sprite from a hosted forum.

Fetches the forum root HTML, extracts ``data-svg-sprite-path`` from the
``data-discourse-setup`` meta tag, downloads the sprite .js, and unwraps
``window.__svg_sprite = "..."`` into an SVG file.
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


class _DiscourseSetupMetaParser(HTMLParser):
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
        self.base_url = attrs_dict.get("data-base-url") or self.base_url
        self.svg_sprite_path = attrs_dict.get("data-svg-sprite-path") or self.svg_sprite_path


def extract_svg_sprite_path(html_bytes: bytes) -> tuple[str | None, str | None]:
    text = html_bytes.decode("utf-8", errors="replace")

    parser = _DiscourseSetupMetaParser()
    parser.feed(text)
    if parser.svg_sprite_path:
        return parser.base_url, parser.svg_sprite_path

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
    return (
        base_match.group(1) if base_match else None,
        svg_match.group(1) if svg_match else None,
    )


def _decode_js_string_literal(lit: str) -> str:
    lit = lit.strip()
    if len(lit) >= 2 and lit[0] == '"' and lit[-1] == '"':
        return json.loads(lit)
    if len(lit) >= 2 and lit[0] == "'" and lit[-1] == "'":
        return ast.literal_eval(lit)
    raise ValueError("Unrecognized string literal quoting in sprite JS.")


def extract_svg_from_sprite_js(js_bytes: bytes) -> str:
    text = js_bytes.decode("utf-8", errors="replace")
    m = re.search(
        r"window\.__svg_sprite\s*=\s*(?P<lit>"
        r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')\s*;",
        text,
        flags=re.DOTALL,
    )
    if not m:
        raise ValueError(
            "Could not find `window.__svg_sprite = ...;` in JS.\n"
            f"JS starts with:\n{text[:4000]}"
        )
    svg = _decode_js_string_literal(m.group("lit"))
    return html.unescape(svg)


def pretty_print_xml_if_possible(xml_text: str) -> str:
    try:
        import xml.dom.minidom as minidom
        dom = minidom.parseString(xml_text.encode("utf-8"))
        pretty = dom.toprettyxml(indent="  ")
        return "\n".join(line for line in pretty.splitlines() if line.strip())
    except Exception:
        return xml_text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url", help="Base forum URL, e.g. https://forum.dirtbikechina.com")
    ap.add_argument("-o", "--out", default="discourse-sprite.xml", help="Output SVG file")
    ap.add_argument("--save-js", default=None, help="Also save the downloaded sprite .js")
    ap.add_argument("--no-pretty", action="store_true", help="Do not pretty-print the SVG")
    ap.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds")
    args = ap.parse_args()

    base_url = args.base_url.rstrip("/") + "/"
    html_bytes = http_get(base_url, timeout=args.timeout)

    meta_base_url, sprite_path = extract_svg_sprite_path(html_bytes)
    if not sprite_path:
        raise SystemExit(
            "Could not locate meta#data-discourse-setup with data-svg-sprite-path.\n"
            "Tip: Try fetching /latest or /categories if your homepage is customized."
        )

    effective_base = meta_base_url or base_url
    sprite_url = urljoin(effective_base.rstrip("/") + "/", sprite_path.lstrip("/"))

    js_bytes = http_get(sprite_url, timeout=args.timeout)
    if args.save_js:
        with open(args.save_js, "wb") as f:
            f.write(js_bytes)

    svg = extract_svg_from_sprite_js(js_bytes)
    if not args.no_pretty:
        svg = pretty_print_xml_if_possible(svg)

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
