"""Xcode asset catalog operations for icon PDFs.

All functions accept the xcassets directory as an argument so callers can
target either a staging dir or the destination Resources dir directly.
"""

import json
import shutil
from pathlib import Path


def ensure_xcassets_root(xcassets_dir: Path) -> None:
    """Create the xcassets dir and (re)write its root Contents.json."""
    xcassets_dir.mkdir(parents=True, exist_ok=True)
    (xcassets_dir / "Contents.json").write_text(
        json.dumps({"info": {"author": "xcode", "version": 1}}, indent=2),
        encoding="utf-8",
    )


def write_imageset(xcassets_dir: Path, asset_name: str, src_file: Path) -> None:
    """Write ``<asset>.imageset/{src_file.name, Contents.json}`` (template rendering)."""
    imageset_dir = xcassets_dir / f"{asset_name}.imageset"
    imageset_dir.mkdir(parents=True, exist_ok=True)

    dst = imageset_dir / src_file.name
    dst.write_bytes(src_file.read_bytes())

    contents = {
        "images": [{"filename": src_file.name, "idiom": "universal"}],
        "info": {"author": "xcode", "version": 1},
        "properties": {"template-rendering-intent": "template"},
    }
    (imageset_dir / "Contents.json").write_text(
        json.dumps(contents, indent=2), encoding="utf-8"
    )


def imageset_pdf_exists(xcassets_dir: Path, asset_name: str) -> bool:
    """True if ``<asset>.imageset/<asset>.pdf`` is present at the destination."""
    return (xcassets_dir / f"{asset_name}.imageset" / f"{asset_name}.pdf").exists()


def delete_orphan_imagesets(xcassets_dir: Path, expected: set[str]) -> int:
    """Remove ``<name>.imageset`` dirs whose name isn't in ``expected``."""
    if not xcassets_dir.exists():
        return 0
    deleted = 0
    for child in xcassets_dir.iterdir():
        if child.is_dir() and child.name.endswith(".imageset"):
            name = child.name[: -len(".imageset")]
            if name not in expected:
                shutil.rmtree(child)
                deleted += 1
    return deleted
