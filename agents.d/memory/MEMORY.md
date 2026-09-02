# discourse-assets memory index

Facts true **only** for this repo. Lazily loaded: read this index, then open only the fact you
need. One line per fact; the fact itself lives in its own file.

- [It only works from inside dak](lives-inside-dak.md) — `emoji.sh`/`icon.sh` hard-code `KIT_DIR="../Sources/DiscourseAssetKit"`; the repo must sit at `dak/discourse-assets`, the path `dak/.gitmodules` declares
- [The shortcode sanitizer is mirrored in Swift](shortcode-sanitizer-mirrored.md) — `src/shared/shortcode.py::sanitize_shortcode_to_asset` ↔ dak `Emoji/Emoji+Init.swift::sanitizeShortcodeToAssetName`; edit both or neither
- [Two different default forums, on purpose](forum-url-defaults.md) — emoji come from `forum.dirtbikechina.com` (meta lacks `search_aliases`), icons from `meta.discourse.org`; `FORUM_URL` overrides either
