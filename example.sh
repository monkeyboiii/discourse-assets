#!/usr/bin/env bash

set -euo pipefail

source activate .venv/bin/activate


uv run \
    python discourse_sprite_dump.py https://forum.dirtbikechina.com \
        -o assets/sprite.xml


uv run --with cairosvg \
    python discourse_sprite_icons.py \
        -i assets/icons.xml \
        -o assets/icons/ \
        --pdf \
        --xcassets DiscourseIcons.xcassets \
        --swift DiscourseIcons.swift \
        --enum-name DiscourseIcon

uv run \
    python discourse_emojis.py \
    --html emojis.html \
    --out assets/emojis \
    --base-url https://forum.dirtbikechina.com \
    --download
