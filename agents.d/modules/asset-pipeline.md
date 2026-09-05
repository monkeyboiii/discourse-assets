---
kind: runbook
status: current
summary: How to regenerate DiscourseAssetKit's emoji PNGs/enums (emoji.sh) and icon xcassets/enum (icon.sh) from a Discourse forum; requirements, layout, tests, the mirrored shortcode sanitizer.
---

# discourse-assets

Python tooling that pulls emoji + icon assets from a *Discourse* forum and
generates Swift sources consumed by `DiscourseAssetKit`.

## Requirements

- [uv](https://github.com/astral-sh/uv) — scripts are one-off, no venv needed.
- `cairosvg` is pulled in by `icon.sh` via `uv run --with cairosvg`. On macOS
  it needs Homebrew `cairo` + `libffi`:

  ```bash
  brew install cairo libffi
  ```

## Usage

```bash
# Regenerate emoji PNGs, enum, and lookup tables
bash emoji.sh

# Regenerate icon xcassets and enum
bash icon.sh

# Override forum
FORUM_URL=https://your.forum.example bash emoji.sh
```

On a fresh clone, `emoji.sh` auto-seeds `assets/emojis/Emojis/` from the
committed package Resources so Step 1 skips the full ~3,400-PNG download.

## Layout

- `src/emoji/` — emoji PNG download + Swift enum / lookup / item-table generators
- `src/icon/` — SVG sprite dump + icon xcassets / enum generator
- `src/shared/` — shared helpers (shortcode sanitization, Swift emit, JS parser, naming)
- `assets/` — source data (`emojis.json`, `data.js`, `sprite-*.xml`)

## Tests

```bash
uv run python -m unittest discover tests -v
```

## Shortcode sanitization

`src/shared/shortcode.py::sanitize_shortcode_to_asset` is mirrored in Swift at
`Sources/DiscourseAssetKit/Emoji/Emoji+Init.swift` (`sanitizeShortcodeToAssetName`).
**Edit both or neither.**
