#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")"

#
# https://meta.discourse.org forum does not expose search aliases, and has an extra default group
# which is not ideal for the script to process into EmojiItem swift struct
# so we use my self-hosted instance with search_aliases expposed
FORUM_URL="${FORUM_URL:-https://forum.dirtbikechina.com}"
KIT_DIR="../Sources/DiscourseAssetKit"
DATA_JS_URL="https://raw.githubusercontent.com/discourse/discourse/main/frontend/pretty-text/addon/emoji/data.js"


# ---------------------------------------------------------------------------
# Step 0: Download source data files
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 0: Download source data files ==="
curl -fsSL "$FORUM_URL/emojis.json" | uv run python -m json.tool --indent 4 --no-ensure-ascii > assets/emojis.json
curl -fsSL "$DATA_JS_URL" -o assets/data.js


# ---------------------------------------------------------------------------
# Step 0.5: Warm staging from the committed package
# ---------------------------------------------------------------------------
if [ ! -d assets/emojis/Emojis ] && [ -d "$KIT_DIR/Resources/Emojis" ]; then
    echo ""
    echo "=== Step 0.5: Seed staging from package Resources ==="
    mkdir -p assets/emojis
    rsync -ah "$KIT_DIR/Resources/Emojis" assets/emojis/
fi


# ---------------------------------------------------------------------------
# Step 1: Download emoji PNGs & generate Swift enum
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 1: Download emoji images ==="
uv run python -m src.emoji.download \
    --json assets/emojis.json \
    --out assets/emojis \
    --base-url "$FORUM_URL" \
    --download \
    --incremental \
    --swift "$KIT_DIR/Emoji/Generated/DiscourseEmoji.swift" \
    --enum-name DiscourseEmoji


# ---------------------------------------------------------------------------
# Step 2: Copy flat PNGs into the Swift package
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 2: Copy flat PNGs ==="
rm -rf "$KIT_DIR/Resources/Emojis"
cp -R assets/emojis/Emojis "$KIT_DIR/Resources/Emojis"


# ---------------------------------------------------------------------------
# Step 3: Generate lookup tables (aliases, replacements, tones)
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 3: Generate lookup tables ==="
uv run python -m src.emoji.lookups \
    --datajs assets/data.js \
    --out-dir "$KIT_DIR/Emoji/Generated"


# ---------------------------------------------------------------------------
# Step 4: Generate static emoji item table
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 4: Generate static emoji item table ==="
uv run python -m src.emoji.items \
    --json assets/emojis.json \
    --datajs assets/data.js \
    --enum-file "$KIT_DIR/Emoji/Generated/DiscourseEmoji.swift" \
    --out "$KIT_DIR/Emoji/Generated/EmojiItemTable.swift"


echo ""
echo "=== Done ==="
echo "  emojis:    $KIT_DIR/Resources/Emojis/"
echo "  enum:      $KIT_DIR/Emoji/Generated/DiscourseEmoji.swift"
echo "  aliases:   $KIT_DIR/Emoji/Generated/EmojiAliasTable.swift"
echo "  replace:   $KIT_DIR/Emoji/Generated/EmojiReplacementTable.swift"
echo "  tones:     $KIT_DIR/Emoji/Generated/EmojiToneTable.swift"
echo "  items:     $KIT_DIR/Emoji/Generated/EmojiItemTable.swift"
