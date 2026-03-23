#!/usr/bin/env bash


set -euo pipefail
cd "$(dirname "$0")"


FORUM_URL="https://forum.dirtbikechina.com"
KIT_DIR="../Sources/DiscourseAssetKit"
DATA_JS_URL="https://raw.githubusercontent.com/discourse/discourse/main/frontend/pretty-text/addon/emoji/data.js"


# ---------------------------------------------------------------------------
# Step 0: Download source data files
# ---------------------------------------------------------------------------
echo "=== Step 0: Download source data files ==="
curl -fsSL "$FORUM_URL/emojis.json" | uv run python -m json.tool --indent 4 --no-ensure-ascii > assets/emojis.json
curl -fsSL $DATA_JS_URL -o assets/data.js


# ---------------------------------------------------------------------------
# Step 1: Download emoji images & generate xcassets + Swift enum
# ---------------------------------------------------------------------------
echo "=== Step 1: Download emoji images & generate xcassets + Swift enum ==="
uv run \
    python discourse_emojis.py \
    --json assets/emojis.json \
    --out assets/emojis \
    --base-url "$FORUM_URL" \
    --download \
    --incremental \
    --swift "$KIT_DIR/Emoji/Generated/DiscourseEmoji.swift" \
    --enum-name DiscourseEmoji


# ---------------------------------------------------------------------------
# Step 2: Copy xcassets into the Xcode project
# ---------------------------------------------------------------------------
echo "=== Step 2: Copy xcassets to App ==="
rsync -aEc assets/emojis/DiscourseEmojis.xcassets/ "$KIT_DIR/Resources/DiscourseEmojis.xcassets/"


# ---------------------------------------------------------------------------
# Step 3: Generate lookup tables from Discourse data.js
#   - EmojiAliasTable.swift    (alias -> canonical name, ~770 entries)
#   - EmojiReplacementTable.swift (Unicode char -> shortcode, ~3400 entries)
#   - EmojiToneTable.swift     (tonable emoji set, ~300 entries)
# ---------------------------------------------------------------------------
echo "=== Step 3: Generate lookup tables (aliases, replacements, tones) ==="
uv run \
    python generate_emoji_lookups.py \
    --datajs assets/data.js \
    --out-dir "$KIT_DIR/Emoji/Generated"


# ---------------------------------------------------------------------------
# Step 4: Generate static emoji item table (replaces runtime JSON parsing)
#   - EmojiItemTable.swift  (pre-computed EmojiItem data, ~2000 entries)
# ---------------------------------------------------------------------------
echo "=== Step 4: Generate static emoji item table ==="
uv run \
    python generate_emoji_items.py \
    --json assets/emojis.json \
    --datajs assets/data.js \
    --enum-file "$KIT_DIR/Emoji/Generated/DiscourseEmoji.swift" \
    --out "$KIT_DIR/Emoji/Generated/EmojiItemTable.swift"


echo ""
echo "=== Done ==="
echo "  xcassets:  $KIT_DIR/Resources/DiscourseEmojis.xcassets/"
echo "  enum:      $KIT_DIR/Emoji/Generated/DiscourseEmoji.swift"
echo "  aliases:   $KIT_DIR/Emoji/Generated/EmojiAliasTable.swift"
echo "  replace:   $KIT_DIR/Emoji/Generated/EmojiReplacementTable.swift"
echo "  tones:     $KIT_DIR/Emoji/Generated/EmojiToneTable.swift"
echo "  items:     $KIT_DIR/Emoji/Generated/EmojiItemTable.swift"
