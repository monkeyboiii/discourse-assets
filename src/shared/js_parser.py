"""Extract and parse ``export const X = ...`` literals from Discourse's data.js."""

import json
import re


def extract_js_object(text: str, export_name: str) -> str:
    """Return the body (including braces) of ``export const <name> = { ... };``."""
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


def extract_js_array(text: str, export_name: str) -> str:
    """Return the body (including brackets) of ``export const <name> = [ ... ];``."""
    pattern = rf"export\s+const\s+{re.escape(export_name)}\s*=\s*\["
    m = re.search(pattern, text)
    if not m:
        raise ValueError(f"Could not find 'export const {export_name}' in data.js")
    start = m.end() - 1
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError(f"Unbalanced brackets for {export_name}")


def js_obj_to_dict(js_body: str) -> dict:
    """Convert a JS object literal to a Python dict.

    Parses line-by-line to handle unquoted keys, quoted keys with special
    chars, single-quoted array values, and multi-line array values.
    """
    result: dict = {}
    current_key: str | None = None
    current_array: list[str] | None = None

    for line in js_body.split("\n"):
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


def js_array_to_list(js_body: str) -> list:
    """Convert a JS array literal to a Python list via JSON."""
    s = js_body.replace("'", '"')
    s = re.sub(r",\s*\]", "]", s)
    return json.loads(s)
