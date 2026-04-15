"""SVG → PDF conversion via cairosvg.

Includes a macOS Homebrew cairo bootstrap so cairocffi can find ``libcairo``
when uv's ephemeral environment doesn't pre-link it.
"""

import os
import sys
from pathlib import Path


def _macos_cairo_bootstrap() -> None:
    if sys.platform != "darwin":
        return
    import subprocess
    brew = subprocess.run(
        ["brew", "--prefix", "cairo"], capture_output=True, text=True
    )
    if brew.returncode != 0 or not brew.stdout.strip():
        return
    lib = os.path.join(brew.stdout.strip(), "lib")
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if lib in existing:
        return
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
        f"{lib}:{existing}" if existing else lib
    )


def svgs_to_pdfs(svg_paths: dict[str, Path], pdf_dir: Path) -> dict[str, Path]:
    """Convert each SVG to a PDF in ``pdf_dir``. Returns symbol_id -> pdf path."""
    _macos_cairo_bootstrap()

    try:
        import cairosvg  # type: ignore
    except Exception:
        raise RuntimeError(
            "cairosvg is required for PDF conversion. "
            "icon.sh invokes uv with --with cairosvg; check your uv install."
        )

    pdf_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for sid, svg_path in svg_paths.items():
        pdf_path = pdf_dir / (svg_path.stem + ".pdf")
        cairosvg.svg2pdf(bytestring=svg_path.read_bytes(), write_to=str(pdf_path))
        out[sid] = pdf_path
    return out
