#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

FORUM_URL="https://forum.dirtbikechina.com"
APP_DIR="../../App"


# ---------------------------------------------------------------------------
# Step 1: Download emoji images & generate xcassets + Swift enum
# ---------------------------------------------------------------------------
# Requires: assets/emojis.json (pre-downloaded from /emojis.json endpoint)
echo "=== Step 1: Download emoji images & generate xcassets + Swift enum ==="
uv run \
    python discourse_emojis.py \
    --json assets/emojis.json \
    --out assets/emojis \
    --base-url "$FORUM_URL" \
    --download \
    --incremental \
    --swift DiscourseEmoji.swift \
    --enum-name DiscourseEmoji


# ---------------------------------------------------------------------------
# Step 2: Copy xcassets into the Xcode project
# ---------------------------------------------------------------------------
echo "=== Step 2: Copy xcassets to App ==="
cp -r assets/emojis/DiscourseEmojis.xcassets/ "$APP_DIR/DiscourseEmojis.xcassets/"


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
    --out-dir "$APP_DIR/Models/Site/Emoji/Generated"


# ---------------------------------------------------------------------------
# Manual step: copy DiscourseEmoji.swift enum content into
#   App/Views/DesignSystem/Emoji/DiscourseEmoji.swift
# The app file has a hand-written extension (sanitizeShortcodeToAssetName,
# init?(shortcodeWithColons:)) that must be preserved after the enum cases.
# ---------------------------------------------------------------------------

echo ""
echo "=== Done ==="
echo "  xcassets:  $APP_DIR/DiscourseEmojis.xcassets/"
echo "  enum:      DiscourseEmoji.swift (merge into app manually)"
echo "  aliases:   $APP_DIR/Models/Site/Emoji/Generated/EmojiAliasTable.swift"
echo "  replace:   $APP_DIR/Models/Site/Emoji/Generated/EmojiReplacementTable.swift"
echo "  tones:     $APP_DIR/Models/Site/Emoji/Generated/EmojiToneTable.swift"
echo ""
echo "NOTE: Manually merge DiscourseEmoji.swift enum cases into"
echo "  App/Views/DesignSystem/Emoji/DiscourseEmoji.swift"
echo "  (preserve the extension at the bottom of that file)"
