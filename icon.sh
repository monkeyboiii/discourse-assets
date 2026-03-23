#!/usr/bin/env bash


set -euo pipefail
cd "$(dirname "$0")"


KIT_DIR="../Sources/DiscourseAssetKit"


# ---------------------------------------------------------------------------
# Step 1: Dump SVG sprite XML
# ---------------------------------------------------------------------------
echo "=== Step 1: Dump SVG sprite XML ==="
uv run \
    python discourse_sprite_dump.py https://forum.dirtbikechina.com \
        -o assets/sprite-dbc.xml


# ---------------------------------------------------------------------------
# Step 2: Generate icons + Swift enum
# ---------------------------------------------------------------------------
echo "=== Step 2: Generate icons + Swift enum ==="
uv run --with cairosvg \
    python discourse_sprite_icons.py \
        -i assets/sprite-dbc.xml \
        -o assets/icons/ \
        --pdf \
        --xcassets assets/icons/DiscourseIcons.xcassets \
        --swift "$KIT_DIR/Icon/Generated/DiscourseIcon.swift" \
        --enum-name DiscourseIcon


# ---------------------------------------------------------------------------
# Step 3: Copy xcassets into the Xcode project
# ---------------------------------------------------------------------------
echo "=== Step 3: Copy xcassets to App ==="
rsync -aEc assets/icons/DiscourseIcons.xcassets/ "$KIT_DIR/Resources/DiscourseIcons.xcassets/"


echo ""
echo "=== Done ==="
echo "  xcassets:  $KIT_DIR/Resources/DiscourseIcons.xcassets/"
echo "  enum:      $KIT_DIR/Icon/Generated/DiscourseIcon.swift"