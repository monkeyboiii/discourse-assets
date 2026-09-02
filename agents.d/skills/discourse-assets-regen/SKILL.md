---
name: discourse-assets-regen
description: Regenerate DiscourseAssetKit's emoji PNGs + Swift enums (emoji.sh) or icon xcassets + enum (icon.sh) from a Discourse forum, then run the unit tests and inspect the diff in dak. Needs uv (+ cairosvg via brew cairo libffi on macOS); not runnable on the Linux dev box. Args: emoji|icon [FORUM_URL]
---

# discourse-assets-regen

Usage: `/discourse-assets-regen emoji|icon [FORUM_URL]`

Examples:
- `/discourse-assets-regen emoji` — refresh emoji from the stage forum (the default)
- `/discourse-assets-regen icon https://meta.discourse.org` — refresh icons from upstream's sprite

Read `agents.d/memory/MEMORY.md` first. All three facts apply to this loop.

## Preconditions

1. You are on a Mac with `uv` installed; for `icon`, `brew install cairo libffi` was done once.
   On the Linux dev box, stop here — `uv` is absent and nothing below can run.
2. `pwd` is `dak/discourse-assets` **inside the dak checkout** — `../Sources/DiscourseAssetKit`
   must exist (memory: `lives-inside-dak`).
3. `git -C .. status --short` is clean in dak, so the regenerated diff is attributable.

## Steps

1. Run the generator from this directory (source: `agents.d/modules/ASSET_PIPELINE.md § Usage`):
   ```bash
   bash emoji.sh                      # or: FORUM_URL=https://your.forum bash emoji.sh
   bash icon.sh
   ```
   `emoji.sh` step 0.5 seeds `assets/emojis/Emojis/` from the committed package Resources on a
   fresh clone, so step 1 skips the full ~3,400-PNG download.
2. Test the Python side:
   ```bash
   uv run python -m unittest discover tests -v
   ```
3. Inspect what changed in dak — the generator writes Swift and assets there, not here:
   ```bash
   git -C .. status --short
   git -C .. diff --stat -- Sources/DiscourseAssetKit
   ```
   New emoji land as flat PNGs under `Sources/DiscourseAssetKit/Resources/Emojis/` (never in an
   xcassets catalog — dak memory `flat-png-not-xcassets`); icons land in
   `Resources/DiscourseIcons.xcassets`.
4. If `src/shared/shortcode.py` changed, the Swift mirror in dak's `Emoji/Emoji+Init.swift`
   changes with it (memory: `shortcode-sanitizer-mirrored`).

## Verify

- `uv run python -m unittest discover tests -v` passes.
- In dak, the generated enums compile — a Mac build; on Linux this criterion is INSPECT.
- The dak commit that carries the regenerated assets is separate from the commit here, and dak's
  gitlink for `discourse-assets` is bumped after this repo is pushed (submodule first).
