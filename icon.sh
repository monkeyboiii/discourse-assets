#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")"

FORUM_URL="${FORUM_URL:-https://meta.discourse.org}"
KIT_DIR="../Sources/DiscourseAssetKit"


# ---------------------------------------------------------------------------
# Step 1: Dump SVG sprite XML
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 1: Dump SVG sprite XML ==="
uv run python -m src.icon.sprite_dump "$FORUM_URL" \
    -o assets/sprite.xml


# ---------------------------------------------------------------------------
# Step 2: Generate icons + Swift enum
# ---------------------------------------------------------------------------
echo ""
echo "=== Step 2: Generate icons + Swift enum ==="
uv run --with cairosvg python -m src.icon.generate \
    -i assets/sprite.xml \
    -o assets/icons/ \
    --xcassets "$KIT_DIR/Resources/DiscourseIcons.xcassets" \
    --swift "$KIT_DIR/Icon/Generated/DiscourseIcon.swift" \
    --enum-name DiscourseIcon \
    --incremental


echo ""
echo "=== Done ==="
echo "  xcassets:  $KIT_DIR/Resources/DiscourseIcons.xcassets/"
echo "  enum:      $KIT_DIR/Icon/Generated/DiscourseIcon.swift"
